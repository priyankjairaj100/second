"""Prospective primary full-byte audit and supplemental actual-model reread."""
import time
from research_v84.config import ROOT,RUN,PROFILES,ORDER,CAP,CELLS
from research_v84 import campaign as c
from research_v84 import receipts
from research_v84.state_audit import verify_profile
from research_v80.audit import AuditInputs
from research_v80.io import require,write
from src.phase_budget import read_budget_snapshot
from src.run_store import canonical_json,digest

def snapshot(p,inputs):
    s=read_budget_snapshot(RUN/'budget',identity=dict(program_sha256=c.sha(RUN/'program.json'),sources_sha256=digest(canonical_json(p['sources']))),phase_cpu_seconds={'feasibility':CAP})
    require(s['status']=='verified' and s['reserved_unknown_attempts']==0 and not s['reservation_overrun_attempts'] and not any(s['over_cap'].values()) and all(a['state']=='settled' for a in s['attempts'].values()),'Settled complete ledger required')
    require(inputs.read(RUN/'budget/ledger.json',retain=False)==dict(bytes=s['ledger_bytes'],sha256=s['ledger_sha256']),'Actual ledger changed')
    return s

def costs(p,completions,inputs):
    result={};controllers={};program_sha=c.sha(RUN/'program.json')
    for trial in ORDER:
        q=completions[trial];tx=inputs.json(RUN/trial/'transaction.json');name=trial.replace('/','--');entry=inputs.json(RUN/(name+'-entry.json'));start=inputs.json(RUN/(name+'-entry-start.json'))
        require(entry['status']=='complete' and entry['error'] is None and entry['program_sha256']==program_sha and entry['operation']=='run' and entry['arguments']==[trial] and entry['job_id']==tx['slurm_job_id']==start['job_id'] and entry['hostname']==p['host'] and entry['cpu_limits']==[300,10202],'Actual matched controller identity differs')
        require(all(type(entry[k]) is int and entry[k]>=0 for k in ('process_cpu_ns','waited_child_cpu_ns','elapsed_ns')) and entry['process_cpu_ns']<=301*10**9,'Controller observed CPU differs')
        require(0<q['worker_elapsed_ns']<=tx['elapsed_ns']<=entry['elapsed_ns'],'Clock containment differs')
        require(start['program_sha256']==program_sha and start['arguments']==[trial] and start['operation']=='run' and start['hostname']==p['host'] and start['affinity_cpus']==entry['affinity_cpus'] and len(entry['affinity_cpus'])==1,'Entry start differs')
        controllers[trial]=entry
        row=dict(transaction_elapsed_ns=tx['elapsed_ns'],worker_elapsed_ns=q['worker_elapsed_ns'],context_elapsed_ns=q['context_elapsed_ns'],entry_process_cpu_ns=entry['process_cpu_ns'],entry_waited_child_cpu_ns=entry['waited_child_cpu_ns'],worker_max_rss_kib=q['max_rss_kib'])
        if 'request' in q:
            r=q['request'];require(0<r['request_elapsed_ns']<=q['worker_elapsed_ns'],'Request clock containment differs')
            row.update(request_elapsed_ns=r['request_elapsed_ns'],request_timing=r['timing'],live_state_bytes=r['live_state_bytes'])
        result[trial]=row
    require(sum(x['process_cpu_ns'] for x in controllers.values())<=p['controller_cpu_allowance_seconds']*10**9,'Controller sum exceeds separate allowance')
    return dict(trials=result,entries=controllers,clock_scopes_overlap=True,host_terminal_accounting_pending=True)

def main(kind):
    require(kind in ('primary','supplemental'),'Known matched audit required');start=time.perf_counter_ns();cpu=time.process_time_ns()
    p=c.verify();inputs=AuditInputs();require(inputs.json(RUN/'program.json')==p,'Matched program changed')
    s=snapshot(p,inputs);completions=receipts.verify(p,inputs,s)
    for name,e in p['sources'].items():require(inputs.read(RUN/name,retain=False)==e,'Matched source changed')
    for entries in p['admitted_targets'].values():
        for e in entries.values():require(inputs.read(e['path'],retain=False)=={k:e[k] for k in ('bytes','sha256')},'Admitted target changed')
    for e in p['terminal_gates'].values():require(inputs.read(e['path'],retain=False)=={k:e[k] for k in ('bytes','sha256')},'Terminal prerequisite changed')
    timing=costs(p,completions,inputs)
    if kind=='primary':evidence={profile:verify_profile(RUN,profile,p,completions,inputs) for profile in PROFILES}
    else:
        primary=inputs.json(RUN/'primary-audit.json')
        require(primary['status']=='verified' and primary['program_sha256']==c.sha(RUN/'program.json') and primary['budget']==s and primary['costs']==timing and set(primary['evidence'])==set(PROFILES) and all(len(primary['evidence'][profile]['comparisons'])==8 for profile in PROFILES),'Complete primary matched audit required')
        for profile in PROFILES:
            for cell in CELLS:
                for step in (1,2):require(inputs.read(RUN/profile/(cell+'-'+str(step))/'outputs/model.bin')==inputs.read(RUN/profile/'oracle/outputs'/f'step-{step}/model.bin'),'Actual same-checkpoint supplemental model mismatch')
        evidence=dict(primary_sha256=digest(canonical_json(primary)),actual_model_pairs_equal=16,full_state_audit_required=True)
    inputs.unchanged()
    write(RUN/(kind+'-audit.json'),dict(schema='complete-matched-'+kind+'-audit-v84',status='verified',program_sha256=c.sha(RUN/'program.json'),budget=s,evidence=evidence,costs=timing,inputs=inputs.files,confirmation=False,quality_evaluation=False,elapsed_ns=time.perf_counter_ns()-start,process_cpu_ns=time.process_time_ns()-cpu,terminal_host_accounting_required=True))
