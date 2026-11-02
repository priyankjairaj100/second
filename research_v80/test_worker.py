"""Actual files and canonical states with synthetic features/codes, not evidence."""
from contextlib import ExitStack,redirect_stdout,contextmanager
from dataclasses import replace
import io,json
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from research_v80 import worker,config,audit
from research_v80.io import write,info,json_read
from research_v61.test_service import FixtureService
from research_v61.test_worker import fixture_program
from research_v61.test_state import BUDGET
from research_v63 import archive,codec
from research_v66.operations import MODERN
from src.run_store import canonical_json,digest,strict_json

BIG=replace(BUDGET,max_tokens=32,max_sources=16)

class Fixture(FixtureService):
    """Canonical modern codec around generated features; no numerical solver."""
    def prepare_payloads(self,rows,values,representation,timing):
        if representation!=MODERN:return super().prepare_payloads(rows,values,representation,timing)
        payloads={}
        for stage in self.bound.stages:
            for r in self.records(rows):
                payloads[stage.stage_id,r.record_id]=codec.serialize(codec.encode_factor(values[stage.stage_id,r.record_id],
                    target_sha256=digest(self.bound.fixed_payload),anchor_target_sha256=digest(self.bound.anchor_payload),
                    record_id=r.record_id,token_sha256=r.token_sha256,stage_id=stage.stage_id))
        return payloads,{},{}
    def serialize(self,rows,codes,representation,payloads,grams,trust,timing):
        if representation==MODERN:return archive.pack(self.bound,self.records(rows),codes,payloads)
        return super().serialize(rows,codes,representation,payloads,grams,trust,timing)

def plan(root,p,trial):
    path=root/trial/'plan.json'
    write(path,dict(trial=trial,program=str(root/'program.json'),program_sha256=digest((root/'program.json').read_bytes()),output=str(root/trial/'outputs'),slurm_job_id='123'))
    return path

def setup_fixture(root,stack):
    p=fixture_program(root);p['trial_order']=config.ORDER;p['inputs']={}
    service=Fixture(None,26,p['record_provenance'])
    for k,b in [('base_target',service.bound.anchor_payload),('calibration_target',canonical_json(strict_json(service.bound.fixed_payload)['calibration_target']))]:
        write(root/k,b,raw=True);p['inputs'][k]=dict(path=str(root/k),**info(b))
    p['new_sources']={}
    write(root/'program.json',p)
    for target in ['research_v61.test_service.BUDGET','research_v61.test_state.BUDGET']:stack.enter_context(patch(target,BIG))
    stack.enter_context(patch.dict(worker.os.environ,SLURM_JOB_ID='123'))
    stack.enter_context(patch.object(worker.os,'sched_getaffinity',return_value={0},create=True))
    stack.enter_context(patch.object(worker,'ROOT',root));stack.enter_context(patch.object(worker,'RUN',root))
    stack.enter_context(patch.object(worker.c,'RUN',root));stack.enter_context(patch.object(worker.c,'verify',return_value=p))
    stack.enter_context(patch.object(worker.c,'load_records',return_value=(p['records'],p['record_provenance'])))
    stack.enter_context(patch.object(worker,'IntegratedService',Fixture))
    @contextmanager
    def fixture_execution(cell):
        metadata=dict(cell=cell,primal={'fixture':True},closed=False)
        try:yield metadata
        finally:metadata['closed']=True
    stack.enter_context(patch.object(worker,'execution',side_effect=fixture_execution))
    stack.enter_context(patch.object(worker,'SERVICE_TARGET',digest(service.bound.fixed_payload)))
    stack.enter_context(patch.object(worker,'CALIBRATION_TARGET',service.bound.calibration_target_sha256))
    stack.enter_context(patch.object(worker,'verify_command_admission'))
    stack.enter_context(redirect_stdout(io.StringIO()))
    return p,service

class WorkerTests(unittest.TestCase):
    def test_ten_file_workers_and_eight_fresh_state_comparisons(self):
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            root=Path(folder).resolve();p,service=setup_fixture(root,stack)
            for trial in config.ORDER:worker._main(plan(root,p,trial))
            completions={t:json_read(root/t/'outputs/completion.json') for t in config.ORDER}
            for arm,rep in worker.ARM_REPRESENTATION.items():
                for step in [1,2]:
                    self.assertEqual((root/(arm+'-'+str(step))/'outputs/state.bin').read_bytes(),(root/'oracle/outputs'/f'step-{step}'/(rep+'-state.bin')).read_bytes())
                    self.assertEqual((root/(arm+'-'+str(step))/'outputs/model.bin').read_bytes(),(root/'oracle/outputs'/f'step-{step}/model.bin').read_bytes())
            with patch.object(audit,'gram_budget',return_value=BIG),patch.object(audit,'SERVICE_TARGET',digest(service.bound.fixed_payload)),patch.object(audit,'execution_matches_target'):
                checked=audit.verify_states(root,p,completions,audit.AuditInputs(),expected_stages=2,expected_codes=8)
            self.assertEqual(len(checked['comparisons']),8)
            # Byte corruption cannot be accepted from the old success receipt.
            path=root/'optimized_modern-2/outputs/model.bin';path.write_bytes(b'x'+path.read_bytes()[1:])
            with patch.object(audit,'gram_budget',return_value=BIG),patch.object(audit,'SERVICE_TARGET',digest(service.bound.fixed_payload)),patch.object(audit,'execution_matches_target'):
                with self.assertRaises(ValueError):audit.verify_states(root,p,completions,audit.AuditInputs(),expected_stages=2,expected_codes=8)

    def test_oracle_does_not_open_preparation_or_request_outputs(self):
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            root=Path(folder).resolve();p,_=setup_fixture(root,stack)
            # No preparation/request output directory exists.
            worker._main(plan(root,p,'oracle'))
            self.assertTrue(json_read(root/'oracle/outputs/completion.json')['complete_model'])
            self.assertFalse((root/'prepare').exists())

    def test_missing_live_cpu_admission_prevents_context_creation(self):
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            root=Path(folder).resolve();p,_=setup_fixture(root,stack)
            with patch.object(worker,'verify_command_admission',side_effect=ValueError('not admitted')),patch.object(worker,'IntegratedService') as factory:
                with self.assertRaisesRegex(ValueError,'not admitted'):worker._main(plan(root,p,'prepare'))
                factory.assert_not_called()

    def test_failed_writer_preserves_failure_receipt(self):
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            root=Path(folder).resolve();p,_=setup_fixture(root,stack);original=worker.write
            def fail(path,*args,**kwargs):
                if Path(path).name=='model.bin':raise OSError('fixture write failure')
                return original(path,*args,**kwargs)
            with patch.object(worker,'write',side_effect=fail):
                with self.assertRaisesRegex(OSError,'fixture write failure'):worker._main(plan(root,p,'prepare'))
            result=json_read(root/'prepare/outputs/completion.json')
            self.assertEqual(result['status'],'failed');self.assertFalse(result['complete_model'])
            self.assertTrue(result['partial_artifacts_are_not_a_committed_complete_model'])

    def test_wrong_job_plan_is_rejected_before_context(self):
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            root=Path(folder).resolve();p,_=setup_fixture(root,stack);path=plan(root,p,'prepare')
            with patch.dict(worker.os.environ,SLURM_JOB_ID='999'),patch.object(worker,'IntegratedService') as factory:
                with self.assertRaises(ValueError):worker._main(path)
                factory.assert_not_called()

if __name__=='__main__':unittest.main()
