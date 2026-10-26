"""Keep live Slurm on the host; generated receipt fixtures are not results."""
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
from research_v104 import prior_admission as old
from research_v104.prior_run import failed_cpu,check_host_binding
from src.run_store import canonical_json


def fixture():
    saved=dict(schema='failed-software-carry-v99',status='verified_failed_software_only',failed_program_sha256=old.SHA,job_id='16301',directory=str(old.PRIOR),
        conservative_aggregate_charge_seconds=56,conservative_controller_charge_seconds=10,remaining_software_aggregate_seconds=546,new_checks_controller_seconds=292,
        new_controller_ceiling_seconds=1500,total_controller_ceiling_seconds=1510,files={},source_archive={},source_inventory={},
        scheduler_raw='16301|FAILED|1:0|59|00:55.799|1|16G|csis.mn1\n',scheduler_cpu_lower_ns=55799000000,scheduler_cpu_upper_ns=55800000000,contained_software_cpu_ns=46480290000)
    entries={'registration.json':dict(program_sha256=old.SHA),'checks-submission.json':dict(job_id='16301',program_sha256=old.SHA,name='checks',operation='checks',snapshot='JobName=second99-checks'),
        'checks-entry.json':dict(status='failed',sealed_worker_cpu_ns=0,software_tree_cpu_ns=46480290000),
        'checks-host.json':dict(status='failed',host_process_cpu_ns=1,preflight_waited_child_cpu_ns=1,outcome=dict(subtree_cpu_ns=50000000000,log=dict(complete=True))),
        'software-results.json':dict(suites={'bounded_components':dict(tests=48,errors=4,failures=0,skipped=0)})}
    return saved,entries

class HostBoundary(unittest.TestCase):
    def exercise(self,live):
        saved,entries=fixture()
        def read(path,*args,**kwargs):
            return canonical_json(saved) if str(path).endswith('gates/v99-failed-software-carry.json') else dict(sha256=old.SHA)
        with ExitStack() as stack:
            stack.enter_context(patch.object(old,'verify_v91',return_value={}))
            stack.enter_context(patch.object(old,'read',side_effect=read))
            stack.enter_context(patch.object(old,'json_read',side_effect=lambda p:entries[Path(p).name]))
            stack.enter_context(patch.object(Path,'rglob',return_value=[]));stack.enter_context(patch.object(Path,'exists',return_value=False))
            child=stack.enter_context(patch.object(old.subprocess,'check_output',return_value='16301|second99-checks|FAILED|1:0|59|00:55.799|1|16G|csis.mn1\n',side_effect=None if live else AssertionError('Container must not invoke Slurm')))
            r=old.verify(live_scheduler=live);self.assertEqual(child.call_count,int(live));self.assertEqual(r['carried_software_seconds'],56)
    def test_container_uses_bound_saved_cost_without_starting_slurm(self):self.exercise(False)
    def test_host_rechecks_live_failed_scheduler_identity(self):self.exercise(True)
    def test_new_failed_job_state_and_cost_cannot_be_relabeled(self):
        raw='16307|second100-checks|FAILED|1:0|4|00:03.249|1|16G|csis.mn1\n'
        self.assertEqual(failed_cpu(raw),(3249000000,3250000000))
        for wrong in (raw.replace('FAILED','COMPLETED'),raw.replace('03.249','02.249'),raw.replace('16307','16308')):
            with self.assertRaises(ValueError):failed_cpu(wrong)
    def test_current_host_binding_cannot_be_reused_for_other_job(self):
        p={'prior_complete_failure':{'fixture_only':True}};start=dict(program_sha256='a'*64,operation='checks',job_id='123',live_failure_scheduler_verified=True,prior_failure_verification=p['prior_complete_failure'])
        check_host_binding(p,start,'a'*64,'checks','123')
        for change in ({'job_id':'124'},{'live_failure_scheduler_verified':False},{'prior_failure_verification':{}},{'program_sha256':'b'*64}):
            with self.assertRaises(ValueError):check_host_binding(p,dict(start,**change),'a'*64,'checks','123')

if __name__=='__main__':unittest.main()
