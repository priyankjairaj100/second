"""Prepared fresh-process actual target admission; no neural feature extraction.

A future separately registered V82 controller and passed V81 are required.
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
from research_v82.prerequisite import verify as verify_upstream
from src.run_store import canonical_json,digest,strict_json
from src.worker_control import verify_command_admission
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/matched-transfer-admission-v82-20261023-a'
V80_PROGRAM=ROOT/'local_runs/four-cell-service-v80-20261023-a/program.json'
V80_SHA='89f6a71e5b4f74b667bac64149c77005862d36b2b2e3dedc2a7260fb05c0ad60'
V81_RUN=ROOT/'local_runs/transfer-software-v81-20261023-a'
V81_SHA='3f89d3c73c21d9d955c9396d6cfbe8150ad98793088f2cca7c6ba5c88c8e5ada'
_CONSUMED=False

def load_plan(path):
    require(sys.platform=='linux' and platform.node()=='csis.mn1' and os.environ.get('SLURM_JOB_ID','').isdigit(),'Pinned Linux Slurm execution required')
    plan=json_read(path);profile=plan['profile']
    require(profile in PROFILES and Path(path).absolute()==RUN/profile/'plan.json','Registered profile plan path required')
    require(plan==dict(profile=profile,program=str(RUN/'program.json'),program_sha256=plan['program_sha256'],
        output=str(RUN/profile/'outputs'),slurm_job_id=os.environ['SLURM_JOB_ID']),'Literal worker plan/job differs')
    verify_command_admission(plan['program_sha256'],'admission',[sys.executable,'-B',str(RUN/'research_v82/target_worker.py'),str(Path(path).absolute())])
    raw=read(plan['program']);require(digest(raw)==plan['program_sha256'],'Program hash differs');p=strict_json(raw)
    require(json_read(RUN/'registration.json')==dict(program_sha256=plan['program_sha256']),'Registered program commitment required')
    require(p['schema']=='matched-transfer-admission-v82' and p['selection_seed']==SEED and p['profiles']==PROFILES
        and p['grid_allowance']==PROPOSED_GRID_CAP and p['grid_allowance_user_approved'] is True,'Frozen new target design differs')
    for name,e in p['new_sources'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Relative source path required');read(RUN/name,e,retain=False)
    old_raw=read(V80_PROGRAM);require(digest(old_raw)==V80_SHA,'Historical input registry differs');old=strict_json(old_raw)
    historical.verify_bindings(old);rows,prov=historical.verify_inputs(old)
    verify_upstream(RUN)
    checkpoint=ROOT/'tmp/models/distilgpt2' if profile=='distilgpt2' else RUN/'checkpoint/gpt2'
    require(p['checkpoint_paths'][profile]==str(checkpoint),'Pinned checkpoint location differs')
    for name,h in PROFILES[profile]['checkpoint_files'].items():require(read(checkpoint/name,retain=False)['sha256']==h,'Actual model input differs')
    if profile=='gpt2':
        fetch=json.loads(read(checkpoint/'fetch-receipt.json'))
        require(fetch['status']=='complete' and fetch['revision']=='607a30d783dfa663caf39e06633721c8d4cfcd7e','Successful immutable public fetch required')
    return plan,p,checkpoint,select(rows,prov)

def main(path):
    global _CONSUMED
    require(not _CONSUMED,'Fresh target-admission process required');_CONSUMED=True
    plan,p,checkpoint,(rows,prov,selection)=load_plan(path)
    out=Path(plan['output']);out.mkdir(parents=True,exist_ok=False);start=time.perf_counter_ns()
    result=dict(schema='actual-matched-target-admission-v82',status='running',profile=plan['profile'],program_sha256=plan['program_sha256'],
        job_id=plan['slurm_job_id'],neural_execution=False,calibration_execution=False,request_benchmark=False,quality_evaluation=False,artifacts={})
    def save(name,blob):result['artifacts'][name]=write(out/name,blob,raw=True,maximum=32*2**20)
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
        write(out/'completion.json',result)

if __name__=='__main__':main(sys.argv[1])
