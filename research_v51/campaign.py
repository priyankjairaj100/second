"""One-use real-stage workers with separate fixed limits and sealed accounting."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from research_v43.campaign import read, new, sha, require
from research_v44.campaign import runtime
from research_v45.campaign import bind, bound
from research_v50.campaign import sources as previous_sources
from research_v51.stage import STAGE_ID, HISTORICAL_CODE
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget, read_budget_snapshot
from src.run_store import read_completed, canonical_json
from src.worker_control import WorkerLimits, run_limited

ROOT = Path(__file__).resolve().parents[1]
ORDER = ('prepare', 'candidate', 'reference', 'compressed')
TRIALS = {
    'prepare': dict(cpu_seconds=900, wall_seconds=1200),
    'candidate': dict(cpu_seconds=1200, wall_seconds=1800),
    'reference': dict(cpu_seconds=1800, wall_seconds=2400),
    'compressed': dict(cpu_seconds=1200, wall_seconds=1800),
}
CAPS = {name: limits['cpu_seconds'] + 2 for name, limits in TRIALS.items()}
COMMON = dict(address_space_bytes=16*2**30, threads=1, file_size_bytes=2**30)


def sources():
    result = previous_sources()
    for p in sorted((ROOT/'research_v51').iterdir()):
        if p.is_file() and (p.suffix == '.py' or p.name == 'PROTOCOL.txt'):
            result[str(p.relative_to(ROOT))] = sha(p)
    for name in ('tests/test_transformer_backend.py', 'tests/test_direct_gram_v35.py'):
        result[name] = sha(ROOT/name)
    return result


def budget_identity(d):
    return dict(protocol_sha256=sha(d/'program.json'), source_sha256=source_hashes(ROOT))


def budget(d):
    return PhaseBudget(d/'budget', identity=budget_identity(d), phase_cpu_seconds=CAPS)


def snapshot(d):
    return read_budget_snapshot(d/'budget', identity=budget_identity(d), phase_cpu_seconds=CAPS)


def review():
    from research_v43.dispatcher import StageSpec, assess_stage, ResourcePolicy, RequestLedger
    from research_v45.service import gram_budget
    path = ROOT/'campaigns/ci_scale_v39/attempts/prepare/outputs/base-target.json'
    entry = next(s for s in read(path)['stages'] if s['stage_id'] == STAGE_ID)
    spec = StageSpec.from_manifest(entry, target_sha256=sha(path))
    require((spec.rows, spec.width, spec.normalization) == (768, 3072, 1664), 'Geometry differs')
    policy = ResourcePolicy(); ledger = RequestLedger(policy)
    reports = {}
    for name in ORDER[1:]:
        kind = 'box' if name == 'compressed' else 'point'
        report = assess_stage(spec, 1664, kind=kind, block_tokens=128, max_blocks=13,
            policy=policy, resident_bytes=4*2**30)
        require(report['admitted'] and report['selected_route'] == 'streamed', 'Stage refused')
        ledger.reserve(report); reports[name] = report
    return dict(reference_manifest_sha256=sha(path), reports=reports,
        aggregate_work_units=ledger.work_units, exact_stage_feature_bytes=1664*3072*8,
        source_validation_scope='First registered record also receives a complete 24-stage traversal.',
        hybrid_wide_route='lossless point; no distinct Gram control at width3072',
        native_gram_max_width=gram_budget(1664).max_width,
        memory_scope='4GiB declared caller residency; solver arrays separately admitted; 16GiB OS cap decisive.',
        cpu_scope='New bounded engineering probe; limits do not predict success or expand V45.',
        no_hidden_neural_replay=True, no_point_retry_on_box_refusal=True)


def verify(d):
    d = Path(d).resolve(); p = read(d/'program.json')
    require(p['directory'] == str(d) and p['schema'] == 'real-wide-stage-program-v51' and
        read(d/'registration.json')['program_sha256'] == sha(d/'program.json'), 'Registration differs')
    require(p['sources'] == sources() and p['runtime'] == runtime(), 'Source/runtime changed')
    require(p['trials'] == TRIALS and p['order'] == list(ORDER) and p['caps'] == CAPS and
        p['common_limits'] == COMMON and p['stage_id'] == STAGE_ID and
        p['historical_code_sha256'] == HISTORICAL_CODE and p['review'] == review(), 'Design changed')
    for entry in p['inputs'].values(): bound(entry)
    return p


def register(d, checks):
    require(os.environ.get('SLURM_JOB_ID'), 'Slurm required')
    d = Path(d).resolve(); checks = Path(checks).resolve()
    require(ROOT in d.parents and not d.exists(), 'Fresh path required')
    check = read(checks)
    require(check['status'] == 'passed' and check['sources'] == sources() and
        check['skipped'] == 0 and check['runtime'] == runtime(), 'Passing pinned software checks required')
    old = ROOT/'local_runs/c4-full-model-v45-20261010-a'
    require(sha(old/'program.json') == '02c7f6cfc0240bc34f2a5faec05dfb5392b81d12e5ac4cd95279167ef99c6d50', 'V45 root differs')
    previous = read(old/'program.json')
    require(read(old/'prepare/transaction.json')['worker_outcome']['kind'] == 'cpu_limit' and
        all(a['state'] == 'settled' for a in read(old/'budget/ledger.json')['attempts'].values()), 'Preserved settled failure required')
    for name, h in previous['sources'].items(): require(sha(ROOT/name) == h, 'V45 source changed')
    for entry in previous['inputs'].values(): bound(entry)
    progress = old/'prepare/outputs/progress-0017.json'
    row = read(progress)
    require(row['stage_id'] == STAGE_ID and row['phase'] == 'stage_certified' and
        row['code_sha256'] == HISTORICAL_CODE and row['fallback'] is False, 'Historical commitment differs')
    profile = ROOT/'local_runs/neighbor-profile-v50-20261011-a'
    require(sha(profile/'program.json') == '8b732267fefab478296300837f26e475782c780afdfe2e15104633c9d7d3db95' and
        read(profile/'outputs/completion.json')['status'] == 'complete' and
        read(profile/'worker/result.json')['outcome']['status'] == 'complete' and
        all(a['state'] == 'settled' for a in read(profile/'budget/ledger.json')['attempts'].values()), 'V50 prerequisite failed')
    require(len(previous['records']) == 13 and all(len(r['tokens']) == 128 for r in previous['records']),
        'Registered root extent changed')
    inputs = {f'v45:{name}': bind(old/name) for name in ('program.json', 'budget/ledger.json',
        'prepare/worker/result.json', 'prepare/transaction.json', 'prepare/outputs/progress-0017.json',
        'prepare/outputs/execution-provenance.json')}
    inputs.update({f'v50:{name}': bind(profile/name) for name in
        ('program.json', 'outputs/completion.json', 'worker/result.json', 'budget/ledger.json')})
    inputs.update({f'data:{name}': entry for name, entry in previous['inputs'].items() if name.startswith('data_')})
    inputs['checks'] = bind(checks)
    p = dict(schema='real-wide-stage-program-v51', directory=str(d), sources=sources(), runtime=runtime(),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        registration_job=os.environ['SLURM_JOB_ID'], inputs=inputs, records=previous['records'],
        record_provenance=previous['record_provenance'], normalization=1664, stage_id=STAGE_ID,
        historical_code_sha256=HISTORICAL_CODE, trials=TRIALS, order=list(ORDER), caps=CAPS,
        common_limits=COMMON, review=review(), complete_model=False, quality_evaluation=False,
        confirmation=False, new_quality_data=False, automatic_retry=False, gpu_numeric_execution=False,
        scope='Known development root; one wide stage, fixed order and no population speed claim.')
    d.mkdir(parents=True); new(d/'program.json', p)
    new(d/'registration.json', dict(program_sha256=sha(d/'program.json'))); budget(d)
    print(canonical_json(dict(status='registered', program_sha256=sha(d/'program.json'))).decode(), flush=True)


def completed(d, trial):
    p = read(d/'program.json'); ph = sha(d/'program.json'); root = d/trial
    identity = read(root/'worker/identity.json'); receipt = read_completed(root/'worker', identity)
    command = [sys.executable, '-B', '-m', 'research_v51.worker', str(d), trial]
    require(receipt is not None and receipt['outcome']['status'] == 'complete' and
        receipt['outcome']['returncode'] == 0 and identity['identity'] == dict(program_sha256=ph, trial=trial)
        and identity['command'] == command and identity['cwd'] == str(ROOT), 'Worker not complete or identity differs')
    limits = dict(**TRIALS[trial], **COMMON)
    require(all(identity['limits'][k] == v for k,v in limits.items()), 'Worker limits changed')
    require(read(root/'transaction.json')['worker_outcome'] == receipt['outcome'], 'Transaction differs')
    snap = snapshot(d)
    require(snap['status'] == 'verified' and not any(snap['over_cap'].values()) and
        snap['attempts'][receipt['budget_attempt_id']] == receipt['budget_debit'] and
        receipt['budget_debit']['state'] == 'settled' and
        receipt['budget_debit']['observed_cpu_ns'] == receipt['resource_usage']['total_cpu_ns'], 'Debit differs')
    result = read(root/'outputs/completion.json')
    require(result['status'] == 'complete' and result['program_sha256'] == ph and result['trial'] == trial,
        'Completion differs')
    for name, entry in result['artifacts'].items():
        require(Path(name).name == name and sha(root/'outputs'/name) == entry['sha256'] and
            (root/'outputs'/name).stat().st_size == entry['bytes'], 'Prepared artifact differs')
    return result


def run(d, trial):
    require(os.environ.get('SLURM_JOB_ID'), 'Slurm required')
    d = Path(d).resolve(); verify(d)
    require(trial in ORDER, 'Unknown trial')
    for previous in ORDER[:ORDER.index(trial)]: completed(d, previous)
    root = d/trial; require(not root.exists(), 'One-use attempt already exists'); root.mkdir()
    start = time.perf_counter_ns()
    result = run_limited([sys.executable, '-B', '-m', 'research_v51.worker', str(d), trial], root/'worker',
        WorkerLimits(**TRIALS[trial], **COMMON, affinity_cpus=(min(os.sched_getaffinity(0)),)),
        identity=dict(program_sha256=sha(d/'program.json'), trial=trial), cwd=ROOT,
        phase_budget=budget(d), phase=trial)
    new(root/'transaction.json', dict(worker_outcome=result['outcome'], elapsed_ns=time.perf_counter_ns()-start,
        budget=snapshot(d), slurm_job_id=os.environ['SLURM_JOB_ID']))
    require(result['outcome']['status'] == 'complete', 'Bounded worker failed: '+trial)
    completed(d, trial)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('operation', choices=('execute','run'))
    parser.add_argument('directory'); parser.add_argument('argument'); args = parser.parse_args()
    d = Path(args.directory).resolve()
    if args.operation == 'execute':
        register(d, args.argument)
        for trial in ORDER: run(d, trial)
        from research_v51.worker import final_check
        final_check(d)
    else: run(d, args.argument)
