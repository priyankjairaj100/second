"""V31 integration fixtures: finite toy decoder only, no empirical inference."""
from dataclasses import replace
from fractions import Fraction
import unittest
from unittest.mock import patch

from scripts import run_compressed_service_v31 as worker
from tests.test_compressed_service_worker_v30 import policy as old_policy
from tests import test_compressed_service_worker_v30 as fixtures
from src.fixed_compressed_state_v26 import from_factor_state, serialize
from src.ordered_fixed_service_v30 import OrderedFixedAnchorService, ordered_preparer_binding
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.dyadic_row_target import build_dyadic_row_target
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


def policy(method='repair'):
    return dict(old_policy(method), codec_bits=48, decoder_backend='ordered', certificate_backend='sparse')


class NativeBoxIntegrationTests(unittest.TestCase):
    def test_policy_rejects_undeclared_precision_decoder_and_route(self):
        worker.validate_policy(policy())
        worker.validate_policy(policy('convert_lossless'))
        for change in ({'codec_bits':40}, {'codec_bits':True}, {'decoder_backend':'scalar'},
                       {'certificate_backend':'primal'}, {'use_candidates':True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                worker.validate_policy(dict(policy(), **change))

    def test_conversion_checks_containment_and_preserves_declared_preparer(self):
        from src.fixed_lossless_state_v29 import from_factor_state as lossless
        exact, _, model, records = fixtures.ConversionTests().fixture()
        identity = ordered_preparer_binding()
        exact = replace(exact, preparer_sha256=identity,
                        anchors=tuple(replace(a, preparer_sha256=identity) for a in exact.anchors))
        converted, metrics = worker.convert_verified_state(lossless(exact), model, records)
        self.assertEqual(converted.bits, 48)
        self.assertEqual(converted.preparer_sha256, identity)
        self.assertTrue(metrics['every_enclosure_contains_source'])
        self.assertEqual(metrics['checked_enclosures'], 6)
        self.assertEqual(serialize(converted), serialize(from_factor_state(exact, bits=48, block_size=256)))
        with self.assertRaises(ValueError):
            worker.convert_verified_state(lossless(exact), model, records, codec_bits=40)

    def test_native_repair_matches_complete_fresh_model_and_canonical_state(self):
        import src.native_box_compressed_service_v31 as service
        decoder = OrderedFiniteDecoder(decoder_fixture(block_count=2), primitive_backend='mpfr_enclosure')
        target = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=4,
                                        bits=4, group_count=1, ridge=Fraction(1,10)))
        records = ({'id':'a','tokens':[0,1]}, {'id':'b','tokens':[2,1]})
        exact = OrderedFixedAnchorService(decoder, target, state_backend='factors')
        original = from_factor_state(exact.run(records).state, bits=48, block_size=256)
        expected = from_factor_state(exact.run(records[1:]).state, bits=48, block_size=256)
        repair = service.NativeBoxCompressedService(decoder,target,bits=48,certificate_backend='sparse',
                                                     max_neural_stage_record_pairs=0)
        with patch.object(service,'ordered_sequential_features',side_effect=AssertionError('unexpected replay')):
            result = repair.run(records[1:],method='repair',prior=original,deleted_ids=('a',))
        self.assertEqual(serialize(result.state), serialize(expected))
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'],0)
        self.assertEqual(result.diagnostics['certificate_accepted_stages'],len(target.stages))
        for row in result.diagnostics['stages']:
            self.assertEqual(row['certificate_route'],'sparse')


if __name__ == '__main__':
    unittest.main()
