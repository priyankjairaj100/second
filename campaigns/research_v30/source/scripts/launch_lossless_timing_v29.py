"""Register a separate local lossless-baseline pilot without resetting old ledgers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
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

C = ROOT/'campaigns/lossless_timing_v29'
CAP = 240
CPU_CAP = 76
PRIOR = {'fixed_feature_v23':639, 'compressed_v25b':7, 'compressed_v25c':8,
         'compressed_v25d':4, 'compressed_v26b':32, 'compressed_v27':8,
         'compressed_timing_v27':143, 'compressed_v28':5, 'compressed_timing_v28':52}
CONTROLLERS = ['scripts/launch_lossless_timing_v29.py', 'src/worker_control.py',
    'src/run_store.py', 'src/phase_budget.py', 'src/pilot_budget.py',
    'src/runtime_contract.py', 'src/experiment_inventory.py']
IDS = ('wikitext2:train:article-row-27113', 'wikitext2:train:article-row-5326')
METHODS = {'repair-001':'repair', 'indexed-001':'indexed_fresh', 'cold-001':'model_only_fresh'}


def hashed(path):
    with path.open('rb') as stream:
        return dict(path=str(path), sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def old_ledgers():
    rows = {}
    for name, charge in PRIOR.items():
        raw = (ROOT/'campaigns'/name/'phase-cpu-budget/ledger.json').read_bytes()
        attempts = json.loads(raw)['attempts'].values()
        if sum(r['charged_cpu_seconds'] for r in attempts) != charge:
            raise ValueError('prior charge changed: '+name)
        if name != 'fixed_feature_v23' and any(r['state'] != 'settled' for r in attempts):
            raise ValueError('unexpected unsettled prior worker')
        rows[name] = dict(sha256=digest(raw), charged_or_reserved_cpu_seconds=charge)
    if sum(PRIOR.values()) != 898 or inherited_allowance(ROOT) != (10775, 25):
        raise ValueError('historical budget checkpoint differs')
    return rows


def register():
    if C.exists():
        raise ValueError('campaign already exists; never overwrite a registration')
    ledgers = old_ledgers()
    audit_dir = ROOT/'campaigns/lossless_state_audit_v29b'
    audit = json.loads((audit_dir/'summary.json').read_bytes())
    if audit['status'] != 'complete' or not audit['artifacts_saved']:
        raise ValueError('lossless archive prerequisite failed')
    for name in ('all_complete_models_preserved', 'all_retained_descriptors_unchanged',
                 'all_state_roundtrips_canonical'):
        if audit.get(name) is not True:
            raise ValueError('archive prerequisite failed: '+name)
    original = audit['generations']['prepare-001']
    retained = audit['generations']['repair-001']
    prior = audit_dir/'original.bin'
    if hashed(prior)['sha256'] != original['complete_state_sha256']:
        raise ValueError('original lossless state changed')
    common = json.loads((ROOT/'campaigns/fixed_feature_v23/program.json').read_bytes())['inputs']
    indexed_inputs = dict(common, prior_state=hashed(prior),
        archive_summary=hashed(audit_dir/'summary.json'), archive_plan=hashed(audit_dir/'plan.json'))
    source = C/'source'
    for folder in ('src', 'scripts'):
        (source/folder).mkdir(parents=True)
        for path in sorted((ROOT/folder).glob('*.py')):
            shutil.copyfile(path, source/folder/path.name)
    order = list(METHODS)
    random.Random(29).shuffle(order)
    program = dict(schema='lossless-timing-program-v29', status='prospectively_registered',
        source_sha256=source_hashes(source),
        controller_sha256={p:digest((ROOT/p).read_bytes()) for p in CONTROLLERS},
        historical_frozen_ledgers=ledgers, historical_phase_held_cpu_seconds=898,
        historical_phase_cap_cpu_seconds=900, legacy_charged_cpu_seconds=10775,
        legacy_cap_cpu_seconds=10800, separate_phase_cpu_cap_seconds=CAP,
        budget_policy='new bounded local phase; historical allowances remain sealed and are not pooled or reset',
        authorization='user requested continuation after the V28 checkpoint; local pilot only; no paid compute',
        trials=[dict(id=name, method=METHODS[name], cpu_seconds=CPU_CAP, wall_seconds=100) for name in order],
        order_seed=29, order_scope='one prospectively fixed permutation; not randomized replication',
        inputs_by_method={'repair':indexed_inputs, 'indexed_fresh':indexed_inputs, 'model_only_fresh':common},
        checkpoint=str(ROOT/'tmp/models/distilgpt2'), record_ids=list(IDS[1:]), deleted_ids=list(IDS[:1]),
        expected_model_sha256=retained['model_sha256'], expected_state_sha256=retained['complete_state_sha256'],
        use_candidates=False, affinity_cpus=[min(os.sched_getaffinity(0))], address_space_bytes=6*2**30,
        primary_clock='controller transaction after input/bootstrap gates through sealed worker receipt and its hash',
        secondary_clock='worker receipt wall time; body and service clocks are diagnostic only',
        repair_access='original lossless state, retained tokens, checkpoint, and trusted archive bindings',
        indexed_access='same retained compressed evidence and numerical path as repair',
        cold_access='registered token manifest and checkpoint; only retained tokens enter calibration; no prior model, features, or archive',
        output_contract='repair/indexed: complete model and state; cold: complete model only',
        preparation='archive conversion cost disclosed separately; ordinary original preparation not retimed',
        stop_policy='one trial per method; stop on failure, exactness mismatch, or insufficient reservation; no retry',
        scope='one tiny development request; mandatory lossless baseline; no broad quality or reliability claim',
        os_cache='uncontrolled', other_machine_activity='uncontrolled',
        native_compile='charged in each fresh process; no shared binary cache',
        confirmation=False, quality_evaluation=False, scientific_promotion=False,
        registered_from_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    raw = canonical_json(program)
    atomic_write(C/'program.json', raw)
    protocol = canonical_json(dict(schema='lossless-timing-policy-v29', program_sha256=digest(raw),
        phase_cpu_seconds={'feasibility':CAP}, historical_frozen_ledgers=ledgers))
    atomic_write(C/'protocol.json', protocol)
    atomic_write(C/'registration.json', canonical_json(dict(program_sha256=digest(raw),
        protocol_sha256=digest(protocol), runtime=capture_runtime_contract())))
    atomic_write(C/'registered-launcher.py', Path(__file__).read_bytes())
    print(json.dumps(dict(registered=True, program_sha256=digest(raw), separate_cpu_cap=CAP, order=order)))


def completed(attempt):
    tx = json.loads((attempt/'transaction.json').read_bytes())
    if tx['worker_outcome']['status'] != 'complete':
        raise ValueError('previous worker did not complete')
    if tx['receipt_sha256'] != digest((attempt/'worker/result.json').read_bytes()):
        raise ValueError('previous receipt binding differs')
    terminal_path = attempt/'outputs/completion.json'
    live_path = attempt/'outputs/progress.json'
    sealed_path = attempt/'sealed-progress.json'
    terminal = terminal_path.read_bytes()
    if json.loads(terminal)['status'] != 'complete':
        raise ValueError('previous terminal record is incomplete')
    if (not live_path.exists() or not sealed_path.exists()
            or terminal != live_path.read_bytes() or terminal != sealed_path.read_bytes()):
        sidecar = attempt/'recheck-progress-discrepancy.json'
        if not sidecar.exists():
            with sidecar.open('xb') as stream:
                stream.write(canonical_json(dict(schema='lossless-progress-recheck-v29',
                    cause='unknown', raw_preserved=True, terminal_sha256=digest(terminal),
                    live_sha256=digest(live_path.read_bytes()) if live_path.exists() else None,
                    sealed_sha256=digest(sealed_path.read_bytes()) if sealed_path.exists() else None)))
        raise ValueError('previous terminal evidence differs')


def run(trial_id):
    raw = (C/'program.json').read_bytes()
    program = json.loads(raw)
    protocol = (C/'protocol.json').read_bytes()
    if json.loads(protocol)['program_sha256'] != digest(raw):
        raise ValueError('program binding changed')
    if old_ledgers() != program['historical_frozen_ledgers']:
        raise ValueError('historical ledgers changed')
    if {p:digest((ROOT/p).read_bytes()) for p in CONTROLLERS} != program['controller_sha256']:
        raise ValueError('controller changed')
    source = C/'source'
    if source_hashes(source) != program['source_sha256']:
        raise ValueError('frozen source changed')
    if capture_runtime_contract() != json.loads((C/'registration.json').read_bytes())['runtime']:
        raise ValueError('runtime changed')
    index = next(i for i,t in enumerate(program['trials']) if t['id'] == trial_id)
    trial = program['trials'][index]
    for prior in program['trials'][:index]:
        completed(C/'attempts'/prior['id'])
    inputs = program['inputs_by_method'][trial['method']]
    for name, entry in inputs.items():
        if hashed(Path(entry['path'])) != entry:
            raise ValueError('input changed: '+name)
    budget = PhaseBudget(C/'phase-cpu-budget', identity={'protocol_sha256':digest(protocol),
        'source_sha256':program['source_sha256']}, phase_cpu_seconds={'feasibility':CAP})
    snapshot = budget.snapshot()
    if any(row['state'] != 'settled' for row in snapshot['attempts'].values()):
        raise ValueError('unsettled worker in this new phase')
    if CAP-snapshot['charged_cpu_seconds']['feasibility'] < trial['cpu_seconds']+2:
        raise ValueError('insufficient full reservation; leave trial unstarted')
    attempt = C/'attempts'/trial_id
    attempt.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter_ns()
    plan = {k:program[k] for k in ('source_sha256','checkpoint','record_ids','deleted_ids',
        'use_candidates','expected_model_sha256','expected_state_sha256')}
    plan.update(program_sha256=digest(raw), protocol_sha256=digest(protocol), phase='feasibility',
        method=trial['method'], inputs=inputs, output=str(attempt/'outputs'))
    path = attempt/'plan.json'
    atomic_write(path, canonical_json(plan))
    receipt = run_limited([sys.executable,str(source/'scripts/run_lossless_timing_v29.py'),str(path)],
        attempt/'worker', WorkerLimits(trial['wall_seconds'],trial['cpu_seconds'],6*2**30,1,
        tuple(program['affinity_cpus'])), identity={'campaign':'lossless-v29','plan_sha256':digest(path.read_bytes())},
        cwd=source,phase_budget=budget,phase='feasibility')
    receipt_sha = digest((attempt/'worker/result.json').read_bytes())
    elapsed = time.perf_counter_ns()-started
    snapshot = budget.snapshot()
    atomic_write(attempt/'transaction.json', canonical_json(dict(schema='lossless-timing-receipt-v29',
        worker_outcome=receipt['outcome'], receipt_sha256=receipt_sha, controller_elapsed_ns=elapsed,
        scope=program['primary_clock'], budget=snapshot, historical_held_cpu_seconds=11673,
        combined_charged_or_reserved_cpu_seconds=11673+snapshot['charged_cpu_seconds']['feasibility'])))
    live = attempt/'outputs/progress.json'
    terminal = attempt/'outputs/completion.json'
    if live.exists():
        atomic_write(attempt/'sealed-progress.json', live.read_bytes())
    if receipt['outcome']['status'] == 'complete':
        if not terminal.exists() or terminal.read_bytes() != live.read_bytes():
            atomic_write(attempt/'progress-discrepancy.json', canonical_json(dict(
                schema='lossless-progress-discrepancy-v29', cause='unknown', raw_preserved=True,
                live_sha256=digest(live.read_bytes()) if live.exists() else None,
                terminal_sha256=digest(terminal.read_bytes()) if terminal.exists() else None)))
            raise ValueError('terminal evidence differs; stop and preserve both records')
        completed(attempt)
    print(json.dumps(dict(trial=trial_id,status=receipt['outcome']['status'],seconds=elapsed/1e9,
        charged=receipt['budget_debit']['charged_cpu_seconds'],phase_charge=snapshot['charged_cpu_seconds']['feasibility'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--register', action='store_true')
    group.add_argument('--run', choices=list(METHODS))
    args = parser.parse_args()
    with research_worker_lock(ROOT):
        register() if args.register else run(args.run)
