"""New finite target admission controller; no command or ledger reuse."""
import os
from pathlib import Path
from research_v80.io import json_read, require
from research_v90.worker_control import run_limited
from research_v91.config import RUN, PROFILES
from research_v91.contracts import target_contract, budget
from research_v91.records import transaction_writer, writer


def admit_target(profile, program, expected):
    require(profile in PROFILES, 'Known profile required')
    folder=RUN/profile; folder.mkdir(exist_ok=False)
    c=target_contract(profile, expected, os.environ['SLURM_JOB_ID'], min(os.sched_getaffinity(0)))
    records=transaction_writer(folder); records.write('plan.json',c['plan'])
    ledger=budget(program,expected)
    receipt=run_limited(c['command'],c['worker_root'],c['limits'],identity=c['identity'],
        cwd=c['cwd'],phase_budget=ledger,phase='admission')
    records.write('transaction.json',dict(worker_outcome=receipt['outcome'],budget=ledger.snapshot(),
        slurm_job_id=c['plan']['slurm_job_id']))
    require(receipt['outcome']['status']=='complete' and receipt['outcome']['returncode']==0,
            'Target admission failed; preserve consumed result')
    return dict(profile=profile,completion=json_read(folder/'outputs/completion.json'))


def close(program,expected):
    snapshot=budget(program,expected,read_only=True)
    require(len(snapshot['attempts'])==2 and not any(snapshot['over_cap'].values())
        and not snapshot['reservation_overrun_attempts'] and not snapshot['reserved_unknown_attempts']
        and all(x['state']=='settled' for x in snapshot['attempts'].values()), 'Exactly two settled target attempts required')
    from research_v91.seals import verify
    audit=verify(RUN,program,expected,snapshot)
    result=dict(schema='matched-target-close-v91',status='admitted_pending_host_terminal_accounting',
        program_sha256=expected,seal_audit=audit,budget=snapshot,
        empirical_transfer=False,neural_execution=False,calibration_execution=False,quality_evaluation=False)
    writer().write('close-report.json',result)
    return result
