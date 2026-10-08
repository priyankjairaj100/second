"""Strict native decisions for universal dyadic feature-box certificates.

Python constructs verified coefficient bounds. C encloses every decision over
the complete feature box. Rejection may invoke the existing Python universal
verifier. Only singleton boxes may invoke a point solver. No target changes.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import numpy as np

from . import preconditioned_box_certificate as preconditioned
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from .exact_core import _rational
from .low_rank_certified import LowRankUnresolved
from .native_ball_quantizer import native_ball_quantize_dyadic_rows, _coefficient_radii
from .token_box_certificate import TokenBoxUnresolved, _box_coefficients, _finish, _matrix
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

typedef struct { double lo, hi; } box;
static double down(double x) { return nextafter(x, -INFINITY); }
static double up(double x) { return nextafter(x, INFINITY); }
static int finite_box(box x) { return isfinite(x.lo) && isfinite(x.hi) && x.lo <= x.hi; }
static int zero(box x) { return x.lo == 0.0 && x.hi == 0.0; }
static box add(box a, box b) {
    if (zero(a)) return b;
    if (zero(b)) return a;
    /* Equal singleton opposites cancel exactly, including signed zeros. */
    if (a.lo == a.hi && b.lo == b.hi && a.lo == -b.lo) return (box){0.0, 0.0};
    return (box){down(a.lo + b.lo), up(a.hi + b.hi)};
}
static box multiply(box a, box b) {
    if (zero(a) || zero(b)) return (box){0.0, 0.0};
    double p0 = a.lo * b.lo, p1 = a.lo * b.hi;
    double p2 = a.hi * b.lo, p3 = a.hi * b.hi;
    return (box){down(fmin(fmin(p0, p1), fmin(p2, p3))),
                 up(fmax(fmax(p0, p1), fmax(p2, p3)))};
}

int nbc_runtime(void) {
    volatile double tiny = 0x0.0000000000001p-1022;
    volatile double one = 1.0, two = 2.0, half_ulp = 0x1p-53;
    return sizeof(double) == 8 && FLT_RADIX == 2 && DBL_MANT_DIG == 53 &&
           DBL_MAX_EXP == 1024 && DBL_MIN_EXP == -1021 &&
           fegetround() == FE_TONEAREST && tiny != 0.0 && tiny * one == tiny &&
           tiny * two == tiny + tiny && one + half_ulp == one;
}

/* Exposed only for exact-arithmetic software verification. */
int nbc_probe(int operation, const double *input, double *output) {
    if (!nbc_runtime()) return 1;
    box a = {input[0], input[1]}, b = {input[2], input[3]};
    if (!finite_box(a) || !finite_box(b) || (operation != 0 && operation != 1)) return 2;
    box result = operation == 0 ? add(a, b) : multiply(a, b);
    output[0] = result.lo; output[1] = result.hi;
    return finite_box(result) ? 0 : 3;
}

int nbc_run(size_t rows, size_t width, size_t rank, size_t grid_size,
            const double *weights, const double *lower, const double *upper,
            const double *proposal, const double *radius, const uint8_t *valid,
            const double *grid, const double *boundary, double *codes,
            int64_t *failed, uint64_t *counts) {
    if (!nbc_runtime()) return 1;
    if (rank > SIZE_MAX / sizeof(box)) return 2;
    box *accum = (box *)calloc(rank ? rank : 1, sizeof(box));
    if (!accum) return 2;
    failed[0] = failed[1] = -1;
    for (size_t row = 0; row < rows; ++row) {
        for (size_t k = 0; k < rank; ++k) accum[k] = (box){0.0, 0.0};
        const double *row_grid = grid + row * grid_size;
        const double *row_boundary = boundary + row * (grid_size - 1);
        for (size_t i = 0; i < width; ++i) {
            counts[0]++;
            double w = weights[row * width + i];
            box value = {w, w};
            double decision_radius = 0.0;
            int all_zero = 1;
            for (size_t k = 0; k < rank; ++k) {
                all_zero = all_zero && zero(accum[k]);
                double p = proposal[i * rank + k];
                value = add(value, multiply(accum[k], (box){p, p}));
                double magnitude = fmax(fabs(accum[k].lo), fabs(accum[k].hi));
                double e = radius[i * rank + k];
                if (e != 0.0 && magnitude != 0.0) {
                    double term = up(e * magnitude);
                    decision_radius = up(decision_radius + term);
                }
            }
            if ((!valid[i] && !all_zero) || !isfinite(decision_radius)) goto unresolved;
            value = add(value, (box){-decision_radius, decision_radius});
            if (!finite_box(value)) goto unresolved;
            double midpoint = value.lo / 2.0 + value.hi / 2.0;
            size_t lo = 0, hi = grid_size - 1;
            while (lo < hi) {
                size_t mid = lo + (hi - lo) / 2;
                if (midpoint > row_boundary[mid]) lo = mid + 1;
                else hi = mid;
            }
            if ((lo != 0 && !(value.lo > row_boundary[lo - 1])) ||
                (lo != grid_size - 1 && !(value.hi <= row_boundary[lo]))) goto unresolved;
            double q = row_grid[lo];
            codes[row * width + i] = q;
            box difference = add((box){w, w}, (box){-q, -q});
            for (size_t k = 0; k < rank; ++k) {
                box feature = {lower[i * rank + k], upper[i * rank + k]};
                accum[k] = add(accum[k], multiply(difference, feature));
                if (!finite_box(accum[k])) goto unresolved;
            }
            counts[1]++;
            continue;
unresolved:
            failed[0] = (int64_t)row; failed[1] = (int64_t)i;
            free(accum); return 3;
        }
    }
    free(accum); return 0;
}
'''

_FLAGS = ('-std=c11', '-O3', '-shared', '-fPIC', '-fno-fast-math',
          '-ffp-contract=off', '-frounding-math', '-fexcess-precision=standard')
_NATIVE = None
_BUILD = None
_BUILD_DIRECTORY = None


def prepare_native_box():
    """Compile source once per process, recording source, binary, and compiler.

Existing binary caches are never loaded. Callers must charge compilation to
complete transactions. A warm call records zero new compilation time.
"""
    global _NATIVE, _BUILD, _BUILD_DIRECTORY
    if _NATIVE is not None:
        return dict(_BUILD, compiled_now=False, call_compile_elapsed_ns=0)
    started = time.perf_counter_ns()
    compiler = shutil.which('cc')
    if compiler is None:
        raise TokenBoxUnresolved('a local C compiler is required for the native box backend')
    directory = tempfile.TemporaryDirectory(prefix='native-box-v26-')
    source, binary = Path(directory.name) / 'native_box.c', Path(directory.name) / 'native_box.so'
    source.write_text(_C_SOURCE)
    try:
        command = [compiler, *_FLAGS, str(source), '-o', str(binary), '-lm']
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise TokenBoxUnresolved('strict native box compilation failed: ' + result.stderr[:2000])
        native = ctypes.CDLL(str(binary))
        native.nbc_runtime.restype = ctypes.c_int
        if native.nbc_runtime() != 1:
            raise TokenBoxUnresolved('native binary64 runtime premises failed')
        ptr = ctypes.POINTER(ctypes.c_double)
        native.nbc_run.argtypes = ([ctypes.c_size_t] * 4 + [ptr] * 5 +
            [ctypes.POINTER(ctypes.c_uint8)] + [ptr] * 3 +
            [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_uint64)])
        native.nbc_run.restype = ctypes.c_int
        native.nbc_probe.argtypes = [ctypes.c_int, ptr, ptr]
        native.nbc_probe.restype = ctypes.c_int
        version = subprocess.run([compiler, '--version'], capture_output=True, text=True, timeout=10)
        _BUILD = {
            'source_sha256': hashlib.sha256(_C_SOURCE.encode()).hexdigest(),
            'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'coefficient_source_sha256': hashlib.sha256(Path(preconditioned.__file__).read_bytes()).hexdigest(),
            'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'compiler': compiler, 'compiler_version': version.stdout.splitlines()[0],
            'flags': list(_FLAGS), 'compile_elapsed_ns': time.perf_counter_ns() - started,
        }
        _NATIVE, _BUILD_DIRECTORY = native, directory
    except BaseException:
        directory.cleanup()
        raise
    return dict(_BUILD, compiled_now=True, call_compile_elapsed_ns=_BUILD['compile_elapsed_ns'])


@dataclass(frozen=True)
class NativeBoxResult(preconditioned.PreconditionedBoxResult):
    backend: str = 'native_universal_box'
    native_attempted_decisions: int = 0
    native_certified_decisions: int = 0
    native_unresolved_row: int = -1
    native_unresolved_coordinate: int = -1
    python_universal_fallback: bool = False
    coefficient_elapsed_ns: int = 0
    native_elapsed_ns: int = 0
    fallback_elapsed_ns: int = 0
    compile_elapsed_ns: int = 0
    total_elapsed_ns: int = 0
    native_source_sha256: str = ''
    native_binary_sha256: str = ''
    native_compiler: str = ''
    coefficient_policy: str = 'ridge_then_preconditioned'
    native_passes: tuple = ()
    decisions_requiring_preconditioner_evaluated: bool = False


def _native_pass(weights, lower, upper, proposals, component, valid, grid, boundaries):
    arrays = [np.ascontiguousarray(x) for x in (weights, lower, upper, proposals, component)]
    valid = np.ascontiguousarray(valid, dtype=np.uint8)
    codes = np.empty(weights.shape, dtype=np.float64)
    failed, counts = np.full(2, -1, dtype=np.int64), np.zeros(2, dtype=np.uint64)
    ptr = ctypes.POINTER(ctypes.c_double)
    tick = time.perf_counter_ns()
    status = _NATIVE.nbc_run(weights.shape[0], weights.shape[1], lower.shape[1], grid.shape[1],
        *(x.ctypes.data_as(ptr) for x in arrays),
        valid.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
        *(x.ctypes.data_as(ptr) for x in (grid, boundaries, codes)),
        failed.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
        counts.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)))
    return status, codes, {
        'native_elapsed_ns': time.perf_counter_ns() - tick,
        'unresolved_row': int(failed[0]), 'unresolved_coordinate': int(failed[1]),
        'attempted_decisions': int(counts[0]), 'certified_decisions': int(counts[1]),
    }


def certify_native_dyadic_box(
        weights, lower, upper, scale_values=None, *, bits=4,
        significant_bits=24, ridge, normalization=1, candidate_codes=None,
        max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=16,
        allow_python_fallback=True):
    """Certify one exact model for all factors in a supplied finite box.

The componentwise bound is native. Native rejection may use the unchanged
Python universal verifier, including its independent ridge bound. This may
repeat coefficient construction; all repeated costs appear in timings.
Only singleton boxes use the common native exact point solver.
Caller-owned arrays must remain unchanged throughout the call.
"""
    started = time.perf_counter_ns()
    diagnostics = {'coefficient_policy': 'ridge_then_preconditioned', 'passes': [],
                   'compile_elapsed_ns': 0, 'fallback_elapsed_ns': 0}
    _check_runtime()
    for name, value in (('weights', weights), ('lower', lower), ('upper', upper)):
        _matrix(value, name)
    scales = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is not None:
        supplied = tuple(scale_values)
        if any(type(s) is not float for s in supplied) or supplied != scales:
            raise ValueError('scales must equal the canonical base-only dyadic scales')
    if lower.shape != upper.shape or lower.shape[0] != weights.shape[1]:
        raise ValueError('feature box dimensions differ from weight width')
    if np.any(lower > upper):
        raise ValueError('reversed feature box')
    if candidate_codes is not None:
        _matrix(candidate_codes, 'candidate_codes')
        if candidate_codes.shape != weights.shape:
            raise ValueError('candidate dimensions differ from weights')
    for value in (max_exact_rank, max_exact_coordinates, max_refinement_coordinates):
        if type(value) is not int or value < 0:
            raise ValueError('fallback limits must be nonnegative built-in integers')
    if type(allow_python_fallback) is not bool:
        raise ValueError('allow_python_fallback must be a built-in bool')
    lam, norm = _rational(ridge, 'ridge'), _rational(normalization, 'normalization')
    if lam <= 0 or norm <= 0:
        raise ValueError('ridge and normalization must be positive')
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.) != tiny or np.float64(2.) * tiny != tiny + tiny:
        raise TokenBoxUnresolved('gradual-underflow runtime check failed')
    uncertain = int(np.count_nonzero(lower != upper))
    common = dict(bits=bits, significant_bits=significant_bits, ridge=lam, normalization=norm,
        max_exact_rank=max_exact_rank, max_exact_coordinates=max_exact_coordinates,
        max_refinement_coordinates=max_refinement_coordinates)
    try:
        if not uncertain:
            tick = time.perf_counter_ns()
            point = native_ball_quantize_dyadic_rows(weights, lower, scales, **common)
            point_ns = time.perf_counter_ns() - tick
            base = preconditioned._result(_finish(point.codes, point.interval_decisions,
                point.exact_decisions, 0, point.max_coefficient_error_squared, candidate_codes))
            return NativeBoxResult(**base.__dict__, backend='native_singleton_point',
                fallback_elapsed_ns=point_ns, compile_elapsed_ns=point.compile_elapsed_ns,
                total_elapsed_ns=time.perf_counter_ns() - started,
                native_source_sha256=point.native_source_sha256,
                native_binary_sha256=point.native_binary_sha256, native_compiler=point.native_compiler)
        build = prepare_native_box()
        diagnostics['build'] = build
        diagnostics['compile_elapsed_ns'] = build['call_compile_elapsed_ns']
        grid, boundaries = _grid_arrays(scales, bits)
        used_preconditioner = False
        for policy in ('ridge_component', 'preconditioned_component'):
            tick = time.perf_counter_ns()
            with np.errstate(over='ignore', invalid='ignore', under='ignore', divide='ignore'):
                if policy == 'ridge_component':
                    proposals, errors = _box_coefficients(lower, upper, lam * norm)
                    # ||c-p||_2 <= rho implies |c_k-p_k| <= rho for each k.
                    # The exact-rational square-root check proves every rho.
                    radii = _coefficient_radii(errors)
                    component = np.broadcast_to(radii[:, None], lower.shape).copy()
                    valid = np.ones(weights.shape[1], dtype=bool)
                else:
                    proposals, errors, component, valid = preconditioned._coefficient_bounds(lower, upper, lam * norm)
                    used_preconditioner = True
            coefficient_ns = time.perf_counter_ns() - tick
            if (not all(np.all(np.isfinite(x)) for x in (proposals, errors, component))
                    or np.any(component < 0) or np.any(errors < 0)):
                raise TokenBoxUnresolved('coefficient bounds must be finite and nonnegative')
            status, codes, receipt = _native_pass(weights, lower, upper, proposals, component, valid, grid, boundaries)
            receipt.update(policy=policy, coefficient_elapsed_ns=coefficient_ns, status=status)
            diagnostics['passes'].append(receipt)
            if status != 3:
                break
        fallback_ns = 0
        if status in (1, 2):
            raise TokenBoxUnresolved('native runtime or allocation failure; no codes committed')
        if status == 3:
            if not allow_python_fallback:
                raise TokenBoxUnresolved(f"native box unresolved at row {receipt['unresolved_row']}, coordinate {receipt['unresolved_coordinate']}")
            tick = time.perf_counter_ns()
            try:
                base = preconditioned.certify_preconditioned_dyadic_box(
                    weights, lower, upper, scales, candidate_codes=candidate_codes, **common)
            finally:
                fallback_ns = time.perf_counter_ns() - tick
                diagnostics['fallback_elapsed_ns'] = fallback_ns
        elif status == 0:
            valid_count = int(np.count_nonzero(valid)) if used_preconditioner else 0
            base = preconditioned._result(_finish(codes, weights.size, 0, uncertain,
                float(np.max(errors)), candidate_codes), valid_count,
                weights.shape[1] - valid_count if used_preconditioner else 0, 0)
        else:
            raise TokenBoxUnresolved('unexpected native status; no codes committed')
        passes = diagnostics['passes']
        return NativeBoxResult(**base.__dict__, native_attempted_decisions=sum(p['attempted_decisions'] for p in passes),
            native_certified_decisions=sum(p['certified_decisions'] for p in passes),
            native_unresolved_row=receipt['unresolved_row'], native_unresolved_coordinate=receipt['unresolved_coordinate'],
            python_universal_fallback=status == 3,
            coefficient_elapsed_ns=sum(p['coefficient_elapsed_ns'] for p in passes),
            native_elapsed_ns=sum(p['native_elapsed_ns'] for p in passes),
            fallback_elapsed_ns=fallback_ns, compile_elapsed_ns=build['call_compile_elapsed_ns'],
            total_elapsed_ns=time.perf_counter_ns() - started,
            native_source_sha256=build['source_sha256'], native_binary_sha256=build['binary_sha256'],
            native_compiler=build['compiler_version'], native_passes=tuple(dict(p) for p in passes),
            decisions_requiring_preconditioner_evaluated=status == 3)
    except TokenBoxUnresolved as exc:
        diagnostics['total_elapsed_ns'] = time.perf_counter_ns() - started
        exc.native_diagnostics = diagnostics
        raise
    except LowRankUnresolved as exc:
        failure = TokenBoxUnresolved(str(exc))
        diagnostics['total_elapsed_ns'] = time.perf_counter_ns() - started
        failure.native_diagnostics = diagnostics
        raise failure from exc
