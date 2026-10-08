"""Bounded-block speculation for the unchanged exact dyadic row target.

Every block starts after all earlier codes are certified. A directed scan
verifies candidate prefixes. One continuation per block combines all
unfinished rows. Exact coefficient and fallback budgets apply across all blocks.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
import time

import numpy as np

from .batched_token_solver import (
    _advance_accumulator, _coefficient_enclosures, _norm_squared_token_major,
)
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays, _check_row_cells
from .exact_core import _nearest_index, _rational
from .low_rank_certified import (
    CertifiedTokenResult, LowRankUnresolved, _add, _down, _exact_coefficient,
    _exact_input, _finite, _multiply_point, _refined_coefficient, _up,
)
from .row_scaled_quantizer import _bits
from .speculative_dyadic_solver import exclusive_interval_scan
from .transformer_backend import _check_runtime


@dataclass(frozen=True)
class BlockSpeculativeTokenResult(CertifiedTokenResult):
    block_width: int = 32
    block_count: int = 0
    speculative_sweeps: int = 0
    speculative_decision_checks: int = 0
    certified_row_blocks: int = 0
    fallback_row_blocks: int = 0
    prefix_verified_decisions: int = 0
    fallback_decisions: int = 0
    prefix_length_histogram: tuple[int, ...] = ()
    coefficient_elapsed_ns: int = 0
    speculative_elapsed_ns: int = 0
    fallback_elapsed_ns: int = 0
    quantizer_elapsed_ns: int = 0
    candidate_source: str = "nearest"
    scan_family: str = "directed_block_blelloch_v1"


def _block_inputs(weights, features, candidate, coefficients, errors,
                  boundaries, incoming_lower, incoming_upper):
    """Enclose F(candidate) inside a block with a certified incoming state.

    All arguments use block-local coordinates. Incoming arrays have shape
    (token, output row). Prefix arrays have shape (coordinate, token, row).
    """
    difference_lo, difference_hi = _add(weights.T, weights.T, -candidate.T, -candidate.T)
    product_lo, product_hi = _multiply_point(
        difference_lo[:, None, :], difference_hi[:, None, :], features[:, :, None])
    _finite(product_lo, product_hi)
    scan_lo, scan_hi = exclusive_interval_scan(product_lo, product_hi)
    scan_lo, scan_hi = _add(
        scan_lo, scan_hi, incoming_lower[None], incoming_upper[None])
    terminal_lo, terminal_hi = _add(
        scan_lo[-1], scan_hi[-1], product_lo[-1], product_hi[-1])
    _finite(scan_lo, scan_hi, terminal_lo, terminal_hi)
    term_lo, term_hi = _multiply_point(scan_lo, scan_hi, coefficients[:, :, None])
    value_lo, value_hi = weights.T.copy(), weights.T.copy()
    for token in range(features.shape[1]):
        value_lo, value_hi = _add(value_lo, value_hi, term_lo[:, token], term_hi[:, token])
    norm_squared = _norm_squared_token_major(
        np.moveaxis(scan_lo, 1, 0), np.moveaxis(scan_hi, 1, 0))
    radius_squared = np.where((norm_squared == 0) | (errors[:, None] == 0),
                              0.0, _up(norm_squared * errors[:, None]))
    _finite(value_lo, value_hi, radius_squared)
    midpoint = value_lo / 2.0 + value_hi / 2.0
    indices = np.count_nonzero(midpoint[:, :, None] > boundaries[None, :, :], axis=2)
    row = np.arange(weights.shape[0])[None, :]
    lower = boundaries[row, np.maximum(indices - 1, 0)]
    upper = boundaries[row, np.minimum(indices, boundaries.shape[1] - 1)]
    lower_gap, upper_gap = _down(value_lo - lower), _down(upper - value_hi)
    lower_safe = (lower_gap > 0) & (_down(lower_gap * lower_gap) > radius_squared)
    upper_safe = (upper_gap > 0) & (_down(upper_gap * upper_gap) > radius_squared)
    lower_safe |= (radius_squared == 0) & (value_lo > lower)
    upper_safe |= (radius_squared == 0) & (value_hi <= upper)
    safe = ((indices == 0) | lower_safe) & ((indices == boundaries.shape[1]) | upper_safe)
    return indices.T, safe.T, scan_lo, scan_hi, terminal_lo, terminal_hi


def block_speculative_quantize_dyadic_rows(
        weights, features, scale_values=None, *, candidate=None, block_width=32,
        max_sweeps=1, row_batch_size=4096, bits=4, significant_bits=24,
        ridge, normalization=1, max_exact_rank=64, max_exact_coordinates=16,
        max_refinement_coordinates=16):
    """Return the exact target, or fail without publishing a model.

    All inputs must remain unchanged during the call. Candidate generation
    is untrusted. Every accepted prefix has a full interval certificate.
    Sweep counts sum across row batches and coordinate blocks.
    Prefix decisions avoid sequential continuation, not verification work.
    All exact and refinement limits count global coordinate indices.
    """
    started = time.perf_counter_ns()
    _check_runtime()
    half = _bits(bits)
    expected = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is None:
        supplied = expected
    else:
        try:
            supplied = tuple(scale_values)
        except TypeError as exc:
            raise TypeError("scale_values must be a sequence of Python floats") from exc
        if any(type(value) is not float for value in supplied) or supplied != expected:
            raise ValueError("scale_values must equal the canonical base-only dyadic row scales")
    if (type(features) is not np.ndarray or features.dtype != np.float64
            or features.ndim != 2 or weights.shape[1] != features.shape[0]):
        raise TypeError("features must be a matching binary64 matrix")
    if not np.all(np.isfinite(features)):
        raise ValueError("features must contain finite values")
    for name, value in (("max_sweeps", max_sweeps), ("max_exact_rank", max_exact_rank),
                        ("max_exact_coordinates", max_exact_coordinates),
                        ("max_refinement_coordinates", max_refinement_coordinates)):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative built-in integer")
    for name, value in (("block_width", block_width), ("row_batch_size", row_batch_size)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive built-in integer")
    lam, norm = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    if lam <= 0 or norm <= 0:
        raise ValueError("ridge and normalization must be positive")
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.) != tiny or np.float64(2.) * tiny != tiny + tiny:
        raise LowRankUnresolved("gradual-underflow runtime check failed")
    grid_codes, boundaries = _grid_arrays(supplied, bits)
    rows, width = weights.shape
    rank = features.shape[1]
    if candidate is not None:
        if (type(candidate) is not np.ndarray or candidate.dtype != np.float64
                or candidate.shape != weights.shape or not np.all(np.isfinite(candidate))):
            raise ValueError("candidate must be a finite binary64 matrix with the weight shape")
        # Validate in both dimensions. This avoids a full-width grid tensor.
        for block_start in range(0, width, block_width):
            block_stop = min(block_start + block_width, width)
            for start in range(0, rows, row_batch_size):
                stop = min(start + row_batch_size, rows)
                if not np.all(np.any(
                        candidate[start:stop, block_start:block_stop, None]
                        == grid_codes[start:stop, None, :], axis=2)):
                    raise ValueError("candidate codes must belong to their exact row grids")
    codes = np.empty_like(weights)
    accumulator_lo, accumulator_hi = np.zeros((rank, rows)), np.zeros((rank, rows))
    tick = time.perf_counter_ns()
    with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
        coefficients, errors = _coefficient_enclosures(features, lam * norm)
    coefficient_ns = time.perf_counter_ns() - tick
    exact_cache, refinement_cache, exact_grids = {}, {}, {}
    exact_coordinates, refined_coordinates = [], []
    exact_decisions = sweeps = checks = prefix_decisions = certified_blocks = fallback_blocks = 0
    speculative_ns = fallback_ns = 0
    # A width larger than d does not allocate a correspondingly large histogram.
    histogram = np.zeros(min(block_width, width) + 1, dtype=np.int64)

    def continue_block(selected, block_start, block_stop, lengths, prefix_lo, prefix_hi):
        nonlocal exact_decisions
        starts = lengths[selected]
        acc_lo, acc_hi = prefix_lo[:, selected].copy(), prefix_hi[:, selected].copy()
        for local_i in range(int(np.min(starts)), block_stop - block_start):
            active = np.flatnonzero(starts <= local_i)
            active_rows = selected[active]
            i = block_start + local_i
            indices, safe = _check_row_cells(
                weights[active_rows, i], acc_lo[:, active], acc_hi[:, active],
                coefficients[i], errors[i], boundaries[active_rows])
            bad = np.flatnonzero(~safe)
            if len(bad) and (i in refinement_cache or len(refined_coordinates) < max_refinement_coordinates):
                if i not in refinement_cache:
                    refined_coordinates.append(i)
                    try:
                        refinement_cache[i] = _refined_coefficient(features, i, lam * norm)
                    except LowRankUnresolved:
                        refinement_cache[i] = None
                refined = refinement_cache[i]
                if refined is not None:
                    better_indices, better_safe = _check_row_cells(
                        weights[active_rows, i], acc_lo[:, active], acc_hi[:, active],
                        refined[0], refined[1], boundaries[active_rows])
                    indices = np.where(safe, indices, better_indices)
                    safe |= better_safe
                bad = np.flatnonzero(~safe)
            if len(bad):
                if rank > max_exact_rank or (i not in exact_cache and len(exact_coordinates) >= max_exact_coordinates):
                    raise LowRankUnresolved(f"exact fallback budget exceeded at coordinate {i}; no codes committed")
                if i not in exact_cache:
                    exact_cache[i] = _exact_coefficient(features, i, lam * norm)
                    exact_coordinates.append(i)
                for row in bad:
                    global_row = int(active_rows[row])
                    if global_row not in exact_grids:
                        scale = Q.from_float(supplied[global_row])
                        exact_grids[global_row] = tuple(code * scale for code in range(-half, half))
                    value = _exact_input(weights, features, codes, global_row, i, exact_cache[i])
                    indices[row] = _nearest_index(value, exact_grids[global_row])
                exact_decisions += len(bad)
            codes[active_rows, i] = grid_codes[active_rows, indices]
            a, b = _advance_accumulator(
                acc_lo[:, active], acc_hi[:, active], weights[active_rows, i],
                codes[active_rows, i], features[i])
            _finite(a, b)
            acc_lo[:, active], acc_hi[:, active] = a, b
        accumulator_lo[:, selected], accumulator_hi[:, selected] = acc_lo, acc_hi

    with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
        for block_start in range(0, width, block_width):
            block_stop = min(block_start + block_width, width)
            size = block_stop - block_start
            # Freeze the incoming accumulator before any row completes this block.
            incoming_lo, incoming_hi = accumulator_lo.copy(), accumulator_hi.copy()
            prefix_lo, prefix_hi = incoming_lo.copy(), incoming_hi.copy()
            lengths = np.zeros(rows, dtype=np.int64)
            pending = []
            for start in range(0, rows, row_batch_size):
                selected = np.arange(start, min(start + row_batch_size, rows))
                tick = time.perf_counter_ns()
                if max_sweeps == 0:
                    proposal = None
                elif candidate is None:
                    nearest = np.count_nonzero(
                        weights[selected, block_start:block_stop, None] > boundaries[selected, None, :], axis=2)
                    proposal = grid_codes[selected[:, None], nearest]
                else:
                    proposal = candidate[selected, block_start:block_stop].copy()
                for _ in range(max_sweeps):
                    if not len(selected):
                        break
                    sweeps += 1
                    checks += len(selected) * size
                    try:
                        indices, safe, scan_lo, scan_hi, terminal_lo, terminal_hi = _block_inputs(
                            weights[selected, block_start:block_stop], features[block_start:block_stop],
                            proposal, coefficients[block_start:block_stop], errors[block_start:block_stop],
                            boundaries[selected], incoming_lo[:, selected], incoming_hi[:, selected])
                    except LowRankUnresolved:
                        break
                    next_proposal = grid_codes[selected[:, None], indices]
                    matches = safe & (next_proposal == proposal)
                    new_lengths = np.where(np.all(matches, axis=1), size, np.argmin(matches, axis=1))
                    for local_row, global_row in enumerate(selected):
                        length = int(new_lengths[local_row])
                        if length > lengths[global_row]:
                            lengths[global_row] = length
                            codes[global_row, block_start:block_start + length] = proposal[local_row, :length]
                            if length < size:
                                prefix_lo[:, global_row] = scan_lo[length, :, local_row]
                                prefix_hi[:, global_row] = scan_hi[length, :, local_row]
                            else:
                                accumulator_lo[:, global_row] = terminal_lo[:, local_row]
                                accumulator_hi[:, global_row] = terminal_hi[:, local_row]
                        known = int(lengths[global_row])
                        next_proposal[local_row, :known] = codes[global_row, block_start:block_start + known]
                    accepted = lengths[selected] == size
                    certified_blocks += int(np.count_nonzero(accepted))
                    selected = selected[~accepted]
                    proposal = next_proposal[~accepted]
                speculative_ns += time.perf_counter_ns() - tick
                if len(selected):
                    fallback_blocks += len(selected)
                    pending.append(selected)
            prefix_decisions += int(np.sum(lengths))
            histogram += np.bincount(lengths, minlength=len(histogram))
            if pending:
                tick = time.perf_counter_ns()
                continue_block(np.concatenate(pending), block_start, block_stop, lengths, prefix_lo, prefix_hi)
                fallback_ns += time.perf_counter_ns() - tick
            _finite(accumulator_lo, accumulator_hi)
    codes.flags.writeable = False
    return BlockSpeculativeTokenResult(
        codes, weights.size - exact_decisions, exact_decisions,
        tuple(sorted(exact_coordinates)), tuple(sorted(refined_coordinates)), float(np.max(errors)),
        block_width=block_width, block_count=(width + block_width - 1) // block_width,
        speculative_sweeps=sweeps, speculative_decision_checks=checks,
        certified_row_blocks=certified_blocks, fallback_row_blocks=fallback_blocks,
        prefix_verified_decisions=prefix_decisions, fallback_decisions=weights.size-prefix_decisions,
        prefix_length_histogram=tuple(int(value) for value in histogram),
        coefficient_elapsed_ns=coefficient_ns, speculative_elapsed_ns=speculative_ns,
        fallback_elapsed_ns=fallback_ns, quantizer_elapsed_ns=time.perf_counter_ns()-started,
        candidate_source="supplied" if candidate is not None else "nearest")
