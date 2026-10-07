"""Refinement correctness and bound-contract fixtures."""
import unittest
import numpy as np
from src.box_refinement import refine_dyadic_boxes
from src.token_box_certificate import TokenBoxUnresolved
from tests.test_dyadic_box_v18 import oracle


class RefinementTests(unittest.TestCase):
    def setUp(self):
        self.w=np.array([[2.6,.21,-.11],[-.3,1.7,.06]])
        self.z=np.array([[.9,-.3],[.4,.7],[-.5,.2]])
        self.boxes=[(rid,np.full((3,1),-100.),np.full((3,1),100.)) for rid in ('z','a')]
        self.exact={'a':self.z[:,:1].copy(),'z':self.z[:,1:].copy()}

    def test_order_and_final_oracle(self):
        calls=[]
        def evaluate(rid):calls.append(rid);return self.exact[rid]
        got=refine_dyadic_boxes(self.w,self.boxes,evaluate,max_records=2,ridge=10,normalization=3)
        self.assertEqual(calls,['a','z'])
        self.assertEqual(got.evaluated_record_ids,('a','z'))
        np.testing.assert_array_equal(got.certificate.codes,oracle(self.w,self.z))
        self.assertTrue(np.all(self.boxes[0][1]==-100.))

    def test_zero_budget_stops_without_evaluation(self):
        def forbidden(rid):raise AssertionError('budget exceeded')
        with self.assertRaises(TokenBoxUnresolved):
            refine_dyadic_boxes(self.w,self.boxes,forbidden,max_records=0,ridge=10)

    def test_contradictory_provider_aborts(self):
        with self.assertRaisesRegex(ValueError,'contradict'):
            refine_dyadic_boxes(self.w,self.boxes,lambda rid:np.full((3,1),101.),max_records=2,ridge=10)

    def test_singletons_avoid_callback(self):
        def forbidden(rid):raise AssertionError('unnecessary source access')
        boxes=[(k,v,v) for k,v in self.exact.items()]
        got=refine_dyadic_boxes(self.w,boxes,forbidden,max_records=0,ridge=10,normalization=3)
        self.assertEqual(got.evaluated_record_ids,())
        np.testing.assert_array_equal(got.certificate.codes,oracle(self.w,self.z))

    def test_duplicate_ids_and_empty_inputs(self):
        for boxes in ([],[self.boxes[0],self.boxes[0]]):
            with self.assertRaises(ValueError):
                refine_dyadic_boxes(self.w,boxes,lambda rid:None,max_records=2,ridge=10)

if __name__=='__main__':unittest.main()
