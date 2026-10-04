"""Provider evidence tests. No empirical datasets or performance claims."""
from fractions import Fraction as Q
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.box_response_provider import BoxResponseProvider, ParameterBox
from src.certified_transformer import AutomaticResponseProvider, UnsupportedCertificate
from src.instrumentation import instrumentation_scope
from src.repair_service import Record, StageSpec
from src.service_telemetry import DiagnosticLimits, ServiceTelemetry, operation, provider_diagnostic
from tests.test_certified_transformer import small_decoder, grids
from tests.test_box_response_provider import narrow_box


@operation
def observed(call):
    return call()


def event(collector, name):
    rows = collector.payload()['certificate_funnel']['stages']
    return next(row['events'][name]['last'] for row in rows if name in row['events'])


class ProviderDiagnosticTests(unittest.TestCase):
    def fixture(self):
        decoder, chart = small_decoder()
        sid = decoder.stage_ids[1]
        stage = StageSpec(sid, decoder.dependencies(sid), decoder.stage_weights(sid), grids(decoder)[sid], 1, 1)
        record = Record('fixture', decoder.record_payload((0, 1)))
        return decoder, chart, stage, record

    def test_affine_span_and_selected_box_failures_are_distinct(self):
        decoder, chart, stage, _ = self.fixture()
        provider = AutomaticResponseProvider(decoder, chart)
        first = decoder.stage_ids[0]
        for location, delta, expected in (((0,0), Q(1,4096), 'inconsistent_affine_span'),
                                          ((4,0), -Q(2,4096), 'selected_solution_outside_box')):
            changed = [list(row) for row in decoder.stage_weights(first)]
            changed[location[0]][location[1]] += delta
            collector = ServiceTelemetry()
            value = observed(lambda: provider.coefficients(stage.stage_id, {first: changed}), telemetry=collector)
            self.assertIsNone(value)
            self.assertEqual(event(collector, 'provider_domain_fit')['status'], expected)
        collector = ServiceTelemetry()
        coefficients = observed(lambda: provider.coefficients(stage.stage_id, {}), telemetry=collector)
        self.assertEqual(coefficients, (Q(0),))
        self.assertEqual(event(collector, 'provider_domain_fit')['status'], 'exact_fit')

    def test_affine_center_and_region_failures_preserve_unavailability(self):
        decoder, chart, stage, record = self.fixture()
        provider = AutomaticResponseProvider(decoder, chart)
        original = AutomaticResponseProvider.feature_jets
        for failure_region, expected in ((False, 'center_jets'), (True, 'region_jets')):
            def fail(self, stage_id, tokens, *, region):
                if region == failure_region:
                    raise UnsupportedCertificate('fixture denominator includes zero')
                return original(self, stage_id, tokens, region=region)
            collector = ServiceTelemetry()
            with patch.object(AutomaticResponseProvider, 'feature_jets', fail):
                result = observed(lambda: provider.intrinsic_moments(record, stage), telemetry=collector)
            self.assertIsNone(result)
            reason = event(collector, 'provider_extraction')
            self.assertEqual(reason['proof_phase'], expected)
            self.assertEqual(reason['failure_type'], 'UnsupportedCertificate')
            self.assertIn('denominator', reason['reason'])

    def test_error_components_match_descriptor_and_clean_output(self):
        decoder, chart, stage, record = self.fixture()
        provider = AutomaticResponseProvider(decoder, chart)
        collector = ServiceTelemetry()
        diagnostic = observed(lambda: provider.intrinsic_moments(record, stage), telemetry=collector)
        details = event(collector, 'provider_error_components')
        def exact(encoded):
            return Q(encoded['numerator'], encoded['denominator'])
        self.assertEqual(details['status'], 'available')
        self.assertEqual(details['record_content_sha256'], record.content_digest)
        constant = exact(details['finite_error']) + exact(details['center_error'])
        self.assertEqual(diagnostic[1].cross_moments[0][0][0], constant * constant)
        with instrumentation_scope('clean'):
            clean = observed(lambda: provider.intrinsic_moments(record, stage), telemetry=ServiceTelemetry())
        self.assertEqual(clean, diagnostic)

    def test_box_failure_phase_and_zero_error_base_shortcut(self):
        decoder, _, stage, record = self.fixture()
        provider = BoxResponseProvider(decoder, narrow_box(decoder))
        collector = ServiceTelemetry()
        with patch.object(BoxResponseProvider, 'feature_enclosures', side_effect=UnsupportedCertificate('fixture box failure')):
            value = observed(lambda: provider.intrinsic_moments(record, stage), telemetry=collector)
        self.assertIsNone(value)
        self.assertEqual(event(collector, 'provider_extraction')['proof_phase'], 'box_feature_enclosure')
        base = BoxResponseProvider(decoder, ParameterBox({}, 'fixed fixture base'))
        collector = ServiceTelemetry()
        value = observed(lambda: base.intrinsic_moments(record, stage), telemetry=collector)
        self.assertIsNotNone(value)
        details = event(collector, 'provider_error_components')
        self.assertEqual(details['proof_phase'], 'fixed_base_features')
        self.assertEqual(details['uniform_feature_error']['numerator'], 0)

    def test_clean_and_capped_hooks_never_run_lazy_builder(self):
        with instrumentation_scope('clean'):
            self.assertFalse(observed(lambda: provider_diagnostic('one', 'a', build=lambda _: self.fail('clean builder')), telemetry=ServiceTelemetry()))
        collector = ServiceTelemetry(diagnostic_limits=DiagnosticLimits(max_stage_records=1))
        def calls():
            self.assertTrue(provider_diagnostic('one', 'a', build=lambda _: {'status': 'recorded'}))
            self.assertFalse(provider_diagnostic('two', 'b', build=lambda _: self.fail('omitted builder')))
        observed(calls, telemetry=collector)
        self.assertEqual(collector.payload()['certificate_funnel']['counters']['stage_observations_omitted'], 1)


if __name__ == '__main__':
    unittest.main()
