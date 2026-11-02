"""Generated refusal tests for the separate recovery; no scientific execution."""
import copy,unittest
from research_v72.recover_accounting import failed_closure,REG71
from research_v71.cost_accounting import scheduler_rows
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.receipt=dict(schema='quality-post-exit-closure-v71',registration_sha256=REG71,job_id='15413',status='failed',result=None,
            error=dict(type='FileNotFoundError',message="[Errno 2] No such file or directory: 'sacct'"),
            process_cpu_ns=4_000_000_000,waited_child_cpu_ns=20_000_000,elapsed_ns=4_000_000_000,maximum_rss_kib=100000,
            whole_process_and_all_waited_children_included=True)
        self.row=scheduler_rows('15413|FAILED|1:0|6|00:04.817|1',{'failed':'15413'})['failed']
    def test_failure_stays_failure_and_cost_not_zero(self):
        r=failed_closure(self.receipt,self.row)
        self.assertFalse(r['original_closure_successful']);self.assertEqual(r['charged_cpu_seconds'],5)
    def test_relabelled_missing_underreported_or_overbudget_failure_rejected(self):
        for key,value in [('status','complete'),('result',{}),('job_id','15414'),('registration_sha256','0'*64),
            ('process_cpu_ns',303*10**9),('elapsed_ns',8*10**9),('maximum_rss_kib',5*2**20),
            ('whole_process_and_all_waited_children_included',False),('error',None)]:
            r=copy.deepcopy(self.receipt);r[key]=value
            with self.subTest(key=key),self.assertRaises((AssertionError,ValueError)):failed_closure(r,self.row)
        for key,value in [('state','COMPLETED'),('exit_code','0:0'),('total_cpu_ns',1),('elapsed_seconds',901),('job_id','15414')]:
            r=copy.deepcopy(self.row);r[key]=value
            with self.subTest(scheduler=key),self.assertRaises((AssertionError,ValueError)):failed_closure(self.receipt,r)
if __name__=='__main__':unittest.main()

class HeldJobTests(unittest.TestCase):
    def test_actual_held_shape_and_mutations(self):
        import tarfile,json
        from pathlib import Path
        from research_v72.submit_once import inspect,RUN,ROOT
        root=Path(__file__).resolve().parents[1]
        with tarfile.open(root/'campaigns/csis_v71_metadata_20261018_g.tar.gz') as t:
            held=json.load(t.extractfile('closure/held-verification.json'))['fields']
        f=dict(held);job='99999';reg='a'*64
        f.update(JobId=job,JobName='second72-cost-audit',Dependency='(null)',TimeLimit='00:20:00',
            Command=str(RUN/'research_v72/run_cpu.sbatch'),StdOut=str(RUN/('slurm-'+job+'.log')),
            StdErr=str(RUN/('slurm-'+job+'.log')),Comment='second-v72:'+reg)
        raw=lambda d:' '.join(k+'='+v for k,v in d.items())
        inspect(raw(f),job,reg)
        for key,value in [('Requeue','1'),('NumCPUs','2'),('JobState','RUNNING'),('Priority','1'),
            ('Comment','other'),('MinMemoryNode','8G'),('TimeLimit','01:00:00'),('ReqNodeList','csis.cn1'),
            ('ReqTRES',f['ReqTRES']+',gres/gpu=1'),('Dependency','afterok:15413(unfulfilled)')]:
            altered=dict(f);altered[key]=value
            with self.subTest(key=key),self.assertRaises((AssertionError,ValueError)):inspect(raw(altered),job,reg)
