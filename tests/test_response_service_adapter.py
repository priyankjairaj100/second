"""Software checks of the response-index/service composition; no research runs."""
from dataclasses import replace
from fractions import Fraction as F
import json
import unittest

from src.repair_service import JobSpec, Record, ReferenceSample, RepairService, StageSpec, UNKNOWN
from src.response_moments import ResponseBasis, record_moments
from src.linear_response import linear_record_moments
from src.response_service_adapter import (
    ResponseQuery, ResponseStageContract, decode_response_descriptor,
    encode_response_descriptor, make_response_provider, make_response_reference_evaluator,
    encode_linear_response_descriptor, decode_linear_response_descriptor,
    make_linear_response_reference_evaluator, make_linear_response_provider,
)


class ResponseServiceAdapterTests(unittest.TestCase):
    def build(self, chart=F(4)):
        stages = tuple(StageSpec(name, deps, ((F(2, 5), F(2, 5)),), ((0, 1), (0, 1)), 1, 1)
                       for name, deps in [("first", ()), ("second", ("first",))])
        job = JobSpec(stages, "exact-affine-prefix-fixture-v1", "zero-reference-and-fixed-response-v1", 1)
        response_bases = {name: ResponseBasis(f"{name}-intrinsic-response-v1", 2, terms, True)
                          for name, terms in [("first", 1), ("second", 2)]}
        errors = {name: ResponseBasis(f"{name}-exact-response-error-v1", 1, basis.terms + 2, True)
                  for name, basis in response_bases.items()}
        contracts = {name: ResponseStageContract(basis, errors[name], chart)
                     for name, basis in response_bases.items()}

        def intrinsic(record, stage):
            values = json.loads(record.payload)
            base = ((F(values[0]),), (F(values[1]),))
            jets = (base,) if stage.stage_id == "first" else (base, ((F(1),), (F(0),)))
            feature = record_moments(response_bases[stage.stage_id], record.record_id, record.content_digest, jets)
            error = record_moments(errors[stage.stage_id], record.record_id, record.content_digest,
                                   (((F(0),),),) * errors[stage.stage_id].terms)
            return feature, error

        reference = make_response_reference_evaluator(
            lambda record, stage: ReferenceSample(((F(0),), (F(0),))), intrinsic)

        def target(record, stage, prefix):
            values = json.loads(record.payload)
            coefficient = F(0) if stage.stage_id == "first" else prefix.as_mapping()["first"][0][1]
            return ((F(values[0]) + coefficient,), (F(values[1]),))

        def query(ctx):
            coefficients = () if ctx.stage.stage_id == "first" else (ctx.prefix.as_mapping()["first"][0][1],)
            return ResponseQuery(ctx.binding, coefficients, F(0), "exact affine feature response to current first-stage code")

        provider = make_response_provider("fixed-response-proof-v1", job.manifest_digest, job.reference_id,
                                          contracts, query)
        return RepairService(job, target, reference, provider), intrinsic, stages

    def test_changed_prefix_complete_state_matches_fresh_without_target_replay(self):
        service, _, _ = self.build()
        records = [Record("a", b"[1,1]"), Record("b", b"[0,1]")]
        original = service.fresh(records).state
        self.assertEqual(original.model[0].codes[0][1], 1)
        result = service.repair(original, [records[0]], lambda _: self.fail("response proof should avoid raw replay"))
        expected = service.fresh(records[1:]).state
        self.assertEqual(result.state.model[0].codes[0][1], 0)
        self.assertEqual(result.state.canonical_bytes(), expected.canonical_bytes())
        self.assertTrue(all(a.route == "transport_certificate" for a in result.stages))
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 0)
        # O(N) intrinsic descriptors are explicitly read; no sublinear-service claim.
        self.assertEqual(result.ledger.count("provider_descriptor_records"), 2)

    def test_out_of_chart_abstains_and_replays_the_changed_prefix(self):
        service, _, _ = self.build(chart=F(0))
        records = [Record("a", b"[1,1]"), Record("b", b"[0,1]")]
        original = service.fresh(records).state
        result = service.repair(original, [], {r.record_id: r for r in records}.__getitem__)
        self.assertEqual(result.state.canonical_bytes(), original.canonical_bytes())
        self.assertEqual(result.stages[0].route, "transport_certificate")
        self.assertEqual(result.stages[1].route, "exact_replay")
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 2)

    def test_descriptor_roundtrip_and_source_binding(self):
        service, intrinsic, stages = self.build()
        record = Record("a", b"[1,1]")
        feature, error = intrinsic(record, stages[1])
        encoded = encode_response_descriptor(feature, error, b"base")
        self.assertEqual(decode_response_descriptor(encoded), (feature, error, b"base"))
        with self.assertRaises(ValueError):
            decode_response_descriptor(encoded + b" ")
        with self.assertRaises(ValueError):
            encode_response_descriptor(feature, replace(error, source_digest="wrong"))

    def test_descriptor_unknown_stage_safe_fallback(self):
        service, _, _ = self.build()
        # A provider with no supported response contracts declines both stages.
        no_contracts = make_response_provider("unsupported", service.job.manifest_digest,
                                              service.job.reference_id, {}, lambda ctx: UNKNOWN)
        service = RepairService(service.job, service.evaluator, service.reference_evaluator, no_contracts)
        record = Record("a", b"[1,1]")
        state = service.fresh([record]).state
        result = service.repair(state, [], lambda _: record)
        self.assertEqual(result.state.canonical_bytes(), state.canonical_bytes())
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 2)


class LinearServiceAdapterTests(unittest.TestCase):
    def fixture(self):
        spec = StageSpec("layer", (), ((F(2, 5), F(2, 5)),), ((0, 1), (0, 1)), 1, 1)
        job = JobSpec((spec,), "small-exact-affine-fixture", "intrinsic-linear-fixture-v1", 1)
        feature_basis = ResponseBasis("fixed-linear-direction-v1", 2, 2, True)
        error_basis = ResponseBasis("exact-linear-error-v1", 1, 4, True)
        contract = ResponseStageContract(feature_basis, error_basis, F(1))
        def intrinsic(record, stage):
            v = json.loads(record.payload)
            jets = (((F(v[0]),), (F(v[1]),)), ((F(1),), (F(0),)))
            feature = linear_record_moments(feature_basis, record.record_id, record.content_digest, jets)
            error = record_moments(error_basis, record.record_id, record.content_digest, (((F(0),),),) * 4)
            return feature, error
        reference = make_linear_response_reference_evaluator(
            lambda r, s: ReferenceSample(((F(0),), (F(0),))), intrinsic)
        provider = make_linear_response_provider(
            "linear-proof-v1", job.manifest_digest, job.reference_id, {"layer": contract},
            lambda ctx: ResponseQuery(ctx.binding, (F(1, 10),), F(0), "exact intrinsic affine response"))
        def target(record, stage, prefix):
            v = json.loads(record.payload)
            return ((F(v[0]) + F(1, 10),), (F(v[1]),))
        return RepairService(job, target, reference, provider), intrinsic, spec

    def test_shifted_linear_signed_certificate_matches_fresh_without_replay(self):
        service, _, _ = self.fixture()
        records = [Record("a", b"[1,1]"), Record("b", b"[0,1]")]
        state = service.fresh(records).state
        repaired = service.repair(state, [records[1]], lambda _: self.fail("unexpected target replay"))
        expected = service.fresh(records[:1]).state
        self.assertEqual(repaired.state.canonical_bytes(), expected.canonical_bytes())
        self.assertEqual(repaired.stages[0].route, "transport_certificate")
        self.assertEqual(repaired.ledger.count("retained_replay_evaluator_calls"), 0)

    def test_compact_descriptor_roundtrip_and_canonical_repeated_state(self):
        service, intrinsic, spec = self.fixture()
        records = [Record("a", b"[1,1]"), Record("b", b"[0,1]"), Record("c", b"[1,2]")]
        feature, error = intrinsic(records[0], spec)
        encoded = encode_linear_response_descriptor(feature, error, b"base")
        self.assertEqual(decode_linear_response_descriptor(encoded), (feature, error, b"base"))
        original = service.fresh(records).state
        source = {r.record_id: r for r in records}.__getitem__
        first = service.repair(original, [records[0]], source).state
        sequential = service.repair(first, [records[1]], source).state
        combined = service.repair(original, records[:2], source).state
        fresh = service.fresh(records[2:]).state
        self.assertEqual(sequential.canonical_bytes(), combined.canonical_bytes())
        self.assertEqual(combined.canonical_bytes(), fresh.canonical_bytes())


class UnavailableResponseTests(unittest.TestCase):
    def verify_unavailable(self, linear):
        spec = StageSpec("layer", (), ((F(2, 5), F(2, 5)),), ((0, 1), (0, 1)), 1, 1)
        tier = "linear" if linear else "quadratic"
        job = JobSpec((spec,), "direct-feature-v1", f"unavailable-{tier}-reference-v1", 1)
        basis = ResponseBasis(f"fixed-{tier}-basis", 2, 2, True)
        errors = ResponseBasis(f"fixed-{tier}-errors", 1, 4, True)
        contracts = {"layer": ResponseStageContract(basis, errors, F(1))}
        reference_factory = make_linear_response_reference_evaluator if linear else make_response_reference_evaluator
        provider_factory = make_linear_response_provider if linear else make_response_provider
        reference = reference_factory(lambda r, s: ReferenceSample(((F(0),), (F(0),)), b"base"),
                                      lambda r, s: None)
        provider = provider_factory(f"{tier}-provider", job.manifest_digest, job.reference_id, contracts,
                                    lambda ctx: ResponseQuery(ctx.binding, (F(0),), F(0), "declared chart"))
        service = RepairService(job, lambda r, s, p: ((F(1),), (F(1),)), reference, provider)
        record = Record("one", b"content")
        original = service.fresh([record]).state
        result = service.repair(original, [], lambda _: record)
        self.assertEqual(result.state.canonical_bytes(), original.canonical_bytes())
        self.assertEqual(result.stages[0].route, "exact_replay")
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 1)

    def test_unavailable_quadratic_descriptor_abstains_and_replays(self):
        self.verify_unavailable(False)

    def test_unavailable_linear_descriptor_abstains_and_replays(self):
        self.verify_unavailable(True)


if __name__ == "__main__":
    unittest.main()
