"""Fresh complete-service producer and exact source/upstream verification."""
import os,sys,time
from pathlib import Path
from research_v80.io import require,read,json_read,info
from research_v82.selection import select
from research_v101.config import OLD_PROGRAM,OLD_SHA,TARGET_FILES
from research_v100.config import ROOT,RUN,ADMISSION,PROFILES,ORDER,TRIALS,design
from research_v100.contracts import contract,budget
from research_v100.records import transaction_writer
from research_v100.gate import verify as verify_gate
from research_v90.worker_control import run_limited
from src.run_store import canonical_json,digest

def sha(path):return read(path,retain=False)['sha256']
def bound(e,retain=True):return read(e['path'],{k:e[k] for k in ('bytes','sha256')},retain=retain)
def command(plan):return [sys.executable,'-B',str(RUN/'research_v100/worker.py'),str(plan)]

def load_records(p):
    from research_v80 import campaign as historical
    old=json_read(OLD_PROGRAM);require(info(canonical_json(old))['sha256']==OLD_SHA,'Historical input registry differs')
    rows,prov=historical.load_records(old);rows,prov,selection=select(rows,prov)
    for profile in PROFILES:
        e=p['admitted_targets'][profile]
        require(bound(e['records.json'])==canonical_json(dict(records=rows)) and bound(e['selection.json'])==canonical_json(selection),
            'Actual admitted matched source rows differ')
    return rows,prov

def prerequisites(p):
    from research_v80 import campaign as historical
    b=p['target_terminal'];require(b['path']==str(RUN/'gates/target-admission-terminal.json'),'Fixed actual gate path required')
    gate,admission,close=verify_gate(b['path'],{k:b[k] for k in ('bytes','sha256')})
    require(gate==p['target_gate'] and admission['checkpoint_paths']==p['checkpoint_paths'],'Actual upstream target gate differs')
    require(set(p['admitted_targets'])==set(PROFILES),'Both admitted target profiles required')
    for profile in PROFILES:
        c=close['seal_audit']['models'][profile];entries=p['admitted_targets'][profile]
        require(set(entries)==set(TARGET_FILES),'Complete admitted artifact census required')
        for name,e in entries.items():
            require(e==dict(path=str(ADMISSION/profile/'outputs'/name),**{k:c['artifacts'][name][k] for k in ('bytes','sha256')}),
                'Actual target binding differs')
            bound(e,retain=False)
    old=json_read(OLD_PROGRAM);require(info(canonical_json(old))['sha256']==OLD_SHA,'Historical input registry changed')
    historical.verify_bindings(old);historical.verify_inputs(old);load_records(p)
    return gate

def verify(program=RUN/'program.json',*,prerequisite=True,registered=True):
    require(Path(program).absolute()==RUN/'program.json','Literal new complete matched program required')
    p=json_read(program);expected=info(canonical_json(p))['sha256']
    require(all(p.get(k)==v for k,v in design().items()),'Unchanged matched design required')
    if registered:require(json_read(RUN/'registration.json')==dict(program_sha256=expected),'New matched registration required')
    require(p['source_count']==len(p['sources']) and p['source_inventory']==info(canonical_json(p['sources']))
        and json_read(RUN/'inventory.json')==p['sources'],'Exact source census required')
    for name,e in p['sources'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Relative source binding required')
        read(RUN/name,e,maximum=64*2**20,retain=False)
    from research_v100.software import SUITES
    require(p['software_suites']=={k:dict(modules=v[0],tests=v[1]) for k,v in SUITES.items()}
        and p['expected_tests']==sum(v[1] for v in SUITES.values()),'Exact Linux gate census required')
    if prerequisite:prerequisites(p)
    return p

def run(trial,p,expected):
    tick=time.perf_counter_ns();before=time.process_time_ns()
    require(trial in TRIALS,'Known new matched trial required')
    for prior in ORDER[:ORDER.index(trial)]:
        require(json_read(RUN/prior/'transaction.json')['worker_outcome']['status']=='complete'
            and json_read(RUN/prior/'outputs/completion.json')['status']=='complete','Prior actual worker failed; no retry')
    c=contract(trial,expected,os.environ['SLURM_JOB_ID'],min(os.sched_getaffinity(0)))
    folder=RUN/trial;folder.mkdir(parents=True,exist_ok=False);records=transaction_writer(folder)
    records.write('plan.json',c['plan']);ledger=budget(p,expected)
    receipt=run_limited(c['command'],c['worker_root'],c['limits'],identity=c['identity'],cwd=c['cwd'],phase_budget=ledger,phase='feasibility')
    records.write('transaction.json',dict(worker_outcome=receipt['outcome'],budget=ledger.snapshot(),
        elapsed_ns=time.perf_counter_ns()-tick,controller_process_cpu_ns=time.process_time_ns()-before,
        slurm_job_id=c['plan']['slurm_job_id'],clock_scope='Dispatch through sealed outcome/ledger; host clock also includes source/gate checks and final writes'))
    require(receipt['outcome']['status']=='complete' and receipt['outcome']['returncode']==0,'New matched worker failed; no retry')
