"""Exact-oracle software fixtures for the bounded-block quantizer."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.block_speculative_dyadic_solver import block_speculative_quantize_dyadic_rows
from src.dyadic_row_quantizer import dyadic_row_scales, quantize_dyadic_rows
from src.exact_core import sequential_oracle
from src.low_rank_certified import LowRankUnresolved


class BlockSpeculativeTests(unittest.TestCase):
    def compare(self, weights, features, **options):
        options = dict(ridge=Q(1, 10), normalization=8,
                       max_exact_coordinates=weights.shape[1]) | options
        got = block_speculative_quantize_dyadic_rows(weights, features, **options)
        z = [[Q.from_float(float(value)) for value in row] for row in features]
        metric = [[(options['ridge'] if i == j else Q(0)) +
                   sum((a*b for a,b in zip(z[i], z[j])), Q(0))/options['normalization']
                   for j in range(len(z))] for i in range(len(z))]
        bits = options.get('bits', 4)
        half = 1 << (bits - 1)
        for row, scale in enumerate(dyadic_row_scales(
                weights, bits, options.get('significant_bits', 24))):
            grid = tuple(k * Q.from_float(scale) for k in range(-half, half))
            w = tuple(Q.from_float(float(value)) for value in weights[row])
            expected = sequential_oracle([w], metric, [grid]*len(w)).codes[0]
            self.assertEqual(tuple(Q.from_float(float(value)) for value in got.codes[row]), expected)
        self.assertEqual(got.interval_decisions + got.exact_decisions, weights.size)
        self.assertEqual(got.prefix_verified_decisions + got.fallback_decisions, weights.size)
        self.assertEqual(got.certified_row_blocks + got.fallback_row_blocks,
                         len(weights)*got.block_count)
        self.assertEqual(sum(got.prefix_length_histogram), len(weights)*got.block_count)
        self.assertEqual(sum(i*count for i,count in enumerate(got.prefix_length_histogram)),
                         got.prefix_verified_decisions)
        self.assertFalse(got.codes.flags.writeable)
        return got

    def test_independent_oracle_across_blocks_grids_and_batches(self):
        rng = np.random.default_rng(160710)
        for bits in (2,4,8):
            for width,rank in ((1,0),(3,2),(7,3)):
                weights = rng.integers(-32,33,(3,width)).astype(float)/32
                features = rng.integers(-6,7,(width,rank)).astype(float)/16
                for block in (1,2,4):
                    got = self.compare(weights,features,bits=bits,block_width=block,row_batch_size=2)
                    warm = self.compare(weights,features,bits=bits,block_width=block,
                                        candidate=got.codes,row_batch_size=4096)
                    np.testing.assert_array_equal(warm.codes,got.codes)

    def test_every_prefix_and_repair_then_later_acceptance(self):
        weights = np.tile(np.array([2.625,-3.,.2,-.2,.4,.7,-.4,.1]),(5,1))
        features = np.empty((8,0))
        reference = quantize_dyadic_rows(weights,features,ridge=Q(1,10),normalization=8)
        candidate = reference.codes.copy()
        for prefix in range(4):
            value = candidate[prefix,prefix]
            candidate[prefix,prefix] = 0. if value else -.375
        before = candidate.copy()
        got = self.compare(weights,features,candidate=candidate,block_width=4,row_batch_size=2)
        self.assertEqual(got.prefix_verified_decisions,30)
        self.assertEqual(got.fallback_decisions,10)
        self.assertEqual(got.certified_row_blocks,6)
        self.assertEqual(got.prefix_length_histogram,(1,1,1,1,6))
        np.testing.assert_array_equal(candidate,before)

    def fixture(self):
        weights = np.array([[2.625,-3.,.2,-.2,.4,.7,-.4],[-3.,2.625,.4,.2,-.2,.1,.6]])
        features = np.array([[1.,.25],[-.25,.5],[.125,-.25],[.5,.5],[.75,.2],[.3,-.2],[-.1,.4]])
        return weights,features

    def test_terminal_accumulator_passes_between_accepted_blocks(self):
        weights,features = self.fixture()
        reference = quantize_dyadic_rows(weights,features,ridge=Q(1,10),normalization=8)
        got = self.compare(weights,features,candidate=reference.codes,block_width=3)
        self.assertEqual(got.prefix_verified_decisions,weights.size)
        self.assertEqual(got.fallback_decisions,0)
        self.assertEqual(got.block_count,3)
        self.assertEqual(got.fallback_elapsed_ns,0)

    def test_later_exact_fallback_uses_corrected_global_prefix(self):
        weights,features = self.fixture()
        reference = quantize_dyadic_rows(weights,features,ridge=Q(1,10),normalization=8)
        candidate = reference.codes.copy()
        candidate[0,1] = 0.
        candidate[0,5] = 0. if candidate[0,5] else -.375
        candidate[1,4] = 0. if candidate[1,4] else -.375
        with patch('src.block_speculative_dyadic_solver._check_row_cells',
                   side_effect=lambda w,*_: (np.zeros(len(w),dtype=np.int64),np.zeros(len(w),dtype=bool))):
            got = self.compare(weights,features,candidate=candidate,block_width=3,
                               max_refinement_coordinates=0,row_batch_size=1)
        self.assertEqual(got.exact_coordinates,(1,2,4,5))
        self.assertEqual(got.exact_decisions,5)
        self.assertEqual(got.prefix_verified_decisions,9)
        np.testing.assert_array_equal(got.codes,reference.codes)

    def test_zero_sweeps_matches_direct_reference(self):
        weights,features = self.fixture()
        a = self.compare(weights,features,block_width=1,max_sweeps=0,row_batch_size=1)
        b = self.compare(weights,features,block_width=32,max_sweeps=0)
        reference = quantize_dyadic_rows(weights,features,ridge=Q(1,10),normalization=8)
        for got in (a,b):
            self.assertEqual(got.speculative_sweeps,0)
            self.assertEqual(got.prefix_verified_decisions,0)
            self.assertEqual(got.fallback_decisions,weights.size)
            np.testing.assert_array_equal(got.codes,reference.codes)

    def test_exact_coordinate_limits_are_global(self):
        weights,features = self.fixture()
        with patch('src.block_speculative_dyadic_solver._check_row_cells',
                   side_effect=lambda w,*_: (np.zeros(len(w),dtype=np.int64),np.zeros(len(w),dtype=bool))):
            got = self.compare(weights,features,block_width=2,max_sweeps=0,
                               max_refinement_coordinates=0,row_batch_size=1)
            self.assertEqual(got.exact_coordinates,tuple(range(weights.shape[1])))
            self.assertEqual(got.exact_decisions,weights.size)
            with patch('src.block_speculative_dyadic_solver._refined_coefficient',
                       side_effect=LowRankUnresolved('forced refinement abstention')) as refinement:
                refined = self.compare(weights,features,block_width=2,max_sweeps=0,
                                       max_refinement_coordinates=2,row_batch_size=1)
            self.assertEqual(refined.refined_coordinates,(0,1))
            self.assertEqual(refinement.call_count,2)
            with self.assertRaises(LowRankUnresolved):
                block_speculative_quantize_dyadic_rows(weights,features,ridge=Q(1,10),normalization=8,
                    block_width=2,max_sweeps=0,max_refinement_coordinates=0,max_exact_coordinates=2)
            with self.assertRaises(LowRankUnresolved):
                block_speculative_quantize_dyadic_rows(weights,features,ridge=Q(1,10),normalization=8,
                    block_width=2,max_sweeps=0,max_refinement_coordinates=0,max_exact_rank=0)

    def test_subnormal_ties_and_partial_final_block(self):
        tiny = 2.**-1074
        weights = np.array([[2.625,-3.,.1875,-.1875,.5625], [0.,tiny,-tiny,2*tiny,0.]])
        for block in (1,2,4,32):
            got = self.compare(weights,np.empty((5,0)),block_width=block)
            np.testing.assert_array_equal(got.codes[0],[2.625,-3.,0.,-.375,.375])
            np.testing.assert_array_equal(got.codes[1],[0.,0.,-2*tiny,2*tiny,0.])

    def test_multiple_sweeps_preserve_candidate_and_target(self):
        weights,features = self.fixture()
        candidate = np.zeros_like(weights)
        got = self.compare(weights,features,candidate=candidate,block_width=3,max_sweeps=3,row_batch_size=1)
        np.testing.assert_array_equal(candidate,0.)
        self.assertGreater(got.speculative_decision_checks,weights.size)

    def test_invalid_candidates_limits_and_overflow_fail_closed(self):
        weights,features = np.array([[.1,-.3]]),np.ones((2,1))
        for candidate in (np.ones((2,1)),np.full((1,2),np.nan),np.full((1,2),.1234567)):
            with self.assertRaises(ValueError):
                block_speculative_quantize_dyadic_rows(weights,features,candidate=candidate,ridge=1)
        for options in ({'block_width':0},{'block_width':True},{'row_batch_size':0},
                        {'max_sweeps':-1},{'max_exact_coordinates':True}):
            with self.assertRaises(ValueError):
                block_speculative_quantize_dyadic_rows(weights,features,ridge=1,**options)
        with self.assertRaises(LowRankUnresolved):
            block_speculative_quantize_dyadic_rows(weights,np.full((2,1),1e308),ridge=1)


if __name__=='__main__':
    unittest.main()
