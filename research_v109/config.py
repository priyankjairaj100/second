"""Prospective single-stage diagnostic inside remaining original ceilings."""
from pathlib import Path

ROOT = Path('/nfs_home/users/poonam/second-20261010')
RUN = ROOT/'local_runs/token-stage-diagnostic-v109-20261026-a'
PARENT = ROOT/'local_runs/matched-complete-recovery-v104-20261026-a'
PARENT_SHA = '2c0ae1a89184ec51d9d759a6ed6d65f15b8a4fc136e8475b89b82cff4b5a812f'
STAGE = 'block.0011.mlp_up'
OPERATIONS = ('checks', 'diagnostic')
ORDER = ('diagnostic',)
TRIALS = dict(diagnostic=dict(cpu_seconds=600, wall_seconds=750))
CAP = 602


def name(operation):
    if operation not in OPERATIONS:
        raise ValueError('Unknown diagnostic operation')
    return operation


def wall(operation):
    name(operation)
    return 600 if operation == 'checks' else 900


def cpu(operation):
    name(operation)
    return (58, 903, 60) if operation == 'checks' else (300, 903, 302)


def design():
    return dict(schema='token-stage-diagnostic-v109', directory=str(RUN),
        numerical_checkout='f900999fcb200509dfad4fc081ce9c87fd172a16',
        parent_program_sha256=PARENT_SHA, profile='gpt2', stage_id=STAGE,
        retained_counts=[3], original_normalization=512, block_tokens=128,
        stage_shape=[3072, 768], route='token', input_kind='point',
        input_source='original complete preparation lossless factors',
        target_changed=False, original_route_repeated=False,
        carried_numerical_seconds=6196, diagnostic_cpu_reservation=CAP,
        original_numerical_ceiling=82840,
        carried_software_seconds=139, software_aggregate_seconds=180,
        original_software_ceiling=602, carried_checks_controller_seconds=33,
        checks_controller_seconds=60, original_checks_controller_ceiling=302,
        carried_numerical_controller_seconds=63, numerical_controller_seconds=302,
        original_numerical_controller_ceiling=6040,
        full_model_comparison=False, transfer_evidence=False, speed_comparison=False,
        cpu_count=1, process_bytes=16*2**30, max_stage_work_units=64_000_000_000,
        max_array_bytes=8*2**30, caller_resident_bytes=9*2**30,
        exact_refinement_coordinates=16, grid_cap=1327104,
        retries_allowed=False, checks_required_before_diagnostic=True)
