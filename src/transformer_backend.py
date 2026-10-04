"""A pinned, record-local CPU decoder for the exact-statistic target V.

This is an executable architecture specification, not an adapter claiming
equivalence to GPTQ, Hugging Face, or a pretrained checkpoint.  Callers supply
weights and token IDs; this module downloads nothing.  Each pre-LayerNorm
decoder block has causal multihead attention and an erf-GELU MLP.  The ordered
quantization stages are fused QKV, attention output, MLP up, and MLP down in
each block.  Embeddings, norms, biases, and the final language-model head stay
fixed.  All earlier stages are declared dependencies (a conservative DAG).

Finite evaluation uses explicit Python binary64 multiply/add/divide schedules,
and the pinned host's ``math.sqrt/exp/erf``.  No BLAS, fused dot, batching,
dropout, cache, reassociation, or parallel reduction is used.  A manifest binds
the source, architecture, exact weights, CPython version, executable, math
extension, loaded libm, and libc identity.  Reproduction requires this manifest
and the declared host contract; cross-platform bitwise equality is NOT claimed.
Linux x86-64/AArch64 with round-to-nearest and gradual underflow is checked at
each public evaluation.  The caller must not change the floating environment
during that evaluation.  Nonfinite inputs/intermediates are target errors.

``stage_features`` transposes token-major finite activations to a d-by-T matrix
of ``Fraction.from_float`` values.  These are exact data for V: this statement
does not require libm to equal ideal real transcendental functions.  Exact
rational metric/rounding statistics belong to the separate repair service.
Rational installed codes are explicitly rounded by ``float(Fraction)`` before
neural evaluation, and this conversion is part of the target.

No analytic floating-error transport certificate is supplied.  The only
shortcut proved here is structural identity: if every relevant installed
matrix has the same finite entries as the base matrix, stage inputs are
identical.  Every other discrepancy request returns UNKNOWN and must replay.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys
from types import MappingProxyType
from typing import Any, Mapping, Sequence


ExactMatrix = tuple[tuple[Fraction, ...], ...]
FloatMatrix = tuple[tuple[float, ...], ...]
ExactVector = tuple[Fraction, ...]
Prefix = Mapping[str, Sequence[Sequence[int | Fraction]]]


class FiniteTargetError(ValueError):
    """The declared finite decoder program is undefined for this input."""


@dataclass(frozen=True)
class DecoderConfig:
    vocabulary_size: int
    model_width: int
    head_count: int
    feedforward_width: int
    block_count: int
    max_sequence_length: int
    layernorm_epsilon: float = 1e-5
    activation: str = "gelu"

    def __post_init__(self) -> None:
        for name in (
            "vocabulary_size", "model_width", "head_count", "feedforward_width",
            "block_count", "max_sequence_length",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive built-in integer")
        if self.model_width % self.head_count:
            raise ValueError("model_width must be divisible by head_count")
        eps = self.layernorm_epsilon
        if type(eps) is not float or not math.isfinite(eps) or eps <= 0:
            raise ValueError("layernorm_epsilon must be a positive finite float")
        if self.activation not in ("gelu", "gelu_new"):
            raise ValueError("activation must be gelu or gelu_new")


def _checked(value: float, where: str) -> float:
    if not math.isfinite(value):
        raise FiniteTargetError(f"nonfinite intermediate in {where}")
    return value


def _exact(value: int | float | Fraction, where: str) -> Fraction:
    if type(value) is int:
        out = Fraction(value)
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{where} must be finite")
        out = Fraction.from_float(value)
    elif isinstance(value, Fraction):
        out = value
    else:
        raise TypeError(f"{where} must be int, float, or Fraction; bool is rejected")
    try:
        _checked(float(out), where)
    except (OverflowError, FiniteTargetError) as exc:
        raise ValueError(f"{where} must convert to finite binary64") from exc
    return out


def _matrix(values: Sequence[Sequence[Any]], rows: int, cols: int, name: str) -> ExactMatrix:
    out = tuple(tuple(_exact(x, f"{name}[{i}][{j}]") for j, x in enumerate(row))
                for i, row in enumerate(values))
    if len(out) != rows or any(len(row) != cols for row in out):
        raise ValueError(f"{name} must have shape {rows} by {cols}")
    return out


def _vector(values: Sequence[Any] | None, size: int, name: str,
            default: int = 0) -> ExactVector:
    out = tuple(_exact(x, f"{name}[{i}]") for i, x in enumerate(values)) if values is not None else (Fraction(default),) * size
    if len(out) != size:
        raise ValueError(f"{name} must have length {size}")
    return out


def _floats(values: ExactMatrix) -> FloatMatrix:
    return tuple(tuple(float(x) for x in row) for row in values)


def _serial_exact(value: Any) -> Any:
    if isinstance(value, Fraction):
        return [str(value.numerator), str(value.denominator)]
    if isinstance(value, Mapping):
        return {str(k): _serial_exact(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_serial_exact(v) for v in value]
    return value


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _rounding_probe() -> Any:
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "aarch64"):
        raise RuntimeError("this pinned backend supports Linux x86_64/aarch64 only")
    try:
        probe = ctypes.CDLL(None).fegetround
    except AttributeError as exc:
        raise RuntimeError("fegetround is required to check the finite target") from exc
    probe.restype = ctypes.c_int
    probe.argtypes = []
    return probe


def _check_runtime() -> None:
    if sys.implementation.name != "cpython" or (
        sys.float_info.radix, sys.float_info.mant_dig, sys.float_info.max_exp
    ) != (2, 53, 1024):
        raise RuntimeError("the finite target requires CPython IEEE binary64")
    # FE_TONEAREST is 0 on the two supported Linux architectures.
    if _rounding_probe()() != 0:
        raise RuntimeError("the finite target requires round-to-nearest mode")
    tiny = float.fromhex("0x0.0000000000001p-1022")
    if sys.float_info.min * 0.5 != float.fromhex("0x0.8000000000000p-1022") or tiny * 1.0 != tiny:
        raise RuntimeError("the finite target requires gradual underflow, not FTZ/DAZ")


@lru_cache(maxsize=1)
def _runtime_manifest() -> dict[str, Any]:
    _check_runtime()
    # /proc maps binds the actual loaded libm, not just a package version.
    paths = set()
    python_libraries = set()
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[-1].startswith("/"):
            path = fields[-1]
            if Path(path).name.startswith("libm.so"):
                paths.add(path)
            if Path(path).name.startswith("libpython"):
                python_libraries.add(path)
    if not paths:
        raise RuntimeError("cannot identify the loaded libm for the kernel manifest")
    # libm may dispatch by CPU capability even when its file hash is equal.
    # Retain stable hardware-identification fields, excluding clock readings.
    cpu_fields = {}
    selected = {"vendor_id", "cpu family", "model", "model name", "stepping", "flags",
                "CPU implementer", "CPU architecture", "CPU variant", "CPU part", "CPU revision", "Features"}
    for line in Path("/proc/cpuinfo").read_text().split("\n\n", 1)[0].splitlines():
        if ":" in line:
            key, value = (part.strip() for part in line.split(":", 1))
            if key in selected:
                cpu_fields[key] = value
    return {
        "python": sys.version,
        "implementation": sys.implementation.name,
        "python_executable_sha256": _file_hash(sys.executable),
        "math_extension_sha256": _file_hash(math.__file__) if getattr(math, "__file__", None) else "built-in; bound by Python binaries",
        "loaded_python_libraries_sha256": sorted(_file_hash(path) for path in python_libraries),
        "loaded_libm_sha256": sorted(_file_hash(path) for path in paths),
        "libc": list(platform.libc_ver()),
        "system": platform.system(), "machine": platform.machine(),
        "cpu_dispatch_fields": cpu_fields,
        "byteorder": sys.byteorder,
        "binary64": [sys.float_info.radix, sys.float_info.mant_dig, sys.float_info.max_exp],
        "rounding": "nearest; caller must not mutate fenv during evaluation",
        "subnormals": "gradual underflow; checked at each public evaluation",
    }


def _sum(values: Sequence[float], where: str) -> float:
    total = 0.0
    for value in values:
        total = _checked(total + value, where)
    return total


def _dot(a: Sequence[float], b: Sequence[float], where: str) -> float:
    if len(a) != len(b):
        raise ValueError("internal dot dimension mismatch")
    total = 0.0
    for x, y in zip(a, b):
        product = _checked(x * y, where)
        total = _checked(total + product, where)
    return total


def _linear(x: FloatMatrix, weight: FloatMatrix, bias: tuple[float, ...], where: str) -> FloatMatrix:
    return tuple(tuple(_checked(_dot(row, w, where) + b, where) for w, b in zip(weight, bias)) for row in x)


def _residual(left: FloatMatrix, right: FloatMatrix) -> FloatMatrix:
    return tuple(tuple(_checked(a + b, "residual add") for a, b in zip(x, y)) for x, y in zip(left, right))


def _layernorm(x: FloatMatrix, scale: tuple[float, ...], bias: tuple[float, ...], eps: float) -> FloatMatrix:
    rows = []
    for row in x:
        mean = _checked(_sum(row, "LayerNorm sum") / len(row), "LayerNorm mean")
        centered = tuple(_checked(value - mean, "LayerNorm centering") for value in row)
        squares = tuple(_checked(value * value, "LayerNorm square") for value in centered)
        variance = _checked(_sum(squares, "LayerNorm variance sum") / len(row), "LayerNorm variance")
        denominator = _checked(math.sqrt(_checked(variance + eps, "LayerNorm epsilon")), "LayerNorm sqrt")
        if denominator <= 0:
            raise FiniteTargetError("LayerNorm denominator is not positive")
        normalized = tuple(_checked(value / denominator, "LayerNorm division") for value in centered)
        rows.append(tuple(_checked(_checked(value * gamma, "LayerNorm scale") + beta, "LayerNorm bias")
                          for value, gamma, beta in zip(normalized, scale, bias)))
    return tuple(rows)


def _gelu(x: FloatMatrix, activation: str = "gelu") -> FloatMatrix:
    if activation == "gelu_new":
        coefficient = math.sqrt(2.0 / math.pi)
        rows = []
        for row in x:
            out = []
            for value in row:
                square = _checked(value * value, "GELU square")
                cube = _checked(square * value, "GELU cube")
                correction = _checked(0.044715 * cube, "GELU cubic correction")
                argument = _checked(coefficient * _checked(value + correction, "GELU inner sum"), "GELU tanh argument")
                factor = _checked(1.0 + math.tanh(argument), "GELU tanh factor")
                out.append(_checked(_checked(0.5 * value, "GELU half") * factor, "GELU product"))
            rows.append(tuple(out))
        return tuple(rows)
    if activation != "gelu":
        raise ValueError("unsupported activation")
    sqrt_two = math.sqrt(2.0)
    rows = []
    for row in x:
        out = []
        for value in row:
            arg = _checked(value / sqrt_two, "GELU argument")
            erf = _checked(math.erf(arg), "GELU erf")
            half = _checked(0.5 * value, "GELU half")
            factor = _checked(1.0 + erf, "GELU factor")
            out.append(_checked(half * factor, "GELU product"))
        rows.append(tuple(out))
    return tuple(rows)


def _attention(qkv: FloatMatrix, width: int, heads: int) -> FloatMatrix:
    head_width = width // heads
    divisor = math.sqrt(float(head_width))
    output = []
    for token in range(len(qkv)):
        token_output = []
        for head in range(heads):
            start = head * head_width
            query = qkv[token][start:start + head_width]
            scores = tuple(_checked(_dot(query, qkv[key][width + start:width + start + head_width],
                                         "attention score dot") / divisor, "attention score scale")
                           for key in range(token + 1))
            maximum = max(scores)  # causal mask always includes this token
            terms = tuple(_checked(math.exp(_checked(score - maximum, "softmax shift")), "softmax exp") for score in scores)
            denominator = _sum(terms, "softmax denominator")
            if denominator <= 0:
                raise FiniteTargetError("softmax denominator is not positive")
            probabilities = tuple(_checked(term / denominator, "softmax divide") for term in terms)
            for coordinate in range(head_width):
                values = tuple(qkv[key][2 * width + start + coordinate] for key in range(token + 1))
                token_output.append(_dot(probabilities, values, "attention value mix"))
        output.append(tuple(token_output))
    return tuple(output)


class DeterministicDecoder:
    """Immutable-weight, tokenizer-free full decoder with exact feature export.

    ``blocks`` contains dictionaries with matrices ``qkv``, ``attn_out``,
    ``mlp_up``, ``mlp_down``.  Optional keys are those names plus ``_bias``
    and ``norm1_scale/bias``, ``norm2_scale/bias``.  Norm scales default to
    one and all biases to zero.  Unrecognized keys raise rather than silently
    omitting a pretrained architecture component.  Arrays may be Python
    sequences containing int, finite float, or Fraction; no mutable array
    references survive construction.
    """

    STAGE_NAMES = ("qkv", "attn_out", "mlp_up", "mlp_down")

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("decoder configuration and weights are immutable")
        object.__setattr__(self, name, value)

    def __init__(
        self, config: DecoderConfig, *, token_embeddings: Sequence[Sequence[Any]],
        position_embeddings: Sequence[Sequence[Any]], blocks: Sequence[Mapping[str, Any]],
        lm_head: Sequence[Sequence[Any]], final_norm_scale: Sequence[Any] | None = None,
        final_norm_bias: Sequence[Any] | None = None, lm_head_bias: Sequence[Any] | None = None,
    ) -> None:
        if not isinstance(config, DecoderConfig):
            raise TypeError("config must be DecoderConfig")
        _check_runtime()
        self.config = config
        d, f = config.model_width, config.feedforward_width
        self._token_embeddings = _matrix(token_embeddings, config.vocabulary_size, d, "token_embeddings")
        self._position_embeddings = _matrix(position_embeddings, config.max_sequence_length, d, "position_embeddings")
        if len(blocks) != config.block_count:
            raise ValueError("blocks length must equal block_count")
        sizes = {"qkv": (3 * d, d), "attn_out": (d, d), "mlp_up": (f, d), "mlp_down": (d, f)}
        allowed = set(self.STAGE_NAMES) | {name + "_bias" for name in self.STAGE_NAMES} | {
            "norm1_scale", "norm1_bias", "norm2_scale", "norm2_bias",
        }
        canonical_blocks = []
        weights: dict[str, ExactMatrix] = {}
        biases: dict[str, ExactVector] = {}
        for index, block in enumerate(blocks):
            if set(block) - allowed:
                raise ValueError(f"unsupported block fields: {sorted(set(block) - allowed)}")
            canonical: dict[str, Any] = {}
            for name in self.STAGE_NAMES:
                stage = f"block.{index:04d}.{name}"
                if name not in block:
                    raise ValueError(f"missing {stage}")
                out_dim, in_dim = sizes[name]
                canonical[name] = _matrix(block[name], out_dim, in_dim, stage)
                canonical[name + "_bias"] = _vector(block.get(name + "_bias"), out_dim, stage + ".bias")
                weights[stage] = canonical[name]
                biases[stage] = canonical[name + "_bias"]
            for norm in ("norm1", "norm2"):
                canonical[norm + "_scale"] = _vector(block.get(norm + "_scale"), d, norm + ".scale", 1)
                canonical[norm + "_bias"] = _vector(block.get(norm + "_bias"), d, norm + ".bias")
            canonical_blocks.append(MappingProxyType(canonical))
        self._blocks = tuple(canonical_blocks)
        self._weights = MappingProxyType(weights)
        self._biases = MappingProxyType(biases)
        self.stage_ids = tuple(weights)
        self._stage_positions = MappingProxyType({name: i for i, name in enumerate(self.stage_ids)})
        self._float_weights = MappingProxyType({name: _floats(value) for name, value in weights.items()})
        self._float_biases = MappingProxyType({name: tuple(float(x) for x in value) for name, value in biases.items()})
        self._lm_head = _matrix(lm_head, config.vocabulary_size, d, "lm_head")
        self._lm_head_bias = _vector(lm_head_bias, config.vocabulary_size, "lm_head_bias")
        self._final_norm_scale = _vector(final_norm_scale, d, "final_norm_scale", 1)
        self._final_norm_bias = _vector(final_norm_bias, d, "final_norm_bias")
        parameters = {
            "token_embeddings": self._token_embeddings, "position_embeddings": self._position_embeddings,
            "blocks": self._blocks, "lm_head": self._lm_head, "lm_head_bias": self._lm_head_bias,
            "final_norm_scale": self._final_norm_scale, "final_norm_bias": self._final_norm_bias,
        }
        config_manifest = {
            name: getattr(config, name) for name in (
                "vocabulary_size", "model_width", "head_count", "feedforward_width",
                "block_count", "max_sequence_length",
            )
        }
        config_manifest["layernorm_epsilon_hex"] = config.layernorm_epsilon.hex()
        config_manifest["activation"] = config.activation
        self._manifest = {
            "schema": "calibration-repair-decoder-v1",
            "source_sha256": _file_hash(__file__),
            "runtime": _runtime_manifest(), "config": config_manifest,
            "parameters_sha256": hashlib.sha256(_json_bytes(_serial_exact(parameters))).hexdigest(),
            "stages": list(self.stage_ids),
            "stage_order": "block index, fused qkv, attention output, mlp up, mlp down",
            "dependencies": "all previous stages; conservative",
            "architecture": "learned token+position; pre-LayerNorm causal attention; configured GELU; final LayerNorm; fixed head",
            "feature_target": "V: finite feature bits interpreted as exact dyadics",
            "record_contract": "one intrinsic variable-length token sequence; no padding, batching, dropout, or cache",
            "linear_kernel": "left-to-right binary64 product then addition; bias added last; no FMA",
            "parameter_conversion": "CPython float(Fraction), before finite neural evaluation",
            "softmax": "causal inclusive mask; finite max subtraction, libm exp, sequential sum, divide",
            "gelu": ("(0.5*x)*(1+libm.erf(x/libm.sqrt(2.0)))" if config.activation == "gelu"
                     else "(0.5*x)*(1+libm.tanh(libm.sqrt(2.0/math.pi)*(x+0.044715*((x*x)*x))))"),
            "transport_provider": "structural finite-parameter identity only; otherwise UNKNOWN",
        }
        self.evaluator_id = "decoder-v1:" + hashlib.sha256(_json_bytes(self._manifest)).hexdigest()
        self.reference_id = self.evaluator_id + ":base-weights"
        self._sealed = True

    @property
    def kernel_manifest(self) -> dict[str, Any]:
        """Return a deep copy so callers cannot alter the bound manifest."""
        return json.loads(_json_bytes(self._manifest))

    def stage_weights(self, stage_id: str) -> ExactMatrix:
        return self._weights[stage_id]

    def dependencies(self, stage_id: str) -> tuple[str, ...]:
        return self.stage_ids[:self._stage_positions[stage_id]]

    def _tokens(self, tokens: Sequence[int]) -> tuple[int, ...]:
        values = tuple(tokens)
        if not 1 <= len(values) <= self.config.max_sequence_length:
            raise ValueError("record must contain between one and max_sequence_length tokens")
        if any(type(token) is not int or not 0 <= token < self.config.vocabulary_size for token in values):
            raise ValueError("token IDs must be built-in integers inside the vocabulary; bool is rejected")
        return values

    @staticmethod
    def record_payload(tokens: Sequence[int]) -> bytes:
        """Canonical payload for a service record, with bounds checked on use."""
        values = tuple(tokens)
        if any(type(token) is not int for token in values):
            raise ValueError("token IDs must be built-in integers")
        return _json_bytes(list(values))

    def decode_payload(self, payload: bytes) -> tuple[int, ...]:
        if type(payload) is not bytes:
            raise TypeError("record payload must be bytes")
        try:
            data = json.loads(payload)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("record payload must be a UTF-8 JSON token array") from exc
        if type(data) is not list:
            raise ValueError("record payload must be a JSON token array")
        return self._tokens(data)

    def _prefix(self, prefix: Prefix | None) -> dict[str, FloatMatrix]:
        if prefix is None:
            return {}
        unknown = set(prefix) - set(self.stage_ids)
        if unknown:
            raise ValueError(f"unknown installed stages: {sorted(unknown)}")
        result = {}
        for stage, values in prefix.items():
            # Installed codes are exact; accepting floats here can hide a
            # caller's premature conversion of the quantizer output.
            if any(type(x) is not int and not isinstance(x, Fraction) for row in values for x in row):
                raise TypeError("installed codes must be int or Fraction")
            base = self._weights[stage]
            result[stage] = _floats(_matrix(values, len(base), len(base[0]), "installed " + stage))
        return result

    def prefix_preserves_stage_inputs(self, stage_id: str, prefix: Prefix | None) -> bool:
        """Exact structural zero-drift proof relative to the base reference.

        Equality compares finite entries, including signed-zero bits.  Missing
        overrides use base weights.  Future/current stage overrides cannot
        affect the requested inputs and are ignored after validation.
        """
        _check_runtime()
        installed = self._prefix(prefix)
        for ancestor in self.dependencies(stage_id):
            if ancestor in installed:
                candidate = installed[ancestor]
                base = self._float_weights[ancestor]
                if any(struct.pack("!d", x) != struct.pack("!d", y)
                       for left, right in zip(candidate, base) for x, y in zip(left, right)):
                    return False
        return True

    def _evaluate(self, tokens: tuple[int, ...], installed: dict[str, FloatMatrix],
                  stop: str | None) -> FloatMatrix:
        config = self.config
        hidden = tuple(tuple(_checked(float(a) + float(b), "embedding addition")
                             for a, b in zip(self._token_embeddings[token], self._position_embeddings[position]))
                       for position, token in enumerate(tokens))
        for index, block in enumerate(self._blocks):
            pre = f"block.{index:04d}."
            norm1 = _layernorm(hidden, tuple(float(x) for x in block["norm1_scale"]),
                               tuple(float(x) for x in block["norm1_bias"]), config.layernorm_epsilon)
            stage = pre + "qkv"
            if stop == stage:
                return norm1
            qkv = _linear(norm1, installed.get(stage, self._float_weights[stage]), self._float_biases[stage], stage)
            mixed = _attention(qkv, config.model_width, config.head_count)
            stage = pre + "attn_out"
            if stop == stage:
                return mixed
            attended = _linear(mixed, installed.get(stage, self._float_weights[stage]), self._float_biases[stage], stage)
            hidden = _residual(hidden, attended)
            norm2 = _layernorm(hidden, tuple(float(x) for x in block["norm2_scale"]),
                               tuple(float(x) for x in block["norm2_bias"]), config.layernorm_epsilon)
            stage = pre + "mlp_up"
            if stop == stage:
                return norm2
            up = _linear(norm2, installed.get(stage, self._float_weights[stage]), self._float_biases[stage], stage)
            activated = _gelu(up, config.activation)
            stage = pre + "mlp_down"
            if stop == stage:
                return activated
            down = _linear(activated, installed.get(stage, self._float_weights[stage]), self._float_biases[stage], stage)
            hidden = _residual(hidden, down)
        normalized = _layernorm(hidden, tuple(float(x) for x in self._final_norm_scale),
                                tuple(float(x) for x in self._final_norm_bias), config.layernorm_epsilon)
        return _linear(normalized, _floats(self._lm_head), tuple(float(x) for x in self._lm_head_bias), "lm_head")

    def stage_features(self, stage_id: str, tokens: Sequence[int], prefix: Prefix | None = None) -> ExactMatrix:
        """Return exact dyadic d-by-token input activations for one stage."""
        _check_runtime()
        if stage_id not in self._weights:
            raise KeyError(stage_id)
        rows = self._evaluate(self._tokens(tokens), self._prefix(prefix), stage_id)
        return tuple(tuple(Fraction.from_float(row[coordinate]) for row in rows) for coordinate in range(len(rows[0])))

    def logits(self, tokens: Sequence[int], prefix: Prefix | None = None) -> FloatMatrix:
        """Run the complete installed decoder; result is token-by-vocabulary."""
        _check_runtime()
        return self._evaluate(self._tokens(tokens), self._prefix(prefix), None)

    def exact_logits(self, tokens: Sequence[int], prefix: Prefix | None = None) -> ExactMatrix:
        return tuple(tuple(Fraction.from_float(value) for value in row) for row in self.logits(tokens, prefix))

    def greedy_generate(self, tokens: Sequence[int], max_new_tokens: int,
                        prefix: Prefix | None = None) -> tuple[int, ...]:
        """Deterministic generation; lower token ID breaks a logit tie.

        Recomputes the whole prefix each step; no cache or performance claim.
        The returned prompt plus continuation must fit the position table.
        """
        output = self._tokens(tokens)
        if type(max_new_tokens) is not int or max_new_tokens < 0:
            raise ValueError("max_new_tokens must be a nonnegative built-in integer")
        if len(output) + max_new_tokens > self.config.max_sequence_length:
            raise ValueError("generated sequence would exceed the position table")
        for _ in range(max_new_tokens):
            last = self.logits(output, prefix)[-1]
            next_token = max(range(len(last)), key=lambda token: (last[token], -token))
            output += (next_token,)
        return output

    def make_repair_service(
        self, grids_by_stage: Mapping[str, Sequence[Sequence[int | Fraction]]], *,
        ridge: int | Fraction = 1, normalization: int | Fraction = 1,
        group_count: int = 8, structural_provider: bool = True,
    ) -> Any:
        """Bind this decoder to the canonical exact sequential service.

        The returned service's ``job`` contains the complete quantizer/grid
        contract.  Record payloads are JSON token arrays created by
        ``record_payload``.  Its independent reference always evaluates the
        supplied base model, never an old corpus-calibrated model.  The optional
        provider proves only exact identity of all finite ancestor matrices;
        changed ancestor matrices return UNKNOWN and retained records replay.
        No arbitrary scalar error bound is accepted through this adapter.

        Full-model verification consists of comparing the resulting canonical
        state with ``service.fresh(retained_records)`` and evaluating logits
        with ``{out.stage_id: out.codes for out in state.model}``.
        """
        try:
            from .repair_service import (
                AbsoluteGramBound, JobSpec, ReferenceSample, RepairService,
                StageSpec, TrustedBoundProvider, UnknownBound,
            )
        except ImportError:
            from repair_service import (
                AbsoluteGramBound, JobSpec, ReferenceSample, RepairService,
                StageSpec, TrustedBoundProvider, UnknownBound,
            )
        if set(grids_by_stage) != set(self.stage_ids):
            raise ValueError("grids_by_stage must name every decoder stage exactly")
        if type(structural_provider) is not bool:
            raise TypeError("structural_provider must be bool")
        stages = tuple(StageSpec(
            stage, self.dependencies(stage), self.stage_weights(stage),
            tuple(tuple(grid) for grid in grids_by_stage[stage]), ridge, normalization,
        ) for stage in self.stage_ids)
        job = JobSpec(stages, self.evaluator_id, self.reference_id, group_count)
        stage_lookup = {stage.stage_id: stage for stage in stages}
        manifest_digest = job.manifest_digest

        def evaluator(record: Any, stage: Any, prefix: Any) -> ExactMatrix:
            if prefix.manifest_digest != manifest_digest or stage_lookup.get(stage.stage_id) != stage:
                raise ValueError("decoder evaluation received a foreign target contract")
            if set(prefix.as_mapping()) != set(self.dependencies(stage.stage_id)):
                raise ValueError("decoder evaluation requires the complete declared ancestor prefix")
            return self.stage_features(stage.stage_id, self.decode_payload(record.payload), prefix.as_mapping())

        def reference(record: Any, stage: Any) -> Any:
            if stage_lookup.get(stage.stage_id) != stage:
                raise ValueError("decoder reference received a foreign stage contract")
            return ReferenceSample(self.stage_features(stage.stage_id, self.decode_payload(record.payload)))

        provider_id = self.evaluator_id + ":structural-identity-v1"

        def prove(context: Any) -> Any:
            if (context.binding.manifest_digest != manifest_digest
                    or context.binding.reference_id != self.reference_id
                    or context.prefix.manifest_digest != manifest_digest
                    or stage_lookup.get(context.stage.stage_id) != context.stage
                    or context.binding.stage_id != context.stage.stage_id
                    or context.binding.prefix_digest != context.prefix.digest):
                return UnknownBound("foreign decoder/provider contract")
            prefix = context.prefix.as_mapping()
            if set(prefix) != set(self.dependencies(context.stage.stage_id)):
                return UnknownBound("incomplete decoder ancestor prefix")
            if self.prefix_preserves_stage_inputs(context.stage.stage_id, prefix):
                return AbsoluteGramBound(
                    context.binding, provider_id, Fraction(0),
                    "same pinned finite program and bit-identical installed ancestor matrices as the independent base reference",
                )
            return UnknownBound("changed finite ancestors: no analytic libm transport certificate implemented")

        provider = TrustedBoundProvider(provider_id, prove) if structural_provider else None
        return RepairService(job, evaluator, reference, provider)


__all__ = ["DecoderConfig", "DeterministicDecoder", "FiniteTargetError"]
