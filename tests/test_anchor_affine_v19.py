"""Finite affine correctness fixtures; no empirical datasets."""
from fractions import Fraction as Q
import unittest
import numpy as np
from src.anchor_affine import prepare_affine_anchor,prepare_affine_change,affine_error_bound,enclose_affine_output


def ordered(x,w,b):
    # Scalar target schedule, independent from array preparation.
    return np.array([[sum_row(row,weight,bias) for weight,bias in zip(w,b)] for row in x])

def sum_row(x,w,b):
    total=0.
    for a,c in zip(x,w):total=float(total+float(float(a)*float(c)))
    return float(total+float(b))


class AnchorAffineTests(unittest.TestCase):
    def test_zero_change_is_exact(self):
        x=np.array([[1.,2.,-3.],[4.,0.,1.]])
        w=np.array([[.1,.2,.3],[-.4,.5,.6]]);b=np.array([.1,-.3])
        anchor=prepare_affine_anchor(x,w,b)
        np.testing.assert_array_equal(anchor.output,ordered(x,w,b))
        error=affine_error_bound(anchor,prepare_affine_change(w,w),b,0)
        self.assertEqual(error,0)
        self.assertTrue(enclose_affine_output(anchor,error).singleton)
        with self.assertRaises(ValueError):anchor.output.flags.writeable=True

    def test_changed_inputs_and_weights(self):
        rng=np.random.default_rng(1901)
        for width in (1,3,17):
            for scale in (2.**-200,1.,2.**100):
                for repetition in range(5):
                    x=rng.integers(-10,11,(3,width)).astype(float)*scale/16
                    w=rng.integers(-10,11,(4,width)).astype(float)/16;b=rng.integers(-4,5,4).astype(float)/8
                    xp=x+rng.integers(-1,2,x.shape)*scale/1024
                    wp=w+rng.integers(-1,2,w.shape)/1024
                    anchor=prepare_affine_anchor(x,w,b)
                    bound=affine_error_bound(anchor,prepare_affine_change(w,wp),b,Q.from_float(scale)/1024)
                    actual=ordered(xp,wp,b)
                    for a,v in zip(anchor.output.flat,actual.flat):
                        self.assertLessEqual(abs(Q.from_float(float(v))-Q.from_float(float(a))),bound)
                    self.assertTrue(enclose_affine_output(anchor,bound).contains(actual))

    def test_subnormal_and_cancellation(self):
        for small in (2.**-1074,2.**-1022):
            x=np.array([[1.,-1.,small]]);w=np.array([[1.,1.,1.]])
            b=np.zeros(1);wp=w.copy();wp[0,1]=np.nextafter(1.,2.)
            anchor=prepare_affine_anchor(x,w,b)
            bound=affine_error_bound(anchor,prepare_affine_change(w,wp),b,0)
            self.assertTrue(enclose_affine_output(anchor,bound).contains(ordered(x,wp,b)))

    def test_matrix_change_bounds_exact_differences(self):
        w=np.array([[1.,-1e100,2.**-1074],[0.,1e100,-2.**-1074]])
        wp=np.nextafter(w,np.inf)
        change=prepare_affine_change(w,wp)
        for i,bound in enumerate(change.difference_column_maxima):
            for a,b in zip(w[:,i],wp[:,i]):
                self.assertLessEqual(abs(Q.from_float(float(a))-Q.from_float(float(b))),bound)

    def test_bindings_reject_wrong_matrix_and_bias(self):
        w=np.ones((1,2));b=np.zeros(1);anchor=prepare_affine_anchor(np.ones((1,2)),w,b)
        with self.assertRaises(ValueError):affine_error_bound(anchor,prepare_affine_change(w+1,w),b,0)
        with self.assertRaises(ValueError):affine_error_bound(anchor,prepare_affine_change(w,w),b+1,0)
        with self.assertRaises(ValueError):affine_error_bound(anchor,prepare_affine_change(w,w),b,-1)
        with self.assertRaises(ArithmeticError):enclose_affine_output(anchor,Q(10)**400)

if __name__=='__main__':unittest.main()
