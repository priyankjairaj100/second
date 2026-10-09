"""Explicit V38 decoder construction with a new live runtime identity.

This module reuses frozen arithmetic helpers. It does not replace their globals.
The V38 evaluator requires new preparation. Historical identities remain distinct.
"""
from __future__ import annotations

from contextlib import contextmanager
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np

from src import transformer_backend as tb
from src import certified_intervals as ci
from src import certified_transformer as ct
from src import finite_primitives as fp
from src import ordered_finite_decoder_v30 as ordered
from src.compact_exact import CompactDyadicMatrix, exact_json_sha256
from src.certified_transformer import CertifiedDecoder, _Finite, _StageWeights
from src.ordered_finite import FiniteWeights
from src.transformer_backend import (
    DecoderConfig, DeterministicDecoder, ExactMatrix, ExactVector,
    _check_runtime, _matrix, _vector, _floats, _file_hash, _json_bytes,
)
from .live_runtime import collect_runtime, assert_runtime_unchanged


class PortableDeterministicDecoder(DeterministicDecoder):
    """Retain parameter validation and arithmetic with an explicit new manifest."""

    def __init__(
        self, config: DecoderConfig, *, token_embeddings: Sequence[Sequence[Any]],
        position_embeddings: Sequence[Sequence[Any]], blocks: Sequence[Mapping[str, Any]],
        lm_head: Sequence[Sequence[Any]], final_norm_scale: Sequence[Any] | None = None,
        final_norm_bias: Sequence[Any] | None = None, lm_head_bias: Sequence[Any] | None = None,
        identity_encoding: str = "exact_json",
    ) -> None:
        if not isinstance(config, DecoderConfig):
            raise TypeError("config must be DecoderConfig")
        _check_runtime()
        if identity_encoding not in ("exact_json", "binary64_tree_v2"):
            raise ValueError("unsupported parameter identity encoding")
        runtime = collect_runtime(domain="transformer")
        self._runtime_binding = _json_bytes(runtime)
        self.identity_encoding = identity_encoding
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
        if identity_encoding == "binary64_tree_v2":
            from src.parameter_identity import binary64_parameter_sha256
            parameter_digest = binary64_parameter_sha256(parameters)
        else:
            parameter_digest = exact_json_sha256(parameters)
        self._manifest = {
            "schema": "calibration-repair-portable-decoder-v38",
            "legacy_numeric_source_sha256": _file_hash(tb.__file__),
            "identity_compatibility": "new evaluator; fresh preparation required",
            "source_sha256": _file_hash(__file__),
            "compact_storage_source_sha256": _file_hash(str(Path(tb.__file__).with_name("compact_exact.py"))),
            "runtime": runtime, "config": config_manifest,
            "parameters_sha256": parameter_digest,
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
        if identity_encoding == "binary64_tree_v2":
            self._manifest.update({
                "parameters_identity_encoding": identity_encoding,
                "parameter_identity_source_sha256": _file_hash(str(Path(tb.__file__).with_name("parameter_identity.py"))),
                "binary64_identity_source_sha256": _file_hash(str(Path(tb.__file__).with_name("binary64_identity.py"))),
            })
        self.evaluator_id = "portable-decoder-v38:" + hashlib.sha256(_json_bytes(self._manifest)).hexdigest()
        self.reference_id = self.evaluator_id + ":base-weights"
        assert_runtime_unchanged(runtime)
        self._sealed = True

    def assert_runtime_current(self):
        _check_runtime()
        assert_runtime_unchanged(json.loads(self._runtime_binding))

    def _evaluate(self, tokens, installed, stop):
        self.assert_runtime_current()
        result = super()._evaluate(tokens, installed, stop)
        self.assert_runtime_current()
        return result

    def prefix_preserves_stage_inputs(self, stage_id, prefix):
        self.assert_runtime_current()
        result = super().prefix_preserves_stage_inputs(stage_id, prefix)
        self.assert_runtime_current()
        return result


def portable_primitive_manifest(backend):
    """Bind unchanged primitive arithmetic to new live evidence."""
    if backend not in ("rational", "mpfr_enclosure"):
        raise ValueError("unsupported primitive backend")
    result = {
        "schema": "portable-finite-primitives-v38",
        "backend": backend,
        "construction_source_sha256": _file_hash(__file__),
        "numeric_source_sha256": _file_hash(fp.__file__),
        "interval_source_sha256": _file_hash(ci.__file__),
        "rounding": "directed real enclosure; identical RN-even binary64 endpoint encodings",
        "completion_domain_equivalence_claimed": False,
    }
    if backend == "mpfr_enclosure":
        import gmpy2 as g
        result.update(
            gmpy2=g.version(), mpfr=g.mpfr_version(), gmp=g.mp_version(),
            runtime=collect_runtime(domain="mpfr"),
            mpfr_context={
                "precision": "max(64, interval_bits+8)",
                "emin": -16384, "emax": 16384,
                "subnormalize": False, "traps": False,
                "rounds": ["toward_negative_infinity", "toward_positive_infinity"],
            },
        )
    return result


def _implementation_payload():
    root = Path(tb.__file__).parent
    names = (
        "transformer_backend.py", "certified_transformer.py", "certified_intervals.py",
        "finite_primitives.py", "ordered_finite.py", "ordered_finite_decoder_v30.py",
        "ordered_attention_v30.py", "compact_exact.py", "parameter_identity.py",
        "binary64_identity.py",
    )
    return {
        "schema": "portable-ordered-finite-implementation-v38",
        "construction_source_sha256": _file_hash(__file__),
        "reused_source_sha256": {name: _file_hash(str(root / name)) for name in names},
        "numpy_version": np.__version__,
        "arithmetic": "frozen V30 scalar operation order; independent NumPy operations; no BLAS reductions",
        "runtime_checks": "live evidence before and after each public evaluation or generator advancement",
        "global_mutation": False,
        "historical_identity_compatibility": False,
        "same_resource_or_refusal_behavior_claimed": False,
    }


class PortableOrderedDecoder(CertifiedDecoder):
    """Use the frozen ordered evaluator under a distinct V38 target identity."""

    def __init__(self, base, *, primitive_backend="mpfr_enclosure"):
        if type(base) is not PortableDeterministicDecoder:
            raise TypeError("base must be PortableDeterministicDecoder")
        primitive = portable_primitive_manifest(primitive_backend)
        base.assert_runtime_current()
        self.base = base
        self.config = base.config
        self.stage_ids = base.stage_ids
        self.primitive_backend = primitive_backend
        self._primitive_binding = _json_bytes(primitive)
        implementation = _implementation_payload()
        self._implementation_bytes = _json_bytes(implementation)
        self._manifest = {
            "schema": "portable-certified-ordered-decoder-v38",
            "base_parameters": base.kernel_manifest,
            "primitive_backend": primitive,
            "implementation": implementation,
            "linear_schedule": "binary64 coordinate-order multiply then add; independent outputs batched; no BLAS",
            "nonlinear": "proved correctly rounded exp/sqrt/erf/tanh; unresolved rounding aborts",
            "softmax": "causal inclusive; finite max shift; exp; sequential sum; divide",
            "gelu_new_coefficient_hex": "0x1.9884533d43651p-1",
            "target": "V38 certified finite features; fresh preparation required",
            "historical_identity_compatibility": False,
            "same_resource_or_refusal_behavior_claimed": False,
        }
        self.evaluator_id = "portable-certified-decoder-v38:" + hashlib.sha256(_json_bytes(self._manifest)).hexdigest()
        self.reference_id = self.evaluator_id + ":base"
        self.assert_runtime_current()
        self._sealed = True

    @property
    def implementation_manifest(self):
        return json.loads(self._implementation_bytes)

    def assert_runtime_current(self):
        self.base.assert_runtime_current()
        primitive = json.loads(self._primitive_binding)
        if "runtime" in primitive:
            assert_runtime_unchanged(primitive["runtime"])

    @contextmanager
    def _evaluation_scope(self):
        self.assert_runtime_current()
        with fp.primitive_scope(self.primitive_backend):
            yield
        self.assert_runtime_current()

    def _eval(self, tokens, prefix, stop):
        with self._evaluation_scope():
            installed = self.base._prefix(prefix)
            weights = _StageWeights(self.stage_ids, lambda stage: FiniteWeights(
                installed.get(stage, self.base._float_weights[stage])))
            result = ordered._execute_ordered(
                self.base, self.base._tokens(tokens), weights,
                lambda value: _Finite(float(value)), stop)
        return result

    def sequential_features(self, tokens):
        return portable_sequential_features(self, tokens)

    def prepare_prefix(self, prefix=None):
        return PortableFinitePrefix(self, prefix)

    def make_repair_service(self, *args, **kwargs):
        raise NotImplementedError(
            "V38 requires explicit service construction; the legacy jet provider is not supported")


def portable_sequential_features(decoder, tokens):
    """Check each advancement and restore primitive scope before each yield."""
    if type(decoder) is not PortableOrderedDecoder:
        raise TypeError("portable traversal requires PortableOrderedDecoder")
    iterator = ordered._ordered_sequence(decoder, tokens)
    try:
        with decoder._evaluation_scope():
            current = next(iterator)
        while True:
            installed = yield current
            with decoder._evaluation_scope():
                try:
                    current = iterator.send(installed)
                except StopIteration:
                    return
    finally:
        iterator.close()


class PortableFinitePrefix:
    """Hold an immutable prefix with V38 runtime checks."""

    def __setattr__(self, name, value):
        if getattr(self, "_sealed", False):
            raise AttributeError("portable prefix is immutable")
        object.__setattr__(self, name, value)

    def __init__(self, decoder, prefix=None):
        if type(decoder) is not PortableOrderedDecoder:
            raise TypeError("portable prefix requires PortableOrderedDecoder")
        decoder.assert_runtime_current()
        self.decoder = decoder
        if prefix is None:
            installed = {}
        else:
            if set(prefix) - set(decoder.stage_ids):
                raise ValueError("unknown installed stages")
            compact = {stage: value for stage, value in prefix.items()
                       if type(value) is CompactDyadicMatrix}
            installed = decoder.base._prefix({stage: value for stage, value in prefix.items()
                                              if type(value) is not CompactDyadicMatrix})
            for stage, value in compact.items():
                base = decoder.base._weights[stage]
                if value.shape != (len(base), len(base[0])):
                    raise ValueError("installed compact matrix has an incorrect shape")
                installed[stage] = value.floats()
        self.installed = MappingProxyType(installed)
        decoder.assert_runtime_current()
        self._sealed = True

    def logits(self, tokens):
        decoder = self.decoder
        with decoder._evaluation_scope():
            weights = _StageWeights(decoder.stage_ids, lambda stage: FiniteWeights(
                self.installed.get(stage, decoder.base._float_weights[stage])))
            rows = ordered._execute_ordered(
                decoder.base, decoder.base._tokens(tokens), weights,
                lambda value: _Finite(float(value)), None)
            result = tuple(tuple(value.value for value in row) for row in rows)
        return result

