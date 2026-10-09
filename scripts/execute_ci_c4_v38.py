#!/usr/bin/env python3
"""Run one public, free C4 campaign and publish bounded text evidence.

This wrapper keeps the V32 worker code and numerical policy unchanged.
It changes the prerequisite to verified, published WikiText metadata.
No historical binary audit or prospective confirmation is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
PREFIX = Path('campaigns/ci_v38')
WORKSPACE = str(PREFIX)
CAMPAIGN = PREFIX / 'independent_c4_v32'
CLAIM = PREFIX / 'execution-claim.json'
TRIGGER = Path('.github/ci/c4-v38-trigger.json')
REVISION = 'c4-v38-one-use-2026-10-09'
REPOSITORY = 'priyankjairaj100/second'
WIKI_ANALYSIS = Path('campaigns/independent_wikitext_v32/analysis-v33.json')
WIKI_SHA256 = 'f290104a56edf865a5b0b91a4758d439f08c0b93f217bc22510e510d83450b2b'
CONTROL_FILES = (
    'scripts/execute_ci_c4_v38.py', '.github/workflows/c4-v38.yml',
    'research_v38/c4_controller.py', 'research_v38/c4_analysis.py', 'research_v38/bootstrap_target.py',
    str(TRIGGER), 'requirements-ci-v38.txt',
    'scripts/preflight_environment_v34.py', 'scripts/recover_assets_v32.py',
    'scripts/check_runtime_portability_v38.py', 'research_v38/live_runtime.py', 'research_v38/runtime_probe.c',
    'scripts/audit_published_results_v32.py', 'scripts/analyze_independent_requests_v32.py',
    'scripts/analyze_compressed_service_v31.py',
    'tests/test_ci_c4_v38.py', 'tests/test_bootstrap_target_v38.py', 'tests/test_transformer_backend.py',
)
TRIGGER_PAYLOAD = {
    'revision': REVISION, 'campaign': str(CAMPAIGN),
    'phase_cpu_cap_seconds': 1900, 'bootstrap_cpu_allowance_seconds': 122, 'workflow_wall_minutes': 60,
    'paid_compute_allowed': False, 'automatic_retry_allowed': False,
    'syntax_amendment': {
        'kind': 'yaml-command-syntax-before-first-runner',
        'rejected_run_id': 37948393273,
        'rejected_source_commit': '1cf45ff1861b7e347bcef6308b3eddbb1e5e6534',
    },
}
PUBLISH_BROKEN = False


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def sha(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing or symbolic file: ' + str(path))
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save_new(relative, value):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def event_guard(env=None, event=None):
    env = os.environ if env is None else env
    event = read(env['GITHUB_EVENT_PATH']) if event is None else event
    require(env.get('GITHUB_ACTIONS') == 'true', 'This command requires GitHub Actions')
    require(env.get('GITHUB_REPOSITORY') == REPOSITORY, 'Repository differs')
    require(env.get('GITHUB_REF') == 'refs/heads/main', 'Only main is authorized')
    require(env.get('GITHUB_EVENT_NAME') == 'push', 'Only the registered push is authorized')
    require(env.get('GITHUB_RUN_ATTEMPT') == '1', 'Reruns are not authorized')
    require(event.get('repository', {}).get('private') is False, 'Private runners are not authorized')
    require(event.get('repository', {}).get('full_name') == REPOSITORY, 'Event repository differs')
    require(event.get('after') == env.get('GITHUB_SHA'), 'Event revision differs')
    require(re.fullmatch(r'[0-9a-f]{40}', env.get('GITHUB_SHA', '')), 'Invalid event revision')
    require(env.get('RUNNER_ENVIRONMENT') == 'github-hosted', 'Only the standard hosted runner is authorized')
    require(env.get('RUNNER_OS') == 'Linux' and env.get('RUNNER_ARCH') == 'X64', 'Runner platform differs')
    require(read(ROOT / TRIGGER) == TRIGGER_PAYLOAD, 'One-use trigger differs')
    return {'run_id': env['GITHUB_RUN_ID'], 'run_attempt': 1,
            'event_commit': env['GITHUB_SHA'], 'repository': REPOSITORY,
            'revision': REVISION, 'repository_public_at_start': True}


def collect_text_paths():
    """Allow text evidence only. Never stage model bytes or lock files."""
    paths = []
    for path in sorted((ROOT / PREFIX).rglob('*')):
        require(not path.is_symlink(), 'Symbolic evidence path refused')
        if not path.is_file() or path.suffix in ('.bin', '.lock', '.pyc') or '__pycache__' in path.parts:
            continue
        if path.name.startswith('.'):
            continue
        require(path.suffix in ('.py', '.json', '.txt', '.md'), 'Unexpected evidence file: ' + str(path))
        require(path.stat().st_size <= 32 * 2**20, 'Text evidence exceeds the file limit')
        raw = path.read_bytes()
        require(b'\0' not in raw, 'Binary evidence refused')
        text = raw.decode('utf-8')
        require(not re.search(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|hf_[A-Za-z0-9]{30,})', text),
                'Possible credential in evidence')
        paths.append(str(path.relative_to(ROOT)))
    return paths


def update_manifest():
    names = git('ls-files', '-z').split('\0')
    rows = [sha(ROOT / name) + '  ' + name + '\n' for name in sorted(names)
            if name and name != 'MANIFEST.sha256']
    (ROOT / 'MANIFEST.sha256').write_text(''.join(rows))
    git('add', '--', 'MANIFEST.sha256')


def publish(message):
    """One non-force push. A publication failure blocks all later workers."""
    global PUBLISH_BROKEN
    require(not PUBLISH_BROKEN, 'An earlier publication failed; no retry is authorized')
    try:
        parent = git('rev-parse', 'HEAD')
        remote = git('ls-remote', 'origin', 'refs/heads/main').split()[0]
        require(parent == remote, 'Remote main moved; stop without overwriting it')
        paths = collect_text_paths()
        require(paths, 'No text evidence to publish')
        for offset in range(0, len(paths), 100):
            git('add', '--', *paths[offset:offset + 100])
        changed = git('diff', '--name-only', 'HEAD').splitlines()
        require(all(Path(p).is_relative_to(PREFIX) or p == 'MANIFEST.sha256' for p in changed),
                'Unrelated changes block publication')
        update_manifest()
        git('config', 'user.name', 'github-actions[bot]')
        git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
        git('commit', '-m', message)
        commit = git('rev-parse', 'HEAD')
        git('push', 'origin', 'HEAD:refs/heads/main')
        require(git('ls-remote', 'origin', 'refs/heads/main').split()[0] == commit,
                'Published revision could not be verified')
        print(json.dumps({'published_commit': commit, 'message': message}), flush=True)
        return commit
    except BaseException:
        PUBLISH_BROKEN = True
        raise


def claim_once():
    identity = event_guard()
    require(git('rev-parse', 'HEAD') == identity['event_commit'], 'Checkout does not match the trigger')
    require(not (ROOT / PREFIX).exists(), 'One-use campaign already exists')
    require(not git('status', '--porcelain'), 'Checkout must be clean before the claim')
    save_new(CLAIM, dict(identity, schema='one-use-free-c4-claim-v38',
        automatic_retry=False, phase_cpu_cap_seconds=1900, bootstrap_cpu_allowance_seconds=122,
        total_separate_cpu_allowances_seconds=2022,
        abrupt_loss_policy='Hold 1900 campaign CPU seconds and 122 bootstrap CPU seconds if settlement cannot be recovered.',
        allowance_is_not_observed_usage=True, model_worker_started=False))
    return publish('Claim the one-use free C4 V38 campaign')


def verify_claim():
    identity = event_guard()
    claim = read(ROOT / CLAIM)
    require(all(claim.get(k) == v for k, v in identity.items()), 'Claim does not belong to this run')
    require(claim['automatic_retry'] is False, 'Retry policy differs')
    require(git('merge-base', '--is-ancestor', identity['event_commit'], 'HEAD') == '', 'Trigger is not an ancestor')
    return claim


def software_fixtures():
    """Run bounded software fixtures. Preserve their result before model work."""
    verify_claim()
    require(not (ROOT / PREFIX / 'software-fixtures.json').exists(), 'Software fixtures already ran')
    (ROOT / 'tmp').mkdir(exist_ok=True)
    command = [sys.executable, '-m', 'unittest', 'tests.test_ci_c4_v38',
               'tests.test_bootstrap_target_v38', '-v']
    start = time.perf_counter_ns()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        outcome = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        result = dict(returncode=outcome.returncode, stdout=outcome.stdout[-64000:], stderr=outcome.stderr[-64000:],
                      wall_timeout=False)
    except subprocess.TimeoutExpired as exc:
        def text(value):
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
        result = dict(returncode=None, stdout=text(exc.stdout)[-64000:], stderr=text(exc.stderr)[-64000:],
                      wall_timeout=True)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    result.update(schema='bounded-c4-software-fixtures-v38', command=command, wall_limit_seconds=120,
        controller_elapsed_ns=time.perf_counter_ns() - start,
        observed_child_cpu_seconds=(after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime),
        empirical_checkpoint_loaded=False, calibration_records_read=False,
        real_proc_constructor_required=True,
        source_sha256={name: sha(ROOT / name) for name in CONTROL_FILES if name.startswith('tests/')})
    result['passed'] = result['returncode'] == 0 and 'skipped=' not in result['stderr']
    save_new(PREFIX / 'software-fixtures.json', result)
    publish('Preserve C4 V38 host software fixtures')
    require(result['passed'], 'Host software fixtures failed or skipped the required constructor check')


def modules():
    sys.path.insert(0, str(ROOT))
    from research_v38 import c4_controller as controller
    from research_v38 import c4_analysis as analysis
    from scripts import preflight_environment_v34 as environment
    from scripts import recover_assets_v32 as assets
    from scripts import audit_published_results_v32 as published
    controller.WORKSPACE = WORKSPACE
    return controller, analysis, environment, assets, published


def published_wiki_prerequisite():
    require(sha(ROOT / WIKI_ANALYSIS) == WIKI_SHA256, 'Published WikiText analysis changed')
    report = read(ROOT / WIKI_ANALYSIS)
    require(report['status'] == 'complete_verified' and report['all_seven_trials_verified'] is True,
            'Published WikiText prerequisite is incomplete')
    require(report['current_binary_artifacts_reverified'] is True, 'Published analysis lacks its original binary audit')
    for name, expected in report['evidence_sha256'].items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'Unsafe historical evidence path')
        require(sha(ROOT / path) == expected, 'Published WikiText evidence changed: ' + name)
    budget = report['phase_budget']
    require(budget['status'] == 'verified' and budget['charged_cpu_seconds']['feasibility'] == 927,
            'Published WikiText budget differs')
    require(len(budget['attempts']) == 7 and all(x['state'] == 'settled' for x in budget['attempts'].values()),
            'Published WikiText contains an unsettled attempt')
    return {'analysis_sha256': WIKI_SHA256, 'bound_files_verified': len(report['evidence_sha256']),
            'historical_binary_outputs_reverified_here': False,
            'prior_analysis_reported_binary_verification': True,
            'original_strict_three_copy_guard_passed': report['original_strict_three_copy_guard_passed'],
            'recovery_provenance': report['recovery_provenance'],
            'scope': 'Published development prerequisite only. No historical runtime is reused for new C4 timing.'}


def register_fresh(controller, prerequisite):
    """Explicit V38 prerequisite amendment; preserve every V32 trial field."""
    current = controller.campaign('c4')
    require(current == ROOT / CAMPAIGN and not current.exists(), 'Fresh C4 registration already exists')
    spec = controller.build_spec('c4')
    historical = controller.archive_evidence()
    controller.validate_design(spec)
    admission = controller.resource_admission(spec)
    source = current / 'source'
    for folder in ('src', 'scripts', 'research_v38'):
        (source / folder).mkdir(parents=True)
        for path in sorted((ROOT / folder).glob('*.py')):
            shutil.copyfile(path, source / folder / path.name)
    program = dict(spec, schema='bounded-independent-recovery-program-v32', status='prospectively_registered',
        source_sha256=controller.source_hashes(source),
        controller_sha256={p: sha(ROOT / p) for p in controller.CONTROLLERS},
        historical_evidence=historical, resource_admission=admission,
        historical_frozen_ledgers=controller.historical_ledgers(current),
        affinity_cpus=[min(os.sched_getaffinity(0))], address_space_bytes=6 * 2**30,
        primary_clock='controller after prerequisite/bootstrap checks through worker receipt and receipt hash',
        secondary_clock='nested worker and service clocks; never add to primary clock',
        authorization='User requested continued experiments. Standard public GitHub runner only. No paid compute.',
        registered_from_commit=git('rev-parse', 'HEAD'),
        ci_v38=dict(schema='fresh-public-c4-amendment-v38', prerequisite=prerequisite,
            same_workspace_wikitext_rerun_required=False, mathematical_recipe_changed=False,
            host_target_rebound=True, target_manifest_sha256=sha(ROOT / PREFIX / 'bootstrap/outputs/fixed-target.json'),
            runtime_portability_decision=read(ROOT / PREFIX / 'runtime-portability-decision.json'),
            runtime_portability_evidence_sha256=sha(ROOT / PREFIX / 'runtime-portability.json'),
            bootstrap_audit_sha256=sha(ROOT / PREFIX / 'bootstrap-audit.json'),
            software_fixtures_sha256=sha(ROOT / PREFIX / 'software-fixtures.json'),
            original_c4_failure_preserved=True, control_sha256={p: sha(ROOT / p) for p in CONTROL_FILES},
            claim_sha256=sha(ROOT / CLAIM), confirmation=False, automatic_retry=False,
            measurement_scope='New C4 root, one shared runner, one timing per method and deletion direction.',
            binary_policy='Audit actual bytes before each checkpoint. Publish text hashes. No artifact storage.'))
    raw = controller.canonical_json(program)
    protocol = controller.canonical_json(dict(schema='bounded-independent-recovery-policy-v32',
        program_sha256=controller.digest(raw), phase_cpu_seconds={'feasibility': 1900}))
    controller.atomic_write(current / 'program.json', raw)
    controller.atomic_write(current / 'protocol.json', protocol)
    controller.atomic_write(current / 'registration.json', controller.canonical_json(dict(
        program_sha256=controller.digest(raw), protocol_sha256=controller.digest(protocol),
        runtime=controller.capture_runtime_contract())))
    controller.atomic_write(current / 'registered-launcher.py', Path(controller.__file__).read_bytes())
    controller.atomic_write(current / 'registered-ci-launcher.py', Path(__file__).read_bytes())
    return current, program


def verify_v38_registration(controller):
    current, program, raw, protocol, registration = controller.check_registered('c4')
    extra = program['ci_v38']
    require(extra['control_sha256'] == {p: sha(ROOT / p) for p in CONTROL_FILES}, 'V38 control source changed')
    require(extra['claim_sha256'] == sha(ROOT / CLAIM), 'One-use claim changed')
    require(extra['prerequisite'] == published_wiki_prerequisite(), 'Historical prerequisite changed')
    portability = read(ROOT / PREFIX / 'runtime-portability.json')
    portability_command = read(ROOT / PREFIX / 'runtime-portability-command.json')
    decision = admit_original_backend(portability, portability_command['exit_code'])
    require(extra['runtime_portability_decision'] == decision
            == read(ROOT / PREFIX / 'runtime-portability-decision.json'), 'Runtime refusal classification changed')
    require(extra['runtime_portability_evidence_sha256'] == sha(ROOT / PREFIX / 'runtime-portability.json'),
            'Runtime cross-check evidence changed')
    require(extra['software_fixtures_sha256'] == sha(ROOT / PREFIX / 'software-fixtures.json'),
            'Host software fixture evidence changed')
    require(extra['bootstrap_audit_sha256'] == sha(ROOT / PREFIX / 'bootstrap-audit.json'), 'Bootstrap audit changed')
    from research_v38.bootstrap_target import verify_bootstrap
    require(verify_bootstrap(ROOT / PREFIX / 'bootstrap') == read(ROOT / PREFIX / 'bootstrap-audit.json'),
            'Verified bootstrap evidence differs from the published audit')
    return current, program


def audit_trial(controller, analysis, current, program, trial_id):
    """Read the full binary outputs while this runner still holds them."""
    started = time.process_time_ns()
    trial = next(t for t in program['trials'] if t['id'] == trial_id)
    result = controller.completed(current, trial_id)
    analysis.verify_result_fields(result, trial)
    attempt = current / 'attempts' / trial_id
    artifacts = {}
    for kind, entry in result['artifacts'].items():
        path = attempt / 'outputs' / entry['file']
        require(path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], 'Actual artifact differs')
        artifacts[kind] = dict(entry, full_file_hash_recomputed=True)
    from src.compact_state import parse
    model_entry = result['artifacts']['model']
    model_path = attempt / 'outputs' / model_entry['file']
    model = parse(model_path.read_bytes(), expected_sha256=model_entry['sha256'])
    count = sum(stage.rows * stage.columns for stage in model.stages)
    require(len(model.stages) == 24 and count == 42467328 and not model.factors, 'Full model extent differs')
    comparisons = []
    for comparison in trial.get('compare_to', []):
        reference = controller.completed(current, comparison['trial'])
        for kind in comparison.get('artifacts', ['model']):
            left = attempt / 'outputs' / result['artifacts'][kind]['file']
            right = current / 'attempts' / comparison['trial'] / 'outputs' / reference['artifacts'][kind]['file']
            require(analysis.equal_file_bytes(left, right), 'Actual comparison bytes differ')
            comparisons.append({'reference': comparison['trial'], 'artifact': kind, 'actual_bytes_equal': True})
    changes = None
    if trial['plan']['method'] not in ('direct_fresh', 'convert_lossless'):
        original = controller.completed(current, program['execution_order'][0])
        entry = original['artifacts']['model']
        path = current / 'attempts' / program['execution_order'][0] / 'outputs' / entry['file']
        changes = analysis.changed_model_codes(parse(path.read_bytes(), expected_sha256=entry['sha256']), model)
    native = None
    if trial['script'] == 'run_compressed_service_v31.py':
        analysis.verify_diagnostics(result, trial['plan'])
        if trial['plan']['method'] != 'convert_lossless':
            native = analysis.verify_native_receipts(result, trial['plan'], program, current / 'source')
    report = dict(schema='actual-c4-trial-binary-audit-v38', trial=trial_id, status='complete_verified',
        model_stage_count=24, model_code_count=count, actual_artifacts=artifacts,
        actual_byte_comparisons=comparisons, deletion_code_changes=changes, native_evidence=native,
        controller_seconds=analysis.verified_seconds(read(attempt / 'transaction.json')),
        scientific_gates=result['registered_scientific_gates'],
        analysis_cpu_ns=time.process_time_ns() - started, analysis_cost_outside_worker_ledger=True,
        retained_state_independent_oracle=False, historical_binary_outputs_reverified=False)
    save_new(CAMPAIGN / 'attempts' / trial_id / 'actual-binary-audit-v38.json', report)
    return report


def admit_original_backend(report, returncode):
    """Keep a narrow portable refusal separate from contradictory runtime facts."""
    require(report.get('schema') == 'runtime-portability-crosscheck-v38', 'Runtime cross-check schema differs')
    status = report.get('status')
    require(status in ('passed', 'unsupported_portable_interface'), 'Runtime cross-check does not admit original C4')
    require(returncode == 0 and report.get('c4_original_backend_admitted') is True,
            'Runtime cross-check exit and admission differ')
    require(report.get('portable_gate_7_passed') is (status == 'passed'), 'Portable promotion flag differs')
    require(report.get('checks', {}).get('old_cpu_record_mapping', {}).get('status') == 'passed',
            'Original CPU record mapping did not pass')
    require({'old_transformer', 'old_primitive'} <= set(report.get('raw_manifests', {})),
            'Original runtime manifests are missing')
    checks, manifests = report['checks'], report['raw_manifests']
    if status == 'unsupported_portable_interface':
        require(bool(report.get('error', {}).get('reason')), 'Portable refusal reason is missing')
        require(checks.get('stable_original_runtime_evidence') is True
                and checks.get('old_cpu_record_mapping_after', {}).get('status') == 'passed',
                'Original runtime stability evidence is missing')
        require({'old_transformer_after', 'old_primitive_after'} <= set(manifests)
                and manifests['old_transformer_after'] == manifests['old_transformer']
                and manifests['old_primitive_after'] == manifests['old_primitive'],
                'Original runtime manifests changed across the portable refusal')
    else:
        require(checks.get('stable_live_evidence') is True
                and checks.get('cpu', {}).get('status') == 'passed'
                and checks.get('libraries', {}).get('status') == 'passed',
                'Portable runtime stability evidence is missing')
        require({'new_before', 'new_after'} <= set(manifests)
                and manifests['new_before'] == manifests['new_after'],
                'Portable runtime manifests changed across the comparison')
    return dict(schema='runtime-backend-admission-v38', status=status, original_c4_admitted=True,
        portable_gate_7_passed=status == 'passed', portable_refusal=report.get('error'),
        numerical_backend='unchanged original backend',
        scope='A portable interface refusal does not establish portable runtime equivalence.')


def execute():
    verify_claim()
    require(read(ROOT / PREFIX / 'software-fixtures.json')['passed'] is True, 'Host fixtures must pass before execution')
    require(not (ROOT / PREFIX / 'execution-start.json').exists(), 'Execution was already started')
    save_new(PREFIX / 'execution-start.json', {'revision': REVISION, 'automatic_retry': False})
    publish('Start one-use C4 V38 admission checks')
    controller, analysis, environment, assets, published = modules()
    preflight = environment.preflight()
    save_new(PREFIX / 'environment-preflight.json', preflight)
    require(preflight['status'] == 'passed', 'Original backend preflight failed')
    save_new(PREFIX / 'published-metadata-audit.json', published.audit(ROOT))
    prerequisite = published_wiki_prerequisite()
    save_new(PREFIX / 'wikitext-prerequisite.json', prerequisite)
    downloads = assets.restore_checkpoint()
    checkpoint = assets.checkpoint_inventory()
    save_new(PREFIX / 'checkpoint-audit.json', dict(checkpoint, downloads=downloads))
    require(checkpoint['checkpoint_verified'], 'Checkpoint identity failed')
    portability = subprocess.run([sys.executable, str(ROOT / 'scripts/check_runtime_portability_v38.py'),
        '--output', str(ROOT / PREFIX / 'runtime-portability.json'), '--cpu', str(min(os.sched_getaffinity(0)))],
        cwd=ROOT, capture_output=True, text=True, timeout=30)
    save_new(PREFIX / 'runtime-portability-command.json', dict(exit_code=portability.returncode,
        stdout=portability.stdout[-16000:], stderr=portability.stderr[-16000:],
        purpose='Software metadata cross-check only. C4 uses the original backend.'))
    decision = admit_original_backend(read(ROOT / PREFIX / 'runtime-portability.json'), portability.returncode)
    save_new(PREFIX / 'runtime-portability-decision.json', decision)
    publish('Preserve original runtime and portable collector cross-check')
    with controller.research_worker_lock(ROOT):
        # The bounded bootstrap runs before scientific registration.
        # It loads the checkpoint and binds the target without neural inference.
        from research_v38.bootstrap_target import register_bootstrap, launch_bootstrap
        register_bootstrap(ROOT / PREFIX / 'bootstrap')
        publish('Register bounded C4 V38 target construction before checkpoint loading')
        bootstrap = launch_bootstrap(ROOT / PREFIX / 'bootstrap')
        save_new(PREFIX / 'bootstrap-audit.json', bootstrap)
        publish('Preserve C4 V38 target binding before registration')
        current, program = register_fresh(controller, prerequisite)
        admission = environment.preflight(current)
        save_new(PREFIX / 'registered-environment-preflight.json', admission)
        require(admission['status'] == 'passed', 'Registered runtime or worker limits failed')
        verify_v38_registration(controller)
        registration_commit = publish('Register C4 V38 before all model workers')
        save_new(PREFIX / 'registration-publication.json', {'registration_commit': registration_commit,
            'program_sha256': sha(current / 'program.json'), 'model_workers_started_before_publication': False})
        for trial_id in program['execution_order']:
            verify_v38_registration(controller)
            trial = next(t for t in program['trials'] if t['id'] == trial_id)
            save_new(CAMPAIGN / 'trial-intents' / (trial_id + '.json'), dict(trial=trial_id,
                state='intent_only_not_observed_usage', automatic_retry=False,
                planned_cpu_limit_seconds=trial['cpu_seconds'], planned_reservation_seconds=trial['cpu_seconds'] + 2,
                loss_policy='Preserve this intent if runner failure prevents a settled receipt. Do not infer CPU usage.'))
            publish('Record C4 V38 trial intent: ' + trial_id)
            outcome = controller.run('c4', trial_id)
            save_new(CAMPAIGN / 'attempts' / trial_id / 'controller-outcome-v38.json', outcome)
            if outcome['status'] != 'complete':
                publish('Preserve C4 V38 failed trial: ' + trial_id)
                raise RuntimeError('Registered trial failed. No retry or dependent work is authorized: ' + trial_id)
            audit = audit_trial(controller, analysis, current, program, trial_id)
            publish('Preserve C4 V38 settled trial and binary audit: ' + trial_id)
            print(json.dumps({'trial': trial_id, 'controller_seconds': audit['controller_seconds'],
                              'scientific_gates': audit['scientific_gates']}), flush=True)
        final = analysis.analyze('c4')
        save_new(CAMPAIGN / 'analysis-v38.json', final)
        require(final['all_seven_trials_verified'] and final['current_binary_artifacts_reverified'],
                'Final binary analysis is incomplete')
        publish('Complete C4 V38 with audited results and all outcomes')
        print(json.dumps({'status': final['status'], 'campaign': str(CAMPAIGN),
                          'cpu_charge': final['phase_budget']['charged_cpu_seconds']}), flush=True)


def finalize():
    """Preserve failures without invoking any worker or changing a ledger."""
    verify_claim()
    path = PREFIX / 'workflow-finalization.json'
    require(not (ROOT / path).exists(), 'Workflow finalization already exists')
    files = collect_text_paths()
    ledger = ROOT / CAMPAIGN / 'phase-cpu-budget/ledger.json'
    bootstrap_ledger = ROOT / PREFIX / 'bootstrap/phase-cpu-budget/ledger.json'
    save_new(path, dict(schema='free-c4-workflow-finalization-v38',
        job_status=os.environ.get('CI_JOB_STATUS', 'unknown'), automatic_retry=False,
        final_analysis_exists=(ROOT / CAMPAIGN / 'analysis-v38.json').is_file(),
        ledger_exists=ledger.is_file(), ledger_sha256=sha(ledger) if ledger.is_file() else None,
        bootstrap_ledger_exists=bootstrap_ledger.is_file(),
        bootstrap_ledger_sha256=sha(bootstrap_ledger) if bootstrap_ledger.is_file() else None,
        text_file_count=len(files), current_text_sha256={p: sha(ROOT / p) for p in files},
        artifact_storage_used=False, cache_storage_used=False,
        campaign_cpu_allowance_seconds=1900, bootstrap_cpu_allowance_seconds=122,
        total_separate_cpu_allowances_seconds=2022, bootstrap_audit_exists=(ROOT / PREFIX / 'bootstrap-audit.json').is_file(),
        abrupt_loss_policy='If settlement is unavailable, hold 1900 campaign CPU seconds and 122 bootstrap CPU seconds. These are not observed usage.'))
    publish('Preserve final C4 V38 workflow state')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('claim', 'fixtures', 'execute', 'finalize'))
    args = parser.parse_args()
    try:
        {'claim': claim_once, 'fixtures': software_fixtures, 'execute': execute, 'finalize': finalize}[args.action]()
    except BaseException as exc:
        error = dict(schema='free-c4-workflow-error-v38', action=args.action,
            error_type=type(exc).__name__, reason=str(exc)[:8000], traceback=traceback.format_exc()[-16000:],
            automatic_retry=False, no_further_model_work=True)
        print(json.dumps(error), flush=True)
        if args.action == 'execute' and (ROOT / CLAIM).exists():
            error_path = PREFIX / 'execution-error.json'
            if not (ROOT / error_path).exists():
                save_new(error_path, error)
            if not PUBLISH_BROKEN:
                publish('Preserve C4 V38 execution failure without retry')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
