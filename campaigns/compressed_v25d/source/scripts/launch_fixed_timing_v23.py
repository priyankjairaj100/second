"""Register and execute a separate, bounded fixed-feature timing campaign.

The legacy 10,800-second pilot ledger remains unchanged. This campaign has
its own prospective 900-second CPU allowance under continued user authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.pilot_budget import inherited_allowance,research_worker_lock
from src.run_store import atomic_write,canonical_json,digest
from src.runtime_contract import capture_runtime_contract
from src.worker_control import WorkerLimits,run_limited

ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/'campaigns/fixed_feature_v23'
ORIGINAL=['wikitext2:train:article-row-27113','wikitext2:train:article-row-5326']
ARMS=[
    ('prepare-001','prepare',False,160),
    ('repair-001','repair',False,120),
    ('cold-001','model_only_fresh',False,120),
    ('indexed-001','indexed_fresh',False,120),
    ('fresh-001','direct_fresh',False,120),
    ('warm-cold-001','model_only_fresh',True,120),
    ('warm-repair-001','repair',True,120),
    ('cold-002','model_only_fresh',False,120),
    ('repair-002','repair',False,120),
    ('repair-003','repair',False,120),
    ('cold-003','model_only_fresh',False,120),
]


def hashed(path):
    with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(path=str(path),sha256=sha)


def register():
    if CAMPAIGN.exists():raise ValueError('campaign registration already exists')
    used,left=inherited_allowance(ROOT)
    if (used,left)!=(10775,25):raise ValueError('legacy checkpoint differs')
    if not (ROOT/'scripts/run_fixed_timing_v23.py').is_file():raise ValueError('worker missing')
    paths=dict(records='pilots/v10/wikitext2/preflight-records.json',
        config='tmp/models/distilgpt2/config.json',weights='tmp/models/distilgpt2/model.safetensors')
    program=dict(schema='fixed-timing-program-v23',status='prospectively_registered',
        phase='feasibility',scope='one development root; complete real-deletion timing',
        original_record_ids=ORIGINAL,retained_record_ids=ORIGINAL[1:],deleted_ids=ORIGINAL[:1],
        tokens_per_record=16,normalization=32,state_backend='factors',solver_backend='native_ball',
        separate_cpu_cap_seconds=900,legacy=dict(charged_cpu_seconds=used,remaining_cpu_seconds=left,
            cap_cpu_seconds=10800,reset=False),
        authorization='continued local empirical work requested by user; prior cap was a bounded feasibility protocol; no paid cloud compute',
        inputs={name:hashed(ROOT/path) for name,path in paths.items()},
        trials=[dict(id=name,method=method,use_candidates=warm,cpu_seconds=cap,wall_seconds=cap)
                for name,method,warm,cap in ARMS],
        pilot_repeat_gate=dict(max_repair_over_best_replay_ratio=.90,
            require_all_exact_models=True,require_equal_complete_retained_states=True,
            compare_replay_arms=['cold-001','warm-cold-001']),
        repeat_policy='two more cold/primary-repair pairs, alternating order; no confirmation or reliability claim',
        stop_policy='stop on failed prerequisite or insufficient complete reservation; no retries, target tuning, or budget reset',
        primary_clock='controller transaction after bootstrap/gates through sealed worker receipt and receipt hash; excludes final observer marker write',
        accounting='initial registration separately recorded; preparation included in lifetime; never add nested clocks',
        os_cache='uncontrolled',other_machine_activity='uncontrolled',
        native_compile='fresh process compilation charged equally; kernel never trusts a binary cache',
        address_space_bytes=6*2**30,threads=1,affinity_cpus=[min(os.sched_getaffinity(0))],
        confirmation=False,quality_evaluation=False,scientific_promotion=False)
    start=time.perf_counter_ns()
    snapshot=CAMPAIGN/'source'
    for folder in ('src','scripts'):
        (snapshot/folder).mkdir(parents=True)
        for path in (ROOT/folder).glob('*.py'):shutil.copyfile(path,snapshot/folder/path.name)
    program['source_sha256']=source_hashes(snapshot)
    program['launcher_sha256']=digest(Path(__file__).read_bytes())
    program['registered_from_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    raw=canonical_json(program);atomic_write(CAMPAIGN/'program.json',raw)
    protocol=canonical_json(dict(schema='fixed-timing-policy-v23',program_sha256=digest(raw),
        phase_cpu_seconds={'feasibility':900},legacy=program['legacy']))
    atomic_write(CAMPAIGN/'protocol.json',protocol)
    atomic_write(CAMPAIGN/'registration.json',canonical_json(dict(
        program_sha256=digest(raw),protocol_sha256=digest(protocol),
        elapsed_ns=time.perf_counter_ns()-start,runtime=capture_runtime_contract(),
        scope='controller registration and source snapshot; no model execution')))
    print(json.dumps(dict(registered=True,program_sha256=digest(raw),new_cpu_cap=900,legacy_remaining=left)))


def complete(attempt):
    path=CAMPAIGN/'attempts'/attempt
    receipt=json.loads((path/'worker/result.json').read_bytes())
    progress=load_progress(path)
    transaction=json.loads((path/'transaction.json').read_bytes())
    if (receipt['outcome']['status']!='complete' or receipt['budget_debit']['state']!='settled'
            or progress['status']!='complete' or progress['plan_sha256']!=digest((path/'plan.json').read_bytes())
            or receipt['worker_identity']['plan_sha256']!=progress['plan_sha256']):
        raise ValueError('failed or incomplete prerequisite: '+attempt)
    if transaction['receipt_sha256']!=digest((path/'worker/result.json').read_bytes()):
        raise ValueError('transaction receipt differs')
    return progress,transaction


def load_progress(path):
    progress=json.loads((path/'outputs/progress.json').read_bytes())
    if progress['status']=='complete':return progress
    amendment=json.loads((CAMPAIGN/'controller-amendment.json').read_bytes())
    if path.name!='cold-001':raise ValueError('no registered metadata recovery for this attempt')
    raw=(CAMPAIGN/'recoveries/cold-001.json').read_bytes()
    if digest(raw)!=amendment['recovery_sha256']:raise ValueError('recovery changed')
    recovery=json.loads(raw)
    for evidence in recovery['evidence'].values():
        if hashed(CAMPAIGN/evidence['path'])['sha256']!=evidence['sha256']:
            raise ValueError('recovery evidence changed')
    return recovery['effective_progress']


def repeat_gate(program):
    rows={name:complete(name) for name,_,_,_ in ARMS[:7]}
    retained=[rows[name][0] for name,_,_,_ in ARMS[1:7]]
    for key in ('fixed_target_sha256','base_target_sha256'):
        if len({r[0][key] for r in rows.values()})!=1:raise ValueError('comparison target identities differ')
    if len({r['model_sha256'] for r in retained})!=1:raise ValueError('retained models differ')
    if retained[0]['model_sha256']==rows['prepare-001'][0]['model_sha256']:
        raise ValueError('deletion changed no model codes; do not promote this root')
    states=[r['state_artifact']['sha256'] for r in retained if r.get('state_artifact')]
    if len(set(states))!=1:raise ValueError('retained complete states differ')
    elapsed=lambda name:rows[name][1]['outer_transaction_elapsed_ns']
    if elapsed('repair-001')>=elapsed('fresh-001'):raise ValueError('repair did not beat complete fresh')
    repair=rows['repair-001'][0]['diagnostics']
    if repair['neural_stage_record_pairs'] or repair['anchor_prepared_records']:
        raise ValueError('repair repeated neural feature work')
    if rows['cold-001'][0]['diagnostics']['neural_stage_record_pairs']!=24:
        raise ValueError('cold replay did not execute complete retained features')
    ratio=elapsed('repair-001')/min(elapsed('cold-001'),elapsed('warm-cold-001'))
    if ratio>program['pilot_repeat_gate']['max_repair_over_best_replay_ratio']:
        raise ValueError('primary repair did not pass best-replay timing gate')
    return ratio


def launch(attempt_id):
    raw=(CAMPAIGN/'program.json').read_bytes();program=json.loads(raw)
    protocol=(CAMPAIGN/'protocol.json').read_bytes();policy=json.loads(protocol)
    if policy['program_sha256']!=digest(raw):raise ValueError('registration binding differs')
    launcher_sha=digest(Path(__file__).read_bytes())
    amendment_sha=None
    if launcher_sha!=program['launcher_sha256']:
        amended=(CAMPAIGN/'controller-amendment.json').read_bytes();amendment=json.loads(amended)
        if (amendment['program_sha256']!=digest(raw) or amendment['new_launcher_sha256']!=launcher_sha
                or amendment['original_launcher_sha256']!=program['launcher_sha256']
                or amendment['scope']!='sealed metadata recovery; unchanged experiment and timing'):
            raise ValueError('launcher source changed without matching recovery amendment')
        amendment_sha=digest(amended)
    trials=program['trials'];index=next((i for i,a in enumerate(trials) if a['id']==attempt_id),None)
    if index is None:raise ValueError('unregistered attempt')
    if (CAMPAIGN/'attempts'/attempt_id).exists():raise ValueError('attempt already exists')
    for prior in trials[:index]:complete(prior['id'])
    if index>=7:repeat_gate(program)
    trial=trials[index];start=time.perf_counter_ns()
    runtime=capture_runtime_contract()
    registered=json.loads((CAMPAIGN/'registration.json').read_bytes())
    if runtime!=registered['runtime']:raise ValueError('registered runtime changed')
    source=CAMPAIGN/'source'
    if source_hashes(source)!=program['source_sha256']:raise ValueError('frozen source changed')
    if inherited_allowance(ROOT)!=(10775,25):raise ValueError('legacy ledger changed')
    budget=PhaseBudget(CAMPAIGN/'phase-cpu-budget',identity={'protocol_sha256':digest(protocol),
        'source_sha256':program['source_sha256']},phase_cpu_seconds={'feasibility':900})
    snapshot=budget.snapshot()
    if any(a['state']!='settled' for a in snapshot['attempts'].values()):raise ValueError('unsettled campaign worker')
    used=snapshot['charged_cpu_seconds']['feasibility']
    if index in (7,9) and 900-used<sum(a['cpu_seconds']+2 for a in trials[index:index+2]):
        raise ValueError('insufficient prospective reservation for complete repeat pair')
    if 900-used<trial['cpu_seconds']+2:raise ValueError('insufficient prospective reservation; leave attempt unstarted')
    inputs={}
    for name,entry in program['inputs'].items():
        actual=hashed(Path(entry['path']))
        if actual!=entry:raise ValueError('registered input changed: '+name)
        inputs[name]=entry
    needs_prior=trial['method'] in ('repair','indexed_fresh') or trial['use_candidates']
    if needs_prior:
        base=CAMPAIGN/'attempts/prepare-001'
        for name,rel in [('prior_progress','outputs/progress.json'),('prior_receipt','worker/result.json'),('prior_plan','plan.json')]:
            inputs[name]=hashed(base/rel)
        artifact='prior_state' if trial['method'] in ('repair','indexed_fresh') else 'prior_model'
        inputs[artifact]=hashed(base/'outputs'/('state.bin' if artifact=='prior_state' else 'model.bin'))
    attempt=CAMPAIGN/'attempts'/attempt_id;attempt.mkdir(parents=True)
    plan=dict(schema='fixed-timing-worker-plan-v23',program_sha256=digest(raw),inputs=inputs,
        source_sha256=program['source_sha256'],checkpoint=str(ROOT/'tmp/models/distilgpt2'),
        output=str(attempt/'outputs'),protocol_sha256=digest(protocol),phase='feasibility',
        original_record_ids=ORIGINAL,record_ids=ORIGINAL if trial['method']=='prepare' else ORIGINAL[1:],
        deleted_ids=[] if trial['method']=='prepare' else ORIGINAL[:1],
        method=trial['method'],use_candidates=trial['use_candidates'],controller_amendment_sha256=amendment_sha)
    path=attempt/'plan.json';atomic_write(path,canonical_json(plan))
    atomic_write(attempt/'runtime.json',canonical_json(runtime))
    receipt=run_limited([sys.executable,str(source/'scripts/run_fixed_timing_v23.py'),str(path)],
        attempt/'worker',WorkerLimits(trial['wall_seconds'],trial['cpu_seconds'],6*2**30,1,
        tuple(program['affinity_cpus'])),identity={'campaign':'fixed-feature-v23','attempt_id':attempt_id,
        'plan_sha256':digest(path.read_bytes())},cwd=source,phase_budget=budget,phase='feasibility')
    receipt_sha=digest((attempt/'worker/result.json').read_bytes())
    elapsed=time.perf_counter_ns()-start
    transaction=dict(schema='fixed-timing-transaction-v23',attempt_id=attempt_id,
        outer_transaction_elapsed_ns=elapsed,receipt_sha256=receipt_sha,
        timing_scope=program['primary_clock'],worker_outcome=receipt['outcome'],
        budget_debit=receipt['budget_debit'])
    atomic_write(attempt/'transaction.json',canonical_json(transaction))
    print(json.dumps(transaction))


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--register',action='store_true');group.add_argument('--id')
    args=parser.parse_args()
    with research_worker_lock(ROOT):
        register() if args.register else launch(args.id)


if __name__=='__main__':main()
