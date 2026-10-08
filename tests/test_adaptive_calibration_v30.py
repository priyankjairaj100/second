"""Bounded dispatch and complete service fixtures, without model experiments."""
from dataclasses import replace
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.adaptive_calibration_v30 import (AdaptiveBudget, CalibrationWorkRefused,
    assess_routes, quantize_adaptive_dyadic_rows)
from src.adaptive_fixed_service_v30 import AdaptiveFixedAnchorService
from src.adaptive_lossless_service_v30 import AdaptiveLosslessService
from src.certified_transformer import CertifiedDecoder
from src.compact_service import model_digest
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_service import FixedAnchorService
from src.fixed_factor_state import serialize as factor_bytes
from src.fixed_lossless_service_v29 import FixedLosslessService
from src.fixed_lossless_state_v29 import serialize as lossless_bytes
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture

RECORDS = ({'id':'a','tokens':[0,1]}, {'id':'b','tokens':[2,1]}, {'id':'c','tokens':[0,2]})


class DispatchTests(unittest.TestCase):
    def test_route_choice_uses_actual_dimensions(self):
        b = AdaptiveBudget(max_workspace_bytes=2**30, max_work_units=10**10, max_refinement_coordinates=0)
        self.assertEqual(assess_routes(8,768,16,budget=b)['selected'],'token')
        self.assertEqual(assess_routes(8,768,1024,budget=b)['selected'],'primal')

    def test_huge_route_refused_without_numerical_construction(self):
        with patch('numpy.empty', side_effect=AssertionError('allocation')):
            report = assess_routes(2304,768,262144)
        self.assertIsNone(report['selected'])
        self.assertFalse(report['whole_process_memory_guaranteed'])

    def test_empty_features_still_charge_model_and_grid_work(self):
        report = assess_routes(8,768,0)
        self.assertGreaterEqual(report['routes']['token']['work_units'],8*768)

    def test_forced_refused_route_never_calls_solver(self):
        w=np.array([[1.,.2]]);x=np.array([[1.,0.],[0.,1.]])
        with patch('src.fast_token_quantizer_v30.native_fast_quantize_dyadic_rows',side_effect=AssertionError('solver')):
            with self.assertRaises(CalibrationWorkRefused):
                quantize_adaptive_dyadic_rows(w,x,ridge=1,route='token',budget=AdaptiveBudget(max_work_units=1))

    def test_both_routes_equal_on_same_exact_input(self):
        w=np.array([[1.,.19,-.32],[.27,-.17,1.]])
        x=np.array([[1.,.5,0.,.25],[.5,1.,-.25,0.],[0.,.5,1.,-.5]])
        a=quantize_adaptive_dyadic_rows(w,x,ridge=Q(1,10),route='token')
        b=quantize_adaptive_dyadic_rows(w,x,ridge=Q(1,10),route='primal')
        np.testing.assert_array_equal(a.codes,b.codes)

    def test_unaligned_arrays_are_copied_before_native_call(self):
        raw=bytearray(8*2+1)
        w=np.ndarray((1,2),dtype=np.float64,buffer=raw,offset=1);w[:]=[[1.,.2]]
        x=np.array([[1.,0.],[0.,1.]])
        from src import fast_token_quantizer_v30 as native
        actual=native.native_fast_quantize_dyadic_rows
        def checked(weights,features,*args,**kwargs):
            self.assertTrue(weights.flags.aligned and features.flags.aligned)
            return actual(weights,features,*args,**kwargs)
        with patch.object(native,'native_fast_quantize_dyadic_rows',side_effect=checked):
            quantize_adaptive_dyadic_rows(w,x,ridge=1,route='token')

    def test_rejects_bad_budget_and_candidates(self):
        for bad in (True,0,-1):
            with self.assertRaises(ValueError):AdaptiveBudget(max_work_units=bad)
        with self.assertRaises(ValueError):
            quantize_adaptive_dyadic_rows(np.ones((1,2)),np.ones((2,2)),ridge=1,candidate=np.zeros((1,2)))


class AdaptiveServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder=CertifiedDecoder(decoder_fixture(block_count=2),primitive_backend='mpfr_enclosure')
        cls.base=build_dyadic_row_target(cls.decoder,TargetRecipe(original_token_count=6,bits=4,group_count=1,ridge=Q(1,10)))
        cls.old=FixedAnchorService(cls.decoder,cls.base,state_backend='factors')
        cls.expected=cls.old.run(RECORDS[1:])

    def test_point_routes_match_complete_original_service_and_state(self):
        for route in ('auto','token','primal'):
            service=AdaptiveFixedAnchorService(self.decoder,self.base,solver_backend=route)
            answer=service.run(RECORDS[1:])
            self.assertEqual(factor_bytes(answer.state),factor_bytes(self.expected.state))
            self.assertEqual(service.target.digest,self.old.target.digest)

    def test_repair_histories_preserve_canonical_exact_state(self):
        service=AdaptiveFixedAnchorService(self.decoder,self.base)
        prior=service.run(RECORDS)
        repaired=service.run(RECORDS[1:],method='repair',prior=prior.state,deleted_ids=('a',))
        self.assertEqual(factor_bytes(repaired.state),factor_bytes(self.expected.state))
        seq=service.run(RECORDS[2:],method='repair',prior=repaired.state,deleted_ids=('b',))
        combined=service.run(RECORDS[2:],method='repair',prior=prior.state,deleted_ids=('a','b'))
        self.assertEqual(factor_bytes(seq.state),factor_bytes(combined.state))
        cold=service.run(RECORDS[1:],method='model_only_fresh')
        self.assertIsNone(cold.state)
        self.assertEqual(model_digest(cold.stages),model_digest(repaired.stages))

    def test_lossless_repair_matches_old_storage_and_zero_replay(self):
        old=FixedLosslessService(self.decoder,self.base)
        prior=old.run(RECORDS)
        expected=old.run(RECORDS[1:])
        service=AdaptiveLosslessService(self.decoder,self.base)
        with patch('src.adaptive_fixed_service_v30.sequential_features',side_effect=AssertionError('replay')):
            repaired=service.repair(prior.state,('a',))
        self.assertEqual(lossless_bytes(repaired.state),lossless_bytes(expected.state))
        self.assertEqual(repaired.diagnostics['neural_stage_record_pairs'],0)
        stale=replace(prior.state,decoder_sha256='0'*64)
        with self.assertRaises(ValueError):service.repair(stale,('a','b','c'))


if __name__=='__main__':unittest.main()
