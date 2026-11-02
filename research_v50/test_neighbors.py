import ctypes
from fractions import Fraction
import platform
import sys
import unittest
import numpy as np
from research_v50.neighbors import prepare,enabled
from research_v35.direct_gram import _coefficient_bounds
from research_v40.streamed_primal_ball import certify_streamed_primal_ball
from src import primal_certificate_v30 as primal
from tests.test_direct_gram_v35 import oracle


@unittest.skipUnless(sys.platform=='linux' and platform.machine() in ('x86_64','aarch64'),'Pinned Linux runtime required')
class NeighborTests(unittest.TestCase):
    def test_reference_values_and_exception_flags(self):
        # Exhaust exponent transitions and adjacent words; add a fixed raw-bit
        # sample spanning signs, mantissas, normals, subnormals, infinities/NaNs.
        words=set()
        for sign in (0,1<<63):
            for exponent in range(2048):
                center=sign|(exponent<<52)
                for delta in (-1,0,1,2):
                    if 0<=center+delta<1<<64:words.add(center+delta)
        words.update([0x7fefffffffffffff,0xffefffffffffffff,0x7ff8000000000001,0xfff8000000000001])
        rng=np.random.Generator(np.random.PCG64(20261012))
        random=rng.bit_generator.random_raw(1_000_000)
        values=np.concatenate((np.array(sorted(words),dtype=np.uint64),random));failure=np.zeros(4,dtype=np.uint64)
        native,_,_=prepare();ptr=ctypes.POINTER(ctypes.c_uint64)
        self.assertEqual(native.v50_compare(len(values),values.ctypes.data_as(ptr),failure.ctypes.data_as(ptr)),0,
            f'neighbor or exception mismatch: {failure.tolist()}')
    def test_point_and_box_gram_and_coefficient_words(self):
        primal.prepare_primal_native();rng=np.random.Generator(np.random.PCG64(5011))
        for width,tokens in ((3,2),(16,12),(47,24)):
            x=rng.integers(-16,17,size=(width,tokens)).astype(np.float64)/16
            for radius in (0.,2**-30):
                low,high=x-radius,x+radius
                g=primal._gram_bounds(low,high,arithmetic_backend='native')
                c=_coefficient_bounds(*g,Fraction(5),arithmetic_backend='native')
                original=primal._NATIVE
                with enabled():
                    g2=primal._gram_bounds(low,high,arithmetic_backend='native')
                    c2=_coefficient_bounds(*g2,Fraction(5),arithmetic_backend='native')
                self.assertIs(primal._NATIVE,original)
                for a,b in zip((*g,c.centers,c.radii),(*g2,c2.centers,c2.radii)):self.assertEqual(a.tobytes(),b.tobytes())
                self.assertEqual(c.max_residual_squared,c2.max_residual_squared)
                self.assertEqual(c.max_solution_error_squared,c2.max_solution_error_squared)
    def test_complete_codes_against_exact_rational_oracle(self):
        weights=np.array([[2.6,.21,-.11],[-.3,1.7,.06]])
        features=np.array([[.9,-.3],[.4,.7],[-.5,.2]])
        with enabled():
            result=certify_streamed_primal_ball(weights,[(features,features)],total_tokens=2,block_tokens=2,
                max_blocks=1,ridge=Fraction(10),normalization=256)
        np.testing.assert_array_equal(result.codes,oracle(weights,features))
    def test_restore_on_failure_and_refuse_nested_selection(self):
        primal.prepare_primal_native();saved=primal._NATIVE
        with self.assertRaisesRegex(RuntimeError,'deliberate'):
            with enabled():raise RuntimeError('deliberate')
        self.assertIs(primal._NATIVE,saved)
        with enabled():
            with self.assertRaisesRegex(RuntimeError,'Dedicated'):
                with enabled():pass


if __name__=='__main__':unittest.main()
