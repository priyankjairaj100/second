"""Prepared Linux tiny actual-file integration, not empirical model evidence.

Different two/three-stage artificial targets exercise checkpoint isolation.
The separately registered V81 suite covers real24/48-stage archive geometry.
"""
from contextlib import ExitStack,contextmanager,redirect_stdout
from types import SimpleNamespace
from dataclasses import replace
import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from research_v92 import worker,config,state_audit
from research_v80.test_worker import Fixture
from research_v61.test_state import BUDGET,bind,fixture,record
from research_v61.postrun import Inputs
from research_v63 import archive
from research_v81 import operations
from research_v80.io import write,info,json_read
from src.run_store import canonical_json,digest,strict_json
from research_v90.outputs import inspect_outputs
from research_v90 import outputs as bounded_outputs
from research_v92.contracts import contract
BIG=replace(BUDGET,max_tokens=16,max_sources=4)
class MatchedFixture(Fixture):
    def __init__(self,checkpoint,profile,provenance,mark=lambda *a,**k:None,**options):
        super().__init__(checkpoint,8,provenance,mark)
        shapes=((2,3),(1,2)) if profile=='distilgpt2' else ((2,3),(1,2),(2,2))
        self.bound=bind(*fixture(shapes,original=8));self.target=SimpleNamespace(stages=self.bound.stages,digest=digest(self.bound.fixed_payload))
        self.provenance=canonical_json(dict(fixture=True,profile=profile));self.gram_budget=BIG

    def extract(self,rows,telemetry):
        result=super().extract(rows,telemetry)
        for r in rows:self.mark('source_replayed',record_id=r['id'])
        return result
    def solve(self,*args,**kwargs):
        mark=self.mark;self.mark=lambda *a,**k:None
        try:result=super().solve(*args,**kwargs)
        finally:self.mark=mark
        for stage in self.bound.stages:mark('stage_certified',stage_id=stage.stage_id)
        return result
    def prepare_payloads(self,*args,**kwargs):
        result=super().prepare_payloads(*args,**kwargs)
        for stage in self.bound.stages:self.mark('payload_stage',stage_id=stage.stage_id)
        return result

def setup(root,stack):
    rows=[dict(id=f'r{i}',tokens=[2*i+1,2*i+2]) for i in range(4)]
    prov={r['id']:json.loads(record(r['id'],r['tokens']).provenance) for r in rows}
    p=dict(config.design(),sources={},admitted_targets={},checkpoint_paths={},checkpoint_bytes={x:123 for x in config.PROFILES},stage_counts={'distilgpt2':2,'gpt2':3},code_counts={'distilgpt2':8,'gpt2':12})
    for profile in config.PROFILES:
        service=MatchedFixture(None,profile,prov);p['checkpoint_paths'][profile]=str(root/'checkpoint'/profile)
        p['admitted_targets'][profile]={}
        for name,blob in [('anchor-target.json',service.bound.anchor_payload),('service-target.json',service.bound.fixed_payload),('calibration-target.json',canonical_json(strict_json(service.bound.fixed_payload)['calibration_target']))]:
            path=root/'admitted'/profile/name;write(path,blob,raw=True);p['admitted_targets'][profile][name]=dict(path=str(path),**info(blob))
    write(root/'program.json',p)
    for module in ('research_v61.test_service','research_v61.test_state'):stack.enter_context(patch(module+'.BUDGET',BIG))
    stack.enter_context(patch.dict(worker.os.environ,SLURM_JOB_ID='123'));stack.enter_context(patch.object(worker.os,'sched_getaffinity',return_value={0},create=True))
    stack.enter_context(patch.object(worker,'RUN',root));stack.enter_context(patch.object(worker,'ROOT',root));stack.enter_context(patch.object(worker,'MatchedService',MatchedFixture))
    stack.enter_context(patch.object(worker.c,'RUN',root));stack.enter_context(patch.object(worker.c,'verify',return_value=p));stack.enter_context(patch.object(worker.c,'load_records',return_value=(rows,prov)))
    stack.enter_context(patch.object(worker,'admit'))
    stack.enter_context(patch.object(worker,'contract',side_effect=lambda t,s,j,a:contract(t,s,j,a,root=root,cwd=root)))
    stack.enter_context(patch.object(worker.c,'prerequisites'))
    stack.enter_context(patch.object(worker.protocol,'allocation'));stack.enter_context(patch.object(worker.protocol,'earlier'))
    stack.enter_context(patch.dict(bounded_outputs.STAGES,{'distilgpt2':2,'gpt2':3}))
    stack.enter_context(patch.dict(bounded_outputs.MODEL_BYTES,{'distilgpt2':4,'gpt2':6}));stack.enter_context(patch.object(operations,'archive',archive));stack.enter_context(patch.object(state_audit,'archive',archive))
    stack.enter_context(patch.object(state_audit,'gram_budget',return_value=BIG));stack.enter_context(patch.object(state_audit,'execution_matches_target'))
    @contextmanager
    def execution(cell):
        metadata=dict(cell=cell,primal={'fixture':True},closed=False)
        try:yield metadata
        finally:metadata['closed']=True
    stack.enter_context(patch.object(worker,'execution',side_effect=execution));stack.enter_context(redirect_stdout(io.StringIO()))
    return p

def plan(root,trial):
    path=root/trial/'plan.json';write(path,dict(trial=trial,program=str(root/'program.json'),program_sha256=digest((root/'program.json').read_bytes()),output=str(root/trial/'outputs'),slurm_job_id='123'));return path

class MatchedWorkers(unittest.TestCase):
    def test_twenty_workers_and_sixteen_same_checkpoint_oracle_pairs(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p=setup(root,stack)
            for trial in config.ORDER:worker._main(plan(root,trial))
            completions={t:json_read(root/t/'outputs/completion.json') for t in config.ORDER}
            for trial in config.ORDER:
                extent=inspect_outputs(root/trial/'outputs',trial)
                self.assertLessEqual(extent['output_bytes'],extent['allowance']['output_bytes'])
            for profile in config.PROFILES:
                result=state_audit.verify_profile(root,profile,p,completions,Inputs());self.assertEqual(len(result['comparisons']),8)
            # Different fixtures must not be compared as the same checkpoint.
            self.assertNotEqual((root/'distilgpt2/prepare/outputs/model.bin').read_bytes(),(root/'gpt2/prepare/outputs/model.bin').read_bytes())
            path=root/'gpt2/optimized_modern-2/outputs/model.bin';path.write_bytes((root/'distilgpt2/optimized_modern-2/outputs/model.bin').read_bytes())
            with self.assertRaises(ValueError):state_audit.verify_profile(root,'gpt2',p,completions,Inputs())
    def test_each_oracle_executes_without_opening_predecessors(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();setup(root,stack)
            for profile in config.PROFILES:
                worker._main(plan(root,profile+'/oracle'));self.assertFalse((root/profile/'prepare').exists())
    def test_wrong_actual_target_is_rejected_before_feature_extraction(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p=setup(root,stack);p['admitted_targets']['gpt2']=p['admitted_targets']['distilgpt2']
            with patch.object(MatchedFixture,'extract') as extract:
                with self.assertRaisesRegex(ValueError,'Actual numerical teacher/target'):worker._main(plan(root,'gpt2/prepare'))
                extract.assert_not_called()
    def test_missing_cpu_admission_prevents_checkpoint_constructor(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();setup(root,stack)
            with patch.object(worker,'admit',side_effect=ValueError('no admission')),patch.object(worker,'MatchedService') as factory:
                with self.assertRaisesRegex(ValueError,'no admission'):worker._main(plan(root,'gpt2/prepare'))
                factory.assert_not_called()
    def test_complete_extent_and_failed_output_are_not_promoted(self):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d).resolve();p=setup(root,stack);p['code_counts']['gpt2']=999
            with self.assertRaisesRegex(ValueError,'Complete matched model'):worker._main(plan(root,'gpt2/prepare'))
            result=json_read(root/'gpt2/prepare/outputs/completion.json');self.assertEqual(result['status'],'failed');self.assertFalse(result['complete_model'])
            self.assertTrue((root/'gpt2/prepare/outputs/model.bin').exists()) # Failed partial remains preserved
    def test_one_process_never_runs_twice_after_failure(self):
        with patch.object(worker,'_CONSUMED',False),patch.object(worker,'_main',side_effect=ValueError('fixture failure')) as run:
            with self.assertRaises(ValueError):worker.main('/unused')
            with self.assertRaisesRegex(RuntimeError,'fresh process'):worker.main('/unused')
            self.assertEqual(run.call_count,1)
if __name__=='__main__':unittest.main()
