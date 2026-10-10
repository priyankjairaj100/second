"""Synthetic exactness, admission, and access-contract tests for V43 dispatch."""
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction as Q
import itertools
import json
from pathlib import Path
import platform
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from research_v35.exact_gram import accumulate, dumps, loads
from research_v43.dispatcher import (DispatchRefused, RequestLedger, ResourcePolicy,
    StageSpec, assess_stage, solve_blocks, solve_gram)
from src.dyadic_row_quantizer import dyadic_row_scales
from src.token_box_certificate import TokenBoxUnresolved
from tests.test_direct_gram_v35 import oracle

native_test = unittest.skipUnless(sys.platform == 'linux' and platform.machine() in ('x86_64', 'aarch64'),
    'unchanged certified numerical backend requires Linux x86_64/aarch64')


def spec(weights, *, normalization=Q(256), ridge=Q(10)):
    stage = SimpleNamespace(stage_id='fixture.stage', weights=weights,
        scale_values=dyadic_row_scales(weights), ridge=ridge, normalization=normalization, bits=4)
    return StageSpec.from_stage(stage, target_sha256='1' * 64)


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.weights = np.array([[2.6, .21, -.11], [-.3, 1.7, .06]])
        self.features = np.array([[.9, -.3], [.4, .7], [-.5, .2]])
        self.spec = spec(self.weights)

    @native_test
    def test_both_point_routes_and_trusted_gram_equal_rational_oracle(self):
        expected = oracle(self.weights, self.features)
        for route in ('token', 'streamed'):
            blocks = [(self.features[:, i:i + 1], self.features[:, i:i + 1]) for i in range(2)]
            result = solve_blocks(self.spec, self.weights, blocks, total_tokens=2,
                block_tokens=1, max_blocks=2, route=route)
            np.testing.assert_array_equal(result.codes, expected)
            self.assertEqual(result.route, route)
            with self.assertRaises(ValueError):
                result.codes.flags.writeable = True
        gram = accumulate(self.features, source_id='fixture', normalization=256)
        result = solve_gram(self.spec, self.weights, gram)
        np.testing.assert_array_equal(result.codes, expected)
        self.assertEqual(result.route, 'direct_gram')

    @native_test
    def test_both_box_routes_certify_all_small_corners(self):
        weights = np.array([[2.6, .21]])
        lo = np.array([[.09, .21], [.19, .11]])
        hi = lo + .00001
        contract = spec(weights)
        for route in ('token', 'streamed'):
            result = solve_blocks(contract, weights, [(lo, hi)], total_tokens=2,
                block_tokens=2, kind='box', route=route)
            for selector in itertools.product((False, True), repeat=4):
                features = np.where(np.array(selector).reshape(2, 2), hi, lo)
                np.testing.assert_array_equal(result.codes, oracle(weights, features))

    @native_test
    def test_empty_and_midpoint_ties_use_original_grid(self):
        weights = np.array([[.5, 1.5, 7.], [-.5, -1.5, 7.]])
        contract = spec(weights, ridge=Q(1))
        for kind in ('point', 'box'):
            result = solve_blocks(contract, weights, [], total_tokens=0, kind=kind, route='streamed')
            np.testing.assert_array_equal(result.codes, [[0., 1., 7.], [-1., -2., 7.]])
        gram = accumulate(np.empty((3, 0)), source_id='empty', normalization=256)
        result = solve_gram(contract, weights, gram)
        np.testing.assert_array_equal(result.codes, [[0., 1., 7.], [-1., -2., 7.]])

    def test_uncertain_boxes_cannot_enter_point_solver(self):
        with self.assertRaisesRegex(ValueError, 'uncertain'):
            solve_blocks(self.spec, self.weights, [(self.features, self.features + .01)],
                         total_tokens=2, route='token')

    def test_bound_weights_scales_and_shapes_are_checked_before_features(self):
        def forbidden():
            raise AssertionError('features consumed before validating bound weights')
            yield
        for weights in (self.weights[:, :2], self.weights + .0001, self.weights.astype(np.float32)):
            with self.assertRaises(ValueError):
                solve_blocks(self.spec, weights, forbidden(), total_tokens=2)
        bad = replace(self.spec, scale_values=tuple(v * 2 for v in self.spec.scale_values))
        with self.assertRaisesRegex(ValueError, 'scales'):
            solve_blocks(bad, self.weights, forbidden(), total_tokens=2)
        with self.assertRaises(FrozenInstanceError):
            self.spec.width = 8

    def test_stream_extent_and_endpoint_errors_never_return_codes(self):
        x = self.features[:, :1]
        cases = ([(x, x)], [(x, x), (x, x), (x, x)],
                 [(x, x - .1), (x, x)], [(np.empty((3, 0)), np.empty((3, 0)))],
                 [(np.ones((2, 2)), np.ones((2, 2)))])
        # Both routes consume the same validated generator. The token adapter
        # fully assembles before invoking the Linux-only native backend.
        for route in ('token',):
            for blocks in cases:
                with self.subTest(route=route, length=len(blocks)), self.assertRaises(ValueError):
                    solve_blocks(self.spec, self.weights, blocks, total_tokens=2,
                                 block_tokens=1, max_blocks=2, route=route)
        with self.assertRaises(ValueError):
            solve_blocks(self.spec, self.weights, [(np.full((3, 2), np.nan), self.features)],
                         total_tokens=2, route='token')

    def test_gram_requires_trust_matching_width_and_original_normalization(self):
        gram = accumulate(self.features, source_id='fixture', normalization=256)
        with self.assertRaises(ValueError):
            solve_gram(self.spec, self.weights, loads(dumps(gram)))
        for wrong in (accumulate(self.features, source_id='fixture', normalization=2),
                      accumulate(self.features[:2], source_id='fixture', normalization=256)):
            with self.assertRaisesRegex(ValueError, 'normalization'):
                solve_gram(self.spec, self.weights, wrong)

    @native_test
    def test_normalization_is_not_replaced_by_retained_token_count(self):
        weights = np.array([[.21, 1.7, 2.6]])
        x = np.array([[1.], [1.], [0.]])
        outputs = []
        for normalization in (Q(1), Q(256)):
            result = solve_blocks(spec(weights, normalization=normalization, ridge=Q(1)), weights,
                [(x, x)], total_tokens=1, route='streamed')
            np.testing.assert_array_equal(result.codes, oracle(weights, x, ridge=Q(1), normalization=normalization))
            outputs.append(result.codes)
        self.assertFalse(np.array_equal(*outputs))

    def test_admission_failure_does_not_scan_weights_consume_blocks_or_compile(self):
        blocks = iter([(self.features, self.features)])
        tiny = ResourcePolicy(max_stage_work_units=1)
        with patch('research_v43.dispatcher._weights', side_effect=AssertionError('weight scan')):
            with self.assertRaises(DispatchRefused):
                solve_blocks(self.spec, self.weights, blocks, total_tokens=2, policy=tiny)
        self.assertEqual(next(blocks)[0].shape, (3, 2))

    def test_runtime_refusal_has_no_cross_route_retry(self):
        with patch('research_v43.dispatcher.quantize_adaptive_dyadic_rows',
                   side_effect=TokenBoxUnresolved('forced refusal')), \
             patch('research_v43.dispatcher.certify_streamed_primal_ball') as alternative:
            with self.assertRaises(DispatchRefused) as caught:
                solve_blocks(self.spec, self.weights, [(self.features, self.features)],
                             total_tokens=2, route='token')
            alternative.assert_not_called()
        self.assertIn('elapsed_ns', caught.exception.diagnostics)

    def test_complete_real_model_admission_for_128_and_768_tokens(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / 'campaigns/ci_scale_v39/attempts/prepare/outputs/base-target.json').read_bytes())
        contracts = [StageSpec.from_manifest(entry, target_sha256='1' * 64) for entry in manifest['stages']]
        self.assertEqual(len(contracts), 24)
        for tokens in (128, 768):
            for kind in ('point', 'box', 'gram'):
                ledger = RequestLedger()
                for contract in contracts:
                    result = assess_stage(contract, tokens, kind=kind,
                        block_tokens=128, max_blocks=tokens // 128, resident_bytes=2 * 2**30)
                    self.assertTrue(result['admitted'], (contract.stage_id, tokens, kind, result))
                    ledger.reserve(result)
                    self.assertLessEqual(result['explicit_array_bytes'], 8 * 2**30)
                    if kind != 'gram':
                        expected = 'token' if 4 * tokens <= contract.width else 'streamed'
                        self.assertEqual(result['selected_route'], expected)
                self.assertEqual(len(ledger.reservations), 24)

    def test_residency_and_cumulative_refusals_are_enforced(self):
        denied = assess_stage(self.spec, 2, resident_bytes=16 * 2**30)
        self.assertFalse(denied['admitted'])
        small = ResourcePolicy(max_request_work_units=1000)
        admission = assess_stage(self.spec, 2, policy=small, route='token')
        self.assertTrue(admission['admitted'])
        ledger = RequestLedger(small)
        while ledger.work_units + admission['work_units'] <= small.max_request_work_units:
            ledger.reserve(admission)
        previous = ledger.work_units
        with self.assertRaises(DispatchRefused):
            ledger.reserve(admission)
        self.assertEqual(ledger.work_units, previous)

    def test_fallback_work_is_reserved_in_point_and_box_routes(self):
        point = assess_stage(self.spec, 2, route='token')
        no_refine = assess_stage(self.spec, 2, route='token',
            policy=ResourcePolicy(max_point_refinement_coordinates=0))
        self.assertGreater(point['work_units'], no_refine['work_units'])
        box = assess_stage(self.spec, 2, kind='box', route='token')
        no_rounds = assess_stage(self.spec, 2, kind='box', route='token',
            policy=ResourcePolicy(max_box_rounds=0))
        self.assertGreater(box['work_units'], no_rounds['work_units'])
        self.assertTrue(box['candidates']['token']['complete_rows_and_bounded_fallback_reserved'])

    def test_invalid_policy_extent_and_route_are_rejected(self):
        for kwargs in ({'max_array_bytes': 17 * 2**30}, {'max_stage_work_units': True},
                       {'max_box_rounds': -1}):
            with self.assertRaises(ValueError):
                ResourcePolicy(**kwargs)
        for kwargs in ({'total_tokens': -1}, {'total_tokens': True},
                       {'total_tokens': 2, 'kind': 'gram', 'route': 'token'},
                       {'total_tokens': 2, 'route': 'direct_gram'},
                       {'total_tokens': 3, 'block_tokens': 1, 'max_blocks': 2}):
            with self.assertRaises(ValueError):
                assess_stage(self.spec, **kwargs)


if __name__ == '__main__':
    unittest.main()
