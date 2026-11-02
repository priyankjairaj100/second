import copy,unittest
from reporting_v138.collect import validate
class Closure(unittest.TestCase):
 def fixture(self):
  h='a'*64;ids=['a','b','c','d'];p=dict(root_ids=ids,profiles={k:dict(blocks=b) for k,b in [('distilgpt2',6),('gpt2',12)]},phases={},total_cpu_ceiling=54760)
  phases=['checks']
  for prof in p['profiles']:
   phases += [prof+'__prepare']+[prof+'__'+m+str(n) for m in ['tokens','references'] for n in [3,2]]+[prof+'__oracle'+str(n) for n in [3,2]]
  phases+=['audit'];receipts={};lines=[];pairs=[]
  for i,phase in enumerate(phases):
   p['phases'][phase]=dict(cpu_seconds=5000);receipts[phase]=dict(phase=phase,job_id=str(9000+i),status='complete',error=None,registration_sha256=h,process_cpu_seconds=1.,result={},artifacts={});lines.append(str(9000+i)+'|COMPLETED|0:0|2|00:00:01.000|100K');lines.append(str(9000+i)+'.batch|COMPLETED|0:0|2|00:00:01.000|100K')
  receipts['checks']['result']['tests']=335
  for prof in p['profiles']:
   for n in [3,2]:
    oracle=prof+'__oracle'+str(n)
    for m in ['tokens','references']:
     phase=prof+'__'+m+str(n);r=receipts[phase];art={m+'/state.bin':dict(bytes=100,sha256='b'*64),m+'/model.bin':dict(bytes=10,sha256='c'*64),m+'/trust.json':dict(bytes=2,sha256='d'*64)}
     r['artifacts']=art;receipts[oracle]['artifacts'].update(copy.deepcopy(art))
     r['elapsed_seconds']=2.;r['peak_rss_kib']=100
     r['result']=dict(mode=m,count=n,profile=prof,retained_ids=ids[-n:],live_state_bytes=102,external_request_reads=[] if m=='tokens' else ids[-n:],timing=dict(neural_stage_record_pairs=4*p['profiles'][prof]['blocks']*n),access_probes=[dict(status=s) for s in (['available']*4 if m=='tokens' else ['available','available','refused','refused'])],request_elapsed_ns=1000000000,context_and_cleanup_ns=1500000000,temporary_feature_array_bytes=1000,predecessor_bytes=110)
     pairs.append(dict(phase=phase,oracle=oracle,quality_qualified=not(prof=='gpt2' and n==3),required_external_source_bytes=0 if m=='tokens' else 20))
  receipts['audit']['result']=dict(complete_pairs=8,independent_fresh_constructions=4,all_exact_same_representation_equal=True,comparisons=pairs)
  return dict(registration_sha256=h,receipts=receipts,sacct='\n'.join(lines)),p,h
 def test_valid_and_no_allocation_step_double_count(self):
  r,p,h=self.fixture();self.assertEqual(validate(r,p,h)['actual_allocation_cpu_seconds'],16)
 def test_scheduler_failure_rejected(self):
  r,p,h=self.fixture();r['sacct']=r['sacct'].replace('9001|COMPLETED|0:0','9001|FAILED|1:0')
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_missing_oracle_byte_equality_rejected(self):
  r,p,h=self.fixture();r['receipts']['gpt2__tokens2']['artifacts']['tokens/model.bin']['sha256']='e'*64
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_unavailable_source_success_rejected(self):
  r,p,h=self.fixture();r['receipts']['gpt2__references2']['result']['access_probes'][3]['status']='available'
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_quality_failure_cannot_be_relabeled(self):
  r,p,h=self.fixture();next(x for x in r['receipts']['audit']['result']['comparisons'] if x['phase']=='gpt2__tokens3')['quality_qualified']=True
  with self.assertRaises(AssertionError):validate(r,p,h)
 def test_duplicate_allocation_or_missing_phase_rejected(self):
  r,p,h=self.fixture();r['receipts']['audit']['job_id']='9000'
  with self.assertRaises(AssertionError):validate(r,p,h)
  r,p,h=self.fixture();del r['receipts']['audit']
  with self.assertRaises(AssertionError):validate(r,p,h)
if __name__=='__main__':unittest.main()
