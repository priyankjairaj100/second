"""Freeze one bounded real-data stage pilot without resetting its CPU allowance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.run_store import atomic_write, canonical_json, digest
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.worker_control import WorkerLimits, run_limited
from src.pilot_budget import inherited_allowance, research_worker_lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--program', type=Path, default=Path('program.json'))
    args = parser.parse_args()
    if not args.id.replace('-', '').isalnum():
        raise ValueError('invalid attempt ID')
    root = Path(__file__).resolve().parents[1]
    archive = root/'pilots/v16'
    program_path = args.program if args.program.is_absolute() else archive/args.program
    program_raw = program_path.read_bytes()
    program = json.loads(program_raw)
    if program['scope'] != 'first_qkv_stage_only' or program['status'] != 'prospectively_registered':
        raise ValueError('the registered stage program is unavailable')
    family = program.get('family', 'whole')
    if family not in ('whole', 'block'):
        raise ValueError('unsupported speculative solver family')
    cpu_seconds, wall_seconds = program['cpu_seconds'], program['wall_seconds']
    if any(type(value) is not int or not 1 <= value <= 450 for value in (cpu_seconds, wall_seconds)):
        raise ValueError('stage workers require positive limits no greater than 450 seconds')
    attempt = archive/args.id
    if attempt.exists():
        raise ValueError('attempt exists; prior evidence cannot be overwritten')
    used, remaining = inherited_allowance(root)
    if remaining < cpu_seconds + 2:
        raise ValueError('insufficient inherited allowance for the bounded worker')
    datasets = []
    for row in program['datasets']:
        path = root/row['records']
        raw = path.read_bytes()
        if digest(raw) != row['records_sha256']:
            raise ValueError('registered real records changed')
        datasets.append(dict(row, records=str(path)))
    snapshot = attempt/'source'
    snapshot.mkdir(parents=True)
    for folder in ('src', 'scripts'):
        (snapshot/folder).mkdir()
        for path in (root/folder).glob('*.py'):
            shutil.copyfile(path, snapshot/folder/path.name)
    policy = dict(schema='speculative-stage-policy-v16', attempt_id=args.id,
        program_sha256=digest(program_raw), scope=program['scope'],
        inherited_cap_cpu_seconds=10800, prior_charged_cpu_seconds=used,
        remaining_allowance_cpu_seconds=remaining, wall_seconds=wall_seconds, cpu_seconds=cpu_seconds,
        solver_family=family,
        address_space_bytes=6*2**30, threads=1, cpu_count=1,
        os_cache='uncontrolled', other_machine_activity='uncontrolled',
        scientific_promotion=False, complete_model=False, complete_state=False,
        numerical_target='unchanged dyadic24 row target; first qkv only; original normalization 32',
        comparison='shared speculative solver with nearest or prior-code initialization; sequential reference',
        failure_rule='preserve every failure; abort remaining cells on any code mismatch')
    atomic_write(attempt/'protocol.json', canonical_json(policy))
    ph = digest(canonical_json(policy))
    checkpoint = root/'tmp/models/distilgpt2'
    hashes = {}
    for name in ('config.json', 'model.safetensors'):
        with (checkpoint/name).open('rb') as stream:
            hashes[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    plan = dict(checkpoint=str(checkpoint), checkpoint_sha256=hashes,
        datasets=datasets, row_batch_size=program['row_batch_size'], family=family,
        output=str(attempt/'outputs'), source_sha256=source_hashes(snapshot), protocol_sha256=ph,
        launcher_sha256=digest(Path(__file__).read_bytes()), program_sha256=digest(program_raw))
    plan_path = attempt/'plan.json'
    atomic_write(plan_path, canonical_json(plan))
    from src.runtime_contract import capture_runtime_contract
    atomic_write(attempt/'runtime.json', canonical_json(capture_runtime_contract()))
    limits = WorkerLimits(wall_seconds, cpu_seconds, 6*2**30, 1, (min(os.sched_getaffinity(0)),))
    budget = PhaseBudget(attempt/'phase-cpu-budget',
        identity={'protocol_sha256':ph, 'source_sha256':source_hashes(snapshot)},
        phase_cpu_seconds={'feasibility':remaining})
    result = run_limited([sys.executable, str(snapshot/'scripts/run_speculative_pilot.py'), str(plan_path)],
        attempt/'worker', limits, identity={'pilot':'speculative-first-stage-v16',
            'plan_sha256':digest(plan_path.read_bytes())}, cwd=snapshot, phase_budget=budget, phase='feasibility')
    print(json.dumps({'outcome':result['outcome'], 'budget_debit':result.get('budget_debit'),
        'resource_usage':result.get('resource_usage')}))


if __name__ == '__main__':
    with research_worker_lock(Path(__file__).resolve().parents[1]):
        main()
