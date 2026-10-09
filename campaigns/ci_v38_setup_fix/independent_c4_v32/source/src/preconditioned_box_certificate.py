"""Universal dyadic certificates with verified coefficient preconditioning.

Midpoint inverses supply proposals only. Directed residual and contraction
checks prove every accepted coefficient bound. The existing ridge-floor
certificate remains an independent fallback. This module changes no target.
"""
from dataclasses import dataclass

import numpy as np

from .dyadic_box_certificate import certify_dyadic_box
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays, _check_row_cells
from .exact_core import _rational
from .low_rank_certified import (
    LowRankUnresolved, _add, _down, _finite, _initial_gram,
    _multiply_point, _up,
)
from .token_box_certificate import (
    TokenBoxResult, TokenBoxUnresolved, _box_residual_squared, _finish,
    _matrix, _multiply, _outer_bounds,
)
from .transformer_backend import _check_runtime


@dataclass(frozen=True)
class PreconditionedBoxResult(TokenBoxResult):
    verified_preconditioner_coordinates: int = 0
    rejected_preconditioner_coordinates: int = 0
    decisions_requiring_preconditioner: int = 0


def _left_product(point, lower, upper):
    """Enclose a point matrix times an interval matrix or vector."""
    shape = (point.shape[0],) + lower.shape[1:]
    out_lo, out_hi = np.zeros(shape), np.zeros(shape)
    for k in range(point.shape[1]):
        coefficient = point[:, k] if lower.ndim == 1 else point[:, k, None]
        lo, hi = _multiply_point(lower[k], upper[k], coefficient)
        out_lo, out_hi = _add(out_lo, out_hi, lo, hi)
    _finite(out_lo, out_hi)
    return out_lo, out_hi


def _positive_product_add(matrix, vector, initial):
    """Upper bound initial + matrix @ vector for nonnegative arguments."""
    value = initial.copy()
    for k in range(len(vector)):
        term = np.where((matrix[:, k] == 0) | (vector[k] == 0),
                        0.0, _up(matrix[:, k] * vector[k]))
        value = np.where(term == 0, value, _up(value + term))
    _finite(value)
    return value


def _supersolution(defect, residual):
    """Prove e >= residual + defect*e, or return no certificate.

The strict directed row-sum test proves ||defect||_infinity < 1.
Candidate iteration and inflation have no authority without the final check.
"""
    rank = len(residual)
    if not rank:
        return np.empty(0)
    if (not np.all(np.isfinite(defect)) or not np.all(np.isfinite(residual))
            or np.any(defect < 0) or np.any(residual < 0)):
        return None
    row_sums = _positive_product_add(defect, np.ones(rank), np.zeros(rank))
    gamma = float(np.max(row_sums))
    if not gamma < 1.0:
        return None
    denominator = float(_down(1.0 - gamma))
    if denominator <= 0:
        return None
    enclosure = residual.copy()
    # Two monotone candidate steps retain useful componentwise differences.
    for _ in range(2):
        required = _positive_product_add(defect, enclosure, residual)
        if np.all(required <= enclosure):
            return enclosure
        enclosure = required
    for _ in range(6):
        required = _positive_product_add(defect, enclosure, residual)
        if np.all(required <= enclosure):
            return enclosure
        deficit = float(np.max(np.maximum(0.0, _up(required - enclosure))))
        correction = float(_up(deficit / denominator))
        # The addition gets its own outward rounding. Acceptance still requires
        # the next independently computed supersolution inequality.
        enclosure = _up(enclosure + correction)
        if not np.all(np.isfinite(enclosure)):
            return None
    return None


def _preconditioned_error(gram_lo, gram_hi, rhs_lo, rhs_hi, proposal, inverse):
    """Return a proved componentwise coefficient radius, or None.

For every G and x in the supplied intervals, D bounds |I-RG| and t
bounds |R(x-Gp)|. A verified e >= t+D*e proves |G^-1*x-p| <= e.
No nominal inverse or solve is accepted without these checks.
"""
    if not np.all(np.isfinite(inverse)) or not np.all(np.isfinite(proposal)):
        return None
    rank = len(proposal)
    if not rank:
        return np.empty(0)
    try:
        rg_lo, rg_hi = _left_product(inverse, gram_lo, gram_hi)
        identity = np.eye(rank)
        defect_lo, defect_hi = _add(identity, identity, -rg_hi, -rg_lo)
        defect = np.maximum(np.abs(defect_lo), np.abs(defect_hi))
        gp_lo, gp_hi = _left_product(proposal[None, :], gram_lo.T, gram_hi.T)
        residual_lo, residual_hi = _add(rhs_lo, rhs_hi, -gp_hi[0], -gp_lo[0])
        transformed_lo, transformed_hi = _left_product(inverse, residual_lo, residual_hi)
        transformed = np.maximum(np.abs(transformed_lo), np.abs(transformed_hi))
        return _supersolution(defect, transformed)
    except LowRankUnresolved:
        return None


def _coefficient_bounds(lower, upper, beta):
    """Build both ridge and preconditioned bounds for each fixed suffix."""
    width, rank = lower.shape
    proposals = np.zeros_like(lower)
    ridge_errors = np.zeros(width)
    component_errors = np.zeros_like(lower)
    valid = np.zeros(width, dtype=bool)
    if not rank:
        return proposals, ridge_errors, component_errors, valid
    gram_lo, gram_hi, beta_squared_lo = _initial_gram(rank, beta)
    inverse = np.eye(rank) / float(beta)
    for i in range(width - 1, -1, -1):
        outer_lo, outer_hi = _outer_bounds(lower[i], upper[i])
        gram_lo, gram_hi = _add(gram_lo, gram_hi, outer_lo, outer_hi)
        _finite(gram_lo, gram_hi)
        midpoint = lower[i] / 2.0 + upper[i] / 2.0
        vector = inverse @ midpoint
        denominator = 1.0 + float(midpoint @ vector)
        if (np.isfinite(denominator) and denominator > 0
                and np.all(np.isfinite(vector))):
            proposal = vector / denominator
            updated = inverse - np.outer(vector, vector) / denominator
            if np.all(np.isfinite(proposal)) and np.all(np.isfinite(updated)):
                inverse = updated
            else:
                inverse, proposal = np.zeros_like(inverse), np.zeros(rank)
        else:
            inverse, proposal = np.zeros_like(inverse), np.zeros(rank)
        proposals[i] = proposal
        ridge_errors[i] = _box_residual_squared(
            gram_lo, gram_hi, lower[i], upper[i], proposal, beta_squared_lo)
        component = _preconditioned_error(
            gram_lo, gram_hi, lower[i], upper[i], proposal, inverse)
        if component is not None:
            component_errors[i] = component
            valid[i] = True
    return proposals, ridge_errors, component_errors, valid


def _component_cells(weights, accum_lo, accum_hi, coefficient, radius, boundaries):
    """Certify cells using sum_k radius[k]*sup|accumulator[k]|."""
    value_lo, value_hi = weights.copy(), weights.copy()
    term_lo, term_hi = _multiply_point(accum_lo, accum_hi, coefficient[:, None])
    for lo, hi in zip(term_lo, term_hi):
        value_lo, value_hi = _add(value_lo, value_hi, lo, hi)
    magnitude = np.maximum(np.abs(accum_lo), np.abs(accum_hi))
    decision_radius = _positive_product_add(magnitude.T, radius, np.zeros(len(weights)))
    value_lo, value_hi = _add(value_lo, value_hi, -decision_radius, decision_radius)
    _finite(value_lo, value_hi)
    midpoint = value_lo / 2.0 + value_hi / 2.0
    indices = np.count_nonzero(midpoint[:, None] > boundaries, axis=1)
    rows = np.arange(len(weights))
    lower_boundary = boundaries[rows, np.maximum(indices - 1, 0)]
    upper_boundary = boundaries[rows, np.minimum(indices, boundaries.shape[1] - 1)]
    safe = (((indices == 0) | (value_lo > lower_boundary))
            & ((indices == boundaries.shape[1]) | (value_hi <= upper_boundary)))
    return indices, safe


def _result(base, valid=0, rejected=0, improved=0):
    return PreconditionedBoxResult(**base.__dict__,
        verified_preconditioner_coordinates=valid,
        rejected_preconditioner_coordinates=rejected,
        decisions_requiring_preconditioner=improved)


def certify_preconditioned_dyadic_box(
        weights, lower, upper, scale_values=None, *, bits=4,
        significant_bits=24, ridge, normalization=1, candidate_codes=None,
        max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=16):
    """Certify exact codes for every factor in the supplied finite box.

This matches certify_dyadic_box's target, tie rule, and public arguments.
Nonzero-width boxes never use pointwise exact fallback. Singleton boxes use
the existing bounded point solver. Caller-owned arrays must remain unchanged.
"""
    _check_runtime()
    for name, value in (("weights", weights), ("lower", lower), ("upper", upper)):
        _matrix(value, name)
    scales = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is not None:
        supplied = tuple(scale_values)
        if any(type(s) is not float for s in supplied) or supplied != scales:
            raise ValueError("scales must equal the canonical base-only dyadic scales")
    if lower.shape != upper.shape or lower.shape[0] != weights.shape[1]:
        raise ValueError("feature box dimensions differ from weight width")
    if np.any(lower > upper):
        raise ValueError("reversed feature box")
    if candidate_codes is not None:
        _matrix(candidate_codes, "candidate_codes")
        if candidate_codes.shape != weights.shape:
            raise ValueError("candidate dimensions differ from weights")
    for value in (max_exact_rank, max_exact_coordinates, max_refinement_coordinates):
        if type(value) is not int or value < 0:
            raise ValueError("fallback limits must be nonnegative built-in integers")
    lam, norm = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    if lam <= 0 or norm <= 0:
        raise ValueError("ridge and normalization must be positive")
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.) != tiny or np.float64(2.) * tiny != tiny + tiny:
        raise TokenBoxUnresolved("gradual-underflow runtime check failed")
    uncertain = int(np.count_nonzero(lower != upper))
    if not uncertain:
        return _result(certify_dyadic_box(weights, lower, upper, scales, bits=bits,
            significant_bits=significant_bits, ridge=lam, normalization=norm,
            candidate_codes=candidate_codes, max_exact_rank=max_exact_rank,
            max_exact_coordinates=max_exact_coordinates,
            max_refinement_coordinates=max_refinement_coordinates))
    try:
        with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
            proposals, errors, component, valid = _coefficient_bounds(lower, upper, lam * norm)
            grid, boundaries = _grid_arrays(scales, bits)
            rows, width = weights.shape
            rank = lower.shape[1]
            accum_lo, accum_hi = np.zeros((rank, rows)), np.zeros((rank, rows))
            codes = np.empty_like(weights)
            improved = 0
            for i in range(width):
                indices, safe = _check_row_cells(
                    weights[:, i], accum_lo, accum_hi, proposals[i], errors[i], boundaries)
                if not np.all(safe) and valid[i]:
                    stronger_indices, stronger_safe = _component_cells(
                        weights[:, i], accum_lo, accum_hi, proposals[i], component[i], boundaries)
                    if np.any(safe & stronger_safe & (indices != stronger_indices)):
                        raise ArithmeticError("independent valid cell certificates disagree")
                    take = ~safe & stronger_safe
                    improved += int(np.count_nonzero(take))
                    indices = np.where(take, stronger_indices, indices)
                    safe |= stronger_safe
                if not np.all(safe):
                    unresolved_rows = np.flatnonzero(~safe)
                    raise TokenBoxUnresolved(
                        f"preconditioned box does not certify every row at coordinate {i}; "
                        f"unresolved_rows={len(unresolved_rows)}; "
                        f"first_unresolved_row={int(unresolved_rows[0])}; "
                        f"verified_preconditioner={bool(valid[i])}")
                codes[:, i] = grid[np.arange(rows), indices]
                dlo, dhi = _add(weights[:, i], weights[:, i], -codes[:, i], -codes[:, i])
                for k in range(rank):
                    tlo, thi = _multiply(dlo, dhi, lower[i, k], upper[i, k])
                    accum_lo[k], accum_hi[k] = _add(accum_lo[k], accum_hi[k], tlo, thi)
                _finite(accum_lo, accum_hi)
            base = _finish(codes, weights.size, 0, uncertain, float(np.max(errors)), candidate_codes)
            count = int(np.count_nonzero(valid))
            return _result(base, count, width - count, improved)
    except TokenBoxUnresolved:
        raise
    except LowRankUnresolved as exc:
        raise TokenBoxUnresolved(str(exc)) from exc
