"""Prospective continuation after V23's evidence failure, within its unchanged cap.

Uses exactly the frozen V23 numerical worker. Original incomplete evidence remains.
One documented unknown reservation stays fully charged and never becomes measured CPU.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from launch_fixed_timing_v23 import CAMPAIGN,ORIGINAL,complete,hashed
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.pilot_budget import inherited_allowance,research_worker_lock
from src.run_store import atomic_write,canonical_json,digest
from src.runtime_contract import capture_runtime_contract
from src.worker_control import WorkerLimits,run_limited
EXT=CAMPAIGN/'continuation-v24'
TRIALS=[('warm-cold-replacement-001','model_only_fresh',True),
        ('warm-repair-001','repair',True),('cold-002','model_only_fresh',False),
        ('repair-002','repair',False),('repair-003','repair',False),('cold-003','model_only_fresh',False)]
CONTROLLERS=['scripts/launch_fixed_continuation_v24.py','scripts/launch_fixed_timing_v23.py',
             'src/worker_control.py','src/phase_budget.py','src/run_store.py',
             'src/runtime_contract.py','src/experiment_inventory.py','src/pilot_budget.py']


def context():
    raw=(CAMPAIGN/'program.json').read_bytes();program=json.loads(raw)
    protocol=(CAMPAIGN/'protocol.json').read_bytes()
    recovery=(CAMPAIGN/'incidents/warm-cold-001/accounting-reconciliation.json').read_bytes()
    return raw,program,protocol,recovery


def register():
    if EXT.exists():raise ValueError('continuation already registered')
    raw,program,protocol,recovery=context()
    for name in ('prepare-001','repair-001','cold-001','indexed-001','fresh-001'):complete(name)
    r=json.loads(recovery)
    if digest((CAMPAIGN/'phase-cpu-budget/ledger.json').read_bytes())!=r['ledger_after_sha256']:
        raise ValueError('reconciled budget changed before registration')
    value=dict(schema='fixed-timing-recovery-continuation-v24',program_sha256=digest(raw),
        protocol_sha256=digest(protocol),reconciliation_sha256=digest(recovery),
        numerical_source_sha256=program['source_sha256'],
        controller_sha256={p:digest((ROOT/p).read_bytes()) for p in CONTROLLERS},
        status='prospectively_registered',trials=[dict(id=i,method=m,use_candidates=w,cpu_seconds=120,wall_seconds=120)
                                                for i,m,w in TRIALS],
        prior_required=['prepare-001','repair-001','cold-001','indexed-001','fresh-001'],
        unknown_reservation_id=r['restored_attempt_id'],unknown_reservation_cpu_seconds=122,
        unknown_reservation_policy='permanent full charge, never observed CPU; raw attempt remains incomplete',
        starting_recorded_cpu_seconds=251,starting_charged_or_reserved_cpu_seconds=373,
        remaining_cpu_seconds=527,unchanged_total_phase_cap_seconds=900,
        numerical_changes=False,quality_evaluation=False,confirmation=False,
        primary_clock=program['primary_clock'],
        controller_changes='durable reservation and pre-settlement exit/log evidence; costs remain inside every new clock',
        comparability='original controller lacked extra archival writes; all new repeat pairs use same amended controller',
        gates_unchanged=True,repeat_pairs=2,order='warm replay replacement, warm repair, cold-repair, repair-cold',
        replacement_reason='warm-cold-001 lost controller settlement evidence; no numerical or timing outcome selection',
        stop_policy='stop on any new failure or mismatch; no further automatic replacement',
        tool_scheduling_precaution='no concurrent agent or root filesystem tool calls during timing; cause of prior loss unknown')
    EXT.mkdir(parents=True);atomic_write(EXT/'program.json',canonical_json(value))
    print(json.dumps(dict(registered=True,sha256=digest(canonical_json(value)),remaining=527)))


def repeat_gate():
    names=['prepare-001','repair-001','cold-001','indexed-001','fresh-001',
           'warm-cold-replacement-001','warm-repair-001']
    rows={n:complete(n) for n in names}
    for k in ('fixed_target_sha256','base_target_sha256'):
        if len({p[k] for p,t in rows.values()})!=1:raise ValueError('target mismatch')
    retained=[rows[n][0] for n in names[1:]]
    if len({p['model_sha256'] for p in retained})!=1:raise ValueError('model mismatch')
    if retained[0]['model_sha256']==rows['prepare-001'][0]['model_sha256']:raise ValueError('no changed output')
    states=[p['state_artifact']['sha256'] for p in retained if p.get('state_artifact')]
    if len(set(states))!=1:raise ValueError('state mismatch')
    elapsed=lambda n:rows[n][1]['outer_transaction_elapsed_ns']
    ratio=elapsed('repair-001')/min(elapsed('cold-001'),elapsed('warm-cold-replacement-001'))
    if ratio>.90 or elapsed('repair-001')>=elapsed('fresh-001'):raise ValueError('timing gate failed')
    d=rows['repair-001'][0]['diagnostics']
    if d['neural_stage_record_pairs'] or d['anchor_preparation_stage_record_pairs']:raise ValueError('repair replayed features')
    if rows['cold-001'][0]['diagnostics']['neural_stage_record_pairs']!=24:raise ValueError('cold replay incomplete')
    return ratio


def launch(name):
    ext_raw=(EXT/'program.json').read_bytes();ext=json.loads(ext_raw)
    raw,program,protocol,recovery=context()
    if digest(raw)!=ext['program_sha256'] or digest(protocol)!=ext['protocol_sha256'] or digest(recovery)!=ext['reconciliation_sha256']:
        raise ValueError('registration changed')
    if {p:digest((ROOT/p).read_bytes()) for p in CONTROLLERS}!=ext['controller_sha256']:
        raise ValueError('registered controller changed')
    trials=ext['trials'];index=next((i for i,t in enumerate(trials) if t['id']==name),None)
    if index is None:raise ValueError('unregistered attempt')
    attempt=CAMPAIGN/'attempts'/name
    if attempt.exists():raise ValueError('attempt already exists')
    for old in ext['prior_required']:complete(old)
    for trial in trials[:index]:complete(trial['id'])
    if index>=2:repeat_gate()
    start=time.perf_counter_ns();runtime=capture_runtime_contract()
    if runtime!=json.loads((CAMPAIGN/'registration.json').read_bytes())['runtime']:raise ValueError('runtime changed')
    source=CAMPAIGN/'source'
    if source_hashes(source)!=program['source_sha256']:raise ValueError('numerical source changed')
    if inherited_allowance(ROOT)!=(10775,25):raise ValueError('legacy budget changed')
    budget=PhaseBudget(CAMPAIGN/'phase-cpu-budget',identity={'protocol_sha256':digest(protocol),
        'source_sha256':program['source_sha256']},phase_cpu_seconds={'feasibility':900})
    snapshot=budget.snapshot();incident=json.loads(recovery)
    unknown={k:v for k,v in snapshot['attempts'].items() if v['state']!='settled'}
    if unknown!={ext['unknown_reservation_id']:incident['restored_row']}:raise ValueError('unexpected unsettled worker')
    used=snapshot['charged_cpu_seconds']['feasibility'];required=244 if index in (2,4) else 122
    if used+required>900:raise ValueError('insufficient complete-block admission')
    trial=trials[index];inputs={}
    for key,entry in program['inputs'].items():
        if hashed(Path(entry['path']))!=entry:raise ValueError('input changed')
        inputs[key]=entry
    if trial['method'] in ('repair','indexed_fresh') or trial['use_candidates']:
        base=CAMPAIGN/'attempts/prepare-001'
        for key,rel in [('prior_progress','outputs/progress.json'),('prior_receipt','worker/result.json'),('prior_plan','plan.json')]:
            inputs[key]=hashed(base/rel)
        state=trial['method'] in ('repair','indexed_fresh')
        inputs['prior_state' if state else 'prior_model']=hashed(base/'outputs'/('state.bin' if state else 'model.bin'))
    attempt.mkdir(parents=True)
    plan=dict(schema='fixed-timing-worker-plan-v23',program_sha256=digest(raw),inputs=inputs,
        source_sha256=program['source_sha256'],checkpoint=str(ROOT/'tmp/models/distilgpt2'),output=str(attempt/'outputs'),
        protocol_sha256=digest(protocol),phase='feasibility',original_record_ids=ORIGINAL,record_ids=ORIGINAL[1:],
        deleted_ids=ORIGINAL[:1],method=trial['method'],use_candidates=trial['use_candidates'],
        continuation_program_sha256=digest(ext_raw))
    path=attempt/'plan.json';atomic_write(path,canonical_json(plan));atomic_write(attempt/'runtime.json',canonical_json(runtime))
    receipt=run_limited([sys.executable,str(source/'scripts/run_fixed_timing_v23.py'),str(path)],attempt/'worker',
        WorkerLimits(120,120,6*2**30,1,tuple(program['affinity_cpus'])),
        identity={'campaign':'fixed-feature-v23-continuation-v24','attempt_id':name,'plan_sha256':digest(path.read_bytes())},
        cwd=source,phase_budget=budget,phase='feasibility')
    receipt_sha=digest((attempt/'worker/result.json').read_bytes());elapsed=time.perf_counter_ns()-start
    transaction=dict(schema='fixed-timing-transaction-v23',attempt_id=name,outer_transaction_elapsed_ns=elapsed,
        receipt_sha256=receipt_sha,timing_scope=program['primary_clock'],worker_outcome=receipt['outcome'],
        budget_debit=receipt['budget_debit'],continuation_program_sha256=digest(ext_raw))
    atomic_write(attempt/'transaction.json',canonical_json(transaction))
    # Auxiliary copies follow the primary clock and never change its value.
    if (attempt/'outputs/progress.json').exists():
        atomic_write(attempt/'sealed-progress.json',(attempt/'outputs/progress.json').read_bytes())
    atomic_write(attempt/'postclock-budget.json',canonical_json(budget.snapshot()))
    if receipt['outcome']['status']!='complete':raise ValueError('worker failed; continuation stopped')
    complete(name)
    print(json.dumps(dict(id=name,seconds=elapsed/1e9,charged=receipt['budget_debit']['charged_cpu_seconds'],
        remaining=900-budget.snapshot()['charged_cpu_seconds']['feasibility'],status='complete')),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--register',action='store_true');group.add_argument('--id');args=parser.parse_args()
    with research_worker_lock(ROOT):register() if args.register else launch(args.id)
