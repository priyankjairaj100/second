"""Fixed V_cert targets from finite base parameters and explicit recipes.

This constructor reads no calibration records. It fixes grids before calibration.
It defines a project target. It does not reproduce a vendor quantizer.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .certified_transformer import CertifiedDecoder
from .repair_service import JobSpec, StageSpec

Q = Fraction
NUMERICAL_CONTRACT = (
    "V_cert:certified-scalar-binary64-features/exact-rational-Gram/"
    "fixed-original-token-normalization/fixed-positive-ridge/"
    "reverse-LDL/fixed-coordinate-order/fixed-power2-signed-grids/lower-ties/v1"
)


def _json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def _hash(value) -> str:
    return hashlib.sha256(_json(value)).hexdigest()


def _rational(value, name: str) -> Q:
    if type(value) is not int and not isinstance(value, Q):
        raise TypeError(f"{name} must be an exact rational")
    return Q(value)


def _positive_integer(value, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive built-in integer")
    return value


def _pair(value: Q) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value, name: str) -> Q:
    if not isinstance(value, list) or len(value) != 2 or any(type(x) is not int for x in value):
        raise TypeError(f"{name} must be an integer pair")
    if value[1] <= 0:
        raise ValueError(f"{name} denominator must be positive")
    q = Q(*value)
    if _pair(q) != value:
        raise ValueError(f"{name} must use a reduced rational pair")
    return q


def _power_two(exponent: int) -> Q:
    return Q(1 << exponent) if exponent >= 0 else Q(1, 1 << -exponent)


def _ceil_log_two(value: Q) -> int:
    if value <= 0:
        raise ValueError("logarithm argument must be positive")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if _power_two(exponent) < value:
        exponent += 1
    return exponent


@dataclass(frozen=True)
class TargetRecipe:
    """The original token count stays fixed after every deletion."""
    original_token_count: int
    bits: int = 4
    ridge: Q = Q(1, 100)
    group_count: int = 8
    max_grid_entries: int = 1_000_000

    def __post_init__(self):
        _positive_integer(self.original_token_count, "original_token_count")
        if type(self.bits) is not int or not 2 <= self.bits <= 8:
            raise ValueError("bits must be a built-in integer between 2 and 8")
        ridge = _rational(self.ridge, "ridge")
        if ridge <= 0:
            raise ValueError("ridge must be strictly positive")
        object.__setattr__(self, "ridge", ridge)
        _positive_integer(self.group_count, "group_count")
        _positive_integer(self.max_grid_entries, "max_grid_entries")

    def payload(self) -> dict:
        return {"schema": "fixed-target-recipe-v1", "original_token_count": self.original_token_count,
                "bits": self.bits, "ridge": _pair(self.ridge), "group_count": self.group_count,
                "max_grid_entries": self.max_grid_entries}

    @classmethod
    def from_payload(cls, data: Mapping) -> "TargetRecipe":
        keys = {"schema", "original_token_count", "bits", "ridge", "group_count", "max_grid_entries"}
        if not isinstance(data, Mapping) or set(data) != keys or data["schema"] != "fixed-target-recipe-v1":
            raise ValueError("unsupported or incomplete target recipe")
        return cls(data["original_token_count"], data["bits"], _read_pair(data["ridge"], "ridge"),
                   data["group_count"], data["max_grid_entries"])


@dataclass(frozen=True)
class TargetManifest:
    recipe: TargetRecipe
    evaluator_id: str
    stages: tuple[StageSpec, ...]
    scale_exponents: tuple[tuple[int, ...], ...]
    constructor_source_sha256: str
    exact_core_source_sha256: str
    service_sources_sha256: tuple[tuple[str, str], ...]

    def __post_init__(self):
        if not isinstance(self.recipe, TargetRecipe):
            raise TypeError("recipe must be TargetRecipe")
        stages = tuple(self.stages)
        exponents = tuple(tuple(row) for row in self.scale_exponents)
        if not stages or any(not isinstance(stage, StageSpec) for stage in stages):
            raise TypeError("stages must contain StageSpec values")
        if len(stages) != len(exponents):
            raise ValueError("each target stage needs a scale row")
        if any(len(row) != stage.width or any(type(e) is not int for e in row)
               for stage, row in zip(stages, exponents)):
            raise ValueError("each input coordinate needs an integer scale exponent")
        if len({stage.stage_id for stage in stages}) != len(stages):
            raise ValueError("target stage IDs must be unique")
        sources = tuple(tuple(pair) for pair in self.service_sources_sha256)
        if any(len(pair) != 2 for pair in sources) or len({pair[0] for pair in sources}) != len(sources):
            raise ValueError("service source names must be unique pairs")
        object.__setattr__(self, "stages", stages)
        object.__setattr__(self, "scale_exponents", exponents)
        object.__setattr__(self, "service_sources_sha256", sources)

    @property
    def grids_by_stage(self):
        return MappingProxyType({stage.stage_id: stage.grids for stage in self.stages})

    def payload(self) -> dict:
        half = 1 << (self.recipe.bits - 1)
        stages = []
        for stage, exponents in zip(self.stages, self.scale_exponents):
            weights = [[_pair(x) for x in row] for row in stage.weights]
            stages.append({"stage_id": stage.stage_id, "dependencies": list(stage.dependencies),
                           "shape": [len(stage.weights), stage.width], "weights_sha256": _hash(weights),
                           "grids_sha256": _hash([[_pair(x) for x in grid] for grid in stage.grids]),
                           "ridge": _pair(stage.ridge), "normalization": _pair(stage.normalization),
                           "scale_exponents": list(exponents)})
        return {"schema": "fixed-v-cert-target-v1", "recipe": self.recipe.payload(),
                "evaluator_id": self.evaluator_id, "numerical_contract": NUMERICAL_CONTRACT,
                "constructor_source_sha256": self.constructor_source_sha256,
                "exact_core_source_sha256": self.exact_core_source_sha256,
                "service_sources_sha256": dict(self.service_sources_sha256),
                "stages": stages, "grid_recipe": "column-extrema-smallest-power2-cover-v1",
                "code_min": -half, "code_max": half - 1, "code_count": 1 << self.recipe.bits,
                "zero_column_scale_exponent": 0,
                "base_parameter_rule": "quantized base entries must equal their binary64 conversions",
                "coordinate_order": "input coordinate ascending; output row ascending; declared stage order",
                "token_program": "nonempty token IDs; positions reset per record; inclusive causal mask; no padding",
                "attention_scope": "record local; no cross-record state",
                "normalization_rule": "original calibration token total; fixed for every retained subset",
                "fixed_components": "embeddings, positions, norms, biases, and final language-model head",
                "scale_fitting": "base weights only; no calibration fitting or retained-data refit",
                "deleted_source_rule": "deleted record payload must be supplied for verified exact subtraction",
                "output_rule": "complete quantized stage matrices and canonical aggregate state",
                "failure_rule": "proof rejection replays; finite evaluator failure aborts without commit"}

    def canonical_bytes(self) -> bytes:
        return _json(self.payload())

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def make_job(self, reference_id: str) -> JobSpec:
        return JobSpec(self.stages, self.evaluator_id, reference_id, self.recipe.group_count,
                       NUMERICAL_CONTRACT + ";target_sha256=" + self.digest)


def build_target(decoder: CertifiedDecoder, recipe: TargetRecipe) -> TargetManifest:
    """Build exactly 2**bits codes per input coordinate, without corpus access."""
    if not isinstance(decoder, CertifiedDecoder) or not isinstance(recipe, TargetRecipe):
        raise TypeError("build_target requires CertifiedDecoder and TargetRecipe")
    from . import exact_core
    count = sum(len(decoder.stage_weights(s)[0]) for s in decoder.stage_ids) * (1 << recipe.bits)
    if count > recipe.max_grid_entries:
        raise ValueError(f"grid budget exceeded: {count} entries > {recipe.max_grid_entries}")
    half = 1 << (recipe.bits - 1)
    stages, all_exponents = [], []
    for stage_id in decoder.stage_ids:
        weights = decoder.stage_weights(stage_id)
        for row in weights:
            if any(Q.from_float(float(x)) != x for x in row):
                raise ValueError("quantized base weights must be exactly representable in binary64")
        grids, exponents = [], []
        for column in zip(*weights):
            needed = max(max(column) / (half - 1), -min(column) / half, Q(0))
            exponent = _ceil_log_two(needed) if needed else 0
            # Smaller scales would collapse distinct codes during finite installation.
            exponent = max(exponent, -1074)
            scale = _power_two(exponent)
            grid = tuple(code * scale for code in range(-half, half))
            for value in grid:
                try:
                    converted = float(value)
                except OverflowError as exc:
                    raise ValueError("grid code exceeds the binary64 domain") from exc
                if not math.isfinite(converted) or Q.from_float(converted) != value:
                    raise ValueError("grid codes must be finite and exactly representable in binary64")
            if min(column) < grid[0] or max(column) > grid[-1]:
                raise AssertionError("grid construction failed to cover base weights")
            grids.append(grid)
            exponents.append(exponent)
        stages.append(StageSpec(stage_id, decoder.dependencies(stage_id), weights, tuple(grids),
                                recipe.ridge, Q(recipe.original_token_count)))
        all_exponents.append(tuple(exponents))
    source_names = ("aggregate_response_service.py", "repair_service.py", "linear_response.py",
                    "response_moments.py", "response_certificate.py", "response_service_adapter.py")
    sources = tuple((name, hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest())
                    for name in source_names)
    return TargetManifest(recipe, decoder.evaluator_id, tuple(stages), tuple(all_exponents),
                          hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                          hashlib.sha256(Path(exact_core.__file__).read_bytes()).hexdigest(), sources)
