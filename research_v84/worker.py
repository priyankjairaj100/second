"""Unregistered matched worker; actual admission and exact-source Linux gate required."""
import sys
from pathlib import Path
if __name__=='__main__':
    root=Path('/nfs_home/users/poonam/second-20261010');run=Path(__file__).resolve().parents[1]
    prior={n:root/'local_runs'/name for n,name in [(63,'lossless-control-v63-20261016-a'),(64,'modern-service-checks-v64-20261016-a'),(65,'disjoint-data-v65-20261016-a'),(66,'complete-service-checks-v66-20261016-a')]}
    sys.path[:0]=[str(prior[63]/'deps'),str(run),*[str(prior[n]) for n in [66,65,64,63]],str(root)]
import gc,os,resource,time,traceback
from research_v84 import campaign as c
from research_v84.config import RUN,ROOT,ORDER,TRIALS,CELLS,trial_parts,predecessor,expected_artifacts
ARTIFACT_LIMIT=2**30
from research_v80.io import require,read,json_read,write,info
from research_v81.operations import REPRESENTATIONS,ARM_REPRESENTATION as BASE_REPRESENTATION,rebuild,request
from research_v79.implementation import execution
from research_v81.service import MatchedService
ARM_REPRESENTATION={cell:BASE_REPRESENTATION[arm] for cell,arm in CELLS.items()}
from src.run_store import canonical_json,digest,strict_json
from src.transaction_timing import verify_command_admission

def _main(plan_path):
    plan_path=Path(plan_path).absolute();plan=json_read(plan_path);p=c.verify(Path(plan['program']))
    trial=plan['trial'];profile,local=trial_parts(trial);require(trial in TRIALS and plan_path==RUN/trial/'plan.json'
        and plan==dict(trial=trial,program=str(RUN/'program.json'),program_sha256=c.sha(RUN/'program.json'),
            output=str(RUN/trial/'outputs'),slurm_job_id=os.environ.get('SLURM_JOB_ID')),'Literal worker plan/job differs')
    verify_command_admission(plan['program_sha256'],'feasibility',c.command(plan_path))
    out=Path(plan['output']);out.mkdir(parents=True,exist_ok=False);start=time.perf_counter_ns()
    result=dict(schema='matched-complete-service-worker-v84',trial=trial,profile=profile,status='running',complete_model=False,
        program_sha256=plan['program_sha256'],slurm_job_id=plan['slurm_job_id'],artifacts={},
        source_files_sha256=digest(canonical_json(p['sources'])),
        confirmation=False,quality_evaluation=False,os_cache_uncontrolled=True,affinity_cpus=sorted(os.sched_getaffinity(0)))
    def persist(name,blob):
        require(name not in result['artifacts'] and name in expected_artifacts(trial),'Unknown/duplicate declared output')
        e=write(out/name,blob,raw=True,maximum=ARTIFACT_LIMIT);e['file']=name;result['artifacts'][name]=e
        return e
    def writer(prefix=''):
        def call(name,blob):
            e=persist(prefix+name,blob);return dict(e,file=name)
        return call
    def mark(phase,**fields):
        item=dict(phase=phase,elapsed_ns=time.perf_counter_ns()-start,**{k:v for k,v in fields.items() if k not in ['admission','solver','elapsed_ns']})
        print(canonical_json(item).decode(),flush=True)
        write(out/f'progress-{mark.count:04d}.json',item);mark.count+=1
    mark.count=0
    service=None
    try:
        cell='reference_modern' if local in ('prepare','oracle') else local.rsplit('-',1)[0]
        with execution(cell) as implementation:
            result['implementation']=implementation
            result['shared_primal_kernel']=implementation['primal']
            try:
                records,provenance=c.load_records(p)
                service=MatchedService(Path(p['checkpoint_paths'][profile]),profile,provenance,mark,allow_proposed_grid_cap=True)
                admitted=p['admitted_targets'][profile]
                base=c.bound(admitted['anchor-target.json']);calibration=c.bound(admitted['calibration-target.json'])
                service_target=c.bound(admitted['service-target.json']);service_sha=digest(service_target);calibration_sha=digest(calibration)
                require(service.bound.anchor_payload==base and service.bound.fixed_payload==service_target
                    and canonical_json(strict_json(service.bound.fixed_payload)['calibration_target'])==calibration
                    and service.bound.calibration_target_sha256==calibration_sha,'Actual numerical teacher/target differs')
                result.update(context_elapsed_ns=service.load_ns,execution_provenance_sha256=digest(service.provenance),
                    service_target_sha256=service_sha,calibration_target_sha256=calibration_sha,base_target_sha256=digest(base))
                persist('execution-provenance.json',service.provenance)
                admissions=[dict(retained=n,representation=rep,**service.admit(records[-n:],rep))
                    for n in [4,3,2] for rep in REPRESENTATIONS]
                persist('admission.json',canonical_json(admissions))
                if local=='prepare':result['preparation']=rebuild(service,records,writer())
                elif local=='oracle':
                    result['steps']=[]
                    for step,n in enumerate(p['retained_counts'],1):
                        tick=time.perf_counter_ns();fresh=rebuild(service,records[-n:],writer(f'step-{step}/'))
                        result['steps'].append(dict(step=step,retained_ids=[r['id'] for r in records[-n:]],
                            oracle_elapsed_ns=time.perf_counter_ns()-tick,**fresh))
                else:
                    cell,step=local.rsplit('-',1);arm=CELLS[cell];step=int(step);retained=p['retained_counts'][step-1]
                    prior_count=4 if step==1 else p['retained_counts'][step-2]
                    def read_predecessor():
                        require(arm!='cold','Cold cannot open predecessor')
                        prior,state,trust=predecessor(trial);directory=RUN/prior/'outputs'
                        completion=json_read(directory/'completion.json')
                        require(completion['status']=='complete' and completion['program_sha256']==plan['program_sha256'],'Complete bound predecessor required')
                        return tuple(read(directory/name,{k:completion['artifacts'][name][k] for k in ['bytes','sha256']},ARTIFACT_LIMIT) for name in [state,trust])
                    result['request']=request(service,records[-prior_count:],records[-retained:],arm,read_predecessor,writer())
                require(set(result['artifacts'])==expected_artifacts(trial),'Complete artifact census differs')
                results=[result['preparation']] if local=='prepare' else result['steps'] if local=='oracle' else [result['request']]
                require(all(r['code_count']==p['code_counts'][profile] for r in results),'Complete matched model code extent differs')
            finally:
                service=None
                gc.collect()
        result.update(status='complete',complete_model=True)
    except BaseException as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc());raise
    finally:
        usage=resource.getrusage(resource.RUSAGE_SELF)
        result.update(worker_elapsed_ns=time.perf_counter_ns()-start,process_cpu_seconds=usage.ru_utime+usage.ru_stime,max_rss_kib=usage.ru_maxrss,
            partial_artifacts_are_not_a_committed_complete_model=result['status']!='complete',
            clock_scope='Worker timer starts after source/runtime/input and CPU-admission verification; controller clock and sealed CPU include those checks, final completion write and shutdown; worker clock includes native setup, context, all service work, fsync, disposal and cache clear')
        write(out/'completion.json',result)

_CONSUMED=False

def main(path):
    global _CONSUMED
    if _CONSUMED:raise RuntimeError('One complete service worker per fresh process')
    _CONSUMED=True
    return _main(path)

if __name__=='__main__':main(sys.argv[1])
