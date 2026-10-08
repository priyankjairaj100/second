"""Common native acceleration for the unchanged exact dyadic target.

The native program uses strict binary64 scalar operations. Explicit balls
certify each decision. Unresolved rows use the existing certified solver.
This is shared numerical infrastructure, not an unlearning speed claim.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import numpy as np

from .batched_token_solver import _coefficient_enclosures
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays, quantize_dyadic_rows
from .exact_core import _rational
from .low_rank_certified import CertifiedTokenResult, LowRankUnresolved, _up
from .transformer_backend import _check_runtime


_C_SOURCE = r'''
#include <float.h>
#include <fenv.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#pragma STDC FENV_ACCESS ON
#pragma STDC FP_CONTRACT OFF

static double up(double x) { return nextafter(x, INFINITY); }
static double plus(double a, double b) { return up(a + b); }
static double times(double a, double b) { return up(a * b); }

int nb_runtime(void) {
    volatile double tiny = 0x0.0000000000001p-1022;
    volatile double one = 1.0;
    volatile double two = 2.0;
    volatile double half_ulp = 0x1p-53;
    if (sizeof(double) != 8 || FLT_RADIX != 2 || DBL_MANT_DIG != 53 ||
        DBL_MAX_EXP != 1024 || DBL_MIN_EXP != -1021 ||
        fegetround() != FE_TONEAREST || tiny * one != tiny ||
        tiny * two != tiny + tiny || tiny == 0.0 || one + half_ulp != one)
        return 0;
    return 1;
}

static int cell(double v, double radius, const double *boundary, int count, int index) {
    double lower = nextafter(v - radius, -INFINITY);
    double upper = nextafter(v + radius, INFINITY);
    if (!isfinite(lower) || !isfinite(upper)) return 0;
    return (index == 0 || lower > boundary[index - 1]) &&
           (index == count || upper <= boundary[index]);
}

int nb_run(size_t rows, size_t width, size_t rank, size_t grid_size,
           const double *weights, const double *features, const double *coefficient,
           const double *rho, const double *umax, const double *u_l1,
           const double *grid, const double *boundary, const int16_t *candidate,
           double *codes, int64_t *failed, uint64_t *counts) {
    if (!nb_runtime()) return 1;
    double *s = (double *)calloc(rank ? rank : 1, sizeof(double));
    double *a = (double *)calloc(rank ? rank : 1, sizeof(double));
    if (!s || !a) { free(s); free(a); return 2; }
    const double floor_bound = 0x1p-1000;
    const double dot_factor = ldexp(4.0 * ((double)rank + 3.0), -53);
    for (size_t row = 0; row < rows; ++row) {
        for (size_t t = 0; t < rank; ++t) { s[t] = 0.0; a[t] = 0.0; }
        failed[row] = -1;
        const double *row_grid = grid + row * grid_size;
        const double *row_boundary = boundary + row * (grid_size - 1);
        for (size_t i = 0; i < width; ++i) {
            counts[2]++;
            double w = weights[row * width + i];
            double v = w, p_sum = 0.0, mixed = 0.0, s_l1 = 0.0, a_l1 = 0.0;
            for (size_t t = 0; t < rank; ++t) {
                double c = coefficient[i * rank + t];
                double p = c * s[t];
                v = v + p;
                p_sum = p_sum + fabs(p);
                mixed = mixed + fabs(c) * a[t];
                s_l1 = s_l1 + fabs(s[t]);
                a_l1 = a_l1 + a[t];
            }
            double factor = ldexp(2.0 * ((double)i + 6.0), -53);
            double accum_radius = plus(times(factor, plus(2.0 * mixed, floor_bound)),
                                       times(umax[i], u_l1[i]));
            double accum_norm = plus(plus(2.0 * s_l1, times(factor, 2.0 * a_l1)),
                                     times((double)rank, umax[i]));
            double coefficient_radius = times(rho[i], accum_norm);
            double arithmetic_radius = plus(times(dot_factor, plus(fabs(w), p_sum)), floor_bound);
            double radius = plus(plus(accum_radius, coefficient_radius), arithmetic_radius);
            if (!isfinite(v) || !isfinite(radius) || !isfinite(mixed) ||
                !isfinite(s_l1) || !isfinite(a_l1) || !isfinite(p_sum)) {
                failed[row] = (int64_t)i; break;
            }
            int index = -1;
            if (candidate) {
                int proposed = candidate[row * width + i];
                counts[0]++;
                if (cell(v, radius, row_boundary, (int)grid_size - 1, proposed)) {
                    index = proposed; counts[1]++;
                }
            }
            if (index < 0) {
                int low = 0, high = (int)grid_size - 1;
                while (low < high) {
                    int mid = low + (high - low) / 2;
                    if (v > row_boundary[mid]) low = mid + 1;
                    else high = mid;
                }
                index = low;
                if (!cell(v, radius, row_boundary, (int)grid_size - 1, index)) {
                    failed[row] = (int64_t)i; break;
                }
            }
            double q = row_grid[index];
            codes[row * width + i] = q;
            double difference = w - q;
            int nonfinite = 0;
            for (size_t t = 0; t < rank; ++t) {
                double p = features[i * rank + t] * difference;
                s[t] = s[t] + p;
                a[t] = a[t] + fabs(p);
                if (!isfinite(s[t]) || !isfinite(a[t])) nonfinite = 1;
            }
            if (nonfinite) { failed[row] = (int64_t)i; break; }
            counts[3]++;
        }
    }
    free(s); free(a); return 0;
}
'''

_FLAGS = ('-std=c11', '-O3', '-shared', '-fPIC', '-fno-fast-math',
          '-ffp-contract=off', '-frounding-math', '-fexcess-precision=standard')
_NATIVE = None
_BUILD = None
_BUILD_DIRECTORY = None


def prepare_native_ball():
    """Compile once per process and return full local build provenance.

    Existing binary caches are not trusted. Compilation is outside kernel time.
    The caller must include compilation in its declared complete transaction.
    """
    global _NATIVE, _BUILD, _BUILD_DIRECTORY
    if _NATIVE is not None:
        return dict(_BUILD, compiled_now=False, call_compile_elapsed_ns=0)
    started = time.perf_counter_ns()
    compiler = shutil.which('cc')
    if compiler is None:
        raise LowRankUnresolved('a local C compiler is required for the native ball backend')
    directory = tempfile.TemporaryDirectory(prefix='native-ball-v17-')
    source = Path(directory.name) / 'native_ball.c'
    binary = Path(directory.name) / 'native_ball.so'
    source.write_text(_C_SOURCE)
    command = [compiler, *_FLAGS, str(source), '-o', str(binary), '-lm']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise LowRankUnresolved('strict native ball compilation failed: ' + result.stderr[:2000])
        native = ctypes.CDLL(str(binary))
        native.nb_runtime.restype = ctypes.c_int
        if native.nb_runtime() != 1:
            raise LowRankUnresolved('native binary64 runtime premises failed')
        ptr = ctypes.POINTER(ctypes.c_double)
        native.nb_run.argtypes = ([ctypes.c_size_t] * 4 + [ptr] * 8 +
            [ctypes.POINTER(ctypes.c_int16), ptr, ctypes.POINTER(ctypes.c_int64),
             ctypes.POINTER(ctypes.c_uint64)])
        native.nb_run.restype = ctypes.c_int
        version = subprocess.run([compiler, '--version'], capture_output=True, text=True, timeout=10)
        _BUILD = {'source_sha256': hashlib.sha256(_C_SOURCE.encode()).hexdigest(),
                  'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                  'compiler': compiler, 'compiler_version': version.stdout.splitlines()[0],
                  'flags': list(_FLAGS), 'compile_elapsed_ns': time.perf_counter_ns() - started}
        _BUILD_DIRECTORY, _NATIVE = directory, native
    except BaseException:
        directory.cleanup()
        raise
    return dict(_BUILD, compiled_now=True, call_compile_elapsed_ns=_BUILD['compile_elapsed_ns'])


def build_native_kernel(cache_directory=None):
    """Compatibility entry point; existing binary caches are never trusted."""
    return prepare_native_ball()


def _coefficient_radii(errors):
    """Certify square roots by exact rational comparison, not libm trust."""
    radii = np.empty_like(errors)
    for i, error in enumerate(errors):
        if not math.isfinite(float(error)) or error < 0:
            raise LowRankUnresolved('invalid coefficient error enclosure')
        value = math.sqrt(float(error))
        exact = Fraction.from_float(float(error))
        while Fraction.from_float(value) ** 2 < exact:
            value = math.nextafter(value, math.inf)
        radii[i] = value
    return radii


def _underflow_bounds(features, coefficients):
    """Compute small shared upper bounds with directed elementary additions."""
    width, rank = features.shape
    prefix = np.zeros(rank, dtype=np.float64)
    umax = np.empty(width, dtype=np.float64)
    u_l1 = np.zeros(width, dtype=np.float64)
    for i in range(width):
        umax[i] = float(np.max(_up(math.ldexp(1.0, -1000) * _up(1.0 + prefix)))) if rank else 0.0
        prefix = _up(prefix + np.abs(features[i]))
    for t in range(rank):
        u_l1 = _up(u_l1 + np.abs(coefficients[:, t]))
    if not np.all(np.isfinite(umax)) or not np.all(np.isfinite(u_l1)):
        raise LowRankUnresolved('native underflow bound overflowed')
    return umax, u_l1


@dataclass(frozen=True)
class NativeBallTokenResult(CertifiedTokenResult):
    native_certified_rows: int = 0
    fallback_rows: int = 0
    native_attempted_decisions: int = 0
    native_prefix_certified_decisions: int = 0
    candidate_checks: int = 0
    candidate_hits: int = 0
    coefficient_elapsed_ns: int = 0
    bounds_elapsed_ns: int = 0
    native_elapsed_ns: int = 0
    fallback_elapsed_ns: int = 0
    compile_elapsed_ns: int = 0
    quantizer_elapsed_ns: int = 0
    candidate_source: str = 'none'
    native_source_sha256: str = ''
    native_binary_sha256: str = ''
    native_compiler: str = ''


def native_ball_quantize_dyadic_rows(
        weights, features, scale_values=None, *, candidate=None, bits=4,
        significant_bits=24, ridge, normalization=1, max_exact_rank=64,
        max_exact_coordinates=16, max_refinement_coordinates=16):
    """Certify the unchanged target with shared native arithmetic.

    A candidate only changes the first cell tested. Fresh uses the same kernel.
    Whole-row fallback repeats work and remains part of the total cost.
    All exact/refinement budgets apply jointly to all unresolved rows.
    No result is returned when the fallback cannot certify the target.
    """
    started = time.perf_counter_ns()
    _check_runtime()
    expected = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is None:
        supplied = expected
    else:
        supplied = tuple(scale_values)
        if any(type(x) is not float for x in supplied) or supplied != expected:
            raise ValueError('scale_values must equal canonical base-only dyadic scales')
    if (type(features) is not np.ndarray or features.dtype != np.float64 or features.ndim != 2
            or weights.shape[1] != features.shape[0] or not np.all(np.isfinite(features))):
        raise TypeError('features must be a finite matching binary64 matrix')
    if max(weights.shape[1], features.shape[1]) > 2 ** 20:
        raise ValueError('native error bounds require width and rank at most 2**20')
    for name, value in (('max_exact_rank', max_exact_rank),
                        ('max_exact_coordinates', max_exact_coordinates),
                        ('max_refinement_coordinates', max_refinement_coordinates)):
        if type(value) is not int or value < 0:
            raise ValueError(name + ' must be a nonnegative built-in integer')
    lam, norm = _rational(ridge, 'ridge'), _rational(normalization, 'normalization')
    if lam <= 0 or norm <= 0:
        raise ValueError('ridge and normalization must be positive')
    grid, boundaries = _grid_arrays(supplied, bits)
    candidate_indices = None
    if candidate is not None:
        if (type(candidate) is not np.ndarray or candidate.dtype != np.float64
                or candidate.shape != weights.shape or not np.all(np.isfinite(candidate))):
            raise ValueError('candidate must be a finite binary64 array with the weight shape')
        candidate_indices = np.empty(weights.shape, dtype=np.int16)
        for row in range(len(weights)):
            indices = np.searchsorted(grid[row], candidate[row])
            if np.any(indices >= len(grid[row])) or not np.array_equal(grid[row, indices], candidate[row]):
                raise ValueError('candidate values must belong to the exact row grid')
            candidate_indices[row] = indices
    build = prepare_native_ball()
    weights = np.ascontiguousarray(weights)
    features = np.ascontiguousarray(features)
    tick = time.perf_counter_ns()
    coefficients, errors = _coefficient_enclosures(features, lam * norm)
    coefficient_ns = time.perf_counter_ns() - tick
    tick = time.perf_counter_ns()
    rho = _coefficient_radii(errors)
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        umax, u_l1 = _underflow_bounds(features, coefficients)
    bounds_ns = time.perf_counter_ns() - tick
    codes = np.empty_like(weights)
    failed = np.empty(len(weights), dtype=np.int64)
    counts = np.zeros(4, dtype=np.uint64)
    ptr = ctypes.POINTER(ctypes.c_double)
    arrays = (weights, features, coefficients, rho, umax, u_l1, grid, boundaries)
    tick = time.perf_counter_ns()
    status = _NATIVE.nb_run(len(weights), weights.shape[1], features.shape[1], grid.shape[1],
        *(array.ctypes.data_as(ptr) for array in arrays),
        None if candidate_indices is None else candidate_indices.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
        codes.ctypes.data_as(ptr), failed.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
        counts.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)))
    native_ns = time.perf_counter_ns() - tick
    if status:
        raise LowRankUnresolved('native runtime or allocation failure; no codes committed')
    selected = np.flatnonzero(failed >= 0)
    exact_decisions, exact_coordinates, refined_coordinates, fallback_ns = 0, (), (), 0
    if len(selected):
        tick = time.perf_counter_ns()
        fallback = quantize_dyadic_rows(weights[selected], features,
            tuple(supplied[int(row)] for row in selected), bits=bits, significant_bits=significant_bits,
            ridge=ridge, normalization=normalization, max_exact_rank=max_exact_rank,
            max_exact_coordinates=max_exact_coordinates,
            max_refinement_coordinates=max_refinement_coordinates)
        codes[selected] = fallback.codes
        fallback_ns = time.perf_counter_ns() - tick
        exact_decisions = fallback.exact_decisions
        exact_coordinates, refined_coordinates = fallback.exact_coordinates, fallback.refined_coordinates
    codes.flags.writeable = False
    return NativeBallTokenResult(
        codes, weights.size - exact_decisions, exact_decisions, exact_coordinates,
        refined_coordinates, float(np.max(errors)), native_certified_rows=len(weights)-len(selected),
        fallback_rows=len(selected), native_attempted_decisions=int(counts[2]),
        native_prefix_certified_decisions=int(counts[3]),
        candidate_checks=int(counts[0]), candidate_hits=int(counts[1]),
        coefficient_elapsed_ns=coefficient_ns, bounds_elapsed_ns=bounds_ns,
        native_elapsed_ns=native_ns, fallback_elapsed_ns=fallback_ns,
        compile_elapsed_ns=build['call_compile_elapsed_ns'],
        quantizer_elapsed_ns=time.perf_counter_ns()-started,
        candidate_source='supplied' if candidate is not None else 'none',
        native_source_sha256=build['source_sha256'], native_binary_sha256=build['binary_sha256'],
        native_compiler=build['compiler_version'])


native_quantize_dyadic_rows = native_ball_quantize_dyadic_rows
