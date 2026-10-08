"""Register a diagnostic screen within the remaining fixed-feature allowance."""
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
C=ROOT/'campaigns/compressed_v25c'
PREVIOUS=ROOT/'campaigns/compressed_v25b'
PARENT=ROOT/'campaigns/fixed_feature_v23'
CONTROLLER_FILES=['scripts/launch_preconditioned_screen_v25.py','src/worker_control.py','src/run_store.py',
                  'src/phase_budget.py','src/pilot_budget.py','src/runtime_contract.py','src/experiment_inventory.py']


def hashed(p):
    with p.open('rb') as f:return dict(path=str(p),sha256=hashlib.file_digest(f,'sha256').hexdigest())


def register():
    if C.exists():raise ValueError('campaign already registered')
    parent=(PARENT/'phase-cpu-budget/ledger.json').read_bytes();ledger=json.loads(parent)
    spent=sum(row['charged_cpu_seconds'] for row in ledger['attempts'].values())
    if spent!=639 or inherited_allowance(ROOT)!=(10775,25):raise ValueError('budget checkpoint differs')
    previous=(PREVIOUS/'phase-cpu-budget/ledger.json').read_bytes()
    previous_ledger=json.loads(previous)
    if sum(r['charged_cpu_seconds'] for r in previous_ledger['attempts'].values())!=7 or any(r['state']!='settled' for r in previous_ledger['attempts'].values()):raise ValueError('previous screen budget differs')
    source=C/'source';source.mkdir(parents=True)
    files=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD','src','scripts'],cwd=ROOT,text=True).splitlines()
    for name in files:
        if not name.endswith('.py'):continue
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT))
    shutil.copyfile(ROOT/'scripts/run_preconditioned_screen_v25.py',source/'scripts/run_preconditioned_screen_v25.py')
    shutil.copyfile(ROOT/'src/preconditioned_box_certificate.py',source/'src/preconditioned_box_certificate.py')
    generation=PARENT/'attempts/repair-001'
    inputs=dict(state=generation/'outputs/state.bin',generation_progress=generation/'outputs/progress.json',
        generation_receipt=generation/'worker/result.json',generation_plan=generation/'plan.json',
        base_target=generation/'outputs/base-target.json',weights=ROOT/'tmp/models/distilgpt2/model.safetensors')
    value=dict(schema='preconditioned-stage-screen-program-v25',status='prospectively_registered',
        follows_completed_program='campaigns/compressed_v25b/program.json',
        purpose='test stronger proved certificate on the same24bit box; preserve baseline rejection',
        previous_ledger_sha256=digest(previous),previous_charged_cpu_seconds=7,
        source_sha256=source_hashes(source),controller_sha256={p:digest((ROOT/p).read_bytes()) for p in CONTROLLER_FILES},
        inputs={k:hashed(p) for k,p in inputs.items()},stage_id='block.0000.qkv',
        weight_key='transformer.h.0.attn.c_attn.weight',retained_record_id='wikitext2:train:article-row-5326',
        precisions=[24],block_size=256,normalization=32,ridge=[1,100],
        trial=dict(id='preconditioned-screen-001',cpu_seconds=40,wall_seconds=60,address_space_bytes=4*2**30),
        phase_cpu_cap_seconds=254,affinity_cpus=[min(os.sched_getaffinity(0))],threads=1,
        parent_ledger_sha256=digest(parent),parent_charged_or_reserved_cpu_seconds=639,
        prior_combined_phase_charged_or_reserved_cpu_seconds=646,
        unchanged_combined_fixed_feature_cap_seconds=900,legacy_charged_cpu_seconds=10775,
        budget_policy='delegate only the remaining254seconds; both prior ledgers frozen; prior7seconds counted; child charges add once; no new allowance',
        numerical_target='existing exact fixed-nearest-feature quantizer',
        source_policy='HEAD numerical snapshot plus new screen worker and reviewed preconditioned verifier; service files excluded',
        computation='archived real factors and bound first-stage weights; all rows; native exact point solves and box verification',
        comparisons='actual factor oracle, lower and upper endpoints, baseline and preconditioned universal certificate at24bits',
        gate='any full-stage certificate accepted with exact archived codes before full compressed-service pilot',
        witness_scope='different endpoint codes refute universal constancy on this box, not every compression scheme',
        stop_policy='stop on provenance mismatch, incorrect code, resource failure; preserve rejected boxes; no automatic tuning',
        confirmation=False,full_model=False,quality_evaluation=False,
        registered_from_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    raw=canonical_json(value);atomic_write(C/'program.json',raw)
    atomic_write(C/'protocol.json',canonical_json(dict(schema='compressed-screen-policy-v25',program_sha256=digest(raw),
        phase_cpu_seconds={'feasibility':254},parent_ledger_sha256=digest(parent),previous_ledger_sha256=digest(previous))))
    atomic_write(C/'registration.json',canonical_json(dict(runtime=capture_runtime_contract(),program_sha256=digest(raw))))
    print(json.dumps(dict(registered=True,program_sha256=digest(raw),child_ceiling=254,parent_frozen_charge=646)))


def run():
    raw=(C/'program.json').read_bytes();program=json.loads(raw);protocol=(C/'protocol.json').read_bytes()
    if json.loads(protocol)['program_sha256']!=digest(raw):raise ValueError('program binding differs')
    if {p:digest((ROOT/p).read_bytes()) for p in CONTROLLER_FILES}!=program['controller_sha256']:raise ValueError('controller changed')
    if digest((PARENT/'phase-cpu-budget/ledger.json').read_bytes())!=program['parent_ledger_sha256']:raise ValueError('parent budget is not frozen')
    if digest((PREVIOUS/'phase-cpu-budget/ledger.json').read_bytes())!=program['previous_ledger_sha256']:raise ValueError('previous ledger changed')
    if inherited_allowance(ROOT)!=(10775,25):raise ValueError('legacy budget changed')
    source=C/'source'
    if source_hashes(source)!=program['source_sha256']:raise ValueError('worker source changed')
    runtime=capture_runtime_contract()
    if runtime!=json.loads((C/'registration.json').read_bytes())['runtime']:raise ValueError('registered runtime differs')
    attempt=C/'attempts'/program['trial']['id']
    if attempt.exists():raise ValueError('attempt already exists')
    for key,entry in program['inputs'].items():
        if hashed(Path(entry['path']))!=entry:raise ValueError('input changed: '+key)
    budget=PhaseBudget(C/'phase-cpu-budget',identity={'protocol_sha256':digest(protocol),'source_sha256':program['source_sha256']},
        phase_cpu_seconds={'feasibility':254})
    if any(r['state']!='settled' for r in budget.snapshot()['attempts'].values()):raise ValueError('unsettled child worker')
    attempt.mkdir(parents=True);start=time.perf_counter_ns()
    plan=dict(program_sha256=digest(raw),protocol_sha256=digest(protocol),source_sha256=program['source_sha256'],
        inputs=program['inputs'],output=str(attempt/'outputs'),stage_id=program['stage_id'],weight_key=program['weight_key'],
        retained_record_id=program['retained_record_id'],precisions=program['precisions'],block_size=program['block_size'])
    path=attempt/'plan.json';atomic_write(path,canonical_json(plan))
    receipt=run_limited([sys.executable,str(source/'scripts/run_preconditioned_screen_v25.py'),str(path)],attempt/'worker',
        WorkerLimits(60,40,4*2**30,1,tuple(program['affinity_cpus'])),
        identity={'campaign':'preconditioned-stage-v25','plan_sha256':digest(path.read_bytes())},cwd=source,
        phase_budget=budget,phase='feasibility')
    receipt_sha=digest((attempt/'worker/result.json').read_bytes());elapsed=time.perf_counter_ns()-start
    report=dict(schema='compressed-screen-receipt-v25',worker_outcome=receipt['outcome'],receipt_sha256=receipt_sha,
        controller_elapsed_ns=elapsed,scope='complete diagnostic worker, not repair latency',budget=budget.snapshot(),
        prior_combined_phase_charged_or_reserved_cpu_seconds=646,
        combined_phase_charged_or_reserved_cpu_seconds=646+budget.snapshot()['charged_cpu_seconds']['feasibility'])
    atomic_write(attempt/'transaction.json',canonical_json(report))
    if (attempt/'outputs/progress.json').exists():atomic_write(attempt/'sealed-progress.json',(attempt/'outputs/progress.json').read_bytes())
    print(json.dumps(dict(status=receipt['outcome']['status'],seconds=elapsed/1e9,
        charged=receipt['budget_debit']['charged_cpu_seconds'],combined_charge=report['combined_phase_charged_or_reserved_cpu_seconds'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--register',action='store_true');g.add_argument('--run',action='store_true');args=parser.parse_args()
    with research_worker_lock(ROOT):register() if args.register else run()
