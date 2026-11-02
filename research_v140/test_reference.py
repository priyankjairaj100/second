import unittest
from fractions import Fraction as Q
from research_v140.reference import solve,quantize,coefficient
class ReferenceTests(unittest.TestCase):
 def test_exact_system_with_pivot_exchange(self):
  self.assertEqual(solve([[0,2],[3,4]],[6,15]),[Q(1),Q(3)])
 def test_conditional_minimum_and_lower_tie(self):
  self.assertEqual(quantize([[.5,.5]],[[1.],[1.]],[1.],Q(1),Q(1)),[[Q(0),Q(1)]])
  self.assertEqual(quantize([[-.5,20.]],[[0.],[0.]],[1.],Q(1),Q(1)),[[Q(-1),Q(7)]])
 def test_coefficient_hand_solution(self):
  self.assertEqual(coefficient([[1.,0.],[0.,1.]],0,Q(1)),[Q(1,2),Q(0)])
if __name__=='__main__':unittest.main()
