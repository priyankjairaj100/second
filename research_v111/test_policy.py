"""Route semantics, failure isolation and actual native rational correctness."""
from dataclasses import replace
import copy,sys,unittest
from unittest.mock import patch
import numpy as np
from research_v43 import dispatcher as d
from research_v43.test_dispatcher import spec
from research_v111 import policy
from tests.test_direct_gram_v35 import oracle
from src.token_box_certificate import TokenBoxUnresolved

class Policy(unittest.TestCase):
    def setUp(self):
        self.w=np.array([[2.6,.21,-.11],[-.3,1.7,.06]])
        self.x=np.array([[.9,-.3],[.4,.7],[-.5,.2]])
        self.spec=spec(self.w)
    def test_point_admission_changes_from_streamed_to_token_before_solving(self):
        self.assertEqual(d.assess_stage(self.spec,2)['selected_route'],'streamed')
        with policy.point_token() as meta:
            actual=d.assess_stage(self.spec,2)
            self.assertEqual(actual['selected_route'],'token')
            self.assertEqual(actual['selection_policy'],policy.POLICY)
        policy.verify_metadata(meta)
        self.assertEqual(d.assess_stage(self.spec,2)['selected_route'],'streamed')
    def test_box_and_gram_routes_unchanged(self):
        for kind in ('box','gram'):
            before=d.assess_stage(self.spec,2,kind=kind)
            with policy.point_token():actual=d.assess_stage(self.spec,2,kind=kind)
            for k in before:self.assertEqual(before[k],actual[k])
    def test_box_cumulative_fallback_limit_is_enforced(self):
        with policy.point_token():r=d.assess_stage(self.spec,2,kind='box')
        cap=r['box_and_point_fallback_work_units']-1
        with policy.point_token(),self.assertRaises(d.DispatchRefused):
            d.assess_stage(self.spec,2,kind='box',policy=d.ResourcePolicy(max_stage_work_units=cap))
    def test_no_runtime_cross_route_retry(self):
        with policy.point_token(),patch.object(d,'quantize_adaptive_dyadic_rows',side_effect=TokenBoxUnresolved('fixture')),patch.object(d,'certify_streamed_primal_ball') as stream:
            with self.assertRaises(d.DispatchRefused):d.solve_blocks(self.spec,self.w,[(self.x,self.x)],total_tokens=2)
            stream.assert_not_called()
    def test_explicit_streamed_point_rejected(self):
        with policy.point_token(),self.assertRaises(ValueError):d.assess_stage(self.spec,2,route='streamed')
    def test_policy_restores_after_exception_and_rejects_nesting(self):
        original=d.assess_stage
        with self.assertRaises(RuntimeError),policy.point_token():
            with policy.point_token():pass
        self.assertIs(d.assess_stage,original)
    def test_metadata_requires_actual_closed_bound_scope(self):
        with policy.point_token() as meta:d.assess_stage(self.spec,2)
        for change in ({'closed':False},{'adapter_sha256':'0'*64},{'point_assessments':0},{'point_route':'streamed'}):
            with self.assertRaises(ValueError):policy.verify_metadata(dict(meta,**change))
    def test_token_denial_never_substitutes_streamed(self):
        original=d.assess_stage
        r=original(self.spec,2,route='token');limit=r['explicit_array_bytes']-1
        with policy.point_token():
            result=d.assess_stage(self.spec,2,policy=d.ResourcePolicy(max_array_bytes=limit))
        self.assertFalse(result['admitted']);self.assertIsNone(result['selected_route'])
    def test_recorded_point_routes_cannot_hide_streamed_execution(self):
        row=dict(stage_id='one',route='token',admission=dict(kind='point',selected_route='token',selection_policy=policy.POLICY))
        q=dict(request=dict(timing=dict(stages=[row])))
        self.assertTrue(policy.verify_routes(q,1))
        for field,value in [('route','streamed'),('stage_id','changed')]:
            if field=='route':
                bad=copy.deepcopy(q);bad['request']['timing']['stages'][0][field]=value
                with self.assertRaises(ValueError):policy.verify_routes(bad,1)
        with self.assertRaises(ValueError):policy.verify_routes(q,2)
        oracle=dict(steps=[dict(common_timing=dict(stages=[row]))])
        self.assertTrue(policy.verify_routes(oracle,1))
        oracle['steps'][0]['common_timing']['stages'][0]['admission']['kind']='box'
        with self.assertRaises(ValueError):policy.verify_routes(oracle,1)

class NativePolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform!='linux':raise RuntimeError('Pinned Linux native policy check required')
    def test_actual_dispatch_matches_rational_oracle_for_both_cells(self):
        w=np.array([[2.6,.21,-.11],[-.3,1.7,.06]]);x=np.array([[.9,-.3],[.4,.7],[-.5,.2]])
        for cell in ('reference_modern','optimized_modern','reference_compressed','optimized_compressed'):
            with policy.execution(cell) as meta:
                answer=d.solve_blocks(spec(w),w,[(x,x)],total_tokens=2,block_tokens=2,max_blocks=1)
                self.assertEqual(answer.route,'token');np.testing.assert_array_equal(answer.codes,oracle(w,x))
            policy.verify_metadata(meta['point_route_policy'])
            self.assertTrue(meta['closed'])
