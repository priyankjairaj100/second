"""Small algebraic software fixtures, not a dataset/benchmark experiment."""
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction as F
from hashlib import sha256
import json
import unittest

from src.repair_service import (
    AbsoluteGramBound, SignedGramBound, CertifiedPrefix, FeatureDriftBound, InvalidWitness,
    JobSpec, Record, ReferenceSample, RepairService, StageSpec,
    SurrogateProposal, TrustedBoundProvider, UNKNOWN, sqrt_upper,
)


def stage(name="first", dependencies=(), width=2):
    return StageSpec(name, dependencies, ((F(2, 5),) * width,),
                     ((F(0), F(1)),) * width, F(1), F(1))


def direct_features(record):
    values = json.loads(record.payload)
    return tuple((F(value),) for value in values)


def rec(name, values):
    return Record(name, json.dumps(values, separators=(",", ":")).encode())


def zero_reference(record, spec):
    return ReferenceSample(tuple((F(0),) for _ in range(spec.width)))


class ExactServiceTests(unittest.TestCase):
    def test_changed_first_stage_can_certify_without_retained_reads(self):
        first, second = stage(), stage("second", ("first",))
        job = JobSpec((first, second), "algebraic-feature-v1", "independent-zero-prefix-v1", 1)
        records = [rec("delete", [1, 1]), rec("keep", [0, 1])]

        def evaluator(record, spec, prefix):
            values = direct_features(record)
            if spec.stage_id == "first":
                return values
            code = prefix.as_mapping()["first"][0][1]
            return ((values[0][0] + code,), values[1])

        def reference(record, spec):
            # The second stage's independent reference has a fixed zero code,
            # determined before any calibration corpus is selected.
            return ReferenceSample(direct_features(record))

        def bound(ctx):
            if ctx.stage.stage_id == "first" or ctx.prefix.as_mapping()["first"][0][1] == 0:
                return AbsoluteGramBound(ctx.binding, "structural", F(0), "identical input expression")
            return UNKNOWN

        service = RepairService(job, evaluator, reference, TrustedBoundProvider("structural", bound))
        original = service.fresh(records).state
        before = original.canonical_bytes()
        self.assertEqual(original.model[0].codes[0][1], 1)

        def forbidden(_):
            self.fail("zero-error transport certificate must not read retained records")

        result = service.repair(original, [records[0]], forbidden)
        expected = service.fresh(records[1:]).state
        self.assertEqual(result.state.model[0].codes[0][1], 0)
        self.assertEqual(result.state.canonical_bytes(), expected.canonical_bytes())
        self.assertEqual(original.canonical_bytes(), before)
        self.assertTrue(all(a.route == "transport_certificate" for a in result.stages))
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 0)

    def test_unknown_group_replay_can_unlock_remaining_zero_bound_groups(self):
        # Choose two IDs with different intrinsic buckets; this is structural
        # test-fixture construction, not a random calibration dataset.
        buckets = {}
        for i in range(20):
            name = f"id{i}"
            buckets.setdefault(int.from_bytes(sha256(name.encode()).digest(), "big") % 2, name)
        left, right = buckets[0], buckets[1]
        records = [rec(left, [1, 1]), rec(right, [0, 1])]
        job = JobSpec((stage(),), "direct-v1", "masked-independent-v1", 2)

        def reference(record, spec):
            return zero_reference(record, spec) if record.record_id == left else ReferenceSample(direct_features(record))

        def bound(ctx):
            if any(r.record_id == left for r in ctx.records):
                return UNKNOWN
            return AbsoluteGramBound(ctx.binding, "known-right", F(0), "reference equals target for right ID")

        service = RepairService(job, lambda r, s, p: direct_features(r), reference,
                                TrustedBoundProvider("known-right", bound))
        original = service.fresh(records).state
        result = service.repair(original, [], {r.record_id: r for r in records}.__getitem__)
        self.assertEqual(result.state.canonical_bytes(), original.canonical_bytes())
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 1)
        self.assertEqual(result.stages[0].replayed_groups, (0,))
        self.assertEqual(result.stages[0].route, "transport_certificate")

    def test_feature_drift_is_converted_to_sound_gram_error_then_replayed(self):
        record = rec("one", [1, 1])
        job = JobSpec((stage(),), "direct-v1", "zero-v1", 1)
        provider = TrustedBoundProvider("norm", lambda ctx: FeatureDriftBound(
            ctx.binding, "norm", F(2), "sqrt(2) <= 2 for the stored two-entry fixture"))
        service = RepairService(job, lambda r, s, p: direct_features(r), zero_reference, provider)
        original = service.fresh([record]).state
        result = service.repair(original, [], lambda _: record)
        self.assertEqual(result.state.canonical_bytes(), original.canonical_bytes())
        self.assertEqual(result.ledger.count("feature_to_gram_bound_conversions"), 1)
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 1)
        self.assertEqual(result.stages[0].route, "exact_replay")

    def test_exact_response_proposal_avoids_target_replay(self):
        records = [rec("a", [1, 1]), rec("b", [0, 1])]
        job = JobSpec((stage(),), "direct-v1", "zero-plus-intrinsic-response-v1", 1)

        def reference(record, spec):
            return ReferenceSample(((F(0),), (F(0),)), record.payload)

        def provider(ctx):
            # Intrinsic descriptors contain an exact two-vector response basis.
            # Real deployments must budget these bytes and descriptor reads.
            vectors = [json.loads(r.descriptor_for(ctx.stage.stage_id)) for r in ctx.records]
            gram = tuple(tuple(sum(F(v[i]) * F(v[j]) for v in vectors) for j in range(2)) for i in range(2))
            proof = AbsoluteGramBound(ctx.binding_for_surrogate(gram), "response", F(0),
                                      "exact fixed intrinsic response basis")
            return SurrogateProposal(ctx.binding, gram, proof)

        service = RepairService(job, lambda r, s, p: direct_features(r), reference,
                                TrustedBoundProvider("response", provider))
        original = service.fresh(records).state
        result = service.repair(original, [records[0]], lambda _: self.fail("unexpected target replay"))
        expected = service.fresh(records[1:]).state
        self.assertEqual(result.state.canonical_bytes(), expected.canonical_bytes())
        self.assertEqual(result.ledger.count("proposal_psd_validation_calls"), 1)
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 0)

    def test_unknown_proposal_replay_subtracts_the_proposed_gram(self):
        record = rec("one", [1, 1])
        job = JobSpec((stage(),), "direct-v1", "zero-v1", 1)
        proposal = ((F(100), F(0)), (F(0), F(3)))
        provider = TrustedBoundProvider("proposal", lambda ctx: SurrogateProposal(ctx.binding, proposal, UNKNOWN))
        service = RepairService(job, lambda r, s, p: direct_features(r), zero_reference, provider)
        original = service.fresh([record]).state
        repaired = service.repair(original, [], lambda _: record)
        self.assertEqual(repaired.state.canonical_bytes(), original.canonical_bytes())
        self.assertEqual(repaired.stages[0].route, "exact_replay")

    def test_proposal_psd_and_surrogate_bindings_fail_closed(self):
        record = rec("one", [1, 1])
        job = JobSpec((stage(),), "direct-v1", "zero-v1", 1)
        for matrix, stale in [(((1, 2), (2, 1)), False), (((1, 0), (0, 1)), True)]:
            with self.subTest(matrix=matrix, stale=stale):
                def provider(ctx):
                    binding = ctx.binding if stale else ctx.binding_for_surrogate(matrix)
                    proof = AbsoluteGramBound(binding, "proposal", F(0), "test obligation")
                    return SurrogateProposal(ctx.binding, matrix, proof)
                service = RepairService(job, lambda r, s, p: direct_features(r), zero_reference,
                                        TrustedBoundProvider("proposal", provider))
                state = service.fresh([record]).state
                before = state.canonical_bytes()
                with self.assertRaises(InvalidWitness):
                    service.repair(state, [], lambda _: record)
                self.assertEqual(state.canonical_bytes(), before)

    def test_prefix_exposes_only_declared_transitive_ancestors(self):
        a, b, c = stage("a"), stage("b"), stage("c", ("a",))
        seen = []
        def evaluator(record, spec, prefix):
            seen.append((spec.stage_id, tuple(prefix.as_mapping())))
            with self.assertRaises(TypeError):
                prefix.as_mapping()["mutation"] = ((F(0),),)
            return direct_features(record)
        service = RepairService(JobSpec((a, b, c), "dag-v1", "direct-v1", 1), evaluator,
                                lambda r, s: ReferenceSample(direct_features(r)))
        service.fresh([rec("one", [0, 1])])
        self.assertEqual(seen, [("a", ()), ("b", ()), ("c", ("a",))])

    def test_repeated_delete_order_canonical_and_old_state_unchanged(self):
        records = [rec("a", [1, 1]), rec("b", [0, 1]), rec("c", [2, 1])]
        mapping = {r.record_id: r for r in records}
        service = RepairService(JobSpec((stage(),), "direct-v1", "direct-v1", 3),
                                lambda r, s, p: direct_features(r),
                                lambda r, s: ReferenceSample(direct_features(r)))
        original = service.fresh(records).state
        before = original.canonical_bytes()
        step1 = service.repair(original, [records[0]], mapping.__getitem__).state
        step2 = service.repair(step1, [records[1]], mapping.__getitem__).state
        reverse1 = service.repair(original, [records[1]], mapping.__getitem__).state
        reverse2 = service.repair(reverse1, [records[0]], mapping.__getitem__).state
        both = service.repair(original, records[:2], mapping.__getitem__).state
        fresh = service.fresh(records[2:]).state
        self.assertEqual({s.canonical_bytes() for s in [step2, reverse2, both, fresh]}, {fresh.canonical_bytes()})
        self.assertEqual(original.canonical_bytes(), before)
        self.assertEqual(step2.retained_ids, ("c",))

    def test_one_sided_large_positive_bound_preserves_positive_lower_scale(self):
        record = rec("one", [10])
        job = JobSpec((stage(width=1),), "direct-scalar-v1", "zero-scalar-v1", 1)
        provider = TrustedBoundProvider("one-sided", lambda ctx: SignedGramBound(
            ctx.binding, "one-sided", F(0), F(100), "actual Gram 100 minus reference Gram zero is PSD"))
        service = RepairService(job, lambda r, s, p: direct_features(r), zero_reference, provider)
        state = service.fresh([record]).state
        result = service.repair(state, [], lambda _: self.fail("one-sided proof should certify"))
        self.assertEqual(result.state.canonical_bytes(), state.canonical_bytes())
        self.assertEqual(result.stages[0].route, "transport_certificate")
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 0)

    def test_service_configuration_is_frozen(self):
        service = RepairService(JobSpec((stage(),), "direct-v1", "zero-v1"),
                                lambda r, s, p: direct_features(r), zero_reference)
        with self.assertRaises(FrozenInstanceError):
            service.job = replace(service.job, group_count=3)
        with self.assertRaises(FrozenInstanceError):
            service.evaluator = lambda r, s, p: ((0,), (0,))
        with self.assertRaises(TypeError):
            service._ancestors["first"] = frozenset({"bad"})

    def test_exact_rational_sqrt_upper(self):
        for value in [F(0), F(1, 100), F(2), F(9, 4), F(1234567, 19)]:
            bound = sqrt_upper(value, 12)
            self.assertGreaterEqual(bound * bound, value)
            self.assertLess(bound - F(1, 4096), bound)
            if bound:
                self.assertLess((bound - F(1, 4096)) ** 2, value)
        with self.assertRaises(TypeError):
            sqrt_upper(0.5)


if __name__ == "__main__":
    unittest.main()
