"""Read-only exact-command admission for the NEW transfer ledger identity.

The caller first verifies its registered program, source inventory, literal
plan and Slurm job. Both controller and worker use this same identity function.
Nothing here initializes, locks, reserves, settles or repairs a ledger.
"""
import os
from pathlib import Path
from research_v90.phase_budget import read_budget_snapshot
from research_v90.worker_control import WorkerLimits
from research_v90.run_store import canonical_json, strict_json, digest


def require(ok, message):
    if not ok: raise ValueError(message)


def ledger_identity(program_sha256, sources):
    require(type(program_sha256) is str and len(program_sha256) == 64
            and all(c in '0123456789abcdef' for c in program_sha256), 'Exact program digest required')
    require(type(sources) is dict and 0 < len(sources) <= 4096, 'Exact bounded source inventory required')
    for name, entry in sources.items():
        p = Path(name)
        require(type(name) is str and not p.is_absolute() and str(p) == name and '..' not in p.parts,
                'Relative bound source path required')
        require(type(entry) is dict and set(entry) == {'bytes', 'sha256'}
                and type(entry['bytes']) is int and 0 <= entry['bytes'] <= 64*2**20
                and type(entry['sha256']) is str and len(entry['sha256']) == 64
                and all(c in '0123456789abcdef' for c in entry['sha256']), 'Exact bound source entry required')
    return dict(program_sha256=program_sha256, sources_sha256=digest(canonical_json(sources)))


def verify_command_admission(program_sha256, phase, expected_command, *, sources,
                             phase_cpu_seconds, budget_root, worker_root,
                             worker_identity, limits, cwd):
    identity = ledger_identity(program_sha256, sources)
    require(type(limits) is WorkerLimits, 'Explicit registered worker limits required')
    require(type(expected_command) is list and expected_command
            and all(type(x) is str and x and '\0' not in x for x in expected_command)
            and Path(expected_command[0]).is_absolute(), 'Literal absolute-executable command required')
    root = Path(budget_root).absolute(); worker = Path(worker_root).absolute(); work = Path(cwd).absolute()
    for path in (root, worker, work):
        require('..' not in path.parts and not any(p.is_symlink() for p in (path, *path.parents)),
                'Nonsymbolic literal admission path required')
    encoded = os.environ.get('CALIBRATION_PHASE_CPU_ADMISSION')
    require(type(encoded) is str and len(encoded) <= 2**20, 'Active bounded CPU admission required')
    admission = strict_json(encoded)
    require(type(admission) is dict and set(admission) == {
        'phase_budget_root', 'phase_budget_binding_sha256', 'attempt_id', 'phase', 'command', 'cwd'},
        'Exact admission schema required')
    require(admission['phase_budget_root'] == str(root) and admission['cwd'] == str(work)
            and admission['phase'] == phase and admission['command'] == expected_command,
            'Admission does not bind exact command, paths and phase')
    snapshot = read_budget_snapshot(root, identity=identity, phase_cpu_seconds=phase_cpu_seconds)
    require(snapshot['status'] == 'verified' and not any(snapshot['over_cap'].values())
            and not snapshot['reservation_overrun_attempts'], 'Valid unchanged-cap ledger required')
    binding_sha = snapshot['binding_sha256']
    require(admission['phase_budget_binding_sha256'] == binding_sha, 'Admission ledger digest differs')
    binding = dict(schema='limited-worker-identity-v1', identity=worker_identity,
                   command=expected_command, cwd=str(work), limits=limits.payload(),
                   phase_budget=dict(binding_sha256=binding_sha, phase=phase, directory=str(root)))
    attempt_id = digest(canonical_json(dict(worker=binding, attempt=str(worker/'attempt-0001'))))
    require(admission['attempt_id'] == attempt_id, 'Admission belongs to another worker or attempt')
    row = snapshot['attempts'].get(attempt_id)
    require(row is not None and row['state'] == 'reserved' and row['phase'] == phase
            and row['reserved_cpu_seconds'] == row['charged_cpu_seconds'] == limits.cpu_seconds+2
            and row['observed_cpu_ns'] is None, 'Exact live reservation required before execution')
    return dict(admission)
