"""Deterministic charts built only from base weights, fixed grids, and recipes.

The small chart spans one rounding drift per ancestor stage. It does not span
generic sequential quantization changes. The coordinate chart spans every grid
prefix, but its dense implementation can exceed the declared resource limits.
Preview counts are symbolic slot counts. They are not byte or latency estimates.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Mapping

from .certified_transformer import AffineChart, AutomaticResponseProvider, CertifiedDecoder
from .box_response_provider import ParameterBox, BoxResponseProvider, grid_box
from .target_manifest import TargetManifest, build_target, _json, _pair, _positive_integer, _rational, _read_pair

Q = Fraction


class ChartBudgetError(ValueError):
    """The declared recipe exceeds a resource limit before dense construction."""


@dataclass(frozen=True)
class ChartRecipe:
    mode: str = "stage-rtn"
    radius: Q = Q(1)
    precision_bits: int = 96
    max_rank: int = 64
    max_direction_entries: int = 1_000_000
    max_aggregate_rationals: int = 5_000_000

    def __post_init__(self):
        if self.mode not in ("stage-rtn", "coordinate", "none", "grid-box"):
            raise ValueError("unsupported chart mode")
        radius = _rational(self.radius, "radius")
        if radius < 1:
            raise ValueError("radius must be at least one")
        if self.mode == "grid-box" and radius != 1:
            raise ValueError("grid-box uses its complete fixed grid domain; radius must equal one")
        object.__setattr__(self, "radius", radius)
        if type(self.precision_bits) is not int or not 64 <= self.precision_bits <= 16384:
            raise ValueError("precision_bits must be an integer from 64 through 16384")
        _positive_integer(self.max_rank, "max_rank")
        _positive_integer(self.max_direction_entries, "max_direction_entries")
        _positive_integer(self.max_aggregate_rationals, "max_aggregate_rationals")

    def payload(self) -> dict:
        return {"schema": "base-only-chart-recipe-v1", "mode": self.mode,
                "radius": _pair(self.radius), "precision_bits": self.precision_bits,
                "max_rank": self.max_rank, "max_direction_entries": self.max_direction_entries,
                "max_aggregate_rationals": self.max_aggregate_rationals}

    @classmethod
    def from_payload(cls, data: Mapping) -> "ChartRecipe":
        keys = {"schema", "mode", "radius", "precision_bits", "max_rank", "max_direction_entries", "max_aggregate_rationals"}
        if not isinstance(data, Mapping) or set(data) != keys or data["schema"] != "base-only-chart-recipe-v1":
            raise ValueError("unsupported or incomplete chart recipe")
        return cls(data["mode"], _read_pair(data["radius"], "radius"), data["precision_bits"],
                   data["max_rank"], data["max_direction_entries"], data["max_aggregate_rationals"])


def _nearest(value: Q, grid: tuple[Q, ...]) -> Q:
    # The second key implements lower ties exactly.
    return min(grid, key=lambda code: (abs(code - value), code))


def _used_stages(target: TargetManifest):
    used = {dependency for stage in target.stages for dependency in stage.dependencies}
    return tuple(stage for stage in target.stages if stage.stage_id in used)


def _validate_target(decoder, target):
    if not isinstance(decoder, CertifiedDecoder) or not isinstance(target, TargetManifest):
        raise TypeError("a certified decoder and generated target are required")
    # Reconstruct the recipe instead of trusting a hand-written provenance label.
    if build_target(decoder, target.recipe).canonical_bytes() != target.canonical_bytes():
        raise ValueError("target does not match this decoder, recipe, or source version")


@dataclass(frozen=True)
class ChartPreview:
    mode: str
    rank: int
    direction_entries: int
    aggregate_rationals_per_group: int
    aggregate_rationals_all_groups: int
    jet_scalar_components_per_value: int
    quantized_parameters: int
    nominal_packed_code_bytes: int
    grid_entries: int
    over_budget: tuple[str, ...]

    @property
    def feasible(self) -> bool:
        return not self.over_budget

    def payload(self):
        return {"schema": "chart-resource-preview-v1", "mode": self.mode, "rank": self.rank,
                "direction_entries": self.direction_entries,
                "domain_storage_kind": "box_endpoint_rationals" if self.mode == "grid-box" else "direction_rationals",
                "aggregate_rationals_per_group": self.aggregate_rationals_per_group,
                "aggregate_rationals_all_groups": self.aggregate_rationals_all_groups,
                "jet_scalar_components_per_value": self.jet_scalar_components_per_value,
                "quantized_parameters": self.quantized_parameters,
                "nominal_packed_code_bytes": self.nominal_packed_code_bytes, "grid_entries": self.grid_entries,
                "over_budget": list(self.over_budget), "feasible": self.feasible,
                "cost_limits": "counts exclude bit lengths, Python objects, metadata, temporary tensors, and execution time",
                "code_size_limits": "packed code bytes exclude scales, fixed weights, metadata, and aggregate state; no packed writer is implemented"}


def preview_chart(decoder: CertifiedDecoder, target: TargetManifest, recipe: ChartRecipe) -> ChartPreview:
    """Count resources without allocating directions or evaluating records."""
    _validate_target(decoder, target)
    if not isinstance(recipe, ChartRecipe):
        raise TypeError("recipe must be ChartRecipe")
    rank = entries = 0
    for stage in _used_stages(target):
        size = len(stage.weights) * stage.width
        if recipe.mode == "coordinate":
            rank += size
            entries += size * size
        elif recipe.mode == "grid-box":
            entries += 2 * size
        elif recipe.mode == "stage-rtn":
            if any(_nearest(value, stage.grids[j]) != value
                   for row in stage.weights for j, value in enumerate(row)):
                rank += 1
                entries += size
    # The provider uses global rank at every stage, including zero directions.
    # Error descriptors have rank+3 terms and scalar upper-triangular moments.
    error_entries = (rank + 3) * (rank + 4) // 2
    per_group = sum((rank + 1) * stage.width**2 + rank**2 + error_entries for stage in target.stages)
    all_groups = per_group * target.recipe.group_count
    parameters = sum(len(stage.weights) * stage.width for stage in target.stages)
    grid_entries = sum(sum(len(grid) for grid in stage.grids) for stage in target.stages)
    exceeded = tuple(name for name, actual, limit in (
        ("rank", rank, recipe.max_rank), ("direction_entries", entries, recipe.max_direction_entries),
        ("aggregate_rationals", all_groups, recipe.max_aggregate_rationals)) if actual > limit)
    return ChartPreview(recipe.mode, rank, entries, per_group, all_groups, 2 + rank + rank**2,
                        parameters, (parameters * target.recipe.bits + 7) // 8, grid_entries, exceeded)


@dataclass(frozen=True)
class ChartConstruction:
    target_digest: str
    recipe: ChartRecipe
    chart: AffineChart | ParameterBox
    preview: ChartPreview
    constructor_source_sha256: str

    def payload(self):
        if isinstance(self.chart, ParameterBox):
            return {"schema": "constructed-base-only-box-v1", "target_digest": self.target_digest,
                    "recipe": self.recipe.payload(), "preview": self.preview.payload(),
                    "constructor_source_sha256": self.constructor_source_sha256,
                    "box_sha256": self.chart.digest, "provenance": self.chart.provenance,
                    "precision_bits": self.chart.precision_bits,
                    "prefix_rule": "check every installed finite ancestor against fixed coordinate bounds",
                    "corpus_access": "none; frozen grid extrema and finite base weights only"}
        directions = [{stage: [[_pair(x) for x in row] for row in matrix]
                       for stage, matrix in direction.items()} for direction in self.chart.directions]
        return {"schema": "constructed-base-only-chart-v1", "target_digest": self.target_digest,
                "recipe": self.recipe.payload(), "preview": self.preview.payload(),
                "constructor_source_sha256": self.constructor_source_sha256,
                "directions_sha256": hashlib.sha256(_json(directions)).hexdigest(),
                "radii": [_pair(x) for x in self.chart.radii], "provenance": self.chart.provenance,
                "precision_bits": self.chart.precision_bits,
                "prefix_rule": "exact fit to complete installed finite ancestor prefix; reject any residual",
                "corpus_access": "none; constructor inputs contain only decoder, generated target, and fixed recipe"}

    def canonical_bytes(self) -> bytes:
        return _json(self.payload())

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def build_chart(decoder: CertifiedDecoder, target: TargetManifest, recipe: ChartRecipe) -> ChartConstruction:
    preview = preview_chart(decoder, target, recipe)
    if not preview.feasible:
        raise ChartBudgetError("chart budget exceeded: " + ", ".join(preview.over_budget))
    if recipe.mode == "grid-box":
        source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        provenance = "base-only-grid-box-v1:" + hashlib.sha256(_json({"target": target.digest,
                     "recipe": recipe.payload(), "constructor_source_sha256": source_hash})).hexdigest()
        box = grid_box(decoder, target, provenance, recipe.precision_bits)
        return ChartConstruction(target.digest, recipe, box, preview, source_hash)
    directions, radii = [], []
    for stage in _used_stages(target):
        if recipe.mode == "stage-rtn":
            drift = tuple(tuple(_nearest(value, stage.grids[j]) - value for j, value in enumerate(row))
                          for row in stage.weights)
            if any(value for row in drift for value in row):
                directions.append({stage.stage_id: drift})
                radii.append(recipe.radius)
        elif recipe.mode == "coordinate":
            for i, row in enumerate(stage.weights):
                for j, value in enumerate(row):
                    step = stage.grids[j][1] - stage.grids[j][0]
                    direction = tuple(tuple(step if (ii, jj) == (i, j) else Q(0)
                                            for jj in range(stage.width)) for ii in range(len(stage.weights)))
                    directions.append({stage.stage_id: direction})
                    radius = max(abs(stage.grids[j][0] - value), abs(stage.grids[j][-1] - value)) / step
                    radii.append(recipe.radius * radius)
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    provenance = "base-only-chart-v1:" + hashlib.sha256(_json({"target": target.digest,
                    "recipe": recipe.payload(), "constructor_source_sha256": source_hash})).hexdigest()
    chart = AffineChart(tuple(directions), tuple(radii), provenance, recipe.precision_bits)
    return ChartConstruction(target.digest, recipe, chart, preview, source_hash)


def make_service(decoder: CertifiedDecoder, target: TargetManifest, construction: ChartConstruction):
    """Reconstruct inputs and bind the explicit V_cert contract to the service."""
    _validate_target(decoder, target)
    if not isinstance(construction, ChartConstruction):
        raise TypeError("construction must come from build_chart")
    expected = build_chart(decoder, target, construction.recipe)
    if construction.canonical_bytes() != expected.canonical_bytes():
        raise ValueError("chart does not match the deterministic construction")
    from .aggregate_response_service import AggregateRepairService
    provider = (BoxResponseProvider(decoder, construction.chart) if isinstance(construction.chart, ParameterBox)
                else AutomaticResponseProvider(decoder, construction.chart))
    job = target.make_job(provider.reference_id)

    def evaluate(record, stage, prefix):
        if prefix.manifest_digest != job.manifest_digest:
            raise ValueError("foreign evaluator prefix")
        if stage not in job.stages:
            raise ValueError("foreign evaluator stage")
        return decoder.stage_features(stage.stage_id, decoder.decode_payload(record.payload), prefix.as_mapping())

    return AggregateRepairService(job, evaluate, provider.intrinsic_moments, provider.contracts, provider.query,
                                  provider_id=provider.provider_id, extractor_id=provider.reference_id,
                                  reference_weights={s: tuple(tuple(Q.from_float(x) for x in row)
                                                             for row in decoder.base._float_weights[s])
                                                     for s in decoder.stage_ids})
