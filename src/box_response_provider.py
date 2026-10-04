"""Corpus-independent parameter boxes with finite, constant response bounds.

This provider does not require a low-dimensional affine prefix. Its interval
proof can still fail or produce a bound too large for a decision certificate.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from . import certified_intervals as ci
from .certified_transformer import CertifiedDecoder, Jet, MAX, _StageWeights, _execute
from .linear_response import linear_record_moments
from .repair_service import UnknownBound
from .response_certificate import dyadic_sqrt_upper
from .response_moments import ResponseBasis, record_moments
from .response_service_adapter import ResponseQuery, ResponseStageContract
from .transformer_backend import _check_runtime, _json_bytes, _serial_exact

Q = Fraction
ZERO = Q(0)


def _exact(value):
    if type(value) is not int and not isinstance(value, Q):
        raise TypeError('box endpoints require exact rational values')
    return Q(value)


@dataclass(frozen=True)
class ParameterBox:
    """A fixed independent interval for each named weight coordinate.

    Missing stages keep their finite base weights. Independence from the
    calibration corpus is a construction requirement, not a user error bound.
    """
    bounds_by_stage: Mapping
    provenance: str
    precision_bits: int = 96

    def __post_init__(self):
        if type(self.provenance) is not str or not self.provenance:
            raise ValueError('a nonempty fixed-box provenance is required')
        if type(self.precision_bits) is not int or self.precision_bits < 64:
            raise ValueError('precision_bits must be an integer at least 64')
        if not isinstance(self.bounds_by_stage, Mapping):
            raise TypeError('box bounds must be a stage mapping')
        frozen = {}
        for stage, matrix in self.bounds_by_stage.items():
            if type(stage) is not str or not stage:
                raise ValueError('box stage IDs must be nonempty strings')
            rows = []
            for row in matrix:
                coordinates = []
                for pair in row:
                    if len(pair) != 2:
                        raise ValueError('each box coordinate requires two endpoints')
                    lo, hi = map(_exact, pair)
                    if not -MAX <= lo <= hi <= MAX:
                        raise ValueError('box endpoints must be ordered within finite binary64 range')
                    coordinates.append((lo, hi))
                if not coordinates:
                    raise ValueError('box rows must be nonempty')
                rows.append(tuple(coordinates))
            if not rows or any(len(row) != len(rows[0]) for row in rows):
                raise ValueError('box matrices must be nonempty and rectangular')
            frozen[stage] = tuple(rows)
        object.__setattr__(self, 'bounds_by_stage', MappingProxyType(frozen))

    def payload(self):
        return {'schema': 'fixed-parameter-box-v1', 'provenance': self.provenance,
                'precision_bits': self.precision_bits,
                'bounds_by_stage': _serial_exact(self.bounds_by_stage),
                'missing_stage_rule': 'finite base weights exactly'}

    def canonical_bytes(self):
        return _json_bytes(self.payload())

    @property
    def digest(self):
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def grid_box(decoder, target, provenance, precision_bits=96):
    """Enclose base and every installed frozen grid value, without corpus reads.

    The full-grid recipe uses each input coordinate's grid extrema. Values
    undergo the decoder's binary64 installation conversion before enclosure.
    """
    if not isinstance(decoder, CertifiedDecoder):
        raise TypeError('grid box requires a certified decoder')
    stages = tuple(target.stages)
    if tuple(stage.stage_id for stage in stages) != decoder.stage_ids:
        raise ValueError('target stages differ from decoder stages')
    used = {ancestor for stage in stages for ancestor in decoder.dependencies(stage.stage_id)}
    bounds = {}
    for stage in stages:
        if stage.stage_id not in used:
            continue
        base = decoder.base._float_weights[stage.stage_id]
        if len(stage.grids) != len(base[0]):
            raise ValueError('grid width differs from decoder stage')
        columns = []
        for grid in stage.grids:
            if not grid:
                raise ValueError('each coordinate requires a frozen grid')
            values = tuple(float(value) for value in grid)
            if any(not math.isfinite(value) for value in values):
                raise ValueError('frozen grid converts to a nonfinite value')
            columns.append((Q.from_float(min(values)), Q.from_float(max(values))))
        bounds[stage.stage_id] = tuple(tuple(
            (min(lo, Q.from_float(value)), max(hi, Q.from_float(value)))
            for value, (lo, hi) in zip(row, columns)) for row in base)
    return ParameterBox(bounds, provenance, precision_bits)


class BoxResponseProvider:
    """Prove constant rational feature anchors over a fixed parameter box."""
    def __setattr__(self, key, value):
        if getattr(self, '_sealed', False):
            raise AttributeError('box response provider is immutable')
        object.__setattr__(self, key, value)

    def __init__(self, decoder: CertifiedDecoder, box: ParameterBox):
        if not isinstance(decoder, CertifiedDecoder) or not isinstance(box, ParameterBox):
            raise TypeError('provider requires a certified decoder and fixed box')
        if set(box.bounds_by_stage) - set(decoder.stage_ids):
            raise ValueError('box names an unknown decoder stage')
        for stage, bounds in box.bounds_by_stage.items():
            base = decoder.stage_weights(stage)
            if len(bounds) != len(base) or any(len(row) != len(base[0]) for row in bounds):
                raise ValueError('box matrix shape differs from decoder stage')
        self.decoder, self.box = decoder, box
        payload = {'decoder': decoder.evaluator_id, 'box': box.payload(),
                   'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'proof': 'rank-zero-interval-finite-discrepancy-v1',
                   'anchor_policy': 'finite-base-on-base-only-domain; interval-midpoint-otherwise-v1'}
        self.reference_id = 'box-response:' + hashlib.sha256(_json_bytes(payload)).hexdigest()
        self.provider_id = self.reference_id + ':constant-gram'
        self.contracts = MappingProxyType({stage: ResponseStageContract(
            ResponseBasis(self.reference_id + ':' + stage + ':anchor', len(decoder.stage_weights(stage)[0]), 1, True),
            ResponseBasis(self.reference_id + ':' + stage + ':error', 1, 3, True), ZERO)
            for stage in decoder.stage_ids})
        self._sealed = True

    def contains_prefix(self, stage_id, prefix):
        _check_runtime()
        if stage_id not in self.decoder.stage_ids:
            raise KeyError(stage_id)
        installed = self.decoder.base._prefix(prefix)
        for stage in self.decoder.dependencies(stage_id):
            base = self.decoder.base._float_weights[stage]
            values = installed.get(stage, base)
            bounds = self.box.bounds_by_stage.get(stage)
            for i, row in enumerate(values):
                for j, value in enumerate(row):
                    q = Q.from_float(value)
                    lo, hi = bounds[i][j] if bounds is not None else (Q.from_float(base[i][j]),) * 2
                    if not lo <= q <= hi:
                        return False
        return True

    def query(self, context):
        if not self.contains_prefix(context.stage.stage_id, context.prefix.as_mapping()):
            return UnknownBound('installed finite ancestor weights lie outside the fixed parameter box')
        return ResponseQuery(context.binding, (), ZERO,
                             'constant hybrid anchor with uniform box interval error and complete finite prefix membership')

    def _parameter_weights(self, stage):
        bounds = self.box.bounds_by_stage.get(stage)
        bits = self.box.precision_bits
        if bounds is None:
            return tuple(tuple(Jet.constant(Q.from_float(value), 0, bits) for value in row)
                         for row in self.decoder.base._float_weights[stage])
        return tuple(tuple(Jet(ci.Interval(lo, hi, bits=bits), (), ()) for lo, hi in row) for row in bounds)

    def feature_enclosures(self, stage_id, tokens):
        """Return real intervals and uniform finite errors; proof failure raises."""
        _check_runtime()
        if stage_id not in self.decoder.stage_ids:
            raise KeyError(stage_id)
        def constant(value):
            return Jet.constant(Q.from_float(float(value)), 0, self.box.precision_bits)
        weights = _StageWeights(self.decoder.stage_ids, self._parameter_weights)
        rows = _execute(self.decoder.base, self.decoder.base._tokens(tokens), weights, constant, stage_id)
        return tuple(tuple(row[k] for row in rows) for k in range(len(rows[0])))

    def _base_only_domain(self, stage_id):
        for stage in self.decoder.dependencies(stage_id):
            bounds = self.box.bounds_by_stage.get(stage)
            if bounds is None:
                continue
            for row, limits in zip(self.decoder.base._float_weights[stage], bounds):
                for value, (lo, hi) in zip(row, limits):
                    if lo != hi or lo != Q.from_float(value):
                        return False
        return True

    def intrinsic_moments(self, record, stage):
        """Extract one record's additive proof data, or mark proof unavailable."""
        tokens = self.decoder.decode_payload(record.payload)
        try:
            if self._base_only_domain(stage.stage_id):
                # Identical installed ancestors execute the identical finite program.
                anchor = self.decoder.stage_features(stage.stage_id, tokens)
                epsilon = ZERO
            else:
                region = self.feature_enclosures(stage.stage_id, tokens)
                anchor = tuple(tuple((bound.value.lo + bound.value.hi) / 2 for bound in row) for row in region)
                square = sum(((bound.value.hi - bound.value.lo) / 2 + bound.error) ** 2
                             for row in region for bound in row)
                epsilon = dyadic_sqrt_upper(square, self.box.precision_bits)
        except (ArithmeticError, ValueError, OverflowError):
            return None
        contract = self.contracts[stage.stage_id]
        response = linear_record_moments(contract.response_basis, record.record_id, record.content_digest, (anchor,))
        error = record_moments(contract.error_basis, record.record_id, record.content_digest,
                               (((epsilon,),), ((ZERO,),), ((ZERO,),)))
        return response, error


__all__ = ['ParameterBox', 'grid_box', 'BoxResponseProvider']
