"""Verified feature-space certificates for the unchanged exact dyadic target.

The feature Gram matrix has width-by-width dimensions. No token-by-token
matrix is allocated. Floating inverse updates are proposals only. Directed
residual bounds certify all accepted coefficients, including uncertain boxes.
Compilation and all preparation belong inside complete transaction costs.
"""
from __future__ import annotations

import ctypes
from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import numpy as np

from . import native_box_certificate as native_box
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from .exact_core import _rational
from .low_rank_certified import (
    LowRankUnresolved, _add, _down, _finite, _initial_gram,
    _multiply_point, _norm_squared_upper, _point_bounds, _up,
)
from .token_box_certificate import (
    TokenBoxResult, TokenBoxUnresolved, _finish, _matrix, _multiply, _outer_bounds,
)
from .transformer_backend import _check_runtime


class PrimalUnresolved(TokenBoxUnresolved):
    """The bounded primal attempt produced no certified complete model."""


@dataclass(frozen=True)
class PrimalBudget:
    """Admission limits, not a wall-time or operating-system memory limit."""
    max_workspace_bytes: int = 256 * 1024 * 1024
    max_work_units: int = 100_000_000

    def __post_init__(self):
        for name in ('max_workspace_bytes', 'max_work_units'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f'{name} must be a positive built-in integer')


@dataclass(frozen=True)
class PrimalAdmission:
    rows: int
    width: int
    tokens: int
    work_units: int
    explicit_array_bytes: int
    coefficient_workspace_bytes: int


def assess_primal_budget(*, rows, width, tokens, bits=4, budget=PrimalBudget()):
    """Reject oversized structural plans without allocating numerical arrays.

    Work units are d*d*T+d*d*d+m*d*d+2*m*2**bits. They are not FLOPs.
    The byte envelope includes conservative explicit-array allowances and
    possible aligned input copies. It excludes caller residency, allocator
    overhead, compiler memory, and opaque BLAS workspace. Use a process cap.
    """
    for name, value, minimum in (('rows', rows, 1), ('width', width, 1), ('tokens', tokens, 0)):
        if type(value) is not int or value < minimum:
            raise ValueError(f'{name} must be a built-in integer >= {minimum}')
    if type(bits) is not int or not 2 <= bits <= 8:
        raise ValueError('bits must be a built-in integer between 2 and 8')
    if type(budget) is not PrimalBudget:
        raise TypeError('budget must be a PrimalBudget')
    work = width * width * tokens + width**3 + rows * width**2 + 2 * rows * (1 << bits)
    coefficient = 8 * (40 * width**2 + 24 * width)
    memory = coefficient + 8 * (4 * width * tokens + 10 * rows * width
                                 + 8 * rows * (1 << bits) + 24 * rows)
    reasons = []
    if work > budget.max_work_units:
        reasons.append(f'work {work} > {budget.max_work_units}')
    if memory > budget.max_workspace_bytes:
        reasons.append(f'workspace {memory} > {budget.max_workspace_bytes}')
    return dict(asdict(PrimalAdmission(rows, width, tokens, work, memory, coefficient)),
                admitted=not reasons, refusal_reason='; '.join(reasons))


# Reuse the reviewed strict interval primitives and row verifier. The added
# kernels keep all trusted arithmetic in elementary scalar operations.
_C_SOURCE = native_box._C_SOURCE + r'''

static double pos_add(double a, double b) {
    if (a == 0.0) return b;
    if (b == 0.0) return a;
    return up(a + b);
}
static double pos_mul(double a, double b) {
    if (a == 0.0 || b == 0.0) return 0.0;
    return up(a * b);
}
static double norm_term(box a) {
    double magnitude = fmax(fabs(a.lo), fabs(a.hi));
    return pos_mul(magnitude, magnitude);
}
static int sqrt_upper(double squared, double *bound) {
    if (!isfinite(squared) || squared < 0.0) return 0;
    if (squared == 0.0) { *bound = 0.0; return 1; }
    int exponent;
    frexp(squared, &exponent);
    if (exponent % 2 != 0) --exponent;
    double normalized = scalbn(squared, -exponent); /* Exact and normal. */
    double root = sqrt(normalized);  /* An untrusted proposal. */
    for (int attempt = 0; attempt < 8; ++attempt) {
        if (!isfinite(root) || root < 0.0) return 0;
        if (down(root * root) >= normalized) {
            *bound = scalbn(root, exponent / 2); /* Exact normal rescaling. */
            return isfinite(*bound);
        }
        root = up(root);
    }
    return 0;
}

int npc_gram(size_t width, size_t tokens, const double *lower,
             const double *upper, double *gram_lo, double *gram_hi) {
    if (!nbc_runtime()) return 1;
    for (size_t h = 0; h < width; ++h) {
        for (size_t j = 0; j <= h; ++j) {
            box value = {0.0, 0.0};
            for (size_t t = 0; t < tokens; ++t) {
                box a = {lower[h*tokens+t], upper[h*tokens+t]};
                box b = {lower[j*tokens+t], upper[j*tokens+t]};
                box product;
                if (h != j) product = multiply(a, b);
                else if (zero(a)) product = (box){0.0, 0.0};
                else {
                    double x = a.lo*a.lo, y = a.hi*a.hi;
                    product.lo = a.lo <= 0.0 && a.hi >= 0.0 ? 0.0 : fmax(0.0, down(fmin(x,y)));
                    product.hi = up(fmax(x,y));
                }
                value = add(value, product);
                if (!finite_box(value)) return 2;
            }
            /* Every realized diagonal is nonnegative. */
            if (h == j && value.lo < 0.0) value.lo = 0.0;
            gram_lo[h*width+j] = gram_lo[j*width+h] = value.lo;
            gram_hi[h*width+j] = gram_hi[j*width+h] = value.hi;
        }
    }
    return 0;
}

int npc_column(size_t width, size_t i, const double *gram_lo,
               const double *gram_hi, const double *proposal,
               double beta_lo, double beta_hi, double beta_squared_lo,
               double *center, double *radius, double *diagnostics) {
    if (!nbc_runtime()) return 1;
    double residual_squared = 0.0;
    for (size_t h = i; h < width; ++h) {
        box value = {0.0, 0.0};
        for (size_t j = i; j < width; ++j) {
            box entry = {gram_lo[h*width+j], gram_hi[h*width+j]};
            if (h == j) entry = add(entry, (box){beta_lo,beta_hi});
            double p = proposal[j-i];
            value = add(value, multiply(entry, (box){p,p}));
        }
        double rhs = h == i ? 1.0 : 0.0;
        box residual = add((box){rhs,rhs}, (box){-value.hi,-value.lo});
        if (!finite_box(residual)) return 2;
        residual_squared = pos_add(residual_squared, norm_term(residual));
    }
    if (!isfinite(residual_squared)) return 2;
    double error_squared = residual_squared == 0.0 ? 0.0 : up(residual_squared / beta_squared_lo);
    if (!isfinite(error_squared)) return 2;
    diagnostics[0] = residual_squared;
    diagnostics[1] = error_squared;
    for (size_t h = 0; h < i; ++h) {
        box value = {0.0,0.0};
        double row_squared = 0.0;
        for (size_t j = i; j < width; ++j) {
            box entry = {gram_lo[h*width+j],gram_hi[h*width+j]};
            double p = proposal[j-i];
            value = add(value, multiply(entry,(box){p,p}));
            row_squared = pos_add(row_squared, norm_term(entry));
        }
        if (!finite_box(value)) return 2;
        /* Two independent bounds. Infinity in one bound can be discarded. */
        double ridge_bound = pos_mul(row_squared, error_squared);
        double leverage_bound = pos_mul(gram_hi[h*width+h], residual_squared);
        if (leverage_bound != 0.0) leverage_bound = up(leverage_bound / beta_lo);
        if (leverage_bound != 0.0) leverage_bound = up(leverage_bound * 0.25);
        double squared = fmin(ridge_bound, leverage_bound);
        double norm_radius;
        if (!sqrt_upper(squared, &norm_radius)) return 2;
        double midpoint = value.lo / 2.0 + value.hi / 2.0;
        double dot_radius = value.lo == value.hi && midpoint == value.lo ? 0.0 :
            fmax(up(midpoint-value.lo),up(value.hi-midpoint));
        double total_radius = pos_add(dot_radius,norm_radius);
        if (!isfinite(midpoint) || !isfinite(total_radius) || total_radius < 0.0) return 2;
        center[h] = midpoint;
        radius[h] = total_radius;
    }
    return 0;
}
'''

_NATIVE = None
_BUILD = None
_DIRECTORY = None


def prepare_primal_native():
    """Compile strict native kernels once. Never load an existing binary cache."""
    global _NATIVE, _BUILD, _DIRECTORY
    if _NATIVE is not None:
        return dict(_BUILD, compiled_now=False, call_compile_elapsed_ns=0)
    tick = time.perf_counter_ns()
    compiler = shutil.which('cc')
    if compiler is None:
        raise PrimalUnresolved('native primal certification requires a local C compiler')
    directory = tempfile.TemporaryDirectory(prefix='primal-v30-')
    source, binary = Path(directory.name)/'primal.c', Path(directory.name)/'primal.so'
    source.write_text(_C_SOURCE)
    try:
        command = [compiler, *native_box._FLAGS, str(source), '-o', str(binary), '-lm']
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if completed.returncode:
            raise PrimalUnresolved('strict primal compilation failed: ' + completed.stderr[:2000])
        native = ctypes.CDLL(str(binary))
        native.nbc_runtime.restype = ctypes.c_int
        if native.nbc_runtime() != 1:
            raise PrimalUnresolved('native primal binary64 runtime check failed')
        ptr = ctypes.POINTER(ctypes.c_double)
        native.npc_gram.argtypes = [ctypes.c_size_t]*2 + [ptr]*4
        native.npc_gram.restype = ctypes.c_int
        native.npc_column.argtypes = [ctypes.c_size_t]*2 + [ptr]*3 + [ctypes.c_double]*3 + [ptr]*3
        native.npc_column.restype = ctypes.c_int
        native.nbc_run.argtypes = ([ctypes.c_size_t]*4 + [ptr]*5 +
            [ctypes.POINTER(ctypes.c_uint8)] + [ptr]*3 +
            [ctypes.POINTER(ctypes.c_int64),ctypes.POINTER(ctypes.c_uint64)])
        native.nbc_run.restype = ctypes.c_int
        version = subprocess.run([compiler,'--version'],capture_output=True,text=True,timeout=10)
        _BUILD = dict(source_sha256=hashlib.sha256(_C_SOURCE.encode()).hexdigest(),
            binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            compiler=compiler, compiler_version=version.stdout.splitlines()[0],
            flags=list(native_box._FLAGS), compile_elapsed_ns=time.perf_counter_ns()-tick)
        _NATIVE, _DIRECTORY = native, directory
    except BaseException:
        directory.cleanup()
        raise
    return dict(_BUILD, compiled_now=True, call_compile_elapsed_ns=_BUILD['compile_elapsed_ns'])


def _ptr(values):
    return values.ctypes.data_as(ctypes.POINTER(ctypes.c_double))


def _gram_bounds(lower, upper, *, arithmetic_backend):
    width, tokens = lower.shape
    lo, hi = np.zeros((width,width)), np.zeros((width,width))
    if arithmetic_backend == 'native':
        status = _NATIVE.npc_gram(width,tokens,_ptr(lower),_ptr(upper),_ptr(lo),_ptr(hi))
        if status:
            raise PrimalUnresolved(f'primal Gram enclosure failed: status={status}')
    else:
        for k in range(tokens):
            term_lo, term_hi = _outer_bounds(lower[:,k], upper[:,k])
            lo, hi = _add(lo,hi,term_lo,term_hi)
            _finite(lo,hi)
        index = np.arange(width)
        lo[index,index] = np.maximum(0.0,lo[index,index])
    return lo,hi


def _sqrt_upper(squared):
    """Verify a proposed square-root upper bound by its directed square."""
    if not np.isfinite(squared) or squared < 0:
        raise PrimalUnresolved('nonfinite or negative squared radius')
    if squared == 0:
        return 0.0
    _,exponent = math.frexp(squared)
    exponent -= exponent % 2
    normalized = math.ldexp(squared,-exponent)
    root = float(np.sqrt(normalized))
    for _ in range(8):
        if not np.isfinite(root) or root < 0:
            break
        if float(_down(root*root)) >= normalized:
            return math.ldexp(root,exponent//2)
        root = float(_up(root))
    raise PrimalUnresolved('proposed radius failed its directed square check')


def _positive_multiply(a,b):
    return 0.0 if a == 0 or b == 0 else float(_up(a*b))


def _column_python(gram_lo,gram_hi,i,proposal,beta_lo,beta_hi,beta_squared_lo):
    width = len(gram_lo)
    lo,hi = np.zeros(width-i),np.zeros(width-i)
    for k in range(i,width):
        a,b = gram_lo[i:,k].copy(),gram_hi[i:,k].copy()
        a[k-i],b[k-i] = _add(a[k-i],b[k-i],beta_lo,beta_hi)
        term_lo,term_hi = _multiply_point(a,b,proposal[k-i])
        lo,hi = _add(lo,hi,term_lo,term_hi)
    rhs = np.zeros(width-i)
    rhs[0] = 1.0
    rlo,rhi = _add(rhs,rhs,-hi,-lo)
    eta_squared = float(_norm_squared_upper(rlo,rhi))
    error_squared = 0.0 if eta_squared == 0 else float(_up(eta_squared/beta_squared_lo))
    _finite(rlo,rhi,eta_squared,error_squared)
    center,radius = np.zeros(width),np.zeros(width)
    for h in range(i):
        lo = hi = 0.0
        for k in range(i,width):
            term_lo,term_hi = _multiply_point(gram_lo[h,k],gram_hi[h,k],proposal[k-i])
            lo,hi = _add(lo,hi,term_lo,term_hi)
        _finite(lo,hi)
        row_squared = float(_norm_squared_upper(gram_lo[h,i:],gram_hi[h,i:]))
        ridge_bound = _positive_multiply(row_squared,error_squared)
        leverage_bound = _positive_multiply(float(gram_hi[h,h]),eta_squared)
        if leverage_bound:
            leverage_bound = float(_up(leverage_bound/beta_lo))
        if leverage_bound:
            leverage_bound = float(_up(leverage_bound*.25))
        norm_radius = _sqrt_upper(min(ridge_bound,leverage_bound))
        midpoint = float(lo/2.0+hi/2.0)
        dot_radius = (0.0 if lo == hi and midpoint == lo else
                      max(float(_up(midpoint-lo)),float(_up(hi-midpoint))))
        total = norm_radius if dot_radius == 0 else (dot_radius if norm_radius == 0
                                                   else float(_up(dot_radius+norm_radius)))
        _finite(midpoint,total)
        center[h],radius[h] = midpoint,total
    return center,radius,eta_squared,error_squared


def _suffix_proposal(nominal,inverse,i,beta):
    """Reverse block-inverse proposal. Its values never constitute evidence."""
    vector = inverse[i+1:,i+1:] @ nominal[i+1:,i]
    schur = nominal[i,i] + beta - nominal[i,i+1:] @ vector
    if np.isfinite(schur) and schur > 0 and np.all(np.isfinite(vector)):
        reciprocal = 1.0/schur
        proposal = np.concatenate((np.array([reciprocal]),-vector*reciprocal))
        updated = inverse[i+1:,i+1:] + np.outer(vector,vector)*reciprocal
        if np.all(np.isfinite(proposal)) and np.all(np.isfinite(updated)):
            inverse[i+1:,i+1:] = updated
            inverse[i,i:] = inverse[i:,i] = proposal
            return proposal,False
    inverse[i:,i:] = 0.0
    return np.zeros(len(nominal)-i),True


@dataclass(frozen=True)
class PrimalCoefficients:
    centers: np.ndarray
    radii: np.ndarray
    max_residual_squared: float
    max_solution_error_squared: float
    proposal_resets: int


def _coefficient_bounds(lower,upper,beta,*,arithmetic_backend):
    width = lower.shape[0]
    beta_lo,beta_hi = _point_bounds(beta)
    # This shared guard establishes a strictly positive downward square.
    _,_,beta_squared_lo = _initial_gram(0,beta)
    gram_lo,gram_hi = _gram_bounds(lower,upper,arithmetic_backend=arithmetic_backend)
    nominal = gram_lo/2.0+gram_hi/2.0
    inverse = np.zeros((width,width))
    centers,radii = np.zeros((width,width)),np.zeros((width,width))
    residual_max,error_max,resets = 0.0,0.0,0
    for i in range(width-1,0,-1):
        proposal,reset = _suffix_proposal(nominal,inverse,i,float(beta))
        resets += int(reset)
        if arithmetic_backend == 'native':
            diagnostic = np.zeros(2)
            status = _NATIVE.npc_column(width,i,_ptr(gram_lo),_ptr(gram_hi),_ptr(proposal),
                beta_lo,beta_hi,beta_squared_lo,_ptr(centers[i]),_ptr(radii[i]),_ptr(diagnostic))
            if status:
                raise PrimalUnresolved(f'primal coefficient enclosure failed at coordinate {i}: status={status}')
            eta_squared,error_squared = map(float,diagnostic)
        else:
            centers[i],radii[i],eta_squared,error_squared = _column_python(
                gram_lo,gram_hi,i,proposal,beta_lo,beta_hi,beta_squared_lo)
        residual_max,error_max = max(residual_max,eta_squared),max(error_max,error_squared)
    return PrimalCoefficients(centers,radii,residual_max,error_max,resets)


def _rows_python(weights,centers,radii,grid,boundaries):
    rows,width = weights.shape
    codes = np.empty_like(weights)
    diff_lo,diff_hi = np.zeros_like(weights),np.zeros_like(weights)
    for i in range(width):
        lo,hi = weights[:,i].copy(),weights[:,i].copy()
        for h in range(i):
            a,b = _add(centers[i,h],centers[i,h],-radii[i,h],radii[i,h])
            term_lo,term_hi = _multiply(diff_lo[:,h],diff_hi[:,h],a,b)
            lo,hi = _add(lo,hi,term_lo,term_hi)
        _finite(lo,hi)
        midpoint = lo/2.0+hi/2.0
        indices = np.count_nonzero(midpoint[:,None] > boundaries,axis=1)
        row = np.arange(rows)
        lower = boundaries[row,np.maximum(indices-1,0)]
        upper = boundaries[row,np.minimum(indices,boundaries.shape[1]-1)]
        safe = ((indices == 0)|(lo > lower)) & ((indices == boundaries.shape[1])|(hi <= upper))
        if not np.all(safe):
            first = int(np.flatnonzero(~safe)[0])
            raise PrimalUnresolved(f'primal rounding cell unresolved at coordinate {i}, row {first}')
        codes[:,i] = grid[row,indices]
        diff_lo[:,i],diff_hi[:,i] = _add(weights[:,i],weights[:,i],-codes[:,i],-codes[:,i])
    return codes,dict(attempted_decisions=weights.size,certified_decisions=weights.size,native_elapsed_ns=0)


def _rows_native(weights,centers,radii,grid,boundaries):
    rows,width = weights.shape
    identity = np.eye(width)
    valid = np.ones(width,dtype=np.uint8)
    codes = np.empty_like(weights)
    failed,counts = np.full(2,-1,dtype=np.int64),np.zeros(2,dtype=np.uint64)
    started = time.perf_counter_ns()
    status = _NATIVE.nbc_run(rows,width,width,grid.shape[1],_ptr(weights),_ptr(identity),_ptr(identity),
        _ptr(centers),_ptr(radii),valid.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
        _ptr(grid),_ptr(boundaries),_ptr(codes),
        failed.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),counts.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)))
    if status:
        raise PrimalUnresolved(f'primal native row verification failed: status={status}, row={failed[0]}, coordinate={failed[1]}')
    return codes,dict(attempted_decisions=int(counts[0]),certified_decisions=int(counts[1]),
                     native_elapsed_ns=time.perf_counter_ns()-started)


@dataclass(frozen=True)
class PrimalBoxResult(TokenBoxResult):
    backend: str = 'verified_primal_dyadic_box'
    arithmetic_backend: str = 'native'
    width: int = 0
    tokens: int = 0
    work_units: int = 0
    explicit_array_bytes: int = 0
    coefficient_workspace_bytes: int = 0
    proposal_resets: int = 0
    max_residual_squared: float = 0.0
    coefficient_elapsed_ns: int = 0
    native_elapsed_ns: int = 0
    compile_elapsed_ns: int = 0
    total_elapsed_ns: int = 0
    native_source_sha256: str = ''
    native_binary_sha256: str = ''
    native_compiler: str = ''
    native_attempted_decisions: int = 0
    native_certified_decisions: int = 0


def certify_primal_dyadic_box(weights,lower,upper,scale_values=None,*,bits=4,
        significant_bits=24,ridge,normalization=1,candidate_codes=None,
        budget=PrimalBudget(),arithmetic_backend='native'):
    """Certify the existing exact target using a feature-space Gram enclosure.

    H = ridge*I + X*X.T/normalization for every lower <= X <= upper.
    The canonical base-only dyadic grid and lower-code ties stay unchanged.
    No exact point fallback or token-space allocation occurs in this method.
    Nontrivial exact ties can remain unresolved. The caller must then stop or
    use a separately bounded exact backend. Caller inputs must remain fixed.
    """
    started = time.perf_counter_ns()
    _check_runtime()
    if arithmetic_backend not in ('native','python'):
        raise ValueError('arithmetic_backend must be native or python')
    # Check shapes before finite scans and before coefficient allocations.
    for name,value in (('weights',weights),('lower',lower),('upper',upper)):
        if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 2:
            raise TypeError(f'{name} must be an ordinary binary64 NumPy matrix')
    if lower.shape != upper.shape or weights.shape[1] != lower.shape[0]:
        raise ValueError('feature box dimensions must match the weight width')
    admission = assess_primal_budget(rows=weights.shape[0],width=weights.shape[1],
        tokens=lower.shape[1],bits=bits,budget=budget)
    if not admission['admitted']:
        raise PrimalUnresolved('primal admission refused: ' + admission['refusal_reason'])
    for name,value in (('weights',weights),('lower',lower),('upper',upper)):
        _matrix(value,name)
    if np.any(lower > upper):
        raise ValueError('lower must not exceed upper')
    if candidate_codes is not None:
        _matrix(candidate_codes,'candidate_codes')
        if candidate_codes.shape != weights.shape:
            raise ValueError('candidate codes must match weights')
    expected = dyadic_row_scales(weights,bits,significant_bits)
    if scale_values is not None:
        supplied = tuple(scale_values)
        if any(type(value) is not float for value in supplied) or supplied != expected:
            raise ValueError('scales must equal the canonical base-only dyadic row scales')
    lam,norm = _rational(ridge,'ridge'),_rational(normalization,'normalization')
    if lam <= 0 or norm <= 0:
        raise ValueError('ridge and normalization must be positive')
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny*np.float64(1.) != tiny or tiny*np.float64(2.) != tiny+tiny:
        raise PrimalUnresolved('NumPy gradual-underflow runtime check failed')
    build = prepare_primal_native() if arithmetic_backend == 'native' else {}
    weights,lower,upper = (np.require(x,dtype=np.float64,requirements=['C','A']) for x in (weights,lower,upper))
    uncertain = int(np.count_nonzero(lower != upper))
    try:
        with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
            tick = time.perf_counter_ns()
            evidence = _coefficient_bounds(lower,upper,lam*norm,arithmetic_backend=arithmetic_backend)
            coefficient_elapsed = time.perf_counter_ns()-tick
            grid,boundaries = _grid_arrays(expected,bits)
            row_function = _rows_native if arithmetic_backend == 'native' else _rows_python
            codes,receipt = row_function(weights,evidence.centers,evidence.radii,grid,boundaries)
            base = _finish(codes,weights.size,0,uncertain,evidence.max_solution_error_squared,candidate_codes)
    except PrimalUnresolved:
        raise
    except LowRankUnresolved as exc:
        raise PrimalUnresolved(str(exc)) from exc
    return PrimalBoxResult(**base.__dict__,arithmetic_backend=arithmetic_backend,
        width=admission['width'],tokens=admission['tokens'],work_units=admission['work_units'],
        explicit_array_bytes=admission['explicit_array_bytes'],
        coefficient_workspace_bytes=admission['coefficient_workspace_bytes'],
        proposal_resets=evidence.proposal_resets,max_residual_squared=evidence.max_residual_squared,
        coefficient_elapsed_ns=coefficient_elapsed,native_elapsed_ns=receipt['native_elapsed_ns'],
        compile_elapsed_ns=build.get('call_compile_elapsed_ns',0),total_elapsed_ns=time.perf_counter_ns()-started,
        native_source_sha256=build.get('source_sha256',''),native_binary_sha256=build.get('binary_sha256',''),
        native_compiler=build.get('compiler',''),native_attempted_decisions=receipt['attempted_decisions'],
        native_certified_decisions=receipt['certified_decisions'])
