"""Config-only planning for compact import and one finite forward pass.

This plan covers base weights, finite forward execution, and target metadata.
It excludes quantization, repair, exact Grams, factors, charts, and proof jets.
Passing this plan does not pass any empirical gate or prove a memory bound.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .checkpoint_adapter import _config, _json
from .resource_preflight import ResourcePlanError
from .target_manifest import TargetRecipe


@dataclass(frozen=True)
class CompactForwardPlan:
    config_sha256: str
    max_record_tokens: int
    stage_count: int
    quantized_parameter_elements: int
    source_parameter_elements_upper: int
    largest_matrix_elements: int
    largest_activation_elements: int
    grid_entries: int
    components_bytes: tuple[tuple[str, int], ...]
    planning_bytes: int
    memory_budget_bytes: int
    rejected_limits: tuple[str, ...]

    @property
    def allowed_by_plan(self) -> bool:
        return not self.rejected_limits

    def require_allowed(self) -> None:
        if self.rejected_limits:
            raise ResourcePlanError("compact finite-forward-only plan rejected: " + ", ".join(self.rejected_limits))

    def payload(self) -> dict:
        out = dict(self.__dict__)
        out["components_bytes"] = dict(self.components_bytes)
        out["rejected_limits"] = list(self.rejected_limits)
        out.update(
            schema="compact-finite-forward-plan-v1",
            scope="compact checkpoint import; one base finite forward pass; fixed target metadata",
            allowed_by_plan=self.allowed_by_plan,
            authorizes_quantization_or_repair=False,
            measured=False,
            memory_bound_proved=False,
            runtime_bound_proved=False,
            assumptions=[
                "At most one record executes at a time.",
                "Every source element reserves eight bytes, including an optional duplicate tied head.",
                "One stage or head converts to binary64 at a time.",
                "Conversion reserves 24 bytes per element of the largest matrix.",
                "Finite activations reserve 256 bytes per element of the largest activation matrix.",
                "Grid rationals reserve 128 bytes per entry.",
                "Interpreter, libraries, and unmodeled overhead receive a one GiB planning allowance.",
                "All byte allowances are planning choices, not proved object-size bounds.",
            ],
            exclusions=[
                "Calibration corpus and record pools", "Installed quantized code matrices",
                "Exact Gram matrices and factors", "Certificate response state and proof jets",
                "Curation and request state", "Multiple simultaneous workers",
                "Unbounded arithmetic precision", "Model quality and useful execution speed",
            ],
            warning="Use a bounded worker. Passing this plan does not admit quantization, repair, or paper experiments.",
        )
        return out


def inspect_compact_forward_config(directory: str | Path, target_recipe: TargetRecipe, *,
                                   max_record_tokens: int,
                                   memory_budget_bytes: int = 6 * 2**30) -> CompactForwardPlan:
    """Read config.json only. Do not open tensor files or execute the model."""
    if not isinstance(target_recipe, TargetRecipe):
        raise TypeError("target_recipe must be TargetRecipe")
    for label, value in (("max_record_tokens", max_record_tokens), ("memory_budget_bytes", memory_budget_bytes)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{label} must be a positive integer")
    root = Path(directory).resolve()
    path = (root / "config.json").resolve()
    if path.parent != root:
        raise ValueError("config must remain inside the supplied directory")
    with path.open("rb") as handle:
        raw = handle.read(1_048_577)
    if len(raw) > 1_048_576:
        raise ValueError("configuration exceeds one MiB")
    config, _ = _config(_json(raw))
    d, f, blocks = config.model_width, config.feedforward_width, config.block_count
    vocabulary, positions = config.vocabulary_size, config.max_sequence_length
    parameters = blocks * (4 * d * d + 2 * d * f)
    fixed = 2 * vocabulary * d + positions * d + blocks * (9 * d + f) + 2 * d
    largest_matrix = max(vocabulary * d, positions * d, 3 * d * d, d * f)
    largest_activation = max_record_tokens * max(vocabulary, 3 * d, f)
    grid_entries = (1 << target_recipe.bits) * blocks * (3 * d + f)
    components = (
        ("source_tensor_bytes_upper", 8 * (parameters + fixed)),
        ("matrix_conversion_temporary_allowance", 24 * largest_matrix),
        ("finite_activation_temporary_allowance", 256 * largest_activation),
        ("attention_temporary_allowance", 64 * config.head_count * max_record_tokens**2),
        ("grid_rational_allowance", 128 * grid_entries),
        ("bias_and_metadata_allowance", 128 * (vocabulary + blocks * (9 * d + f) + 2 * d) + 2**20),
        ("streaming_hash_allowance", 2 * 65536),
        ("runtime_and_unmodeled_allowance", 2**30),
    )
    planning = sum(value for _, value in components)
    rejected = tuple(label for label, value, limit in (
        ("max_record_tokens", max_record_tokens, positions),
        ("grid_entries", grid_entries, target_recipe.max_grid_entries),
        ("planning_bytes", planning, memory_budget_bytes),
    ) if value > limit)
    return CompactForwardPlan(hashlib.sha256(raw).hexdigest(), max_record_tokens, 4 * blocks,
                              parameters, parameters + fixed, largest_matrix, largest_activation,
                              grid_entries, components, planning, memory_budget_bytes, rejected)
