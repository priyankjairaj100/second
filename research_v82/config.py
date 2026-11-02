"""Lightweight preregistration constants; no model or numerical execution."""
from pathlib import Path
from research_v81.profile import PROFILES,PROPOSED_GRID_CAP
from research_v82.selection import SEED
ROOT=Path("/nfs_home/users/poonam/second-20261010")
RUN=ROOT/"local_runs/matched-transfer-admission-v82-20261023-a"
DESIGN=dict(schema='matched-transfer-admission-v82',selection_seed=SEED,profiles=PROFILES,
    grid_allowance=PROPOSED_GRID_CAP,grid_allowance_user_approved=True,numerical_checkout='f900999fcb200509dfad4fc081ce9c87fd172a16',
    target_cpu_seconds=600,target_wall_seconds=900,target_phase_cpu_seconds=1204,
    process_memory_bytes=16*2**30,file_size_bytes=2*2**30,threads=1,host='csis.mn1',
    automatic_retry=False,neural_execution=False,calibration_execution=False,
    order=['checks','fetch','distilgpt2','gpt2','close'],expected_software_tests=26,
    checkpoint_paths={'distilgpt2':str(ROOT/'tmp/models/distilgpt2'),'gpt2':str(RUN/'checkpoint/gpt2')},
    controller_process_cpu_soft_seconds=300,controller_process_cpu_hard_seconds=902,
    controller_cpu_allowance_seconds=1510,software_aggregate_cpu_seconds=602,
    prerequisite_policy='Known V81 program/job/exact-count result, host terminal gate and immutable first-admission receipt binding',
    grid_approval_text='Approve the transfer-only grid allowance')
