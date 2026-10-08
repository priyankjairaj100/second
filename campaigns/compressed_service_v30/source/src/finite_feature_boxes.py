"""Array enclosures of the declared binary64 decoder, not real arithmetic.

Every endpoint operation uses the target's round-to-nearest operation.
Monotonicity therefore encloses all finite machine results without an extra
outward ulp. This is distinct from an enclosure of an ideal real decoder.
Evaluation from tokens is retained-source work, including interval evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .certified_transformer import CertifiedDecoder
from .finite_primitives import primitive_scope, rounded
from .ordered_finite import FiniteWeights
from .transformer_backend import _check_runtime, FiniteTargetError


def _array(values):
    if hasattr(values, 'float_array'):
        values = values.float_array()
    out = np.asarray(values, dtype=np.float64)
    if not np.isfinite(out).all():
        raise FiniteTargetError('feature box has a nonfinite endpoint')
    return out


def _freeze(array):
    """The bytes owner prevents a caller from re-enabling array writes."""
    shape = array.shape
    array = np.ascontiguousarray(array, dtype=np.float64)
    return np.frombuffer(array.tobytes(), dtype=np.float64).reshape(shape)


def _runtime():
    _check_runtime()
    tiny = np.asarray([float.fromhex('0x0.0000000000001p-1022')])
    with np.errstate(under='ignore'):
        if np.multiply(tiny, 1.0)[0] != tiny[0] or np.add(tiny, 0.0)[0] != tiny[0]:
            raise ArithmeticError('feature boxes require vector gradual underflow')
        if np.add(np.asarray([1.0]), 2.0**-53)[0] != 1.0:
            raise ArithmeticError('feature boxes require vector round-to-nearest-even')


@dataclass(frozen=True, init=False, eq=False)
class FloatBox:
    """Inclusive finite binary64 bounds, with immutable array storage.

    Input rationals undergo the same float conversion as installed decoder
    weights. Callers needing real-rational intervals must convert outward
    before construction. Shapes must agree; broadcasting occurs in operations.
    """
    lower: np.ndarray
    upper: np.ndarray
    singleton: bool

    def __init__(self, lower, upper=None):
        lo = _array(lower)
        hi = lo if upper is None else _array(upper)
        if lo.shape != hi.shape or np.any(lo > hi):
            raise ValueError('feature box bounds must have equal shapes and lower <= upper')
        thin = np.array_equal(lo, hi)
        frozen = _freeze(lo)
        object.__setattr__(self, 'lower', frozen)
        object.__setattr__(self, 'upper', frozen if thin else _freeze(hi))
        object.__setattr__(self, 'singleton', thin)

    @property
    def shape(self):
        return self.lower.shape

    @classmethod
    def point(cls, value):
        return cls(value)

    @classmethod
    def hull(cls, first, second):
        a, b = _box(first), _box(second)
        return cls(np.minimum(a.lower, b.lower), np.maximum(a.upper, b.upper))

    def contains(self, values):
        x = _array(values)
        return x.shape == self.shape and bool(np.all(self.lower <= x) and np.all(x <= self.upper))

    def __getitem__(self, index):
        return FloatBox(self.lower[index], self.upper[index])

    def __neg__(self):
        return FloatBox(-self.upper, -self.lower)

    def __add__(self, other):
        b = _box(other)
        return _operation(np.add, self, b, monotone=True)

    __radd__ = __add__

    def __sub__(self, other):
        return self + (-_box(other))

    def __rsub__(self, other):
        return _box(other) - self

    def __mul__(self, other):
        return _operation(np.multiply, self, _box(other))

    __rmul__ = __mul__

    def __truediv__(self, other):
        b = _box(other)
        if np.any((b.lower <= 0) & (b.upper >= 0)):
            raise FiniteTargetError('feature box denominator includes zero')
        return _operation(np.divide, self, b)

    def __rtruediv__(self, other):
        return _box(other) / self

    def square(self):
        with np.errstate(over='raise', invalid='raise', under='ignore'):
            a = np.multiply(self.lower, self.lower)
            b = np.multiply(self.upper, self.upper)
        lo = np.minimum(a, b)
        lo = np.where((self.lower <= 0) & (self.upper >= 0), 0.0, lo)
        return FloatBox(lo, np.maximum(a, b))

    def primitive(self, name):
        if name not in ('sqrt', 'exp', 'erf', 'tanh'):
            raise ValueError('unsupported feature box primitive')
        if name == 'sqrt' and np.any(self.lower < 0):
            raise FiniteTargetError('feature box square root includes negative values')
        # The four target functions are increasing. Each call certifies the
        # correctly rounded endpoint value, or fails closed.
        def apply(array):
            return np.fromiter((rounded(name, float(x)) for x in array.flat),
                               dtype=np.float64, count=array.size).reshape(array.shape)
        lo = apply(self.lower)
        return FloatBox(lo, lo if self.singleton else apply(self.upper))


def _box(value):
    return value if type(value) is FloatBox else FloatBox.point(value)


def _operation(operation, a, b, monotone=False):
    with np.errstate(over='raise', invalid='raise', divide='raise', under='ignore'):
        if a.singleton and b.singleton:
            return FloatBox.point(operation(a.lower, b.lower))
        if monotone:
            return FloatBox(operation(a.lower, b.lower), operation(a.upper, b.upper))
        corners = (operation(a.lower, b.lower), operation(a.lower, b.upper),
                   operation(a.upper, b.lower), operation(a.upper, b.upper))
        return FloatBox(np.minimum.reduce(corners), np.maximum.reduce(corners))


def _sum_last(value):
    total = FloatBox.point(np.zeros(value.shape[:-1], dtype=np.float64))
    for index in range(value.shape[-1]):
        total = total + value[..., index]
    return total


def _linear(value, weights, bias):
    w = _box(weights)
    bias = _array(bias)
    if len(value.shape) != 2 or len(w.shape) != 2 or value.shape[1] != w.shape[1]:
        raise ValueError('feature box linear dimensions differ')
    if bias.shape != (w.shape[0],):
        raise ValueError('feature box bias dimensions differ')
    total = FloatBox.point(np.zeros((value.shape[0], w.shape[0])))
    for coordinate in range(value.shape[1]):
        # Separate elementwise multiply then add; no BLAS or fused operation.
        total = total + value[:, coordinate, None] * w[None, :, coordinate]
    return total + bias[None, :]


def _norm(value, scale, bias, epsilon):
    mean = _sum_last(value) / value.shape[-1]
    centered = value - mean[:, None]
    variance = _sum_last(centered.square()) / value.shape[-1]
    denominator = (variance + epsilon).primitive('sqrt')
    return (centered / denominator[:, None]) * _array(scale) + _array(bias)


def _softmax(scores):
    if not 1 <= scores.shape[-1] <= 2**53:
        raise ValueError('feature box softmax length is unsupported')
    maximum = FloatBox(np.max(scores.lower, axis=-1), np.max(scores.upper, axis=-1))
    shifted = scores - maximum[..., None]
    # Each actual shifted score is <= 0. At least one is exactly zero.
    shifted = FloatBox(shifted.lower, np.minimum(shifted.upper, 0.0))
    terms = shifted.primitive('exp')
    denominator = _sum_last(terms)
    denominator = FloatBox(np.maximum(denominator.lower, 1.0), denominator.upper)
    probabilities = terms / denominator[..., None]
    return FloatBox(np.maximum(probabilities.lower, 0.0), np.minimum(probabilities.upper, 1.0))


def _stack(values, axis=0):
    return FloatBox(np.stack([v.lower for v in values], axis=axis),
                    np.stack([v.upper for v in values], axis=axis))


def _attention(qkv, width, heads):
    head_width = width // heads
    divisor = FloatBox.point(head_width).primitive('sqrt')
    rows = []
    for token in range(qkv.shape[0]):
        row = []
        for head in range(heads):
            start = head * head_width
            query = qkv[token, start:start + head_width]
            keys = qkv[:token + 1, width + start:width + start + head_width]
            scores = _sum_last(keys * query) / divisor
            probabilities = _softmax(scores)
            values = qkv[:token + 1, 2 * width + start:2 * width + start + head_width]
            mixed = FloatBox.point(np.zeros(head_width))
            for key in range(token + 1):
                mixed = mixed + probabilities[key] * values[key]
            row.append(mixed)
        rows.append(FloatBox(np.concatenate([x.lower for x in row]),
                             np.concatenate([x.upper for x in row])))
    return _stack(rows)


def _activation(value, name):
    if name == 'gelu':
        divisor = FloatBox.point(2).primitive('sqrt')
        return (0.5 * value) * (1 + (value / divisor).primitive('erf'))
    coefficient = float.fromhex('0x1.9884533d43651p-1')
    return (0.5 * value) * (1 + (coefficient *
        (value + 0.044715 * value * value * value)).primitive('tanh'))


def _weight_box(weights, shape):
    if type(weights) is FloatBox:
        box = weights
    else:
        box = FloatBox.point(FiniteWeights(weights).array())
    if box.shape != shape:
        raise ValueError('installed feature box weight dimensions differ')
    return box


def _stream(decoder, tokens, include_logits):
    base, cfg = decoder.base, decoder.config
    hidden = FloatBox.point([base._token_embeddings[t] for t in tokens]) + FloatBox.point(
        [base._position_embeddings[p] for p in range(len(tokens))])
    for index, block in enumerate(base._blocks):
        prefix = f'block.{index:04d}.'
        norm = _norm(hidden, block['norm1_scale'], block['norm1_bias'], cfg.layernorm_epsilon)
        installed = yield prefix + 'qkv', norm
        qkv = _linear(norm, _weight_box(installed, (3 * cfg.model_width, cfg.model_width)), block['qkv_bias'])
        mixed = _attention(qkv, cfg.model_width, cfg.head_count)
        installed = yield prefix + 'attn_out', mixed
        hidden = hidden + _linear(mixed, _weight_box(installed, (cfg.model_width, cfg.model_width)), block['attn_out_bias'])
        norm = _norm(hidden, block['norm2_scale'], block['norm2_bias'], cfg.layernorm_epsilon)
        installed = yield prefix + 'mlp_up', norm
        up = _linear(norm, _weight_box(installed, (cfg.feedforward_width, cfg.model_width)), block['mlp_up_bias'])
        activated = _activation(up, cfg.activation)
        installed = yield prefix + 'mlp_down', activated
        if not include_logits and index + 1 == len(base._blocks):
            return
        hidden = hidden + _linear(activated, _weight_box(installed, (cfg.model_width, cfg.feedforward_width)), block['mlp_down_bias'])
    norm = _norm(hidden, base._final_norm_scale, base._final_norm_bias, cfg.layernorm_epsilon)
    return _linear(norm, FloatBox.point(FiniteWeights(base._lm_head).array()), base._lm_head_bias)


def sequential_feature_boxes(decoder, tokens, *, include_logits=False):
    """Yield token-major boxes; send installed weights or weight boxes.

    Each advancement scopes its primitive backend. A nonfinite endpoint or
    unproved primitive rejects the enclosure. With include_logits=True, the
    generator's StopIteration.value contains the final logit box.
    """
    if type(decoder) is not CertifiedDecoder:
        raise TypeError('feature boxes require the declared certified decoder')
    _runtime()
    iterator = _stream(decoder, decoder.base._tokens(tokens), include_logits)
    with primitive_scope(decoder.primitive_backend):
        current = next(iterator)
    while True:
        installed = yield current
        _runtime()
        with primitive_scope(decoder.primitive_backend):
            try:
                current = iterator.send(installed)
            except StopIteration as end:
                return end.value


def feature_box(decoder, tokens, prefix, stage):
    """Evaluate a supplied prefix to one stage input. This reads the record."""
    if stage not in decoder.stage_ids:
        raise ValueError('unknown requested feature stage')
    prefix = {} if prefix is None else dict(prefix)
    if set(prefix) - set(decoder.stage_ids):
        raise ValueError('unknown installed feature stage')
    stream = sequential_feature_boxes(decoder, tokens)
    current, values = next(stream)
    while current != stage:
        current, values = stream.send(prefix.get(current, decoder.base._float_weights[current]))
    stream.close()
    return values


def logits_box(decoder, tokens, prefix=None):
    """Full decoder enclosure, including the final norm and language head."""
    prefix = {} if prefix is None else dict(prefix)
    if set(prefix) - set(decoder.stage_ids):
        raise ValueError('unknown installed feature stage')
    stream = sequential_feature_boxes(decoder, tokens, include_logits=True)
    stage, _ = next(stream)
    while True:
        try:
            stage, _ = stream.send(prefix.get(stage, decoder.base._float_weights[stage]))
        except StopIteration as end:
            return end.value
