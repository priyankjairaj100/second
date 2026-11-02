"""All-cell saved-scalar reduction, gated on the actual completed V104 terminal.

This does not rerun a model or independently re-audit binary equality. It binds
reporting metadata to the completed cluster terminal's checked input inventory.
"""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reporting_v93.cost_scope import comparisons,phase_partition
from research_v83.accounting import scheduler_rows
from research_v104.config import RUN,ORDER,OPERATIONS,PROFILES,CELLS,name,design


def require(value,message):
    if not value:raise ValueError(message)


def identity(blob):return dict(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())


def validate(terminal,program,primary,supplemental,program_raw):
    sha=identity(program_raw)['sha256']
    require(terminal['schema']=='matched-complete-terminal-v104' and terminal['status']=='verified'
        and terminal['program_sha256']==sha and all(program.get(k)==v for k,v in design().items()),
        'Actual completed matched terminal and exact program required')
    require(set(terminal['jobs'])==set(terminal['costs'])==set(OPERATIONS)
        and all(r['name']=='second104-'+name(op) for op,r in terminal['jobs'].items()), 'Every actual operation required')
    scheduled=scheduler_rows(terminal['scheduler_raw'],terminal['jobs'])
    for op,row in scheduled.items():
        cost=terminal['costs'][op]
        require(cost['job_id']==row['job_id'] and cost['scheduler_cpu_ns']==row['cpu_ns']
            and cost['scheduler_quantum_ns']==row['quantum_ns'], 'Actual scheduler costs differ')
    carry=terminal['prior_complete_failure']
    require(carry==program['prior_complete_failure'] and carry['carried_software_seconds']==72
        and carry['carried_controller_seconds']==19 and carry['carried_numerical_controller_seconds']==1,
        'Earlier qualification and dispatch costs must be carried')
    require(terminal['costs']['checks']['complete_controller_upper_cpu_ns']+19*10**9<=302*10**9
        and terminal['costs']['distilgpt2/prepare']['complete_controller_upper_cpu_ns']+10**9<=302*10**9
        and sum(terminal['costs'][op]['complete_controller_upper_cpu_ns'] for op in ORDER)+10**9<=6040*10**9,
        'Cumulative controller allowances differ')
    cumulative=72*10**9+terminal['costs']['checks']['scheduler_cpu_ns']+terminal['costs']['checks']['scheduler_quantum_ns']
    require(terminal['cumulative_software_upper_cpu_ns']==cumulative<=602*10**9,
        'Cumulative software allowance differs')
    budget=terminal['budget']
    require(budget['status']=='verified' and len(budget['attempts'])==20 and not budget['reserved_unknown_attempts']
        and not budget['reservation_overrun_attempts'] and not any(budget['over_cap'].values())
        and all(a['state']=='settled' for a in budget['attempts'].values()), 'Every numerical debit must settle')
    for kind,audit in [('primary',primary),('supplemental',supplemental)]:
        require(audit['schema']=='complete-matched-'+kind+'-audit-v104' and audit['status']=='verified'
            and audit['program_sha256']==sha and audit['budget']==budget
            and audit['confirmation'] is audit['quality_evaluation'] is False, 'Both actual scoped audits required')
        require(all(terminal['inputs'].get(p)==e for p,e in audit['inputs'].items()), 'Audit inputs omitted or changed')
    require(primary['costs']==supplemental['costs'] and primary['worker_output_extents']==supplemental['worker_output_extents']
        and set(primary['evidence'])==set(PROFILES) and supplemental['evidence']['actual_model_pairs_equal']==16,
        'Actual paired audits disagree')
    require(supplemental['evidence']['primary_sha256']==terminal['inputs'][str(RUN/'primary-audit.json')]['sha256'],
        'Supplemental audit targets another primary')
    require(terminal['evidence']==dict(actual_model_state_trust_pairs=16,checkpoints=2,related_gpt_family_only=True,
        single_observation_screen=True,stable_speedup=False,cross_architecture_generality=False,quality_evaluation=False),
        'Matched evidence scope changed')
    for profile in PROFILES:
        pairs=primary['evidence'][profile]['comparisons']
        require(len(pairs)==8 and {(r['cell'],r['step']) for r in pairs}=={(c,s) for c in CELLS for s in (1,2)}
            and all(r['profile']==profile and r['actual_model_bytes_equal'] is r['actual_state_bytes_equal'] is r['actual_trust_bytes_equal'] is True for r in pairs),
            'Every same-checkpoint model/state/trust pair is required')
    return scheduled


def main(terminal_path,receipt_directory,output_path):
    raw=Path(terminal_path).read_bytes();t=json.loads(raw);base=Path(receipt_directory);bound={}
    def read(relative,decode=True):
        blob=(base/relative).read_bytes();expected=t['inputs'][str(RUN/relative)]
        require(identity(blob)==expected,'Changed or unbound reporting input: '+relative)
        bound[relative]=expected
        return json.loads(blob) if decode else blob
    pr=read('program.json',False);p=json.loads(pr);a=read('primary-audit.json');b=read('supplemental-audit.json')
    validate(t,p,a,b,pr)
    rows=[];ratios={}
    for profile in PROFILES:
        current={}
        for cell in CELLS:
            for step in (1,2):
                trial=f'{profile}/{cell}-{step}';completion=read(trial+'/outputs/completion.json');host=read(name(trial)+'-host.json')
                request=completion['request'];time=a['costs']['trials'][trial];storage=a['evidence'][profile]['storage'][cell][step-1]
                require(host['status']==completion['status']=='complete' and completion['slurm_job_id']==t['costs'][trial]['job_id']
                    and host['elapsed_ns']==time['complete_host_elapsed_ns'] and request['request_elapsed_ns']==time['request_elapsed_ns']
                    and request['live_state_bytes']==storage['live_state_bytes'] and len(request['retained_ids'])==p['retained_counts'][step-1],
                    'Actual complete request identity, timing or storage differs')
                phases=phase_partition(host['elapsed_ns'],request,p['stage_counts'][profile])
                current[cell,step]=dict(profile=profile,cell=cell,step=step,retained_records=len(request['retained_ids']),
                    job_id=completion['slurm_job_id'],host_elapsed_ns=host['elapsed_ns'],request_elapsed_ns=request['request_elapsed_ns'],
                    max_rss_kib=completion['max_rss_kib'],**storage,**phases)
        rows.extend(current.values());ratios[profile]=comparisons(current)
    result=dict(schema='matched-screen-scalar-reduction-v102',status='verified_saved_scalar_reduction',actual_terminal=identity(raw),
        inputs=bound,rows=rows,comparisons=ratios,numerical_budget=t['budget'],
        scheduler_cpu_lower_ns=sum(c['scheduler_cpu_ns'] for c in t['costs'].values()),
        scheduler_cpu_upper_ns=sum(c['scheduler_cpu_ns']+c['scheduler_quantum_ns'] for c in t['costs'].values()),
        worker_controller_upper_ns=sum(t['costs'][op]['complete_controller_upper_cpu_ns'] for op in ORDER),
        complete_preparation_host_ns={profile:a['costs']['trials'][profile+'/prepare']['complete_host_elapsed_ns'] for profile in PROFILES},
        old_unknown_v80_cpu_seconds=12602,prior_failed_v99_software_cpu_charge_seconds=56,
        prior_failed_v100_software_cpu_charge_seconds=4,
        prior_v103_software_cpu_charge_seconds=68,prior_v103_dispatch_controller_charge_seconds=1,
        cumulative_screen_software_upper_cpu_ns=t['cumulative_software_upper_cpu_ns'],
        cumulative_screen_controller_upper_ns=10**9+sum(t['costs'][op]['complete_controller_upper_cpu_ns'] for op in ORDER),
        clocks_overlap=True,preparation_shared_across_cells=True,individual_optimization_effect_identified=False,
        new_quality_evaluation=False,stable_latency_established=False,cross_architecture_generality=False,
        binary_equality_scope='Actual prior terminal audits; this reducer checks bound reporting metadata only',no_numerical_execution=True)
    with Path(output_path).open('x') as stream:json.dump(result,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=result['status'],rows=len(rows),terminal=result['actual_terminal'])))

if __name__=='__main__':main(*sys.argv[1:])
