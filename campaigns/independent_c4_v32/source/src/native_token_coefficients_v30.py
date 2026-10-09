"""Strict native residual checks for unchanged exact token coefficients.

NumPy provides untrusted Sherman-Morrison proposals. Native scalar operations
construct directed suffix Gram bounds and verify each proposal independently.
The operation order matches the existing point coefficient reference.
No token is discarded and no approximate coefficient is accepted as exact.
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
from .low_rank_certified import LowRankUnresolved, _finite, _initial_gram
from .transformer_backend import _check_runtime


@dataclass(frozen=True)
class NativeCoefficientBudget:
    """Structural limits; these do not bound elapsed time or process RSS."""

    max_work_units: int = 2_000_000_000
    max_workspace_bytes: int = 512 * 2**20

    def __post_init__(self):
        for name in ('max_work_units', 'max_workspace_bytes'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f'{name} must be a positive built-in integer')


def assess_native_coefficients(width, tokens, *, budget=NativeCoefficientBudget()):
    """Describe the schedule before numerical arrays or compilation start."""
    if type(width) is not int or not 1 <= width <= 2**20:
        raise ValueError('width must be a built-in integer from 1 through 2**20')
    if type(tokens) is not int or not 0 <= tokens <= 2**20:
        raise ValueError('tokens must be a built-in integer from 0 through 2**20')
    if type(budget) is not NativeCoefficientBudget:
        raise TypeError('budget must be a NativeCoefficientBudget')
    work = width * tokens**2 + width * tokens + tokens**2
    # Includes Gram endpoints, nominal inverse updates, alignment copies,
    # returned immutable evidence, and conservative vector temporaries.
    memory = 8 * (24 * tokens**2 + 4 * width * tokens + 16 * tokens + 4 * width)
    reasons = []
    if work > budget.max_work_units:
        reasons.append('work proxy exceeds limit')
    if memory > budget.max_workspace_bytes:
        reasons.append('array allowance exceeds limit')
    return dict(width=width, tokens=tokens, work_units=work,
                explicit_array_bytes=memory, admitted=not reasons,
                refusal_reason='; '.join(reasons),
                whole_process_memory_guaranteed=False, wall_time_guaranteed=False)


_C_SOURCE = native_box._C_SOURCE + r'''

/* Match low_rank_certified._add, without an extra cancellation shortcut. */
static box ntc_add(box a, box b) {
    if (zero(a)) return b;
    if (zero(b)) return a;
    return (box){down(a.lo+b.lo), up(a.hi+b.hi)};
}

static box ntc_point_product(box a, double point) {
    if (point == 0.0 || zero(a)) return (box){0.0,0.0};
    double x = a.lo*point, y = a.hi*point;
    return (box){down(fmin(x,y)), up(fmax(x,y))};
}

/* Update one suffix and verify one already constructed proposal. */
int ntc_step(size_t tokens, const double *vector, const double *proposal,
             double *gram_lo, double *gram_hi, double beta_squared_lo,
             double *error_squared) {
    if (!nbc_runtime()) return 1;
    if (!isfinite(beta_squared_lo) || beta_squared_lo <= 0.0) return 2;
    for (size_t j = 0; j < tokens; ++j) {
        for (size_t k = 0; k <= j; ++k) {
            double a = vector[j], b = vector[k];
            double p = a*b;
            box outer = a == 0.0 || b == 0.0 ? (box){0.0,0.0} : (box){down(p),up(p)};
            box old = {gram_lo[j*tokens+k],gram_hi[j*tokens+k]};
            box value = ntc_add(old,outer);
            if (!finite_box(value)) return 3;
            gram_lo[j*tokens+k] = gram_lo[k*tokens+j] = value.lo;
            gram_hi[j*tokens+k] = gram_hi[k*tokens+j] = value.hi;
        }
    }
    double norm_squared = 0.0;
    for (size_t j = 0; j < tokens; ++j) {
        box product = {0.0,0.0};
        for (size_t k = 0; k < tokens; ++k) {
            box entry = {gram_lo[j*tokens+k],gram_hi[j*tokens+k]};
            product = ntc_add(product,ntc_point_product(entry,proposal[k]));
        }
        box residual = ntc_add((box){vector[j],vector[j]},(box){-product.hi,-product.lo});
        if (!finite_box(residual)) return 3;
        double magnitude = fmax(fabs(residual.lo),fabs(residual.hi));
        double term = magnitude == 0.0 ? 0.0 : up(magnitude*magnitude);
        if (term != 0.0) norm_squared = up(norm_squared+term);
    }
    double error = norm_squared == 0.0 ? 0.0 : up(norm_squared/beta_squared_lo);
    if (!isfinite(norm_squared) || !isfinite(error) || error < 0.0) return 3;
    *error_squared = error;
    return 0;
}
'''

_NATIVE = None
_BUILD = None
_DIRECTORY = None


def prepare_native_token_coefficients():
    """Compile strict source once per process; never load a saved binary."""
    global _NATIVE, _BUILD, _DIRECTORY
    if _NATIVE is not None:
        return dict(_BUILD, compiled_now=False, call_compile_elapsed_ns=0)
    started = time.perf_counter_ns()
    compiler = shutil.which('cc')
    if compiler is None:
        raise LowRankUnresolved('native token coefficients require a local C compiler')
    directory = tempfile.TemporaryDirectory(prefix='token-coefficients-v30-')
    source, binary = Path(directory.name)/'coefficients.c', Path(directory.name)/'coefficients.so'
    source.write_text(_C_SOURCE)
    try:
        command = [compiler,*native_box._FLAGS,str(source),'-o',str(binary),'-lm']
        completed = subprocess.run(command,capture_output=True,text=True,timeout=60)
        if completed.returncode:
            raise LowRankUnresolved('strict token coefficient compilation failed: '+completed.stderr[:2000])
        native = ctypes.CDLL(str(binary))
        native.nbc_runtime.restype = ctypes.c_int
        if native.nbc_runtime() != 1:
            raise LowRankUnresolved('native token coefficient runtime check failed')
        ptr = ctypes.POINTER(ctypes.c_double)
        native.ntc_step.argtypes = [ctypes.c_size_t]+[ptr]*4+[ctypes.c_double,ptr]
        native.ntc_step.restype = ctypes.c_int
        version = subprocess.run([compiler,'--version'],capture_output=True,text=True,timeout=10)
        _BUILD = dict(source_sha256=hashlib.sha256(_C_SOURCE.encode()).hexdigest(),
                      binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                      wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      compiler=compiler, compiler_version=version.stdout.splitlines()[0],
                      flags=list(native_box._FLAGS), compile_elapsed_ns=time.perf_counter_ns()-started)
        _NATIVE, _DIRECTORY = native, directory
    except BaseException:
        directory.cleanup()
        raise
    return dict(_BUILD, compiled_now=True, call_compile_elapsed_ns=_BUILD['compile_elapsed_ns'])


def _ptr(values):
    return values.ctypes.data_as(ctypes.POINTER(ctypes.c_double))


def _freeze(array):
    return np.frombuffer(array.tobytes(order='C'),dtype=np.float64).reshape(array.shape)


@dataclass(frozen=True)
class NativeCoefficientResult:
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
    native_source_sha256: str
    native_binary_sha256: str
    wrapper_source_sha256: str
    native_compiler: str
    backend: str = 'strict_native_token_coefficients_v30'
    guarantee: str = 'squared Euclidean error bounds for exact suffix coefficients'


def native_token_coefficient_enclosures(features,beta,*,budget=NativeCoefficientBudget()):
    """Return proposals and proved error squares for exact point features.

    Every feature denotes its exact binary64 value. The exact positive scalar
    beta equals ridge times the fixed target normalization. Inputs must remain
    unchanged. This function performs no quantization or empirical evaluation.
    It has no exact, preconditioned, or feature-replay fallback.
    """
    started = time.perf_counter_ns()
    if type(features) is not np.ndarray or features.dtype != np.float64 or features.ndim != 2:
        raise TypeError('features must be an ordinary binary64 NumPy matrix')
    width,tokens = features.shape
    admission = assess_native_coefficients(width,tokens,budget=budget)
    if not admission['admitted']:
        error = LowRankUnresolved('native coefficient admission refused: '+admission['refusal_reason'])
        error.coefficient_admission = admission
        raise error
    _check_runtime()
    if not np.all(np.isfinite(features)):
        raise ValueError('features must be finite')
    beta = _rational(beta,'beta')
    if beta <= 0:
        raise ValueError('beta must be positive')
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny*np.float64(1.) != tiny or tiny*np.float64(2.) != tiny+tiny:
        raise LowRankUnresolved('NumPy gradual-underflow runtime check failed')
    coefficients,errors = np.empty((width,tokens)),np.zeros(width)
    nominal_ns = native_ns = 0
    build = {}
    if tokens:
        features = np.require(features,dtype=np.float64,requirements=['C','A'])
        gram_lo,gram_hi,beta_squared_lo = _initial_gram(tokens,beta)
        build = prepare_native_token_coefficients()
        with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
            inverse = np.eye(tokens)/float(beta)
            _finite(inverse)
            for i in range(width-1,-1,-1):
                tick = time.perf_counter_ns()
                vector = features[i]
                candidate = inverse @ vector
                denominator = 1.0+float(vector @ candidate)
                if not np.isfinite(denominator) or denominator <= 0:
                    raise LowRankUnresolved('native coefficient inverse proposal failed')
                coefficient = candidate/denominator
                inverse -= np.outer(candidate,candidate)/denominator
                _finite(inverse,coefficient)
                coefficients[i] = coefficient
                nominal_ns += time.perf_counter_ns()-tick
                tick = time.perf_counter_ns()
                status = _NATIVE.ntc_step(tokens,_ptr(vector),_ptr(coefficients[i]),
                    _ptr(gram_lo),_ptr(gram_hi),beta_squared_lo,_ptr(errors[i:i+1]))
                native_ns += time.perf_counter_ns()-tick
                if status:
                    raise LowRankUnresolved(f'native token residual refused coordinate {i}: status={status}')
    return NativeCoefficientResult(_freeze(coefficients),_freeze(errors),width,tokens,
        admission['work_units'],admission['explicit_array_bytes'],nominal_ns,native_ns,
        build.get('call_compile_elapsed_ns',0),time.perf_counter_ns()-started,
        build.get('source_sha256',''),build.get('binary_sha256',''),
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),build.get('compiler_version',''))
