"""Generated Linux fixtures; no model, corpus or scientific timing claim."""
import ctypes
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import unittest
import numpy as np
from research_v76.token_neighbors import enabled,point,box

def raw_check():
    words=set()
    for sign in (0,1<<63):
        for exponent in range(2048):
            for delta in (-1,0,1,2):
                value=sign+(exponent<<52)+delta
                if 0<=value<1<<64:words.add(value)
    words.update((0x7fefffffffffffff,0xffefffffffffffff,0x7ff8000000000001,0xfff8000000000001))
    rng=np.random.default_rng(20261022)
    values=np.concatenate((np.array(sorted(words),dtype=np.uint64),rng.bit_generator.random_raw(1000000)))
    ptr=ctypes.POINTER(ctypes.c_uint64)
    failure=np.zeros(4,dtype=np.uint64)
    with enabled() as manifests:
        for module in (point,box):
            status=module._NATIVE.v50_compare(len(values),values.ctypes.data_as(ptr),failure.ctypes.data_as(ptr))
            if status:raise AssertionError((module.__name__,status,failure.tolist()))
    return dict(words_per_library=len(values),directions=2,libraries=2,manifests=manifests)

def signature(result):
    return (result.coefficients.tobytes(),result.errors.tobytes(),getattr(result,'zero_proposal_fallbacks',None))

def compare_cases():
    rng=np.random.default_rng(20261023)
    cases=0
    for width,tokens in ((3,0),(5,3),(32,16),(65,24)):
        x=rng.integers(-16,17,size=(width,tokens)).astype(np.float64)/16
        x[::3]=0
        for radius in (0.,2.**-30):
            a=point.native_token_coefficient_enclosures(x,Fraction(5))
            b=box.native_box_coefficient_enclosures(x-radius,x+radius,Fraction(5))
            with enabled():
                c=point.native_token_coefficient_enclosures(x,Fraction(5))
                d=box.native_box_coefficient_enclosures(x-radius,x+radius,Fraction(5))
            assert signature(a)==signature(c)
            assert signature(b)==signature(d)
            cases+=2
    # Exceptional exit must restore both source and compiled-library selection.
    originals=[(m._C_SOURCE,m._NATIVE,m._BUILD,m._DIRECTORY) for m in (point,box)]
    try:
        with enabled():
            try:
                with enabled():raise AssertionError('nested context admitted')
            except RuntimeError:pass
            raise LookupError('fixture')
    except LookupError:pass
    for m,saved in zip((point,box),originals):
        assert m._C_SOURCE==saved[0] and m._NATIVE is saved[1] and m._BUILD is saved[2] and m._DIRECTORY is saved[3]
    return cases

def benchmark():
    rng=np.random.default_rng(20261024)
    rows=[]
    for width,tokens in ((192,32),(768,128),(1536,128)):
        x=rng.integers(-16,17,size=(width,tokens)).astype(np.float64)/16
        for kind in ('point','box'):
            def solve():
                if kind=='point':return point.native_token_coefficient_enclosures(x,Fraction(5))
                return box.native_box_coefficient_enclosures(x-2.**-40,x+2.**-40,Fraction(5))
            samples={name:[] for name in ('reference','optimized')}
            expected=signature(solve())
            for repeat in range(5):
                order=('reference','optimized') if repeat%2==0 else ('optimized','reference')
                for name in order:
                    if name=='optimized':
                        with enabled():
                            start=time.perf_counter_ns();out=solve();elapsed=time.perf_counter_ns()-start
                    else:
                        start=time.perf_counter_ns();out=solve();elapsed=time.perf_counter_ns()-start
                    assert signature(out)==expected
                    samples[name].append(dict(total_ns=elapsed,native_ns=out.native_elapsed_ns,nominal_ns=out.nominal_elapsed_ns))
            medians={name:statistics.median(x['total_ns'] for x in values)/1e9 for name,values in samples.items()}
            rows.append(dict(kind=kind,width=width,tokens=tokens,samples=samples,median_s=medians,
                speedup=medians['reference']/medians['optimized'],compile_excluded=True,
                output_sha256=hashlib.sha256(expected[0]+expected[1]).hexdigest()))
    return rows

def main(output):
    start=time.perf_counter_ns()
    result=dict(scope='Generated software qualification; not model or service performance',
        primitive=raw_check(),coefficient_parity_cases=compare_cases())
    modules=['tests.test_native_token_coefficients_v30','tests.test_native_box_coefficients_v31']
    result['legacy_tests']={}
    for mode in ('reference','optimized'):
        suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
        if mode=='optimized':
            with enabled():r=unittest.TextTestRunner(verbosity=2).run(suite)
        else:r=unittest.TextTestRunner(verbosity=2).run(suite)
        result['legacy_tests'][mode]=dict(count=r.testsRun,errors=len(r.errors),failures=len(r.failures),skips=len(r.skipped))
        if not r.wasSuccessful() or r.skipped or r.testsRun!=21:
            raise AssertionError(('legacy native suite failed',result['legacy_tests']))
    result['benchmarks']=benchmark()
    result['elapsed_ns']=time.perf_counter_ns()-start
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='passed',parity_cases=result['coefficient_parity_cases'],
        benchmarks=[dict(kind=x['kind'],width=x['width'],tokens=x['tokens'],speedup=x['speedup']) for x in result['benchmarks']])))

if __name__=='__main__':main(sys.argv[1])
