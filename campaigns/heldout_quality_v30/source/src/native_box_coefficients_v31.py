"""Strict native residual bounds for universal token-feature boxes.

Nominal inverse updates remain untrusted NumPy proposals. Directed C operations
preserve the reference interval Gram and residual schedule, including diagonal
square correlation. No point approximation replaces an uncertain feature box.
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

from . import native_box_certificate as native_box
from .exact_core import _rational
from .low_rank_certified import LowRankUnresolved, _initial_gram
from .token_box_certificate import TokenBoxUnresolved
from .transformer_backend import _check_runtime


@dataclass(frozen=True)
class NativeBoxCoefficientBudget:
    """Structural limits, not measured operation counts or whole-process RSS."""
    max_work_units: int = 2_000_000_000
    max_workspace_bytes: int = 512 * 2**20

    def __post_init__(self):
        for name in ('max_work_units', 'max_workspace_bytes'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(name+' must be a positive built-in integer')


def assess_native_box_coefficients(width, tokens, *, budget=NativeBoxCoefficientBudget()):
    """Admit before scanning values, constructing arrays, or compiling C."""
    if type(width) is not int or not 1 <= width <= 2**20:
        raise ValueError('width must be a built-in integer from 1 through 2**20')
    if type(tokens) is not int or not 0 <= tokens <= 2**20:
        raise ValueError('tokens must be a built-in integer from 0 through 2**20')
    if type(budget) is not NativeBoxCoefficientBudget:
        raise TypeError('budget must be NativeBoxCoefficientBudget')
    # Same O(width*tokens**2) structural coefficient proxy as the sparse policy.
    # The positive width term charges empty-token metadata and output work.
    work = width*tokens**2 + width*tokens + width
    # Includes inputs, alignment copies, endpoints, inverse update temporaries,
    # proposals, immutable output copies, and conservative vector temporaries.
    memory = 8*(28*tokens**2 + 8*width*tokens + 24*tokens + 8*width)
    reasons = []
    if work > budget.max_work_units:
        reasons.append('work proxy exceeds limit')
    if memory > budget.max_workspace_bytes:
        reasons.append('array allowance exceeds limit')
    return dict(width=width, tokens=tokens, work_units=work, explicit_array_bytes=memory,
        admitted=not reasons, refusal_reason='; '.join(reasons),
        whole_process_memory_guaranteed=False, wall_time_guaranteed=False)


_C_SOURCE = native_box._C_SOURCE + r'''

/* Deliberately match low_rank_certified._add: no cancellation shortcut. */
static box nbxc_add(box a, box b) {
    if (zero(a)) return b;
    if (zero(b)) return a;
    return (box){down(a.lo+b.lo), up(a.hi+b.hi)};
}

static box nbxc_point_product(box a, double point) {
    if (point == 0.0 || zero(a)) return (box){0.0,0.0};
    double x = a.lo*point, y = a.hi*point;
    return (box){down(fmin(x,y)), up(fmax(x,y))};
}

static box nbxc_outer(box a, box b, int diagonal) {
    if (!diagonal) return multiply(a,b);
    /* A diagonal product contains one shared variable, not two variables. */
    double x = a.lo*a.lo, y = a.hi*a.hi;
    double lower = down(fmin(x,y)), upper = up(fmax(x,y));
    if (a.lo <= 0.0 && a.hi >= 0.0) lower = 0.0;
    if (zero(a)) upper = 0.0;
    return (box){lower,upper};
}

/* One reverse-coordinate suffix update. All inputs have validated lengths. */
int nbxc_update(size_t tokens, const double *lower, const double *upper,
                double *gram_lo, double *gram_hi) {
    if (!nbc_runtime()) return 1;
    for (size_t j = 0; j < tokens; ++j) {
        box a = {lower[j],upper[j]};
        if (!finite_box(a)) return 2;
        for (size_t k = 0; k <= j; ++k) {
            box b = {lower[k],upper[k]};
            if (!finite_box(b)) return 2;
            box old = {gram_lo[j*tokens+k],gram_hi[j*tokens+k]};
            if (!finite_box(old)) return 2;
            box value = nbxc_add(old,nbxc_outer(a,b,j == k));
            if (!finite_box(value)) return 3;
            gram_lo[j*tokens+k] = gram_lo[k*tokens+j] = value.lo;
            gram_hi[j*tokens+k] = gram_hi[k*tokens+j] = value.hi;
        }
    }
    return 0;
}

/* Each row reduction follows ascending token coordinates exactly. */
int nbxc_residual(size_t tokens, const double *gram_lo, const double *gram_hi,
                  const double *rhs_lo, const double *rhs_hi, const double *proposal,
                  double beta_squared_lo, double *error_squared) {
    if (!nbc_runtime()) return 1;
    if (!isfinite(beta_squared_lo) || beta_squared_lo <= 0.0) return 2;
    for (size_t k = 0; k < tokens; ++k) if (!isfinite(proposal[k])) return 2;
    double norm_squared = 0.0;
    for (size_t j = 0; j < tokens; ++j) {
        box product = {0.0,0.0};
        for (size_t k = 0; k < tokens; ++k) {
            box entry = {gram_lo[j*tokens+k],gram_hi[j*tokens+k]};
            if (!finite_box(entry)) return 2;
            product = nbxc_add(product,nbxc_point_product(entry,proposal[k]));
            if (!finite_box(product)) return 3;
        }
        box rhs = {rhs_lo[j],rhs_hi[j]};
        if (!finite_box(rhs)) return 2;
        box residual = nbxc_add(rhs,(box){-product.hi,-product.lo});
        if (!finite_box(residual)) return 3;
        double magnitude = fmax(fabs(residual.lo),fabs(residual.hi));
        double term = magnitude == 0.0 ? 0.0 : up(magnitude*magnitude);
        if (term != 0.0) norm_squared = up(norm_squared+term);
        if (!isfinite(norm_squared)) return 3;
    }
    double error = norm_squared == 0.0 ? 0.0 : up(norm_squared/beta_squared_lo);
    if (!isfinite(error) || error < 0.0) return 3;
    *error_squared = error;
    return 0;
}

/* Exposed only for exact software checks of correlated square intervals. */
int nbxc_outer_probe(const double *input, int diagonal, double *output) {
    if (!nbc_runtime()) return 1;
    box a = {input[0],input[1]}, b = {input[2],input[3]};
    if (!finite_box(a) || !finite_box(b) || (diagonal != 0 && diagonal != 1)) return 2;
    box result = nbxc_outer(a,b,diagonal);
    output[0] = result.lo; output[1] = result.hi;
    return finite_box(result) ? 0 : 3;
}
'''

_NATIVE = None
_BUILD = None
_DIRECTORY = None


def prepare_native_box_coefficients():
    """Compile strict source once per process; never trust a saved binary."""
    global _NATIVE, _BUILD, _DIRECTORY
    if _NATIVE is not None:
        return dict(_BUILD, compiled_now=False, call_compile_elapsed_ns=0)
    started = time.perf_counter_ns()
    compiler = shutil.which('cc')
    if compiler is None:
        raise TokenBoxUnresolved('native box coefficients require a local C compiler')
    directory = tempfile.TemporaryDirectory(prefix='box-coefficients-v31-')
    source, binary = Path(directory.name)/'coefficients.c', Path(directory.name)/'coefficients.so'
    source.write_text(_C_SOURCE)
    try:
        command = [compiler,*native_box._FLAGS,str(source),'-o',str(binary),'-lm']
        completed = subprocess.run(command,capture_output=True,text=True,timeout=60)
        if completed.returncode:
            raise TokenBoxUnresolved('strict box coefficient compilation failed: '+completed.stderr[:2000])
        native = ctypes.CDLL(str(binary))
        native.nbc_runtime.restype = ctypes.c_int
        if native.nbc_runtime() != 1:
            raise TokenBoxUnresolved('native box coefficient runtime check failed')
        ptr = ctypes.POINTER(ctypes.c_double)
        native.nbxc_update.argtypes = [ctypes.c_size_t]+[ptr]*4
        native.nbxc_update.restype = ctypes.c_int
        native.nbxc_residual.argtypes = [ctypes.c_size_t]+[ptr]*5+[ctypes.c_double,ptr]
        native.nbxc_residual.restype = ctypes.c_int
        native.nbxc_outer_probe.argtypes = [ptr,ctypes.c_int,ptr]
        native.nbxc_outer_probe.restype = ctypes.c_int
        version = subprocess.run([compiler,'--version'],capture_output=True,text=True,timeout=10)
        _BUILD = dict(source_sha256=hashlib.sha256(_C_SOURCE.encode()).hexdigest(),
            binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            compiler=compiler,compiler_version=version.stdout.splitlines()[0],flags=list(native_box._FLAGS),
            compile_elapsed_ns=time.perf_counter_ns()-started)
        _NATIVE, _DIRECTORY = native, directory
    except BaseException:
        directory.cleanup()
        raise
    return dict(_BUILD,compiled_now=True,call_compile_elapsed_ns=_BUILD['compile_elapsed_ns'])


def _ptr(values):
    return values.ctypes.data_as(ctypes.POINTER(ctypes.c_double))


def _freeze(array):
    return np.frombuffer(array.tobytes(order='C'),dtype=np.float64).reshape(array.shape)


@dataclass(frozen=True)
class NativeBoxCoefficientResult:
    coefficients: np.ndarray
    errors: np.ndarray
    width: int
    tokens: int
    work_units: int
    explicit_array_bytes: int
    nominal_elapsed_ns: int
    native_elapsed_ns: int
    compile_elapsed_ns: int
    total_elapsed_ns: int
    zero_proposal_fallbacks: int
    native_source_sha256: str
    native_binary_sha256: str
    wrapper_source_sha256: str
    native_compiler: str
    backend: str = 'strict_native_universal_box_coefficients_v31'
    guarantee: str = 'squared Euclidean coefficient error bounds for every matrix inside the supplied box'
    native_build_manifest: object = None


def native_box_coefficient_enclosures(lower,upper,beta,*,budget=NativeBoxCoefficientBudget()):
    """Return common proposals and universal squared coefficient error bounds.

All endpoints denote their exact binary64 values. Beta is the exact positive
ridge-normalization product. Inputs must remain unchanged during execution.
No rational solve, feature replay, or point-feature fallback is available.
"""
    started = time.perf_counter_ns()
    for name,array in (('lower',lower),('upper',upper)):
        if type(array) is not np.ndarray or array.dtype != np.float64 or array.ndim != 2:
            raise TypeError(name+' must be an ordinary binary64 NumPy matrix')
    if lower.shape != upper.shape:
        raise ValueError('feature bound dimensions differ')
    width,tokens = lower.shape
    admission = assess_native_box_coefficients(width,tokens,budget=budget)
    if not admission['admitted']:
        error = TokenBoxUnresolved('native box coefficient admission refused: '+admission['refusal_reason'])
        error.coefficient_admission = admission
        raise error
    _check_runtime()
    if not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)):
        raise ValueError('feature bounds must be finite')
    if np.any(lower > upper):
        raise ValueError('reversed feature box')
    beta = _rational(beta,'beta')
    if beta <= 0:
        raise ValueError('beta must be positive')
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny*np.float64(1.) != tiny or tiny*np.float64(2.) != tiny+tiny:
        raise TokenBoxUnresolved('NumPy gradual-underflow runtime check failed')
    coefficients,errors = np.zeros((width,tokens)),np.zeros(width)
    nominal_ns = native_ns = zero_fallbacks = 0
    build = {}
    diagnostics = dict(admission=admission,completed_coordinates=0,failed_coordinate=None,
        nominal_elapsed_ns=0,native_elapsed_ns=0,compile_elapsed_ns=0,zero_proposal_fallbacks=0)
    try:
        if tokens:
            lower = np.require(lower,dtype=np.float64,requirements=['C','A'])
            upper = np.require(upper,dtype=np.float64,requirements=['C','A'])
            with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
                gram_lo,gram_hi,beta_squared_lo = _initial_gram(tokens,beta)
                tick = time.perf_counter_ns()
                try:
                    build = prepare_native_box_coefficients()
                except LowRankUnresolved:
                    diagnostics['compile_elapsed_ns'] = time.perf_counter_ns()-tick
                    diagnostics['compilation_completed'] = False
                    raise
                diagnostics['build'] = build
                diagnostics['compile_elapsed_ns'] = build['call_compile_elapsed_ns']
                diagnostics['compilation_completed'] = True
                inverse = np.eye(tokens)/float(beta)
                for i in range(width-1,-1,-1):
                    diagnostics['failed_coordinate'] = i
                    tick = time.perf_counter_ns()
                    status = _NATIVE.nbxc_update(tokens,_ptr(lower[i]),_ptr(upper[i]),
                        _ptr(gram_lo),_ptr(gram_hi))
                    native_ns += time.perf_counter_ns()-tick
                    if status:
                        raise TokenBoxUnresolved(f'native interval Gram refused coordinate {i}: status={status}')
                    tick = time.perf_counter_ns()
                    midpoint = lower[i]/2.0+upper[i]/2.0
                    vector = inverse @ midpoint
                    denominator = 1.0+float(midpoint @ vector)
                    if np.isfinite(denominator) and denominator > 0 and np.all(np.isfinite(vector)):
                        proposal = vector/denominator
                        updated = inverse-np.outer(vector,vector)/denominator
                        if np.all(np.isfinite(proposal)) and np.all(np.isfinite(updated)):
                            inverse = updated
                        else:
                            inverse,proposal = np.zeros_like(inverse),np.zeros(tokens)
                            zero_fallbacks += 1
                    else:
                        inverse,proposal = np.zeros_like(inverse),np.zeros(tokens)
                        zero_fallbacks += 1
                    coefficients[i] = proposal
                    nominal_ns += time.perf_counter_ns()-tick
                    tick = time.perf_counter_ns()
                    status = _NATIVE.nbxc_residual(tokens,_ptr(gram_lo),_ptr(gram_hi),
                        _ptr(lower[i]),_ptr(upper[i]),_ptr(coefficients[i]),beta_squared_lo,_ptr(errors[i:i+1]))
                    native_ns += time.perf_counter_ns()-tick
                    if status:
                        raise TokenBoxUnresolved(f'native universal residual refused coordinate {i}: status={status}')
                    diagnostics['completed_coordinates'] += 1
                diagnostics['failed_coordinate'] = None
    except LowRankUnresolved as exc:
        diagnostics.update(nominal_elapsed_ns=nominal_ns,native_elapsed_ns=native_ns,
            zero_proposal_fallbacks=zero_fallbacks,total_elapsed_ns=time.perf_counter_ns()-started)
        exc.coefficient_diagnostics = diagnostics
        raise
    return NativeBoxCoefficientResult(_freeze(coefficients),_freeze(errors),width,tokens,
        admission['work_units'],admission['explicit_array_bytes'],nominal_ns,native_ns,
        build.get('call_compile_elapsed_ns',0),time.perf_counter_ns()-started,zero_fallbacks,
        build.get('source_sha256',''),build.get('binary_sha256',''),
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),build.get('compiler_version',''),
        native_build_manifest=dict(build))
