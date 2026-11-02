"""Actual tiny canonical states and failure before feature acquisition."""
from contextlib import ExitStack,redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research_v61 import worker
from research_v61.campaign import bind
from research_v61.test_state import BUDGET,record
from src.run_store import canonical_json,digest,strict_json

BIG=replace(BUDGET,max_tokens=32,max_sources=16)


def fixture_program(root):
    rows=[dict(id=f'r{i:02d}',tokens=[2*i+1,2*i+2]) for i in range(13)]
    return dict(directory=str(root),normalization=26,records=rows,retained_counts=[12,6],
        record_provenance={r['id']:json.loads(record(r['id'],r['tokens']).provenance) for r in rows},
        sources={},shared_checkpoint_bytes=123,inputs={})


def write_plan(root,program,trial):
    (root/'program.json').write_bytes(canonical_json(program))
    path=root/trial;path.mkdir()
    plan=dict(trial=trial,program=str(root/'program.json'),program_sha256=worker.sha(root/'program.json'),
        output=str(path/'outputs'),slurm_job_id='fixture')
    (path/'plan.json').write_bytes(canonical_json(plan));return path/'plan.json'


class WorkerTests(unittest.TestCase):
    def test_actual_successive_states_and_final_quality_bytes_match_fresh_oracle(self):
        from research_v61.test_service import FixtureService
        with tempfile.TemporaryDirectory() as temporary,ExitStack() as stack:
            root=Path(temporary).resolve();program=fixture_program(root)
            for target in ('research_v61.test_service.BUDGET','research_v61.test_state.BUDGET'):
                stack.enter_context(patch(target,BIG))
            stack.enter_context(patch.dict(worker.os.environ,{'SLURM_JOB_ID':'fixture'}))
            stack.enter_context(patch.object(worker,'ROOT',root));stack.enter_context(patch.object(worker,'Service',FixtureService))
            stack.enter_context(patch.object(worker,'verify',return_value=program))
            admitted=stack.enter_context(patch.object(worker,'verify_command_admission'))
            stack.enter_context(redirect_stdout(io.StringIO()))
            service=FixtureService(None,26,program['record_provenance'])
            from research_v61.service import telemetry
            timing=telemetry();retained=program['records'][-6:]
            values=service.extract(retained,timing)
            codes,_=service.solve(retained,'lossless',{},{},{},timing,direct_values=values)
            for name,blob in (('v59_base_target',service.bound.anchor_payload),
                ('v59_candidate_target',canonical_json(strict_json(service.bound.fixed_payload)['calibration_target'])),
                ('v59_candidate_model',worker.model_blob(codes))):
                path=root/name;path.write_bytes(blob);program['inputs'][name]=bind(path)
            for trial in ('prepare','cached','compressed','hybrid','cold','oracle'):
                plan=write_plan(root,program,trial);worker._main(plan,{'backend':'fixture'})
                admitted.assert_called_with(worker.sha(root/'program.json'),'feasibility',
                    [worker.sys.executable,'-B','-m','research_v61.worker',str(plan)])
            for arm,representation in (('cached','lossless'),('compressed','compressed48'),('hybrid','hybrid_gram'),('cold','lossless')):
                result=json.loads((root/arm/'outputs/completion.json').read_bytes())
                self.assertEqual([len(r['deleted_ids']) for r in result['steps']],[1,6])
                self.assertEqual([len(r['retained_ids']) for r in result['steps']],[12,6])
                self.assertTrue(result['v59_final_model_actual_bytes_equal'])
                for step in (1,2):
                    self.assertEqual((root/arm/f'outputs/step-{step}-state.bin').read_bytes(),
                        (root/'oracle'/f'outputs/step-{step}-{representation}.bin').read_bytes())
            self.assertEqual([r['timing']['neural_stage_record_pairs'] for r in json.loads((root/'hybrid/outputs/completion.json').read_bytes())['steps']],[2,12])

    def test_failed_admission_records_failure_without_feature_extraction(self):
        class Refused:
            load_ns=0;provenance=b'{}';extracted=False
            def __init__(self,*args):pass
            def admit(self,*args):raise ValueError('fixture shape refusal')
            def extract(self,*args):type(self).extracted=True;raise AssertionError('features opened')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();p=fixture_program(root);plan=write_plan(root,p,'prepare')
            with patch.dict(worker.os.environ,{'SLURM_JOB_ID':'fixture'}),patch.object(worker,'verify',return_value=p), \
                 patch.object(worker,'Service',Refused),patch.object(worker,'bind_service_reference',return_value={}), \
                 patch.object(worker,'verify_command_admission'):
                with self.assertRaisesRegex(ValueError,'fixture shape refusal'):worker._main(plan,{'backend':'fixture'})
            result=strict_json((root/'prepare/outputs/completion.json').read_bytes())
            self.assertEqual(result['status'],'failed');self.assertFalse(result['complete_model'])
            self.assertTrue(result['partial_artifacts_are_not_a_committed_complete_model']);self.assertFalse(Refused.extracted)

    def test_literal_plan_and_command_admission_precede_service_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();p=fixture_program(root);plan=write_plan(root,p,'prepare')
            with patch.dict(worker.os.environ,{'SLURM_JOB_ID':'different-job'}),patch.object(worker,'verify',return_value=p), \
                 patch.object(worker,'Service') as service:
                with self.assertRaisesRegex(ValueError,'Literal worker plan'):worker._main(plan,{})
                service.assert_not_called()
            with patch.dict(worker.os.environ,{'SLURM_JOB_ID':'fixture'}),patch.object(worker,'verify',return_value=p), \
                 patch.object(worker,'Service') as service,patch.object(worker,'verify_command_admission',side_effect=ValueError('not admitted')):
                with self.assertRaisesRegex(ValueError,'not admitted'):worker._main(plan,{})
                service.assert_not_called()

    def test_final_model_comparison_uses_bytes_and_does_not_replace_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();path=root/'model.bin';path.write_bytes(b'passed')
            program=dict(retained_counts=[12,6],inputs={'v59_candidate_model':dict(path=str(path),bytes=6,sha256=digest(b'passed'))})
            self.assertFalse(worker.check_final_model(b'other',program,12))
            self.assertTrue(worker.check_final_model(b'passed',program,6))
            with self.assertRaisesRegex(ValueError,'actual bytes differ'):worker.check_final_model(b'failed',program,6)
            self.assertEqual(path.read_bytes(),b'passed')


if __name__=='__main__':unittest.main()
