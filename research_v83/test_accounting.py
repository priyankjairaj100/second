"""Generated terminal fixtures, never scientific evidence."""
import copy,unittest
from research_v83.accounting import cpu_time,scheduler_rows,reconcile
JOBS={'trial':dict(job_id='15905',name='second80-prepare')}
RAW='15905|second80-prepare|COMPLETED|0:0|10|00:07.100|1|16G|csis.mn1\n'
def entry():return dict(status='complete',error=None,job_id='15905',program_sha256='a'*64,operation='run',process_cpu_ns=2*10**9,waited_child_cpu_ns=5*10**9,elapsed_ns=9*10**9,maximum_rss_kib=9000)
def worker():return dict(resource_usage=dict(total_cpu_ns=4*10**9,user_cpu_ns=3*10**9,system_cpu_ns=10**9,max_rss_kib=10000),outcome=dict(status='complete',returncode=0),budget_debit=dict(state='settled',observed_cpu_ns=4*10**9,reserved_cpu_seconds=602,charged_cpu_seconds=4),budget_reservation_overrun=False,limits=dict(cpu_seconds=600))
def check(e=None,s=None,w=None):return reconcile(e or entry(),s or scheduler_rows(RAW,JOBS)['trial'],program_sha='a'*64,operation='run',own_cap=301,aggregate_cap=903,worker=w)
class Terminal(unittest.TestCase):
    def test_exact_clocks_with_days_and_fraction_precision(self):
        self.assertEqual(cpu_time('1-02:03:04.123456'),(93784123456000,1000));self.assertEqual(cpu_time('00:02'),(2000000000,1000000000))
        for s in ('nan','1:99','1-25:00:00','-1:00','1.5'):
            with self.assertRaises(ValueError):cpu_time(s)
    def test_allocation_and_steps_are_not_added_twice(self):
        rows=scheduler_rows(RAW+'15905.batch|batch|COMPLETED|0:0|10|00:07.100|1||csis.mn1\n',JOBS)
        self.assertEqual(len(rows),1);self.assertEqual(rows['trial']['cpu_ns'],7100000000)
    def test_missing_duplicate_unknown_and_running_jobs_refuse(self):
        for raw in ('',RAW+RAW,RAW+RAW.replace('15905','999'),RAW.replace('COMPLETED','RUNNING')):
            with self.assertRaises(ValueError):scheduler_rows(raw,JOBS)
    def test_failed_jobs_cannot_be_promoted_by_successful_entry(self):
        for raw in (RAW.replace('COMPLETED','FAILED'),RAW.replace('|0:0|','|1:0|')):
            with self.assertRaises(ValueError):scheduler_rows(raw,JOBS)
    def test_name_node_memory_and_cpu_changes_refuse(self):
        for a,b in [('second80-prepare','other'),('csis.mn1','csis.mn2'),('16G','32G'),('|1|','|2|')]:
            with self.assertRaises(ValueError):scheduler_rows(RAW.replace(a,b),JOBS)
    def test_process_tree_does_not_add_sealed_cpu_twice(self):
        r=check(w=worker());self.assertEqual(r['observed_process_tree_cpu_ns'],7*10**9);self.assertEqual(r['nonworker_child_cpu_ns'],10**9)
    def test_underreported_scheduler_and_duration_refuse(self):
        for k,v in [('cpu_ns',1),('elapsed_seconds',0)]:
            s=scheduler_rows(RAW,JOBS)['trial'];s[k]=v
            with self.assertRaises(ValueError):check(s=s)
    def test_wrong_receipt_identity_and_failure_refuse(self):
        for k,v in [('program_sha256','b'*64),('job_id','1'),('operation','checks'),('status','failed'),('error',{})]:
            e=entry();e[k]=v
            with self.assertRaises(ValueError):check(e=e)
    def test_missing_child_cpu_and_bad_debit_refuse(self):
        e=entry();e['waited_child_cpu_ns']=3*10**9
        with self.assertRaises(ValueError):check(e=e,w=worker())
        w=worker();w['budget_debit']['charged_cpu_seconds']=3
        with self.assertRaises(ValueError):check(w=w)
    def test_memory_and_cpu_overruns_refuse(self):
        for k,v in [('maximum_rss_kib',17*2**20),('process_cpu_ns',302*10**9),('waited_child_cpu_ns',-1)]:
            e=entry();e[k]=v
            with self.assertRaises(ValueError):check(e=e)
    def test_helper_children_cannot_hide_in_worker_reservation(self):
        e=entry();e['process_cpu_ns']=300*10**9;e['waited_child_cpu_ns']=6*10**9
        s=scheduler_rows(RAW,JOBS)['trial'];s['cpu_ns']=306*10**9
        with self.assertRaises(ValueError):check(e=e,s=s,w=worker())
if __name__=='__main__':unittest.main()
