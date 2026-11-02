"""One shared literal contract used by producer, actual child and seal reader."""
import sys
from pathlib import Path
from research_v80.io import require
from research_v90.admission import ledger_identity, verify_command_admission
from research_v90.worker_control import WorkerLimits
from research_v90.phase_budget import PhaseBudget, read_budget_snapshot
from research_v91.config import RUN, ROOT, PROFILES


def target_contract(profile, expected, job, cpu, *, root=RUN, cwd=ROOT, executable=None):
    require(profile in PROFILES and type(job) is str and job.isdigit(), 'Fixed profile and actual job required')
    require(type(cpu) is int and cpu >= 0, 'Single actual affinity CPU required')
    root=Path(root).absolute(); cwd=Path(cwd).absolute(); base=root/profile
    plan=dict(profile=profile, program=str(root/'program.json'), program_sha256=expected,
              output=str(base/'outputs'), slurm_job_id=job)
    command=[sys.executable if executable is None else executable, '-B',
             str(root/'research_v91/target_worker.py'), str(base/'plan.json')]
    limits=WorkerLimits(cpu_seconds=600, wall_seconds=900, address_space_bytes=16*2**30,
                       file_size_bytes=2*2**30, threads=1, affinity_cpus=(cpu,))
    return dict(plan=plan, command=command, limits=limits,
                identity=dict(program_sha256=expected, profile=profile),
                worker_root=base/'worker', budget_root=root/'budget', cwd=cwd)


def budget(program, expected, *, root=RUN, read_only=False):
    kwargs=dict(identity=ledger_identity(expected, program['sources']),
                phase_cpu_seconds=program['phase_cpu_seconds'])
    if read_only:
        snapshot=read_budget_snapshot(Path(root)/'budget', **kwargs)
        require(snapshot['status']=='verified','Actual complete ledger snapshot required')
        return snapshot
    return PhaseBudget(Path(root)/'budget', **kwargs)


def admit(contract, program, expected):
    return verify_command_admission(expected, 'admission', contract['command'],
        sources=program['sources'], phase_cpu_seconds=program['phase_cpu_seconds'],
        budget_root=contract['budget_root'], worker_root=contract['worker_root'],
        worker_identity=contract['identity'], limits=contract['limits'], cwd=contract['cwd'])
