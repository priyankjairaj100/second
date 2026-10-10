"""Shared exact-Gram verifier with explicit larger-token admission.

The V37 numerical steps are unchanged. Only the exact archive budget is
passed explicitly to its enclosure converter. Trusted PSD lineage remains
mandatory. This adapter cannot widen an admission budget by itself.
"""
import hashlib
from pathlib import Path
import time
import numpy as np
from research_v35 import direct_gram as direct
from research_v35.exact_gram import GramBudget, require_trusted_gram, to_float64_enclosure
from research_v37.direct_gram_ball import (
    DirectGramBallResult, DirectGramBallUnresolved, assess_direct_gram_ball_budget, _rows_with_ball)
from src import native_ball_quantizer as ball
from src import primal_certificate_v30 as primal
from src.dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from src.exact_core import _rational
from src.low_rank_certified import LowRankUnresolved
from src.token_box_certificate import _finish, _matrix
from src.transformer_backend import _check_runtime


def certify_exact_gram_ball(weights, gram, scale_values=None, *, ridge, bits=4,
                            significant_bits=24, candidate_codes=None,
                            budget=primal.PrimalBudget(), gram_budget=GramBudget()):
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
            lower, upper = to_float64_enclosure(gram, budget=gram_budget)
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
