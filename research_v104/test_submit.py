"""New launcher refusal boundaries; scheduler calls are local fakes only."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from research_v104 import submit
from research_v104.config import design
from research_v104.records import writer


def snapshot(name='checks',dependency=None):
    return ('JobState=PENDING JobName=second104-'+submit.operation_name(name)+' NumCPUs=1 Requeue=0 MinMemoryNode=16G ReqNodeList=csis.mn1 '
        'TimeLimit='+submit.clock(name)+' Partition=cpu-short QOS=cpu-short Reason=JobHeldUser Priority=0 Dependency='+
        ('(null)' if dependency is None else 'afterok:'+dependency))

class Submit(unittest.TestCase):
    def test_exact_held_resources_and_dependency(self):
        self.assertTrue(submit.held_ok(snapshot(),'checks',None))
        self.assertTrue(submit.held_ok(snapshot('distilgpt2/prepare','7'),'distilgpt2/prepare','7'))
        for old,new in [('NumCPUs=1','NumCPUs=2'),('MinMemoryNode=16G','MinMemoryNode=32G'),('Requeue=0','Requeue=1'),
            ('QOS=cpu-short','QOS=other'),('Dependency=(null)','Dependency=afterok:7')]:
            self.assertFalse(submit.held_ok(snapshot().replace(old,new),'checks',None))
    def exercise(self,response,held=None):
        with TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p=design();sha='a'*64
            stack.enter_context(patch.object(submit,'RUN',root));stack.enter_context(patch.object(submit,'__file__',str(root/'research_v104/submit.py')))
            stack.enter_context(patch.object(submit.campaign,'verify',return_value=p));stack.enter_context(patch.object(submit,'inspect_upstream'))
            stack.enter_context(patch.object(submit.campaign,'sha',return_value=sha))
            stack.enter_context(patch.object(submit,'admit',return_value=({}, {}, {})))
            stack.enter_context(patch.object(submit,'writer',side_effect=lambda:writer(root)))
            def fake_call(args):
                if 'rev-parse' in args:return p['numerical_checkout']
                if args[0]=='scontrol':return snapshot() if held is None else held
                return ''
            stack.enter_context(patch.object(submit,'call',side_effect=fake_call))
            launches=[]
            def fake_run(args,**kwargs):
                launches.append(args)
                return SimpleNamespace(returncode=0,stdout=response,stderr='')
            stack.enter_context(patch.object(submit.subprocess,'run',side_effect=fake_run))
            if response.strip().isdigit() and held is None:submit.main('checks',sha)
            else:
                with self.assertRaises(ValueError):submit.main('checks',sha)
            with self.assertRaisesRegex(ValueError,'consumed'):submit.main('checks',sha)
            return launches,{f.name:f.read_bytes() for f in root.iterdir()}
    def test_ambiguous_submission_never_retries(self):
        calls,files=self.exercise('uncertain acknowledgement')
        self.assertEqual(len(calls),1);self.assertIn('checks-response.json',files);self.assertNotIn('checks-held-chain.json',files)
    def test_bad_held_constraints_never_release(self):
        calls,files=self.exercise('76543',snapshot().replace('NumCPUs=1','NumCPUs=2'))
        self.assertEqual(len(calls),1);self.assertIn('checks-submission.json',files);self.assertNotIn('checks-release.json',files)
    def test_verified_held_job_released_exactly_once(self):
        calls,files=self.exercise('76543')
        self.assertEqual([c[0] for c in calls],['sbatch','scontrol']);self.assertEqual(calls[1],['scontrol','release','76543'])
        self.assertIn('checks-held-chain.json',files);self.assertIn('checks-released-chain.json',files)
if __name__=='__main__':unittest.main()
