"""Validate an immutable installed prefix once, then evaluate many records.

The arithmetic path is exactly CertifiedDecoder._eval followed by value
extraction. Only repeated validation/conversion of unchanged codes is removed.
The captured mapping owns immutable tuples or compact immutable-byte views.
This is common evaluation infrastructure, not a repair-speed certificate.
"""
from types import MappingProxyType
from .certified_transformer import CertifiedDecoder,_StageWeights,_Finite,_execute
from .ordered_finite import FiniteWeights
from .finite_primitives import primitive_scope
from .transformer_backend import _check_runtime


class PreparedFinitePrefix:
    def __setattr__(self,key,value):
        if getattr(self,'_sealed',False):raise AttributeError('prepared prefix is immutable')
        object.__setattr__(self,key,value)

    def __init__(self,decoder,prefix=None):
        if type(decoder) is not CertifiedDecoder:raise TypeError('requires the declared certified decoder')
        _check_runtime()
        self.decoder=decoder
        self.installed=MappingProxyType(decoder.base._prefix(prefix))
        self._sealed=True

    def logits(self,tokens):
        _check_runtime()
        base=self.decoder.base
        weights=_StageWeights(self.decoder.stage_ids,lambda stage:FiniteWeights(self.installed.get(stage,base._float_weights[stage])))
        with primitive_scope(self.decoder.primitive_backend):
            rows=_execute(base,base._tokens(tokens),weights,lambda value:_Finite(float(value)),None)
        return tuple(tuple(value.value for value in row) for row in rows)
