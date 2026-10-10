"""Bounded feature-space certificates without a concatenated token matrix."""
from pathlib import Path
import hashlib
import time
import numpy as np

from research_v35 import direct_gram
from research_v37 import direct_gram_ball
from research_v39.feature_primal_ball import FeaturePrimalBallResult
from src import native_ball_quantizer as ball
from src import primal_certificate_v30 as primal
from src.dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from src.exact_core import _rational
from src.token_box_certificate import _finish, _matrix
from src.transformer_backend import _check_runtime


def assess_streamed(*, rows, width, tokens, block_tokens, max_blocks=None, bits=4, budget=primal.PrimalBudget()):
    for name, value, minimum in [('tokens', tokens, 0), ('block_tokens', block_tokens, 1)]:
        if type(value) is not int or value < minimum:
            raise ValueError(name + ' has an invalid limit')
    max_blocks = tokens if max_blocks is None else max_blocks
    if type(max_blocks) is not int or max_blocks < 0 or max_blocks * block_tokens < tokens:
        raise ValueError('block count cannot cover the declared tokens')
    max_blocks = min(tokens, max_blocks)
    result = direct_gram_ball.assess_direct_gram_ball_budget(rows=rows, width=width, bits=bits, budget=budget)
    # Every block is nonempty. Both product work and all block sums are admitted.
    result['work_units'] += width * width * tokens + 4 * width * width * max_blocks
    # Block endpoints, directed partial Grams, sum temporaries, and zero masks.
    result['explicit_array_bytes'] += 32 * width * min(tokens, block_tokens) + 80 * width * width
    reasons = []
    if result['work_units'] > budget.max_work_units:
        reasons.append('streamed work exceeds budget')
    if result['explicit_array_bytes'] > budget.max_workspace_bytes:
        reasons.append('streamed arrays exceed budget')
    result.update(admitted=not reasons, refusal_reason='; '.join(reasons), tokens=tokens, block_tokens=block_tokens, max_blocks=max_blocks,
        scope='Explicit workspace excludes caller-owned source storage and whole-process overhead')
    return result


def _sum_boxes(lower, upper, next_lower, next_upper):
    """Outward addition with exact-zero identities and a PSD diagonal guard."""
    first_zero = (lower == 0) & (upper == 0)
    second_zero = (next_lower == 0) & (next_upper == 0)
    lo = np.nextafter(lower + next_lower, -np.inf)
    hi = np.nextafter(upper + next_upper, np.inf)
    lo = np.where(first_zero, next_lower, np.where(second_zero, lower, lo))
    hi = np.where(first_zero, next_upper, np.where(second_zero, upper, hi))
    np.fill_diagonal(lo, np.maximum(np.diag(lo), 0.))
    _matrix(lo, 'streamed Gram lower')
    _matrix(hi, 'streamed Gram upper')
    return np.ascontiguousarray(lo), np.ascontiguousarray(hi)


def certify_streamed_primal_ball(weights, blocks, *, total_tokens, block_tokens,
        ridge, normalization=1, scale_values=None, bits=4, significant_bits=24, max_blocks=None,
        budget=primal.PrimalBudget()):
    """Certify one common code array for every realization of streamed boxes.

    Each item is a pair of finite binary64 arrays with shape (width, tokens).
    Blocks must be nonempty and stay within the registered block-token limit.
    The exact total is required before any numerical allocation. Inputs must
    remain unchanged while their private snapshot is copied. No external Gram
    or claimed PSD matrix enters this interface.
    """
    started = time.perf_counter_ns()
    _check_runtime()
    if type(weights) is not np.ndarray or weights.dtype != np.float64 or weights.ndim != 2:
        raise TypeError('weights must be an ordinary binary64 matrix')
    rows, width = weights.shape
    admission = assess_streamed(rows=rows, width=width, tokens=total_tokens,
        block_tokens=block_tokens, max_blocks=max_blocks, bits=bits, budget=budget)
    if not admission['admitted']:
        raise primal.PrimalUnresolved('streamed primal admission refused: ' + admission['refusal_reason'])
    _matrix(weights, 'weights')
    scales = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is not None:
        supplied = tuple(scale_values)
        if any(type(v) is not float for v in supplied) or supplied != scales:
            raise ValueError('row scales differ from fixed base weights')
    lam, norm = _rational(ridge, 'ridge'), _rational(normalization, 'normalization')
    if lam <= 0 or norm <= 0:
        raise ValueError('ridge and normalization must be positive')
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.) != tiny or tiny * np.float64(2.) != tiny + tiny:
        raise primal.PrimalUnresolved('NumPy gradual-underflow runtime check failed')
    coefficient_build, row_build = primal.prepare_primal_native(), ball.prepare_native_ball()
    weights = np.require(weights, dtype=np.float64, requirements=['C', 'A'])
    gram_lo, gram_hi = np.zeros((width, width)), np.zeros((width, width))
    count = seen = nonpoint = 0
    tick = time.perf_counter_ns()
    with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
        for lower, upper in blocks:
            if count >= admission['max_blocks']:
                raise ValueError('streamed block count exceeds the declared limit')
            for value in (lower, upper):
                if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 2:
                    raise TypeError('block endpoints must be ordinary binary64 matrices')
            if (lower.shape != upper.shape or lower.shape[0] != width
                    or not 1 <= lower.shape[1] <= block_tokens or seen + lower.shape[1] > total_tokens):
                raise ValueError('streamed block dimensions exceed the declared extent')
            lower, upper = (np.array(value, dtype=np.float64, order='C', copy=True) for value in (lower, upper))
            _matrix(lower, 'block lower')
            _matrix(upper, 'block upper')
            if np.any(lower > upper):
                raise ValueError('reversed block endpoints')
            next_lo, next_hi = primal._gram_bounds(lower, upper, arithmetic_backend='native')
            gram_lo, gram_hi = _sum_boxes(gram_lo, gram_hi, next_lo, next_hi)
            seen += lower.shape[1]
            count += 1
            nonpoint += int(np.count_nonzero(lower != upper))
            del lower, upper, next_lo, next_hi
        if seen != total_tokens:
            raise ValueError('stream ended before the declared token total')
        gram_ns = time.perf_counter_ns() - tick
        tick = time.perf_counter_ns()
        evidence = direct_gram._coefficient_bounds(gram_lo, gram_hi, lam * norm, arithmetic_backend='native')
        coefficient_ns = time.perf_counter_ns() - tick
        grid, boundaries = _grid_arrays(scales, bits)
        codes, row_diagnostics = direct_gram_ball._rows_with_ball(weights, evidence.centers, evidence.radii, grid, boundaries)
        base = _finish(codes, weights.size, 0, nonpoint, evidence.max_solution_error_squared, None)
    return FeaturePrimalBallResult(**base.__dict__, backend='streamed_feature_primal_ball_v40', diagnostics=dict(
        admission=admission, blocks=count, observed_tokens=seen, gram_elapsed_ns=gram_ns,
        coefficient_elapsed_ns=coefficient_ns, rows=row_diagnostics, coefficient_build=coefficient_build,
        row_build=row_build, total_elapsed_ns=time.perf_counter_ns() - started,
        wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
