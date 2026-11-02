"""Prospective primary full-byte audit and supplemental actual-model reread."""
import time
from research_v111.config import ROOT,RUN,PROFILES,ORDER,CAP,CELLS,expected_artifacts
from research_v90.outputs import inspect_outputs
from research_v111 import campaign as c
from research_v111 import receipts
from research_v111.state_audit import verify_profile
from research_v83.terminal import Inputs as AuditInputs
from research_v111.contracts import budget
from research_v111.records import writer
from research_v111.host import reconcile_cpu
from research_v80.io import require,write
from src.phase_budget import read_budget_snapshot
from src.run_store import canonical_json,digest

def snapshot(p,inputs):
    s=budget(p,c.sha(RUN/'program.json'),read_only=True)
    require(s['status']=='verified' and len(s['attempts'])==len(ORDER) and s['reserved_unknown_attempts']==0 and not s['reservation_overrun_attempts'] and not any(s['over_cap'].values()) and all(a['state']=='settled' for a in s['attempts'].values()),'Settled complete ledger required')
    require(inputs.read(RUN/'budget/ledger.json',retain=False)==dict(bytes=s['ledger_bytes'],sha256=s['ledger_sha256']),'Actual ledger changed')
    return s

from research_v111.timing import costs

def main(kind):
    require(kind in ('primary','supplemental'),'Known matched audit required');start=time.perf_counter_ns();cpu=time.process_time_ns()
    p=c.verify();inputs=AuditInputs();require(inputs.json(RUN/'program.json')==p,'Matched program changed')
    s=snapshot(p,inputs);completions=receipts.verify(p,inputs,s)
    for name,e in p['sources'].items():require(inputs.read(RUN/name,retain=False)==e,'Matched source changed')
    for entries in p['admitted_targets'].values():
        for e in entries.values():require(inputs.read(e['path'],retain=False)=={k:e[k] for k in ('bytes','sha256')},'Admitted target changed')
    e=p['target_terminal'];require(inputs.read(e['path'],retain=False)=={k:e[k] for k in ('bytes','sha256')},'Actual target prerequisite changed')
    timing=costs(p,completions,inputs)
    output_extents={}
    for trial in ORDER:
        directory=RUN/trial/'outputs';profile=trial.split('/')[0]
        extent=inspect_outputs(directory,trial)
        for name,e in extent['files'].items():
            key=str((directory/name).absolute())
            observed=inputs.files.get(key)
            if observed is None:observed=inputs.read(directory/name,retain=False)
            require(observed['bytes']==e['bytes'],'Output extent changed')
        output_extents[trial]=extent
    if kind=='primary':evidence={profile:verify_profile(RUN,profile,p,completions,inputs) for profile in PROFILES}
    else:
        primary=inputs.json(RUN/'primary-audit.json')
        require(primary['status']=='verified' and primary['program_sha256']==c.sha(RUN/'program.json') and primary['budget']==s and primary['costs']==timing and primary['worker_output_extents']==output_extents and set(primary['evidence'])==set(PROFILES) and all(len(primary['evidence'][profile]['comparisons'])==8 for profile in PROFILES),'Complete primary matched audit required')
        for profile in PROFILES:
            for cell in CELLS:
                for step in (1,2):require(inputs.read(RUN/profile/(cell+'-'+str(step))/'outputs/model.bin')==inputs.read(RUN/profile/'oracle/outputs'/f'step-{step}/model.bin'),'Actual same-checkpoint supplemental model mismatch')
        evidence=dict(primary_sha256=digest(canonical_json(primary)),actual_model_pairs_equal=16,full_state_audit_required=True)
    inputs.unchanged()
    writer().write(kind+'-audit.json',dict(schema='complete-matched-'+kind+'-audit-v111',status='verified',program_sha256=c.sha(RUN/'program.json'),budget=s,evidence=evidence,costs=timing,worker_output_extents=output_extents,inputs=inputs.files,confirmation=False,quality_evaluation=False,elapsed_ns=time.perf_counter_ns()-start,process_cpu_ns=time.process_time_ns()-cpu,terminal_host_accounting_required=True))
