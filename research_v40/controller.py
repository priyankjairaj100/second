"""One-use registration, resource admission, and actual artifact audits."""
from pathlib import Path
import os
import sys
import time

from research_v40.policy import (ROOT, PREFIX, REVISION, PHASE_CAP, DATA_CAP,
    RETAINED_COUNTS, ORIGINAL_RECORDS, TOKENS, NORMALIZATION, arm_order,
    require, read, sha, new, extra_sources, verify_sources)
from src.run_store import canonical_json, digest
from src.experiment_inventory import source_hashes
from src.runtime_contract import capture_runtime_contract
from src.phase_budget import PhaseBudget
from src.worker_control import WorkerLimits, run_limited
from src.service_terminal_evidence_v30 import verify_completed


def trial_specs():
    return [dict(id='data', kind='data', cpu_seconds=120, wall_seconds=240, phase_group='data'),
            dict(id='prepare', kind='prepare', cpu_seconds=240, wall_seconds=420, phase_group='model')] + [
        dict(id=f'retain-{n:02d}', kind='case', retained_count=n, arm_order=arm_order(n),
             cpu_seconds=700, wall_seconds=900, phase_group='model') for n in RETAINED_COUNTS]


def historical_ledgers():
    return {str(p.relative_to(ROOT)): sha(p) for folder in ('campaigns', 'pilots', 'local_runs')
            for p in sorted((ROOT / folder).rglob('ledger.json')) if ROOT / PREFIX not in p.parents}


def control_sources():
    names = ['.github/workflows/native-scale-v40.yml', '.github/ci/native-scale-v40-trigger.json',
             'requirements-ci-v38.txt', 'requirements-scale-v39.txt',
             'docs/SCALE_PROTOCOL_V40.md', 'docs/NATIVE_EXACT_GRAM_V40.md',
             'docs/STREAMED_PRIMAL_V40.md', 'tests/test_native_exact_gram_v40.py',
             'tests/test_streamed_primal_ball_v40.py', 'tests/test_scale_protocol_v40.py']
    return {name: sha(ROOT / name) for name in names}


def register(event_commit):
    root = ROOT / PREFIX
    require(not (root / 'program.json').exists(), 'Program already registered')
    program = dict(schema='bounded-real-scale-program-v40', revision=REVISION,
        root=str(root), registered_source_commit=event_commit,
        source_sha256=source_hashes(ROOT), extra_source_sha256=extra_sources(),
        control_source_sha256=control_sources(), historical_ledgers_sha256=historical_ledgers(),
        runtime=capture_runtime_contract(), affinity_cpus=[min(os.sched_getaffinity(0))],
        trials=trial_specs(), execution_order=[x['id'] for x in trial_specs()],
        phase_cpu_seconds=dict(data=DATA_CAP, model=PHASE_CAP), address_space_bytes=6 * 2**30,
        original_records=ORIGINAL_RECORDS, tokens_per_record=TOKENS, normalization=NORMALIZATION,
        recipe='fixed nearest-grid features; first complete QKV stage; original normalization; ridge 1/100; four bits',
        automatic_retry=False, paid_compute=False, confirmation=False, full_model=False,
        selection='Existing development article partition and hash order. First 13 distinct 128-token chunks.',
        endpoints=['complete code agreement', 'exact retained Gram agreement', 'component elapsed time',
                   'descriptor payload bytes', 'native/reference exact archive equality', 'certificate refusals', 'fallback cost', 'neural stage-record pairs'],
        no_population_inference=True, no_lifetime_claim=True, no_independent_state_oracle=True)
    new(root / 'program.json', program)
    for group, cap in program['phase_cpu_seconds'].items():
        new(root / f'protocol-{group}.json', dict(schema='scale-phase-policy-v40',
            program_sha256=sha(root / 'program.json'), phase_cpu_seconds={'feasibility': cap},
            phase_group=group, automatic_retry=False))
    new(root / 'registration.json', dict(program_sha256=sha(root / 'program.json'),
        protocols={group: sha(root / f'protocol-{group}.json') for group in program['phase_cpu_seconds']}))
    return program


def verify_registration():
    root = ROOT / PREFIX
    program = read(root / 'program.json')
    require(program['root'] == str(root) and program['trials'] == trial_specs(), 'Registered design differs')
    require(program['phase_cpu_seconds'] == dict(data=DATA_CAP, model=PHASE_CAP), 'CPU caps differ')
    registration = read(root / 'registration.json')
    require(registration['program_sha256'] == sha(root / 'program.json'), 'Program changed')
    for group, expected in registration['protocols'].items():
        path = root / f'protocol-{group}.json'
        require(sha(path) == expected and read(path)['program_sha256'] == registration['program_sha256'],
                'Phase protocol changed')
    verify_sources(program)
    require(control_sources() == program['control_source_sha256'], 'Controls changed')
    require(capture_runtime_contract() == program['runtime'], 'Runtime changed')
    return program


def expected_plan(program, trial_id):
    """Only deterministic prior artifacts may supply dynamic input hashes."""
    matches = [x for x in program['trials'] if x['id'] == trial_id]
    require(len(matches) == 1, 'Trial is not uniquely registered')
    trial = matches[0]
    root = Path(program['root'])
    require(root == ROOT / PREFIX, 'Campaign path differs')
    plan = dict(trial, trial_id=trial_id, program_path=str(root / 'program.json'),
        program_sha256=sha(root / 'program.json'),
        protocol_sha256=sha(root / f'protocol-{trial["phase_group"]}.json'),
        output=str(root / 'attempts' / trial_id / 'outputs'))
    if trial['kind'] != 'data':
        selected = root / 'attempts/data/outputs'
        plan.update(records_path=str(selected / 'records.json'), records_sha256=sha(selected / 'records.json'))
    if trial['kind'] == 'case':
        selected_ids = read(root / 'attempts/data/outputs/selection.json')['sampling_order_ids']
        plan['retained_ids'] = sorted(selected_ids[:trial['retained_count']])
        prepared = root / 'attempts/prepare/outputs'
        plan.update(preparation_path=str(prepared), preparation_sha256=sha(prepared / 'completion.json'))
    return plan


def budget_for(program, group):
    root = Path(program['root'])
    return PhaseBudget(root / f'{group}-phase-cpu-budget',
        identity=dict(protocol_sha256=sha(root / f'protocol-{group}.json'), source_sha256=program['source_sha256']),
        phase_cpu_seconds={'feasibility': program['phase_cpu_seconds'][group]})


def audit_completed(program, trial_id):
    start = time.process_time_ns()
    attempt = Path(program['root']) / 'attempts' / trial_id
    require(read(attempt / 'plan.json') == expected_plan(program, trial_id), 'Recorded plan differs')
    result = verify_completed(attempt)
    require(result['source_sha256'] == program['source_sha256']
            and result['extra_source_sha256'] == program['extra_source_sha256'], 'Worker sources differ')
    if result['kind'] == 'case':
        require(result['exact_gram_bytes_equal'] and result['actual_binary_comparison_performed'],
                'Worker binary audit missing')
        require(set(result['arms']) == set(read(attempt / 'plan.json')['arm_order']), 'An arm disappeared')
        output = attempt / 'outputs'
        require((output / 'gram_delete_python-gram.bin').read_bytes()
                == (output / 'gram_delete_native-gram.bin').read_bytes()
                == (output / 'gram_fresh_native-gram.bin').read_bytes(),
                'Actual retained Gram files differ')
        payloads = [(output / (arm + '-codes.bin')).read_bytes() for arm, row in result['arms'].items()
                    if row['status'] == 'certified']
        require(not payloads or all(blob == payloads[0] for blob in payloads), 'Actual code files differ')
        require(all(row['code_count'] == 1_769_472 for row in result['arms'].values()
                    if row['status'] == 'certified'), 'Stage code extent differs')
    return dict(schema='scale-actual-artifact-audit-v40', trial=trial_id, status='verified',
        completion_sha256=sha(attempt / 'outputs/completion.json'),
        actual_output_files_rehashed=True, binary_bytes_compared=result['kind'] == 'case',
        artifact_count=len(result['artifacts']), analysis_cpu_ns=time.process_time_ns() - start,
        analysis_cost_outside_worker_ledger=True)


def run_trial(trial_id):
    program = verify_registration()
    root = Path(program['root'])
    order = program['execution_order']
    require(trial_id in order, 'Unregistered attempt')
    for previous in order[:order.index(trial_id)]:
        audit_completed(program, previous)
    trial = next(x for x in program['trials'] if x['id'] == trial_id)
    budget = budget_for(program, trial['phase_group'])
    snapshot = budget.snapshot()
    require(all(row['state'] == 'settled' for row in snapshot['attempts'].values()), 'Unsettled attempt blocks work')
    require(program['phase_cpu_seconds'][trial['phase_group']] - snapshot['charged_cpu_seconds']['feasibility']
            >= trial['cpu_seconds'] + 2, 'Full CPU reservation does not fit')
    attempt = root / 'attempts' / trial_id
    require(not attempt.exists(), 'Attempt exists; retry is prohibited')
    attempt.mkdir(parents=True)
    plan = expected_plan(program, trial_id)
    plan_path = attempt / 'plan.json'
    new(plan_path, plan)
    started = time.perf_counter_ns()
    receipt = run_limited([sys.executable, '-m', 'research_v40.worker', str(plan_path)], attempt / 'worker',
        WorkerLimits(trial['wall_seconds'], trial['cpu_seconds'], program['address_space_bytes'], 1,
                     tuple(program['affinity_cpus'])),
        identity=dict(campaign=REVISION, plan_sha256=sha(plan_path)), cwd=ROOT, phase_budget=budget, phase='feasibility')
    new(attempt / 'transaction.json', dict(schema='research-transaction-v30',
        worker_outcome=receipt['outcome'], receipt_sha256=sha(attempt / 'worker/result.json'),
        controller_elapsed_ns=time.perf_counter_ns() - started, budget=budget.snapshot(),
        clock='worker launch through receipt hashing; prerequisite audits excluded'))
    progress = attempt / 'outputs/progress.json'
    if progress.is_file():
        new(attempt / 'sealed-progress.json', progress.read_bytes(), raw=True)
    if receipt['outcome']['status'] == 'complete':
        new(attempt / 'actual-artifact-audit.json', audit_completed(program, trial_id))
    return receipt['outcome']['status']


def analyze():
    start = time.process_time_ns()
    program = verify_registration()
    root = Path(program['root'])
    audits = {trial: audit_completed(program, trial) for trial in program['execution_order']}
    cases = {}
    for count in RETAINED_COUNTS:
        result = verify_completed(root / 'attempts' / f'retain-{count:02d}')
        arms = result['arms']
        ratios = {}
        for base, method in [('gram_delete_python', 'gram_delete_native'),
                             ('gram_fresh_native', 'gram_delete_native'),
                             ('cached_primal', 'streamed_primal'),
                             ('cached_primal', 'gram_delete_native'),
                             ('streamed_primal', 'streamed_compressed_40'),
                             ('gram_delete_native', 'streamed_compressed_40')]:
            key = base + '_over_' + method
            ratios[key] = (arms[base]['component_elapsed_ns'] / arms[method]['component_elapsed_ns']
                          if arms[base]['status'] == arms[method]['status'] == 'certified' else None)
        cases[str(count * TOKENS)] = dict(arms=arms, ratios=ratios,
            exact_code_agreement=result['all_committed_code_bytes_equal'],
            all_arms_certified=result['all_arms_certified'])
    return dict(schema='real-scale-analysis-v40', status='complete_verified', cases=cases, audits=audits,
        budgets={group: budget_for(program, group).snapshot() for group in program['phase_cpu_seconds']},
        actual_binary_artifacts_reverified=True, confirmation=False, full_model=False,
        paired_repetitions=1, population_inference=False, lifetime_benefit_established=False,
        stage='First complete QKV stage only. Shared checkpoint loads and native builds are outside arm ratios.',
        analysis_cpu_ns=time.process_time_ns() - start, analysis_cost_outside_worker_ledger=True)
