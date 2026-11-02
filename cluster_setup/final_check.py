"""Final setup checks for the new planner and actual container runtime.

Run through run_cpu.sbatch. No model inference or empirical ledger is used.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    job = os.environ.get('SLURM_JOB_ID')
    if not job:
        raise SystemExit('Slurm allocation required')
    output = ROOT / 'local_runs/cluster-setup-20261010' / ('final-' + job)
    output.mkdir(parents=True, exist_ok=False)
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for d in ('cluster_setup', 'research_v42') for p in (ROOT / d).iterdir() if p.is_file()}
    report = dict(schema='second-final-setup-check-v1', source_sha256=sources, checks=[],
                  empirical_worker_launched=False, acl_submission_ready=False)
    commands = [
        ('planner-fixtures', ['-m', 'unittest', 'research_v42.test_resource_plan', '-v']),
        ('resource-plan', ['-m', 'research_v42.resource_plan', '--output', str(output / 'resource-plan.json')]),
        ('portability', ['scripts/check_runtime_portability_v38.py', '--output', str(output / 'runtime-portability.json')]),
    ]
    try:
        for name, args in commands:
            with (output / (name + '.stdout')).open('x') as out, (output / (name + '.stderr')).open('x') as err:
                process = subprocess.run([sys.executable, '-B', *args], cwd=ROOT,
                                         stdout=out, stderr=err, timeout=180)
            report['checks'].append(dict(name=name, returncode=process.returncode))
            if process.returncode:
                raise RuntimeError(name + ' failed; inspect saved logs')
        report['passed'] = True
    except Exception as exc:
        report.update(passed=False, error=str(exc))
        raise
    finally:
        (output / 'summary.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(passed=True, output=str(output))))


if __name__ == '__main__':
    main()
