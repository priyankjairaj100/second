"""Explicit equivalent finite decoder with ordered attention and activations.

This subclass preserves the scalar reference target manifest. Its separate
implementation manifest identifies the code that actually executes. No global
function replacement or cross-thread mutation enables the optimized path.
"""
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import numpy as np

from .certified_transformer import CertifiedDecoder, _Finite, _StageWeights, _norm, _linear, _add
from .compact_exact import CompactDyadicMatrix
from .finite_primitives import primitive_scope
from .ordered_attention_v30 import finite_attention, batch_rounded_primitive
from .ordered_finite import FiniteWeights
from .transformer_backend import FiniteTargetError, _check_runtime


def ordered_activation(rows,activation,constant):
    """Batch independent MLP entries while retaining each scalar operation."""
    _check_runtime()
    if activation not in ('gelu','gelu_new'):
        raise ValueError('unsupported finite activation')
    if any(type(value) is not _Finite or not isinstance(value.value,(float,np.float64))
           for row in rows for value in row):
        raise TypeError('ordered activation requires finite scalar values')
    values = np.asarray([[float(value.value) for value in row] for row in rows],dtype=np.float64)
    if values.ndim != 2 or not values.size or not np.all(np.isfinite(values)):
        raise FiniteTargetError('nonfinite or malformed finite activation input')
    half = constant(Q(1,2)).value
    one = constant(1).value
    half_values = np.empty_like(values)
    argument = np.empty_like(values)
    try:
        with np.errstate(over='raise',invalid='raise',divide='raise',under='ignore'):
            np.multiply(half,values,out=half_values)
            if activation == 'gelu':
                divisor = constant(2).sqrt().value
                np.divide(values,divisor,out=argument)
                nonlinear = batch_rounded_primitive('erf',argument)
            else:
                # Retain left association: ((0.044715*x)*x)*x.
                np.multiply(constant(0.044715).value,values,out=argument)
                np.multiply(argument,values,out=argument)
                np.multiply(argument,values,out=argument)
                np.add(values,argument,out=argument)
                np.multiply(constant(float.fromhex('0x1.9884533d43651p-1')).value,argument,out=argument)
                nonlinear = batch_rounded_primitive('tanh',argument)
            if not np.all(np.isfinite(nonlinear)):
                raise FiniteTargetError('nonfinite certified decoder intermediate')
            np.add(nonlinear,one,out=nonlinear)
            np.multiply(half_values,nonlinear,out=half_values)
    except FloatingPointError as exc:
        raise FiniteTargetError('nonfinite certified decoder intermediate') from exc
    if not np.all(np.isfinite(half_values)):
        raise FiniteTargetError('nonfinite certified decoder intermediate')
    return tuple(tuple(_Finite(float(value)) for value in row) for row in half_values)


def _execute_ordered(base,tokens,weights,constant,stop):
    cfg = base.config
    hidden = tuple(tuple(constant(a)+constant(b) for a,b in
                         zip(base._token_embeddings[t],base._position_embeddings[p]))
                   for p,t in enumerate(tokens))
    for index,block in enumerate(base._blocks):
        prefix = f'block.{index:04d}.'
        norm = _norm(hidden,block['norm1_scale'],block['norm1_bias'],cfg.layernorm_epsilon,constant)
        stage = prefix+'qkv'
        if stop == stage:
            return norm
        qkv = _linear(norm,weights[stage],block['qkv_bias'],constant)
        mixed = finite_attention(qkv,cfg.model_width,cfg.head_count,constant)
        stage = prefix+'attn_out'
        if stop == stage:
            return mixed
        hidden = _add(hidden,_linear(mixed,weights[stage],block['attn_out_bias'],constant))
        norm = _norm(hidden,block['norm2_scale'],block['norm2_bias'],cfg.layernorm_epsilon,constant)
        stage = prefix+'mlp_up'
        if stop == stage:
            return norm
        up = _linear(norm,weights[stage],block['mlp_up_bias'],constant)
        activated = ordered_activation(up,getattr(cfg,'activation','gelu'),constant)
        stage = prefix+'mlp_down'
        if stop == stage:
            return activated
        hidden = _add(hidden,_linear(activated,weights[stage],block['mlp_down_bias'],constant))
    norm = _norm(hidden,base._final_norm_scale,base._final_norm_bias,cfg.layernorm_epsilon,constant)
    return _linear(norm,FiniteWeights(base._lm_head),base._lm_head_bias,constant)


def _implementation_payload():
    root = Path(__file__).parent
    names = ('ordered_finite_decoder_v30.py','ordered_attention_v30.py',
             'ordered_finite.py','finite_primitives.py','certified_intervals.py','certified_transformer.py')
    return dict(schema='ordered-equivalent-finite-decoder-v30',
        source_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names},
        numpy_version=np.__version__,
        target='unchanged CertifiedDecoder manifest; implementation identity remains separate',
        arithmetic='original scalar reduction order; independent ufunc operations; no BLAS reductions',
        primitives='directed MPFR endpoints and exact rational binary64 conversion; unchanged fallback',
        global_mutation=False, same_resource_or_refusal_behavior_claimed=False)


class OrderedFiniteDecoder(CertifiedDecoder):
    """Opt-in finite evaluator with the same declared mathematical target."""

    def __init__(self,base,*,primitive_backend='rational'):
        super().__init__(base,primitive_backend=primitive_backend)
        raw = json.dumps(_implementation_payload(),sort_keys=True,separators=(',',':')).encode('ascii')
        object.__setattr__(self,'_implementation_bytes',raw)

    @property
    def implementation_manifest(self):
        return json.loads(self._implementation_bytes)

    def _eval(self,tokens,prefix,stop):
        _check_runtime()
        installed = self.base._prefix(prefix)
        weights = _StageWeights(self.stage_ids,
            lambda stage:FiniteWeights(installed.get(stage,self.base._float_weights[stage])))
        with primitive_scope(self.primitive_backend):
            return _execute_ordered(self.base,self.base._tokens(tokens),weights,lambda value:_Finite(float(value)),stop)

    def sequential_features(self,tokens):
        return ordered_sequential_features(self,tokens)

    def prepare_prefix(self,prefix=None):
        return OrderedFinitePrefix(self,prefix)


def _ordered_sequence(decoder,tokens):
    _check_runtime()
    base = decoder.base
    tokens = base._tokens(tokens)
    constant = lambda value:_Finite(float(value))
    cfg = base.config
    hidden = tuple(tuple(constant(a)+constant(b) for a,b in
                         zip(base._token_embeddings[t],base._position_embeddings[p]))
                   for p,t in enumerate(tokens))
    def values(rows):
        return tuple(tuple(value.value for value in row) for row in rows)
    for index,block in enumerate(base._blocks):
        prefix = f'block.{index:04d}.'
        norm = _norm(hidden,block['norm1_scale'],block['norm1_bias'],cfg.layernorm_epsilon,constant)
        installed = yield prefix+'qkv',values(norm)
        qkv = _linear(norm,FiniteWeights(installed),block['qkv_bias'],constant)
        mixed = finite_attention(qkv,cfg.model_width,cfg.head_count,constant)
        installed = yield prefix+'attn_out',values(mixed)
        hidden = _add(hidden,_linear(mixed,FiniteWeights(installed),block['attn_out_bias'],constant))
        norm = _norm(hidden,block['norm2_scale'],block['norm2_bias'],cfg.layernorm_epsilon,constant)
        installed = yield prefix+'mlp_up',values(norm)
        up = _linear(norm,FiniteWeights(installed),block['mlp_up_bias'],constant)
        activated = ordered_activation(up,getattr(cfg,'activation','gelu'),constant)
        installed = yield prefix+'mlp_down',values(activated)
        if index+1 == len(base._blocks):
            return
        hidden = _add(hidden,_linear(activated,FiniteWeights(installed),block['mlp_down_bias'],constant))


def ordered_sequential_features(decoder,tokens):
    """Scope each generator advancement without leaking across suspension."""
    if type(decoder) is not OrderedFiniteDecoder:
        raise TypeError('ordered feature traversal requires OrderedFiniteDecoder')
    iterator = _ordered_sequence(decoder,tokens)
    with primitive_scope(decoder.primitive_backend):
        current = next(iterator)
    while True:
        installed = yield current
        with primitive_scope(decoder.primitive_backend):
            try:
                current = iterator.send(installed)
            except StopIteration:
                return


class OrderedFinitePrefix:
    """Validate installed immutable weights once, then use the ordered evaluator."""

    def __setattr__(self,key,value):
        if getattr(self,'_sealed',False):
            raise AttributeError('ordered prepared prefix is immutable')
        object.__setattr__(self,key,value)

    def __init__(self,decoder,prefix=None):
        if type(decoder) is not OrderedFiniteDecoder:
            raise TypeError('ordered prepared prefix requires OrderedFiniteDecoder')
        _check_runtime()
        self.decoder = decoder
        if prefix is None:
            installed = {}
        else:
            unknown = set(prefix)-set(decoder.stage_ids)
            if unknown:
                raise ValueError(f'unknown installed stages: {sorted(unknown)}')
            compact = {stage:value for stage,value in prefix.items() if type(value) is CompactDyadicMatrix}
            installed = decoder.base._prefix({stage:value for stage,value in prefix.items()
                if type(value) is not CompactDyadicMatrix})
            for stage,value in compact.items():
                base = decoder.base._weights[stage]
                if value.shape != (len(base),len(base[0])):
                    raise ValueError('installed compact matrix has an incorrect shape')
                installed[stage] = value.floats()
        self.installed = MappingProxyType(installed)
        self._sealed = True

    def logits(self,tokens):
        _check_runtime()
        base = self.decoder.base
        weights = _StageWeights(self.decoder.stage_ids,
            lambda stage:FiniteWeights(self.installed.get(stage,base._float_weights[stage])))
        with primitive_scope(self.decoder.primitive_backend):
            rows = _execute_ordered(base,base._tokens(tokens),weights,lambda value:_Finite(float(value)),None)
        return tuple(tuple(value.value for value in row) for row in rows)
