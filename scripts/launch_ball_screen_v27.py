"""Register a precision/cost diagnostic within the original fixed-feature cap."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.run_store import atomic_write, canonical_json, digest
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.worker_control import WorkerLimits, run_limited
from src.pilot_budget import inherited_allowance, research_worker_lock
from src.runtime_contract import capture_runtime_contract

C = ROOT/'campaigns/compressed_v27'
PRIOR = {'campaigns/fixed_feature_v23': 639, 'campaigns/compressed_v25b': 7,
         'campaigns/compressed_v25c': 8, 'campaigns/compressed_v25d': 4, 'campaigns/compressed_v26b': 32}
CONTROLLERS = ['scripts/launch_ball_screen_v27.py', 'src/worker_control.py',
    'src/run_store.py', 'src/phase_budget.py', 'src/pilot_budget.py',
    'src/runtime_contract.py', 'src/experiment_inventory.py']
ADDITIONS = ['scripts/run_ball_screen_v27.py', 'src/fixed_factor_codec_v26.py',
             'src/preconditioned_box_certificate.py', 'src/native_box_certificate.py', 'src/ball_box_certificate_v27.py']


def hashed(path):
    with path.open('rb') as stream:
        return dict(path=str(path), sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def prior_ledgers():
    result = {}
    for name, expected in PRIOR.items():
        path = ROOT/name/'phase-cpu-budget/ledger.json'
        raw = path.read_bytes()
        rows = json.loads(raw)['attempts'].values()
        if sum(r['charged_cpu_seconds'] for r in rows) != expected:
            raise ValueError('prior budget changed: '+name)
        if name != 'campaigns/fixed_feature_v23' and any(r['state'] != 'settled' for r in rows):
            raise ValueError('unsettled prior diagnostic')
        result[name] = dict(sha256=digest(raw), charged_or_reserved_cpu_seconds=expected)
    return result


def register():
    if C.exists():
        raise ValueError('campaign already registered')
    ledgers = prior_ledgers()
    if inherited_allowance(ROOT) != (10775, 25):
        raise ValueError('legacy budget changed')
    source = C/'source'
    source.mkdir(parents=True)
    files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', 'HEAD', 'src', 'scripts'], cwd=ROOT, text=True).splitlines()
    for name in files:
        if name.endswith('.py'):
            dest = source/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(subprocess.check_output(['git', 'show', 'HEAD:'+name], cwd=ROOT))
    for name in ADDITIONS:
        shutil.copyfile(ROOT/name, source/name)
    generation = ROOT/'campaigns/fixed_feature_v23/attempts/repair-001'
    inputs = dict(state=generation/'outputs/state.bin', generation_progress=generation/'outputs/progress.json',
        generation_receipt=generation/'worker/result.json', generation_plan=generation/'plan.json',
        base_target=generation/'outputs/base-target.json', weights=ROOT/'tmp/models/distilgpt2/model.safetensors')
    program = dict(schema='ball-stage-program-v27', status='prospectively_registered',
        purpose='test fast-ball universal verification cost at40bits against the prior interval verifier',
        follows_completed_program='campaigns/compressed_v26b/program.json',
        source_sha256=source_hashes(source), controller_sha256={p:digest((ROOT/p).read_bytes()) for p in CONTROLLERS},
        inputs={k:hashed(p) for k,p in inputs.items()}, stage_id='block.0000.qkv',
        weight_key='transformer.h.0.attn.c_attn.weight', retained_record_id='wikitext2:train:article-row-5326',
        precisions=[40], block_size=256, normalization=32, ridge=[1,100],
        trial=dict(id='ball-screen-001', cpu_seconds=30, wall_seconds=50, address_space_bytes=4*2**30),
        phase_cpu_cap_seconds=210, prior_frozen_ledgers=ledgers, prior_combined_phase_charge=690,
        unchanged_combined_fixed_feature_cap_seconds=900, legacy_charged_cpu_seconds=10775,
        budget_policy='delegate only210remaining seconds; frozen prior690counted once; no new allowance',
        affinity_cpus=[min(os.sched_getaffinity(0))], threads=1,
        numerical_target='unchanged exact fixed-nearest-feature quantizer; only evidence precision changes',
        source_policy='HEAD plus explicit codec, preconditioner, interval certificate, ball certificate, and diagnostic worker',
        comparisons='exact true point, lower and upper endpoints, native interval and native ball universal certificates',
        order='40bits only; interval thenball; complete costs includingcompilation andfallback',
        gate='exact ball acceptance with wholecalltime atmost twice coldpointcall allows fullmodel feasibility; this is only a screening heuristic',
        stop_policy='stop on any hash mismatch, incorrect code, invalid enclosure, or resource failure',
        confirmation=False, full_model=False, quality_evaluation=False,
        registered_from_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    raw = canonical_json(program)
    atomic_write(C/'program.json',raw)
    atomic_write(C/'protocol.json',canonical_json(dict(schema='precision-stage-policy-v26',
        program_sha256=digest(raw),phase_cpu_seconds={'feasibility':210},prior_frozen_ledgers=ledgers)))
    atomic_write(C/'registration.json',canonical_json(dict(program_sha256=digest(raw), runtime=capture_runtime_contract())))
    atomic_write(C/'registered-launcher.py',Path(__file__).read_bytes())
    print(json.dumps(dict(registered=True,program_sha256=digest(raw),remaining_cpu_seconds=210)))


def run():
    raw=(C/'program.json').read_bytes()
    program=json.loads(raw)
    protocol=(C/'protocol.json').read_bytes()
    if json.loads(protocol)['program_sha256'] != digest(raw):
        raise ValueError('program binding differs')
    if prior_ledgers() != program['prior_frozen_ledgers'] or inherited_allowance(ROOT) != (10775,25):
        raise ValueError('prior budgets changed')
    if {p:digest((ROOT/p).read_bytes()) for p in CONTROLLERS} != program['controller_sha256']:
        raise ValueError('controller changed')
    source=C/'source'
    if source_hashes(source) != program['source_sha256']:
        raise ValueError('numerical source changed')
    if capture_runtime_contract() != json.loads((C/'registration.json').read_bytes())['runtime']:
        raise ValueError('runtime changed')
    for key,entry in program['inputs'].items():
        if hashed(Path(entry['path'])) != entry:
            raise ValueError('input changed: '+key)
    budget=PhaseBudget(C/'phase-cpu-budget',identity={'protocol_sha256':digest(protocol),'source_sha256':program['source_sha256']},
        phase_cpu_seconds={'feasibility':210})
    if budget.snapshot()['attempts']:
        raise ValueError('diagnostic already attempted')
    attempt=C/'attempts'/program['trial']['id']
    attempt.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter_ns()
    plan={k:program[k] for k in ('source_sha256','inputs','stage_id','weight_key','retained_record_id','precisions','block_size')}
    plan.update(program_sha256=digest(raw),protocol_sha256=digest(protocol),output=str(attempt/'outputs'))
    plan_path=attempt/'plan.json'
    atomic_write(plan_path,canonical_json(plan))
    receipt=run_limited([sys.executable,str(source/'scripts/run_ball_screen_v27.py'),str(plan_path)],attempt/'worker',
        WorkerLimits(50,30,4*2**30,1,tuple(program['affinity_cpus'])),
        identity={'campaign':'ball-stage-v27','plan_sha256':digest(plan_path.read_bytes())},
        cwd=source,phase_budget=budget,phase='feasibility')
    elapsed=time.perf_counter_ns()-started
    snapshot=budget.snapshot()
    total=690+snapshot['charged_cpu_seconds']['feasibility']
    atomic_write(attempt/'transaction.json',canonical_json(dict(schema='precision-stage-receipt-v26',
        worker_outcome=receipt['outcome'],receipt_sha256=digest((attempt/'worker/result.json').read_bytes()),
        controller_elapsed_ns=elapsed,scope='complete diagnostic worker; not repair latency',budget=snapshot,
        prior_combined_phase_charge=690,combined_phase_charged_or_reserved_cpu_seconds=total)))
    if (attempt/'outputs/progress.json').exists():
        atomic_write(attempt/'sealed-progress.json',(attempt/'outputs/progress.json').read_bytes())
    print(json.dumps(dict(status=receipt['outcome']['status'],seconds=elapsed/1e9,
        charged=receipt['budget_debit']['charged_cpu_seconds'],combined_charge=total)))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--register',action='store_true')
    group.add_argument('--run',action='store_true')
    args=parser.parse_args()
    with research_worker_lock(ROOT):
        register() if args.register else run()
