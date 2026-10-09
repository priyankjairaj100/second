"""Deterministic request-local refinement of proved factor boxes.

The caller must establish box validity before using this algorithm.
Checking fallback values cannot validate boxes accepted without evaluation.
This module defines neither persistent state nor transformer transport.
"""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .dyadic_box_certificate import certify_dyadic_box
from .token_box_certificate import TokenBoxUnresolved, _matrix


@dataclass(frozen=True)
class RefinementResult:
    certificate: object
    evaluated_record_ids: tuple
    certificate_attempts: int


def refine_dyadic_boxes(weights, record_boxes, evaluate_exact, *, max_records,
                        **certificate_options):
    """Refine the widest record first; break ties by record ID.

    record_boxes contains (ID, lower, upper) triples with width-by-token arrays.
    evaluate_exact(ID) must return exact target factors for that same record.
    All records must have at least one token. IDs and arrays remain caller-owned.
    The function copies boxes before evaluating any callback.
    """
    if type(max_records) is not int or max_records < 0:
        raise ValueError('max_records must be a nonnegative built-in integer')
    _matrix(weights, 'weights')
    boxes={}
    for rid,lo,hi in record_boxes:
        if type(rid) is not str or not rid or rid in boxes:
            raise ValueError('record IDs must be distinct nonempty strings')
        _matrix(lo,'lower'); _matrix(hi,'upper')
        if lo.shape!=hi.shape or lo.shape[0]!=weights.shape[1] or lo.shape[1]==0 or np.any(lo>hi):
            raise ValueError('invalid record factor box')
        boxes[rid]=[lo.copy(),hi.copy()]
    if not boxes:
        raise ValueError('at least one record box is required')
    ids=sorted(boxes)
    # Exact dyadic subtraction prevents overflow and fixes selection order.
    scores={rid:max((Fraction.from_float(float(b))-Fraction.from_float(float(a))
                    for a,b in zip(boxes[rid][0].flat,boxes[rid][1].flat)),default=Fraction(0))
            for rid in ids}
    evaluated=[]; attempts=0
    while True:
        attempts+=1
        try:
            result=certify_dyadic_box(weights,
                np.concatenate([boxes[rid][0] for rid in ids],axis=1),
                np.concatenate([boxes[rid][1] for rid in ids],axis=1),**certificate_options)
            return RefinementResult(result,tuple(evaluated),attempts)
        except TokenBoxUnresolved:
            candidates=[rid for rid in ids if scores[rid]>0]
            if not candidates or len(evaluated)>=max_records:
                raise
            rid=min(candidates,key=lambda key:(-scores[key],key))
            value=evaluate_exact(rid)
            _matrix(value,'exact factors')
            lo,hi=boxes[rid]
            if value.shape!=lo.shape or np.any(value<lo) or np.any(value>hi):
                raise ValueError('exact factors contradict the supplied box')
            boxes[rid]=[value.copy(),value.copy()]
            scores[rid]=Fraction(0);evaluated.append(rid)
