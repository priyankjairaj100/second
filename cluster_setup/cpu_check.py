"""Validate a new Linux runtime under Slurm using software fixtures only.

Usage: python -B -m cluster_setup.cpu_check NEW_OUTPUT_DIRECTORY
This is setup evidence, not an empirical campaign or historical reproduction.
"""
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not os.environ.get('SLURM_JOB_ID'):
        raise SystemExit('Run through Slurm, not on the login node.')
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    report = dict(schema='second-cluster-software-check-v1',
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  python=platform.python_version(), system=platform.system(), machine=platform.machine(),
                  slurm_job_id=os.environ['SLURM_JOB_ID'], checks=[],
                  empirical_worker_launched=False, historical_runtime_equivalence=False,
                  software_cost_outside_empirical_ledgers=True,
                  packages={x.metadata['Name']: x.version for x in importlib.metadata.distributions() if x.metadata['Name']})
    def save():
        (output / 'summary.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    def check(name, args, timeout=180):
        started = time.monotonic()
        with (output / (name + '.stdout')).open('x') as stdout, (output / (name + '.stderr')).open('x') as stderr:
            result = subprocess.run([sys.executable, '-B', *args], cwd=ROOT, stdout=stdout,
                                    stderr=stderr, timeout=timeout)
        report['checks'].append(dict(name=name, returncode=result.returncode,
                                     elapsed_seconds=time.monotonic() - started))
        save()
        if result.returncode:
            raise RuntimeError(name + ' failed; inspect saved logs')
    save()
    try:
        check('environment', ['scripts/preflight_environment_v34.py'])
        check('capture', ['scripts/check_runtime.py', '--capture', str(output / 'runtime.json')])
        check('verify', ['scripts/check_runtime.py', '--verify', str(output / 'runtime.json')])
        check('v40-fixtures', ['-m', 'unittest', 'tests.test_native_exact_gram_v40',
                              'tests.test_streamed_primal_ball_v40', 'tests.test_scale_protocol_v40', '-v'])
        check('v38-v39-fixtures', ['-m', 'unittest', 'tests.test_live_runtime_v38',
                                  'tests.test_feature_primal_ball_v39', 'tests.test_scale_protocol_v39', '-v'])
        report['passed'] = True
    except Exception as exc:
        report['passed'] = False
        report['error'] = str(exc)
        raise
    finally:
        save()
    print(json.dumps(dict(passed=True, output=str(output), checks=len(report['checks']))))


if __name__ == '__main__':
    main()
