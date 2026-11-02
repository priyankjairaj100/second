"""Prepared actual child-module admission wiring; no real checkpoint is opened."""
import os,sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from contextlib import ExitStack
from research_v91.contracts import target_contract,budget
from research_v91.config import design
from src.run_store import canonical_json,digest

@unittest.skipUnless(sys.platform=='linux','Pinned Linux gate required')
class TargetWiring(unittest.TestCase):
    def test_actual_target_import_has_defined_admission(self):
        from research_v91 import target_worker
        self.assertTrue(callable(target_worker.admit))
    def exercise(self,with_admission):
        from research_v91 import target_worker as worker
        with TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();sha='a'*64;p=dict(design(),sources={'fixture.py':dict(bytes=3,sha256='b'*64)})
            c=target_contract('gpt2',sha,'54321',min(os.sched_getaffinity(0)),root=root,cwd=root)
            ledger=budget(p,sha,root=root)
            binding=dict(schema='limited-worker-identity-v1',identity=c['identity'],command=c['command'],cwd=str(root),
                limits=c['limits'].payload(),phase_budget=dict(binding_sha256=ledger.identity_digest,phase='admission',directory=str(ledger.root)))
            attempt=digest(canonical_json(dict(worker=binding,attempt=str(c['worker_root']/'attempt-0001'))))
            ledger.reserve('admission',attempt,602)
            env=dict(SLURM_JOB_ID='54321')
            if with_admission:env['CALIBRATION_PHASE_CPU_ADMISSION']=canonical_json(dict(
                phase_budget_root=str(ledger.root),phase_budget_binding_sha256=ledger.identity_digest,attempt_id=attempt,
                phase='admission',command=c['command'],cwd=str(root))).decode()
            stack.enter_context(patch.dict(os.environ,env,clear=True))
            for name,value in [('RUN',root),('ROOT',root),('__file__',str(root/'research_v91/target_worker.py'))]:stack.enter_context(patch.object(worker,name,value))
            stack.enter_context(patch.object(worker.platform,'node',return_value='csis.mn1'))
            stack.enter_context(patch.object(worker,'json_read',return_value=c['plan']))
            stack.enter_context(patch.object(worker,'target_contract',return_value=c))
            stack.enter_context(patch.object(worker.protocol,'program',return_value=p))
            stack.enter_context(patch.object(worker.protocol,'allocation'))
            stack.enter_context(patch.object(worker.protocol,'earlier'))
            prerequisite=stack.enter_context(patch.object(worker.protocol,'prerequisites',side_effect=ValueError('reached real prerequisite boundary')))
            constructor=stack.enter_context(patch.object(worker,'MatchedService'))
            message='reached real prerequisite boundary' if with_admission else 'Active bounded CPU admission'
            before=(ledger.root/'ledger.json').read_bytes()
            with self.assertRaisesRegex(ValueError,message):worker.load_plan(root/'gpt2/plan.json')
            self.assertEqual(before,(ledger.root/'ledger.json').read_bytes());constructor.assert_not_called()
            self.assertEqual(prerequisite.call_count,int(with_admission))
    def test_actual_target_loader_accepts_matching_live_ledger_before_upstream(self):self.exercise(True)
    def test_missing_admission_stops_before_upstream_and_model(self):self.exercise(False)

if __name__=='__main__':unittest.main()
