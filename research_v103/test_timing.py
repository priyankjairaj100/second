"""Saved-byte nested clocks: generated fixture, not measured research speed."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from research_v103 import timing
from research_v103.host import reconcile_cpu
from research_v83.terminal import Inputs
from research_v80.io import write,info,json_read
from src.run_store import canonical_json,digest
TRIAL='distilgpt2/reference_modern-1'

def fixture(root):
    p={'host':'csis.mn1','controller_cpu_allowance_seconds':6040};sha=digest(canonical_json(p));write(root/'program.json',p)
    key=TRIAL.replace('/','--');ident=dict(program_sha256=sha,job_id='123',operation=TRIAL,arguments=[])
    q=dict(worker_elapsed_ns=10,context_elapsed_ns=1,max_rss_kib=20,request=dict(request_elapsed_ns=5,timing={'fixture':True},live_state_bytes=30))
    e=dict(ident,status='complete',error=None,hostname='csis.mn1',cpu_limits=[300,10202],affinity_cpus=[0],
        process_cpu_ns=4,waited_child_cpu_ns=10,sealed_worker_cpu_ns=9,software_tree_cpu_ns=0,elapsed_ns=30)
    h=dict(ident,status='complete',error=None,elapsed_ns=40,host_process_cpu_ns=2,preflight_waited_child_cpu_ns=3,
        outcome=dict(exit_code=0,failure=None,subtree_cpu_ns=20,log=dict(**info(b'log'),complete=True)))
    h['accounting']=reconcile_cpu(TRIAL,2,3,20,e)
    for suffix,obj in [('entry',e),('entry-start',ident),('host',h)]:write(root/(key+'-'+suffix+'.json'),obj)
    write(root/(key+'-bootstrap.log'),b'log',raw=True)
    write(root/TRIAL/'transaction.json',dict(slurm_job_id='123',elapsed_ns=20))
    return p,{TRIAL:q},key

class Timing(unittest.TestCase):
    def test_primary_host_contains_transaction_worker_and_request(self):
        with TemporaryDirectory() as d:
            root=Path(d).resolve();p,q,_=fixture(root)
            with patch('research_v83.terminal.BASE',root),patch.object(timing,'RUN',root),patch.object(timing,'ORDER',[TRIAL]):r=timing.costs(p,q,Inputs())
            row=r['trials'][TRIAL];self.assertEqual([row[n] for n in ('complete_host_elapsed_ns','transaction_elapsed_ns','worker_elapsed_ns','request_elapsed_ns')],[40,20,10,5])
            self.assertEqual(row['complete_host_cpu_ns'],25)
    def test_false_clock_containment_and_modified_log_refuse(self):
        for change in ('clock','log'):
            with TemporaryDirectory() as d:
                root=Path(d).resolve();p,q,key=fixture(root)
                if change=='clock':q[TRIAL]['worker_elapsed_ns']=100
                else:(root/(key+'-bootstrap.log')).write_bytes(b'changed')
                with patch('research_v83.terminal.BASE',root),patch.object(timing,'RUN',root),patch.object(timing,'ORDER',[TRIAL]),self.assertRaises(ValueError):timing.costs(p,q,Inputs())
    def test_missing_envelope_cost_or_extra_controller_cpu_refuse(self):
        for change in ('cost','overhead'):
            with TemporaryDirectory() as d:
                root=Path(d).resolve();p,q,key=fixture(root);path=root/(key+'-host.json');h=json_read(path)
                if change=='cost':h['accounting']['nonnumerical_cpu_ns']=0
                else:h['host_process_cpu_ns']=303*10**9
                path.write_bytes(canonical_json(h))
                with patch('research_v83.terminal.BASE',root),patch.object(timing,'RUN',root),patch.object(timing,'ORDER',[TRIAL]),self.assertRaises(ValueError):timing.costs(p,q,Inputs())
if __name__=='__main__':unittest.main()
