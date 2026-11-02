"""Actual one-use token-stage diagnostic; selected-stage result only."""
import sys
from pathlib import Path
if __name__=='__main__':
    root=Path('/nfs_home/users/poonam/second-20261010');run=Path(__file__).resolve().parents[1]
    sys.path[:0]=[str(root/'local_runs/lossless-control-v63-20261016-a/deps'),str(run),str(root)]
import gc,os,time,traceback
from research_v109 import campaign as c,protocol
from research_v109.config import RUN,PARENT,STAGE
from research_v109.contracts import contract,admit
from research_v109.stage import select_stage,decode_points,solve_token
from research_v80.io import require,read,json_read,write
from research_v79.implementation import execution
from research_v81.service import MatchedService
from research_v61.state import validate_state
from src.ordered_finite import FiniteWeights
from research_v43.dispatcher import StageSpec
from src.run_store import canonical_json,digest


def main(plan_path):
    require(Path(plan_path)==RUN/'diagnostic/plan.json','Literal diagnostic plan required')
    plan=json_read(plan_path);p=c.verify(prerequisite=False);expected=c.sha(RUN/'program.json')
    actual=contract('diagnostic',expected,os.environ['SLURM_JOB_ID'],min(os.sched_getaffinity(0)))
    require(plan==actual['plan'],'Exact literal worker plan required');admit(actual,p,expected)
    protocol.allocation('diagnostic',expected,os.environ['SLURM_JOB_ID']);protocol.earlier('diagnostic',expected)
    old=c.prerequisites(p);out=RUN/'diagnostic/outputs';out.mkdir(exist_ok=False)
    result=dict(schema='token-stage-result-v109',program_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],
        stage_id=STAGE,status='running',complete_model=False,transfer_evidence=False,
        speed_comparison=False,original_streamed_route_executed=False,artifacts={})
    tick=time.perf_counter_ns()
    try:
        from research_v104.campaign import load_records
        rows,provenance=load_records(old)
        with execution('reference_modern') as implementation:
            service=MatchedService(Path(p['checkpoint_path']),'gpt2',provenance,allow_proposed_grid_cap=True)
            require(service.bound.anchor_payload==c.bound(p['admitted_target']['anchor-target.json'])
                and service.bound.fixed_payload==c.bound(p['admitted_target']['service-target.json']),
                'Actual reconstructed target differs')
            completion=json_read(PARENT/'gpt2/prepare/outputs/completion.json')
            require(completion['status']=='complete' and completion['complete_model'],'Original complete preparation required')
            e=completion['artifacts']['lossless-state.bin']
            blob=read(PARENT/'gpt2/prepare/outputs/lossless-state.bin',{k:e[k] for k in ('bytes','sha256')})
            state=validate_state(blob,expected_target=service.bound,expected_records=service.records(rows))
            require(state.representation=='lossless','Original point factors required')
            stage=select_stage(service.target.stages)
            points,identities=decode_points(stage,rows[-3:],state.source_map(),service.target.digest,service.base.digest)
            result.update(retained_ids=[r['id'] for r in rows[-3:]],point_identities=identities,
                preparation_lossless_state={k:e[k] for k in ('bytes','sha256')},target_sha256=service.target.digest,
                anchor_sha256=service.base.digest,implementation=implementation)
            del blob,state;gc.collect()
            spec=StageSpec.from_stage(stage,target_sha256=service.target.digest)
            weights=FiniteWeights(stage.weights).array();started=time.perf_counter_ns()
            answer,code=solve_token(spec,weights,points,policy=service.policy)
            result['solve_elapsed_ns']=time.perf_counter_ns()-started
            result['artifacts']['codes.bin']=write(out/'codes.bin',code.packed_indices,raw=True,maximum=2**20*2)
            from scripts.execute_gram_pilot_v35 import public_result
            result.update(status='certified_stage',route=answer.route,admission=answer.admission,
                solver=public_result(answer.solver_result),code_metadata=code.metadata(),
                certified_codes=code.rows*code.columns,exact_point_refinement_cap=16)
            del service,points,weights,answer,code;gc.collect()
    except BaseException as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        result['worker_elapsed_ns']=time.perf_counter_ns()-tick
        write(out/'completion.json',result,maximum=2**20)


if __name__=='__main__':main(sys.argv[1])
