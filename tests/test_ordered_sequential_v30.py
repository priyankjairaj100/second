"""Ordered sequential worker contracts, using only miniature software fixtures."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scripts import run_ordered_sequential_v30 as ordered
from scripts import run_sequential_comparison_v30 as scalar
from src.adaptive_calibration_v30 import AdaptiveBudget, CalibrationWorkRefused, quantize_adaptive_dyadic_rows
from src.certified_transformer import CertifiedDecoder
from src.compact_state import CompactState, serialize
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_target import build_fixed_anchor_target
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.run_store import canonical_json, digest, strict_json
from src.target_manifest import TargetRecipe
from tests.test_checkpoint_adapter import checkpoint_fixture
from tests.test_sequential_comparison_v30 import RECORDS, SequentialWorkerIntegrationTests
from tests.test_transformer_backend import decoder_fixture


class OrderedSequentialTests(unittest.TestCase):
    def run_fixture(self, module, decoder, target, records):
        seen = []
        def capture(weights, features, scales, **options):
            seen.append(features.copy())
            return quantize_adaptive_dyadic_rows(weights, features, scales, **options)
        method = (module.calibrate_sequential_ordered if module is ordered else module.calibrate_sequential)
        with patch('src.adaptive_calibration_v30.quantize_adaptive_dyadic_rows', side_effect=capture):
            stages, metrics = method(decoder, target, records, budget=AdaptiveBudget(),
                route='auto', max_point_work_units=10**9)
        return serialize(CompactState(target.digest, stages, ())), seen, metrics

    def test_feature_bits_and_complete_models_equal_scalar_worker(self):
        bases = [decoder_fixture(block_count=2, head_count=2)]
        bases.extend(checkpoint_fixture(activation)[2] for activation in ('gelu', 'gelu_new'))
        for base in bases:
            old = CertifiedDecoder(base, primitive_backend='mpfr_enclosure')
            new = OrderedFiniteDecoder(base, primitive_backend='mpfr_enclosure')
            a = build_dyadic_row_target(old, TargetRecipe(original_token_count=4, group_count=1))
            b = build_dyadic_row_target(new, TargetRecipe(original_token_count=4, group_count=1))
            self.assertEqual(a.digest, b.digest)
            self.assertEqual(build_fixed_anchor_target(old, a).digest, build_fixed_anchor_target(new, b).digest)
            old_model, old_features, old_metrics = self.run_fixture(scalar, old, a, RECORDS)
            new_model, new_features, new_metrics = self.run_fixture(ordered, new, b, RECORDS)
            self.assertEqual(new_model, old_model)
            self.assertEqual(len(old_features), len(base.stage_ids))
            for left, right in zip(old_features, new_features):
                np.testing.assert_array_equal(left.view(np.uint64), right.view(np.uint64))
            self.assertEqual(old_metrics['neural_stage_record_pairs'], new_metrics['neural_stage_record_pairs'])
            self.assertEqual(new_metrics['implementation_manifest_sha256'], digest(canonical_json(new.implementation_manifest)))

    def test_empty_retained_model_equals_scalar(self):
        base = decoder_fixture()
        old = CertifiedDecoder(base, primitive_backend='mpfr_enclosure')
        new = OrderedFiniteDecoder(base, primitive_backend='mpfr_enclosure')
        target = build_dyadic_row_target(new, TargetRecipe(original_token_count=4, group_count=1))
        original = self.run_fixture(scalar, old, target, [])
        changed = self.run_fixture(ordered, new, target, [])
        self.assertEqual(original[0], changed[0])
        self.assertEqual(changed[2]['neural_stage_record_pairs'], 0)

    def test_wrong_decoder_and_fixed_target_are_rejected(self):
        base = decoder_fixture()
        new = OrderedFiniteDecoder(base, primitive_backend='mpfr_enclosure')
        target = build_dyadic_row_target(new, TargetRecipe(original_token_count=4, group_count=1))
        for decoder, candidate in ((CertifiedDecoder(base), target), (new, build_fixed_anchor_target(new, target))):
            with self.assertRaises(ValueError):
                self.run_fixture(ordered, decoder, candidate, RECORDS)

    def test_budget_refusal_precedes_features(self):
        new = OrderedFiniteDecoder(decoder_fixture(), primitive_backend='mpfr_enclosure')
        target = build_dyadic_row_target(new, TargetRecipe(original_token_count=4, group_count=1))
        with patch('src.ordered_finite_decoder_v30.ordered_sequential_features', side_effect=AssertionError('no features')):
            with self.assertRaises(CalibrationWorkRefused):
                ordered.calibrate_sequential_ordered(new, target, RECORDS, budget=AdaptiveBudget(),
                    route='auto', max_point_work_units=1)

    def test_failure_preserves_both_diagnostic_fields(self):
        new = OrderedFiniteDecoder(decoder_fixture(), primitive_backend='mpfr_enclosure')
        target = build_dyadic_row_target(new, TargetRecipe(original_token_count=4, group_count=1))
        calls = []
        def stop(weights, features, scales, **options):
            calls.append(1)
            if len(calls) == 2:
                raise ArithmeticError('fixture refusal')
            return quantize_adaptive_dyadic_rows(weights, features, scales, **options)
        with patch('src.adaptive_calibration_v30.quantize_adaptive_dyadic_rows', side_effect=stop):
            with self.assertRaises(ArithmeticError) as caught:
                ordered.calibrate_sequential_ordered(new, target, RECORDS, budget=AdaptiveBudget(),
                    route='auto', max_point_work_units=10**9)
        self.assertIs(caught.exception.diagnostics, caught.exception.service_diagnostics)
        self.assertEqual(caught.exception.diagnostics['completed_stages'], 1)

    def test_complete_worker_emits_explicit_artifacts_and_unchanged_model(self):
        helper = SequentialWorkerIntegrationTests()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan, loaded = helper.setup_plan(root)
            path = root/'plan.json'; path.write_bytes(canonical_json(plan))
            with patch.object(ordered.sys, 'argv', ['run_ordered_sequential_v30.py', str(path)]), \
                    patch.object(ordered, 'source_hashes', return_value=plan['source_sha256']), \
                    patch.object(ordered, 'verify_command_admission') as admission, \
                    patch('src.checkpoint_adapter.load_gpt2_checkpoint', return_value=loaded), \
                    contextlib.redirect_stdout(io.StringIO()):
                ordered.main()
            admission.assert_called_once()
            output = Path(plan['output'])
            raw = (output/'completion.json').read_bytes()
            self.assertEqual(raw, (output/'progress.json').read_bytes())
            result = strict_json(raw)
            self.assertEqual(result['stage_count'], 24)
            self.assertTrue(result['target_identity_matches_scalar_reference'])
            self.assertFalse(result['complete_state'])
            self.assertEqual(set(result['artifacts']), {'model', 'implementation'})
            for entry in result['artifacts'].values():
                blob = (output/entry['file']).read_bytes()
                self.assertEqual(len(blob), entry['bytes'])
                self.assertEqual(digest(blob), entry['sha256'])
            old = CertifiedDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
            target = build_dyadic_row_target(old, TargetRecipe(original_token_count=4, group_count=1))
            expected, _, _ = self.run_fixture(scalar, old, target, RECORDS[1:])
            self.assertEqual((output/'model.bin').read_bytes(), expected)


if __name__ == '__main__':
    unittest.main()
