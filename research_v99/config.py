"""Fixed recovery admission scope. Only actual V89 closure can qualify it."""
from pathlib import Path
from research_v81.profile import PROFILES, PROPOSED_GRID_CAP
from research_v82.selection import SEED
ROOT = Path('/nfs_home/users/poonam/second-20261010')
RUN = ROOT/'local_runs/matched-transfer-admission-v99-20261026-a'
OLD_PROGRAM = ROOT/'local_runs/four-cell-service-v80-20261023-a/program.json'
OLD_SHA = '89f6a71e5b4f74b667bac64149c77005862d36b2b2e3dedc2a7260fb05c0ad60'
ORDER = ('checks', 'fetch', 'distilgpt2', 'gpt2', 'close')
WALL = {'checks': 600, 'fetch': 600, 'distilgpt2': 1500, 'gpt2': 1500, 'close': 600}
TARGET_FILES = ('records.json', 'selection.json', 'anchor-target.json', 'service-target.json',
    'calibration-target.json', 'execution-provenance.json', 'structural-admission.json', 'actual-admission.json')


def design():
    return dict(schema='matched-transfer-admission-v99', directory=str(RUN), order=list(ORDER),
        selection_seed=SEED, profiles=PROFILES, grid_allowance=PROPOSED_GRID_CAP,
        grid_allowance_user_approved=True, grid_approval_text='Approve the transfer-only grid allowance',
        numerical_checkout='f900999fcb200509dfad4fc081ce9c87fd172a16',
        historical_input_registry=dict(path=str(OLD_PROGRAM), sha256=OLD_SHA),
        checkpoint_paths={'distilgpt2':str(ROOT/'tmp/models/distilgpt2'), 'gpt2':str(RUN/'checkpoint/gpt2')},
        target_cpu_seconds=600, target_wall_seconds=900, phase_cpu_seconds={'admission':1204},
        process_memory_bytes=16*2**30, file_size_bytes=2*2**30, threads=1, host='csis.mn1',
        controller_cpu_soft_seconds=300, target_controller_cpu_hard_seconds=902,
        controller_allowance_seconds=1510, per_operation_controller_seconds=302,
        software_aggregate_cpu_seconds=602, operation_wall_seconds=WALL,
        automatic_retry=False, neural_execution=False, calibration_execution=False,
        request_benchmark=False, quality_evaluation=False, model_transfer_result=False,
        upstream_policy='Actual V89 terminal and all reopened inputs; old failures and full12602 debit retained')
