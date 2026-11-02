import unittest
import numpy as np
from research_v49.profile import fixture,WIDTHS


class FixtureTests(unittest.TestCase):
    def test_deterministic_exact_dyadic_inputs(self):
        for width in WIDTHS:
            w,x=fixture(width);w2,x2=fixture(width)
            self.assertEqual(w.shape,(4,width));self.assertEqual(x.shape,(width,128))
            self.assertEqual(w.tobytes(),w2.tobytes());self.assertEqual(x.tobytes(),x2.tobytes())
            self.assertTrue(np.equal(w*512,np.rint(w*512)).all())
            self.assertTrue(np.equal(x*64,np.rint(x*64)).all())
            self.assertGreater(np.count_nonzero(x),0)
    def test_unregistered_case_refused(self):
        with self.assertRaises(ValueError):fixture(3072)


if __name__=='__main__':unittest.main()
