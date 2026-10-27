"""Unchanged V84 workload with separate source/gate/namespace identities."""
from pathlib import Path
from research_v84.config import (ROOT, PROFILES, CELLS, ARM_ORDER, LOCAL_ORDER,
    REBUILT_REPRESENTATIONS, predecessor, expected_artifacts)
from research_v84.config import ORDER as ORIGINAL_ORDER, TRIALS as ORIGINAL_TRIALS
from research_v84.config import design as original_design
RUN=ROOT/'local_runs/matched-complete-recovery-v111-20261026-a'
PARENT=ROOT/'local_runs/matched-complete-recovery-v104-20261026-a'
PARENT_SHA='2c0ae1a89184ec51d9d759a6ed6d65f15b8a4fc136e8475b89b82cff4b5a812f'
DIAGNOSTIC=ROOT/'local_runs/token-stage-diagnostic-v110-20261026-a'
DIAGNOSTIC_SHA='29e114bb8cae47f5dc8fa70a346d62cd575e6b0dfc959b286903bed0071e2602'
ORDER=[t for t in ORIGINAL_ORDER if not t.endswith('/prepare')]
TRIALS={t:dict(ORIGINAL_TRIALS[t]) for t in ORDER}
CAP=sum(t['cpu_seconds']+2 for t in TRIALS.values())
SOFTWARE_CAP=395
CHECKS_CONTROLLER_CAP=254
POLICY='all-point-inputs-token-from-start-v111'
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
    return {'checks':(252,883,CHECKS_CONTROLLER_CAP),'primary':(7200,7201,7201),'supplemental':(3600,3601,3601)}[operation]

def trial_parts(trial):
    if trial not in TRIALS:raise ValueError('Unknown new matched trial')
    return tuple(trial.split('/'))

def predecessor_directory(trial,root=RUN,parent=PARENT):
    prior,_,_=predecessor(trial)
    return Path(parent if prior.endswith('/prepare') else root)/prior/'outputs'

def design():
    p=original_design()
    for k in ('software_modules','expected_tests'):p.pop(k)
    p.update(schema='matched-complete-recovery-v111',directory=str(RUN),target_admission_directory=str(ADMISSION),
        worker_output_limits=dict(state_bytes=2**30,metadata_bytes=64*2**20,progress_bytes=2**20,
            progress_files='source-bound V90 per-phase census',model_extent='exact packed model bytes'),
        upstream_policy='Actual V89 and V101 terminal inputs reopened; no successful old V80/V81/V82 substitution',
        primary_timing='Complete host envelope including source checks, startup, numerical work, sealing and shutdown; final write in scheduler',
        complete_host_accounting_required=True,per_worker_complete_controller_seconds=302,
        trial_order=ORDER,trials=TRIALS,phase_cpu_seconds=CAP,
        parent_preparation_directory=str(PARENT),parent_preparation_program_sha256=PARENT_SHA,
        point_route_policy=POLICY,point_streamed_attempted=False,box_policy_unchanged=True,
        carried_numerical_seconds=6304,original_matched_numerical_ceiling=82840,
        carried_failed_software_seconds=207,software_aggregate_cpu_seconds=SOFTWARE_CAP,
        carried_numerical_controller_seconds=79,controller_cpu_allowance_seconds=5436,
        carried_checks_controller_seconds=48,original_software_aggregate_seconds=602,
        original_checks_controller_seconds=302,empirical_result=False,source_packaging_requires_actual_upstream=True)
    return p
