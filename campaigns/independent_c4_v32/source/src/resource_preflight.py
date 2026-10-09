"""Config-only planning counts before eager checkpoint decoding.

Counts use the current dense reference representation. Memory numbers apply
declared planning costs to scalar slots. They are neither measured peaks nor
proved memory upper bounds. A passing estimate does not guarantee allocation.
Stage-RTN counts are conservative because zero directions require weight reads.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .checkpoint_adapter import _config, _json
from .chart_construction import ChartRecipe
from .target_manifest import TargetRecipe


class ResourcePlanError(ValueError):
    """The declared planning limits reject a configuration."""


@dataclass(frozen=True)
class PreflightResult:
    config_sha256: str
    quantized_parameters: int
    fixed_parameter_slots: int
    stage_count: int
    chart_rank_upper: int
    direction_entries_upper: int
    aggregate_rationals_upper: int
    grid_entries: int
    temporary_jet_components_upper: int
    planning_bytes: int
    memory_budget_bytes: int
    rejected_limits: tuple[str, ...]
    response_tier: str = "linear"

    @property
    def allowed_by_plan(self) -> bool:
        return not self.rejected_limits

    def payload(self) -> dict:
        result = dict(self.__dict__)
        result['rejected_limits'] = list(self.rejected_limits)
        result.update(schema='config-resource-plan-v1', allowed_by_plan=self.allowed_by_plan,
                      measured=False, memory_bound_proved=False,
                      planning_scalar_bytes=128,
                      planning_jet_component_bytes=128,
                      assumptions='dense base state; all potential RTN directions retained; one parameter-stage wrapper at a time; no record-dependent allocation counted',
                      exclusions=['record payloads', 'metadata', 'feature activations', 'serialization buffers',
                                  'temporary arithmetic integers', 'Python interpreter', 'other processes'],
                      warning='Passing this plan does not guarantee memory fit or useful runtime.')
        return result

    def require_allowed(self) -> None:
        if self.rejected_limits:
            raise ResourcePlanError('configuration exceeds planning limits: ' + ', '.join(self.rejected_limits))


def inspect_local_config(directory: str | Path, chart_recipe: ChartRecipe,
                         target_recipe: TargetRecipe, *,
                         memory_budget_bytes: int = 6 * 2**30) -> PreflightResult:
    """Read config metadata only. Never open a tensor file or execute a model."""
    if not isinstance(chart_recipe, ChartRecipe) or not isinstance(target_recipe, TargetRecipe):
        raise TypeError('generated chart and target recipes are required')
    if type(memory_budget_bytes) is not int or memory_budget_bytes <= 0:
        raise ValueError('memory_budget_bytes must be a positive integer')
    root = Path(directory).resolve()
    path = (root / 'config.json').resolve()
    if path.parent != root:
        raise ValueError('config must remain inside the supplied directory')
    with path.open('rb') as handle:
        raw = handle.read(1_048_577)
    if len(raw) > 1_048_576:
        raise ValueError('configuration exceeds one MiB')
    config, _ = _config(_json(raw))
    d, f, blocks = config.model_width, config.feedforward_width, config.block_count
    stage_count = 4 * blocks
    parameters = blocks * (4*d*d + 2*f*d)
    # All previous stages are dependencies. The last stage cannot affect a
    # later calibration input, so its directions are absent from this chart.
    if chart_recipe.mode == 'stage-rtn':
        rank = stage_count - 1
        entries = parameters - f*d
    elif chart_recipe.mode == 'coordinate':
        rank = parameters - f*d
        entries = blocks * (10*d**4 + 2*(f*d)**2) - (f*d)**2
    elif chart_recipe.mode == 'grid-box':
        rank = 0
        entries = 2 * (parameters - f*d)
    else:
        rank = entries = 0
    error = (rank+3)*(rank+4)//2
    if chart_recipe.response_tier == 'quadratic':
        aggregates = target_recipe.group_count * ((rank+1)*(rank+2)//2*blocks*(3*d*d+f*f)
                                                   + stage_count*error)
    else:
        aggregates = target_recipe.group_count * ((rank+1)*blocks*(3*d*d+f*f)
                                                   + stage_count*(rank*rank+error))
    grids = (2**target_recipe.bits) * blocks * (3*d+f)
    # Lazy parameter wrappers retain one accessed stage matrix at a time.
    # Include the finite-error scalar beside each interval value/derivative.
    jets = max(3*d*d, f*d) * (2+rank+rank*rank)
    fixed = (2*config.vocabulary_size*d + config.max_sequence_length*d
             + blocks*(9*d+f) + 2*d + config.vocabulary_size)
    planning = 128*(parameters+fixed+entries+aggregates+grids+jets)
    limits = tuple(name for name, actual, limit in (
        ('chart_rank_upper', rank, chart_recipe.max_rank),
        ('direction_entries_upper', entries, chart_recipe.max_direction_entries),
        ('aggregate_rationals_upper', aggregates, chart_recipe.max_aggregate_rationals),
        ('grid_entries', grids, target_recipe.max_grid_entries),
        ('planning_bytes', planning, memory_budget_bytes)) if actual > limit)
    return PreflightResult(hashlib.sha256(raw).hexdigest(), parameters, fixed, stage_count,
                           rank, entries, aggregates, grids, jets, planning, memory_budget_bytes, limits,
                           chart_recipe.response_tier)
