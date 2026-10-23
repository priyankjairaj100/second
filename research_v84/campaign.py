"""Prospective one-use matched controller. Requires separately bound real gates."""
import json,os,sys,time
from pathlib import Path
from research_v84.config import ROOT,RUN,ADMISSION,ADMISSION_SHA,PROFILES,TRIALS,ORDER,CAP,design
from research_v80.io import require,read,json_read,write
from research_v80 import campaign as historical
from research_v82.selection import select
from research_v81.profile import PROFILES as MODEL_PROFILES
from src.run_store import canonical_json,digest
from src.worker_control import WorkerLimits,run_limited
from src.phase_budget import PhaseBudget

V80_PROGRAM=ROOT/'local_runs/four-cell-service-v80-20261023-a/program.json'
V80_SHA='89f6a71e5b4f74b667bac64149c77005862d36b2b2e3dedc2a7260fb05c0ad60'
TERMINAL_SHAS={'v80':V80_SHA,'v81':'3f89d3c73c21d9d955c9396d6cfbe8150ad98793088f2cca7c6ba5c88c8e5ada','v82':ADMISSION_SHA}
ARTIFACTS={'records.json','selection.json','anchor-target.json','service-target.json','calibration-target.json','execution-provenance.json','structural-admission.json','actual-admission.json'}

def sha(path):return read(path,retain=False)['sha256']
def bound(e,retain=True):return read(e['path'],{k:e[k] for k in ('bytes','sha256')},retain=retain)
def load_records(p):
    old=json_read(V80_PROGRAM);rows,prov=historical.load_records(old)
    rows,prov,selection=select(rows,prov)
    for profile in PROFILES:
        entries=p['admitted_targets'][profile]
        require(bound(entries['records.json'])==canonical_json(dict(records=rows)) and bound(entries['selection.json'])==canonical_json(selection),'Actual admitted matched source rows differ')
    return rows,prov

def verify(program=RUN/'program.json',*,software=True):
    require(Path(program).absolute()==RUN/'program.json','Literal new matched registry required')
    p=json_read(program);require(all(p.get(k)==v for k,v in design().items()),'Prospective complete matched design differs')
    require(json_read(RUN/'registration.json')==dict(program_sha256=sha(program)),'Separate new registration required')
    require(len(p['sources'])==p['source_count'],'Complete matched source census required')
    for name,e in p['sources'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Relative package source required');read(RUN/name,e,retain=False)
    require(sha(V80_PROGRAM)==V80_SHA,'Historical source/input registry differs')
    old=json_read(V80_PROGRAM);historical.verify_bindings(old);historical.verify_inputs(old)
    require(sha(ADMISSION/'program.json')==ADMISSION_SHA,'Actual target admission registry differs')
    require(set(p['terminal_gates'])==set(TERMINAL_SHAS),'Every actually closed prerequisite required')
    for version,e in p['terminal_gates'].items():
        require(Path(e['path'])==RUN/'gates'/(version+'-terminal.json'),'Literal uploaded terminal gate path required')
        report=json.loads(bound(e))
        require(report['status']=='verified' and report['kind']==version and report['program_sha256']==TERMINAL_SHAS[version],'Actual completed host terminal prerequisite differs')
        # Reopen the exact actual completion/audit bytes named by the host report.
        for path,raw in report['payloads'].items():
            if path.endswith(('-audit.json','-completion.json','/completion.json')):require(read(path)==raw.encode('utf8'),'Terminal prerequisite input changed')
    require(set(p['admitted_targets'])==set(PROFILES),'Both admitted complete profiles required')
    for profile,entries in p['admitted_targets'].items():
        require(set(entries)==ARTIFACTS,'Complete admitted target artifact census required')
        for name,e in entries.items():
            require(Path(e['path'])==ADMISSION/profile/'outputs'/name,'Fixed admitted output path required');bound(e,retain=False)
        require(p['checkpoint_paths'][profile]==str(ROOT/'tmp/models/distilgpt2' if profile=='distilgpt2' else ADMISSION/'checkpoint/gpt2'),'Literal checkpoint path differs')
        for name,h in MODEL_PROFILES[profile]['checkpoint_files'].items():require(sha(Path(p['checkpoint_paths'][profile])/name)==h,'Complete actual checkpoint bytes differ')
    load_records(p)
    if software:
        gate=json_read(RUN/'software-completion.json')
        require(gate['status']=='complete' and gate['error'] is None and gate['program_sha256']==sha(program)
            and gate['tests']==p['expected_tests'] and gate['errors']==gate['failures']==gate['skipped']==0,'Passed exact-source Linux gate required')
    return p

def command(plan):return [sys.executable,'-B',str(RUN/'research_v84/worker.py'),str(plan)]
def budget(p):return PhaseBudget(RUN/'budget',identity=dict(program_sha256=sha(RUN/'program.json'),sources_sha256=digest(canonical_json(p['sources']))),phase_cpu_seconds={'feasibility':CAP})

def run(trial):
    require(sys.platform=='linux' and os.environ.get('SLURM_JOB_ID','').isdigit(),'Pinned Slurm controller required')
    tick=time.perf_counter_ns();cpu=time.process_time_ns();p=verify();require(trial in TRIALS,'Registered matched trial required')
    for previous in ORDER[:ORDER.index(trial)]:
        require(json_read(RUN/previous/'transaction.json')['worker_outcome']['status']=='complete'
            and json_read(RUN/previous/'outputs/completion.json')['status']=='complete','Earlier matched trial failed or missing; no retry')
    attempt=RUN/trial;attempt.mkdir(parents=True,exist_ok=False)
    plan=dict(trial=trial,program=str(RUN/'program.json'),program_sha256=sha(RUN/'program.json'),output=str(attempt/'outputs'),slurm_job_id=os.environ['SLURM_JOB_ID'])
    write(attempt/'plan.json',plan)
    receipt=run_limited(command(attempt/'plan.json'),attempt/'worker',WorkerLimits(**TRIALS[trial],address_space_bytes=16*2**30,file_size_bytes=2*2**30,threads=1,affinity_cpus=(min(os.sched_getaffinity(0)),)),identity=dict(program_sha256=plan['program_sha256'],trial=trial),cwd=ROOT,phase_budget=budget(p),phase='feasibility')
    write(attempt/'transaction.json',dict(worker_outcome=receipt['outcome'],budget=budget(p).snapshot(),elapsed_ns=time.perf_counter_ns()-tick,controller_process_cpu_ns=time.process_time_ns()-cpu,slurm_job_id=plan['slurm_job_id'],clock_scope='Complete controller verification/setup, worker, sealing and ledger snapshot; scheduler additionally includes final write and shutdown'))
    require(receipt['outcome']['status']=='complete','One-use matched trial failed; preserve all partial outputs')
