import unittest,copy
from research_v130.worker import retained
class Membership(unittest.TestCase):
 def setUp(self):self.root=[{'id':str(i),'tokens':[i]*128} for i in range(4)]
 def test_exact_two_and_three_memberships(self):
  for ids in [['1','2','3'],['2','3']]:self.assertEqual(retained(self.root,ids),self.root[-len(ids):])
 def test_duplicate_missing_or_wrong_extent_refused(self):
  for ids in [['1','1'],['1','5'],['1'],['0','1','2','3']]:
   with self.assertRaises(AssertionError):retained(self.root,ids)
 def test_wrong_token_words_or_shape_refused(self):
  for toks in [[0]*127,[50257]*128,[True]*128]:
   root=copy.deepcopy(self.root);root[0]['tokens']=toks
   with self.assertRaises(AssertionError):retained(root,['2','3'])
 def test_noncanonical_or_mutated_root_extent_refused(self):
  for root in [list(reversed(self.root)),self.root[1:],self.root+[self.root[0]]]:
   with self.assertRaises(AssertionError):retained(root,['2','3'])
