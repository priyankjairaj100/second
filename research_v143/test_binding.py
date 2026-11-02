import unittest,copy,json
from pathlib import Path
from research_v143.binding import endpoint
class Endpoints(unittest.TestCase):
 def setUp(self):
  # Generated metadata with the actual frozen program's shape, no model reads.
  x=dict(path='/declared/model',bytes=1,sha256='1'*64)
  self.p={'endpoints':{key:dict(completion=dict(x),model=dict(x)) for key in ('candidate_2','candidate_3')}}
 def test_both_actual_keys_resolve(self):
  for n in (2,3):self.assertEqual(endpoint(self.p,n),self.p['endpoints']['candidate_'+str(n)])
 def test_old_wrong_key_cannot_pass_preflight(self):
  self.p['endpoints']['retained2']=self.p['endpoints'].pop('candidate_2')
  with self.assertRaises(AssertionError):endpoint(self.p,2)
 def test_incomplete_artifact_binding_refused(self):
  del self.p['endpoints']['candidate_3']['model']['sha256']
  with self.assertRaises(AssertionError):endpoint(self.p,2)
if __name__=='__main__':unittest.main()
