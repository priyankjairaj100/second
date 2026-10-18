"""Generated post-exit accounting and mocked predecessors, no actual jobs."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import copy,unittest
from research_v71 import closure as f


def receipt():
    phases={p:{'job_id':str(100+i)} for i,p in enumerate(f.c.ORDER)}
    return dict(schema='quality-post-exit-closure-v71',registration_sha256='a'*64,job_id='999',
        status='complete',error=None,process_cpu_ns=2*10**9,waited_child_cpu_ns=10**9,
        elapsed_ns=4*10**9,maximum_rss_kib=1000,whole_process_and_all_waited_children_included=True,
        result=dict(accounting=dict(status='verified_complete_cost_accounting',phases=phases,
            execution_successful=True,scheduler_cpu_ns=40*10**9,worker_charged_cpu_seconds=20,
            controller_charged_cpu_seconds=8),actual_artifacts_verified=True,quality_guard_pass=False))


class ClosureTests(unittest.TestCase):
    def test_own_terminal_cost_is_required_and_negative_quality_remains_complete(self):
        row='999|COMPLETED|0:0|5|00:03.500|1'
        result=f.verify_observer(receipt(),row,registration_sha256='a'*64,closure_job='999')
        self.assertEqual(result['total_registered_scheduler_cpu_ns'],43500000000)
        self.assertEqual(result['total_registered_cpu_allowance_seconds'],44726)
        self.assertTrue(result['all_registered_execution_succeeded']);self.assertFalse(result['quality_guard_pass'])
        with self.assertRaises(ValueError):f.verify_observer(receipt(),'',registration_sha256='a'*64,closure_job='999')
        with self.assertRaises(ValueError):f.verify_observer(receipt(),row.replace('COMPLETED','RUNNING'),registration_sha256='a'*64,closure_job='999')

    def test_underreported_overbudget_or_duplicate_closure_costs_refuse(self):
        row='999|COMPLETED|0:0|5|00:03.500|1'
        for key,value in [('process_cpu_ns',303*10**9),('whole_process_and_all_waited_children_included',False),
            ('waited_child_cpu_ns',4*10**9),('maximum_rss_kib',5*2**20)]:
            r=receipt();r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):f.verify_observer(r,row,registration_sha256='a'*64,closure_job='999')
        r=receipt();r['result']['accounting']['phases']['terminal']['job_id']='999'
        with self.assertRaises(ValueError):f.verify_observer(r,row,registration_sha256='a'*64,closure_job='999')

    def test_accounted_execution_failure_cannot_claim_actual_artifacts(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();(root/'budget').mkdir();(root/'budget/ledger.json').write_bytes(b'generated')
            jobs={p:str(100+i) for i,p in enumerate(f.c.ORDER)}
            raw='\n'.join(j+'|FAILED|1:0|5|00:03.500|1' for j in jobs.values())
            with patch.object(f.c,'RUN',root),patch.object(f.c,'job',side_effect=lambda p,n:{'job_id':jobs[n]}),\
                patch.object(f.c,'snapshot',return_value={}),patch.object(f,'json_read',return_value={'affinity_cpus':[3]}),\
                patch.object(f.c,'worker_identity',return_value={}),patch.object(f.costs,'worker',return_value={}),\
                patch.object(f.costs,'reconcile',return_value={}),\
                patch.object(f.costs,'complete',return_value={'execution_successful':False}),patch.object(f.c,'finished') as finish:
                result=f.audit({},raw)
            finish.assert_not_called();self.assertFalse(result['actual_artifacts_verified']);self.assertIsNone(result['quality_guard_pass'])


if __name__=='__main__':unittest.main()
