"""Exact pooled-Gram decisions with the shared native ball kernel.

The unchanged V35 primal residual certificate supplies coefficient boxes.
Their outward Euclidean radii permit the unchanged V17 ball decision kernel.
Its virtual features are the identity, not new calibration observations.
Unresolved rows receive the unchanged primal interval verifier. Both passes
are admitted and timed; failure of either required verifier returns no model.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import hashlib
from pathlib import Path
import time

import numpy as np

from research_v35 import direct_gram as direct
from research_v35.exact_gram import require_trusted_gram, to_float64_enclosure
from src import native_ball_quantizer as ball
from src import primal_certificate_v30 as primal
from src.dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from src.exact_core import _rational
from src.low_rank_certified import LowRankUnresolved, _finite, _norm_squared_upper
from src.token_box_certificate import TokenBoxResult, _finish, _matrix
from src.transformer_backend import _check_runtime


class DirectGramBallUnresolved(direct.DirectGramUnresolved):
    """The ball pass and required interval fallback did not certify all rows."""


def assess_direct_gram_ball_budget(*, rows, width, bits=4, budget=primal.PrimalBudget()):
    """Admit shared coefficients, virtual identity, and both complete row passes.

    Work units are structural proxies, not FLOPs or time. Caller Gram storage,
    integer accumulation, allocator overhead, and compiler memory are excluded.
    The extra envelope covers identity, radius conversion temporaries, native
    vectors, failed-row copies, fallback outputs, and immutable returned codes.
    """
    result = direct.assess_direct_gram_budget(rows=rows, width=width, bits=bits, budget=budget)
    if width > 2**20:
        raise ValueError('native ball width and virtual rank must not exceed 2**20')
    result['work_units'] += rows * width**2 + 3 * width**2
    result['explicit_array_bytes'] += 8 * (5 * width**2 + 4 * rows * width + 12 * width + 4 * rows)
    reasons = []
    if result['work_units'] > budget.max_work_units:
        reasons.append(f'work {result["work_units"]} > {budget.max_work_units}')
    if result['explicit_array_bytes'] > budget.max_workspace_bytes:
        reasons.append(f'workspace {result["explicit_array_bytes"]} > {budget.max_workspace_bytes}')
    result.update(admitted=not reasons, refusal_reason='; '.join(reasons),
        virtual_rank=width, admitted_full_row_passes=2,
        work_scope='shared direct coefficients, radius conversion, ball rows, and worst-case interval fallback')
    return result


def _euclidean_radii(radii):
    """Outward square/sum, followed by the existing exact square-root check."""
    _matrix(radii, 'coefficient radii')
    if np.any(radii < 0):
        raise ValueError('coefficient radii must be nonnegative')
    squared = _norm_squared_upper(radii, radii)
    _finite(squared)
    return ball._coefficient_radii(squared)


def _rows_with_ball(weights, centers, radii, grid, boundaries):
    """Apply the reviewed ball algebra to virtual identity accumulators.

    Coefficient evidence is an internal precondition, supplied by the unchanged
    residual verifier. The native ball entry point never solves an identity
    metric. It only consumes the supplied coefficient centers and error radii.
    """
    rows, width = weights.shape
    row_start = time.perf_counter_ns()
    tick = time.perf_counter_ns()
    identity = np.eye(width, dtype=np.float64)
    rho = _euclidean_radii(radii)
    umax, u_l1 = ball._underflow_bounds(identity, centers)
    bounds_elapsed = time.perf_counter_ns() - tick
    codes = np.empty_like(weights)
    failed = np.empty(rows, dtype=np.int64)
    counts = np.zeros(4, dtype=np.uint64)
    ptr = ctypes.POINTER(ctypes.c_double)
    arrays = (weights, identity, centers, rho, umax, u_l1, grid, boundaries)
    tick = time.perf_counter_ns()
    status = ball._NATIVE.nb_run(rows, width, width, grid.shape[1],
        *(value.ctypes.data_as(ptr) for value in arrays), None,
        codes.ctypes.data_as(ptr), failed.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
        counts.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)))
    native_elapsed = time.perf_counter_ns() - tick
    if status:
        raise DirectGramBallUnresolved(
            f'direct Gram ball runtime or allocation failure: status={status}; no codes committed')
    selected = np.flatnonzero(failed >= 0)
    diagnostics = dict(bounds_elapsed_ns=bounds_elapsed, native_elapsed_ns=native_elapsed,
        native_attempted_decisions=int(counts[2]), native_prefix_certified_decisions=int(counts[3]),
        native_certified_rows=rows-len(selected), fallback_rows=len(selected),
        fallback_row_indices=tuple(map(int, selected)),
        ball_failed_coordinates=tuple(int(failed[row]) for row in selected),
        fallback_elapsed_ns=0, fallback_native_elapsed_ns=0,
        fallback_attempted_decisions=0, fallback_certified_decisions=0,
        max_euclidean_coefficient_radius=float(np.max(rho)))
    if len(selected):
        tick = time.perf_counter_ns()
        try:
            fallback, receipt = primal._rows_native(
                weights[selected], centers, radii, grid[selected], boundaries[selected])
        except LowRankUnresolved as exc:
            diagnostics['fallback_elapsed_ns'] = time.perf_counter_ns() - tick
            diagnostics['row_elapsed_ns'] = time.perf_counter_ns() - row_start
            # The unchanged helper discards its native receipt on failure.
            # Unknown work must not be reported as zero work.
            diagnostics['fallback_native_elapsed_ns'] = None
            diagnostics['fallback_attempted_decisions'] = None
            diagnostics['fallback_certified_decisions'] = None
            error = DirectGramBallUnresolved(str(exc))
            error.native_ball_diagnostics = diagnostics
            raise error from exc
        codes[selected] = fallback
        diagnostics.update(fallback_elapsed_ns=time.perf_counter_ns()-tick,
            fallback_native_elapsed_ns=receipt['native_elapsed_ns'],
            fallback_attempted_decisions=receipt['attempted_decisions'],
            fallback_certified_decisions=receipt['certified_decisions'])
    diagnostics['row_elapsed_ns'] = time.perf_counter_ns() - row_start
    return codes, diagnostics


@dataclass(frozen=True)
class DirectGramBallResult(TokenBoxResult):
    guarantee: str = 'exact dyadic codes for the trusted exact PSD Gram and original normalization'
    backend: str = 'verified_direct_exact_gram_shared_ball_v37'
    width: int = 0
    tokens: int = 0
    virtual_rank: int = 0
    normalization_numerator: int = 0
    normalization_denominator: int = 1
    work_units: int = 0
    explicit_array_bytes: int = 0
    admitted_full_row_passes: int = 2
    enclosed_gram_entries: int = 0
    proposal_resets: int = 0
    max_residual_squared: float = 0.0
    max_euclidean_coefficient_radius: float = 0.0
    enclosure_elapsed_ns: int = 0
    coefficient_elapsed_ns: int = 0
    bounds_elapsed_ns: int = 0
    native_elapsed_ns: int = 0
    row_elapsed_ns: int = 0
    fallback_elapsed_ns: int = 0
    fallback_native_elapsed_ns: int = 0
    compile_elapsed_ns: int = 0
    total_elapsed_ns: int = 0
    native_attempted_decisions: int = 0
    native_prefix_certified_decisions: int = 0
    native_certified_rows: int = 0
    fallback_rows: int = 0
    fallback_row_indices: tuple[int, ...] = ()
    ball_failed_coordinates: tuple[int, ...] = ()
    fallback_attempted_decisions: int = 0
    fallback_certified_decisions: int = 0
    native_source_sha256: str = ''
    native_binary_sha256: str = ''
    native_flags: tuple[str, ...] = ()
    native_compiler: str = ''
    coefficient_native_source_sha256: str = ''
    coefficient_native_binary_sha256: str = ''
    coefficient_native_flags: tuple[str, ...] = ()
    coefficient_native_compiler: str = ''
    wrapper_sha256: str = ''
    reused_direct_wrapper_sha256: str = ''


def certify_exact_gram_ball(weights, gram, scale_values=None, *, ridge, bits=4,
                            significant_bits=24, candidate_codes=None,
                            budget=primal.PrimalBudget()):
    """Certify the unchanged target with shared native row acceleration.

    Normalization comes only from trusted Gram lineage. Ball-refused rows
    receive one complete interval fallback, sharing the same coefficients.
    Candidate codes are checked after certification; they never guide it.
    Caller inputs must remain unchanged throughout execution.
    """
    started = time.perf_counter_ns()
    _check_runtime()
    require_trusted_gram(gram)
    if type(weights) is not np.ndarray or weights.dtype != np.float64 or weights.ndim != 2:
        raise TypeError('weights must be an ordinary binary64 NumPy matrix')
    if weights.shape[1] != gram.width:
        raise ValueError('weight width must equal trusted Gram width')
    admission = assess_direct_gram_ball_budget(rows=weights.shape[0], width=weights.shape[1],
                                              bits=bits, budget=budget)
    if not admission['admitted']:
        raise DirectGramBallUnresolved('direct Gram ball admission refused: ' + admission['refusal_reason'])
    _matrix(weights, 'weights')
    if candidate_codes is not None:
        _matrix(candidate_codes, 'candidate_codes')
        if candidate_codes.shape != weights.shape:
            raise ValueError('candidate codes must match weights')
    expected = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is not None:
        supplied = tuple(scale_values)
        if any(type(value) is not float for value in supplied) or supplied != expected:
            raise ValueError('scales must equal the canonical base-only dyadic row scales')
    lam, norm = _rational(ridge, 'ridge'), _rational(gram.normalization, 'normalization')
    if lam <= 0 or norm <= 0:
        raise ValueError('ridge and normalization must be positive')
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny*np.float64(1.) != tiny or tiny*np.float64(2.) != tiny+tiny:
        raise DirectGramBallUnresolved('NumPy gradual-underflow runtime check failed')
    coefficient_build, row_build = primal.prepare_primal_native(), ball.prepare_native_ball()
    weights = np.require(weights, dtype=np.float64, requirements=['C', 'A'])
    try:
        with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
            tick = time.perf_counter_ns()
            lower, upper = to_float64_enclosure(gram)
            enclosure_elapsed = time.perf_counter_ns() - tick
            for name, value in (('Gram lower', lower), ('Gram upper', upper)):
                _matrix(value, name)
                if value.shape != (gram.width, gram.width):
                    raise ValueError('Gram enclosure must be square and match its declared width')
            if (np.any(lower > upper) or not np.array_equal(lower, lower.T)
                    or not np.array_equal(upper, upper.T) or np.any(np.diag(lower) < 0)):
                raise ValueError('invalid symmetric Gram enclosure')
            lower, upper = (np.require(value, dtype=np.float64, requirements=['C', 'A'])
                            for value in (lower, upper))
            enclosed = int(np.count_nonzero(lower != upper))
            tick = time.perf_counter_ns()
            evidence = direct._coefficient_bounds(lower, upper, lam*norm, arithmetic_backend='native')
            coefficient_elapsed = time.perf_counter_ns() - tick
            grid, boundaries = _grid_arrays(expected, bits)
            codes, diagnostic = _rows_with_ball(weights, evidence.centers, evidence.radii, grid, boundaries)
            base = _finish(codes, weights.size, 0, 0, evidence.max_solution_error_squared, candidate_codes)
    except DirectGramBallUnresolved:
        raise
    except LowRankUnresolved as exc:
        raise DirectGramBallUnresolved(str(exc)) from exc
    values = dict(base.__dict__)
    values.pop('guarantee')
    wrapper_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    direct_sha = hashlib.sha256(Path(direct.__file__).read_bytes()).hexdigest()
    return DirectGramBallResult(**values, **diagnostic, width=gram.width, tokens=gram.tokens,
        virtual_rank=gram.width, normalization_numerator=norm.numerator,
        normalization_denominator=norm.denominator, work_units=admission['work_units'],
        explicit_array_bytes=admission['explicit_array_bytes'], enclosed_gram_entries=enclosed,
        proposal_resets=evidence.proposal_resets, max_residual_squared=evidence.max_residual_squared,
        enclosure_elapsed_ns=enclosure_elapsed, coefficient_elapsed_ns=coefficient_elapsed,
        compile_elapsed_ns=coefficient_build['call_compile_elapsed_ns']+row_build['call_compile_elapsed_ns'],
        total_elapsed_ns=time.perf_counter_ns()-started,
        native_source_sha256=row_build['source_sha256'], native_binary_sha256=row_build['binary_sha256'],
        native_flags=tuple(row_build['flags']), native_compiler=row_build['compiler_version'],
        coefficient_native_source_sha256=coefficient_build['source_sha256'],
        coefficient_native_binary_sha256=coefficient_build['binary_sha256'],
        coefficient_native_flags=tuple(coefficient_build['flags']),
        coefficient_native_compiler=coefficient_build['compiler_version'],
        wrapper_sha256=wrapper_sha, reused_direct_wrapper_sha256=direct_sha)
