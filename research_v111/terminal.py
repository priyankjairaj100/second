"""Readonly complete scheduler, host, model/state and source closure."""
from pathlib import Path
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import datetime,json,platform,resource,time
from research_v111 import campaign,protocol
from research_v111.config import ROOT,RUN,ORDER,OPERATIONS,PROFILES,CELLS,name
from research_v111.submit import call,FIELDS,inspect_upstream
from research_v111.closure import review
from research_v111.contracts import budget
from research_v83.accounting import scheduler_rows
from research_v83.terminal import Inputs
from research_v80.io import require

def main(expected):
    require(sys.platform=='linux' and platform.node()=='csis.mn1' and Path(__file__).resolve()==RUN/'research_v111/terminal.py',
        'Literal Linux host terminal reporter required')
    resource.setrlimit(resource.RLIMIT_CPU,(300,301));resource.setrlimit(resource.RLIMIT_AS,(2*2**30,)*2)
    tick=time.perf_counter_ns();p=campaign.verify(prerequisite=False)
    require(campaign.sha(RUN/'program.json')==expected,'Exact new matched program required')
    require(call(['git','-C',str(ROOT),'rev-parse','HEAD'])==p['numerical_checkout'] and not call(['git','-C',str(ROOT),'status','--short']),
        'Frozen clean numerical checkout required')
    inspect_upstream(p);inputs=Inputs()
    require(inputs.json(RUN/'program.json')==p and inputs.json(RUN/'registration.json')==dict(program_sha256=expected),
        'Actual registered program changed during terminal review')
    prior=inputs.json(p['target_terminal']['path'])
    old_ids={str(i) for i in range(15904,15918)}|{str(i) for i in range(15921,15926)}|{str(i) for i in range(16004,16017)}|{r['job_id'] for r in prior['jobs'].values()}|{'16301','16307'}|{str(i) for i in range(16309,16332)}|{str(i) for i in range(16336,16359)}|{'16366','16367'}
    jobs={}
    for mode,sequence in [('checks',['checks']),('chain',list(OPERATIONS[1:]))]:
        chain=inputs.json(RUN/(mode+'-released-chain.json'));held=inputs.json(RUN/(mode+'-held-chain.json'))
        require(chain==held and chain['program_sha256']==expected and [r['operation'] for r in chain['jobs']]==sequence,
            'Exact held/released operation order required')
        dependency=None if mode=='checks' else jobs['checks']['job_id']
        for op,row in zip(sequence,chain['jobs']):
            key=name(op)
            require(row==inputs.json(RUN/(key+'-submission.json')) and row['name']==key and row['operation']==op
                and row['arguments']==[] and row['dependency']==dependency and row['job_id'] not in old_ids,
                'Literal new one-use matched allocation differs')
            protocol.allocation(op,expected,row['job_id'],require_release=True)
            inputs.json(RUN/(key+'-release.json'));jobs[op]=dict(job_id=row['job_id'],name='second111-'+key);dependency=row['job_id']
        inputs.json(RUN/(mode+'-chain-intent.json'))
    raw=call(['sacct','-nP','-j',','.join(r['job_id'] for r in jobs.values()),FIELDS]);scheduled=scheduler_rows(raw,jobs)
    costs={};debits={}
    for op in OPERATIONS:
        costs[op],worker=review(op,p,expected,inputs,scheduled[op])
        if worker:
            require(worker['budget_attempt_id'] not in debits,'Repeated matched worker debit')
            debits[worker['budget_attempt_id']]=worker['budget_debit']
    current=budget(p,expected,read_only=True);inputs.read(RUN/'budget/ledger.json',retain=False)
    require(current['attempts']==debits and len(debits)==len(ORDER) and not current['reserved_unknown_attempts']
        and not current['reservation_overrun_attempts'] and not any(current['over_cap'].values()),'All eighteen new workers must settle')
    audits={}
    for kind in ('primary','supplemental'):
        a=inputs.json(RUN/(kind+'-audit.json'))
        require(a['schema']=='complete-matched-'+kind+'-audit-v111' and a['status']=='verified' and a['program_sha256']==expected
            and a['budget']==current and a['confirmation'] is a['quality_evaluation'] is False,'Both actual matched audits required')
        for path,e in a['inputs'].items():inputs.read(path,e,retain=False)
        audits[kind]=a
    a,b=audits['primary'],audits['supplemental']
    require(set(a['evidence'])==set(PROFILES) and b['evidence']['actual_model_pairs_equal']==16
        and b['evidence']['primary_sha256']==inputs.files[str(RUN/'primary-audit.json')]['sha256']
        and a['costs']==b['costs'] and a['worker_output_extents']==b['worker_output_extents'],'Actual independent audit agreement required')
    wanted={(cell,step) for cell in CELLS for step in (1,2)}
    for profile in PROFILES:
        comparisons=a['evidence'][profile]['comparisons']
        require(len(comparisons)==8 and {(r['cell'],r['step']) for r in comparisons}==wanted
            and all(r['profile']==profile and r['actual_model_bytes_equal'] is r['actual_state_bytes_equal'] is r['actual_trust_bytes_equal'] is True
                for r in comparisons),'Every same-checkpoint model/state/trust pair must match')
    require(sum(costs[t]['complete_controller_upper_cpu_ns'] for t in ORDER)<=5436*10**9,'Complete eighteen-worker controller allowance exceeded')
    for path,e in p['sources'].items():inputs.read(RUN/path,e,retain=False)
    inputs.unchanged()
    result=dict(schema='matched-complete-terminal-v111',status='verified',program_sha256=expected,prior_complete_failure=p['prior_complete_failure'],
        cumulative_software_upper_cpu_ns=207*10**9+costs['checks']['scheduler_cpu_ns']+costs['checks']['scheduler_quantum_ns'],
        cumulative_numerical_seconds=6304+current['charged_cpu_seconds']['feasibility'],
        cumulative_numerical_controller_upper_cpu_ns=79*10**9+sum(costs[t]['complete_controller_upper_cpu_ns'] for t in ORDER),
        cumulative_checks_controller_upper_cpu_ns=48*10**9+costs['checks']['complete_controller_upper_cpu_ns'],
        jobs=jobs,scheduler_raw=raw,
        costs=costs,budget=current,target_gate=p['target_gate'],inputs=inputs.files,
        evidence=dict(actual_model_state_trust_pairs=16,checkpoints=2,related_gpt_family_only=True,
            single_observation_screen=True,stable_speedup=False,cross_architecture_generality=False,quality_evaluation=False),
        overlapping_clocks_not_summed=True,readonly_review_cost_outside_experiment=True,
        readonly_host_cpu_ns=time.process_time_ns(),readonly_host_elapsed_ns=time.perf_counter_ns()-tick,
        captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    print(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))

if __name__=='__main__':main(*sys.argv[1:])
