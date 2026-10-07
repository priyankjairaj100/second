"""Incremental finite features for one retained-data sequential quantization.

The caller installs each exact-grid stage before requesting the next input.
Induction gives the same features as restarting the declared decoder for every
stage, because records have no shared hidden state. This is a common solver
optimization, available equally to repair and fresh controls.
"""
from fractions import Fraction as Q
from .certified_transformer import _Finite, _norm, _linear, _attention, _add
from .ordered_finite import FiniteWeights
from .transformer_backend import _check_runtime


def _sequential_features(decoder, tokens):
    """Yield (stage_id, token-major binary64 rows); send its installed matrix.

    After the last stage is yielded, callers can stop without evaluating the
    last stage output or LM head. No later calibration input depends on them.
    This routine produces features only, never task-quality measurements.
    """
    _check_runtime()
    base=decoder.base
    tokens=base._tokens(tokens)
    constant=lambda x:_Finite(float(x))
    cfg=base.config
    hidden=tuple(tuple(constant(a)+constant(b) for a,b in zip(base._token_embeddings[t],base._position_embeddings[p]))
                 for p,t in enumerate(tokens))
    def values(rows):return tuple(tuple(z.value for z in row) for row in rows)
    for index,block in enumerate(base._blocks):
        pre=f'block.{index:04d}.'
        norm=_norm(hidden,block['norm1_scale'],block['norm1_bias'],cfg.layernorm_epsilon,constant)
        installed=yield pre+'qkv',values(norm)
        qkv=_linear(norm,FiniteWeights(installed),block['qkv_bias'],constant)
        mixed=_attention(qkv,cfg.model_width,cfg.head_count,constant)
        installed=yield pre+'attn_out',values(mixed)
        hidden=_add(hidden,_linear(mixed,FiniteWeights(installed),block['attn_out_bias'],constant))
        norm=_norm(hidden,block['norm2_scale'],block['norm2_bias'],cfg.layernorm_epsilon,constant)
        installed=yield pre+'mlp_up',values(norm)
        up=_linear(norm,FiniteWeights(installed),block['mlp_up_bias'],constant)
        if cfg.activation=='gelu':
            divisor=constant(2).sqrt()
            activated=tuple(tuple((constant(Q(1,2))*x)*(1+(x/divisor).erf()) for x in row) for row in up)
        else:
            c=constant(float.fromhex('0x1.9884533d43651p-1'))
            activated=tuple(tuple((constant(Q(1,2))*x)*(1+(c*(x+constant(0.044715)*x*x*x)).tanh()) for x in row) for row in up)
        installed=yield pre+'mlp_down',values(activated)
        if index+1==len(base._blocks):return
        hidden=_add(hidden,_linear(activated,FiniteWeights(installed),block['mlp_down_bias'],constant))


def sequential_features(decoder,tokens):
    """Scope each generator advancement without leaking across suspension."""
    from .finite_primitives import primitive_scope
    iterator=_sequential_features(decoder,tokens)
    with primitive_scope(decoder.primitive_backend):current=next(iterator)
    while True:
        installed=yield current
        with primitive_scope(decoder.primitive_backend):
            try:current=iterator.send(installed)
            except StopIteration:return
