import unittest,copy
from research_v132.worker import retained
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

class TargetBinding(unittest.TestCase):
 def fixture(self):
  from types import SimpleNamespace
  from src.run_store import canonical_json,digest
  cal=canonical_json({'target':'fixture'});anchor=b'anchor'
  return SimpleNamespace(anchor_payload=anchor,fixed_payload=canonical_json({'calibration_target':{'target':'fixture'},'service_metadata':'distinct wrapper'}),calibration_target_sha256=digest(cal)),anchor,cal
 def test_inner_calibration_not_outer_service_payload(self):
  from research_v132.worker import verify_target
  b,a,c=self.fixture();self.assertNotEqual(b.fixed_payload,c);verify_target(b,a,c)
 def test_changed_anchor_and_calibration_rejected(self):
  from research_v132.worker import verify_target
  b,a,c=self.fixture()
  for x,y in [(b'wrong',c),(a,b'wrong')]:
   with self.assertRaises(AssertionError):verify_target(b,x,y)
 def test_changed_calibration_digest_rejected(self):
  from research_v132.worker import verify_target
  b,a,c=self.fixture();b.calibration_target_sha256='0'*64
  with self.assertRaises(AssertionError):verify_target(b,a,c)
