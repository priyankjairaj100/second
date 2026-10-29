"""Actual exclusive intent files with simulated Slurm responses; no submissions."""
from contextlib import ExitStack,redirect_stdout
import hashlib,io,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from research_v89 import submit

def fixture(root,stack):
    p=dict(numerical_checkout='f900999',sources={},prior_sources={},new_sources={},dependency_files={},historical_ledgers={},inputs={},expected_tests=84,trial_order=['prepare','oracle'],trials={t:dict(wall_seconds=100) for t in ['prepare','oracle']},primary_audit_caps=dict(wall=100),supplemental_audit_caps=dict(wall=100))
    raw=json.dumps(p,sort_keys=True,separators=(',',':')).encode();(root/'program.json').write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
    submitted={};released=[]
    def run(args,**kwargs):
        if args[0]=='sbatch':
            job=str(1000+len(submitted));submitted[job]=args;return SimpleNamespace(returncode=0,stdout=job+'\n',stderr='')
        if args[:2]==['scontrol','release']:released.append(args[2]);return SimpleNamespace(returncode=0)
        raise AssertionError(args)
    def call(args):
        if args[0]=='git':return 'f900999' if 'rev-parse' in args else ''
        if args[0]=='squeue':return ''
        if args[0]=='sacct':return '1000|COMPLETED|0:0'
        if args[:3]==['scontrol','show','job']:
            command=submitted[args[3]];options=dict(a[2:].split('=',1) for a in command if a.startswith('--') and '=' in a)
            return 'JobState=PENDING JobName='+options['job-name']+' NumCPUs=1 Requeue=0 MinMemoryNode=16G ReqNodeList=csis.mn1 TimeLimit='+options['time']+' Priority=0 Reason=JobHeldUser Dependency='+options.get('dependency','(null)')
        raise AssertionError(args)
    stack.enter_context(patch.object(submit,'RUN',root));stack.enter_context(patch.object(submit,'ROOT',root));stack.enter_context(patch.object(submit,'__file__',str(root/'research_v89/submit.py')))
    stack.enter_context(patch.object(submit,'design',return_value={}))
    stack.enter_context(patch.object(submit,'verify_failure_bindings'))
    stack.enter_context(patch.object(submit,'terminal_disposition'))
    stack.enter_context(patch.object(submit,'admit',return_value=({}, {}, {})))
    stack.enter_context(patch.object(submit,'call',side_effect=call));stack.enter_context(patch.object(submit.subprocess,'run',side_effect=run));stack.enter_context(redirect_stdout(io.StringIO()))
    return p,sha,submitted,released

class SubmitFlow(unittest.TestCase):
    def test_checks_then_finite_chain_have_distinct_intents_and_no_trial_directory_collision(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p,sha,submitted,released=fixture(root,stack);submit.main('checks',sha)
            self.assertEqual(released,['1000']);self.assertTrue((root/'checks-chain-intent.json').is_file());self.assertTrue((root/'checks-intent.json').is_file())
            (root/'software-completion.json').write_text(json.dumps(dict(status='complete',error=None,program_sha256=sha,tests=84,errors=0,failures=0,skipped=0,empirical_execution=False,job_id='1000',container_storage_mapping=dict(status='matched_host_devices_and_new_file_groups'))))
            (root/'checks-host.json').write_text(json.dumps(dict(status='complete',error=None,program_sha256=sha,job_id='1000',accounting=dict(nonnumerical_cpu_ns=100))))
            submit.main('chain',sha);self.assertEqual(len(submitted),5);self.assertEqual(len(released),5)
            self.assertFalse((root/'prepare').exists());self.assertFalse((root/'oracle').exists())
            self.assertEqual(json.loads((root/'oracle-submission.json').read_text())['arguments'],['oracle'])
    def test_consumed_registration_never_submits_again(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p,sha,submitted,released=fixture(root,stack);submit.main('checks',sha)
            with self.assertRaises(FileExistsError):submit.main('checks',sha)
            self.assertEqual(len(submitted),1)
    def test_storage_refusal_leaves_no_registration_or_submission(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p,sha,submitted,released=fixture(root,stack)
            with patch.object(submit,'admit',side_effect=ValueError('quota exhausted')):
                with self.assertRaisesRegex(ValueError,'quota'):submit.main('checks',sha)
            self.assertFalse((root/'registration.json').exists());self.assertFalse(submitted);self.assertFalse(released)

    def test_unknown_submission_outcome_preserves_intent_and_never_releases(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p,sha,submitted,released=fixture(root,stack)
            with patch.object(submit.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='uncertain')):
                with self.assertRaisesRegex(ValueError,'Uncertain submission'):submit.main('checks',sha)
            self.assertTrue((root/'checks-intent.json').exists());self.assertTrue((root/'registration.json').exists());self.assertFalse(released)

    def test_wrong_held_constraints_leave_all_jobs_held(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p,sha,submitted,released=fixture(root,stack)
            with patch.object(submit,'held_ok',return_value=False):
                with self.assertRaisesRegex(ValueError,'Held constraints'):submit.main('checks',sha)
            self.assertEqual(len(submitted),1);self.assertFalse(released)

if __name__=='__main__':unittest.main()

