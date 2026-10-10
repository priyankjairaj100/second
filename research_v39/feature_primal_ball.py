"""Feature-space certificates using the existing shared ball row kernel.

Every feature matrix inside the supplied box has a positive semidefinite Gram.
The existing directed Gram kernel encloses each such Gram. The existing
residual verifier then bounds its rounding coefficients. The V37 ball adapter
verifies rows and applies its mandatory interval fallback to unresolved rows.
No proposal or floating Gram is accepted as exact evidence by itself.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import time

import numpy as np

from research_v35 import direct_gram
from research_v37 import direct_gram_ball
from src import native_ball_quantizer as ball
from src import primal_certificate_v30 as primal
from src.dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from src.exact_core import _rational
from src.low_rank_certified import LowRankUnresolved
from src.token_box_certificate import TokenBoxResult, _finish, _matrix
from src.transformer_backend import _check_runtime


def assess_feature_primal_ball(*, rows, width, tokens, bits=4, budget=primal.PrimalBudget()):
    if type(tokens) is not int or tokens < 0:
        raise ValueError('tokens must be a nonnegative built-in integer')
    assessment = direct_gram_ball.assess_direct_gram_ball_budget(
        rows=rows, width=width, bits=bits, budget=budget)
    assessment['tokens'] = tokens
    assessment['work_units'] += width * width * tokens
    assessment['explicit_array_bytes'] += 8 * 4 * width * tokens
    reasons = []
    if assessment['work_units'] > budget.max_work_units:
        reasons.append('structural work exceeds budget')
    if assessment['explicit_array_bytes'] > budget.max_workspace_bytes:
        reasons.append('explicit arrays exceed budget')
    assessment.update(admitted=not reasons, refusal_reason='; '.join(reasons),
        work_scope='directed feature Gram, residual coefficients, ball rows, and mandatory interval fallback')
    return assessment


@dataclass(frozen=True)
class FeaturePrimalBallResult(TokenBoxResult):
    backend: str = 'feature_primal_shared_ball_v39'
    diagnostics: object = None


def certify_feature_primal_ball(weights, lower, upper, scale_values=None, *,
        ridge, normalization=1, bits=4, significant_bits=24, budget=primal.PrimalBudget()):
    """Return exact constant codes for all features in the box, or refuse.

    The API derives Gram bounds from supplied features. It accepts no external
    coefficient evidence or claim of positive semidefiniteness. All callers
    must keep inputs unchanged during the call. Bounds require supported IEEE
    arithmetic, positive ridge, fixed normalization, and base-only row grids.
    """
    started = time.perf_counter_ns()
    _check_runtime()
    for name, value in (('weights', weights), ('lower', lower), ('upper', upper)):
        if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 2:
            raise TypeError(name + ' must be an ordinary binary64 matrix')
    if lower.shape != upper.shape or weights.shape[1] != lower.shape[0]:
        raise ValueError('feature dimensions differ')
    admission = assess_feature_primal_ball(rows=weights.shape[0], width=weights.shape[1],
        tokens=lower.shape[1], bits=bits, budget=budget)
    if not admission['admitted']:
        raise primal.PrimalUnresolved('feature primal ball admission refused: ' + admission['refusal_reason'])
    for name, value in (('weights', weights), ('lower', lower), ('upper', upper)):
        _matrix(value, name)
    if np.any(lower > upper):
        raise ValueError('reversed feature endpoints')
    scales = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is not None:
        supplied = tuple(scale_values)
        if any(type(v) is not float for v in supplied) or supplied != scales:
            raise ValueError('row scales differ from the fixed base weights')
    lam, norm = _rational(ridge, 'ridge'), _rational(normalization, 'normalization')
    if lam <= 0 or norm <= 0:
        raise ValueError('ridge and normalization must be positive')
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(2.) != tiny + tiny or tiny * np.float64(1.) != tiny:
        raise primal.PrimalUnresolved('NumPy gradual-underflow runtime check failed')
    coefficient_build, row_build = primal.prepare_primal_native(), ball.prepare_native_ball()
    weights, lower, upper = (np.require(x, dtype=np.float64, requirements=['C', 'A'])
                             for x in (weights, lower, upper))
    with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
        tick = time.perf_counter_ns()
        gram_lo, gram_hi = primal._gram_bounds(lower, upper, arithmetic_backend='native')
        gram_ns = time.perf_counter_ns() - tick
        tick = time.perf_counter_ns()
        evidence = direct_gram._coefficient_bounds(gram_lo, gram_hi, lam * norm, arithmetic_backend='native')
        coefficient_ns = time.perf_counter_ns() - tick
        grid, boundaries = _grid_arrays(scales, bits)
        codes, rows = direct_gram_ball._rows_with_ball(weights, evidence.centers, evidence.radii, grid, boundaries)
        base = _finish(codes, weights.size, 0, int(np.count_nonzero(lower != upper)),
                       evidence.max_solution_error_squared, None)
    diagnostics = dict(admission=admission, gram_elapsed_ns=gram_ns, coefficient_elapsed_ns=coefficient_ns,
        rows=rows, coefficient_build=coefficient_build, row_build=row_build,
        max_residual_squared=evidence.max_residual_squared, proposal_resets=evidence.proposal_resets,
        wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        total_elapsed_ns=time.perf_counter_ns() - started)
    return FeaturePrimalBallResult(**base.__dict__, diagnostics=diagnostics)
