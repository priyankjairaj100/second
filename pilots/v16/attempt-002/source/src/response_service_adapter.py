"""Bind exact response moments to the complete sequential repair service.

This bridge is implemented, but it does not invent a neural Taylor theorem.
The intrinsic extractor and descriptor semantics are trusted fixed-program
contracts. The query callback must obtain coefficients from the NEW certified
prefix, and returns UNKNOWN when its chart/numerical premises are unavailable.
A configured coefficient-ball test is additionally checked exactly here.

This transparent implementation keeps both per-record moment payloads in the
canonical reference descriptors and rebuilds group totals at a request. Thus it
avoids retained NEURAL replay on a successful certificate but still reads and
sums O(N) stored moment payloads, with O(N r^2 d^2) stored rational entries for
quadratic feature responses. It does NOT inherit the aggregate-index module's
record-independent query cost. A persistent aggregate service extension would
need a separately declared canonical state/schema and deletion path.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
import json
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from .repair_service import (
    AbsoluteGramBound, BoundResult, GroupBinding, GroupContext, InvalidWitness,
    Record, ReferenceEvaluator, ReferenceSample, StageSpec, SurrogateProposal,
    TrustedBoundProvider, UnknownBound, UNKNOWN,
)
from .response_certificate import response_gram_enclosure
from .response_moments import RecordMoments, ResponseBasis, ResponseIndex


def _dump(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def encode_response_descriptor(response: RecordMoments, error: RecordMoments,
                               base_descriptor: bytes = b"") -> bytes:
    if type(base_descriptor) is not bytes:
        raise TypeError("base_descriptor must be bytes")
    if (response.record_id, response.source_digest) != (error.record_id, error.source_digest):
        raise ValueError("response/error moments must bind identical source records")
    return _dump({"schema": "service-response-descriptor-v1",
                  "response": response.canonical_bytes().decode("ascii"),
                  "error": error.canonical_bytes().decode("ascii"),
                  "base_descriptor": base_descriptor.hex()})


def decode_response_descriptor(payload: bytes) -> tuple[RecordMoments, RecordMoments, bytes]:
    if type(payload) is not bytes:
        raise TypeError("response descriptor must be bytes")
    value = json.loads(payload)
    if not isinstance(value, dict) or value.get("schema") != "service-response-descriptor-v1":
        raise ValueError("unsupported service response descriptor")
    response = RecordMoments.from_canonical_bytes(value["response"].encode("ascii"))
    error = RecordMoments.from_canonical_bytes(value["error"].encode("ascii"))
    base = bytes.fromhex(value["base_descriptor"])
    if encode_response_descriptor(response, error, base) != payload:
        raise ValueError("response descriptor is not canonically encoded")
    return response, error, base


def _unavailable_descriptor(kind: str, base_descriptor: bytes) -> bytes:
    return _dump({"schema": "service-response-unavailable-v1", "kind": kind,
                  "base_descriptor": base_descriptor.hex()})


def _is_unavailable(payload: bytes, kind: str) -> bool:
    """A declared lack of evidence is distinct from malformed claimed evidence."""
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, UnicodeError):
        return False
    if not isinstance(value, dict) or value.get("schema") != "service-response-unavailable-v1":
        return False
    if value.get("kind") != kind:
        raise ValueError("unavailable-response marker has a different tier")
    base = bytes.fromhex(value["base_descriptor"])
    if _unavailable_descriptor(kind, base) != payload:
        raise ValueError("unavailable-response marker is not canonical")
    return True


@dataclass(frozen=True)
class ResponseStageContract:
    response_basis: ResponseBasis
    error_basis: ResponseBasis
    # None permits an unbounded chart only under the trusted descriptor theorem.
    max_squared_coefficient_norm: Fraction | None = None

    def __post_init__(self) -> None:
        if self.error_basis.rows != 1 or self.error_basis.terms != self.response_basis.terms + 2:
            raise ValueError("error basis must have one row and r+3 descriptor terms")
        radius = self.max_squared_coefficient_norm
        if radius is not None:
            if type(radius) is int:
                radius = Fraction(radius)
            if not isinstance(radius, Fraction) or radius < 0:
                raise ValueError("chart squared radius must be a nonnegative exact rational")
            object.__setattr__(self, "max_squared_coefficient_norm", radius)


@dataclass(frozen=True)
class ResponseQuery:
    binding: GroupBinding
    coefficients: tuple[Fraction, ...]
    unrepresented_parameter_norm: Fraction = Fraction(0)
    justification: str = ""

    def __post_init__(self) -> None:
        def exact(x):
            if type(x) is int:
                return Fraction(x)
            if isinstance(x, Fraction):
                return x
            raise TypeError("response query scalars must be int or Fraction")
        object.__setattr__(self, "coefficients", tuple(exact(x) for x in self.coefficients))
        residual = exact(self.unrepresented_parameter_norm)
        if residual < 0:
            raise ValueError("unrepresented parameter norm cannot be negative")
        object.__setattr__(self, "unrepresented_parameter_norm", residual)
        if not isinstance(self.justification, str) or not self.justification:
            raise ValueError("response query must state its trusted chart/prefix premise")


def make_response_reference_evaluator(
    base_reference: ReferenceEvaluator,
    intrinsic_moments: Callable[[Record, StageSpec], tuple[RecordMoments, RecordMoments] | None],
) -> ReferenceEvaluator:
    """Attach corpus-independent response/error moments to retained descriptors.

    The surrounding job's reference_id MUST name this composite fixed extractor,
    including basis directions and descriptor/numerical contracts, not merely
    the underlying neural reference. The hook is called on setup/deleted records
    only. A None result stores a canonical unavailable marker with the base descriptor;
    the group provider then abstains and permits exact retained replay.
    """
    def reference(record: Record, stage: StageSpec) -> ReferenceSample:
        base = base_reference(record, stage)
        moments = intrinsic_moments(record, stage)
        if moments is None:
            return ReferenceSample(base.features, _unavailable_descriptor("quadratic", base.descriptor))
        if not isinstance(moments, tuple) or len(moments) != 2:
            raise TypeError("intrinsic_moments must return a response/error pair or None")
        response, error = moments
        if not isinstance(response, RecordMoments) or not isinstance(error, RecordMoments):
            raise TypeError("intrinsic response/error values must be RecordMoments")
        for item in (response, error):
            if item.record_id != record.record_id or item.source_digest != record.content_digest:
                raise ValueError("intrinsic moments do not bind the supplied raw record")
        if response.basis.rows != stage.width:
            raise ValueError("response basis dimension does not match the target stage")
        return ReferenceSample(base.features, encode_response_descriptor(response, error, base.descriptor))
    return reference


def make_response_provider(
    provider_id: str,
    manifest_digest: str,
    reference_id: str,
    contracts: Mapping[str, ResponseStageContract],
    query: Callable[[GroupContext], ResponseQuery | UnknownBound],
) -> TrustedBoundProvider:
    """Create a manifested provider that contracts stored response/error moments.

    Error descriptor validity (including both finite-program discrepancies) and
    corpus independence remain trusted premises. This function checks source,
    prefix, extractor bases, nonnegative exact scalars, the configured chart ball,
    and all arithmetic. An unsupported stage or out-of-chart query abstains.
    Malformed/stale claimed evidence raises InvalidWitness without committing.
    """
    fixed_contracts = MappingProxyType(dict(contracts))
    if not manifest_digest or not reference_id:
        raise ValueError("provider must pin target and composite reference identities")
    if any(not isinstance(c, ResponseStageContract) for c in fixed_contracts.values()):
        raise TypeError("contracts must contain ResponseStageContract values")

    def prove(ctx: GroupContext) -> BoundResult | SurrogateProposal:
        if (ctx.binding.manifest_digest != manifest_digest or ctx.binding.reference_id != reference_id
                or ctx.prefix.manifest_digest != manifest_digest or ctx.prefix.digest != ctx.binding.prefix_digest):
            raise InvalidWitness("response provider received a foreign target/reference/prefix")
        contract = fixed_contracts.get(ctx.stage.stage_id)
        if contract is None:
            return UNKNOWN
        if contract.response_basis.rows != ctx.stage.width:
            raise InvalidWitness("response contract dimension differs from target stage")
        request = query(ctx)
        if isinstance(request, UnknownBound):
            return request
        if not isinstance(request, ResponseQuery) or request.binding != ctx.binding:
            raise InvalidWitness("response query must bind the exact current group/prefix")
        if len(request.coefficients) != contract.response_basis.terms - 1:
            raise InvalidWitness("response query has the wrong coefficient dimension")
        radius = contract.max_squared_coefficient_norm
        if radius is not None and sum((a * a for a in request.coefficients), Fraction(0)) > radius:
            return UnknownBound("candidate prefix lies outside the proved response chart")
        response_records, error_records = [], []
        for record in ctx.records:
            try:
                payload = record.descriptor_for(ctx.stage.stage_id)
                if _is_unavailable(payload, "quadratic"):
                    return UnknownBound("intrinsic response evidence is unavailable for this retained group")
                response, error, _ = decode_response_descriptor(payload)
            except (KeyError, TypeError, ValueError, UnicodeError) as exc:
                raise InvalidWitness("invalid intrinsic response descriptor") from exc
            if response.basis != contract.response_basis or error.basis != contract.error_basis:
                raise InvalidWitness("intrinsic response/error extractor identity does not match the provider")
            if any(item.record_id != record.record_id or item.source_digest != record.content_digest
                   for item in (response, error)):
                raise InvalidWitness("intrinsic response moments bind a different retained record")
            response_records.append(response)
            error_records.append(error)
        response_index = ResponseIndex.from_records(contract.response_basis, response_records)
        error_index = ResponseIndex.from_records(contract.error_basis, error_records)
        bound = response_gram_enclosure(response_index, error_index, request.coefficients, 1,
                                       request.unrepresented_parameter_norm)
        raw = bound.raw_surrogate_gram
        proof = AbsoluteGramBound(ctx.binding_for_surrogate(raw), provider_id,
                                  bound.raw_absolute_gram_error,
                                  "intrinsic response/error contraction; " + request.justification)
        return SurrogateProposal(ctx.binding, raw, proof)

    return TrustedBoundProvider(provider_id, prove)


__all__ = ["ResponseStageContract", "ResponseQuery", "encode_response_descriptor",
           "decode_response_descriptor", "make_response_reference_evaluator", "make_response_provider"]

# Compact tier: retain linear Gram responses plus a scalar tangent Gram.
# Its service descriptor cost is O(N (r d^2+r^2)); group rebuilding is still O(N).
from .linear_response import (LinearRecordMoments, LinearResponseIndex,
                              shifted_linear_response_bound)
from .repair_service import SignedGramBound


def encode_linear_response_descriptor(response: LinearRecordMoments, error: RecordMoments,
                                      base_descriptor: bytes = b"") -> bytes:
    if type(base_descriptor) is not bytes:
        raise TypeError("base_descriptor must be bytes")
    if (response.record_id, response.source_digest) != (error.record_id, error.source_digest):
        raise ValueError("linear response/error moments must bind identical records")
    return _dump({"schema": "service-linear-response-descriptor-v1",
                  "response": response.canonical_bytes().decode("ascii"),
                  "error": error.canonical_bytes().decode("ascii"),
                  "base_descriptor": base_descriptor.hex()})


def decode_linear_response_descriptor(payload: bytes) -> tuple[LinearRecordMoments, RecordMoments, bytes]:
    if type(payload) is not bytes:
        raise TypeError("linear response descriptor must be bytes")
    value = json.loads(payload)
    if not isinstance(value, dict) or value.get("schema") != "service-linear-response-descriptor-v1":
        raise ValueError("unsupported service linear response descriptor")
    response = LinearRecordMoments.from_canonical_bytes(value["response"].encode("ascii"))
    error = RecordMoments.from_canonical_bytes(value["error"].encode("ascii"))
    base = bytes.fromhex(value["base_descriptor"])
    if encode_linear_response_descriptor(response, error, base) != payload:
        raise ValueError("linear response descriptor is not canonically encoded")
    return response, error, base


def make_linear_response_reference_evaluator(
    base_reference: ReferenceEvaluator,
    intrinsic_moments: Callable[[Record, StageSpec], tuple[LinearRecordMoments, RecordMoments] | None],
) -> ReferenceEvaluator:
    """Attach compact intrinsic linear/error moments to canonical descriptors.

    All independence, source identity and numerical obligations of the quadratic
    bridge apply. The job reference identity must pin this composite extractor.
    """
    def reference(record: Record, stage: StageSpec) -> ReferenceSample:
        base = base_reference(record, stage)
        moments = intrinsic_moments(record, stage)
        if moments is None:
            return ReferenceSample(base.features, _unavailable_descriptor("linear", base.descriptor))
        if not isinstance(moments, tuple) or len(moments) != 2:
            raise TypeError("linear intrinsic moments must be a response/error pair")
        response, error = moments
        if not isinstance(response, LinearRecordMoments) or not isinstance(error, RecordMoments):
            raise TypeError("linear extractor must return LinearRecordMoments and RecordMoments")
        if any(item.record_id != record.record_id or item.source_digest != record.content_digest
               for item in (response, error)):
            raise ValueError("linear intrinsic moments do not bind the supplied raw record")
        if response.basis.rows != stage.width:
            raise ValueError("linear response dimension differs from target stage")
        return ReferenceSample(base.features, encode_linear_response_descriptor(response, error, base.descriptor))
    return reference


def make_linear_response_provider(
    provider_id: str,
    manifest_digest: str,
    reference_id: str,
    contracts: Mapping[str, ResponseStageContract],
    query: Callable[[GroupContext], ResponseQuery | UnknownBound],
) -> TrustedBoundProvider:
    """Contract the compact shifted-linear tier with asymmetric Loewner bounds.

    P=S_linear+beta I is PSD. The typed service premise is
    -(beta+delta) I <= true_raw_Gram-P <= delta I.
    Its two sides remain distinct through multi-group replay and certification.
    All returned moments/bounds are exact conditional on the trusted descriptor
    theorem. No automatic claim of a second-order neural remainder is made.
    """
    fixed_contracts = MappingProxyType(dict(contracts))
    if not manifest_digest or not reference_id:
        raise ValueError("linear provider must pin target/reference identities")
    if any(not isinstance(c, ResponseStageContract) for c in fixed_contracts.values()):
        raise TypeError("contracts must contain ResponseStageContract values")

    def prove(ctx: GroupContext) -> BoundResult | SurrogateProposal:
        if (ctx.binding.manifest_digest != manifest_digest or ctx.binding.reference_id != reference_id
                or ctx.prefix.manifest_digest != manifest_digest or ctx.prefix.digest != ctx.binding.prefix_digest):
            raise InvalidWitness("linear response provider received a foreign target/reference/prefix")
        contract = fixed_contracts.get(ctx.stage.stage_id)
        if contract is None:
            return UNKNOWN
        if contract.response_basis.rows != ctx.stage.width:
            raise InvalidWitness("linear response dimension differs from target stage")
        request = query(ctx)
        if isinstance(request, UnknownBound):
            return request
        if not isinstance(request, ResponseQuery) or request.binding != ctx.binding:
            raise InvalidWitness("linear response query has a stale group/prefix")
        if len(request.coefficients) != contract.response_basis.terms - 1:
            raise InvalidWitness("linear response coefficient count mismatch")
        radius = contract.max_squared_coefficient_norm
        if radius is not None and sum((a * a for a in request.coefficients), Fraction(0)) > radius:
            return UnknownBound("candidate prefix lies outside the proved linear-response chart")
        response_records, error_records = [], []
        for record in ctx.records:
            try:
                payload = record.descriptor_for(ctx.stage.stage_id)
                if _is_unavailable(payload, "linear"):
                    return UnknownBound("intrinsic linear-response evidence is unavailable for this retained group")
                response, error, _ = decode_linear_response_descriptor(payload)
            except (KeyError, TypeError, ValueError, UnicodeError) as exc:
                raise InvalidWitness("invalid intrinsic linear response descriptor") from exc
            if response.basis != contract.response_basis or error.basis != contract.error_basis:
                raise InvalidWitness("linear response/error basis differs from provider contract")
            if any(item.record_id != record.record_id or item.source_digest != record.content_digest
                   for item in (response, error)):
                raise InvalidWitness("linear response moments bind a different retained record")
            response_records.append(response)
            error_records.append(error)
        response_index = LinearResponseIndex.from_records(contract.response_basis, response_records)
        error_index = ResponseIndex.from_records(contract.error_basis, error_records)
        bound = shifted_linear_response_bound(response_index, error_index, request.coefficients,
                                              ctx.stage.ridge, 1, request.unrepresented_parameter_norm)
        raw = bound.raw_surrogate_gram
        beta, delta = bound.omitted_psd_trace_normalized, bound.response_gram_error_normalized
        proof = SignedGramBound(ctx.binding_for_surrogate(raw), provider_id, beta + delta, delta,
                                "shifted intrinsic linear response; " + request.justification)
        return SurrogateProposal(ctx.binding, raw, proof)

    return TrustedBoundProvider(provider_id, prove)


__all__ += ["encode_linear_response_descriptor", "decode_linear_response_descriptor",
            "make_linear_response_reference_evaluator", "make_linear_response_provider"]
