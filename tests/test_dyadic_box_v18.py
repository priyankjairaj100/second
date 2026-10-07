"""Small correctness fixtures, not empirical datasets."""
import itertools
from fractions import Fraction as Q
import unittest
from unittest.mock import patch
import numpy as np
from src.dyadic_box_certificate import certify_dyadic_box
from src.dyadic_row_quantizer import dyadic_row_scales
from src.exact_core import sequential_oracle
from src.token_box_certificate import TokenBoxUnresolved


def oracle(w, z, ridge=Q(10), norm=Q(3)):
    zz=[[Q.from_float(float(x)) for x in row] for row in z]
    h=[[sum((x*y for x,y in zip(a,b)), Q(0))/norm+(ridge if i==j else 0)
        for j,b in enumerate(zz)] for i,a in enumerate(zz)]
    rows=[]
    for row,scale in zip(w,dyadic_row_scales(w)):
        grid=tuple(k*Q.from_float(scale) for k in range(-8,8))
        rows.append(sequential_oracle([[Q.from_float(float(x)) for x in row]],h,[grid]*w.shape[1]).codes[0])
    return np.array(rows,dtype=np.float64)


class DyadicBoxTests(unittest.TestCase):
    def setUp(self):
        self.w=np.array([[2.6,.21,-.11],[-.3,1.7,.06]])
        self.z=np.array([[.9,-.3],[.4,.7],[-.5,.2]])

    def test_singleton_matches_independent_dense_oracle(self):
        for z in (self.z,np.empty((3,0))):
            got=certify_dyadic_box(self.w,z,z,ridge=10,normalization=3)
            np.testing.assert_array_equal(got.codes,oracle(self.w,z))
            self.assertEqual(got.uncertain_features,0)

    def test_nonzero_box_all_vertices_and_interiors(self):
        lo=self.z;hi=lo+1e-8
        with patch('src.dyadic_box_certificate.quantize_dyadic_rows',side_effect=AssertionError('point fallback')):
            got=certify_dyadic_box(self.w,lo,hi,ridge=10,normalization=3)
        for mask in itertools.product((False,True),repeat=lo.size):
            z=np.where(np.array(mask).reshape(lo.shape),hi,lo)
            np.testing.assert_array_equal(got.codes,oracle(self.w,z))
        for alpha in (.125,.5,.875):
            np.testing.assert_array_equal(got.codes,oracle(self.w,lo+alpha*(hi-lo)))
        self.assertEqual(got.point_exact_decisions,0)
        self.assertEqual(got.uncertain_features,6)
        with self.assertRaises(ValueError):got.codes.flags.writeable=True

    def test_candidate_check_and_wrong_scales(self):
        got=certify_dyadic_box(self.w,self.z,self.z,ridge=10,normalization=3)
        matched=certify_dyadic_box(self.w,self.z,self.z,ridge=10,normalization=3,candidate_codes=got.codes)
        self.assertTrue(matched.candidate_checked)
        with self.assertRaises(TokenBoxUnresolved):
            certify_dyadic_box(self.w,self.z,self.z,ridge=10,candidate_codes=np.zeros_like(self.w))
        with self.assertRaises(ValueError):
            certify_dyadic_box(self.w,self.z,self.z,[1.,1.],ridge=10)

    def test_limits_and_invalid_bounds(self):
        for value in (True,-1,1.5):
            with self.assertRaises(ValueError):
                certify_dyadic_box(self.w,self.z,self.z,ridge=10,max_exact_coordinates=value)
        with self.assertRaises(ValueError):certify_dyadic_box(self.w,self.z+1,self.z,ridge=10)
        with self.assertRaises(ValueError):certify_dyadic_box(self.w,self.z,self.z,ridge=0)
        with self.assertRaises(TokenBoxUnresolved):
            certify_dyadic_box(self.w,np.full_like(self.z,-1e100),np.full_like(self.z,1e100),ridge=1)

    def test_runtime_guard(self):
        with patch('src.dyadic_box_certificate._check_runtime',side_effect=RuntimeError('unsupported')):
            with self.assertRaises(RuntimeError):certify_dyadic_box(self.w,self.z,self.z,ridge=1)

if __name__=='__main__':unittest.main()
