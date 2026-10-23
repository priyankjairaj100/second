"""Prepared finite admission controller. No registration or launch occurs on import."""
import datetime,gc,json,os,platform,resource,signal,sys,time,traceback,unittest
from pathlib import Path
if __name__=='__main__':
    root=Path('/nfs_home/users/poonam/second-20261010');run=Path(__file__).resolve().parents[1]
    sys.path[:0]=[str(run),str(root/'local_runs/lossless-control-v63-20261016-a/deps'),str(root)]
from research_v80.io import require,read,json_read,write
from research_v80 import campaign as historical
from research_v82.selection import SEED,select
from research_v82.fetch import fetch_checkpoint
from research_v82.target_worker import ROOT,RUN,V80_PROGRAM,V80_SHA,V81_RUN,V81_SHA
from research_v81.profile import PROFILES,PROPOSED_GRID_CAP
from src.run_store import canonical_json,digest
from src.worker_control import WorkerLimits,run_limited
from src.phase_budget import PhaseBudget

DESIGN=dict(schema='matched-transfer-admission-v82',selection_seed=SEED,profiles=PROFILES,
    grid_allowance=PROPOSED_GRID_CAP,grid_allowance_user_approved=True,numerical_checkout='f900999fcb200509dfad4fc081ce9c87fd172a16',
    target_cpu_seconds=600,target_wall_seconds=900,target_phase_cpu_seconds=1204,
    process_memory_bytes=16*2**30,file_size_bytes=2*2**30,threads=1,host='csis.mn1',
    automatic_retry=False,neural_execution=False,calibration_execution=False,
    order=['checks','fetch','distilgpt2','gpt2','close'],expected_software_tests=12,
    checkpoint_paths={'distilgpt2':str(ROOT/'tmp/models/distilgpt2'),'gpt2':str(RUN/'checkpoint/gpt2')},
    controller_process_cpu_soft_seconds=300,controller_process_cpu_hard_seconds=902,
    controller_cpu_allowance_seconds=1510,software_aggregate_cpu_seconds=602,
    grid_approval_text='Approve the transfer-only grid allowance')

def verify(expected,operation):
    raw=read(RUN/'program.json');require(digest(raw)==expected,'Program commitment differs');p=json_read(RUN/'program.json')
    require(all(p.get(k)==v for k,v in DESIGN.items()),'Exact admission design differs')
    require(json_read(RUN/'registration.json')==dict(program_sha256=expected),'Registration missing/different')
    for name,e in p['new_sources'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Relative source path required');read(RUN/name,e,retain=False)
    old=read(V80_PROGRAM);require(digest(old)==V80_SHA,'Historical program differs')
    old=json.loads(old);historical.verify_bindings(old);historical.verify_inputs(old)
    q=json.loads(read(V81_RUN/'completion.json',p['v81_completion']))
    require(q['status']=='complete' and q['error'] is None and q['program_sha256']==V81_SHA and q['job_id']=='15917','Completed V81 software required')
    report=json.loads(read(V81_RUN/'outputs/transfer-results.json',q['outputs']['outputs/transfer-results.json']))
    require(report['suites']=={k:dict(tests=n,failures=0,errors=0,skipped=0) for k,n in {'legacy':44,'four_cell_integration':5,'profiles':4,'full_geometry_archives':5,'service_guards':4}.items()},'V81 test census differs')
    for earlier in DESIGN['order'][:DESIGN['order'].index(operation)]:
        c=json_read(RUN/(earlier+'-completion.json'))
        require(c['status']=='complete' and c['error'] is None and c['program_sha256']==expected,'Earlier admission step failed/missing; no retry')
    return p,old

def budget(expected,p):return PhaseBudget(RUN/'budget',identity=dict(program_sha256=expected,sources_sha256=digest(canonical_json(p['new_sources']))),phase_cpu_seconds={'admission':1204})

def admit_target(profile,p,expected):
    attempt=RUN/profile;attempt.mkdir(exist_ok=False)
    plan=dict(profile=profile,program=str(RUN/'program.json'),program_sha256=expected,output=str(attempt/'outputs'),slurm_job_id=os.environ['SLURM_JOB_ID'])
    write(attempt/'plan.json',plan)
    receipt=run_limited([sys.executable,'-B',str(RUN/'research_v82/target_worker.py'),str(attempt/'plan.json')],attempt/'worker',
        WorkerLimits(cpu_seconds=600,wall_seconds=900,address_space_bytes=16*2**30,file_size_bytes=2*2**30,threads=1,affinity_cpus=(min(os.sched_getaffinity(0)),)),
        identity=dict(program_sha256=expected,profile=profile),cwd=ROOT,phase_budget=budget(expected,p),phase='admission')
    write(attempt/'transaction.json',dict(worker_outcome=receipt['outcome'],budget=budget(expected,p).snapshot(),slurm_job_id=plan['slurm_job_id']))
    require(receipt['outcome']['status']=='complete','Target admission failed; preserve one-use result')
    return json_read(attempt/'outputs/completion.json')

def close(p,expected):
    snap=budget(expected,p).snapshot();require(len(snap['attempts'])==2 and not any(snap['over_cap'].values())
        and all(x['state']=='settled' for x in snap['attempts'].values()),'Exactly two settled target attempts required')
    models={};selection=None
    for profile in PROFILES:
        d=RUN/profile/'outputs';c=json_read(d/'completion.json')
        require(c['status']=='complete' and c['program_sha256']==expected and c['profile']==profile,'Target admission receipt differs')
        require(c['stage_count']==4*PROFILES[profile]['blocks'] and c['code_count']==7077888*PROFILES[profile]['blocks']
            and c['grid_allowance']==PROPOSED_GRID_CAP,'Complete target extent differs')
        for name,e in c['artifacts'].items():read(d/name,{k:e[k] for k in ('bytes','sha256')},32*2**20,retain=False)
        s=json_read(d/'selection.json');require(selection is None or selection==s,'Matched source selection differs');selection=s
        models[profile]=c
    # This is a preliminary admission closure. It does not replace independent
    # target-byte review, full worker seal/debit verification or host accounting.
    return dict(status='admitted_pending_host_and_sealed_receipt_review',models=models,selection=selection,budget=snap,
        empirical_transfer=False,neural_execution=False,quality_evaluation=False)

def main(operation,expected):
    require(sys.platform=='linux' and platform.node()==DESIGN['host'] and os.environ.get('SLURM_JOB_ID','').isdigit(),'Pinned Linux Slurm entry required')
    require(operation in DESIGN['order'] and Path(__file__).resolve()==RUN/'research_v82/controller.py','Fixed one-use controller required')
    resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(2*2**30,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_CPU,(300,902))
    signal.signal(signal.SIGXCPU,lambda *unused:(_ for _ in ()).throw(RuntimeError('Controller CPU cap exceeded')))
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):require(os.environ.get(key)=='1','Single-thread environment required')
    start=time.perf_counter_ns();cpu=time.process_time_ns();prior=resource.getrusage(resource.RUSAGE_CHILDREN)
    write(RUN/(operation+'-start.json'),dict(job_id=os.environ['SLURM_JOB_ID'],operation=operation,program_sha256=expected,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    error=None;result=None
    try:
        p,old=verify(expected,operation)
        if operation=='checks':
            tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(['research_v82.test_inputs','research_v82.test_admission']))
            require(tests.testsRun==12 and tests.wasSuccessful() and not tests.skipped,'Exact software gate failed')
            result=dict(tests=12,failures=0,errors=0,skipped=0)
        elif operation=='fetch':result=fetch_checkpoint(RUN/'checkpoint/gpt2')
        elif operation in PROFILES:result=admit_target(operation,p,expected)
        else:result=close(p,expected)
    except BaseException as exc:
        # Fetch errors may carry signed HTTP redirect URLs. Keep only the type.
        error=dict(type=type(exc).__name__)
        if operation!='fetch':error['message']=str(exc);traceback.print_exc()
    child=resource.getrusage(resource.RUSAGE_CHILDREN);own=time.process_time_ns()-cpu
    child_ns=round((child.ru_utime+child.ru_stime-prior.ru_utime-prior.ru_stime)*1e9)
    if own>301*10**9:error=dict(type='ControllerCPUExceeded')
    if operation=='checks' and own+child_ns>602*10**9:error=dict(type='SoftwareCPUExceeded')
    write(RUN/(operation+'-completion.json'),dict(status='complete' if error is None else 'failed',error=error,result=result,operation=operation,
        program_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],process_cpu_ns=own,waited_child_cpu_ns=child_ns,
        elapsed_ns=time.perf_counter_ns()-start,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        final_host_accounting_and_sealed_review_required=True))
    require(error is None,'One-use admission step failed; do not retry')
if __name__=='__main__':main(*sys.argv[1:])
