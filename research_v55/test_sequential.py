"""Miniature exact sequential parity and refusal fixtures; no empirical model."""
from dataclasses import replace
import unittest
from unittest.mock import patch
import numpy as np
from research_v55 import sequential
from research_v43.dispatcher import ResourcePolicy
from research_v50.neighbors import enabled
from scripts.run_ordered_sequential_v30 import calibrate_sequential_ordered
from src.adaptive_calibration_v30 import AdaptiveBudget,quantize_adaptive_dyadic_rows
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_target import build_fixed_anchor_target
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.run_store import digest
from src.target_manifest import TargetRecipe
from tests.test_checkpoint_adapter import checkpoint_fixture
from tests.test_transformer_backend import decoder_fixture

RECORDS=[dict(id='a',tokens=[0,1]),dict(id='b',tokens=[2,1])]


def context(base=None):
    decoder=OrderedFiniteDecoder(base or decoder_fixture(),primitive_backend='mpfr_enclosure')
    return decoder,build_dyadic_row_target(decoder,TargetRecipe(original_token_count=4,group_count=1))


class SequentialTests(unittest.TestCase):
    def test_feature_words_and_all_model_codes_match_original_constructor(self):
        bases=[decoder_fixture(block_count=2,head_count=2)]
        bases.extend(checkpoint_fixture(a)[2] for a in ('gelu','gelu_new'))
        for base in bases:
            with self.subTest(activation=base.config.activation):
                decoder,target=context(base);old_features=[];new_features=[]
                solve=sequential.dispatch.solve_blocks
                def old_capture(weights,features,scales,**kw):
                    old_features.append(features.copy())
                    return quantize_adaptive_dyadic_rows(weights,features,scales,**kw)
                def new_capture(spec,weights,blocks,**kw):
                    new_features.append(np.concatenate([lo for lo,hi in blocks],axis=1))
                    return solve(spec,weights,blocks,**kw)
                with enabled(),patch('src.adaptive_calibration_v30.quantize_adaptive_dyadic_rows',side_effect=old_capture):
                    old,om=calibrate_sequential_ordered(decoder,target,RECORDS,
                        budget=AdaptiveBudget(),route='auto',max_point_work_units=10**9)
                with enabled(),patch.object(sequential.dispatch,'solve_blocks',side_effect=new_capture):
                    new,nm=sequential.calibrate(decoder,target,RECORDS)
                self.assertEqual(old,new)
                self.assertEqual(len(old_features),len(new_features))
                for a,b in zip(old_features,new_features):np.testing.assert_array_equal(a.view(np.uint64),b.view(np.uint64))
                self.assertEqual(om['neural_stage_record_pairs'],nm['neural_stage_record_pairs'])
                for index,row in enumerate(nm['stages']):
                    self.assertEqual(row['installed_parent_packed_sha256'],digest(new[index-1].packed_indices) if index else None)

    def test_wrong_decoder_fixed_target_and_empty_records_refuse(self):
        decoder,target=context()
        for d,t,r in ((decoder.base,target,RECORDS),(decoder,build_fixed_anchor_target(decoder,target),RECORDS),(decoder,target,[])):
            with self.assertRaises(ValueError):sequential.calibrate(d,t,r)

    def test_stage_and_request_admission_precede_feature_execution(self):
        decoder,target=context()
        policies=(replace(ResourcePolicy(),max_stage_work_units=1),replace(ResourcePolicy(),max_request_work_units=1))
        for policy in policies:
            with patch.object(sequential,'ordered_sequential_features',side_effect=AssertionError('no features')) as spy:
                with self.assertRaises(ValueError):sequential.calibrate(decoder,target,RECORDS,policy=policy)
                spy.assert_not_called()

    def test_solver_failure_keeps_completed_prefix_and_closes_every_stream(self):
        decoder,target=context();solve=sequential.dispatch.solve_blocks
        stream=sequential.ordered_sequential_features;calls=[];closed=[]
        def tracked(d,t):
            try:yield from stream(d,t)
            finally:closed.append(tuple(t))
        def stop(*a,**kw):
            calls.append(1)
            if len(calls)==2:raise ArithmeticError('fixture refusal')
            return solve(*a,**kw)
        with enabled(),patch.object(sequential,'ordered_sequential_features',side_effect=tracked),patch.object(sequential.dispatch,'solve_blocks',side_effect=stop):
            with self.assertRaises(ArithmeticError) as caught:sequential.calibrate(decoder,target,RECORDS)
        self.assertIs(caught.exception.diagnostics,caught.exception.service_diagnostics)
        self.assertEqual(caught.exception.diagnostics['completed_stages'],1)
        self.assertEqual(len(caught.exception.diagnostics['stages']),1)
        self.assertCountEqual(closed,[tuple(r['tokens']) for r in RECORDS])

    def test_retained_membership_canonical_order_and_duplicate_rejection(self):
        decoder,target=context()
        with enabled():
            a,am=sequential.calibrate(decoder,target,RECORDS)
            b,bm=sequential.calibrate(decoder,target,list(reversed(RECORDS)))
            c,cm=sequential.calibrate(decoder,target,RECORDS[1:])
        self.assertEqual(a,b)
        self.assertEqual(cm['retained_tokens'],2)
        self.assertEqual(cm['neural_stage_record_pairs'],len(target.stages))
        with patch.object(sequential,'ordered_sequential_features',side_effect=AssertionError('no features')):
            with self.assertRaises(ValueError):sequential.calibrate(decoder,target,[RECORDS[0],RECORDS[0]])

    def test_wrong_stream_stage_refuses_and_closes(self):
        decoder,target=context();closed=[]
        def wrong(d,t):
            try:yield 'incorrect-stage',np.zeros((len(t),target.stages[0].width))
            finally:closed.append(True)
        with patch.object(sequential,'ordered_sequential_features',side_effect=wrong):
            with self.assertRaises(ValueError) as caught:sequential.calibrate(decoder,target,RECORDS)
        self.assertEqual(caught.exception.diagnostics['completed_stages'],0)
        self.assertEqual(closed,[True])


if __name__=='__main__':unittest.main()
