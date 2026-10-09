#!/usr/bin/env python3
"""Parse the complete workflow before publication. No workflow is triggered.

This local check requires PyYAML. The hosted workflow does not install it.
GitHub remains the authority for platform-specific workflow validation.
"""
import argparse
import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = Path('.github/workflows/c4-v38.yml')
INSTALL = ('python -m pip install --disable-pip-version-check --no-cache-dir '
           '--only-binary=:all: --require-hashes -r requirements-ci-v38.txt')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate():
    raw = (ROOT / WORKFLOW).read_bytes()
    # BaseLoader retains the literal key "on" under PyYAML's YAML 1.1 parser.
    # It uses the full YAML scanner and parser. Scalar type coercion is unnecessary here.
    workflow = yaml.load(raw, Loader=yaml.BaseLoader)
    require(set(workflow['jobs']) == {'c4'}, 'Unexpected jobs')
    job = workflow['jobs']['c4']
    steps = job['steps']
    require(len(steps) == 7, 'Unexpected step count')
    install = next(step['run'] for step in steps if step['name'] == 'Install pinned numerical dependencies without cache')
    require(install == INSTALL, 'Parsed dependency command differs')
    require(workflow['on'] == {'push': {'branches': ['main'], 'paths': ['.github/ci/c4-v38-trigger.json']}},
            'Trigger changed')
    require(workflow['permissions'] == {'contents': 'write'}, 'Permissions changed')
    require(job['runs-on'] == 'ubuntu-24.04' and job['timeout-minutes'] == '60', 'Runner or limit changed')
    require("github.event.repository.private == false" in job['if'] and "github.run_attempt == '1'" in job['if'],
            'Public-only or one-use job guard changed')
    expected_actions = {
        'actions/checkout@11d5960a326750d5838078e36cf38b85af677262',
        'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065',
    }
    require({step['uses'] for step in steps if 'uses' in step} == expected_actions, 'Action pins changed')
    require(steps[1]['run'] == 'python3 scripts/execute_ci_c4_v38.py claim', 'Durable claim order changed')
    return dict(schema='ci-workflow-yaml-validation-v38', status='passed',
        parser='PyYAML BaseLoader', parser_version=yaml.__version__, workflow=str(WORKFLOW),
        workflow_sha256=hashlib.sha256(raw).hexdigest(), validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        complete_yaml_parsed=True, parsed_install_command=install, job_count=1, step_count=len(steps),
        workflow_trigger_pattern_unchanged=True, permissions_unchanged=True, numerical_workers_invoked=False,
        workflow_triggered=False, limitation='Local YAML and declared-field checks. GitHub validates workflow-specific contexts.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = validate()
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            stream.write(text)
    print(text, end='')


if __name__ == '__main__':
    main()
