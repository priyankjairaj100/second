"""Read-only audit of the first V34 worker's procfs startup failure.

Writes only a new report. Does not modify, retry, or recover the failed attempt.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.run_store import canonical_json, strict_json
from src.phase_budget import read_budget_snapshot
from scripts.analyze_full_service_v30 import verify_plan, verify_worker_schedule


def check(value,message):
    if not value:raise ValueError(message)


def raw(path):
    check(path.is_file() and not path.is_symlink(),'missing or unsafe file: '+str(path))
    return path.read_bytes()


def read(path):
    value=strict_json(raw(path));check(type(value) is dict,'expected JSON object');return value


def hashed(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def entry(path):return dict(bytes=path.stat().st_size,sha256=hashed(path))


def audit():
    start=time.process_time_ns();c=ROOT/'campaigns/independent_c4_v32';a=c/'attempts/c4-delete-0-repair'
    p=read(c/'program.json');q=read(c/'protocol.json');reg=read(c/'registration.json')
    ph,qh=hashed(c/'program.json'),hashed(c/'protocol.json')
    check(ph==q['program_sha256']==reg['program_sha256'] and qh==reg['protocol_sha256'],'registration differs')
    t=read(a/'transaction.json');r=read(a/'worker/result.json');identity=read(a/'worker/identity.json');plan=read(a/'plan.json')
    check(t['receipt_sha256']==hashed(a/'worker/result.json'),'receipt binding differs')
    check(r['status']=='complete','receipt not sealed')
    check(r['outcome']['status']=='failed' and r['outcome']['kind']=='nonzero_exit' and r['outcome']['returncode']==1,'unexpected outcome')
    check(t['worker_outcome']==r['outcome'],'transaction outcome differs')
    check(r['identity_sha256']==hashlib.sha256(canonical_json(identity)).hexdigest(),'identity digest differs')
    check(r['worker_identity']==identity['identity'] and identity['identity']['plan_sha256']==hashed(a/'plan.json'),'plan identity differs')
    inner=a/'worker'/r['attempt'];check(r['attempt']=='attempt-0001','unexpected attempt')
    for name,e in r['artifacts'].items():
        check(Path(name).name==name and entry(inner/name)==e,'receipt artifact differs: '+name)
    request=read(inner/'request.json')
    for key in ('command','cwd','limits'):check(request[key]==identity[key],'request differs: '+key)
    logs={name:read(inner/(name+'-summary.json')) for name in ('stdout','stderr')}
    for name,log in logs.items():
        check(log['bytes']<=log['tail_max_bytes'],'full log unavailable')
        encoded=log['tail_utf8'].encode();check(len(encoded)==log['bytes'] and hashlib.sha256(encoded).hexdigest()==log['sha256'],'stream digest differs')
    check("FileNotFoundError: [Errno 2] No such file or directory: '/proc/self/maps'" in logs['stderr']['tail_utf8'],'missing expected traceback')
    progress=read(a/'outputs/progress.json')
    check(progress['status']=='failed' and progress['error_type']=='FileNotFoundError' and progress['error']=="[Errno 2] No such file or directory: '/proc/self/maps'",'failure metadata differs')
    phases=[x['phase'] for x in progress['phases']]
    check(phases==['input_validation_started','inputs_verified','checkpoint_load_started','failed'],'unexpected work phases')
    check(progress['artifacts']=={} and 'complete_model' not in progress,'unexpected model artifact claim')
    check(raw(a/'outputs/progress.json')==raw(a/'sealed-progress.json'),'failed progress seal differs')
    check(sorted(x.name for x in (a/'outputs').iterdir())==['plan.json','progress.json'],'unexpected output exists')
    check(not (a/'outputs/completion.json').exists(),'completion must not exist')
    check(not (a/'outputs/model.bin').exists() and not (a/'outputs/state.bin').exists(),'model or state output must not exist')
    trial=next(x for x in p['trials'] if x['id']==a.name)
    parents={name:read(c/'attempts'/name/'outputs/completion.json') for name in ('c4-root-prepare','c4-delete-0-cold')}
    verify_plan(c,trial,plan,p,ph,qh,parents);verify_worker_schedule(c,trial,t,identity,reg,p)
    for name,e in p['source_sha256'].items():check(hashed(c/'source'/name)==e,'frozen source differs')
    debit=r['budget_debit'];cpu=debit['observed_cpu_ns']
    check(debit['state']=='settled' and cpu==6324538000 and debit['charged_cpu_seconds']==7 and debit['reserved_cpu_seconds']==182,'failure CPU debit differs')
    check(cpu==r['resource_usage']['total_cpu_ns'],'observed CPU differs')
    check(debit['charged_cpu_seconds']==max(1,(cpu+999999999)//1000000000),'CPU rounding differs')
    budget=read_budget_snapshot(c/'phase-cpu-budget',identity=dict(protocol_sha256=qh,source_sha256=p['source_sha256']),phase_cpu_seconds={'feasibility':1900})
    check(budget['status']=='verified' and budget['reserved_unknown_attempts']==0,'ledger unavailable or unsettled')
    receipt_debits={}
    for name in ['c4-root-prepare','c4-delete-0-cold','c4-delete-0-repair']:
        receipt=read(c/'attempts'/name/'worker/result.json');receipt_debits[receipt['budget_attempt_id']]=receipt['budget_debit']
    check(budget['attempts']==receipt_debits==t['budget']['attempts'],'ledger differs from complete receipt set')
    check(budget['charged_cpu_seconds']=={'feasibility':429} and not budget['over_cap']['feasibility'],'ledger charge differs')
    remaining=[x['id'] for x in p['trials'][3:]]
    check(sorted(x.name for x in (c/'attempts').iterdir())==sorted(x['id'] for x in p['trials'][:3]),'unexpected attempt')
    for name in remaining:check(not (c/'attempts'/name).exists(),'remaining trial started')
    original_audit=ROOT/'campaigns/recovery_v34/c4-cold0-incident-independent-audit.json'
    original_review=ROOT/'campaigns/recovery_v34/continuation-independent-review.json'
    check(hashed(original_audit)=='57df74042ea0313a05d1c006f955aea5fce1ef5b9fee3f2d9fa8836427d3be92','earlier incident audit changed')
    check(hashed(original_review)=='448ffc2862bdd928bf6e9332dc3dce060e27e28507d7b046b451c5de94eb3ae1','earlier review changed')
    old=read(original_audit)
    for name,e in old['metadata_inventory'].items():check(entry(ROOT/old['incident']/name)==e,'earlier cold incident changed')
    return dict(schema='c4-procfs-startup-failure-audit-v34',audit_status='checks_passed',campaign_status='blocked_after_execution_failure',
        failed_trial=a.name,program_sha256=ph,protocol_sha256=qh,amendment_sha256=hashed(c/'continuation-v1.json'),
        original_evidence_modified=False,experiments_run_by_audit=False,automatic_retry_permitted=False,
        outcome=r['outcome'],controller_elapsed_ns=t['controller_elapsed_ns'],observed_cpu_ns=cpu,charged_cpu_seconds=7,
        phase_budget=dict(cap=1900,charged_cpu_seconds=429,remaining_cpu_seconds=1471,unsettled_attempts=0,ledger_sha256=hashed(c/'phase-cpu-budget/ledger.json')),
        failure=dict(error_type=progress['error_type'],message=progress['error'],last_nonfailure_phase='checkpoint_load_started',observed_phases=phases,neural_inference_started=False,completed_model=False,completed_state=False,completion_file_exists=False,model_file_exists=False,state_file_exists=False),
        remaining_unstarted_trials=remaining,metadata_inventory={x.relative_to(a).as_posix():entry(x) for x in sorted(a.rglob('*.json'))},
        prior_audit_sha256=hashed(original_audit),prior_review_sha256=hashed(original_review),
        correction='Earlier matching portable-runtime, worker-limit, subprocess, and native-kernel checks were necessary but insufficient. They did not execute the checkpoint decoder runtime manifest. The previous recommendation to execute is superseded by this observed blocker. Original audit bytes remain unchanged.',
        proc_dependencies=[dict(module='src/transformer_backend.py',function='_runtime_manifest',paths=['/proc/self/maps','/proc/cpuinfo'],requirement='mandatory during DeterministicDecoder checkpoint construction; binds loaded libm/libpython and CPU dispatch fields'),dict(module='src/finite_primitives.py',function='_primitive_manifest_bytes',paths=['/proc/self/maps'],requirement='mandatory for mpfr_enclosure manifest; binds gmpy2 and loaded GMP/MPFR/MPC binaries'),dict(module='src/transaction_timing.py',function='_owned_children and _enable_subreaper',paths=['/proc/self/status','/proc/<pid>/status','/proc/self/task'],requirement='required by full subreaper observer path; not the command-admission-only path used by this failed worker'),dict(module='src/arithmetic_audit.py',function='_rss',paths=['/proc/self/statm'],requirement='optional diagnostic; OSError is caught and current RSS is reported unavailable')],
        local_restart='Use a normal supported Linux environment with readable procfs and the actual loaded library files. Perform decoder and MPFR runtime manifest preflight before registering a fresh local reproduction. Preserve the failed campaign and existing ledger; do not retry or substitute machine facts at this path. New-machine timing comparisons require newly matched arms and a new registration.',
        scientific_interpretation='Execution environment failure before inference. This is neither a repair speed measurement nor a numerical correctness failure. No completed C4 repair/cold comparison is available.',analysis_process_cpu_ns=time.process_time_ns()-start)


if __name__=='__main__':
    result=audit();out=ROOT/'campaigns/recovery_v34/c4-repair0-procfs-failure-audit.json'
    with out.open('xb') as f:f.write(canonical_json(result))
    print(json.dumps(dict(report=str(out.relative_to(ROOT)),sha256=hashed(out),status=result['campaign_status'],budget=result['phase_budget'])))
