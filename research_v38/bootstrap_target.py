"""Construct one static target with the unchanged constructors and actual runtime.

This worker does not evaluate records or prepare a calibration service.
A separate published registration and CPU ledger precede its only attempt.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget, read_budget_snapshot
from src.run_store import canonical_json, digest, read_completed, strict_json
from src.runtime_contract import capture_runtime_contract
from src.transaction_timing import verify_command_admission
from src.worker_control import THREAD_VARIABLES, WorkerLimits, run_limited

SCHEMA = 'static-fixed-target-bootstrap-v38'
PHASE = 'feasibility'
CAP = 122
CHECKPOINT_HASHES = {
    'config.json': '4ec5947c1d59fee6212cdf3b0ec1a53eac02092554c5ff0a733488cbd2c64f3a',
    'model.safetensors': 'e1ff18884359fe8beb795a5f414feb85a6ce3d929ad019c0d958c039d2b94a1b',
}
FILES = ('fixed-target.json', 'base-target.json', 'evaluator.json',
         'decoder-implementation.json', 'checkpoint-provenance.json', 'recipe.json')
NO_WORK = dict(neural_stage_record_pairs=0, calibration_records_read=0,
               gram_products=0, quantized_code_decisions=0, service_preparations=0)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe(path):
    path = Path(path).absolute()
    require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
            'Symbolic paths are unsupported')
    require(path == ROOT or ROOT in path.parents, 'Path is outside the repository')
    return path


def hashed(path):
    path = safe(path)
    require(path.is_file(), 'Bound file is missing: ' + str(path))
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    path = safe(path)
    require(path.is_file() and path.stat().st_size <= 32 * 2**20, 'Invalid bounded JSON file')
    raw = path.read_bytes()
    value = strict_json(raw)
    require(type(value) is dict and canonical_json(value) == raw, 'JSON bytes are not canonical')
    return value


def save_new(path, value):
    path = safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json(value)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return digest(raw)


def command(directory):
    return [sys.executable, str(ROOT / 'research_v38/bootstrap_target.py'),
            '--worker-plan', str(directory / 'plan.json')]


def registration(directory):
    directory = safe(directory)
    protocol = read(directory / 'protocol.json')
    plan = read(directory / 'plan.json')
    require(protocol.get('schema') == SCHEMA + '-protocol', 'Bootstrap protocol schema differs')
    require(protocol.get('directory') == str(directory), 'Bootstrap directory differs')
    require(protocol.get('phase_cpu_cap_seconds') == CAP and protocol.get('automatic_retry') is False,
            'Bootstrap budget or retry policy differs')
    require(protocol.get('source_sha256') == source_hashes(ROOT), 'Numerical source files changed')
    require(protocol.get('helper_sha256') == hashed(__file__), 'Bootstrap source changed')
    require(protocol.get('runtime') == capture_runtime_contract(), 'Declared runtime changed')
    expected = dict(schema=SCHEMA + '-plan', protocol_sha256=hashed(directory / 'protocol.json'),
                    output=str(directory / 'outputs'), checkpoint=str(ROOT / 'tmp/models/distilgpt2'),
                    checkpoint_files_sha256=CHECKPOINT_HASHES,
                    source_sha256=protocol['source_sha256'], original_token_count=256,
                    group_count=1, primitive_backend='mpfr_enclosure',
                    identity_encoding='binary64_tree_v2')
    require(plan == expected, 'Bootstrap plan differs from the fixed policy')
    limits = WorkerLimits.from_payload(protocol['limits'])
    require(limits.cpu_seconds == 120 and limits.wall_seconds == 240
            and limits.address_space_bytes == 6 * 2**30 and limits.threads == 1
            and len(limits.affinity_cpus) == 1 and limits.termination_grace_seconds == 1
            and limits.file_size_bytes == 32 * 2**20, 'Bootstrap limits differ')
    for name, expected_hash in CHECKPOINT_HASHES.items():
        require(hashed(Path(plan['checkpoint']) / name) == expected_hash, 'Checkpoint hash differs: ' + name)
    return protocol, plan, limits


def register_bootstrap(directory):
    """Write static registration files. Do not load checkpoint tensors."""
    directory = safe(directory)
    require(not directory.exists(), 'Bootstrap directory already exists; retries are forbidden')
    checkpoint = ROOT / 'tmp/models/distilgpt2'
    for name, expected in CHECKPOINT_HASHES.items():
        require(hashed(checkpoint / name) == expected, 'Checkpoint input differs: ' + name)
    limits = WorkerLimits(240, 120, 6 * 2**30, 1, (min(os.sched_getaffinity(0)),),
                          file_size_bytes=32 * 2**20)
    limits.check_host()
    protocol = dict(schema=SCHEMA + '-protocol', status='registered_before_execution',
        directory=str(directory), source_sha256=source_hashes(ROOT), helper_sha256=hashed(__file__),
        runtime=capture_runtime_contract(), phase_cpu_cap_seconds=CAP, limits=limits.payload(),
        automatic_retry=False, paid_compute=False,
        scope='Static checkpoint identity and fixed target only; no calibration or neural evaluation',
        publication_rule='Publish protocol and plan before launching the worker',
        cost_scope='Separate bootstrap ledger; no debit or speed credit in the main C4 phase',
        identity_scope='New target identity from this host; old runtime facts are never reused')
    protocol_sha = save_new(directory / 'protocol.json', protocol)
    plan = dict(schema=SCHEMA + '-plan', protocol_sha256=protocol_sha,
        output=str(directory / 'outputs'), checkpoint=str(checkpoint),
        checkpoint_files_sha256=CHECKPOINT_HASHES, source_sha256=protocol['source_sha256'],
        original_token_count=256, group_count=1, primitive_backend='mpfr_enclosure',
        identity_encoding='binary64_tree_v2')
    save_new(directory / 'plan.json', plan)
    return dict(schema=SCHEMA + '-registration', status='registered_before_execution',
                protocol_sha256=protocol_sha, plan_sha256=hashed(directory / 'plan.json'),
                phase_cpu_cap_seconds=CAP, numerical_execution=False)


def _construct_static(checkpoint, expected_hashes):
    """Use exactly the constructors called by the frozen service worker."""
    from src.checkpoint_adapter import load_gpt2_checkpoint
    from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
    from src.target_manifest import TargetRecipe
    from src.dyadic_row_target import build_dyadic_row_target
    from src.fixed_anchor_target import build_fixed_anchor_target
    loaded = load_gpt2_checkpoint(checkpoint, identity_encoding='binary64_tree_v2')
    require(loaded.provenance['files_sha256'] == expected_hashes, 'Loaded checkpoint provenance differs')
    decoder = OrderedFiniteDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
    expected_stages = tuple(f'block.{b:04d}.{s}' for b in range(6)
                           for s in ('qkv', 'attn_out', 'mlp_up', 'mlp_down'))
    require(tuple(decoder.stage_ids) == expected_stages, 'Expected all 24 DistilGPT2 stages')
    base = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=256, group_count=1))
    target = build_fixed_anchor_target(decoder, base)
    require(target.digest != base.digest, 'Fixed and sequential targets collide')
    payloads = dict(zip(FILES, (target.payload(), base.payload(), decoder.kernel_manifest,
        decoder.implementation_manifest, loaded.provenance, base.recipe.payload())))
    require(digest(canonical_json(payloads['fixed-target.json'])) == target.digest,
            'Fixed target encoding differs')
    require(digest(canonical_json(payloads['base-target.json'])) == base.digest,
            'Base target encoding differs')
    return payloads, dict(fixed_target_sha256=target.digest, base_target_sha256=base.digest,
                         evaluator_id=decoder.evaluator_id, stage_ids=list(decoder.stage_ids))


def worker(plan_path):
    directory = safe(plan_path).parent
    protocol, plan, limits = registration(directory)
    verify_command_admission(plan['protocol_sha256'], PHASE, command(directory))
    output = safe(plan['output'])
    require(not output.exists(), 'Bootstrap output already exists')
    output.mkdir()
    started = time.perf_counter_ns()
    result = dict(schema=SCHEMA + '-completion', status='failed',
        protocol_sha256=plan['protocol_sha256'], plan_sha256=hashed(plan_path),
        source_sha256=protocol['source_sha256'], helper_sha256=protocol['helper_sha256'],
        runtime=protocol['runtime'], checkpoint_files_sha256=CHECKPOINT_HASHES,
        work_counts=dict(NO_WORK), artifacts={}, scientific_experiment=False,
        confirmation=False, outputs_are_quantized_model=False)
    try:
        # These immutable constructors require actual procfs. Missing files refuse execution.
        payloads, facts = _construct_static(Path(plan['checkpoint']), CHECKPOINT_HASHES)
        for name, value in payloads.items():
            value_hash = save_new(output / name, value)
            result['artifacts'][name] = dict(sha256=value_hash, bytes=(output / name).stat().st_size)
        result.update(facts, status='complete')
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
    result['worker_elapsed_ns'] = time.perf_counter_ns() - started
    result_hash = save_new(output / 'completion.json', result)
    seal = dict(schema=SCHEMA + '-terminal', completion_sha256=result_hash,
                status=result['status'], protocol_sha256=plan['protocol_sha256'])
    seal_hash = save_new(output / 'terminal.json', seal)
    print(canonical_json(dict(schema=SCHEMA + '-stdout', terminal_sha256=seal_hash,
                              status=result['status'])).decode('ascii'), flush=True)
    return 0 if result['status'] == 'complete' else 1


def _identity(protocol, plan):
    return dict(protocol_sha256=plan['protocol_sha256'], source_sha256=protocol['source_sha256'])


def launch_bootstrap(directory):
    """Launch exactly once after the caller publishes the static registration."""
    directory = safe(directory)
    protocol, plan, limits = registration(directory)
    require(not (directory / 'worker').exists() and not (directory / 'outputs').exists(),
            'Bootstrap attempt already exists; retries are forbidden')
    require(not (directory / 'phase-cpu-budget').exists(), 'Bootstrap ledger already exists')
    budget = PhaseBudget(directory / 'phase-cpu-budget', identity=_identity(protocol, plan),
                         phase_cpu_seconds={PHASE: CAP})
    receipt = run_limited(command(directory), directory / 'worker', limits,
        identity=_identity(protocol, plan), cwd=ROOT, phase_budget=budget, phase=PHASE)
    require(receipt['outcome']['status'] == 'complete', 'Bootstrap worker failed; preserve its receipt and stop')
    return verify_bootstrap(directory)


def verify_bootstrap(directory):
    """Verify sealed artifacts and the actual runtime without loading weights."""
    directory = safe(directory)
    protocol, plan, limits = registration(directory)
    identity = _identity(protocol, plan)
    budget_binding = dict(identity=identity, phase_cpu_seconds={PHASE: CAP},
                         scope='trusted_worker_cpu_admission_not_process_tree_containment')
    binding = dict(schema='limited-worker-identity-v1', identity=identity, command=command(directory),
        cwd=str(ROOT), limits=limits.payload(), phase_budget=dict(binding_sha256=digest(canonical_json(budget_binding)),
        phase=PHASE, directory=str(directory / 'phase-cpu-budget')))
    receipt = read_completed(directory / 'worker', binding)
    require(receipt is not None and receipt['outcome']['status'] == 'complete', 'No successful bootstrap receipt')
    require(receipt['outcome']['returncode'] == 0 and receipt.get('limits_applied') is not None,
            'Bootstrap worker limits or exit differ')
    require(receipt['limits'] == limits.payload() and receipt['worker_identity'] == identity,
            'Bootstrap receipt limits or identity differ')
    expected_applied = dict(address_space=[limits.address_space_bytes] * 2,
        cpu_seconds=[limits.cpu_seconds, limits.cpu_seconds + 1],
        file_size=[limits.file_size_bytes] * 2, affinity_cpus=list(limits.affinity_cpus),
        thread_environment={name: str(limits.threads) for name in THREAD_VARIABLES},
        pid=receipt['worker_pid'], process_group=receipt['worker_pid'])
    applied = receipt['limits_applied']
    require({key: applied.get(key) for key in expected_applied} == expected_applied,
            'Applied worker limits differ from registration')
    request = read(directory / 'worker' / receipt['attempt'] / 'request.json')
    require(applied.get('request_sha256') == digest(canonical_json(request)), 'Applied request hash differs')
    require(request['command'] == command(directory) and request['limits'] == limits.payload()
            and request['cwd'] == str(ROOT), 'Applied worker request differs')
    require(type(receipt.get('resource_usage')) is dict
            and receipt['resource_usage'].get('total_cpu_ns') == receipt['budget_debit']['observed_cpu_ns'],
            'Observed CPU use differs from the settled debit')
    ledger = read_budget_snapshot(directory / 'phase-cpu-budget', identity=identity, phase_cpu_seconds={PHASE: CAP})
    require(ledger['status'] == 'verified' and ledger['reserved_unknown_attempts'] == 0
            and len(ledger['attempts']) == 1 and not ledger['over_cap'][PHASE], 'Bootstrap ledger is incomplete')
    require(ledger['attempts'].get(receipt['budget_attempt_id']) == receipt['budget_debit'], 'Bootstrap debit differs')
    output = directory / 'outputs'
    result = read(output / 'completion.json')
    seal = read(output / 'terminal.json')
    require(seal == dict(schema=SCHEMA + '-terminal', completion_sha256=hashed(output / 'completion.json'),
        status='complete', protocol_sha256=plan['protocol_sha256']), 'Bootstrap terminal seal differs')
    summary = read(directory / 'worker' / receipt['attempt'] / 'stdout-summary.json')
    expected_stdout = canonical_json(dict(schema=SCHEMA + '-stdout',
        terminal_sha256=hashed(output / 'terminal.json'), status='complete')) + b'\n'
    require(summary['sha256'] == digest(expected_stdout) and summary['bytes'] == len(expected_stdout)
            and summary['tail_utf8'].encode() == expected_stdout, 'Bootstrap stdout differs')
    require(result['schema'] == SCHEMA + '-completion' and result['status'] == 'complete'
            and result['protocol_sha256'] == plan['protocol_sha256']
            and result['plan_sha256'] == hashed(directory / 'plan.json')
            and result['source_sha256'] == protocol['source_sha256']
            and result['helper_sha256'] == protocol['helper_sha256']
            and result['runtime'] == protocol['runtime']
            and result['checkpoint_files_sha256'] == CHECKPOINT_HASHES, 'Bootstrap completion binding differs')
    require(result['work_counts'] == NO_WORK and result['scientific_experiment'] is False
            and result['confirmation'] is False and result['outputs_are_quantized_model'] is False,
            'Bootstrap scope differs')
    require(set(result['artifacts']) == set(FILES), 'Bootstrap artifact set differs')
    require({p.name for p in output.iterdir()} == set(FILES) | {'completion.json', 'terminal.json'},
            'Bootstrap output contains unexpected files')
    for name, entry in result['artifacts'].items():
        require(entry == dict(sha256=hashed(output / name), bytes=(output / name).stat().st_size),
                'Bootstrap artifact changed: ' + name)
        read(output / name)
    from src.transformer_backend import _runtime_manifest
    from src.finite_primitives import primitive_manifest, _primitive_manifest_bytes
    _runtime_manifest.cache_clear()
    _primitive_manifest_bytes.cache_clear()
    evaluator = read(output / 'evaluator.json')
    require(evaluator['base_parameters']['runtime'] == _runtime_manifest(), 'Actual decoder runtime changed')
    require(evaluator['primitive_backend'] == primitive_manifest('mpfr_enclosure'), 'Actual MPFR runtime changed')
    from src.ordered_finite_decoder_v30 import _implementation_payload
    require(read(output / 'decoder-implementation.json') == _implementation_payload(),
            'Actual decoder implementation differs')
    require(read(output / 'checkpoint-provenance.json')['files_sha256'] == CHECKPOINT_HASHES,
            'Recorded checkpoint provenance differs')
    require(result['evaluator_id'] == 'certified-decoder-v1:' + hashed(output / 'evaluator.json'),
            'Evaluator identity differs')
    target = read(output / 'fixed-target.json')
    base = read(output / 'base-target.json')
    require(result['fixed_target_sha256'] == hashed(output / 'fixed-target.json')
            and result['base_target_sha256'] == hashed(output / 'base-target.json')
            and target['anchor_target_sha256'] == result['base_target_sha256']
            and target['decoder_sha256'] == hashed(output / 'evaluator.json'), 'Target binding differs')
    require(result['stage_ids'] == [f'block.{b:04d}.{s}' for b in range(6)
        for s in ('qkv', 'attn_out', 'mlp_up', 'mlp_down')]
        and [s['stage_id'] for s in base['stages']] == result['stage_ids'], 'Complete stage list differs')
    require(base['recipe'] == read(output / 'recipe.json')
        == dict(schema='fixed-target-recipe-v1', original_token_count=256, bits=4,
                ridge=[1, 100], group_count=1, max_grid_entries=1000000), 'Target recipe differs')
    return dict(schema=SCHEMA + '-audit', status='verified',
        protocol_sha256=plan['protocol_sha256'], plan_sha256=hashed(directory / 'plan.json'),
        completion_sha256=hashed(output / 'completion.json'), terminal_sha256=hashed(output / 'terminal.json'),
        receipt_sha256=hashed(directory / 'worker/result.json'), ledger_sha256=ledger['ledger_sha256'],
        charged_cpu_seconds=ledger['charged_cpu_seconds'][PHASE], phase_cpu_cap_seconds=CAP,
        fixed_target_sha256=result['fixed_target_sha256'], base_target_sha256=result['base_target_sha256'],
        work_counts=dict(NO_WORK), actual_runtime_verified=True, stage_count=24,
        scope='Static target only; not a prepared service, quantized model, or empirical result')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-plan', required=True, type=Path)
    return worker(parser.parse_args().worker_plan.absolute())


if __name__ == '__main__':
    raise SystemExit(main())
