"""Wrapper control-flow fixtures. No empirical worker is launched."""
from contextlib import redirect_stdout, redirect_stderr
import io
import subprocess
import unittest
from unittest.mock import patch

from scripts import continue_empirical_v32 as wrapper


class ContinueEmpiricalTests(unittest.TestCase):
    def main(self,args,side_effect):
        with patch.object(wrapper.sys,'argv',['wrapper',*args]), \
             patch.object(wrapper,'call',side_effect=side_effect) as calls,redirect_stdout(io.StringIO()):
            result=wrapper.main()
            return result,calls.call_args_list

    def test_status_is_default_and_never_registers_or_runs(self):
        result,calls=self.main(['--workspace','local_runs/replay-001'],
            lambda corpus,action,workspace:dict(corpus=corpus,registered=False))
        self.assertEqual(result,0)
        self.assertEqual([c.args for c in calls],[('wikitext','--status','local_runs/replay-001'),
            ('c4','--status','local_runs/replay-001')])

    def test_seven_trials_each_then_c4_and_no_budget_mutation(self):
        calls=[];registered=set();completed={'wikitext':0,'c4':0}
        def controller(corpus,action,workspace):
            calls.append((corpus,action,workspace))
            self.assertEqual(workspace,'local_runs/replay-001')
            if corpus=='c4':self.assertEqual(completed['wikitext'],7)
            if action=='--status':
                return dict(registered=corpus in registered,blocked=None,
                    complete=completed[corpus]==7,completed=list(range(completed[corpus])),
                    budget=dict(charged_cpu_seconds={'feasibility':completed[corpus]*10}))
            if action=='--register':registered.add(corpus);return dict(registered=True)
            self.assertEqual(action,'--run-next')
            completed[corpus]+=1
            return dict(status='complete',scientific_gates={'all_passed':False})
        result,_=self.main(['--workspace','local_runs/replay-001','--execute'],controller)
        self.assertEqual(result,0)
        self.assertEqual(completed,{'wikitext':7,'c4':7})
        self.assertEqual(sum(action=='--register' for _,action,_ in calls),2)
        self.assertEqual(sum(action=='--run-next' for _,action,_ in calls),14)
        self.assertTrue(all(action in ('--status','--register','--run-next') for _,action,_ in calls))

    def test_blocked_trial_stops_without_run_retry_or_c4(self):
        calls=[]
        def controller(corpus,action,workspace):
            calls.append((corpus,action))
            return dict(registered=True,blocked={'id':'failed-repair'},complete=False)
        with self.assertRaisesRegex(RuntimeError,'Existing trial is blocked'):
            self.main(['--execute'],controller)
        self.assertEqual(calls,[('wikitext','--status'),('wikitext','--status')])

    def test_failed_trial_status_stops_without_retry_or_c4(self):
        calls=[]
        def controller(corpus,action,workspace):
            calls.append((corpus,action))
            if action=='--status':return dict(registered=True,blocked=None,complete=False)
            return dict(status='failed')
        with self.assertRaisesRegex(RuntimeError,'no automatic retry'):
            self.main(['--execute'],controller)
        self.assertEqual(calls,[('wikitext','--status'),('wikitext','--status'),('wikitext','--run-next')])

    def test_controller_exception_stops_without_second_attempt(self):
        calls=[]
        def controller(corpus,action,workspace):
            calls.append((corpus,action))
            if action=='--run-next':raise RuntimeError('controller failed')
            return dict(registered=True,blocked=None,complete=False)
        with self.assertRaisesRegex(RuntimeError,'controller failed'):
            self.main(['--execute'],controller)
        self.assertEqual(sum(action=='--run-next' for _,action in calls),1)
        self.assertFalse(any(corpus=='c4' for corpus,_ in calls))

    def test_completed_existing_roots_do_not_register_or_run(self):
        def controller(corpus,action,workspace):
            return dict(registered=True,complete=True,blocked=None,completed=list(range(7)),budget={})
        result,calls=self.main(['--execute'],controller)
        self.assertEqual(result,0)
        self.assertTrue(all(c.args[1]=='--status' for c in calls))

    def test_fixed_iteration_guard_stops_unexpected_controller(self):
        calls=[]
        def controller(corpus,action,workspace):
            calls.append((corpus,action))
            return dict(status='complete') if action=='--run-next' else dict(registered=True,blocked=None,complete=False)
        with self.assertRaisesRegex(RuntimeError,'Unexpected trial count'):
            self.main(['--execute'],controller)
        self.assertEqual(sum(action=='--run-next' for _,action in calls),8)
        self.assertFalse(any(corpus=='c4' for corpus,_ in calls))

    def test_call_preserves_literal_controller_args_without_budget_options(self):
        result=subprocess.CompletedProcess([],0,stdout='{"complete":true}',stderr='')
        with patch.object(wrapper.subprocess,'run',return_value=result) as run:
            self.assertEqual(wrapper.call('c4','--run-next','local_runs/replay-001'),{'complete':True})
            args=run.call_args
            self.assertEqual(args.args[0],[wrapper.sys.executable,str(wrapper.CONTROLLER),'--corpus','c4',
                '--run-next','--workspace','local_runs/replay-001'])
            self.assertEqual(args.kwargs,dict(cwd=wrapper.ROOT,text=True,capture_output=True))

    def test_nonzero_controller_exit_is_reported_and_not_retried(self):
        result=subprocess.CompletedProcess([],1,stdout='partial evidence\n',stderr='refused\n')
        out,err=io.StringIO(),io.StringIO()
        with patch.object(wrapper.subprocess,'run',return_value=result) as run,redirect_stdout(out),redirect_stderr(err):
            with self.assertRaisesRegex(RuntimeError,'do not retry automatically'):
                wrapper.call('wikitext','--run-next',None)
            self.assertEqual(run.call_count,1)
        self.assertIn('partial evidence',out.getvalue());self.assertIn('refused',err.getvalue())


if __name__=='__main__':unittest.main()
