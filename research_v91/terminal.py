"""Read-only host closure of actual five-step target admission and all clocks."""
from pathlib import Path
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import datetime,json,platform,resource,time
from research_v91 import protocol
from research_v91.config import ROOT,RUN,ORDER,PROFILES,TARGET_FILES
from research_v91.submit import call,FIELDS,inspect_upstream
from research_v91.closure import review
from research_v91.contracts import budget
from research_v91.fetch import verify_fetch,EXPECTED as FETCH_FILES
from research_v83.accounting import scheduler_rows
from research_v83.terminal import Inputs
from research_v80.io import require


def main(expected):
    require(sys.platform=='linux' and platform.node()=='csis.mn1' and Path(__file__).resolve()==RUN/'research_v91/terminal.py',
        'Literal host terminal reporter required')
    resource.setrlimit(resource.RLIMIT_CPU,(300,301));resource.setrlimit(resource.RLIMIT_AS,(2*2**30,)*2)
    tick=time.perf_counter_ns();p=protocol.program(expected)
    require(call(['git','-C',str(ROOT),'rev-parse','HEAD'])==p['numerical_checkout'] and not call(['git','-C',str(ROOT),'status','--short']),
        'Frozen clean numerical checkout required')
    inspect_upstream(p);inputs=Inputs();inputs.json(RUN/'program.json');inputs.json(RUN/'registration.json')
    jobs={};old_ids={str(i) for i in range(15904,15918)}|{str(i) for i in range(15921,15926)}|{str(i) for i in range(16004,16017)}
    for mode,names in [('checks',['checks']),('chain',list(ORDER[1:]))]:
        chain=inputs.json(RUN/(mode+'-released-chain.json'))
        require(chain['program_sha256']==expected and [r['name'] for r in chain['jobs']]==names,'Exact released chain order required')
        dependency=None if mode=='checks' else jobs['checks']['job_id']
        for row in chain['jobs']:
            name=row['name'];require(row==inputs.json(RUN/(name+'-submission.json')) and row['dependency']==dependency
                and row['operation']==name and row['arguments']==[] and row['job_id'] not in old_ids,'New finite chain identity differs')
            protocol.allocation(name,expected,row['job_id'],require_release=True)
            inputs.json(RUN/(name+'-release.json'));jobs[name]=dict(job_id=row['job_id'],name='second91-'+name);dependency=row['job_id']
        inputs.json(RUN/(mode+'-held-chain.json'));inputs.json(RUN/(mode+'-chain-intent.json'))
    raw=call(['sacct','-nP','-j',','.join(r['job_id'] for r in jobs.values()),FIELDS]);scheduled=scheduler_rows(raw,jobs)
    costs={};debits={}
    for name in ORDER:
        costs[name],worker=review(name,p,expected,inputs,scheduled[name])
        if worker:
            require(worker['budget_attempt_id'] not in debits,'Duplicate target CPU debit')
            debits[worker['budget_attempt_id']]=worker['budget_debit']
    snapshot=budget(p,expected,read_only=True);inputs.read(RUN/'budget/ledger.json',retain=False)
    require(snapshot['attempts']==debits and len(debits)==2 and not snapshot['reserved_unknown_attempts']
        and not snapshot['reservation_overrun_attempts'] and not any(snapshot['over_cap'].values()),'Every target debit must be settled and counted')
    close=inputs.json(RUN/'close-report.json');entry=inputs.json(RUN/'close-entry.json')
    require(entry['result']==close and close['schema']=='matched-target-close-v91' and close['program_sha256']==expected
        and close['status']=='admitted_pending_host_terminal_accounting' and close['budget']==snapshot,'Actual close report and ledger differ')
    audit=close['seal_audit'];require(audit['schema']=='matched-target-seals-v91' and audit['actual_targets_verified'] is True
        and audit['sealed_workers_verified'] is True and audit['matched_records_verified'] is True
        and audit['numerical_model_transfer'] is False,'Actual target seals were not verified')
    require(close['empirical_transfer'] is close['neural_execution'] is close['calibration_execution'] is close['quality_evaluation'] is False,
        'Admission scope cannot become empirical transfer')
    for profile in PROFILES:
        root=RUN/profile;c=inputs.json(root/'outputs/completion.json')
        require(c==audit['models'][profile] and c['status']=='complete' and c['program_sha256']==expected
            and c['job_id']==jobs[profile]['job_id'] and set(c['artifacts'])==set(TARGET_FILES),'Saved actual target closure differs')
        for name,binding in c['artifacts'].items():inputs.read(root/'outputs'/name,{k:binding[k] for k in ('bytes','sha256')},retain=False)
        inputs.json(root/'plan.json');inputs.json(root/'transaction.json')
    verify_fetch(RUN/'checkpoint/gpt2')
    for name in [*FETCH_FILES,'fetch-intent.json','fetch-receipt.json']:inputs.read(RUN/'checkpoint/gpt2'/name,retain=False)
    for name,binding in p['sources'].items():inputs.read(RUN/name,binding,retain=False)
    require(sum(c['complete_controller_upper_cpu_ns'] for c in costs.values())<=1510*10**9,'Complete controller aggregate exceeded1510seconds')
    inputs.unchanged()
    result=dict(schema='matched-target-terminal-v91',status='verified',program_sha256=expected,
        actual_target_admission=True,empirical_transfer=False,quality_evaluation=False,
        jobs=jobs,scheduler_raw=raw,costs=costs,budget=snapshot,recovery_gate=p['recovery_gate'],
        close_report=inputs.files[str(RUN/'close-report.json')],inputs=inputs.files,
        overlapping_clocks_not_summed=True,readonly_review_cost_outside_experiment=True,
        readonly_host_cpu_ns=time.process_time_ns(),readonly_host_elapsed_ns=time.perf_counter_ns()-tick,
        captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    print(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))

if __name__=='__main__':main(*sys.argv[1:])
