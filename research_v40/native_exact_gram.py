"""Exact four-limb Gram accumulation for admitted binary64 inputs.

This trusted factory preserves the V35 archive and source commitments.
Only integer products and modular limb arithmetic enter the native kernel.
The admitted absolute-sum bound rules out signed overflow. No floating
Gram, eigenvalue test, or checksum alone creates trusted PSD evidence.
"""
import ctypes
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time

import numpy as np

from research_v35 import exact_gram as reference

_SOURCE = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <limits.h>
typedef __uint128_t wide;

static void product(const uint64_t *a, const uint64_t *b, uint64_t *p) {
    p[0]=p[1]=p[2]=p[3]=0;
    for (size_t i=0;i<2;i++) {
        wide carry=0;
        for (size_t j=0;j<2;j++) {
            wide value=(wide)a[i]*b[j]+p[i+j]+carry;
            p[i+j]=(uint64_t)value;
            carry=value>>64;
        }
        p[i+2]=(uint64_t)carry;
    }
}

int exact_gram(size_t width, size_t tokens, const uint64_t *words,
               int exponent, uint64_t *output) {
    if (!width || width>8192 || tokens>((size_t)1<<24)) return 1;
    if (tokens && width>SIZE_MAX/tokens) return 1;
    size_t count=width*tokens;
    if (count>SIZE_MAX/(2*sizeof(uint64_t))) return 1;
    uint64_t *values=calloc(count ? 2*count : 1,sizeof(uint64_t));
    unsigned char *negative=calloc(count ? count : 1,1);
    if (!values || !negative) { free(values); free(negative); return 2; }
    for (size_t i=0;i<count;i++) {
        uint64_t word=words[i], encoded=(word>>52)&2047;
        uint64_t sig=word&((((uint64_t)1)<<52)-1);
        if (encoded==2047) { free(values); free(negative); return 3; }
        int exp=-1074;
        if (encoded) { sig|=((uint64_t)1)<<52; exp=(int)encoded-1075; }
        if (!sig) continue;
        int trailing=__builtin_ctzll(sig);
        sig>>=trailing;
        exp+=trailing;
        int shift=exp-exponent, bits=64-__builtin_clzll(sig);
        if (shift<0 || bits+shift>127) { free(values); free(negative); return 3; }
        if (shift<64) {
            values[2*i]=sig<<shift;
            values[2*i+1]=shift ? sig>>(64-shift) : 0;
        } else {
            values[2*i]=0;
            values[2*i+1]=sig<<(shift-64);
        }
        negative[i]=(unsigned char)(word>>63);
    }
    size_t index=0;
    for (size_t i=0;i<width;i++) for (size_t j=0;j<=i;j++) {
        uint64_t sum[4]={0,0,0,0};
        for (size_t t=0;t<tokens;t++) {
            size_t a=i*tokens+t, b=j*tokens+t;
            uint64_t p[4]; product(values+2*a,values+2*b,p);
            wide carry=0;
            if (negative[a]==negative[b]) {
                for (size_t k=0;k<4;k++) {
                    wide value=(wide)sum[k]+p[k]+carry;
                    sum[k]=(uint64_t)value; carry=value>>64;
                }
            } else {
                for (size_t k=0;k<4;k++) {
                    wide sub=(wide)p[k]+carry;
                    carry=(wide)sum[k]<sub;
                    sum[k]=(uint64_t)((wide)sum[k]-sub);
                }
            }
        }
        for (size_t k=0;k<4;k++) output[4*index+k]=sum[k];
        index++;
    }
    free(values); free(negative); return 0;
}
'''

_NATIVE = None
_BUILD = None
_DIRECTORY = None
_FLAGS = ('-O3', '-std=c11', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror')


def prepare_native():
    global _NATIVE, _BUILD, _DIRECTORY
    if _NATIVE is not None:
        return dict(_BUILD, compiled_now=False, call_compile_elapsed_ns=0)
    if sys.byteorder != 'little' or struct.calcsize('Q') != 8:
        raise RuntimeError('Native exact Gram requires little-endian 64-bit words')
    compiler = shutil.which('cc')
    if compiler is None:
        raise RuntimeError('Native exact Gram requires a C compiler')
    started = time.perf_counter_ns()
    directory = tempfile.TemporaryDirectory(prefix='exact-gram-v40-')
    source, binary = Path(directory.name) / 'gram.c', Path(directory.name) / 'gram.so'
    source.write_text(_SOURCE)
    try:
        result = subprocess.run([compiler, *_FLAGS, str(source), '-o', str(binary)],
                                capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError('Native exact Gram compilation failed: ' + result.stderr[:2000])
        native = ctypes.CDLL(str(binary))
        ptr = ctypes.POINTER(ctypes.c_uint64)
        native.exact_gram.argtypes = [ctypes.c_size_t, ctypes.c_size_t, ptr, ctypes.c_int, ptr]
        native.exact_gram.restype = ctypes.c_int
        version = subprocess.run([compiler, '--version'], capture_output=True, text=True, timeout=10)
        _BUILD = dict(source_sha256=hashlib.sha256(_SOURCE.encode()).hexdigest(),
            binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            compiler=compiler, compiler_version=version.stdout.splitlines()[0], flags=list(_FLAGS),
            compile_elapsed_ns=time.perf_counter_ns() - started)
        _NATIVE, _DIRECTORY = native, directory
    except BaseException:
        directory.cleanup()
        raise
    return dict(_BUILD, compiled_now=True, call_compile_elapsed_ns=_BUILD['compile_elapsed_ns'])


def accumulate(features, *, source_id, normalization=256, budget=reference.GramBudget()):
    """Create a trusted exact Gram from a private, admitted feature snapshot.

    The source must remain unchanged during the snapshot copy. Every partial
    sum has magnitude below 2**255, by the conservative absolute-sum bound.
    Four limbs therefore recover the exact signed result from modular sums.
    The archive is byte-identical to reference.accumulate, including lineage.
    """
    source_id = reference._source_id(source_id)
    normalization = reference._normalization(normalization)
    array, admission = reference._feature_scan(features, budget)
    width, tokens = array.shape
    if width > 8192 or tokens > 2**24 or admission.accumulator_magnitude_bits > 255:
        raise reference.GramAdmissionError('native exact accumulator admission exceeded')
    native_bytes = 17 * width * tokens + 64 * admission.packed_entries
    if admission.explicit_memory_bound + native_bytes > budget.max_memory_bytes:
        raise reference.GramAdmissionError('native exact workspace admission exceeded')
    prepare_native()
    words = array.view(np.uint64)
    output = np.empty((admission.packed_entries, 4), dtype=np.uint64)
    ptr = ctypes.POINTER(ctypes.c_uint64)
    status = _NATIVE.exact_gram(width, tokens, words.ctypes.data_as(ptr),
        admission.feature_exponent, output.ctypes.data_as(ptr))
    if status:
        raise RuntimeError(f'native exact Gram failed: status={status}')
    raw = output.tobytes(order='C')
    packed = [int.from_bytes(raw[offset:offset + 32], 'little', signed=True) for offset in range(0, len(raw), 32)]
    if any(abs(value).bit_length() > admission.accumulator_magnitude_bits for value in packed):
        raise ArithmeticError('Native result exceeds the admitted exact bound')
    if any(packed[i * (i + 1) // 2 + i] < 0 for i in range(width)):
        raise ArithmeticError('Native exact Gram has a negative diagonal')
    packed, exponent = reference._canonical(packed, 2 * admission.feature_exponent)
    feature_hash = hashlib.sha256()
    feature_hash.update(struct.pack('>II', width, tokens))
    feature_hash.update(array.astype('<f8', copy=False).tobytes(order='C'))
    source = reference.SourceCommitment(source_id, feature_hash.hexdigest(),
        reference._numeric_digest(width, exponent, packed), tokens)
    # This is a new trusted factory backed by exact native accumulation.
    # The private seal is never exported or used for arbitrary caller Grams.
    return reference.ExactGram(width, tokens, normalization, exponent, packed, (source,),
        trusted=True, admission=admission, _seal=reference._SEAL)
