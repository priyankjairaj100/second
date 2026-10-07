"""Automatic, fail-closed response certificates for an explicit decoder.

This is a distinct finite program from transformer_backend's libm decoder.
It uses proved correctly rounded primitives and stable finite softmax.
A fixed affine chart selects allowed changes to ancestor matrices. Interval
second-order differentiation proves jets and mixed curvature on the chart box.
The provider rejects every unrepresented prefix. No user error bound is used.
Finite linear maps batch independent entries without changing the scalar arithmetic order.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from itertools import islice
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from . import certified_intervals as ci
from .transformer_backend import DeterministicDecoder, FiniteTargetError, _check_runtime, _serial_exact, _json_bytes
from .response_certificate import dyadic_sqrt_upper
from .response_moments import ResponseBasis, record_moments
from .linear_response import linear_record_moments
from .response_service_adapter import ResponseQuery, ResponseStageContract
from .repair_service import JobSpec, StageSpec, UnknownBound

Q = Fraction
ZERO = Q(0)
ONE = Q(1)
U = Q(1, 2**53)
TINY = Q(1, 2**1075)
MAX = Q.from_float(float.fromhex('0x1.fffffffffffffp+1023'))


class UnsupportedCertificate(ArithmeticError):
    """The proof domain does not establish a safe finite computation."""


def _ceil(value: Q, bits: int) -> Q:
    scale = 1 << bits
    return Q(-((-value.numerator * scale) // value.denominator), scale)


def _rounded_error(exact_magnitude: Q, propagated: Q, bits: int) -> Q:
    if exact_magnitude > MAX:
        raise UnsupportedCertificate('finite operation may overflow on the chart')
    return _ceil(propagated + U * exact_magnitude + TINY, bits)


def _interval(value: Q, bits: int) -> ci.Interval:
    return ci.Interval.point(value, bits=bits)


def _away(value: ci.Interval) -> Q:
    if value.lo <= 0 <= value.hi:
        raise UnsupportedCertificate('denominator enclosure contains zero')
    return min(abs(value.lo), abs(value.hi))


@dataclass(frozen=True)
class Jet:
    """Real value/derivatives, plus a uniform binary64 discrepancy bound."""
    value: ci.Interval
    gradient: tuple[ci.Interval, ...]
    hessian: tuple[tuple[ci.Interval, ...], ...]
    error: Q = ZERO

    @classmethod
    def constant(cls, value: Q, rank: int, bits: int) -> 'Jet':
        z = _interval(ZERO, bits)
        return cls(_interval(value, bits), (z,) * rank, tuple((z,) * rank for _ in range(rank)))

    @property
    def bits(self) -> int:
        return self.value.bits

    def _coerce(self, other: Any) -> 'Jet':
        if isinstance(other, Jet):
            if len(other.gradient) != len(self.gradient) or other.bits != self.bits:
                raise ValueError('incompatible jets')
            return other
        return Jet.constant(Q(other), len(self.gradient), self.bits)

    def expanded(self) -> ci.Interval:
        return ci.Interval(self.value.lo - self.error, self.value.hi + self.error, bits=self.bits)

    def __neg__(self) -> 'Jet':
        # Binary64 negation is exact, including subnormals.
        return Jet(-self.value, tuple(-g for g in self.gradient),
                   tuple(tuple(-h for h in row) for row in self.hessian), self.error)

    def __add__(self, other: Any) -> 'Jet':
        b = self._coerce(other)
        raw = self.expanded() + b.expanded()
        e = _rounded_error(raw.abs_bound(), self.error + b.error, self.bits)
        return Jet(self.value + b.value, tuple(x + y for x, y in zip(self.gradient, b.gradient)),
                   tuple(tuple(x + y for x, y in zip(ar, br)) for ar, br in zip(self.hessian, b.hessian)), e)

    __radd__ = __add__

    def __sub__(self, other: Any) -> 'Jet':
        return self + (-self._coerce(other))

    def __rsub__(self, other: Any) -> 'Jet':
        return self._coerce(other) - self

    def __mul__(self, other: Any) -> 'Jet':
        b = self._coerce(other)
        r = len(self.gradient)
        grad = tuple(self.gradient[i] * b.value + self.value * b.gradient[i] for i in range(r))
        hess = tuple(tuple(self.hessian[i][j] * b.value + self.gradient[i] * b.gradient[j]
                           + self.gradient[j] * b.gradient[i] + self.value * b.hessian[i][j]
                           for j in range(r)) for i in range(r))
        propagated = self.value.abs_bound() * b.error + b.value.abs_bound() * self.error + self.error * b.error
        raw = self.expanded() * b.expanded()
        return Jet(self.value * b.value, grad, hess, _rounded_error(raw.abs_bound(), propagated, self.bits))

    __rmul__ = __mul__

    def square(self) -> 'Jet':
        out = self * self
        return Jet(self.value.square(), out.gradient, out.hessian, out.error)

    def __truediv__(self, other: Any) -> 'Jet':
        b = self._coerce(other)
        minimum, finite_minimum = _away(b.value), _away(b.expanded())
        inv = ONE / b.value
        inv2, inv3 = inv.square(), inv.square() * inv
        r = len(self.gradient)
        grad = tuple(self.gradient[i] * inv - self.value * b.gradient[i] * inv2 for i in range(r))
        hess = tuple(tuple(self.hessian[i][j] * inv
                           - (self.gradient[i] * b.gradient[j] + self.gradient[j] * b.gradient[i]
                              + self.value * b.hessian[i][j]) * inv2
                           + 2 * self.value * b.gradient[i] * b.gradient[j] * inv3
                           for j in range(r)) for i in range(r))
        propagated = self.error / finite_minimum + self.value.abs_bound() * b.error / (minimum * finite_minimum)
        raw = self.expanded() / b.expanded()
        return Jet(self.value / b.value, grad, hess, _rounded_error(raw.abs_bound(), propagated, self.bits))

    def __rtruediv__(self, other: Any) -> 'Jet':
        return self._coerce(other) / self

    def _compose(self, value: ci.Interval, first: ci.Interval, second: ci.Interval,
                 finite_value: ci.Interval, lipschitz: Q) -> 'Jet':
        grad = tuple(first * g for g in self.gradient)
        hess = tuple(tuple(first * h + second * gi * gj for h, gj in zip(row, self.gradient))
                     for row, gi in zip(self.hessian, self.gradient))
        return Jet(value, grad, hess, _rounded_error(finite_value.abs_bound(), lipschitz * self.error, self.bits))

    def exp(self) -> 'Jet':
        value, wide = self.value.exp(), self.expanded().exp()
        return self._compose(value, value, value, wide, wide.hi)

    def sqrt(self) -> 'Jet':
        wide_input = self.expanded()
        if self.value.lo <= 0 or wide_input.lo <= 0:
            raise UnsupportedCertificate('sqrt proof needs a strictly positive input')
        value, wide = self.value.sqrt(), wide_input.sqrt()
        first = ONE / (2 * value)
        second = -ONE / (4 * self.value * value)
        return self._compose(value, first, second, wide, ONE / (2 * wide.lo))

    def erf(self) -> 'Jet':
        c = 2 / ci.pi_interval(self.bits).sqrt()
        first = c * (-self.value.square()).exp()
        second = -2 * self.value * first
        return self._compose(self.value.erf(), first, second, self.expanded().erf(), Q(2))

    def tanh(self) -> 'Jet':
        value = self.value.tanh()
        first = 1 - value.square()
        second = -2 * value * first
        return self._compose(value, first, second, self.expanded().tanh(), ONE)


@dataclass(frozen=True)
class _Finite:
    value: float

    def __post_init__(self):
        if not math.isfinite(self.value):
            raise FiniteTargetError('nonfinite certified decoder intermediate')

    def _c(self, x):
        return x if isinstance(x, _Finite) else _Finite(float(x))

    def __add__(self, b): return _Finite(self.value + self._c(b).value)
    __radd__ = __add__
    def __neg__(self): return _Finite(-self.value)
    def __sub__(self, b): return self + (-self._c(b))
    def __rsub__(self, b): return self._c(b) - self
    def __mul__(self, b): return _Finite(self.value * self._c(b).value)
    __rmul__ = __mul__
    def __truediv__(self, b): return _Finite(self.value / self._c(b).value)
    def __rtruediv__(self, b): return self._c(b) / self
    def square(self): return self * self
    def exp(self): return _Finite(ci.round_exp(self.value))
    def sqrt(self): return _Finite(ci.round_sqrt(self.value))
    def erf(self): return _Finite(ci.round_erf(self.value))
    def tanh(self): return _Finite(ci.round_tanh(self.value))


def _sum(values, constant):
    result = constant(0)
    for value in values:
        result = result + value
    return result


def _linear_scalar(x, weights, bias, constant):
    return tuple(tuple(_sum((a * b for a, b in zip(row, w)), constant) + constant(b)
                       for w, b in zip(weights, bias)) for row in x)


def _linear(x, weights, bias, constant):
    from .ordered_finite import FiniteWeights, ordered_linear
    if isinstance(weights, FiniteWeights):
        if any(type(z) is not _Finite for row in x for z in row):
            raise TypeError('finite linear weights cannot evaluate proof jets')
        try:
            result = ordered_linear([[z.value for z in row] for row in x],
                                    weights.array(), [float(z) for z in bias])
        except (ArithmeticError, ValueError) as exc:
            raise FiniteTargetError(str(exc)) from exc
        return tuple(tuple(_Finite(z) for z in row) for row in result)
    return _linear_scalar(x, weights, bias, constant)


def _norm(x, scale, bias, eps, constant):
    out = []
    for row in x:
        mean = _sum(row, constant) / constant(len(row))
        centered = tuple(z - mean for z in row)
        variance = _sum((z.square() for z in centered), constant) / constant(len(row))
        denominator = (variance + constant(eps)).sqrt()
        out.append(tuple((z / denominator) * constant(g) + constant(b)
                         for z, g, b in zip(centered, scale, bias)))
    return tuple(out)


def _add(x, y):
    return tuple(tuple(a + b for a, b in zip(ar, br)) for ar, br in zip(x, y))


def _softmax(scores, constant):
    """Smooth ideal derivatives; separately bound the stable finite schedule.

    The finite maximum is not differentiated. Softmax is invariant to the
    shift in real arithmetic. Its infinity-to-infinity Jacobian norm is at
    most 1/2. The finite schedule always contains an exact exp(0)=1 term.
    """
    if len(scores) > 2**53:
        raise UnsupportedCertificate("softmax length exceeds the exact integer summation bound")
    if isinstance(scores[0], _Finite):
        maximum = max(scores, key=lambda x: x.value)
        terms = tuple((x - maximum).exp() for x in scores)
        denominator = _sum(terms, constant)
        return tuple(x / denominator for x in terms)
    if len(scores) == 1:
        return (Jet.constant(ONE, len(scores[0].gradient), scores[0].bits),)
    bits, rank, n = scores[0].bits, len(scores[0].gradient), len(scores)
    zero = _interval(ZERO, bits)
    shift = max(x.value.hi for x in scores)
    terms = tuple((x.value - shift).exp() for x in scores)
    denominator = sum(terms, zero)
    if denominator.lo <= 0:
        raise UnsupportedCertificate('softmax interval cannot prove a positive denominator')
    probabilities = tuple(ci.Interval(max(ZERO, (x / denominator).lo),
                                      min(ONE, (x / denominator).hi), bits=bits) for x in terms)
    mean_g = tuple(sum((p * x.gradient[t] for p,x in zip(probabilities,scores)), zero) for t in range(rank))
    mean_h = tuple(tuple(sum((p*x.hessian[t][u] for p,x in zip(probabilities,scores)), zero)
                         for u in range(rank)) for t in range(rank))
    covariance = tuple(tuple(sum((p*x.gradient[t]*x.gradient[u] for p,x in zip(probabilities,scores)), zero)
                             - mean_g[t]*mean_g[u] for u in range(rank)) for t in range(rank))
    finite_ranges = tuple(x.expanded() for x in scores)
    span = max(x.hi for x in finite_ranges) - min(x.lo for x in finite_ranges)
    if span > MAX:
        raise UnsupportedCertificate('softmax subtraction may overflow')
    shift_error = U * span + TINY
    exp_error = shift_error + U + TINY
    # For n<=2**53, RN monotonicity and exp terms<=1 give partial sums<=k.
    # Thus no denominator addition overflows. Both denominators are >=1.
    sum_error = n * exp_error + n * U * n * (1 + exp_error) + n * TINY
    error = _ceil(max(x.error for x in scores)/2 + exp_error + sum_error + U + TINY, bits)
    out=[]
    for p,x in zip(probabilities,scores):
        centered=tuple(x.gradient[t]-mean_g[t] for t in range(rank))
        grad=tuple(p*g for g in centered)
        hess=tuple(tuple(p*(centered[t]*centered[u]+x.hessian[t][u]-mean_h[t][u]-covariance[t][u])
                         for u in range(rank)) for t in range(rank))
        out.append(Jet(p,grad,hess,error))
    return tuple(out)


def _attention(qkv, width, heads, constant):
    hd = width // heads
    divisor = constant(hd).sqrt()
    out = []
    for token in range(len(qkv)):
        row = []
        for head in range(heads):
            start = head * hd
            query = qkv[token][start:start + hd]
            scores = tuple(_sum((a * b for a, b in zip(query, qkv[key][width + start:width + start + hd])), constant)
                           / divisor for key in range(token + 1))
            probs = _softmax(scores, constant)
            for k in range(hd):
                row.append(_sum((p * qkv[key][2 * width + start + k] for key, p in enumerate(probs)), constant))
        out.append(tuple(row))
    return tuple(out)


class _StageWeights(Mapping):
    """Create one stage matrix on access, without retaining parameter wrappers.

    The executor reads each required matrix once. Its scalar operation order
    stays unchanged. Unused later matrices are never constructed.
    """
    def __init__(self, stages, factory):
        self._stages = tuple(stages)
        self._factory = factory

    def __getitem__(self, stage):
        if stage not in self._stages:
            raise KeyError(stage)
        return self._factory(stage)

    def __iter__(self):
        return iter(self._stages)

    def __len__(self):
        return len(self._stages)


def _execute(base, tokens, weights, constant, stop):
    cfg = base.config
    hidden = tuple(tuple(constant(a) + constant(b) for a, b in zip(base._token_embeddings[t], base._position_embeddings[p]))
                   for p, t in enumerate(tokens))
    for index, block in enumerate(base._blocks):
        pre = f'block.{index:04d}.'
        norm = _norm(hidden, block['norm1_scale'], block['norm1_bias'], cfg.layernorm_epsilon, constant)
        stage = pre + 'qkv'
        if stop == stage: return norm
        qkv = _linear(norm, weights[stage], block['qkv_bias'], constant)
        mixed = _attention(qkv, cfg.model_width, cfg.head_count, constant)
        stage = pre + 'attn_out'
        if stop == stage: return mixed
        hidden = _add(hidden, _linear(mixed, weights[stage], block['attn_out_bias'], constant))
        norm = _norm(hidden, block['norm2_scale'], block['norm2_bias'], cfg.layernorm_epsilon, constant)
        stage = pre + 'mlp_up'
        if stop == stage: return norm
        up = _linear(norm, weights[stage], block['mlp_up_bias'], constant)
        if getattr(cfg, 'activation', 'gelu') == 'gelu':
            divisor = constant(2).sqrt()
            activated = tuple(tuple((constant(Q(1, 2)) * x) * (1 + (x / divisor).erf()) for x in row) for row in up)
        else:
            # Bind a binary64 constant, rather than claim equality to libm pi.
            c = constant(float.fromhex('0x1.9884533d43651p-1'))
            activated = tuple(tuple((constant(Q(1, 2)) * x) * (1 + (c * (x + constant(0.044715) * x * x * x)).tanh())
                                   for x in row) for row in up)
        stage = pre + 'mlp_down'
        if stop == stage: return activated
        hidden = _add(hidden, _linear(activated, weights[stage], block['mlp_down_bias'], constant))
    norm = _norm(hidden, base._final_norm_scale, base._final_norm_bias, cfg.layernorm_epsilon, constant)
    from .ordered_finite import FiniteWeights
    head = FiniteWeights(base._lm_head) if type(constant(0)) is _Finite else tuple(tuple(constant(x) for x in row) for row in base._lm_head)
    return _linear(norm, head, base._lm_head_bias, constant)


class CertifiedDecoder:
    """Immutable wrapper defining a separate, certifiable finite target."""
    def __setattr__(self, key, value):
        if getattr(self, '_sealed', False): raise AttributeError('certified decoder is immutable')
        object.__setattr__(self, key, value)

    def __init__(self, base: DeterministicDecoder):
        if not isinstance(base, DeterministicDecoder): raise TypeError('base must be DeterministicDecoder')
        self.base = base
        self.config = base.config
        self.stage_ids = base.stage_ids
        self._manifest = {
            'schema': 'certified-scalar-decoder-v1', 'base_parameters': base.kernel_manifest,
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'primitive_source_sha256': hashlib.sha256(Path(ci.__file__).read_bytes()).hexdigest(),
            'linear_source_sha256': hashlib.sha256(Path(__file__).with_name('ordered_finite.py').read_bytes()).hexdigest(),
            'linear_schedule': 'binary64 coordinate-order multiply then add; independent outputs batched; no BLAS',
            'nonlinear': 'proved correctly rounded exp/sqrt/erf/tanh; unresolved rounding aborts',
            'softmax': 'causal inclusive; finite max shift; exp; sequential sum; divide; smooth derivative with separate roundoff proof',
            'target': 'exact-statistic V_cert; distinct from prior libm V',
            'gelu_new_coefficient_hex': '0x1.9884533d43651p-1',
        }
        self.evaluator_id = 'certified-decoder-v1:' + hashlib.sha256(_json_bytes(self._manifest)).hexdigest()
        self.reference_id = self.evaluator_id + ':base'
        self._sealed = True

    @property
    def kernel_manifest(self): return json.loads(_json_bytes(self._manifest))
    def stage_weights(self, stage): return self.base.stage_weights(stage)
    def dependencies(self, stage): return self.base.dependencies(stage)
    def record_payload(self, tokens): return self.base.record_payload(tokens)
    def decode_payload(self, payload): return self.base.decode_payload(payload)

    def _eval(self, tokens, prefix, stop):
        _check_runtime()
        installed = self.base._prefix(prefix)
        from .ordered_finite import FiniteWeights
        weights = _StageWeights(self.stage_ids, lambda s: FiniteWeights(installed.get(s, self.base._float_weights[s])))
        return _execute(self.base, self.base._tokens(tokens), weights, lambda x: _Finite(float(x)), stop)

    def stage_features(self, stage, tokens, prefix=None):
        if stage not in self.stage_ids: raise KeyError(stage)
        rows = self._eval(tokens, prefix, stage)
        return tuple(tuple(Q.from_float(row[k].value) for row in rows) for k in range(len(rows[0])))

    def logits(self, tokens, prefix=None):
        return tuple(tuple(x.value for x in row) for row in self._eval(tokens, prefix, None))

    def exact_logits(self, tokens, prefix=None):
        return tuple(tuple(Q.from_float(x) for x in row) for row in self.logits(tokens, prefix))

    def make_repair_service(self, grids_by_stage, chart, *, ridge=1, normalization=1, group_count=8,
                            response_tier="linear"):
        """Build the compact aggregate service with automatically proved moments."""
        from .aggregate_response_service import AggregateRepairService
        provider = AutomaticResponseProvider(self, chart)
        if set(grids_by_stage) != set(self.stage_ids): raise ValueError('grids must cover every stage')
        stages = tuple(StageSpec(s, self.dependencies(s), self.stage_weights(s),
                                 tuple(tuple(g) for g in grids_by_stage[s]), ridge, normalization) for s in self.stage_ids)
        job = JobSpec(stages, self.evaluator_id, provider.reference_id, group_count)
        def evaluate(record, stage, prefix):
            if prefix.manifest_digest != job.manifest_digest: raise ValueError('foreign evaluator prefix')
            return self.stage_features(stage.stage_id, self.decode_payload(record.payload), prefix.as_mapping())
        if response_tier not in ("linear", "quadratic"):
            raise ValueError('unsupported response tier')
        extract = provider.intrinsic_moments if response_tier == "linear" else provider.quadratic_intrinsic_moments
        return AggregateRepairService(job, evaluate, extract, provider.contracts, provider.query,
                                      provider_id=provider.provider_id, extractor_id=provider.reference_id,
                                      response_tier=response_tier)


@dataclass(frozen=True)
class AffineChart:
    """Fixed directions and a convex coefficient box, fixed before corpus use.

    Directions map stage IDs to exact matrices. Missing stages have zero
    direction. Their independence remains a provenance requirement. Numerical
    errors and derivatives are computed automatically, never supplied here.
    """
    directions: tuple[Mapping[str, Sequence[Sequence[int | Q]]], ...]
    radii: tuple[Q, ...]
    provenance: str
    precision_bits: int = 96

    def __post_init__(self):
        if type(self.precision_bits) is not int or self.precision_bits < 64:
            raise ValueError('precision_bits must be an integer at least 64')
        if not self.provenance: raise ValueError('fixed pre-corpus chart provenance is required')
        if type(self.provenance) is not str:
            raise TypeError("chart provenance must be text")
        if any(type(x) is not int and not isinstance(x, Q) for x in self.radii):
            raise TypeError("chart radii require exact rationals")
        radii = tuple(Q(x) for x in self.radii)
        if len(radii) != len(self.directions) or any(x < 0 for x in radii):
            raise ValueError('one nonnegative radius is required per direction')
        dirs = []
        for direction in self.directions:
            frozen = {}
            for stage, matrix in direction.items():
                if any(type(x) is not int and not isinstance(x, Q) for row in matrix for x in row):
                    raise TypeError('chart directions require exact rationals')
                frozen[stage] = tuple(tuple(Q(x) for x in row) for row in matrix)
            dirs.append(MappingProxyType(frozen))
        object.__setattr__(self, 'directions', tuple(dirs))
        object.__setattr__(self, 'radii', radii)


def _solve(rows, right, rank):
    """Exact RREF; free variables zero; abstain if this solution misses the box."""
    matrix = [list(a) + [b] for a, b in zip(rows, right)]
    pivots, top = [], 0
    for col in range(rank):
        found = next((i for i in range(top, len(matrix)) if matrix[i][col]), None)
        if found is None: continue
        matrix[top], matrix[found] = matrix[found], matrix[top]
        value = matrix[top][col]
        matrix[top] = [x / value for x in matrix[top]]
        for i in range(len(matrix)):
            if i != top and matrix[i][col]:
                value = matrix[i][col]
                matrix[i] = [x - value * y for x, y in zip(matrix[i], matrix[top])]
        pivots.append(col)
        top += 1
    if any(not any(row[:-1]) and row[-1] for row in matrix): return None
    result = [ZERO] * rank
    for i, col in enumerate(pivots): result[col] = matrix[i][-1]
    return tuple(result)


class AutomaticResponseProvider:
    """Intrinsic Taylor jets plus proved numerical and curvature descriptors."""
    def __setattr__(self, key, value):
        if getattr(self, '_sealed', False): raise AttributeError('response provider is immutable')
        object.__setattr__(self, key, value)

    def __init__(self, decoder: CertifiedDecoder, chart: AffineChart):
        if not isinstance(decoder, CertifiedDecoder) or not isinstance(chart, AffineChart):
            raise TypeError('provider requires a certified decoder and fixed chart')
        self.decoder, self.chart = decoder, chart
        for direction in chart.directions:
            if set(direction) - set(decoder.stage_ids): raise ValueError('chart names unknown stage')
            for stage, matrix in direction.items():
                base = decoder.stage_weights(stage)
                if len(matrix) != len(base) or any(len(row) != len(base[0]) for row in matrix):
                    raise ValueError('chart direction matrix has wrong shape')
        payload = {'decoder': decoder.evaluator_id, 'directions': _serial_exact(chart.directions),
                   'radii': _serial_exact(chart.radii), 'provenance': chart.provenance,
                   'bits': chart.precision_bits, 'proof': 'interval-second-order-ad-binary64-error-v1'}
        self.reference_id = 'automatic-response:' + hashlib.sha256(_json_bytes(payload)).hexdigest()
        self.provider_id = self.reference_id + ':linear-gram'
        rank = len(chart.directions)
        self.contracts = MappingProxyType({stage: ResponseStageContract(
            ResponseBasis(self.reference_id + ':' + stage + ':jet', len(decoder.stage_weights(stage)[0]), rank + 1, True),
            ResponseBasis(self.reference_id + ':' + stage + ':error', 1, rank + 3, True),
            sum((r * r for r in chart.radii), ZERO)) for stage in decoder.stage_ids})
        self._sealed = True

    def coefficients(self, stage_id, prefix):
        from .service_telemetry import provider_diagnostic
        _check_runtime()
        installed = self.decoder.base._prefix(prefix)
        rows, rhs = [], []
        for stage in self.decoder.dependencies(stage_id):
            base = self.decoder.base._float_weights[stage]
            target = installed.get(stage, base)
            for i, row in enumerate(base):
                for j, x in enumerate(row):
                    rows.append(tuple(direction[stage][i][j] if stage in direction else ZERO for direction in self.chart.directions))
                    rhs.append(Q.from_float(target[i][j]) - Q.from_float(x))
        solution = _solve(rows, rhs, len(self.chart.directions))
        if solution is None:
            provider_diagnostic(stage_id, 'provider_domain_fit', build=lambda cap: {
                'status': 'inconsistent_affine_span', 'coefficient_count': len(self.chart.directions),
                'equation_count': len(rows)})
            return None
        if any(abs(a) > r for a, r in zip(solution, self.chart.radii)):
            provider_diagnostic(stage_id, 'provider_domain_fit', build=lambda cap: {
                'status': 'selected_solution_outside_box', 'coefficient_count': len(solution),
                'violations': sum(abs(a) > r for a, r in zip(solution, self.chart.radii)),
                'samples': [{'coefficient': a, 'radius': r} for a, r in islice(zip(solution, self.chart.radii), cap)]})
            return None
        provider_diagnostic(stage_id, 'provider_domain_fit', build=lambda cap: {
            'status': 'exact_fit', 'coefficient_count': len(solution), 'equation_count': len(rows)})
        return solution

    def query(self, context):
        coefficients = self.coefficients(context.stage.stage_id, context.prefix.as_mapping())
        if coefficients is None: return UnknownBound('canonical affine fit failed or its selected coefficients exceed the box')
        return ResponseQuery(context.binding, coefficients, ZERO,
                             'automatic interval jets, full mixed curvature, binary64 error, and exact ancestor chart fit')

    def feature_jets(self, stage_id, tokens, *, region: bool):
        _check_runtime()
        if stage_id not in self.decoder.stage_ids: raise KeyError(stage_id)
        bits, rank = self.chart.precision_bits, len(self.chart.directions)
        def constant(x):
            return Jet.constant(Q.from_float(float(x)), rank, bits)
        z = _interval(ZERO, bits)
        def stage_weights(stage):
            matrix = []
            for i, row in enumerate(self.decoder.base._float_weights[stage]):
                out = []
                for j, value in enumerate(row):
                    grad = tuple(_interval(direction[stage][i][j] if stage in direction else ZERO, bits)
                                 for direction in self.chart.directions)
                    v = _interval(Q.from_float(value), bits)
                    if region:
                        for derivative, radius in zip(grad, self.chart.radii):
                            v = v + derivative * ci.Interval(-radius, radius, bits=bits)
                    out.append(Jet(v, grad, tuple((z,) * rank for _ in range(rank))))
                matrix.append(tuple(out))
            return tuple(matrix)
        weights = _StageWeights(self.decoder.stage_ids, stage_weights)
        rows = _execute(self.decoder.base, self.decoder.base._tokens(tokens), weights, constant, stage_id)
        return tuple(tuple(row[k] for row in rows) for k in range(len(rows[0])))

    def intrinsic_moments(self, record, stage):
        """Read only this supplied record; return unavailable if proof fails."""
        return self._intrinsic_moments(record, stage, quadratic=False)

    def quadratic_intrinsic_moments(self, record, stage):
        """Store all affine feature cross-moments for the quadratic control."""
        return self._intrinsic_moments(record, stage, quadratic=True)

    def _intrinsic_moments(self, record, stage, *, quadratic):
        from .service_telemetry import provider_diagnostic
        tokens = self.decoder.decode_payload(record.payload)
        proof_phase = 'center_jets'
        try:
            center = self.feature_jets(stage.stage_id, tokens, region=False)
            proof_phase = 'region_jets'
            region = self.feature_jets(stage.stage_id, tokens, region=True)
        except (ArithmeticError, ValueError, OverflowError) as exc:
            provider_diagnostic(stage.stage_id, 'provider_extraction', build=lambda cap: {
                'status': 'unavailable', 'proof_phase': proof_phase,
                'failure_type': type(exc).__name__, 'reason': str(exc)})
            return None
        rank, bits = len(self.chart.directions), self.chart.precision_bits
        def midpoint(interval): return (interval.lo + interval.hi) / 2
        features = [tuple(tuple(midpoint(x.value) for x in row) for row in center)]
        features += [tuple(tuple(midpoint(x.gradient[t]) for x in row) for row in center) for t in range(rank)]
        def norm(values): return dyadic_sqrt_upper(sum((v * v for v in values), ZERO), bits)
        e0 = norm((x.value.hi - x.value.lo) / 2 for row in center for x in row)
        errors = [norm((x.gradient[t].hi - x.gradient[t].lo) / 2 for row in center for x in row) for t in range(rank)]
        nu = norm(x.error for row in region for x in row)
        hessian = norm(h.abs_bound() for row in region for x in row for hs in x.hessian for h in hs)
        descriptors = [nu + e0] + errors + [hessian, ZERO]
        provider_diagnostic(stage.stage_id, 'provider_error_components', build=lambda cap: {
            'status': 'available', 'provider': 'affine_response', 'finite_error': nu,
            'center_error': e0, 'mixed_hessian_bound': hessian,
            'gradient_error_count': len(errors), 'gradient_error_samples': errors[:cap],
            'record_content_sha256': record.content_digest, 'precision_bits': bits,
            'numerical_values_are_upper_bounds': True})
        contract = self.contracts[stage.stage_id]
        make_moments = record_moments if quadratic else linear_record_moments
        response = make_moments(contract.response_basis, record.record_id, record.content_digest, features)
        error = record_moments(contract.error_basis, record.record_id, record.content_digest,
                               tuple(((v,),) for v in descriptors))
        return response, error


__all__ = ['CertifiedDecoder', 'AffineChart', 'AutomaticResponseProvider', 'Jet', 'UnsupportedCertificate']
