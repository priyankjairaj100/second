"""Shared exact stage dispatch under a new, explicit V43 resource policy.

Every arm can use the same dispatcher. Geometry chooses a token solver when
4*tokens <= width and streamed primal otherwise; only admitted candidates can
run. This is a prospective rule, not a measured timing crossover. Trusted Gram
inputs use the unchanged direct-Gram solver. There is no numerical cross-route
retry, approximate point substitution, or hidden neural replay. A caller must
reserve any fresh fallback and charge its complete traversal separately.

The policy defaults to 16 GiB process, 8 GiB explicit arrays, 64 billion stage
structural units, and one trillion request units. These are new allowances,
not reused empirical grants. Array/work admission includes complete bounded
row fallbacks and dispatcher copies. Callers declare other live residency and
must enforce the OS limit externally; these proxies do not prove process RSS
or completion. RequestLedger reserves each planned operation cumulatively.

Blocks are pairs of binary64 (width, tokens) arrays. ``kind='point'`` requires
equal endpoints; ``kind='box'`` certifies every realization without assuming
that the midpoint is the true feature. Containment and source provenance are
the service/preparer's obligations, not established by this numerical adapter.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
import math
import time

import numpy as np

from research_v35.exact_gram import GramAdmissionError, GramBudget, require_trusted_gram
from research_v37.direct_gram_ball import assess_direct_gram_ball_budget
from research_v39.scaled_gram_ball import certify_exact_gram_ball
from research_v40.streamed_primal_ball import assess_streamed, certify_streamed_primal_ball
from src.adaptive_calibration_v30 import AdaptiveBudget, assess_routes, quantize_adaptive_dyadic_rows
from src.dyadic_row_quantizer import dyadic_row_scales
from src.low_rank_certified import LowRankUnresolved
from src.native_box_coefficients_v31 import NativeBoxCoefficientBudget, assess_native_box_coefficients
from src.native_token_coefficients_v30 import NativeCoefficientBudget, assess_native_coefficients
from src.ordered_finite import FiniteWeights
from src.primal_certificate_v30 import PrimalBudget
from src.sparse_box_certificate_v30 import SparseCertificateBudget, _workspace_allowance
from src.sparse_box_certificate_v31 import certify_sparse_ball_dyadic_box
from src.token_box_certificate import TokenBoxUnresolved


def _int(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(name + ' has an invalid integer limit')
    return value


def _digest(value, name):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(name + ' must be a lowercase SHA-256 digest')


def _rational(value, name):
    if type(value) is not int and type(value) is not Fraction:
        raise TypeError(name + ' must be an exact integer or Fraction')
    value = Fraction(value)
    if value <= 0:
        raise ValueError(name + ' must be positive')
    return value


def _weight_digest(values):
    # Same identity framing as src.binary64_identity, accepting already finite
    # binary64 arrays. Each signed-zero word is preserved in this identity.
    digest = hashlib.sha256(b'binary64-matrix-little-endian-row-major-v1\0')
    digest.update(json.dumps(list(values.shape), separators=(',', ':')).encode('ascii'))
    digest.update(b'\0')
    for start in range(0, len(values), 64):
        digest.update(values[start:start + 64].astype('<f8', copy=False).tobytes(order='C'))
    return digest.hexdigest()


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    target_sha256: str
    rows: int
    width: int
    scale_values: tuple
    ridge: Fraction
    normalization: Fraction
    weights_sha256: str
    bits: int = 4
    significant_bits: int = 24

    def __post_init__(self):
        if type(self.stage_id) is not str or not self.stage_id:
            raise ValueError('stage ID must be nonempty')
        _digest(self.target_sha256, 'target')
        _digest(self.weights_sha256, 'weights')
        _int(self.rows, 'rows')
        _int(self.width, 'width')
        if self.width > 2**20:
            raise ValueError('width exceeds the native proof limit')
        if type(self.bits) is not int or self.bits != 4 or type(self.significant_bits) is not int or self.significant_bits != 24:
            raise ValueError('V43 dispatch requires four-bit canonical dyadic24 row grids')
        scales = tuple(self.scale_values)
        if len(scales) != self.rows or any(type(v) is not float or not math.isfinite(v) or v <= 0 for v in scales):
            raise ValueError('invalid complete canonical scale tuple')
        object.__setattr__(self, 'scale_values', scales)
        object.__setattr__(self, 'ridge', _rational(self.ridge, 'ridge'))
        object.__setattr__(self, 'normalization', _rational(self.normalization, 'normalization'))

    @classmethod
    def from_stage(cls, stage, *, target_sha256):
        weights = FiniteWeights(stage.weights).array()
        if weights.ndim != 2 or not weights.size or not np.isfinite(weights).all():
            raise ValueError('stage must have finite nonempty binary64 weights')
        return cls(stage.stage_id, target_sha256, *weights.shape, tuple(stage.scale_values),
                   stage.ridge, stage.normalization, _weight_digest(weights), stage.bits)

    @classmethod
    def from_manifest(cls, entry, *, target_sha256, bits=4):
        """Bind a published stage entry without loading its weight matrix."""
        if entry.get('grid_axis') != 'output_row' or entry.get('significant_bits') != 24:
            raise ValueError('unsupported manifest row grid')
        return cls(entry['stage_id'], target_sha256, *entry['shape'],
            tuple(float.fromhex(x) for x in entry['row_scale_hex']),
            Fraction(*entry['ridge']), Fraction(*entry['normalization']), entry['weights_sha256'], bits)


@dataclass(frozen=True)
class ResourcePolicy:
    max_process_bytes: int = 16 * 2**30
    max_array_bytes: int = 8 * 2**30
    max_stage_work_units: int = 64_000_000_000
    max_request_work_units: int = 1_000_000_000_000
    max_point_refinement_coordinates: int = 16
    max_box_preconditioned_coordinates: int = 16
    max_box_rounds: int = 4

    def __post_init__(self):
        for name, value in asdict(self).items():
            _int(value, name, 0 if name in ('max_point_refinement_coordinates',
                 'max_box_preconditioned_coordinates', 'max_box_rounds') else 1)
        if self.max_array_bytes > self.max_process_bytes:
            raise ValueError('array limit exceeds declared process limit')


class DispatchRefused(TokenBoxUnresolved):
    def __init__(self, message, admission, *, diagnostics=None):
        super().__init__(message)
        self.admission = admission
        self.diagnostics = {} if diagnostics is None else diagnostics


@dataclass(frozen=True)
class DispatchResult:
    codes: object
    route: str
    admission: dict
    solver_result: object


class RequestLedger:
    """Cumulative prospective reservations; refused/failed work is never refunded."""
    def __init__(self, policy=ResourcePolicy()):
        if type(policy) is not ResourcePolicy:
            raise TypeError('policy must be ResourcePolicy')
        self.policy, self.work_units, self.reservations = policy, 0, []

    def reserve(self, admission):
        if admission.get('policy') != asdict(self.policy) or admission.get('admitted') is not True:
            raise DispatchRefused('request cannot reserve an incompatible or refused stage', admission)
        units = _int(admission.get('work_units'), 'reservation work', 0)
        if self.work_units + units > self.policy.max_request_work_units:
            raise DispatchRefused('cumulative request work allowance exhausted', admission,
                diagnostics=dict(reserved=self.work_units, required=units,
                    limit=self.policy.max_request_work_units))
        self.work_units += units
        self.reservations.append(dict(stage_id=admission['stage_id'], kind=admission['kind'],
                                      route=admission['selected_route'], work_units=units))


def assess_stage(spec, total_tokens, *, kind='point', block_tokens=128, max_blocks=None,
                 policy=ResourcePolicy(), resident_bytes=0, route='auto'):
    """Admit complete solver schedules plus dispatcher arrays before block reads.

    resident_bytes excludes arrays allocated by this adapter, and includes all
    caller-held feature/state/model/Gram storage. Compiler, Python and BLAS
    overhead remain subject to the caller's externally enforced process cap.
    Structural work is an accounting proxy, never a runtime prediction.
    """
    if type(spec) is not StageSpec or type(policy) is not ResourcePolicy:
        raise TypeError('StageSpec and ResourcePolicy are required')
    _int(total_tokens, 'total_tokens', 0)
    _int(block_tokens, 'block_tokens')
    _int(resident_bytes, 'resident_bytes', 0)
    if total_tokens > 2**20 or total_tokens > spec.normalization:
        raise ValueError('tokens exceed native proof limit or original calibration normalization')
    if kind not in ('point', 'box', 'gram') or route not in ('auto', 'token', 'streamed', 'direct_gram'):
        raise ValueError('unknown evidence kind or route')
    if kind == 'gram' and route not in ('auto', 'direct_gram') or kind != 'gram' and route == 'direct_gram':
        raise ValueError('route is incompatible with evidence access')
    max_blocks = total_tokens if max_blocks is None else max_blocks
    _int(max_blocks, 'max_blocks', 0)
    if max_blocks * block_tokens < total_tokens:
        raise ValueError('block count cannot cover total_tokens')
    max_blocks = min(max_blocks, total_tokens)
    rows, width, tokens = spec.rows, spec.width, total_tokens
    pbudget = PrimalBudget(max_workspace_bytes=policy.max_array_bytes,
                          max_work_units=policy.max_stage_work_units)
    adaptive = AdaptiveBudget(max_workspace_bytes=policy.max_array_bytes,
        max_work_units=policy.max_stage_work_units,
        max_refinement_coordinates=policy.max_point_refinement_coordinates)
    candidates = {}
    if kind == 'gram':
        candidates['direct_gram'] = assess_direct_gram_ball_budget(rows=rows, width=width,
            bits=spec.bits, budget=pbudget)
    else:
        candidates['streamed'] = assess_streamed(rows=rows, width=width, tokens=tokens,
            block_tokens=block_tokens, max_blocks=max_blocks, bits=spec.bits, budget=pbudget)
        if kind == 'point':
            full = assess_routes(rows, width, tokens, budget=adaptive)['routes']['token']
            coeff = assess_native_coefficients(width, tokens, budget=NativeCoefficientBudget(
                max_work_units=policy.max_stage_work_units, max_workspace_bytes=policy.max_array_bytes))
            candidates['token'] = dict(full, coefficient_assessment=coeff)
        else:
            rounds = min(policy.max_box_rounds, width, policy.max_box_preconditioned_coordinates)
            checked = min(width, policy.max_box_preconditioned_coordinates) if rounds else 0
            row_units = rows * width * (2 * tokens + spec.bits + 1)
            initial = width * tokens**2 + row_units + width * tokens + rows * (1 << spec.bits)
            work = initial + (1 + rounds) * row_units + rounds * width * tokens**2 + checked * tokens**3
            coeff = assess_native_box_coefficients(width, tokens, budget=NativeBoxCoefficientBudget(
                max_work_units=policy.max_stage_work_units, max_workspace_bytes=policy.max_array_bytes))
            candidates['token'] = dict(work_units=max(work, coeff['work_units']),
                explicit_array_bytes=max(_workspace_allowance(rows, width, tokens, 1 << spec.bits,
                    min(width, policy.max_box_preconditioned_coordinates)), coeff['explicit_array_bytes']),
                complete_bounded_path_work_units=work, coefficient_assessment=coeff)
    for name, candidate in candidates.items():
        # Private weight snapshot, identity hashing chunk, immutable result,
        # and block snapshot/assembly in addition to the solver's own envelope.
        extra = 32 * rows * width + 32 * width * min(tokens, block_tokens)
        if name == 'token':
            extra += 32 * width * tokens
        candidate['dispatcher_array_bytes'] = extra
        candidate['explicit_array_bytes'] += extra
        candidate['process_known_bytes'] = resident_bytes + candidate['explicit_array_bytes']
        reasons = []
        if candidate['work_units'] > policy.max_stage_work_units:
            reasons.append('complete solver work exceeds stage limit')
        if candidate['explicit_array_bytes'] > policy.max_array_bytes:
            reasons.append('solver and dispatcher arrays exceed array limit')
        if candidate['process_known_bytes'] > policy.max_process_bytes:
            reasons.append('declared residency plus arrays exceeds process limit')
        if not candidate.get('coefficient_assessment', {'admitted': True})['admitted']:
            reasons.append('native coefficient admission refused')
        candidate.update(admitted=not reasons, refusal_reason='; '.join(reasons),
            complete_rows_and_bounded_fallback_reserved=True)
    preferred = ['direct_gram'] if kind == 'gram' else (
        ['token', 'streamed'] if 4 * tokens <= width else ['streamed', 'token'])
    choices = preferred if route == 'auto' else [route]
    selected = next((name for name in choices if candidates[name]['admitted']), None)
    return dict(schema='exact-stage-dispatch-admission-v43', stage_id=spec.stage_id,
        target_sha256=spec.target_sha256, weights_sha256=spec.weights_sha256,
        rows=rows, width=width, total_tokens=tokens, kind=kind, block_tokens=block_tokens,
        max_blocks=max_blocks, policy=asdict(policy), resident_bytes=resident_bytes,
        candidates=candidates, selected_route=selected, admitted=selected is not None,
        work_units=candidates[selected]['work_units'] if selected else 0,
        explicit_array_bytes=candidates[selected]['explicit_array_bytes'] if selected else 0,
        selection_policy='token when 4*tokens <= width; otherwise streamed; admitted candidates only',
        whole_process_fit_guaranteed=False, process_cap_enforced_here=False,
        source_provenance_and_containment_verified_here=False)


def _weights(spec, weights):
    if type(weights) is not np.ndarray or weights.dtype != np.float64 or weights.shape != (spec.rows, spec.width):
        raise ValueError('weight dtype or shape differs from bound stage')
    snapshot = np.array(weights, dtype=np.float64, order='C', copy=True)
    if not np.isfinite(snapshot).all() or _weight_digest(snapshot) != spec.weights_sha256:
        raise ValueError('weight values differ from bound stage')
    if dyadic_row_scales(snapshot, spec.bits, spec.significant_bits) != spec.scale_values:
        raise ValueError('scales differ from canonical bound stage grid')
    return snapshot


def _blocks(blocks, spec, admission):
    seen = count = 0
    for block in blocks:
        if type(block) not in (tuple, list) or len(block) != 2:
            raise ValueError('each block must contain lower and upper arrays')
        lower, upper = block
        if count >= admission['max_blocks']:
            raise ValueError('too many feature blocks')
        for value in block:
            if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 2:
                raise ValueError('block endpoints must be binary64 matrices')
        if (lower.shape != upper.shape or lower.shape[0] != spec.width
                or not 1 <= lower.shape[1] <= admission['block_tokens']
                or seen + lower.shape[1] > admission['total_tokens']):
            raise ValueError('feature block dimensions differ from admitted extent')
        lower, upper = (np.array(v, dtype=np.float64, order='C', copy=True) for v in block)
        if not np.isfinite(lower).all() or not np.isfinite(upper).all() or np.any(lower > upper):
            raise ValueError('feature endpoints must be finite and ordered')
        if admission['kind'] == 'point' and not np.array_equal(lower, upper):
            raise ValueError('point evidence cannot contain uncertain feature boxes')
        seen += lower.shape[1]
        count += 1
        yield lower, upper
    if seen != admission['total_tokens']:
        raise ValueError('feature stream ended before the bound token total')


def _run(spec, weights, admission, operation):
    if not admission['admitted']:
        raise DispatchRefused('no complete stage solver fits the declared policy', admission)
    started = time.perf_counter_ns()
    weights = _weights(spec, weights)
    try:
        answer = operation(weights)
    except (TokenBoxUnresolved, LowRankUnresolved, GramAdmissionError) as error:
        raise DispatchRefused('certified stage refused: ' + str(error), admission,
            diagnostics=dict(elapsed_ns=time.perf_counter_ns() - started,
                error_type=type(error).__name__, solver_diagnostics=getattr(error, 'native_diagnostics',
                    getattr(error, 'native_ball_diagnostics', getattr(error, 'diagnostics', None))))) from error
    if answer.codes.shape != weights.shape or not np.isfinite(answer.codes).all():
        raise ArithmeticError('solver returned incomplete or nonfinite codes')
    codes = np.frombuffer(answer.codes.tobytes(order='C'), dtype=np.float64).reshape(weights.shape)
    return DispatchResult(codes, admission['selected_route'], admission, answer)


def solve_blocks(spec, weights, blocks, *, total_tokens, kind='point', block_tokens=128,
                 max_blocks=None, policy=ResourcePolicy(), resident_bytes=0, route='auto'):
    if kind not in ('point', 'box'):
        raise ValueError('block solves require point or box evidence')
    admission = assess_stage(spec, total_tokens, kind=kind, block_tokens=block_tokens,
        max_blocks=max_blocks, policy=policy, resident_bytes=resident_bytes, route=route)
    options = dict(scale_values=spec.scale_values, bits=spec.bits, significant_bits=spec.significant_bits,
                   ridge=spec.ridge, normalization=spec.normalization)

    def operation(private_weights):
        stream = _blocks(blocks, spec, admission)
        if admission['selected_route'] == 'streamed':
            return certify_streamed_primal_ball(private_weights, stream, total_tokens=total_tokens,
                block_tokens=block_tokens, max_blocks=admission['max_blocks'],
                budget=PrimalBudget(max_work_units=policy.max_stage_work_units,
                    max_workspace_bytes=policy.max_array_bytes), **options)
        lower = np.empty((spec.width, total_tokens), dtype=np.float64)
        upper = np.empty_like(lower)
        offset = 0
        for lo, hi in stream:
            lower[:, offset:offset + lo.shape[1]], upper[:, offset:offset + lo.shape[1]] = lo, hi
            offset += lo.shape[1]
        if kind == 'point':
            return quantize_adaptive_dyadic_rows(private_weights, lower, route='token',
                budget=AdaptiveBudget(max_workspace_bytes=policy.max_array_bytes,
                    max_work_units=policy.max_stage_work_units,
                    max_refinement_coordinates=policy.max_point_refinement_coordinates), **options)
        return certify_sparse_ball_dyadic_box(private_weights, lower, upper,
            coefficient_backend='native', allow_python_fallback=False,
            max_exact_rank=0, max_exact_coordinates=0, max_refinement_coordinates=0,
            budget=SparseCertificateBudget(max_work_units=admission['work_units'],
                max_workspace_bytes=policy.max_array_bytes,
                max_preconditioned_coordinates=policy.max_box_preconditioned_coordinates,
                max_rounds=policy.max_box_rounds), **options)
    return _run(spec, weights, admission, operation)


def solve_gram(spec, weights, gram, *, gram_budget=GramBudget(), policy=ResourcePolicy(), resident_bytes=0):
    require_trusted_gram(gram)
    if gram.width != spec.width or gram.normalization != spec.normalization:
        raise ValueError('trusted Gram width or original normalization differs from stage')
    admission = assess_stage(spec, gram.tokens, kind='gram', policy=policy, resident_bytes=resident_bytes)
    return _run(spec, weights, admission, lambda private_weights: certify_exact_gram_ball(
        private_weights, gram, spec.scale_values, ridge=spec.ridge, bits=spec.bits,
        significant_bits=spec.significant_bits, gram_budget=gram_budget,
        budget=PrimalBudget(max_work_units=policy.max_stage_work_units,
            max_workspace_bytes=policy.max_array_bytes)))
