import copy,unittest
from reporting_v138.test_collect import Closure as OldFixture
from reporting_v143.collect import validate

class Closure(unittest.TestCase):
 def fixture(self):
  r,p,h=OldFixture().fixture();oracles={}
  for phase in list(p['phases']):
   if '__oracle' in phase:
    oracles[phase]=dict(producer_state='FAILED',artifacts=copy.deepcopy(r['receipts'][phase]['artifacts']))
   if '__prepare' in phase or '__oracle' in phase:
    del p['phases'][phase];del r['receipts'][phase]
  r['receipts']['checks']['result']['tests']=338
  r['saved_output_audit']=dict(status='complete',result=dict(independently_constructed_oracles_audited=4,oracles=oracles))
  r['saved_output_audit_identity']=dict(bytes=23,sha256='b'*64);p['saved_output_audit']=dict(r['saved_output_audit_identity'],path='/audit/completion.json')
  p.update(total_cpu_ceiling=30000,prior_v138_total_actual_cpu_seconds=9626.619,prior_v138_original_ceiling_preserved=54760)
  return r,p,h
 def test_valid_and_no_double_charge(self):
  r,p,h=self.fixture();a=validate(r,p,h);self.assertEqual(a['actual_allocation_cpu_seconds'],10);self.assertEqual(a['actual_jobs'],10)
 def test_changed_artifact_refused(self):
  r,p,h=self.fixture();r['receipts']['gpt2__tokens2']['artifacts']['tokens/model.bin']['sha256']='f'*64
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_failed_job_cannot_count_as_success(self):
  r,p,h=self.fixture();r['sacct']=r['sacct'].replace('9002|COMPLETED|0:0','9002|FAILED|1:0')
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_oracle_failure_not_erased(self):
  r,p,h=self.fixture();r['saved_output_audit']['result']['oracles']['gpt2__oracle2']['producer_state']='COMPLETED'
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_wrong_audit_receipt_refused(self):
  r,p,h=self.fixture();r['saved_output_audit_identity']['sha256']='f'*64
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_duplicate_pair_refused(self):
  r,p,h=self.fixture();a=r['receipts']['audit']['result']['comparisons'];a[-1]=copy.deepcopy(a[0])
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_unavailable_reference_success_refused(self):
  r,p,h=self.fixture();r['receipts']['gpt2__references2']['result']['access_probes'][3]['status']='available'
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_failed_quality_remains_failed(self):
  r,p,h=self.fixture();next(x for x in r['receipts']['audit']['result']['comparisons'] if x['phase']=='gpt2__tokens3')['quality_qualified']=True
  with self.assertRaises(AssertionError):validate(r,p,h)

if __name__=='__main__':unittest.main()
