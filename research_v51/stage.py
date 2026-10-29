"""Prepare only a registered prefix of the unchanged ordered feature stream."""
import numpy as np
from src.anchor_transformer import decoder_binding, provider_binding
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder, ordered_sequential_features
from src.fixed_factor_state import FactorBlock

STAGE_ID = 'block.0000.mlp_down'
HISTORICAL_CODE = '91b450c2c1547e40b6533005e8245fbdb6d1c4c34af889efab5fbf1e214eea5a'


def prefix_factor(decoder, target, record, context, stage_id=STAGE_ID):
    if type(decoder) is not OrderedFiniteDecoder:
        raise TypeError('OrderedFiniteDecoder required')
    if (context.target_sha256 != target.digest or
            context.decoder_sha256 != decoder_binding(decoder) or
            context.provider_sha256 != provider_binding()):
        raise ValueError('Ordered context binding differs')
    if type(record) is not dict or set(record) != {'id', 'tokens'}:
        raise ValueError('Record requires ID and tokens')
    ids = [s.stage_id for s in target.stages]
    if stage_id not in ids:
        raise ValueError('Stage is outside target')
    stop = ids.index(stage_id)
    tokens = decoder.base._tokens(record['tokens'])
    stream = ordered_sequential_features(decoder, tokens)
    try:
        for i in range(stop + 1):
            sid, values = next(stream) if i == 0 else stream.send(context.anchor_matrices[i-1])
            if sid != ids[i]:
                raise ValueError('Ordered source stage differs')
            if i == stop:
                # Same serialization as prepare_ordered_leaf, preserving words.
                block = FactorBlock.from_array(sid, values)
                if block.array().shape != (len(tokens), target.stages[i].width):
                    raise ValueError('Source shape differs')
                return block
    finally:
        stream.close()


def checked_feature(values, width, tokens):
    a = np.asarray(values)
    if a.dtype != np.float64 or a.shape != (tokens, width) or not np.isfinite(a).all():
        raise ValueError('Invalid complete feature matrix')
    return np.ascontiguousarray(a)
