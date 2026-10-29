"""Exercise every real host dispatch boundary with external effects replaced."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
from research_v104 import host,campaign,dispatch_failure,storage_plan
from research_v104.config import OPERATIONS,design,name
from research_v104.records import writer
from research_v80.io import info,write,json_read

class Dispatch(unittest.TestCase):
    def test_all_twenty_three_operations_keep_registered_name_through_storage_and_container(self):
        for operation in OPERATIONS:
            with self.subTest(operation=operation),tempfile.TemporaryDirectory() as d,ExitStack() as stack:
                root=Path(d).resolve();sha='a'*64;job='76543';prior={'fixture_only':True};sources={'fixture.py':info(b'x')}
                p=dict(design(),sources=sources,source_archive=dict(bytes=10240),storage_plan=storage_plan.build(sources,10240),prior_complete_failure=prior)
                stack.enter_context(patch.object(host,'RUN',root));stack.enter_context(patch.object(host,'ROOT',root))
                stack.enter_context(patch.object(host,'__file__',str(root/'research_v104/host.py')))
                stack.enter_context(patch.object(host.sys,'platform','linux'));stack.enter_context(patch.dict(os.environ,SLURM_JOB_ID=job))
                stack.enter_context(patch.object(host.os,'sched_getaffinity',return_value={0},create=True));stack.enter_context(patch.object(host.os,'sched_setaffinity',create=True))
                stack.enter_context(patch.object(host.resource,'setrlimit'))
                stack.enter_context(patch.object(campaign,'verify',return_value=p));stack.enter_context(patch.object(campaign,'sha',return_value=sha))
                stack.enter_context(patch.object(host.protocol,'allocation'));stack.enter_context(patch.object(dispatch_failure,'verify',return_value=prior))
                stack.enter_context(patch.object(host,'writer',side_effect=lambda:writer(root)))
                capture=stack.enter_context(patch.object(host,'capture',return_value=dict(observations={},quota_text='',group_reports={})))
                stack.enter_context(patch.object(host,'evaluate',return_value={'fixture_only':True}))
                def collect(command,log,*args,**kwargs):
                    self.assertEqual(command,['/bin/bash',str(root/'research_v104/container.sh'),operation,sha])
                    write(root/(name(operation)+'-entry.json'),dict(status='complete',error=None,program_sha256=sha,job_id=job,
                        sealed_worker_cpu_ns=0,software_tree_cpu_ns=0,waited_child_cpu_ns=20,process_cpu_ns=10))
                    return dict(exit_code=0,failure=None,subtree_cpu_ns=30,log=dict(**info(b''),complete=True))
                child=stack.enter_context(patch.object(host,'collect',side_effect=collect))
                host.main(operation,sha)
                capture.assert_called_once_with(storage_plan.requests(p['storage_plan'],sources,10240,operation));self.assertEqual(child.call_count,1)
                start=json_read(root/(name(operation)+'-host-start.json'));self.assertEqual(start['operation'],operation)
                self.assertEqual(start['prior_failure_verification'],prior);self.assertTrue(start['live_failure_scheduler_verified'])
                self.assertEqual(json_read(root/(name(operation)+'-host.json'))['status'],'complete')
    def test_filename_aliases_are_not_storage_operations(self):
        sources={'fixture.py':info(b'x')};plan=storage_plan.build(sources,10240)
        for op in OPERATIONS:
            if '/' in op:
                with self.assertRaises(ValueError):storage_plan.requests(plan,sources,10240,name(op))

if __name__=='__main__':unittest.main()
