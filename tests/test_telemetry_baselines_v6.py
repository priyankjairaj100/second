"""Correctness fixtures for matched controls and exclusive diagnostic timing."""
from fractions import Fraction as Q
import json
import unittest

from src.aggregate_response_service import AggregateRepairService
from src.repair_service import JobSpec, Record, StageSpec, _Work, _gram, _is_psd
from src.response_moments import record_moments
from src.service_telemetry import ServiceTelemetry, operation
from tests import test_aggregate_response_service as affine_fixture
from tests.test_certified_transformer import small_decoder, grids


def with_reference(service, reference):
    return AggregateRepairService(service.job, service.evaluator, service.intrinsic_moments,
                                  service.contracts, service.query,
                                  provider_id=service.provider_id, extractor_id=service.extractor_id,
                                  reference_weights=reference)


class TelemetryControlTests(unittest.TestCase):
    def fixture(self):
        fixture = affine_fixture.AggregateServiceTests()
        service, _, _, _ = fixture.build()
        # This affine fixture uses zero, not stage weights, as its fixed reference.
        reference = {s.stage_id: tuple(tuple(Q(0) for x in row) for row in s.weights)
                     for s in service.job.stages}
        return with_reference(service, reference), fixture.records()

    def test_nested_exclusive_intervals_with_repeated_names_and_failure(self):
        ticks = iter([0, 2, 5, 9, 12, 20])
        collector = ServiceTelemetry(clock=lambda: next(ticks))
        with collector.span('outer'):
            with collector.span('same'):
                with collector.span('same'):
                    pass
        result = collector.payload()
        self.assertEqual(result['total_exclusive_ns'], 20)
        self.assertEqual(result['timings']['outer']['exclusive_ns'], 10)
        self.assertEqual(result['timings']['same'], {'exclusive_ns': 10, 'calls': 2})
        failure = ServiceTelemetry(clock=iter([0, 7]).__next__)
        with self.assertRaises(ValueError):
            with failure.span('failure'):
                raise ValueError('fixture')
        self.assertEqual(failure.payload()['timings']['failure']['exclusive_ns'], 7)

    def test_all_controls_preserve_identical_canonical_state(self):
        service, records = self.fixture()
        old = service.fresh(records).state
        expected = service.fresh(records[1:]).state.canonical_bytes()
        for mode in ('certified', 'identity_only', 'fixed_reference', 'full_replay'):
            collector = ServiceTelemetry()
            result = service.repair(old, records[:1], {r.record_id: r for r in records}.__getitem__,
                                    mode=mode, telemetry=collector)
            self.assertEqual(result.state.canonical_bytes(), expected)
            data = collector.payload()
            self.assertEqual(data['events']['operation.completed'], 1)
            self.assertGreater(data['total_exclusive_ns'], 0)
            self.assertEqual(data['total_exclusive_ns'], sum(x['exclusive_ns'] for x in data['timings'].values()))
            self.assertIn('serialization', data['timings'])
            self.assertIn('extraction', data['timings'])
            self.assertIn('validation_metadata', data['timings'])
            self.assertIn('gram_accumulation', data['timings'])
            self.assertIn('factor_rounding', data['timings'])
            if mode == 'full_replay':
                self.assertNotIn('bound_query', data['timings'])
                self.assertIn('replay_feature_evaluation', data['timings'])

    def test_old_model_identity_does_not_imply_reference_identity(self):
        service, records = self.fixture()
        old = service.fresh(records[:2]).state
        collector = ServiceTelemetry()
        result = service.repair(old, (), {r.record_id: r for r in records}.__getitem__,
                                mode='identity_only', telemetry=collector)
        self.assertEqual(result.state.canonical_bytes(), old.canonical_bytes())
        self.assertNotEqual(old.model[0].codes, service.reference_weights['first'])
        self.assertGreater(result.ledger.count('identity_prefix_mismatch_groups'), 0)
        self.assertGreater(result.ledger.count('retained_replay_evaluator_calls'), 0)
        self.assertEqual(collector.payload()['events']['proposal.identity_prefix_mismatch'], 1)

    def test_identity_checks_transitive_ancestors(self):
        original, records = self.fixture()
        first, second = original.job.stages
        second = StageSpec('second', ('first',), ((0, 0),), second.grids, 1, 1)
        third = StageSpec('third', ('second',), first.weights, first.grids, 1, 1)
        job = JobSpec((first, second, third), 'three-stage-affine', 'base-affine', 1)
        contracts = dict(original.contracts)
        contracts['third'] = contracts['second']
        def target(record, stage, prefix):
            value = json.loads(record.payload)
            coefficient = 0 if stage.stage_id == 'first' else prefix.as_mapping()['first'][0][1]
            return ((Q(value[0]) + coefficient,), (Q(value[1]),))
        def intrinsic(record, stage):
            return original.intrinsic_moments(record, original.job.stages[1] if stage.stage_id == 'third' else stage)
        reference = {s.stage_id: ((Q(0), Q(0)),) for s in job.stages}
        service = AggregateRepairService(job, target, intrinsic, contracts, original.query,
                    provider_id='three-stage-affine', extractor_id='base-affine', reference_weights=reference)
        old = service.fresh(records[:2]).state
        self.assertEqual(old.model[1].codes, reference['second'])
        self.assertNotEqual(old.model[0].codes, reference['first'])
        repaired = service.repair(old, (), {r.record_id: r for r in records}.__getitem__, mode='identity_only')
        self.assertEqual(repaired.state.canonical_bytes(), old.canonical_bytes())
        self.assertEqual(repaired.ledger.count('identity_prefix_mismatch_groups'), 2)

    def test_missing_reference_mapping_replays_without_changing_manifest(self):
        service, records = self.fixture()
        raw, _, _, _ = affine_fixture.AggregateServiceTests().build()
        self.assertEqual(service.manifest_digest, raw.manifest_digest)
        old = raw.fresh(records).state
        result = raw.repair(old, (), {r.record_id: r for r in records}.__getitem__, mode='identity_only')
        self.assertEqual(old.canonical_bytes(), result.state.canonical_bytes())
        self.assertEqual(result.ledger.count('identity_reference_unavailable_groups'), 2)

    def test_fixed_reference_bound_covers_actual_changed_gram(self):
        service, records = self.fixture()
        state = service.fresh(records[:2]).state
        stage = service.job.stages[1]
        prefix = service._engine._prefix(stage, state.model)
        group = state.groups[0]
        raw, bound = service._proposal(group, group.stages[1], stage, prefix, _Work(), 'fixed_reference')
        actual = tuple(tuple(sum((_gram(service.evaluator(r, stage, prefix), _Work())[i][j]
                                  for r in records[:2]), Q(0)) for j in range(stage.width))
                       for i in range(stage.width))
        self.assertEqual(raw, group.stages[1].response.constant_gram)
        self.assertNotEqual(raw, actual)
        negative, positive = bound
        lower = tuple(tuple(actual[i][j] - raw[i][j] + (negative if i == j else 0)
                            for j in range(stage.width)) for i in range(stage.width))
        upper = tuple(tuple(raw[i][j] - actual[i][j] + (positive if i == j else 0)
                            for j in range(stage.width)) for i in range(stage.width))
        self.assertTrue(_is_psd(lower))
        self.assertTrue(_is_psd(upper))

    def test_identity_gate_keeps_finite_error_floor(self):
        service, records = self.fixture()
        base_extract = service.intrinsic_moments
        def with_error(record, stage):
            response, _ = base_extract(record, stage)
            contract = service.contracts[stage.stage_id]
            entries = (((Q(1, 100),),),) + (((Q(0),),),) * (contract.error_basis.terms - 1)
            return response, record_moments(contract.error_basis, record.record_id, record.content_digest, entries)
        bounded = AggregateRepairService(service.job, service.evaluator, with_error, service.contracts, service.query,
                    provider_id=service.provider_id, extractor_id='nonzero-floor-fixture',
                    reference_weights=service.reference_weights)
        state = bounded.fresh(records).state
        stage = bounded.job.stages[0]
        prefix = bounded._engine._prefix(stage, ())
        group = state.groups[0]
        _, bound = bounded._proposal(group, group.stages[0], stage, prefix, _Work(), 'identity_only')
        self.assertGreater(bound[0], 0)
        self.assertGreater(bound[1], 0)

    def test_failure_telemetry_survives_without_mutation_or_context_leak(self):
        service, records = self.fixture()
        old = service.fresh(records).state
        before = old.canonical_bytes()
        collector = ServiceTelemetry()
        with self.assertRaises(ValueError):
            service.repair(old, [Record(records[0].record_id, b'wrong')], lambda _: None, telemetry=collector)
        data = collector.payload()
        self.assertEqual(data['events']['operation.failed'], 1)
        self.assertEqual(data['reasons'][0]['reason'], 'ValueError')
        self.assertEqual(old.canonical_bytes(), before)
        frozen = collector.payload()
        service.fresh(records)
        self.assertEqual(collector.payload(), frozen)

    def test_certified_finite_decoder_controls_match_complete_state(self):
        decoder, chart = small_decoder()
        original_service = decoder.make_repair_service(grids(decoder), chart, group_count=1)
        service = with_reference(original_service, {s: decoder.stage_weights(s) for s in decoder.stage_ids})
        records = [Record('a', decoder.record_payload((0, 1))), Record('b', decoder.record_payload((1, 0)))]
        state = service.fresh(records).state
        expected = service.fresh(records[1:]).state.canonical_bytes()
        for mode in ('identity_only', 'fixed_reference', 'full_replay'):
            result = service.repair(state, records[:1], {r.record_id: r for r in records}.__getitem__, mode=mode)
            self.assertEqual(result.state.canonical_bytes(), expected)

    def test_collector_reentry_is_rejected_and_recovers(self):
        collector = ServiceTelemetry()
        @operation
        def nested():
            @operation
            def child():
                return None
            child(telemetry=collector)
        with self.assertRaises(RuntimeError):
            nested(telemetry=collector)
        self.assertEqual(collector.payload()['events']['operation.failed'], 1)


if __name__ == '__main__':
    unittest.main()
