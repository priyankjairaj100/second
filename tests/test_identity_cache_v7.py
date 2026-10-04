"""Behavioral fixtures only. No dataset studies or performance claims."""
from dataclasses import replace, FrozenInstanceError
from fractions import Fraction as Q
import json
import unittest

from src.aggregate_response_service import StateParseLimits
from src.identity_cache import IdentityCacheService, IdentityCacheState, IdentityCacheRunnerAdapter
from src.repair_service import JobSpec, Record, StageSpec
from src.service_telemetry import ServiceTelemetry


class IdentityCacheTests(unittest.TestCase):
    def fixture(self, *, transitive=False):
        first = StageSpec('first', (), ((Q(2, 5), Q(2, 5)),), ((0, 1), (0, 1)), 1, 1)
        if transitive:
            middle = StageSpec('middle', ('first',), ((0,),), ((0,),), 1, 1)
            last = StageSpec('last', ('middle',), first.weights, first.grids, 1, 1)
            separate = StageSpec('separate', (), first.weights, first.grids, 1, 1)
            stages = (first, middle, last, separate)
        else:
            stages = (first, StageSpec('second', ('first',), first.weights, first.grids, 1, 1))
        job = JobSpec(stages, 'cache-fixture-evaluator-v1', 'cache-fixture-reference-v1')
        calls = []
        def evaluate(record, stage, prefix):
            self.assertEqual(prefix.manifest_digest, job.manifest_digest)
            calls.append((record.record_id, stage.stage_id, prefix.digest))
            data = json.loads(record.payload)
            if stage.stage_id == 'middle':
                return ((Q(data[0]),),)
            added = prefix.as_mapping()['first'][0][1] if stage.stage_id in ('second', 'last') else 0
            return ((Q(data[0]) + added,), (Q(data[1]),))
        return IdentityCacheService(job, evaluate), calls

    @staticmethod
    def records():
        return (Record('a', b'[1,1]'), Record('b', b'[0,1]'), Record('c', b'[1,2]'))

    def source(self, records):
        return {r.record_id: r for r in records}.__getitem__

    def test_identity_route_never_reads_retained_records(self):
        service, calls = self.fixture()
        records = (Record('a', b'[0,1]'), Record('b', b'[0,1]'))
        original = service.fresh(records).state
        before = original.canonical_bytes()
        calls.clear()
        result = service.repair(original, records[:1], lambda _: self.fail('retained read'),
                                expected_digest=original.digest)
        self.assertEqual([(rid, sid) for rid, sid, _ in calls], [('a', 'first'), ('a', 'second')])
        self.assertTrue(all(a.route == 'old_ancestor_identity' for a in result.stages))
        self.assertEqual(result.ledger.count('retained_source_record_reads'), 0)
        self.assertEqual(result.ledger.count('deleted_target_evaluator_calls'), 2)
        self.assertEqual(result.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())
        self.assertEqual(original.canonical_bytes(), before)

    def test_changed_ancestor_replays_and_refreshes_exact_gram(self):
        service, calls = self.fixture()
        records = self.records()[:2]
        original = service.fresh(records).state
        self.assertEqual(original.model[0].codes[0][1], 1)
        calls.clear()
        reads = []
        def source(rid):
            reads.append(rid)
            return self.source(records)(rid)
        result = service.repair(original, records[:1], source, expected_digest=original.digest)
        self.assertEqual(result.state.model[0].codes[0][1], 0)
        self.assertEqual([a.route for a in result.stages], ['old_ancestor_identity', 'changed_ancestor_replay'])
        self.assertEqual(reads, ['b'])
        self.assertEqual([(rid, sid) for rid, sid, _ in calls], [('a', 'first'), ('b', 'second')])
        fresh = service.fresh(records[1:])
        self.assertEqual(result.state.canonical_bytes(), fresh.state.canonical_bytes())
        self.assertNotEqual(original.stages[1].prefix_digest, result.state.stages[1].prefix_digest)

    def test_transitive_ancestor_changes_and_unrelated_branches(self):
        service, _ = self.fixture(transitive=True)
        records = self.records()[:2]
        original = service.fresh(records).state
        result = service.repair(original, records[:1], self.source(records), expected_digest=original.digest)
        self.assertEqual(original.model[1], result.state.model[1])
        self.assertEqual(result.stages[2].route, 'changed_ancestor_replay')
        self.assertEqual(result.stages[3].route, 'old_ancestor_identity')
        self.assertEqual(result.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())

    def test_repeated_reordered_and_combined_deletion_are_canonical(self):
        service, _ = self.fixture()
        records, source = self.records(), self.source(self.records())
        original = service.fresh(records).state
        left = service.repair(original, records[:1], source, expected_digest=original.digest).state
        left = service.repair(left, records[1:2], source, expected_digest=left.digest).state
        right = service.repair(original, records[1:2], source, expected_digest=original.digest).state
        right = service.repair(right, records[:1], source, expected_digest=right.digest).state
        combined = service.repair(original, records[:2], source, expected_digest=original.digest).state
        fresh = service.fresh(records[2:]).state
        self.assertEqual(left.canonical_bytes(), right.canonical_bytes())
        self.assertEqual(left.canonical_bytes(), combined.canonical_bytes())
        self.assertEqual(left.canonical_bytes(), fresh.canonical_bytes())
        self.assertEqual(left.retained_ids, ('c',))

    def test_full_deletion_uses_empty_target_without_feature_evaluation(self):
        service, calls = self.fixture()
        records = self.records()
        original = service.fresh(records).state
        calls.clear()
        result = service.repair(original, records, lambda _: self.fail('retained read'),
                                expected_digest=original.digest)
        self.assertEqual(calls, [])
        self.assertTrue(all(a.route == 'empty_retained' for a in result.stages))
        self.assertEqual(result.state.canonical_bytes(), service.fresh(()).state.canonical_bytes())
        again = service.repair(result.state, (), lambda _: self.fail('read'), expected_digest=result.state.digest)
        self.assertEqual(again.state.canonical_bytes(), result.state.canonical_bytes())

    def test_empty_request_is_canonical_without_reads_or_evaluation(self):
        service, calls = self.fixture()
        original = service.fresh(self.records()).state
        calls.clear()
        result = service.repair(original, (), lambda _: self.fail('read'), expected_digest=original.digest)
        self.assertEqual(calls, [])
        self.assertEqual(result.state.canonical_bytes(), original.canonical_bytes())

    def test_indexed_fresh_receives_same_cache_and_work(self):
        service, _ = self.fixture()
        records, source = self.records(), self.source(self.records())
        state = service.fresh(records).state
        repair = service.repair(state, records[:1], source, expected_digest=state.digest)
        indexed = service.indexed_fresh(state, records[:1], source, expected_digest=state.digest)
        self.assertEqual(repair.state.canonical_bytes(), indexed.state.canonical_bytes())
        self.assertEqual(repair.ledger, indexed.ledger)
        self.assertEqual(repair.stages, indexed.stages)

    def test_forged_cache_rejected_before_source_reads(self):
        service, calls = self.fixture()
        state = service.fresh(self.records()).state
        wrong = replace(state.stages[0], raw_gram=((Q(100), Q(0)), (Q(0), Q(100))))
        forged = replace(state, stages=(wrong,) + state.stages[1:])
        calls.clear()
        with self.assertRaisesRegex(ValueError, 'trusted expected digest'):
            service.repair(forged, (), lambda _: self.fail('read'), expected_digest=state.digest)
        self.assertEqual(calls, [])
        with self.assertRaises(TypeError):
            service.repair(state, (), lambda _: None)

    def test_wrong_prefix_and_non_psd_cache_rejected(self):
        service, _ = self.fixture()
        state = service.fresh(self.records()).state
        wrong = replace(state.stages[1], prefix_digest='0' * 64)
        forged = replace(state, stages=(state.stages[0], wrong))
        with self.assertRaisesRegex(ValueError, 'prefix binding'):
            service.repair(forged, (), lambda _: self.fail('read'), expected_digest=forged.digest)
        wrong = replace(state.stages[0], raw_gram=((Q(1), Q(2)), (Q(2), Q(1))))
        forged = replace(state, stages=(wrong,) + state.stages[1:])
        with self.assertRaisesRegex(ValueError, 'positive semidefinite'):
            service.repair(forged, (), lambda _: self.fail('read'), expected_digest=forged.digest)

    def test_payload_failures_preserve_committed_cache(self):
        service, _ = self.fixture()
        records = self.records()[:2]
        state = service.fresh(records).state
        before = state.canonical_bytes()
        with self.assertRaisesRegex(ValueError, 'deleted source content'):
            service.repair(state, [Record('a', b'[9,9]')], lambda _: self.fail('read'), expected_digest=state.digest)
        with self.assertRaisesRegex(ValueError, 'retained source content'):
            service.repair(state, records[:1], lambda rid: Record(rid, b'[9,9]'), expected_digest=state.digest)
        with self.assertRaisesRegex(ValueError, 'wrong record'):
            service.repair(state, records[:1], lambda rid: records[0], expected_digest=state.digest)
        with self.assertRaisesRegex(ValueError, 'unique'):
            service.repair(state, [records[0]] * 2, self.source(records), expected_digest=state.digest)
        self.assertEqual(state.canonical_bytes(), before)
        with self.assertRaises(FrozenInstanceError):
            state.model = ()

    def test_persisted_canonical_state_limits_and_corruption(self):
        service, _ = self.fixture()
        state = service.fresh(self.records()).state
        raw = state.canonical_bytes()
        parsed = IdentityCacheState.from_canonical_bytes(raw)
        self.assertEqual(parsed, state)
        result = service.repair(parsed, (), lambda _: self.fail('read'), expected_digest=state.digest)
        self.assertEqual(result.state, state)
        with self.assertRaisesRegex(ValueError, 'max_bytes'):
            IdentityCacheState.from_canonical_bytes(raw, limits=StateParseLimits(max_bytes=1))
        with self.assertRaisesRegex(ValueError, 'canonical'):
            IdentityCacheState.from_canonical_bytes(raw + b' ')
        duplicate = raw.replace(b'{', b'{"schema":"x",', 1)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            IdentityCacheState.from_canonical_bytes(duplicate)

    def test_costs_include_setup_refresh_state_storage_and_telemetry(self):
        service, _ = self.fixture()
        records = self.records()[:2]
        setup = service.fresh(records)
        self.assertEqual(setup.ledger.count('fresh_target_evaluator_calls'), 4)
        self.assertEqual(setup.state.stored_gram_rationals, 8)
        self.assertEqual(setup.state.stored_model_rationals, 4)
        collector = ServiceTelemetry()
        result = service.repair(setup.state, records[:1], self.source(records),
                                expected_digest=setup.state.digest, telemetry=collector)
        counts = result.ledger
        self.assertEqual(counts.count('cache_stage_refreshes'), 2)
        self.assertEqual(counts.count('exact_factorization_calls'), 2)
        self.assertEqual(counts.count('canonical_serialized_bytes'), len(result.state.canonical_bytes()))
        self.assertEqual(counts.count('input_cache_serialized_bytes'), len(setup.state.canonical_bytes()))
        self.assertEqual(counts.count('committed_cache_integer_bits'), result.state.stored_integer_bits)
        payload = collector.payload()
        for name in ('cache_feature_extraction', 'cache_factor_rounding', 'cache_validation', 'cache_serialization'):
            self.assertIn(name, payload['timings'])
        self.assertGreater(payload['total_exclusive_ns'], 0)

    def test_matches_independent_aggregate_service_target(self):
        from tests import test_aggregate_response_service as fixtures
        aggregate, *_ = fixtures.AggregateServiceTests().build()
        cache = IdentityCacheService(aggregate.job, aggregate.evaluator)
        records = self.records()
        original = cache.fresh(records).state
        self.assertEqual(original.model, aggregate.fresh(records).state.model)
        result = cache.repair(original, records[:1], self.source(records), expected_digest=original.digest)
        self.assertEqual(result.state.model, aggregate.fresh(records[1:]).state.model)

    def test_adapter_requires_trusted_origin_and_preserves_equal_information(self):
        core, _ = self.fixture()
        records = self.records()
        direct = core.fresh(records).state
        adapter = IdentityCacheRunnerAdapter(core)
        with self.assertRaisesRegex(ValueError, 'trusted digest'):
            adapter.repair(direct, records[:1], self.source(records))
        state = adapter.load_state(direct.canonical_bytes(), expected_digest=direct.digest)
        repaired = adapter.repair(state, records[:1], self.source(records))
        prepared = adapter.prepare_index(state, records[:1])
        indexed = adapter.indexed_fresh(prepared.index, self.source(records))
        self.assertEqual(repaired.state, indexed.state)
        self.assertEqual(repaired.ledger, indexed.ledger)
        self.assertEqual(prepared.index.original.model, state.model)
        self.assertEqual(prepared.ledger.count('prepared_deleted_record_entries'), 1)
        self.assertEqual(prepared.ledger.count('deleted_target_evaluator_calls'), 0)

    def test_forced_replay_is_distinct_and_rejects_unsupported_mode(self):
        service, _ = self.fixture()
        records = (Record('a', b'[0,1]'), Record('b', b'[0,1]'))
        state = service.fresh(records).state
        replay = service.repair(state, records[:1], self.source(records), expected_digest=state.digest,
                                mode='full_replay')
        self.assertEqual([a.route for a in replay.stages], ['forced_full_replay'] * 2)
        self.assertEqual(replay.ledger.count('retained_replay_evaluator_calls'), 2)
        self.assertEqual(replay.ledger.count('deleted_target_evaluator_calls'), 0)
        self.assertEqual(replay.state, service.fresh(records[1:]).state)
        with self.assertRaisesRegex(ValueError, 'supports'):
            service.repair(state, (), self.source(records), expected_digest=state.digest, mode='fixed_reference')

    def test_adapter_origin_registry_is_bounded_and_reload_restores_trust(self):
        core, _ = self.fixture()
        adapter = IdentityCacheRunnerAdapter(core, max_trusted_states=2)
        records = self.records()
        old = adapter.fresh(records).state
        adapter.fresh(records[:2])
        newest = adapter.fresh(records[:1])
        self.assertEqual(newest.ledger.count('adapter_trusted_digest_entries'), 2)
        with self.assertRaisesRegex(ValueError, 'trusted digest'):
            adapter.repair(old, (), self.source(records))
        adapter.load_state(old.canonical_bytes(), expected_digest=old.digest)
        self.assertEqual(adapter.repair(old, (), self.source(records)).state, old)
        with self.assertRaises(ValueError):
            IdentityCacheRunnerAdapter(core, max_trusted_states=1)

    def test_existing_runner_can_compare_optional_cache_interface(self):
        import tempfile
        from tests import test_experiment_runner as runner_fixtures
        from src.experiment_runner import run_comparison
        from src.run_store import RunStore
        decoder, aggregate, records, heldout, metadata = runner_fixtures.ExperimentRunnerTests().fixture()
        service = IdentityCacheRunnerAdapter(IdentityCacheService(aggregate.job, aggregate.evaluator))
        with tempfile.TemporaryDirectory() as folder:
            result = run_comparison(decoder, service, records, ['0'], heldout, RunStore(folder, {'cache': 1}), metadata)
            self.assertEqual(result['status'], 'complete', result.get('failure'))
            for method in result['methods'].values():
                self.assertTrue(method['exact_state_equal'])
                self.assertTrue(method['exact_model_equal'])
            self.assertGreater(result['setup']['stored_aggregate_rationals'], 0)


if __name__ == '__main__':
    unittest.main()
