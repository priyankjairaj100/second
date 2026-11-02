"""Fixed synthetic component profile of the unchanged streamed certificate."""
from fractions import Fraction
import hashlib
import time
import numpy as np
from research_v40.streamed_primal_ball import certify_streamed_primal_ball
from src.primal_certificate_v30 import PrimalBudget

WIDTHS=(192,768,1536)


def fixture(width):
    if width not in WIDTHS:raise ValueError('Unregistered synthetic width')
    rng=np.random.Generator(np.random.PCG64(20261011+width))
    weights=rng.integers(-1024,1025,size=(4,width)).astype(np.float64)/512
    features=rng.integers(-16,17,size=(width,128)).astype(np.float64)/64
    return weights,features


def run(emit):
    rows=[]
    for width in WIDTHS:
        weights,features=fixture(width)
        identity=dict(width=width,rows=4,tokens=128,
            weights_sha256=hashlib.sha256(weights.astype('<f8').tobytes()).hexdigest(),
            features_sha256=hashlib.sha256(features.astype('<f8').tobytes()).hexdigest())
        emit(dict(phase='case_started',**identity));start=time.perf_counter_ns()
        result=certify_streamed_primal_ball(weights,[(features,features)],total_tokens=128,block_tokens=128,
            max_blocks=1,ridge=Fraction(1,100),normalization=1664,
            budget=PrimalBudget(max_workspace_bytes=8*2**30,max_work_units=64_000_000_000))
        row=dict(**identity,status='certified',elapsed_ns=time.perf_counter_ns()-start,
            code_sha256=hashlib.sha256(result.codes.astype('<f8').tobytes()).hexdigest(),diagnostics=result.diagnostics)
        rows.append(row);emit(dict(phase='case_complete',**row))
    return rows
