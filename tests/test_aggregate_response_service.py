"""Behavioral software tests; these are not empirical dataset experiments."""
from dataclasses import FrozenInstanceError, fields, replace
from fractions import Fraction as F
import json
import unittest

from src.aggregate_response_service import AggregateRepairService, AggregateRecord
from src.linear_response import linear_record_moments
from src.repair_service import JobSpec, Record, StageSpec, UNKNOWN, InvalidWitness, _Work
from src.response_moments import ResponseBasis, record_moments
from src.response_service_adapter import ResponseQuery, ResponseStageContract


class AggregateServiceTests(unittest.TestCase):
    def build(self, *, groups=1, missing=(), query_unknown=False, chart=F(4), normalization=1):
        stages = tuple(StageSpec(name, deps, ((F(2, 5), F(2, 5)),), ((0, 1), (0, 1)), 1, normalization)
                       for name, deps in [("first", ()), ("second", ("first",))])
        job = JobSpec(stages, "exact-affine-prefix-test-v1", "fixed-intrinsic-linear-test-v1", groups)
        bases = {name: ResponseBasis(name + "/response", 2, terms, True)
                 for name, terms in [("first", 1), ("second", 2)]}
        errors = {name: ResponseBasis(name + "/error", 1, b.terms + 2, True) for name, b in bases.items()}
        contracts = {name: ResponseStageContract(b, errors[name], chart) for name, b in bases.items()}
        calls, contexts = [], []
        control = {"corrupt": False, "stale": False, "missing": set(missing)}
        def intrinsic(record, stage):
            calls.append((record.record_id, stage.stage_id))
            if record.record_id in control["missing"]:
                return None
            value = json.loads(record.payload)
            base = ((F(value[0]) + int(control["corrupt"]),), (F(value[1]),))
            jets = (base,) if stage.stage_id == "first" else (base, ((F(1),), (F(0),)))
            response = linear_record_moments(bases[stage.stage_id], record.record_id, record.content_digest, jets)
            error = record_moments(errors[stage.stage_id], record.record_id, record.content_digest,
                                   (((F(0),),),) * errors[stage.stage_id].terms)
            return response, error
        def target(record, stage, prefix):
            if prefix.manifest_digest != job.manifest_digest:
                raise ValueError("foreign target manifest")
            value = json.loads(record.payload)
            coefficient = 0 if stage.stage_id == "first" else prefix.as_mapping()["first"][0][1]
            return ((F(value[0]) + coefficient,), (F(value[1]),))
        def query(ctx):
            contexts.append(ctx)
            if query_unknown:
                return UNKNOWN
            coefficient = () if ctx.stage.stage_id == "first" else (ctx.prefix.as_mapping()["first"][0][1],)
            binding = replace(ctx.binding, prefix_digest="stale") if control["stale"] else ctx.binding
            return ResponseQuery(binding, coefficient, F(0), "exact affine feature response")
        service = AggregateRepairService(job, target, intrinsic, contracts, query,
                                         provider_id="affine-exact-proof", extractor_id="fixed-affine-jets")
        return service, calls, contexts, control

    def records(self):
        return [Record("a", b"[1,1]"), Record("b", b"[0,1]"), Record("c", b"[1,2]")]

    def test_changed_first_stage_zero_retained_replay_matches_fresh_state(self):
        service, calls, contexts, _ = self.build()
        records = self.records()[:2]
        original = service.fresh(records).state
        before = original.canonical_bytes()
        self.assertEqual(original.model[0].codes[0][1], 1)
        calls.clear()
        result = service.repair(original, records[:1], lambda _: self.fail("retained read on accepted response"))
        self.assertEqual(calls, [("a", "first"), ("a", "second")])
        expected = service.fresh(records[1:]).state
        self.assertEqual(result.state.model[0].codes[0][1], 0)
        self.assertEqual(result.state.canonical_bytes(), expected.canonical_bytes())
        self.assertEqual(original.canonical_bytes(), before)
        self.assertTrue(all(a.route == "transport_certificate" for a in result.stages))
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 0)
        self.assertEqual(result.ledger.count("retained_source_record_reads"), 0)
        self.assertEqual(result.ledger.count("aggregate_contraction_calls"), 2)
        self.assertTrue(all(not hasattr(ctx, "records") for ctx in contexts))
        self.assertTrue(all(ctx.response.records == ctx.error.records == () for ctx in contexts))

    def test_repeated_and_reordered_deletion_equals_fresh_complete_bytes(self):
        service, _, _, _ = self.build(groups=2)
        records = self.records()
        state = service.fresh(records).state
        source = {r.record_id: r for r in records}.__getitem__
        sequential = service.repair(service.repair(state, [records[0]], source).state, [records[1]], source).state
        reverse = service.repair(service.repair(state, [records[1]], source).state, [records[0]], source).state
        combined = service.repair(state, records[:2], source).state
        fresh = service.fresh(records[2:]).state
        self.assertEqual(sequential.canonical_bytes(), reverse.canonical_bytes())
        self.assertEqual(sequential.canonical_bytes(), combined.canonical_bytes())
        self.assertEqual(combined.canonical_bytes(), fresh.canonical_bytes())

    def test_rational_storage_and_proposal_work_ignore_record_count(self):
        service, calls, _, _ = self.build()
        small = [Record(str(i), b"[0,1]") for i in range(2)]
        large = [Record(str(i), b"[0,1]") for i in range(20)]
        a, b = service.fresh(small).state, service.fresh(large).state
        self.assertEqual(a.stored_aggregate_rational_count, b.stored_aggregate_rational_count)
        for state in (a, b):
            for group in state.groups:
                for stage in group.stages:
                    self.assertEqual(stage.response.records, ())
                    self.assertEqual(stage.error.records, ())
            self.assertEqual({f.name for f in fields(AggregateRecord)},
                             {"record_id", "content_digest", "group_id", "contributions"})
            self.assertTrue(all(type(c.contribution_digest) is str for r in state.records for c in r.contributions))
        calls.clear()
        x = service.repair(a, [], lambda _: self.fail("unexpected source access"))
        y = service.repair(b, [], lambda _: self.fail("unexpected source access"))
        self.assertEqual(calls, [])
        self.assertEqual(x.ledger.count("proposal_aggregate_rational_entries"),
                         y.ledger.count("proposal_aggregate_rational_entries"))
        self.assertEqual(x.ledger.count("aggregate_contraction_calls"), y.ledger.count("aggregate_contraction_calls"))
        self.assertEqual(x.ledger.count("validated_record_entries"), 2)
        self.assertEqual(y.ledger.count("validated_record_entries"), 20)
        self.assertEqual(y.ledger.count("metadata_serialized_entries"), 20)
        self.assertEqual(y.ledger.count("metadata_deletion_filter_entries"), 20)
        self.assertGreater(y.ledger.count("canonical_serialized_bytes"), x.ledger.count("canonical_serialized_bytes"))

    def test_unknown_intrinsic_group_selectively_replays(self):
        service, _, _, control = self.build(groups=2)
        ids = {}
        for i in range(20):
            rid = f"id{i}"
            ids.setdefault(service._engine._group(rid), rid)
        records = [Record(ids[0], b"[0,1]"), Record(ids[1], b"[0,1]")]
        control["missing"] = {ids[0]}
        state = service.fresh(records).state
        reads = []
        def source(rid):
            reads.append(rid)
            return {r.record_id: r for r in records}[rid]
        result = service.repair(state, [], source)
        self.assertEqual(result.state.canonical_bytes(), state.canonical_bytes())
        self.assertEqual(reads, [ids[0]])
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 2)
        self.assertTrue(all(a.replayed_groups == (0,) and a.unknown_groups == (0,) for a in result.stages))
        self.assertTrue(all(a.route == "transport_certificate" for a in result.stages))

    def test_unknown_query_and_missing_contract_fall_back_exactly(self):
        service, _, _, _ = self.build(query_unknown=True)
        records = self.records()
        source = {r.record_id: r for r in records}.__getitem__
        state = service.fresh(records).state
        result = service.repair(state, [records[0]], source)
        self.assertEqual(result.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 4)
        self.assertTrue(all(a.route == "exact_replay" for a in result.stages))
        unsupported = AggregateRepairService(service.job, service.evaluator,
            lambda r, s: self.fail("unsupported extractor must not run"), {}, lambda ctx: UNKNOWN,
            provider_id="unsupported", extractor_id="unsupported")
        state = unsupported.fresh(records).state
        result = unsupported.repair(state, [records[0]], source)
        self.assertEqual(result.state.canonical_bytes(), unsupported.fresh(records[1:]).state.canonical_bytes())
        self.assertEqual(result.state.stored_aggregate_rational_count, 0)

    def test_out_of_chart_replays_and_preserves_full_state(self):
        service, _, _, _ = self.build(chart=0)
        records = self.records()[:2]
        state = service.fresh(records).state
        result = service.repair(state, [], {r.record_id: r for r in records}.__getitem__)
        self.assertEqual(result.state.canonical_bytes(), state.canonical_bytes())
        self.assertEqual(result.ledger.count("out_of_chart_aggregate_groups"), 1)
        self.assertEqual(result.stages[1].route, "exact_replay")

    def test_bad_deleted_payload_and_changed_intrinsic_digest_are_transactional(self):
        service, _, _, control = self.build()
        records = self.records()
        state = service.fresh(records).state
        before = state.canonical_bytes()
        with self.assertRaisesRegex(ValueError, "content differs"):
            service.repair(state, [Record("a", b"different")], lambda _: self.fail("source read"))
        control["corrupt"] = True
        with self.assertRaisesRegex(ValueError, "committed digest"):
            service.repair(state, [records[0]], lambda _: self.fail("source read"))
        control["corrupt"] = False
        control["missing"] = {"a"}
        with self.assertRaisesRegex(ValueError, "committed digest"):
            service.repair(state, [records[0]], lambda _: self.fail("source read"))
        self.assertEqual(state.canonical_bytes(), before)

    def test_stale_prefix_and_foreign_schema_rejected_without_mutation(self):
        service, _, _, control = self.build()
        records = self.records()[:2]
        state = service.fresh(records).state
        before = state.canonical_bytes()
        control["stale"] = True
        with self.assertRaises(InvalidWitness):
            service.repair(state, [], lambda _: self.fail("source read"))
        with self.assertRaisesRegex(ValueError, "service manifest"):
            service.repair(replace(state, manifest_digest=service.job.manifest_digest), [], lambda _: None)
        self.assertEqual(state.canonical_bytes(), before)
        with self.assertRaises(FrozenInstanceError):
            service.query = lambda ctx: UNKNOWN

    def test_retained_source_binding_failure_is_transactional(self):
        service, _, _, _ = self.build(query_unknown=True)
        records = self.records()[:2]
        state = service.fresh(records).state
        before = state.canonical_bytes()
        with self.assertRaisesRegex(ValueError, "content differs"):
            service.repair(state, [], lambda rid: Record(rid, b"[9,9]"))
        self.assertEqual(state.canonical_bytes(), before)

    def test_metadata_mismatch_and_embedded_per_record_matrices_rejected(self):
        service, _, _, _ = self.build()
        records = self.records()[:2]
        state = service.fresh(records).state
        group = state.groups[0]
        bad_stage = replace(group.stages[0], unavailable_count=1)
        bad = replace(state, groups=(replace(group, stages=(bad_stage,) + group.stages[1:]),))
        with self.assertRaisesRegex(ValueError, "unavailable count"):
            service.repair(bad, [], lambda _: None)
        bad = replace(state, groups=(replace(group, membership_digest="0" * 64),))
        with self.assertRaisesRegex(ValueError, "membership"):
            service.repair(bad, [], lambda _: None)
        response, _ = service.intrinsic_moments(records[0], service.job.stages[0])
        from src.linear_response import LinearResponseIndex
        indexed = LinearResponseIndex.from_records(response.basis, (response,))
        bad_stage = replace(group.stages[0], response=indexed)
        bad = replace(state, groups=(replace(group, stages=(bad_stage,) + group.stages[1:]),))
        with self.assertRaisesRegex(ValueError, "per-record bindings"):
            service.repair(bad, [], lambda _: None)

    def test_empty_deletion_target_is_canonical_without_source_reads(self):
        service, _, _, _ = self.build()
        records = self.records()
        state = service.fresh(records).state
        result = service.repair(state, records, lambda _: self.fail("empty retained set read"))
        self.assertEqual(result.state.canonical_bytes(), service.fresh([]).state.canonical_bytes())
        self.assertEqual(result.state.records, ())
        self.assertEqual(result.state.groups, ())
        self.assertEqual(result.state.stored_aggregate_rational_count, 0)

    def test_signed_response_radius_and_fixed_normalization(self):
        service, _, _, _ = self.build(normalization=7)
        records = self.records()[:2]
        state = service.fresh(records).state
        result = service.repair(state, [records[0]], {r.record_id: r for r in records}.__getitem__)
        self.assertEqual(result.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())
        # On a prefix with coefficient one, the PSD tail affects only the negative side.
        from src.repair_service import CertifiedPrefix, StageOutput
        stage = service.job.stages[1]
        prefix = CertifiedPrefix(service.job.manifest_digest, (StageOutput("first", ((0, 1),)),))
        _, bounds = service._proposal(state.groups[0], state.groups[0].stages[1], stage, prefix, _Work())
        self.assertGreater(bounds[0], bounds[1])
        self.assertEqual(bounds[1], 0)


if __name__ == "__main__":
    unittest.main()
