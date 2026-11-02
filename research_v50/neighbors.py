"""Select a separately compiled primal kernel with equivalent normal neighbors.

Historical sources stay unchanged. Boundary values still call libm nextafter.
This adapter is confined to a dedicated, single-thread Python worker and restores
the historical kernel after the call. It is not admission for a model campaign.
"""
from contextlib import contextmanager
import ctypes
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
from src import primal_certificate_v30 as primal

HELPER=r'''
#include <string.h>
static double v50_neighbor(double x, int upward) {
    uint64_t word;
    memcpy(&word, &x, sizeof(word));
    uint64_t magnitude = word & UINT64_C(0x7fffffffffffffff);
    /* All zeros, subnormals, boundary normals, infinities and NaNs retain
       the reference operation and its floating exception behavior. */
    if (magnitude <= UINT64_C(0x0010000000000000) ||
        magnitude >= UINT64_C(0x7fefffffffffffff))
        return nextafter(x, upward ? INFINITY : -INFINITY);
    /* Both x and its neighbor are normal. Increasing unsigned magnitude
       increases a positive value and decreases a negative value. */
    if ((word >> 63) == (uint64_t)upward) --word;
    else ++word;
    memcpy(&x, &word, sizeof(x));
    return x;
}
'''
PROBE=r'''
int v50_layout(void) {
    double one = 1.0, minus_one = -1.0;
    uint64_t a, b;
    if (sizeof(double) != sizeof(uint64_t)) return 0;
    memcpy(&a, &one, sizeof(a)); memcpy(&b, &minus_one, sizeof(b));
    return nbc_runtime() && a == UINT64_C(0x3ff0000000000000) &&
           b == UINT64_C(0xbff0000000000000);
}
int v50_compare(size_t count, const uint64_t *words, uint64_t *failure) {
    if (!v50_layout()) return 1;
    int original_flags = fetestexcept(FE_ALL_EXCEPT);
    for (size_t i=0; i<count; ++i) for (int upward=0; upward<2; ++upward) {
        double x, expected, actual;
        uint64_t e, a;
        memcpy(&x, words+i, sizeof(x));
        feclearexcept(FE_ALL_EXCEPT);
        expected=nextafter(x, upward ? INFINITY : -INFINITY);
        int ef=fetestexcept(FE_ALL_EXCEPT);
        feclearexcept(FE_ALL_EXCEPT);
        actual=v50_neighbor(x, upward);
        int af=fetestexcept(FE_ALL_EXCEPT);
        memcpy(&e,&expected,sizeof(e)); memcpy(&a,&actual,sizeof(a));
        if (e!=a || ef!=af) { failure[0]=i;failure[1]=upward;failure[2]=e;failure[3]=a;return 2; }
    }
    feclearexcept(FE_ALL_EXCEPT); feraiseexcept(original_flags);
    return 0;
}
'''


def source():
    raw=primal._C_SOURCE
    for name,direction in (('down','-INFINITY'),('up','INFINITY')):
        old=f'static double {name}(double x) {{ return nextafter(x, {direction}); }}'
        if raw.count(old)!=1:raise RuntimeError('Historical primitive shape changed')
        raw=raw.replace(old,f'static double {name}(double x) {{ return v50_neighbor(x, {int(name=="up")}); }}')
    position=raw.index('typedef struct { double lo, hi; } box;')
    return raw[:position]+HELPER+raw[position:]+PROBE


_BUILT=None
_ACTIVE=False


def prepare():
    global _BUILT
    if _BUILT is not None:return _BUILT
    primal.prepare_primal_native();compiler=shutil.which('cc');raw=source();start=time.perf_counter_ns()
    directory=tempfile.TemporaryDirectory(prefix='neighbors-v50-');p=Path(directory.name)
    (p/'kernel.c').write_text(raw)
    try:
        done=subprocess.run([compiler,*primal.native_box._FLAGS,str(p/'kernel.c'),'-o',str(p/'kernel.so'),'-lm'],
            capture_output=True,text=True,timeout=60)
        if done.returncode:raise RuntimeError(done.stderr)
        native=ctypes.CDLL(str(p/'kernel.so'))
        for name in ('npc_gram','npc_column','nbc_run'):
            getattr(native,name).argtypes=getattr(primal._NATIVE,name).argtypes
            getattr(native,name).restype=getattr(primal._NATIVE,name).restype
        native.v50_layout.restype=ctypes.c_int
        if native.v50_layout()!=1:raise RuntimeError('Unsupported binary64 representation or rounding runtime')
        ptr=ctypes.POINTER(ctypes.c_uint64)
        native.v50_compare.argtypes=[ctypes.c_size_t,ptr,ptr];native.v50_compare.restype=ctypes.c_int
        build=dict(source_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            original_c_source_sha256=hashlib.sha256(primal._C_SOURCE.encode()).hexdigest(),
            binary_sha256=hashlib.sha256((p/'kernel.so').read_bytes()).hexdigest(),
            wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            compiler=compiler,compiler_version=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
            flags=list(primal.native_box._FLAGS),compile_elapsed_ns=time.perf_counter_ns()-start,
            backend='normal_neighbor_primal_v50')
        _BUILT=native,build,directory
        return _BUILT
    except BaseException:directory.cleanup();raise


@contextmanager
def enabled():
    global _ACTIVE
    if _ACTIVE or threading.active_count()!=1:raise RuntimeError('Dedicated single-thread worker required')
    native,build,directory=prepare();saved=primal._NATIVE,primal._BUILD,primal._DIRECTORY
    _ACTIVE=True;primal._NATIVE,primal._BUILD,primal._DIRECTORY=native,build,directory
    try:yield build
    finally:
        primal._NATIVE,primal._BUILD,primal._DIRECTORY=saved;_ACTIVE=False
