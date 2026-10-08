"""Finite affine bounds from a fixed anchor, without retained dot products.

This component does not bound a whole transformer. Its caller must prove the
input error bound and bind the anchor to a calibration-independent execution.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
import hashlib
import math
import sys
import numpy as np
from .finite_feature_boxes import FloatBox, _freeze, _runtime
from .token_box_certificate import _matrix

_U=Q(1,2**53)
_ETA=Q(1,2**1074)
_MAX=Q.from_float(sys.float_info.max)


def _q(value):return Q.from_float(float(value))

def _hash(value):
    return hashlib.sha256(str(value.shape).encode()+value.astype('<f8',copy=False).tobytes()).hexdigest()


def _nonnegative(value):
    result=Q(value)
    if result<0:raise ValueError('error bound must be nonnegative')
    return result


def _finite_bound(value):
    if value>_MAX:raise ArithmeticError('bound cannot exclude finite overflow')
    return value


def _rounded_difference(real_delta, anchor_real_magnitude):
    if not real_delta:return Q(0)
    _finite_bound(anchor_real_magnitude+real_delta)
    return real_delta+_U*(2*anchor_real_magnitude+real_delta)+2*_ETA


@dataclass(frozen=True)
class AffineAnchor:
    """Trusted preparation output; fields do not authenticate hostile inputs."""
    weight_sha256: str
    bias_sha256: str
    weight_shape: tuple
    input_maxima: tuple
    product_maxima: tuple
    accumulator_maxima: tuple
    output: np.ndarray


@dataclass(frozen=True)
class AffineChange:
    anchor_weight_sha256: str
    target_weight_sha256: str
    shape: tuple
    target_column_maxima: tuple
    difference_column_maxima: tuple


def prepare_affine_anchor(inputs, weights, bias):
    """Run the declared ordered multiply-add schedule once for anchor values."""
    _runtime();_matrix(inputs,'inputs');_matrix(weights,'weights')
    if not all(inputs.shape) or not all(weights.shape) or inputs.shape[1]!=weights.shape[1]:
        raise ValueError('incompatible nonempty affine dimensions')
    if type(bias) is not np.ndarray or bias.dtype!=np.float64 or bias.shape!=(weights.shape[0],) or not np.isfinite(bias).all():
        raise ValueError('invalid affine bias')
    accum=np.zeros((inputs.shape[0],weights.shape[0]),dtype=np.float64)
    im=[];pm=[];am=[0.]
    with np.errstate(over='raise',invalid='raise',under='ignore'):
        for i in range(inputs.shape[1]):
            product=np.multiply(inputs[:,i,None],weights[None,:,i])
            accum=np.add(accum,product)
            im.append(float(np.max(np.abs(inputs[:,i]))))
            pm.append(float(np.max(np.abs(product))))
            am.append(float(np.max(np.abs(accum))))
        output=np.add(accum,bias[None,:])
    if not np.isfinite(output).all():raise ArithmeticError('nonfinite anchor')
    return AffineAnchor(_hash(weights),_hash(bias),tuple(weights.shape),tuple(im),tuple(pm),tuple(am),_freeze(output))


def prepare_affine_change(anchor_weights,target_weights):
    """Scan matrices once. Reuse this trusted change object across records."""
    _matrix(anchor_weights,'anchor_weights');_matrix(target_weights,'target_weights')
    if anchor_weights.shape!=target_weights.shape or not all(anchor_weights.shape):
        raise ValueError('incompatible matrix dimensions')
    _runtime()
    with np.errstate(over='raise',invalid='raise',under='ignore'):
        difference=np.abs(np.subtract(target_weights,anchor_weights))
        largest=np.max(difference,axis=0)
        upper=np.where(largest==0.,0.,np.nextafter(largest,np.inf))
    if not np.isfinite(upper).all():raise ArithmeticError('matrix difference exceeds finite range')
    maxima=tuple(_q(v) for v in np.max(np.abs(target_weights),axis=0))
    differences=tuple(_q(v) for v in upper)
    return AffineChange(_hash(anchor_weights),_hash(target_weights),tuple(anchor_weights.shape),maxima,differences)



def affine_error_bound(anchor,change,bias,input_error):
    """Return one exact dyadic/rational output-error bound for all entries.

    Premise: every new input entry differs from its anchor by at most input_error.
    The bias is fixed. No retained input values or dot products are read here.
    """
    _runtime()
    if type(anchor) is not AffineAnchor or type(change) is not AffineChange:
        raise TypeError('trusted prepared anchor and change objects are required')
    if change.anchor_weight_sha256!=anchor.weight_sha256 or change.shape!=anchor.weight_shape:
        raise ValueError('anchor matrix binding mismatch')
    if type(bias) is not np.ndarray or bias.dtype!=np.float64 or bias.shape!=(anchor.weight_shape[0],) or not np.isfinite(bias).all() or _hash(bias)!=anchor.bias_sha256:
        raise ValueError('fixed bias binding mismatch')
    delta=_nonnegative(input_error);accum=Q(0)
    for i in range(anchor.weight_shape[1]):
        # |w'x'-wx| <= |w'| |x'-x| + |w'-w| |x|.
        product_real=change.target_column_maxima[i]*delta+change.difference_column_maxima[i]*_q(anchor.input_maxima[i])
        # The anchor rounded product differs from its real value by rounding.
        # Bound the real anchor product using its rounded magnitude instead:
        # |real| <= (|RN(real)|+eta)/(1-u).
        product_magnitude=(_q(anchor.product_maxima[i])+_ETA)/(1-_U)
        product=_rounded_difference(product_real,product_magnitude)
        magnitude=_q(anchor.accumulator_maxima[i])+_q(anchor.product_maxima[i])
        accum=_rounded_difference(accum+product,magnitude)
    magnitude=_q(anchor.accumulator_maxima[-1])+max(_q(abs(v)) for v in bias)
    return _finite_bound(_rounded_difference(accum,magnitude))


def enclose_affine_output(anchor,error):
    """Materialize output boxes only; this costs one pass over stored outputs."""
    error=_nonnegative(error)
    if not error:return FloatBox.point(anchor.output)
    def endpoint(value,sign):
        exact=_q(value)+sign*error
        if abs(exact)>_MAX:raise ArithmeticError('output box exceeds finite range')
        result=float(exact)
        if (sign<0 and _q(result)>exact) or (sign>0 and _q(result)<exact):
            result=float(np.nextafter(result,-math.inf if sign<0 else math.inf))
        if not math.isfinite(result):raise ArithmeticError('nonfinite box endpoint')
        return result
    lo=np.array([endpoint(v,-1) for v in anchor.output.flat]).reshape(anchor.output.shape)
    hi=np.array([endpoint(v,1) for v in anchor.output.flat]).reshape(anchor.output.shape)
    return FloatBox(lo,hi)
