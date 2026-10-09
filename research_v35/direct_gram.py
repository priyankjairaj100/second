"""Bounded direct-Gram certificates for the existing exact dyadic target.

Only a Gram created by trusted exact feature accumulation and closed source
algebra is accepted. A checksum, positive diagonal, or floating eigenvalue
test does not establish the PSD premise. Raw interval arrays are not an API.

This module reuses the unchanged V30 residual and row certificates. Floating
inverse proposals never establish correctness. Accepted codes equal the
exact target with H = ridge*I + G/original_normalization. Unresolved cases
return no model. This is a component, not a complete pooled-Gram service.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import time

import numpy as np

from src import primal_certificate_v30 as primal
from src.dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from src.exact_core import _rational
from src.low_rank_certified import LowRankUnresolved, _initial_gram, _point_bounds
from src.token_box_certificate import TokenBoxResult, _finish, _matrix
from src.transformer_backend import _check_runtime


class DirectGramUnresolved(primal.PrimalUnresolved):
    """The admitted direct-Gram certificate did not prove complete codes."""


def assess_direct_gram_budget(*, rows, width, bits=4, budget=primal.PrimalBudget()):
    """Bound coefficient/row arrays and structural work before allocation.

    The V30 envelope uses tokens=0 because no feature multiplication occurs.
    Work is d**3 + m*d**2 + 2*m*2**bits; it is not a FLOP or bit-cost count.
    Exact accumulation, serialized parsing, and caller Gram residency require
    separate Gram admission. Compiler and allocator overhead require an OS cap.
    """
    result = primal.assess_primal_budget(rows=rows, width=width, tokens=0,
                                        bits=bits, budget=budget)
    result['work_scope'] = 'direct coefficient and row certification; excludes exact accumulation'
    return result


def _coefficient_bounds(gram_lo, gram_hi, beta, *, arithmetic_backend):
    """V30 coefficient algorithm, replacing only feature-to-Gram formation.

    Internal precondition: bounds contain the trusted exact PSD Gram.
    This helper does not establish PSD for arbitrary caller arrays.
    """
    width = len(gram_lo)
    beta_lo, beta_hi = _point_bounds(beta)
    _, _, beta_squared_lo = _initial_gram(0, beta)
    nominal = gram_lo / 2.0 + gram_hi / 2.0
    inverse = np.zeros((width, width))
    centers, radii = np.zeros((width, width)), np.zeros((width, width))
    residual_max, error_max, resets = 0.0, 0.0, 0
    for i in range(width - 1, 0, -1):
        proposal, reset = primal._suffix_proposal(nominal, inverse, i, float(beta))
        resets += int(reset)
        if arithmetic_backend == 'native':
            diagnostic = np.zeros(2)
            status = primal._NATIVE.npc_column(
                width, i, primal._ptr(gram_lo), primal._ptr(gram_hi),
                primal._ptr(proposal), beta_lo, beta_hi, beta_squared_lo,
                primal._ptr(centers[i]), primal._ptr(radii[i]), primal._ptr(diagnostic))
            if status:
                raise DirectGramUnresolved(
                    f'direct Gram coefficient enclosure failed at coordinate {i}: status={status}')
            eta_squared, error_squared = map(float, diagnostic)
        else:
            centers[i], radii[i], eta_squared, error_squared = primal._column_python(
                gram_lo, gram_hi, i, proposal, beta_lo, beta_hi, beta_squared_lo)
        residual_max = max(residual_max, eta_squared)
        error_max = max(error_max, error_squared)
    return primal.PrimalCoefficients(centers, radii, residual_max, error_max, resets)


@dataclass(frozen=True)
class DirectGramResult(TokenBoxResult):
    guarantee: str = 'exact dyadic codes for the trusted exact PSD Gram and original normalization'
    backend: str = 'verified_direct_exact_gram_v35'
    arithmetic_backend: str = 'native'
    width: int = 0
    tokens: int = 0
    normalization_numerator: int = 0
    normalization_denominator: int = 1
    work_units: int = 0
    explicit_array_bytes: int = 0
    coefficient_workspace_bytes: int = 0
    enclosed_gram_entries: int = 0
    proposal_resets: int = 0
    max_residual_squared: float = 0.0
    enclosure_elapsed_ns: int = 0
    coefficient_elapsed_ns: int = 0
    native_elapsed_ns: int = 0
    compile_elapsed_ns: int = 0
    total_elapsed_ns: int = 0
    native_source_sha256: str = ''
    native_binary_sha256: str = ''
    native_compiler: str = ''
    native_flags: tuple[str, ...] = ()
    direct_wrapper_sha256: str = ''
    primal_wrapper_sha256: str = ''
    native_attempted_decisions: int = 0
    native_certified_decisions: int = 0


def certify_exact_gram(weights, gram, scale_values=None, *, ridge, bits=4,
                       significant_bits=24, candidate_codes=None,
                       budget=primal.PrimalBudget(), arithmetic_backend='native'):
    """Certify complete rows from trusted exact moments, with no token array.

    ``gram.normalization`` is the original positive calibration normalization.
    It is never inferred from retained tokens. Canonical base-only scales,
    fixed coordinate order, endpoint saturation, and lower-code ties match
    ``quantize_dyadic_rows``. No unresolved approximate result is committed.

    Caller-owned weights must remain unchanged throughout this call. The
    Gram must pass the exact accumulator's trusted-lineage check; loading a
    serialized matrix alone is insufficient to establish that premise.
    """
    # Import here so numerical kernels remain reusable independently of the
    # accumulator. Its trusted-lineage check is mandatory on every call.
    from .exact_gram import require_trusted_gram, to_float64_enclosure

    started = time.perf_counter_ns()
    _check_runtime()
    require_trusted_gram(gram)
    if arithmetic_backend not in ('native', 'python'):
        raise ValueError('arithmetic_backend must be native or python')
    if type(weights) is not np.ndarray or weights.dtype != np.float64 or weights.ndim != 2:
        raise TypeError('weights must be an ordinary binary64 NumPy matrix')
    if weights.shape[1] != gram.width:
        raise ValueError('weight width must equal trusted Gram width')
    admission = assess_direct_gram_budget(rows=weights.shape[0], width=weights.shape[1],
                                         bits=bits, budget=budget)
    if not admission['admitted']:
        raise DirectGramUnresolved('direct Gram admission refused: ' + admission['refusal_reason'])
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
    lam = _rational(ridge, 'ridge')
    norm = _rational(gram.normalization, 'normalization')
    if lam <= 0 or norm <= 0:
        raise ValueError('ridge and normalization must be positive')
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.) != tiny or tiny * np.float64(2.) != tiny + tiny:
        raise DirectGramUnresolved('NumPy gradual-underflow runtime check failed')
    build = primal.prepare_primal_native() if arithmetic_backend == 'native' else {}
    weights = np.require(weights, dtype=np.float64, requirements=['C', 'A'])
    try:
        with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
            tick = time.perf_counter_ns()
            gram_lo, gram_hi = to_float64_enclosure(gram)
            enclosure_elapsed = time.perf_counter_ns() - tick
            # Defensive postconditions do not substitute for PSD lineage.
            for name, value in (('Gram lower', gram_lo), ('Gram upper', gram_hi)):
                _matrix(value, name)
                if value.shape != (gram.width, gram.width):
                    raise ValueError('Gram enclosure must be square and match its declared width')
            if (np.any(gram_lo > gram_hi) or not np.array_equal(gram_lo, gram_lo.T)
                    or not np.array_equal(gram_hi, gram_hi.T) or np.any(np.diag(gram_lo) < 0)):
                raise ValueError('invalid symmetric Gram enclosure')
            gram_lo, gram_hi = (np.require(value, dtype=np.float64, requirements=['C', 'A'])
                                for value in (gram_lo, gram_hi))
            enclosed = int(np.count_nonzero(gram_lo != gram_hi))
            tick = time.perf_counter_ns()
            evidence = _coefficient_bounds(gram_lo, gram_hi, lam * norm,
                                           arithmetic_backend=arithmetic_backend)
            coefficient_elapsed = time.perf_counter_ns() - tick
            grid, boundaries = _grid_arrays(expected, bits)
            row_function = primal._rows_native if arithmetic_backend == 'native' else primal._rows_python
            codes, receipt = row_function(weights, evidence.centers, evidence.radii, grid, boundaries)
            base = _finish(codes, weights.size, 0, 0,
                           evidence.max_solution_error_squared, candidate_codes)
    except DirectGramUnresolved:
        raise
    except LowRankUnresolved as exc:
        raise DirectGramUnresolved(str(exc)) from exc
    values = dict(base.__dict__)
    values.pop('guarantee')
    return DirectGramResult(**values, arithmetic_backend=arithmetic_backend,
        width=gram.width, tokens=gram.tokens,
        normalization_numerator=norm.numerator, normalization_denominator=norm.denominator,
        work_units=admission['work_units'], explicit_array_bytes=admission['explicit_array_bytes'],
        coefficient_workspace_bytes=admission['coefficient_workspace_bytes'],
        enclosed_gram_entries=enclosed, proposal_resets=evidence.proposal_resets,
        max_residual_squared=evidence.max_residual_squared,
        enclosure_elapsed_ns=enclosure_elapsed, coefficient_elapsed_ns=coefficient_elapsed,
        native_elapsed_ns=receipt['native_elapsed_ns'],
        compile_elapsed_ns=build.get('call_compile_elapsed_ns', 0),
        total_elapsed_ns=time.perf_counter_ns() - started,
        native_source_sha256=build.get('source_sha256', ''),
        native_binary_sha256=build.get('binary_sha256', ''),
        native_compiler=build.get('compiler', ''), native_flags=tuple(build.get('flags', ())),
        direct_wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        primal_wrapper_sha256=hashlib.sha256(Path(primal.__file__).read_bytes()).hexdigest(),
        native_attempted_decisions=receipt['attempted_decisions'],
        native_certified_decisions=receipt['certified_decisions'])
