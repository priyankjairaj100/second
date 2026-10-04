"""Independent state/provenance software fixtures, without research datasets."""

from dataclasses import replace
from fractions import Fraction as F
import json
import unittest

from src.repair_service import (
    AbsoluteGramBound, InvalidWitness, JobSpec, Record, ReferenceSample,
    RepairService, SignedGramBound, StageSpec, SurrogateProposal, TrustedBoundProvider, UNKNOWN,
)
try:
    from .test_exact_core_independent import constrained_oracle
except ImportError:  # unittest discover -s tests imports top-level modules.
    from test_exact_core_independent import constrained_oracle


def service_fixture(provider=None):
    grid = ((-1, 0, 1),) * 2
    stages = (
        StageSpec("first", (), ((F(1, 3), F(2, 5)),), grid, F(1), F(1)),
        StageSpec("second", ("first",), ((F(3, 5), F(2, 5)),), grid, F(1), F(1)),
    )
    job = JobSpec(stages, "explicit-finite-feature-fixture-v1", "fixed-base-reference-v1", 2)

    def features(record, stage, prefix):
        x, y = map(F, json.loads(record.payload))
        if stage.stage_id == "first":
            return ((x,), (y,))
        q = prefix.as_mapping()["first"][0]
        return ((x + q[1] * y,), (y + q[0] * x,))

    def reference(record, stage):
        x, y = map(F, json.loads(record.payload))
        q = stages[0].weights[0]
        values = ((x,), (y,)) if stage.stage_id == "first" else ((x + q[1] * y,), (y + q[0] * x,))
        return ReferenceSample(values)

    records = tuple(Record(name, json.dumps(values).encode()) for name, values in
                    (("a", (3, 1)), ("b", (1, 4)), ("c", (2, -1))))
    return RepairService(job, features, reference, provider), records


def independent_target(service, records):
    """Reconstruct feature formula and solve constrained quadratics independently."""
    output = []
    for stage in service.job.stages:
        columns = []
        for record in records:
            x, y = map(F, json.loads(record.payload))
            if stage.stage_id == "second":
                q = output[0][0]
                x, y = x + q[1] * y, y + q[0] * x
            columns.append((x, y))
        h = tuple(tuple(stage.ridge * (i == j) + sum(
            (x[i] * x[j] for x in columns), F(0)) / stage.normalization
                        for j in range(2)) for i in range(2))
        output.append(constrained_oracle(stage.weights, h, stage.grids))
    return tuple(output)


class AdversarialServiceTests(unittest.TestCase):
    def test_changed_prefix_matches_independent_oracle_and_fresh_bytes(self):
        service, records = service_fixture()
        old = service.fresh(records)
        retained = {r.record_id: r for r in records[:2]}
        reads = []

        def source(record_id):
            reads.append(record_id)
            return retained[record_id]

        repaired = service.repair(old.state, (records[2],), source)
        expected = independent_target(service, records[:2])
        self.assertNotEqual(old.state.model[0].codes, repaired.state.model[0].codes)
        self.assertEqual(tuple(stage.codes for stage in repaired.state.model), expected)
        self.assertEqual(repaired.state.canonical_bytes(), service.fresh(records[:2]).state.canonical_bytes())
        self.assertEqual(sorted(reads), ["a", "b"])
        self.assertEqual(old.state.retained_ids, ("a", "b", "c"))

    def test_repeated_and_empty_deletions_have_canonical_fresh_state(self):
        service, records = service_fixture()
        initial = service.fresh(records).state
        current = service.repair(initial, (records[2],), {r.record_id: r for r in records[:2]}.__getitem__).state
        current = service.repair(current, (records[0],), {"b": records[1]}.__getitem__).state
        self.assertEqual(current.canonical_bytes(), service.fresh((records[1],)).state.canonical_bytes())
        final = service.repair(current, (records[1],), lambda rid: self.fail("empty retained set must not read"))
        self.assertEqual(final.state.canonical_bytes(), service.fresh(()).state.canonical_bytes())
        empty_request = service.repair(initial, (), {r.record_id: r for r in records}.__getitem__)
        self.assertEqual(empty_request.state.canonical_bytes(), initial.canonical_bytes())

    def test_stale_or_forged_binding_fields_abort_transaction(self):
        fields = (
            ("manifest_digest", "foreign"), ("stage_id", "foreign"),
            ("prefix_digest", "old-prefix"), ("reference_id", "different-reference"),
            ("group_id", 999), ("records_digest", "different-record-set"),
            ("reference_gram_digest", "different-gram"),
            ("surrogate_gram_digest", "different-proposal"),
        )
        for field, altered in fields:
            def prove(context, field=field, altered=altered):
                return AbsoluteGramBound(replace(context.binding, **{field: altered}), "test-proof", F(0), "deliberately invalid binding")
            service, records = service_fixture(TrustedBoundProvider("test-proof", prove))
            state = service.fresh(records).state
            before = state.canonical_bytes()
            with self.assertRaises(InvalidWitness):
                service.repair(state, (), {r.record_id: r for r in records}.__getitem__)
            self.assertEqual(state.canonical_bytes(), before)

    def test_bad_provider_identity_bound_type_and_sign_rejected(self):
        factories = (
            lambda c: AbsoluteGramBound(c.binding, "other-provider", F(0), "bad provider"),
            lambda c: AbsoluteGramBound(c.binding, "test-proof", F(-1), "negative error"),
            lambda c: AbsoluteGramBound(c.binding, "test-proof", 0.0, "floating estimate"),
            lambda c: AbsoluteGramBound(c.binding, "test-proof", True, "boolean estimate"),
            lambda c: SignedGramBound(c.binding, "test-proof", F(-1), F(0), "negative signed radius"),
            lambda c: SignedGramBound(c.binding, "test-proof", F(0), 0.0, "floating signed radius"),
            lambda c: (F(1), F(1)),
        )
        for factory in factories:
            service, records = service_fixture(TrustedBoundProvider("test-proof", factory))
            state = service.fresh(records).state
            with self.assertRaises(InvalidWitness):
                service.repair(state, (), {r.record_id: r for r in records}.__getitem__)

    def test_record_and_manifest_mismatch_rejected(self):
        service, records = service_fixture()
        state = service.fresh(records).state
        source = {r.record_id: r for r in records}.__getitem__
        for deletions in ((records[0], records[0]), (Record("absent", b"[]"),),
                          (Record("a", b"[999, 999]"),)):
            with self.assertRaises(ValueError):
                service.repair(state, deletions, source)
        with self.assertRaises(ValueError):
            service.repair(replace(state, manifest_digest="foreign"), (), source)
        with self.assertRaises(ValueError):
            service.repair(state, (), lambda rid: Record(rid, b"[99,99]"))

    def test_service_configuration_cannot_drift_under_old_manifest(self):
        service, _ = service_fixture()
        changed_stage = replace(service.job.stages[0], normalization=F(10))
        changed_job = replace(service.job, stages=(changed_stage,) + service.job.stages[1:])
        with self.assertRaises(AttributeError):
            service.job = changed_job
        with self.assertRaises(AttributeError):
            service.evaluator = lambda *args: ((F(0),), (F(0),))
        with self.assertRaises(TypeError):
            service._ancestors["second"] = frozenset()

    def test_signed_raw_radius_is_normalized_exactly_once(self):
        # A missing division by M0=1/4 would accept the wrong zero proposal.
        stage = StageSpec("one", (), ((F(1, 3), F(9, 25)),), ((0, 1),) * 2,
                          F(1), F(1, 4))
        job = JobSpec((stage,), "normalization-fixture", "fixed-reference", 1)
        record = Record("a", b"finite explicit fixture")
        target = ((F(3, 5),), (F(4, 5),))

        def prove(context):
            zero = ((F(0), F(0)), (F(0), F(0)))
            # Target raw Gram has eigenvalues 1 and 0, so 0 <= S* <= I.
            witness = SignedGramBound(context.binding_for_surrogate(zero), "normalization-proof",
                                      F(0), F(1), "exact rank-one unit-vector Gram")
            return SurrogateProposal(context.binding, zero, witness)

        service = RepairService(job, lambda *args: target,
                                lambda *args: ReferenceSample(target),
                                TrustedBoundProvider("normalization-proof", prove))
        state = service.fresh((record,)).state
        repaired = service.repair(state, (), lambda rid: record)
        self.assertEqual(repaired.state.model[0].codes, ((F(0), F(1)),))
        self.assertEqual(repaired.state.canonical_bytes(), state.canonical_bytes())
        self.assertEqual(repaired.ledger.count("retained_replay_evaluator_calls"), 1)
