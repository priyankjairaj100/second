"""Public GitHub execution with one-use claims and fail-closed publication."""
import importlib.metadata
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time
import traceback
from research_v39.policy import ROOT, PREFIX, REVISION, REPOSITORY, PHASE_CAP, DATA_CAP
from research_v39.policy import require, read, sha, new, TRIGGER as TRIGGER_PAYLOAD

TRIGGER = Path('.github/ci/scale-v39-trigger.json')
CLAIM = PREFIX / 'execution-claim.json'
PUBLISH_BROKEN = False

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def save(relative, value):
    return new(ROOT / relative, value)


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
    require(git('rev-parse', 'HEAD') == identity['event_commit'], 'Checkout differs from trigger')
    require(not (ROOT / PREFIX).exists(), 'One-use campaign already exists')
    require(not git('status', '--porcelain'), 'Claim requires a clean checkout')
    save(CLAIM, dict(identity, schema='one-use-free-scale-claim-v39', automatic_retry=False,
        phase_cpu_seconds=PHASE_CAP, data_cpu_seconds=DATA_CAP,
        abrupt_loss_policy='Hold 2400 model CPU seconds and 122 data CPU seconds if settlements cannot be recovered.',
        allowance_is_not_observed_usage=True, model_worker_started=False))
    publish('Claim the one-use real-data scale V39 pilot')


def verify_claim():
    identity = event_guard()
    claim = read(ROOT / CLAIM)
    require(all(claim.get(k) == v for k, v in identity.items()), 'Claim belongs to another run')
    require(claim['automatic_retry'] is False, 'Retry policy differs')
    require(git('merge-base', '--is-ancestor', identity['event_commit'], 'HEAD') == '', 'Trigger is not an ancestor')
    return claim


def assets():
    verify_claim()
    require(not (ROOT / PREFIX / 'asset-audit.json').exists(), 'Asset phase already ran')
    from research_v39.data import recover_assets
    from scripts.recover_assets_v32 import checkpoint_inventory
    result = recover_assets()
    result['checkpoint_audit'] = checkpoint_inventory()
    require(result['checkpoint_audit']['checkpoint_verified'], 'Checkpoint is not verified')
    result['resolved_distributions'] = {x.metadata['Name']: x.version for x in importlib.metadata.distributions()
                                        if x.metadata['Name']}
    save(PREFIX / 'asset-audit.json', result)
    publish('Preserve V39 checkpoint, real data, and resolved dependencies')


def fixtures():
    verify_claim()
    require((ROOT / PREFIX / 'asset-audit.json').is_file(), 'Assets must precede fixtures')
    require(not (ROOT / PREFIX / 'software-fixtures.json').exists(), 'Fixtures already ran')
    command = [sys.executable, '-m', 'unittest', 'tests.test_feature_primal_ball_v39',
               'tests.test_scale_protocol_v39', '-v']
    start = time.perf_counter_ns()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        result = dict(returncode=process.returncode, stdout=process.stdout[-64000:], stderr=process.stderr[-64000:])
    except subprocess.TimeoutExpired as error:
        def text(x):
            return x.decode(errors='replace') if isinstance(x, bytes) else x or ''
        result = dict(returncode=None, stdout=text(error.stdout)[-64000:], stderr=text(error.stderr)[-64000:])
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    result.update(passed=result['returncode'] == 0 and 'skipped=' not in result['stderr'], command=command,
        elapsed_ns=time.perf_counter_ns() - start,
        child_cpu_seconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
        cost_outside_empirical_ledgers=True, empirical_data_used=False)
    save(PREFIX / 'software-fixtures.json', result)
    publish('Preserve V39 host software checks before empirical registration')
    require(result['passed'], 'Software checks failed')


def execute():
    claim = verify_claim()
    require(read(ROOT / PREFIX / 'software-fixtures.json')['passed'], 'Host fixtures did not pass')
    require(not (ROOT / PREFIX / 'execution-start.json').exists(), 'Execution already started')
    save(PREFIX / 'execution-start.json', dict(revision=REVISION, automatic_retry=False))
    from research_v39 import controller
    from src.pilot_budget import research_worker_lock
    with research_worker_lock(ROOT):
        program = controller.register(claim['event_commit'])
        commit = publish('Register V39 data selection and all stage comparisons before execution')
        save(PREFIX / 'registration-publication.json', dict(commit=commit,
            program_sha256=sha(ROOT / PREFIX / 'program.json'), no_workers_before_publication=True))
        for trial in program['trials']:
            save(PREFIX / 'trial-intents' / (trial['id'] + '.json'), dict(trial=trial['id'],
                allowance_seconds=trial['cpu_seconds'] + 2, automatic_retry=False, observed_usage=False))
            publish('Preserve V39 trial intent: ' + trial['id'])
            status = controller.run_trial(trial['id'])
            publish('Preserve V39 settled trial and actual output audit: ' + trial['id'])
            require(status == 'complete', 'Registered attempt failed; no retry or dependent work: ' + trial['id'])
        save(PREFIX / 'analysis.json', controller.analyze())
        publish('Complete V39 real-data scale pilot with all arm outcomes')


def finalize():
    verify_claim()
    require(not (ROOT / PREFIX / 'workflow-finalization.json').exists(), 'Finalization already exists')
    paths = collect_text_paths()
    save(PREFIX / 'workflow-finalization.json', dict(schema='scale-workflow-finalization-v39',
        job_status=os.environ.get('CI_JOB_STATUS', 'unknown'), automatic_retry=False,
        analysis_exists=(ROOT / PREFIX / 'analysis.json').is_file(),
        text_sha256={p: sha(ROOT / p) for p in paths},
        artifact_storage=False, cache_storage=False, model_cpu_allowance=PHASE_CAP, data_cpu_allowance=DATA_CAP,
        abrupt_loss_policy='Hold each phase allowance without a recoverable settlement. Do not infer observed usage.'))
    publish('Preserve final V39 workflow state')


def main():
    action = sys.argv[1]
    actions = dict(claim=claim_once, assets=assets, fixtures=fixtures, execute=execute, finalize=finalize)
    require(action in actions, 'Unknown action')
    try:
        actions[action]()
    except BaseException as error:
        result = dict(action=action, error_type=type(error).__name__, error=str(error)[:8000],
            traceback=traceback.format_exc()[-16000:], automatic_retry=False, no_further_model_work=True)
        print(json.dumps(result), flush=True)
        if action != 'claim' and (ROOT / CLAIM).exists() and not PUBLISH_BROKEN:
            path = PREFIX / (action + '-error.json')
            if not (ROOT / path).exists():
                save(path, result)
                publish('Preserve V39 failure without retry: ' + action)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


