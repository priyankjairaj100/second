"""Reopen actual V101 admission and its V89 predecessor, without inventing success."""
from pathlib import Path
from research_v80.io import read,require,info
from research_v83.accounting import scheduler_rows
from research_v83.terminal import Inputs
from research_v90.recovery_gate import verify as recovery
from research_v101.config import design as admission_design,ORDER as ADMISSION_ORDER,TARGET_FILES
from research_v101.closure import review
from research_v101.contracts import budget
from research_v101.fetch import verify_fetch
from research_v104.prior_admission import verify as verify_prior_setup
from research_v104.config import ROOT,ADMISSION,PROFILES
from src.run_store import canonical_json,strict_json


def validate(report,p,close):
    expected=info(canonical_json(p))['sha256']
    require(report['schema']=='matched-target-terminal-v101' and report['status']=='verified'
        and report['program_sha256']==expected and all(p.get(k)==v for k,v in admission_design().items()),
        'Actual matching V101 target-admission report/program required')
    require(report['actual_target_admission'] is True and report['empirical_transfer'] is report['quality_evaluation'] is False,
        'Target admission is not empirical transfer or quality')
    require(set(report['jobs'])==set(ADMISSION_ORDER) and all(r['name']=='second101-'+n for n,r in report['jobs'].items()),
        'Every actual admission allocation required')
    scheduled=scheduler_rows(report['scheduler_raw'],report['jobs'])
    require(set(report['costs'])==set(scheduled) and report['recovery_gate']==p['recovery_gate'], 'Actual cost/upstream census differs')
    s=report['budget']
    require(s['status']=='verified' and len(s['attempts'])==2 and not s['reserved_unknown_attempts']
        and not s['reservation_overrun_attempts'] and not any(s['over_cap'].values())
        and all(a['state']=='settled' for a in s['attempts'].values()),'Two actual settled target workers required')
    require(close['schema']=='matched-target-close-v101' and close['status']=='admitted_pending_host_terminal_accounting'
        and close['program_sha256']==expected and close['budget']==s
        and close['empirical_transfer'] is close['neural_execution'] is close['calibration_execution'] is close['quality_evaluation'] is False,
        'Actual admission-only close report required')
    a=close['seal_audit']
    require(a['schema']=='matched-target-seals-v101' and a['actual_targets_verified'] is a['sealed_workers_verified'] is a['matched_records_verified'] is True
        and a['numerical_model_transfer'] is False and set(a['models'])==set(PROFILES),'Both actual target seals required')
    for profile in PROFILES:
        c=a['models'][profile]
        require(c['status']=='complete' and c['profile']==profile and c['program_sha256']==expected
            and c['job_id']==report['jobs'][profile]['job_id'] and set(c['artifacts'])==set(TARGET_FILES),
            'Actual complete target profile/job differs')
    return scheduled


def verify(path,expected):
    raw=read(path,expected,maximum=64*2**20);r=strict_json(raw)
    require(canonical_json(r)==raw,'Canonical actual saved V101 terminal report required')
    inventory=r['inputs'];require(type(inventory) is dict and 0<len(inventory)<=8192,'Bounded admission input census required')
    inputs=Inputs()
    for name,e in inventory.items():
        q=Path(name)
        require(q.is_absolute() and '..' not in q.parts and q.is_relative_to(ROOT)
            and type(e) is dict and set(e)=={'bytes','sha256'} and type(e['bytes']) is int and 0<=e['bytes']<=2**30,
            'Pinned bounded admission input required')
        inputs.read(q,e,retain=False)
    def meta(relative):
        p=ADMISSION/relative;require(str(p) in inventory,'Actual admission metadata omitted')
        return strict_json(inputs.read(p,inventory[str(p)]))
    p=meta('program.json');close=meta('close-report.json');scheduled=validate(r,p,close);sha=r['program_sha256']
    require(verify_prior_setup()==p['prior_setup_failure'],'Preserved V91 setup failure differs')
    require(r['close_report']==inventory[str(ADMISSION/'close-report.json')], 'Actual target close commitment differs')
    require(meta('registration.json')==dict(program_sha256=sha) and strict_json(inputs.read(ADMISSION/'inventory.json',p['source_inventory']))==p['sources'],
        'Registered admission inventory differs')
    require(all(inventory.get(str(ADMISSION/n))==e for n,e in p['sources'].items()),'Actual admission sources missing')
    for operation in ADMISSION_ORDER:
        cost,_=review(operation,p,sha,inputs,scheduled[operation])
        require(cost==r['costs'][operation],'Reopened complete admission cost differs')
        submission=meta(operation+'-submission.json')
        require(submission['job_id']==r['jobs'][operation]['job_id'] and submission['program_sha256']==sha
            and submission['operation']==submission['name']==operation and submission['arguments']==[], 'Actual admission job differs')
        require(meta(operation+'-release.json')==dict(program_sha256=sha,job_id=submission['job_id'],released=True),
            'Actual one-use release required')
    require(sum(c['complete_controller_upper_cpu_ns'] for c in r['costs'].values())<=1500*10**9,'Actual target controller aggregate exceeded')
    carried=p['prior_setup_failure']
    require(r['prior_failed_software']==carried and carried['carried_software_seconds']==56
        and carried['carried_controller_seconds']==10,'Prior failed software cost omitted')
    controller=10*10**9+sum(c['complete_controller_upper_cpu_ns'] for c in r['costs'].values())
    software=56*10**9+r['costs']['checks']['scheduler_cpu_ns']+r['costs']['checks']['scheduler_quantum_ns']
    require(controller==r['cumulative_controller_upper_cpu_ns']<=1510*10**9
        and software==r['cumulative_software_upper_cpu_ns']<=602*10**9,'Cumulative failed plus new caps exceeded')
    require(budget(p,sha,read_only=True)==r['budget'],'Actual settled admission ledger changed')
    for profile in PROFILES:
        c=meta(profile+'/outputs/completion.json')
        require(c==close['seal_audit']['models'][profile],'Actual target completion differs')
        for n,e in c['artifacts'].items():
            require(inventory.get(str(ADMISSION/profile/'outputs'/n))=={k:e[k] for k in ('bytes','sha256')},'Actual target artifact missing')
    verify_fetch(ADMISSION/'checkpoint/gpt2')
    b=p['recovery_terminal'];require(recovery(b['path'],{k:b[k] for k in ('bytes','sha256')})==p['recovery_gate'],
        'Actual V89 prerequisite changed')
    inputs.unchanged();read(path,expected,maximum=64*2**20,retain=False)
    return dict(schema='reopened-target-admission-gate-v104',status='verified',program_sha256=sha,
        report=info(raw),inputs_reopened=len(inventory),targets=2,empirical_transfer=False,
        recovery_gate=p['recovery_gate']),p,close
