"""Unchanged V84 workload with separate source/gate/namespace identities."""
from pathlib import Path
from research_v84.config import (ROOT, PROFILES, CELLS, ARM_ORDER, LOCAL_ORDER, ORDER,
    TRIALS, CAP, REBUILT_REPRESENTATIONS, trial_parts, predecessor, expected_artifacts)
from research_v84.config import design as original_design
RUN=ROOT/'local_runs/matched-complete-recovery-v100-20261026-a'
ADMISSION=ROOT/'local_runs/matched-transfer-admission-v101-20261026-a'
OPERATIONS=('checks',*ORDER,'primary','supplemental')

def name(operation):
    if operation not in OPERATIONS:raise ValueError('Unknown matched operation')
    return operation.replace('/','--')

def wall(operation):
    if operation in TRIALS:return TRIALS[operation]['wall_seconds']+600
    return {'checks':600,'primary':9000,'supplemental':5400}[operation]

def cpu(operation):
    if operation in TRIALS:return 300,10202,302
    return {'checks':(300,902,302),'primary':(7200,7201,7201),'supplemental':(3600,3601,3601)}[operation]

def design():
    p=original_design()
    for k in ('software_modules','expected_tests'):p.pop(k)
    p.update(schema='matched-complete-recovery-v100',directory=str(RUN),target_admission_directory=str(ADMISSION),
        worker_output_limits=dict(state_bytes=2**30,metadata_bytes=64*2**20,progress_bytes=2**20,
            progress_files='source-bound V90 per-phase census',model_extent='exact packed model bytes'),
        upstream_policy='Actual V89 and V101 terminal inputs reopened; no successful old V80/V81/V82 substitution',
        primary_timing='Complete host envelope including source checks, startup, numerical work, sealing and shutdown; final write in scheduler',
        complete_host_accounting_required=True,per_worker_complete_controller_seconds=302,
        empirical_result=False,source_packaging_requires_actual_upstream=True)
    return p
