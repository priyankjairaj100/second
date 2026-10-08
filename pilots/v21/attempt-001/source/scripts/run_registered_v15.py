"""Run the fixed dyadic complete-state controls serially, stopping on failure."""
import fcntl
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.run_store import atomic_write, canonical_json, digest


def main():
    root = Path(__file__).resolve().parents[1]
    archive = root / 'pilots/v15'
    program_path = archive / 'prospective-program.json'
    program = json.loads(program_path.read_bytes())
    outcomes = dict(schema='v15-program-outcomes', status='running', slots=[],
                    program_sha256=digest(program_path.read_bytes()))

    def save():
        atomic_write(archive / 'program-outcomes.json', canonical_json(outcomes))

    for slot in program['runs']:
        directory = archive / slot['id']
        if directory.exists():
            receipt = json.loads((directory / 'worker/result.json').read_bytes())
        else:
            command = [sys.executable, str(root / 'scripts/launch_compact_service_pilot.py'),
                       '--revision', 'v15', '--id', slot['id'], '--method', slot['method'],
                       '--grid-axis', program['grid_axis'], '--solver-backend', program['solver_backend']]
            for index in slot['delete_indices']:
                command.extend(['--delete-index', str(index)])
            if slot['prior']:
                command.extend(['--prior-attempt', slot['prior']])
            save()
            process = subprocess.run(command, cwd=root)
            path = directory / 'worker/result.json'
            if not path.exists():
                outcomes['slots'].append(dict(id=slot['id'], status='unstarted',
                                              reason='admission rejected or launcher failed', returncode=process.returncode))
                break
            receipt = json.loads(path.read_bytes())
        ledger = json.loads((directory / 'phase-cpu-budget/ledger.json').read_bytes())
        if (receipt.get('budget_debit', {}).get('state') != 'settled'
                or any(row['state'] != 'settled' for row in ledger['attempts'].values())):
            raise ValueError('existing attempt is still reserved; no duplicate worker admitted')
        status = receipt['outcome']['status']
        outcomes['slots'].append(dict(id=slot['id'], status=status))
        save()
        if status != 'complete':
            break
    known = {row['id'] for row in outcomes['slots']}
    for slot in program['runs']:
        if slot['id'] not in known:
            outcomes['slots'].append(dict(id=slot['id'], status='unstarted', reason='prior stop condition'))
    outcomes['status'] = 'settled'
    save()
    print(json.dumps(outcomes))


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'pilots/v15/controller.lock'
    with path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
