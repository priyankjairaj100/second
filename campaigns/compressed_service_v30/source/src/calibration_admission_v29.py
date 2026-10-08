"""Necessary memory bounds for the current token-space calibration backend.

This module allocates no numerical arrays. Passing admission means only that
the stated lower bound does not rule out the request. It never guarantees
memory fit, successful certification, completion, or speed superiority.
"""
from dataclasses import dataclass


def _integer(value, name, *, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        relation = 'positive' if positive else 'nonnegative'
        raise ValueError(f'{name} must be a {relation} built-in integer')
    return value


@dataclass(frozen=True)
class StageShape:
    stage_id: str
    width: int
    rows: int

    def __post_init__(self):
        if type(self.stage_id) is not str or not self.stage_id or self.stage_id != self.stage_id.strip():
            raise ValueError('stage_id must be a nonempty built-in string without surrounding whitespace')
        _integer(self.width, 'width', positive=True)
        _integer(self.rows, 'rows', positive=True)


@dataclass(frozen=True)
class StageMemoryBound:
    stage_id: str
    width: int
    rows: int
    retained_tokens: int
    token_matrix_shape: tuple
    token_matrix_bytes: int
    feature_matrix_shape: tuple
    feature_matrix_bytes: int
    coefficient_table_shape: tuple
    coefficient_table_bytes: int
    logical_box_endpoint_bytes: int
    weight_matrix_shape: tuple
    weight_matrix_bytes: int
    alternative_primal_matrix_shape: tuple
    alternative_primal_matrix_bytes: int
    single_array_lower_bound_bytes: int
    exceeds_process_cap: bool
    alternative_primal_certificate_implemented: bool = False


@dataclass(frozen=True)
class CalibrationAdmission:
    backend: str
    retained_tokens: int
    process_cap_bytes: int
    stages: tuple
    single_array_lower_bound_bytes: int
    raw_full_factor_values: int
    raw_full_factor_storage_bytes: int
    status: str
    ruled_out: bool
    lower_bound_witnesses: tuple
    fit_guaranteed: bool = False
    speed_guaranteed: bool = False
    completion_guaranteed: bool = False
    actual_arrays_allocated: bool = False
    alternative_primal_certificate_implemented: bool = False
    guarantee: str = ('Rejection follows from a necessary single-array size. A passing result means only '
                      'not ruled out by this lower bound; all other arrays, runtime, state, and work remain unbounded.')
    storage_scope: str = ('Raw binary64 retained factors across all listed stages, excluding model codes, '
                          'tokens, headers, metadata, temporary arrays, and deleted-source state. '
                          'This is not compressed storage and is not added to the process lower bound.')


def assess_calibration_admission(stages, *, retained_tokens, process_cap_bytes):
    """Reject only when a proved required array exceeds the process cap.

For positive token counts, the current backend forms a dense T-by-T token
matrix. It also materializes d-by-T features/coefficient tables and m-by-d
weights. The maximum required array size is a valid conservative lower bound.
We deliberately do not sum potentially aliased arrays or persistent storage.
The alternative d-by-d size is informative; no primal backend is dispatched.
"""
    _integer(retained_tokens, 'retained_tokens')
    _integer(process_cap_bytes, 'process_cap_bytes', positive=True)
    if type(stages) is not tuple or not stages or any(type(stage) is not StageShape for stage in stages):
        raise ValueError('stages must be a nonempty built-in tuple of StageShape instances')
    if len({stage.stage_id for stage in stages}) != len(stages):
        raise ValueError('stage IDs must be unique')
    token_bytes = 8 * retained_tokens * retained_tokens
    reports, witnesses = [], []
    for stage in stages:
        feature_bytes = 8 * stage.width * retained_tokens
        weight_bytes = 8 * stage.rows * stage.width
        candidates = {
            'dense_token_matrix': token_bytes,
            'feature_or_coefficient_table': feature_bytes,
            'weight_matrix': weight_bytes,
        }
        lower_bound = max(candidates.values())
        for kind, byte_count in candidates.items():
            if byte_count > process_cap_bytes:
                witnesses.append((stage.stage_id, kind, byte_count))
        reports.append(StageMemoryBound(
            stage.stage_id, stage.width, stage.rows, retained_tokens,
            (retained_tokens, retained_tokens), token_bytes,
            (stage.width, retained_tokens), feature_bytes,
            (stage.width, retained_tokens), feature_bytes,
            2 * feature_bytes, (stage.rows, stage.width), weight_bytes,
            (stage.width, stage.width), 8 * stage.width * stage.width,
            lower_bound, lower_bound > process_cap_bytes))
    raw_values = retained_tokens * sum(stage.width for stage in stages)
    lower_bound = max(report.single_array_lower_bound_bytes for report in reports)
    rejected = lower_bound > process_cap_bytes
    return CalibrationAdmission(
        'current_token_space_v28', retained_tokens, process_cap_bytes, tuple(reports),
        lower_bound, raw_values, 8 * raw_values,
        'ruled_out_by_lower_bound' if rejected else 'not_ruled_out_by_lower_bound',
        rejected, tuple(witnesses))
