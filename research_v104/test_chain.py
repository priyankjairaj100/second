"""Twenty-two held dependent jobs against fake Slurm; never a live submission."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import io,json,unittest
from contextlib import redirect_stdout
from research_v104 import submit
from research_v104.config import OPERATIONS,design,name
from research_v104.records import writer
from research_v80.io import write,json_read
from research_v104.test_submit import snapshot
class Chain(unittest.TestCase):
    def exercise(self,fail_at=None):
        with TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p=design();sha='a'*64;launched=[];released=[];states={}
            write(root/'checks-submission.json',dict(job_id='76543'))
            for obj,key,value in [(submit,'RUN',root),(submit,'__file__',str(root/'research_v104/submit.py'))]:stack.enter_context(patch.object(obj,key,value))
            stack.enter_context(patch.object(submit.campaign,'verify',return_value=p));stack.enter_context(patch.object(submit.campaign,'sha',return_value=sha))
            for obj,key in [(submit,'inspect_upstream'),(submit.protocol,'allocation'),(submit,'review')]:stack.enter_context(patch.object(obj,key))
            stack.enter_context(patch.object(submit,'scheduler_rows',return_value={'checks':{}}))
            stack.enter_context(patch.object(submit,'admit',return_value=({}, {}, {})))
            stack.enter_context(patch.object(submit,'writer',side_effect=lambda:writer(root)))
            def call(args):
                if 'rev-parse' in args:return p['numerical_checkout']
                if args[0]=='scontrol':return states[args[-1]]
                return ''
            def run(args,**kw):
                if args[0]=='sbatch':
                    op=args[-2];index=len(launched);job=str(80000+index);launched.append(args)
                    dependency=next(a.split('afterok:',1)[1] for a in args if a.startswith('--dependency='))
                    states[job]=snapshot(op,dependency)
                    return SimpleNamespace(returncode=0,stdout='unknown' if index==fail_at else job,stderr='')
                # Every job must be checked while held before any release occurs.
                held=json_read(root/'chain-held-chain.json');self.assertEqual(len(held['jobs']),22)
                released.append(args[-1]);return SimpleNamespace(returncode=0)
            stack.enter_context(patch.object(submit,'call',side_effect=call));stack.enter_context(patch.object(submit.subprocess,'run',side_effect=run))
            with redirect_stdout(io.StringIO()):
                if fail_at is None:submit.main('chain',sha)
                else:
                    with self.assertRaises(ValueError):submit.main('chain',sha)
            with self.assertRaisesRegex(ValueError,'consumed'):submit.main('chain',sha)
            return launched,released,{f.name:f.read_bytes() for f in root.iterdir()}
    def test_complete_prespecified_chain_is_held_verified_then_released(self):
        launched,released,files=self.exercise();self.assertEqual([x[-2] for x in launched],list(OPERATIONS[1:]))
        self.assertEqual(released,[str(80000+i) for i in range(22)])
        for args,op in zip(launched,OPERATIONS[1:]):
            self.assertIn('--job-name=second104-'+name(op),args);self.assertIn('--time='+submit.clock(op),args)
            self.assertIn('--mem=16G',args);self.assertIn('--cpus-per-task=1',args);self.assertIn('--no-requeue',args)
        self.assertIn('chain-released-chain.json',files)
    def test_uncertain_later_submission_preserves_earlier_held_jobs_without_release(self):
        launched,released,files=self.exercise(fail_at=1)
        self.assertEqual(len(launched),2);self.assertEqual(released,[]);self.assertNotIn('chain-held-chain.json',files)
        self.assertIn(name(OPERATIONS[1])+'-submission.json',files)
if __name__=='__main__':unittest.main()
