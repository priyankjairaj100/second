"""Generated future-receipt validation; no upstream success is inferred."""
import copy,json,unittest
from research_v82.prerequisite import validate_payloads,V81_SHA,COUNTS,info,canonical

def fixture():
    r=dict(empirical_execution=False,suites={k:dict(tests=n,failures=0,errors=0,skipped=0) for k,n in COUNTS.items()})
    b=canonical(r)
    q=dict(status='complete',error=None,program_sha256=V81_SHA,job_id='15917',hostname='csis.mn1',empirical_execution=False,
        outputs={'outputs/transfer-results.json':info(b)},process_cpu_ns=12,waited_child_cpu_ns=34,aggregate_cpu_ns=46)
    return q,r
class Prerequisite(unittest.TestCase):
    def test_exact_pass_binds_actual_receipt_and_report_bytes(self):
        q,r=fixture();a,b=canonical(q),canonical(r);p=validate_payloads(a,b)
        self.assertEqual(p['completion'],info(a));self.assertEqual(p['report'],info(b));self.assertEqual(p['test_count'],62)
    def test_wrong_job_program_status_and_cpu_refuse(self):
        q,r=fixture()
        for key,value in [('status','failed'),('job_id','15918'),('program_sha256','0'*64),('hostname','wrong'),('aggregate_cpu_ns',47),('empirical_execution',True)]:
            bad=dict(q);bad[key]=value
            with self.assertRaises(ValueError):validate_payloads(canonical(bad),canonical(r))
    def test_skipped_missing_or_failed_suites_refuse_even_after_rehash(self):
        q,r=fixture()
        for kind in ('skip','missing','failure'):
            bad=copy.deepcopy(r)
            if kind=='skip':bad['suites']['profiles']['skipped']=1
            elif kind=='missing':bad['suites'].pop('profiles')
            else:bad['suites']['profiles']['failures']=1
            blob=canonical(bad);bound=copy.deepcopy(q);bound['outputs']['outputs/transfer-results.json']=info(blob)
            with self.assertRaises(ValueError):validate_payloads(canonical(bound),blob)
    def test_report_byte_change_cannot_use_old_completion(self):
        q,r=fixture()
        with self.assertRaises(ValueError):validate_payloads(canonical(q),canonical(r)+b' ')
if __name__=='__main__':unittest.main()
