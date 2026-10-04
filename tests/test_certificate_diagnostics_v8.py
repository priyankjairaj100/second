"""Bounded external certificate diagnostics; no empirical benchmark data."""
from fractions import Fraction as Q
import json
import unittest

from src.aggregate_response_service import AggregateRepairService
from src.linear_response import linear_record_moments
from src.repair_service import JobSpec, Record, StageSpec
from src.response_moments import ResponseBasis, record_moments
from src.response_service_adapter import ResponseQuery, ResponseStageContract
from src.service_telemetry import DiagnosticLimits, ServiceTelemetry
from tests import test_aggregate_response_service as fixture
from tests import test_telemetry_baselines_v6 as control_fixture


def stages(collector):
    return {row['stage_id']: row for row in collector.payload()['certificate_funnel']['stages']}


def fraction(value):
    assert value['encoding'] == 'rational'
    return Q(value['numerator'], value['denominator'])


def scalar_bound_service(width=1):
    weights = ((Q(1, 2),),) if width == 1 else ((Q(2, 5), Q(2, 5)),)
    stage = StageSpec('only', (), weights, ((0, 1),) * width, 1, 1)
    job = JobSpec((stage,), 'exact-constant-features', 'fixed-zero-anchor', 1)
    response = ResponseBasis('response', width, 1, True)
    error = ResponseBasis('error', 1, 3, True)
    contract = ResponseStageContract(response, error, 0)
    def intrinsic(record, stage):
        anchor = linear_record_moments(response, record.record_id, record.content_digest,
                                       (tuple((Q(0),) for _ in range(width)),))
        residual = record_moments(error, record.record_id, record.content_digest,
                                  (((Q(width),),), ((Q(0),),), ((Q(0),),)))
        return anchor, residual
    def target(record, stage, prefix):
        return tuple((Q(1),) for _ in range(width))
    def query(ctx):
        return ResponseQuery(ctx.binding, (), Q(0), 'known constant feature error')
    return AggregateRepairService(job, target, intrinsic, {'only': contract}, query,
        provider_id='constant-proof', extractor_id='zero-anchor', verifier_policy='spectral_or_interval')


class CertificateDiagnosticsTests(unittest.TestCase):
    def test_successful_funnel_preserves_canonical_state_and_has_exact_cell_summaries(self):
        service, _, _, _ = fixture.AggregateServiceTests().build()
        records = fixture.AggregateServiceTests().records()[:2]
        old = service.fresh(records).state
        collector = ServiceTelemetry()
        observed = service.repair(old, records[:1], lambda _: self.fail('unexpected replay'), telemetry=collector)
        expected = service.repair(old, records[:1], lambda _: self.fail('unexpected replay'))
        self.assertEqual(observed.state.canonical_bytes(), expected.state.canonical_bytes())
        self.assertNotIn(b'certificate_funnel', observed.state.canonical_bytes())
        funnel = collector.payload()['certificate_funnel']
        self.assertEqual(funnel['schema'], 'certificate-funnel-v1')
        self.assertTrue(funnel['operations'][-1]['produced_complete_model'])
        self.assertGreater(observed.ledger.count('diagnostic_observations_recorded'), 0)
        self.assertIn('certificate_diagnostics', collector.payload()['timings'])
        for row in stages(collector).values():
            self.assertEqual(row['status'], 'complete')
            events = row['events']
            self.assertEqual(events['domain_query']['last']['status'], 'accepted_provider_query')
            result = events['spectral_certificate']['last']
            self.assertTrue(result['accepted'])
            self.assertEqual(result['failed_cells'], 0)
            self.assertGreaterEqual(fraction(result['samples'][0]['radius_squared']), 0)
            self.assertEqual(events['stage_completed']['last']['route'], 'transport_certificate')
            self.assertNotIn('feature_evaluation_attempted', events)
        encoded = json.dumps(funnel)
        self.assertNotIn('[1,1]', encoded)
        self.assertNotIn('record_id', encoded)

    def test_provider_unknown_radius_rejection_and_missing_descriptors_are_distinct(self):
        records = fixture.AggregateServiceTests().records()[:2]
        source = {r.record_id: r for r in records}.__getitem__
        unknown, _, _, _ = fixture.AggregateServiceTests().build(query_unknown=True)
        collector = ServiceTelemetry()
        unknown.repair(unknown.fresh(records).state, (), source, telemetry=collector)
        self.assertEqual(stages(collector)['second']['events']['domain_query']['last']['status'], 'provider_unknown')
        self.assertEqual(stages(collector)['second']['events']['feature_evaluation_completed']['count'], 2)
        radius, _, _, _ = fixture.AggregateServiceTests().build(chart=0)
        collector = ServiceTelemetry()
        radius.repair(radius.fresh(records).state, (), source, telemetry=collector)
        event = stages(collector)['second']['events']['domain_query']['last']
        self.assertEqual(event['status'], 'coefficient_radius_exceeded')
        self.assertGreater(fraction(event['coefficient_norm_squared']), fraction(event['allowed_norm_squared']))
        missing, _, _, _ = fixture.AggregateServiceTests().build(missing=('a',))
        collector = ServiceTelemetry()
        missing.repair(missing.fresh(records).state, (), source, telemetry=collector)
        events = stages(collector)['second']['events']
        self.assertEqual(events['proposal_unavailable']['last']['reason'], 'unavailable_aggregate_descriptors')
        self.assertNotIn('domain_query', events)
        self.assertEqual(events['aggregate_descriptor_status']['last']['unavailable_records'], 1)

    def test_full_replay_and_reference_controls_do_not_claim_unrun_certificates(self):
        service, records = control_fixture.TelemetryControlTests().fixture()
        old = service.fresh(records[:2]).state
        source = {r.record_id: r for r in records}.__getitem__
        for mode in ('full_replay', 'identity_only', 'fixed_reference'):
            collector = ServiceTelemetry()
            result = service.repair(old, (), source, mode=mode, telemetry=collector)
            self.assertEqual(result.state.canonical_bytes(), old.canonical_bytes())
            row = stages(collector)['second']
            events = row['events']
            if mode == 'full_replay':
                self.assertEqual(events['certificate_bypassed']['last']['reason'], 'full_replay_control')
                self.assertNotIn('domain_query', events)
                self.assertNotIn('finite_gram_bound', events)
                self.assertNotIn('spectral_certificate', events)
                self.assertEqual(events['feature_evaluation_completed']['count'], 2)
            elif mode == 'identity_only':
                self.assertEqual(events['identity_gate']['last']['status'], 'base_ancestor_mismatch')
                self.assertNotIn('domain_query', events)
            else:
                self.assertEqual(events['finite_gram_bound']['last']['proposal'], 'fixed_reference')
                self.assertGreater(fraction(events['finite_gram_bound']['last']['tangent_energy']), 0)

    def test_relative_scale_keeps_original_normalization_and_raw_bound_units(self):
        service, _, _, _ = fixture.AggregateServiceTests().build(normalization=7)
        records = fixture.AggregateServiceTests().records()[:2]
        old = service.fresh(records).state
        collector = ServiceTelemetry()
        service.repair(old, (), {r.record_id: r for r in records}.__getitem__, telemetry=collector)
        event = stages(collector)['second']['events']['relative_enclosure']['first']
        negative = fraction(event['raw_negative_error'])
        self.assertEqual(fraction(event['normalization']), 7)
        self.assertEqual(fraction(event['lower_scale']), 1-negative/7)

    def test_interval_acceptance_and_rejection_report_actual_cells_and_replay(self):
        records = [Record('a', b'a'), Record('b', b'b')]
        for width in (1, 2):
            service = scalar_bound_service(width)
            old = service.fresh(records).state
            collector = ServiceTelemetry()
            result = service.repair(old, records[:1], {r.record_id: r for r in records}.__getitem__, telemetry=collector)
            self.assertEqual(result.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())
            events = stages(collector)['only']['events']
            self.assertEqual(events['spectral_skipped']['last']['reason'], 'nonpositive_lower_scale')
            interval = events['interval_certificate']['first']
            self.assertEqual(interval['accepted'], width == 1)
            if width == 1:
                self.assertEqual(fraction(interval['samples'][0]['upper_margin']), 0)
                self.assertNotIn('group_replay_started', events)
            else:
                self.assertGreater(interval['failed_cells'], 0)
                self.assertEqual(interval['sample_selection'], 'first_failed')
                self.assertEqual(events['group_replay_completed']['count'], 1)
                self.assertEqual(events['feature_evaluation_completed']['count'], 1)

    def test_evaluator_abort_marks_failed_stage_and_no_completed_model(self):
        base, _, _, _ = fixture.AggregateServiceTests().build(query_unknown=True)
        fail = {'enabled': False}
        def target(record, stage, prefix):
            if fail['enabled'] and stage.stage_id == 'second':
                raise ArithmeticError('fixture finite evaluator abort')
            return base.evaluator(record, stage, prefix)
        service = AggregateRepairService(base.job, target, base.intrinsic_moments, base.contracts, base.query,
            provider_id=base.provider_id, extractor_id=base.extractor_id)
        records = fixture.AggregateServiceTests().records()[:2]
        old = service.fresh(records).state
        before = old.canonical_bytes()
        fail['enabled'] = True
        collector = ServiceTelemetry()
        with self.assertRaises(ArithmeticError):
            service.repair(old, (), {r.record_id: r for r in records}.__getitem__, telemetry=collector)
        self.assertEqual(stages(collector)['first']['status'], 'complete')
        self.assertEqual(stages(collector)['second']['status'], 'failed')
        self.assertIn('feature_evaluation_failed', stages(collector)['second']['events'])
        self.assertFalse(collector.payload()['certificate_funnel']['operations'][-1]['produced_complete_model'])
        self.assertEqual(old.canonical_bytes(), before)

    def test_stage_event_caps_omit_builders_and_payload_is_detached(self):
        collector = ServiceTelemetry(diagnostic_limits=DiagnosticLimits(max_stage_records=1, max_event_kinds_per_stage=1,
                                                                       max_cell_samples=1, max_integer_bits=16))
        huge = Q(1 << 100000, 3)
        for i in range(100):
            collector.diagnostic('one', 'bound', values={'x': huge, 'i': i})
        collector.diagnostic('one', 'another', build=lambda _: self.fail('omitted event builder ran'))
        collector.diagnostic('two', 'bound', build=lambda _: self.fail('omitted stage builder ran'))
        payload = collector.payload()
        funnel = payload['certificate_funnel']
        self.assertEqual(len(funnel['stages']), 1)
        event = funnel['stages'][0]['events']['bound']
        self.assertEqual(event['count'], 100)
        self.assertEqual(event['first']['i'], 0)
        self.assertEqual(event['last']['i'], 99)
        self.assertEqual(event['last']['x']['encoding'], 'rational_magnitude')
        self.assertGreater(funnel['counters']['event_kind_observations_omitted'], 0)
        self.assertGreater(funnel['counters']['stage_observations_omitted'], 0)
        self.assertLess(len(json.dumps(payload)), 10000)
        event['last']['i'] = -100
        self.assertEqual(collector.payload()['certificate_funnel']['stages'][0]['events']['bound']['last']['i'], 99)

    def test_disposition_and_total_counters_preserve_intermediate_observations(self):
        collector = ServiceTelemetry()
        for status in ('accepted_provider_query', 'provider_unknown', 'accepted_provider_query'):
            collector.diagnostic('stage', 'domain_query', values={'status': status})
        for count in (2, 3, 4):
            collector.diagnostic('stage', 'aggregate_descriptor_status', values={
                'retained_records': count, 'unavailable_records': 1, 'contract_available': True})
        row = stages(collector)['stage']
        self.assertEqual(row['dispositions']['domain_query:status=provider_unknown'], 1)
        self.assertEqual(row['dispositions']['domain_query:status=accepted_provider_query'], 2)
        self.assertEqual(row['totals']['aggregate_descriptor_status:retained_records'], 9)
        self.assertEqual(row['totals']['aggregate_descriptor_status:unavailable_records'], 3)
        collector.event('huge', count=1 << 100000)
        self.assertEqual(collector.payload()['events']['huge'], (1 << 64)-1)
        self.assertEqual(collector.payload()['certificate_funnel']['counters']['counter_values_saturated'], 1)
        self.assertLess(len(json.dumps(collector.payload())), 10000)

    def test_model_only_result_marks_complete_model_but_prepared_index_does_not(self):
        from src.model_fresh import fresh_model
        service, _, _, _ = fixture.AggregateServiceTests().build()
        records = fixture.AggregateServiceTests().records()
        original = service.fresh(records).state
        collector = ServiceTelemetry()
        fresh_model(service.job, service.evaluator, records, target_digest='a'*64, telemetry=collector)
        service.prepare_index(original, records[:1], telemetry=collector)
        operations = collector.payload()['certificate_funnel']['operations']
        self.assertEqual([row['operation'] for row in operations], ['fresh_model', 'prepare_index'])
        self.assertEqual([row['produced_complete_model'] for row in operations], [True, False])

    def test_complete_deletion_records_completion_without_feature_evaluations(self):
        service, _, _, _ = fixture.AggregateServiceTests().build()
        records = fixture.AggregateServiceTests().records()
        old = service.fresh(records).state
        collector = ServiceTelemetry()
        result = service.repair(old, records, lambda _: self.fail('empty retained read'), telemetry=collector)
        self.assertEqual(result.state.canonical_bytes(), service.fresh(()).state.canonical_bytes())
        self.assertTrue(collector.payload()['certificate_funnel']['operations'][-1]['produced_complete_model'])
        for row in stages(collector).values():
            self.assertEqual(row['status'], 'complete')
            self.assertEqual(row['events']['stage_started']['last']['retained_records'], 0)
            self.assertNotIn('feature_evaluation_attempted', row['events'])


if __name__ == '__main__':
    unittest.main()
