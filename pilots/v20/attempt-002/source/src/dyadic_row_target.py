"""Distinct model-code target with fixed fine dyadic grids per output row."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .dyadic_row_quantizer import dyadic_row_scales
from .ordered_finite import FiniteWeights
from .target_manifest import build_target


@dataclass(frozen=True)
class DyadicRowStage:
    stage_id: str
    dependencies: tuple
    weights: object
    ridge: object
    normalization: object
    scale_values: tuple
    bits: int

    @property
    def width(self):
        return len(self.weights[0])


@dataclass(frozen=True)
class DyadicRowTarget:
    recipe: object
    stages: tuple
    payload_bytes: bytes

    def payload(self):
        return json.loads(self.payload_bytes)

    @property
    def digest(self):
        return hashlib.sha256(self.payload_bytes).hexdigest()


def build_dyadic_row_target(decoder, recipe, *, weight_digest_encoding="binary64_matrix_v1"):
    base = build_target(decoder, recipe, weight_digest_encoding=weight_digest_encoding)
    row_grid_count = sum(len(stage.weights) for stage in base.stages) * (1 << recipe.bits)
    if row_grid_count > recipe.max_grid_entries:
        raise ValueError(f"output-row grid budget exceeded: {row_grid_count} entries > {recipe.max_grid_entries}")
    payload = base.payload()
    root = Path(__file__).parent
    payload.update(
        schema="fixed-v-cert-dyadic-row-grid-diagnostic-target-v1",
        numerical_contract="correctly-rounded finite sequential features; exact rational metric; fixed base-only output-row dyadic24 grids; lower ties",
        grid_recipe="output-row-extrema-smallest-dyadic24-cover-with-exact-midpoints-v1",
        output_rule="complete stage codes only; no canonical repair-state contract declared",
        deleted_source_rule="retained-record code target; no deletion-service access contract declared",
        failure_rule="bounded exact fallback for unresolved cells; exhausted budget or finite evaluator failure aborts",
        significant_bits=24,
        minimum_row_scale_hex=float.fromhex("0x0.0000000000002p-1022").hex(),
        zero_row_scale_rule="minimum admissible positive scale; exact half-step midpoint required",
        dyadic_constructor_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        dyadic_solver_source_sha256=hashlib.sha256((root / "dyadic_row_quantizer.py").read_bytes()).hexdigest(),
        batched_solver_source_sha256=hashlib.sha256((root / "batched_token_solver.py").read_bytes()).hexdigest(),
        token_solver_source_sha256=hashlib.sha256((root / "low_rank_certified.py").read_bytes()).hexdigest())
    payload.pop("zero_column_scale_exponent", None)
    stages = []
    for stage, entry in zip(base.stages, payload["stages"]):
        scales = dyadic_row_scales(FiniteWeights(stage.weights).array(), bits=recipe.bits, significant_bits=24)
        stages.append(DyadicRowStage(stage.stage_id, stage.dependencies, stage.weights, stage.ridge,
                                     stage.normalization, scales, recipe.bits))
        entry.pop("grids_sha256", None)
        entry.pop("scale_exponents", None)
        entry.update(grid_axis="output_row", row_scale_hex=[value.hex() for value in scales], significant_bits=24)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    return DyadicRowTarget(recipe, tuple(stages), raw)
