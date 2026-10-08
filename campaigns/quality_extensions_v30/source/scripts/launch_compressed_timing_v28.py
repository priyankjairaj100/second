"""One prospectively registered complete compressed-repair/replay pair."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.run_store import atomic_write,canonical_json,digest
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.worker_control import WorkerLimits,run_limited
from src.pilot_budget import inherited_allowance,research_worker_lock
from src.runtime_contract import capture_runtime_contract
C=ROOT/'campaigns/compressed_timing_v28'
PRIOR={'campaigns/fixed_feature_v23':639,'campaigns/compressed_v25b':7,
    'campaigns/compressed_v25c':8,'campaigns/compressed_v25d':4,
    'campaigns/compressed_v26b':32,'campaigns/compressed_v27':8,
    'campaigns/compressed_timing_v27':143}
SPARSE_LEDGER=ROOT/'campaigns/compressed_v28/phase-cpu-budget/ledger.json'
PRIOR['campaigns/compressed_v28']=sum(r['charged_cpu_seconds'] for r in json.loads(SPARSE_LEDGER.read_bytes())['attempts'].values())
CAP=900-sum(PRIOR.values())
CPU_CAP=min(52,CAP-2)
CONTROLLERS=['scripts/launch_compressed_timing_v28.py','src/worker_control.py','src/run_store.py',
    'src/phase_budget.py','src/pilot_budget.py','src/runtime_contract.py','src/experiment_inventory.py']
ADDITIONS=['scripts/run_compressed_timing_v28.py','scripts/analyze_compressed_state_v26.py',
    'src/fixed_compressed_service_v27.py','src/fixed_compressed_state_v26.py',
    'src/fixed_factor_codec_v26.py','src/preconditioned_box_certificate.py',
    'src/native_box_certificate.py','src/ball_box_certificate_v27.py','src/ball_box_certificate_v28.py',
    'src/fixed_compressed_service_v28.py']
IDS=('wikitext2:train:article-row-27113','wikitext2:train:article-row-5326')


def hashed(path):
    with path.open('rb') as stream:
        return dict(path=str(path),sha256=hashlib.file_digest(stream,'sha256').hexdigest())


def prior_ledgers():
    rows={}
    for name,charge in PRIOR.items():
        raw=(ROOT/name/'phase-cpu-budget/ledger.json').read_bytes()
        attempts=json.loads(raw)['attempts'].values()
        if sum(r['charged_cpu_seconds'] for r in attempts)!=charge:
            raise ValueError('prior charge changed: '+name)
        if name!='campaigns/fixed_feature_v23' and any(r['state']!='settled' for r in attempts):
            raise ValueError('unsettled diagnostic')
        rows[name]=dict(sha256=digest(raw),charged_or_reserved_cpu_seconds=charge)
    return rows


def register():
    if C.exists():raise ValueError('campaign already exists')
    ledgers=prior_ledgers()
    if inherited_allowance(ROOT)!=(10775,25):raise ValueError('legacy budget changed')
    gate=ROOT/'campaigns/compressed_v28/attempts/sparse-screen-001'
    if CPU_CAP<1:raise ValueError('no remaining complete worker allowance')
    progress=json.loads((gate/'sealed-progress.json').read_bytes())
    receipt=json.loads((gate/'worker/result.json').read_bytes())
    if (progress['status']!='complete' or not progress['permits_full_compressed_pilot']
            or receipt['outcome']['status']!='complete' or receipt['budget_debit']['state']!='settled'):
        raise ValueError('component gate not met')
    source=C/'source';source.mkdir(parents=True)
    files=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD','src','scripts'],cwd=ROOT,text=True).splitlines()
    for name in files:
        if name.endswith('.py'):
            dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT))
    for name in ADDITIONS:shutil.copyfile(ROOT/name,source/name)
    common=json.loads((ROOT/'campaigns/fixed_feature_v23/program.json').read_bytes())['inputs']
    archive=ROOT/'campaigns/compressed_state_audit_v26'
    audit=json.loads((archive/'summary.json').read_bytes())
    if audit['status']!='complete' or not audit['artifacts_saved']:raise ValueError('archive conversion incomplete')
    prior=archive/'original40.bin'
    original=audit['generations']['prepare-001']['precisions']['40']
    if hashed(prior)['sha256']!=original['complete_state_sha256']:raise ValueError('compressed prior changed')
    repair_inputs=dict(common,prior_state=hashed(prior),archive_summary=hashed(archive/'summary.json'),
        archive_plan=hashed(archive/'plan.json'))
    expected_model=audit['generations']['repair-001']['model_sha256']
    expected_state=audit['generations']['repair-001']['precisions']['40']['complete_state_sha256']
    program=dict(schema='sparse-complete-retiming-v28',status='prospectively_registered',
        source_sha256=source_hashes(source),controller_sha256={p:digest((ROOT/p).read_bytes()) for p in CONTROLLERS},
        prior_frozen_ledgers=ledgers,prior_combined_phase_charge=sum(PRIOR.values()),phase_cpu_cap_seconds=CAP,
        unchanged_combined_fixed_feature_cap_seconds=900,legacy_charged_cpu_seconds=10775,
        budget_policy='delegate only the remaining original900second phase balance; all frozen prior charges counted once; no new allowance',
        gate_progress=hashed(gate/'sealed-progress.json'),gate_receipt=hashed(gate/'worker/result.json'),
        inputs_by_method={'repair':repair_inputs,'model_only_fresh':common},
        expected_model_sha256=expected_model,expected_state_sha256=expected_state,
        checkpoint=str(ROOT/'tmp/models/distilgpt2'),original_record_ids=list(IDS),
        record_ids=list(IDS[1:]),deleted_ids=list(IDS[:1]),use_candidates=False,
        bits=40,block_size=256,normalization=32,ridge=[1,100],solver_backend='native_ball',
        certificate_backend='ball',max_neural_stage_record_pairs=24,
        trials=[dict(id='repair-001',method='repair')],
        cpu_seconds=CPU_CAP,wall_seconds=90,address_space_bytes=6*2**30,
        affinity_cpus=[min(os.sched_getaffinity(0))],threads=1,
        primary_clock='controller transaction after input/bootstrap gates through sealed worker receipt and its hash',
        secondary_clock='worker receipt wall time; body clock is diagnostic only',
        repair_access='original compressed state, retained tokens, base checkpoint, trusted conversion metadata; no retained oracle codes or factors',
        cold_access='retained tokens and base checkpoint; no cached factors or previous model',
        comparison='complete compressed repair retiming versus already sealed V27 cold-001; unchanged numerical replay baseline',
        baseline_path='campaigns/compressed_timing_v27/attempts/cold-001',
        baseline_receipt=hashed(ROOT/'campaigns/compressed_timing_v27/attempts/cold-001/worker/result.json'),
        baseline_discrepancy=hashed(ROOT/'campaigns/compressed_timing_v27/attempts/cold-001/progress-discrepancy.json'),
        indexed_baseline='same compressed indexed access shares repair numerical path; no strict dominance claim',
        preparation='archive conversion cost reported separately; not a measured ordinary compressed preparation transaction',
        stop_policy='one repair only; preserve failure/resource exhaustion; no automatic rerun',
        scope='one development retiming with an earlier same-session comparator; no randomized pair or reliability claim',
        os_cache='uncontrolled',other_machine_activity='uncontrolled',
        confirmation=False,quality_evaluation=False,full_model=True,
        registered_from_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    raw=canonical_json(program);atomic_write(C/'program.json',raw)
    atomic_write(C/'protocol.json',canonical_json(dict(schema='compressed-timing-policy-v27',
        program_sha256=digest(raw),phase_cpu_seconds={'feasibility':CAP},prior_frozen_ledgers=ledgers)))
    atomic_write(C/'registration.json',canonical_json(dict(program_sha256=digest(raw),runtime=capture_runtime_contract())))
    atomic_write(C/'registered-launcher.py',Path(__file__).read_bytes())
    print(json.dumps(dict(registered=True,program_sha256=digest(raw),remaining_cpu_seconds=CAP)))


def run(trial_id):
    raw=(C/'program.json').read_bytes();program=json.loads(raw);protocol=(C/'protocol.json').read_bytes()
    if json.loads(protocol)['program_sha256']!=digest(raw):raise ValueError('program binding changed')
    if prior_ledgers()!=program['prior_frozen_ledgers'] or inherited_allowance(ROOT)!=(10775,25):raise ValueError('prior budgets changed')
    if {p:digest((ROOT/p).read_bytes()) for p in CONTROLLERS}!=program['controller_sha256']:raise ValueError('controller changed')
    source=C/'source'
    if source_hashes(source)!=program['source_sha256']:raise ValueError('source changed')
    if capture_runtime_contract()!=json.loads((C/'registration.json').read_bytes())['runtime']:raise ValueError('runtime changed')
    trials=program['trials'];index=next(i for i,t in enumerate(trials) if t['id']==trial_id);trial=trials[index]
    if index:
        previous=C/'attempts'/trials[index-1]['id']
        prior=json.loads((previous/'transaction.json').read_bytes())
        terminal=json.loads((previous/'sealed-progress.json').read_bytes())
        if prior['worker_outcome']['status']!='complete' or terminal['status']!='complete':raise ValueError('previous trial failed')
    inputs=program['inputs_by_method'][trial['method']]
    for key,entry in inputs.items():
        if hashed(Path(entry['path']))!=entry:raise ValueError('input changed: '+key)
    budget=PhaseBudget(C/'phase-cpu-budget',identity={'protocol_sha256':digest(protocol),'source_sha256':program['source_sha256']},
        phase_cpu_seconds={'feasibility':CAP})
    if any(r['state']!='settled' for r in budget.snapshot()['attempts'].values()):raise ValueError('unsettled current worker')
    attempt=C/'attempts'/trial_id;attempt.mkdir(parents=True,exist_ok=False);started=time.perf_counter_ns()
    plan={k:program[k] for k in ('source_sha256','checkpoint','record_ids','deleted_ids','use_candidates',
        'expected_model_sha256','expected_state_sha256')}
    plan.update(program_sha256=digest(raw),protocol_sha256=digest(protocol),phase='feasibility',
        method=trial['method'],inputs=inputs,output=str(attempt/'outputs'))
    path=attempt/'plan.json';atomic_write(path,canonical_json(plan))
    receipt=run_limited([sys.executable,str(source/'scripts/run_compressed_timing_v28.py'),str(path)],attempt/'worker',
        WorkerLimits(90,CPU_CAP,6*2**30,1,tuple(program['affinity_cpus'])),
        identity={'campaign':'sparse-complete-v28','plan_sha256':digest(path.read_bytes())},
        cwd=source,phase_budget=budget,phase='feasibility')
    receipt_sha=digest((attempt/'worker/result.json').read_bytes());elapsed=time.perf_counter_ns()-started
    snapshot=budget.snapshot();total=sum(PRIOR.values())+snapshot['charged_cpu_seconds']['feasibility']
    atomic_write(attempt/'transaction.json',canonical_json(dict(schema='compressed-timing-receipt-v27',
        worker_outcome=receipt['outcome'],receipt_sha256=receipt_sha,controller_elapsed_ns=elapsed,
        scope=program['primary_clock'],budget=snapshot,prior_combined_phase_charge=sum(PRIOR.values()),
        combined_phase_charged_or_reserved_cpu_seconds=total)))
    if (attempt/'outputs/progress.json').exists():atomic_write(attempt/'sealed-progress.json',(attempt/'outputs/progress.json').read_bytes())
    print(json.dumps(dict(trial=trial_id,status=receipt['outcome']['status'],seconds=elapsed/1e9,
        charged=receipt['budget_debit']['charged_cpu_seconds'],combined_charge=total)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--register',action='store_true');group.add_argument('--run',choices=['repair-001','cold-001'])
    args=parser.parse_args()
    with research_worker_lock(ROOT):register() if args.register else run(args.run)
