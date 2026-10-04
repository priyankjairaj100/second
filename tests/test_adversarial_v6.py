"""Independent software attacks for v6 preparation, without research runs."""
from fractions import Fraction as Q
from types import SimpleNamespace
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.aggregate_response_service import AggregateRepairService
from src.box_response_provider import BoxResponseProvider, ParameterBox, grid_box
from src.certified_transformer import AutomaticResponseProvider
from src.linear_response import LinearResponseIndex, shifted_linear_response_bound
from src.repair_service import JobSpec, Record, StageSpec, UNKNOWN, _is_psd
from src.request_workload import prepare_original_scores, build_workload, validate_phase_pools
from src.response_moments import ResponseIndex
from src.service_telemetry import ServiceTelemetry, operation, timed
from src.worker_control import WorkerLimits, run_limited
from src.run_store import RunStore, digest
from src.experiment_campaign import _existing_campaign
from tests.test_certified_transformer import small_decoder, grids
from tests.test_result_analysis import record as analysis_record
from src.result_analysis import AnalysisError, analyze_runs


def narrow_box(decoder):
    first = decoder.stage_ids[0]
    epsilon = Q(1, 65536)
    bounds = tuple(tuple((x - epsilon, x + epsilon) for x in row)
                   for row in decoder.stage_weights(first))
    return ParameterBox({first: bounds}, 'independent fixed full-coordinate software box')


class AdversarialBoxTests(unittest.TestCase):
    def test_independent_coordinate_changes_have_finite_and_gram_enclosures(self):
        decoder, chart = small_decoder()
        provider = BoxResponseProvider(decoder, narrow_box(decoder))
        affine = AutomaticResponseProvider(decoder, chart)
        first, last = decoder.stage_ids[0], decoder.stage_ids[-1]
        base = decoder.stage_weights(first)
        radius = Q(1, 65536)
        record = Record('independent', decoder.record_payload((0, 1)))
        stage = StageSpec(last, decoder.dependencies(last), decoder.stage_weights(last), grids(decoder)[last], 1, 1)
        response, error = provider.intrinsic_moments(record, stage)
        region = provider.feature_enclosures(last, (0, 1))
        bound = shifted_linear_response_bound(LinearResponseIndex.from_records(response.basis, (response,)),
                                              ResponseIndex.from_records(error.basis, (error,)), (), 1, 1)
        for sign in (-1, 1):
            changed = tuple(tuple(x + (sign * radius if (i + j) % 2 else -sign * radius)
                                  for j, x in enumerate(row)) for i, row in enumerate(base))
            prefix = {first: changed}
            self.assertTrue(provider.contains_prefix(last, prefix))
            self.assertIsNone(affine.coefficients(last, prefix))
            actual = decoder.stage_features(last, (0, 1), prefix)
            for row, enclosure in zip(actual, region):
                for value, enclosed in zip(row, enclosure):
                    self.assertLessEqual(enclosed.value.lo - enclosed.error, value)
                    self.assertLessEqual(value, enclosed.value.hi + enclosed.error)
            gram = tuple(tuple(sum(a * b for a, b in zip(x, y)) for y in actual) for x in actual)
            raw, delta = bound.raw_surrogate_gram, bound.response_gram_error_normalized
            for direction in (-1, 1):
                difference = tuple(tuple(direction * (gram[i][j] - raw[i][j]) + (delta if i == j else 0)
                                         for j in range(len(raw))) for i in range(len(raw)))
                self.assertTrue(_is_psd(difference))

    def test_grid_recipe_encloses_installed_binary64_values(self):
        decoder, _ = small_decoder()
        configured = grids(decoder)
        stages = tuple(StageSpec(s, decoder.dependencies(s), decoder.stage_weights(s),
                                 tuple((Q(1, 10), Q(1, 3)) for _ in configured[s]), 1, 1)
                       for s in decoder.stage_ids)
        provider = BoxResponseProvider(decoder, grid_box(decoder, SimpleNamespace(stages=stages), 'fixed rational grid'))
        first, last = decoder.stage_ids[0], decoder.stage_ids[-1]
        prefix = {first: tuple(tuple(Q(1, 3) for _ in row) for row in decoder.stage_weights(first))}
        self.assertTrue(provider.contains_prefix(last, prefix))
        self.assertNotEqual(Q.from_float(float(Q(1, 3))), Q(1, 3))

    def test_unneeded_later_parameters_are_never_constructed(self):
        decoder, _ = small_decoder()
        provider = BoxResponseProvider(decoder, narrow_box(decoder))
        with patch.object(BoxResponseProvider, '_parameter_weights', side_effect=AssertionError('unused parameters')):
            feature = provider.feature_enclosures(decoder.stage_ids[0], (0, 1))
        self.assertEqual(len(feature), decoder.config.model_width)

    def test_unboxed_ancestors_require_finite_base_identity(self):
        decoder, _ = small_decoder()
        provider = BoxResponseProvider(decoder, ParameterBox({}, 'fixed empty parameter box'))
        first, second = decoder.stage_ids[:2]
        changed = [list(row) for row in decoder.stage_weights(first)]
        changed[0][0] += Q(1, 65536)
        self.assertFalse(provider.contains_prefix(second, {first: changed}))
        self.assertTrue(provider.contains_prefix(first, {first: changed}))

    def test_mutating_supplied_boxes_cannot_change_the_bound(self):
        decoder, _ = small_decoder()
        first = decoder.stage_ids[0]
        mutable = [[list((x, x)) for x in row] for row in decoder.stage_weights(first)]
        box = ParameterBox({first: mutable}, 'fixed immutable box')
        before = box.canonical_bytes()
        mutable[0][0][0] = Q(-10)
        self.assertEqual(before, box.canonical_bytes())
        with self.assertRaises(TypeError):
            box.bounds_by_stage[first] = ()


class AdversarialTelemetryTests(unittest.TestCase):
    def test_repeated_nested_categories_count_each_interval_once(self):
        ticks = iter((0, 2, 4, 7, 11, 15))
        collector = ServiceTelemetry(clock=lambda: next(ticks))
        with collector.span('outer'):
            with collector.span('same'):
                with collector.span('same'):
                    pass
        payload = collector.payload()
        self.assertEqual(payload['total_exclusive_ns'], 15)
        self.assertEqual(payload['timings']['outer']['exclusive_ns'], 6)
        self.assertEqual(payload['timings']['same'], {'exclusive_ns': 9, 'calls': 2})

    def test_exception_closes_context_and_allows_a_later_independent_operation(self):
        @timed('helper')
        def fail():
            raise ValueError('declared fixture failure')
        @operation
        def call():
            fail()
        first = ServiceTelemetry()
        with self.assertRaises(ValueError):
            call(telemetry=first)
        self.assertEqual(first.payload()['events']['operation.failed'], 1)
        second = ServiceTelemetry()
        with self.assertRaises(ValueError):
            call(telemetry=second)
        self.assertEqual(second.payload()['events']['operation.failed'], 1)


class AdversarialWorkloadTests(unittest.TestCase):
    def test_midpoint_infinity_does_not_promote_zero_leverage_records(self):
        stage = StageSpec('s', (), ((Q(2, 5), Q(1, 2)),), ((0, 1), (0, 1)), 1, 1)
        def evaluate(record, stage, prefix):
            return ((Q(record.record_id != 'zero'),), (Q(0),))
        service = AggregateRepairService(JobSpec((stage,), 'independent-selector', 'base', 1), evaluate,
                                         lambda record, stage: None, {}, lambda context: UNKNOWN,
                                         provider_id='none', extractor_id='none')
        records = (Record('zero', b'zero'), Record('nonzero', b'nonzero'))
        state = service.fresh(records).state
        with patch.object(AggregateRepairService, 'repair', side_effect=AssertionError('selector observed repair')):
            scores = prepare_original_scores(service, state, records, prepared_records_sha256='a'*64,
                                             source_sha256={'fixture': 'b'*64})
            workload = build_workload(('zero', 'nonzero'), root_id='root', seed=7, scores=scores,
                                      prepared_records_sha256='a'*64, original_state_sha256=state.digest)
        self.assertEqual(scores['records'][0]['difficulty'], [0, 1])
        self.assertEqual(scores['records'][1]['difficulty'], 'infinity')
        difficult = next(x for x in workload['requests'] if x['request_id'] == 'difficult_1_of_16')
        self.assertEqual(difficult['deleted_ids'], ['nonzero'])

    def test_phase_split_rejects_different_ids_for_identical_normalized_text(self):
        pools = {phase: [{'record_id': phase, 'document_id': phase,
                          'normalized_text_sha256': code*64, 'payload_sha256': code*64}]
                 for phase, code in [('development', 'a'), ('confirmation', 'a'), ('evaluation', 'b')]}
        with self.assertRaisesRegex(ValueError, 'crosses phases'):
            validate_phase_pools(pools)


class AdversarialWorkerTests(unittest.TestCase):
    def test_invalid_limit_acknowledgment_is_sealed_and_never_retried(self):
        limits = WorkerLimits(10, 5, 256 * 1024 * 1024, 1, (min(os.sched_getaffinity(0)),))
        with tempfile.TemporaryDirectory() as directory:
            ack = Path(directory) / 'attempt-0001' / 'limits-ack.pending.json'
            command = [sys.executable, '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).write_text("{}")', str(ack)]
            first = run_limited(command, directory, limits, identity={'fixture': 'invalid_ack'})
            self.assertEqual(first['status'], 'complete')
            self.assertEqual(first['outcome']['status'], 'failed')
            self.assertEqual(first['outcome']['kind'], 'limits_ack_invalid')
            second = run_limited(command, directory, limits, identity={'fixture': 'invalid_ack'})
            self.assertEqual(first, second)
            self.assertFalse((Path(directory) / 'attempt-0002').exists())


class AdversarialCampaignTests(unittest.TestCase):
    def test_completed_campaign_checks_failed_worker_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worker_root = root / 'worker'
            with RunStore(worker_root, {'worker': 'failure'}) as worker:
                worker.write_artifact('stderr-summary.json', b'original failure evidence')
                worker.finish({'status': 'complete', 'outcome': {'status': 'failed'}})
            record = worker_root / 'result.json'
            campaign_root = root / 'campaign'
            identity = {'campaign': 'independent fixture'}
            with RunStore(campaign_root, identity) as campaign:
                campaign.write_artifact('inventory.json', b'fixed inventory')
                campaign.finish({'status': 'complete', 'runs': [{'status': 'failed',
                    'worker_record_path': str(record), 'worker_record_sha256': digest(record.read_bytes())}]})
            self.assertIsNotNone(_existing_campaign(campaign_root, identity))
            (worker.attempt / 'stderr-summary.json').write_bytes(b'changed failure evidence')
            with self.assertRaisesRegex(ValueError, 'artifact hash mismatch'):
                _existing_campaign(campaign_root, identity)


class AdversarialAnalysisContractTests(unittest.TestCase):
    def test_one_configuration_cannot_mix_service_modes(self):
        first, second = analysis_record('r0'), analysis_record('r1')
        first['service_mode'] = 'certified'
        second['service_mode'] = 'fixed_reference'
        with self.assertRaises(AnalysisError):
            analyze_runs((first, second), draws=10)

    def test_one_configuration_cannot_mix_chart_or_service_hashes(self):
        for field in ('chart_sha256', 'service_manifest_sha256'):
            with self.subTest(field=field):
                first, second = analysis_record('r0'), analysis_record('r1')
                first[field], second[field] = 'c'*64, 'd'*64
                with self.assertRaises(AnalysisError):
                    analyze_runs((first, second), draws=10)

    def test_observed_contract_hash_cannot_disappear_within_configuration(self):
        for field in ('chart_sha256', 'service_manifest_sha256'):
            with self.subTest(field=field):
                first, second = analysis_record('r0'), analysis_record('r1')
                first[field] = 'c'*64
                with self.assertRaises(AnalysisError):
                    analyze_runs((first, second), draws=10)

    def test_missing_planned_run_keeps_its_denominator_with_unknown_optional_hashes(self):
        observed, missing = analysis_record('r0'), analysis_record('r1')
        observed.update(chart_sha256='c'*64, service_manifest_sha256='d'*64)
        result = analyze_runs((observed,), planned_runs=(dict(observed), missing), draws=10)['strata'][0]
        self.assertEqual(result['planned_attempt_count'], 2)
        self.assertEqual(result['methods']['repair']['outcomes']['missing_run'], 1)
        self.assertEqual(result['chart_sha256'], 'c'*64)

    def test_frozen_plan_rejects_a_changed_service_mode(self):
        observed = analysis_record()
        planned = dict(observed, service_mode='identity_only')
        observed['service_mode'] = 'certified'
        with self.assertRaises(AnalysisError):
            analyze_runs((observed,), planned_runs=(planned,), draws=10)


if __name__ == '__main__':
    unittest.main()
