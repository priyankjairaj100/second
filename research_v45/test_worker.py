"""Actual canonical state fixtures for a one-then-six deletion sequence."""
from contextlib import ExitStack,redirect_stdout
from dataclasses import replace
import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from research_v43.test_service import FixtureService
from research_v43.test_state import BUDGET,record
from research_v43.state import validate_state
from research_v45 import worker
from src.run_store import canonical_json

BIG=replace(BUDGET,max_tokens=32,max_sources=16)
class ScaleWorkerTests(unittest.TestCase):
    def test_actual_successors_and_six_source_gram_subtraction_match_fresh_oracle(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root=Path(folder);rows=[dict(id=f'r{i:02d}',tokens=[2*i+1,2*i+2]) for i in range(13)]
            program=dict(directory=str(root),normalization=26,records=rows,retained_counts=[12,6],
                record_provenance={r['id']:json.loads(record(r['id'],r['tokens']).provenance) for r in rows},
                sources={},shared_checkpoint_bytes=123)
            (root/'program.json').write_bytes(canonical_json(program))
            for target in ('research_v43.test_service.BUDGET','research_v43.test_state.BUDGET'):stack.enter_context(patch(target,BIG))
            stack.enter_context(patch.object(worker,'ROOT',root));stack.enter_context(patch.object(worker,'Service',FixtureService))
            stack.enter_context(patch.object(worker,'verify',return_value=program));checker=stack.enter_context(patch.object(worker,'verify_command_admission'))
            stack.enter_context(redirect_stdout(io.StringIO()))
            for trial in ('prepare','cached','compressed','hybrid','cold','oracle'):
                path=root/trial;path.mkdir();plan=dict(trial=trial,program=str(root/'program.json'),
                    program_sha256=worker.sha(root/'program.json'),output=str(path/'outputs'),slurm_job_id='fixture')
                (path/'plan.json').write_bytes(canonical_json(plan));worker.main(path/'plan.json')
                checker.assert_called_with(plan['program_sha256'],'feasibility',[worker.sys.executable,'-B','-m','research_v45.worker',str(path/'plan.json')])
            for arm,representation in (('cached','lossless'),('compressed','compressed40'),('hybrid','hybrid_gram'),('cold','lossless')):
                result=json.loads((root/arm/'outputs/completion.json').read_bytes())
                self.assertEqual([len(r['deleted_ids']) for r in result['steps']],[1,6])
                self.assertEqual([len(r['retained_ids']) for r in result['steps']],[12,6])
                for step in (1,2):
                    actual=(root/arm/f'outputs/step-{step}-state.bin').read_bytes()
                    fresh=(root/'oracle'/f'outputs/step-{step}-{representation}.bin').read_bytes()
                    self.assertEqual(actual,fresh)
            self.assertEqual([r['timing']['neural_stage_record_pairs'] for r in json.loads((root/'hybrid/outputs/completion.json').read_bytes())['steps']],[2,12])

    def test_shape_admission_covers_every_stage_and_fallback(self):
        from research_v45.resource_review import review
        report=review();self.assertEqual(len(report['requests']),9)
        for request in report['requests']:
            self.assertEqual(len(request['stages']),24)
            self.assertTrue(all(s['admitted'] for s in request['stages']))
        self.assertEqual(report['gram_budget']['max_sources'],13)
