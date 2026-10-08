"""Deterministic corner proposals for a conditional quantizer decision.

All gradients and solves here are untrusted proposals. Only separate exact
point quantization can turn distinct corner outputs into a negative witness.
This module neither certifies constant codes nor declares box ambiguity.
"""
from dataclasses import dataclass
import math

import numpy as np

from .exact_core import _rational


class CornerProposalUnresolved(ArithmeticError):
    """A finite numerical corner proposal could not be constructed."""


@dataclass(frozen=True)
class GradientCorners:
    minus: np.ndarray
    plus: np.ndarray
    gradient: np.ndarray
    midpoint: np.ndarray
    midpoint_decision: float
    coordinate: int
    guarantee: str = "finite endpoint proposals only; exact point solves must verify any witness"


def _freeze(value):
    return np.frombuffer(value.tobytes(order='C'), dtype=np.float64).reshape(value.shape)


def _array(value, name, dimension):
    if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != dimension:
        raise TypeError(name + ' must be an ordinary binary64 array with the required dimension')
    if not np.isfinite(value).all():
        raise ValueError(name + ' must contain only finite values')


def gradient_corners(weights_row, candidate_row, lower, upper, coordinate, *, beta):
    """Propose two box corners from a fixed-prefix decision gradient.

Feature arrays use width-by-token order. All original weight columns remain.
beta is the positive exact ridge-normalization product. Candidate codes stay
fixed during differentiation, even if exact corner solves later change them.

The plus corner uses the upper endpoint where the proposed gradient is
nonnegative. The minus corner uses the opposite endpoint. Zero gradients
therefore choose upper for plus and lower for minus. No sampling is used.
Caller-owned arrays must remain unchanged throughout the call.
"""
    _array(weights_row, 'weights_row', 1)
    _array(candidate_row, 'candidate_row', 1)
    _array(lower, 'lower', 2)
    _array(upper, 'upper', 2)
    width = len(weights_row)
    if (not width or candidate_row.shape != weights_row.shape
            or lower.shape != upper.shape or lower.shape[0] != width):
        raise ValueError('weight rows and feature boxes must have matching nonempty width')
    if np.any(lower > upper):
        raise ValueError('reversed feature box')
    if type(coordinate) is not int or not 0 <= coordinate < width:
        raise ValueError('coordinate must be a built-in integer within the original width')
    exact_beta = _rational(beta, 'beta')
    if exact_beta <= 0:
        raise ValueError('beta must be positive')
    try:
        nominal_beta = float(exact_beta)
    except OverflowError as exc:
        raise CornerProposalUnresolved('beta has no positive finite binary64 proposal') from exc
    if not math.isfinite(nominal_beta) or nominal_beta <= 0:
        raise CornerProposalUnresolved('beta has no positive finite binary64 proposal')
    with np.errstate(over='ignore', invalid='ignore', under='ignore', divide='ignore'):
        # The finite average can lose a subnormal half. Clamping keeps this
        # untrusted evaluation point inside the supplied finite box.
        midpoint = np.maximum(lower, np.minimum(upper, lower/2.0 + upper/2.0))
        rank = midpoint.shape[1]
        gradient = np.zeros_like(midpoint)
        decision = float(weights_row[coordinate])
        if rank:
            suffix = midpoint[coordinate:]
            gram = suffix.T @ suffix + nominal_beta*np.eye(rank)
            difference = weights_row[:coordinate] - candidate_row[:coordinate]
            accumulated = difference @ midpoint[:coordinate]
            if not np.isfinite(gram).all() or not np.isfinite(accumulated).all():
                raise CornerProposalUnresolved('nonfinite midpoint system')
            try:
                solution = np.linalg.solve(gram, np.column_stack((midpoint[coordinate], accumulated)))
            except np.linalg.LinAlgError as exc:
                raise CornerProposalUnresolved('midpoint solve failed') from exc
            a, b = solution[:, 0], solution[:, 1]
            gradient[:coordinate] = difference[:, None]*a[None, :]
            xa, xb = suffix @ a, suffix @ b
            gradient[coordinate:] = -xb[:, None]*a[None, :] - xa[:, None]*b[None, :]
            gradient[coordinate] += b
            decision += float(midpoint[coordinate] @ b)
        if (not np.isfinite(midpoint).all() or not np.isfinite(gradient).all()
                or not math.isfinite(decision)):
            raise CornerProposalUnresolved('nonfinite midpoint gradient or decision')
        nonnegative = gradient >= 0.0
        plus = np.where(nonnegative, upper, lower)
        minus = np.where(nonnegative, lower, upper)
    return GradientCorners(_freeze(minus), _freeze(plus), _freeze(gradient),
                           _freeze(midpoint), decision, coordinate)
