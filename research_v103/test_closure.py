"""Saved receipt-byte review with synthetic clocks/capacity, no cluster evidence."""
import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from research_v80.io import json_read,read,write,info
from research_v103 import closure,storage_plan,host
from research_v103.config import design
from research_v103.software import SUITES
from research_v88.storage import evaluate
from src.run_store import canonical_json,digest
class Inputs:
    def json(self,path):return json_read(path)
    def read(self,path,expected=None,retain=True):return read(path,expected,retain=retain)


def fixture(root):
    sources={'fixture.py':info(b'x')};p=dict(design(),sources=sources,source_archive=dict(bytes=10240),storage_plan=storage_plan.build(sources,10240))
    p['prior_complete_failure']={'fixture_only':True}
    sha=digest(canonical_json(p));wanted=storage_plan.requests(p['storage_plan'],sources,10240,'checks')
    quota='Filesystem blocks quota limit grace files quota limit grace\n/dev/project 100 999999999 1000000000 12 0 0\n'
    observations={scope:dict(path=item['path'],device=1 if scope=='project' else 2,source='/dev/project' if scope=='project' else '/dev/temp',
        mount='/',filesystem='ext4' if scope=='project' else 'xfs',options='rw,usrquota' if scope=='project' else 'rw,noquota',
        available_bytes=2**40,available_files=100000,fragment_bytes=4096,write_group=1008) for scope,item in wanted.items()}
    snap=dict(requested=wanted,observations=observations,quota_text=quota,group_reports={})
    ident=dict(program_sha256=sha,job_id='76543',operation='checks',arguments=[])
    report=dict(schema='complete-matched-software-v103',empirical_execution=False,
        suites={name:dict(tests=count,failures=0,errors=0,skipped=0) for name,(_,count) in SUITES.items()})
    entry=dict(ident,status='complete',error=None,process_cpu_ns=10,waited_child_cpu_ns=50,sealed_worker_cpu_ns=0,
        software_tree_cpu_ns=40,elapsed_ns=90,maximum_rss_kib=10,result=report,
        container_storage_mapping=dict(status='matched_host_devices_and_new_file_groups',paths_redirected=False,
            observations={scope:dict(path=str(root) if scope=='project' else '/tmp',device=o['device'],write_group=1008) for scope,o in observations.items()}))
    h=dict(ident,status='complete',error=None,host_process_cpu_ns=3,preflight_waited_child_cpu_ns=7,elapsed_ns=100,
        outcome=dict(exit_code=0,failure=None,subtree_cpu_ns=100,log=dict(**info(b'log'),observed_bytes=3,complete=True)),
        accounting=host.reconcile_cpu('checks',3,7,100,entry))
    start=dict(ident,live_failure_scheduler_verified=True,prior_failure_verification=p['prior_complete_failure'],requests=wanted,snapshot=snap,admission=evaluate(wanted,observations,quota,{}))
    for name,value in [('checks-entry.json',entry),('checks-host.json',h),('checks-host-start.json',start),('software-results.json',report)]:write(root/name,value)
    write(root/'checks-bootstrap.log',b'log',raw=True);write(root/'checks-76543.log',b'',raw=True)
    scheduled=dict(job_id='76543',cpu_ns=110,quantum_ns=1,elapsed_seconds=1)
    return p,sha,scheduled

class Closure(unittest.TestCase):
    def test_complete_saved_files_and_overlapping_clocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p,sha,s=fixture(root)
            with patch.object(closure,'RUN',root):
                cost,worker=closure.review('checks',p,sha,Inputs(),s)
            self.assertIsNone(worker);self.assertEqual(cost['complete_controller_upper_cpu_ns'],71)
    def test_changed_log_and_omitted_software_suite_refuse(self):
        for which in ('log','suite'):
            with self.subTest(which=which),tempfile.TemporaryDirectory() as d:
                root=Path(d).resolve();p,sha,s=fixture(root)
                if which=='log':(root/'checks-bootstrap.log').write_bytes(b'changed')
                else:
                    e=json_read(root/'checks-entry.json');e['result']['suites'].pop('profiles');(root/'checks-entry.json').write_bytes(canonical_json(e))
                with patch.object(closure,'RUN',root),self.assertRaises(ValueError):closure.review('checks',p,sha,Inputs(),s)
    def test_stale_storage_device_and_forged_clock_refuse(self):
        for which in ('mapping','clock'):
            with self.subTest(which=which),tempfile.TemporaryDirectory() as d:
                root=Path(d).resolve();p,sha,s=fixture(root)
                path=root/('checks-entry.json' if which=='mapping' else 'checks-host.json');e=json_read(path)
                if which=='mapping':e['container_storage_mapping']['observations']['temporary']['device']+=1
                else:e['host_process_cpu_ns']+=1
                path.write_bytes(canonical_json(e))
                with patch.object(closure,'RUN',root),self.assertRaises(ValueError):closure.review('checks',p,sha,Inputs(),s)
    def test_scheduler_cannot_underreport_envelope_or_hide_final_overhead(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p,sha,s=fixture(root)
            for value in (100,603*10**9):
                with patch.object(closure,'RUN',root),self.assertRaises(ValueError):closure.review('checks',p,sha,Inputs(),dict(s,cpu_ns=value))
if __name__=='__main__':unittest.main()
