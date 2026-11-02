"""Prepared fresh-process actual target admission; no neural feature extraction.

A separate V91 registry and actual successful V89 closure are required.
This file cannot admit a bare command or run against a local Mac checkpoint.
"""
import gc,json,os,platform,resource,sys,time,traceback
from pathlib import Path
if __name__=='__main__':
    root=Path('/nfs_home/users/poonam/second-20261010');run=Path(__file__).resolve().parents[1]
    sys.path[:0]=[str(run),str(root/'local_runs/lossless-control-v63-20261016-a/deps'),str(root)]
from research_v80.io import require,read,json_read,write,info
from research_v80 import campaign as historical
from research_v79.implementation import execution
from research_v81.service import MatchedService
from research_v81.profile import PROFILES,PROPOSED_GRID_CAP,validate_geometry
from research_v81.resource_review import review
from research_v81.operations import REPRESENTATIONS
from research_v82.selection import select,SEED
from research_v91 import protocol
from research_v91.contracts import target_contract, admit
from research_v91.records import target_writer
from research_v91.config import ROOT, RUN, TARGET_FILES
from src.run_store import canonical_json,digest,strict_json

_CONSUMED=False

def load_plan(path):
    require(sys.platform=='linux' and platform.node()=='csis.mn1' and os.environ.get('SLURM_JOB_ID','').isdigit(),'Pinned Linux Slurm execution required')
    require(Path(__file__).resolve()==RUN/'research_v91/target_worker.py','Literal fresh target child required')
    plan=json_read(path);profile=plan['profile']
    require(profile in PROFILES and Path(path).absolute()==RUN/profile/'plan.json','Registered profile plan path required')
    expected=plan['program_sha256']
    p=protocol.program(expected)
    contract=target_contract(profile,expected,os.environ['SLURM_JOB_ID'],min(os.sched_getaffinity(0)))
    require(plan==contract['plan'],'Literal worker plan/job differs')
    # Verify the actual live reservation before checkpoint construction or upstream reopening.
    admit(contract,p,expected)
    protocol.allocation(profile,expected,plan['slurm_job_id']);protocol.earlier(profile,expected)
    _,rows,prov=protocol.prerequisites(p)
    checkpoint=Path(p['checkpoint_paths'][profile])
    for name,h in PROFILES[profile]['checkpoint_files'].items():
        require(read(checkpoint/name,retain=False)['sha256']==h,'Actual model input differs')
    if profile=='gpt2':
        from research_v91.fetch import verify_fetch
        verify_fetch(checkpoint)
    return plan,p,checkpoint,select(rows,prov)

def main(path):
    global _CONSUMED
    require(not _CONSUMED,'Fresh target-admission process required');_CONSUMED=True
    plan,p,checkpoint,(rows,prov,selection)=load_plan(path)
    out=Path(plan['output']);out.mkdir(parents=True,exist_ok=False);start=time.perf_counter_ns()
    result=dict(schema='actual-matched-target-admission-v91',status='running',profile=plan['profile'],program_sha256=plan['program_sha256'],
        job_id=plan['slurm_job_id'],neural_execution=False,calibration_execution=False,request_benchmark=False,quality_evaluation=False,artifacts={})
    records=target_writer(out)
    def save(name,blob):
        require(name in TARGET_FILES and name not in result['artifacts'],'Fixed target artifact census required')
        value=strict_json(blob);require(canonical_json(value)==blob,'Canonical target payload required')
        result['artifacts'][name]=records.write(name,value)
    service=None
    try:
        with execution('reference_modern') as implementation:
            try:
                service=MatchedService(checkpoint,plan['profile'],prov,allow_proposed_grid_cap=True)
                require(validate_geometry(service.base.payload(),plan['profile'])==plan['profile'],'Actual checkpoint profile differs')
                require(service.base.recipe.max_grid_entries==PROPOSED_GRID_CAP,'Both new targets require exact approved allowance')
                save('records.json',canonical_json(dict(records=rows)))
                save('selection.json',canonical_json(selection))
                save('anchor-target.json',service.bound.anchor_payload);save('service-target.json',service.bound.fixed_payload)
                save('calibration-target.json',canonical_json(service.target.calibration_target.payload()))
                save('execution-provenance.json',service.provenance)
                save('structural-admission.json',canonical_json(review(service.bound.anchor_payload)))
                reports=[dict(retained=n,representation=rep,**service.admit(rows[-n:],rep)) for n in (4,3,2) for rep in REPRESENTATIONS]
                save('actual-admission.json',canonical_json(dict(reports=reports)))
                result.update(stage_count=len(service.target.stages),code_count=sum(s.rows*s.width for s in service.bound.stages),
                    base_target_sha256=digest(service.bound.anchor_payload),service_target_sha256=digest(service.bound.fixed_payload),
                    calibration_target_sha256=service.bound.calibration_target_sha256,grid_allowance=PROPOSED_GRID_CAP,
                    checkpoint_files=PROFILES[plan['profile']]['checkpoint_files'])
            finally:
                service=None;gc.collect()
        require(implementation['closed'],'Context cleanup required')
        result.update(status='complete',implementation=implementation)
    except BaseException as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc());raise
    finally:
        u=resource.getrusage(resource.RUSAGE_SELF)
        result.update(elapsed_ns=time.perf_counter_ns()-start,process_cpu_seconds=u.ru_utime+u.ru_stime,max_rss_kib=u.ru_maxrss,
            clock_scope='Worker target/cleanup interval; sealed controller/CPU clocks additionally include prior input verification and final receipt write')
        records.write('completion.json',result)

if __name__=='__main__':main(sys.argv[1])
