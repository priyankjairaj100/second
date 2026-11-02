"""Fixed workload and bounded ceilings; registration binds these exact values."""
from pathlib import Path
from src.run_store import digest
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/four-cell-recovery-v89-20261023-a'
STAGED={63:ROOT/'local_runs/lossless-control-v63-20261016-a',
        64:ROOT/'local_runs/modern-service-checks-v64-20261016-a',
        65:ROOT/'local_runs/disjoint-data-v65-20261016-a',
        66:ROOT/'local_runs/complete-service-checks-v66-20261016-a'}
CELLS={'reference_compressed':'compressed','reference_modern':'modern',
       'optimized_compressed':'compressed','optimized_modern':'modern'}
ARMS=tuple(CELLS)
ARM_ORDER=sorted(ARMS,key=lambda a:digest(('second-four-cell-development-v80:'+a).encode()))
ORDER=['prepare',*[a+'-1' for a in ARM_ORDER],*[a+'-2' for a in reversed(ARM_ORDER)],'oracle']
TRIALS={'prepare':dict(cpu_seconds=12600,wall_seconds=16200),'oracle':dict(cpu_seconds=16200,wall_seconds=21600)}
for cell,arm in CELLS.items():
    pairs={'compressed':[(12600,16200),(9000,12600)],'modern':[(10800,14400),(7200,10800)]}[arm]
    for step,(cpu,wall) in enumerate(pairs,1):TRIALS[cell+'-'+str(step)]=dict(cpu_seconds=cpu,wall_seconds=wall)
CAP=sum(x['cpu_seconds']+2 for x in TRIALS.values())
MEMORY=16*2**30
FILE_LIMIT=2*2**30
ARTIFACT_LIMIT=2**30
RESIDENT=9*2**30
RECORDS_SHA='3bbdefd1e2836d6797723f8426d9ad359d36da2b2e13b35df4661002a8db89b9'
SELECTION_SHA='15936823286a872fd4f3996446eea5fce9a717eafad8a50d0cb918e9b40cd85b'
V65_REG='13d9ecb7ddb9ee37ba05498387af490a5e6f16879340c4ec301bbe2aaf5f08d2'
V66_REG='5727138fa7739700e5d14b10a015e33b42765da19dad80b6723a3bdf29e5ada3'
# The exact base and numerical payload hashes are supplied by the immutable
# prior evidence bindings; their actual canonical bytes are compared in workers.
BASE_TARGET='ddcc41a5420a63c60f64372af1fb5e077efc9266ad12feafe6ed04be5d6248b8'
SERVICE_TARGET='ded01d9b27816eb32a8ddc241f0c014a05b43a5ffe7ce6f2f0a8853aefb3d0ad'
CALIBRATION_TARGET='3853008973e0a89db5c80d73d30cb4304bc5d9c89fafa80e6f7f15de232a1245'

def design():
    return dict(schema='four-cell-recovery-v89',directory=str(RUN),trials=TRIALS,trial_order=ORDER,
        old_unknown_reservation_cpu_seconds=12602,combined_recovery_reservation_cpu_seconds=12602+CAP,
        old_controller_reservation_cpu_seconds=602,combined_controller_reservation_cpu_seconds=6622,
        phase_cpu_seconds=CAP,preserved_phase_ceiling=120624,cells=CELLS,process_address_space_bytes=MEMORY,file_size_bytes=FILE_LIMIT,
        artifact_limit_bytes=ARTIFACT_LIMIT,resident_reservation_bytes=RESIDENT,
        normalization=1664,record_count=13,tokens_per_record=128,retained_counts=[12,6],
        precision=48,block_size=256,code_count=42_467_328,model_bytes=21_233_664,stage_count=24,
        shared_backend='normal_neighbor_primal_v50',confirmation=False,quality_evaluation=False,
        automatic_retry=False,threads=1,startup='fresh_process_and_context_per_request',
        cache_policy='OS cache uncontrolled; no flushing; same admitted CPU host',
        arm_order_seed='second-four-cell-development-v80:',audit_history_physically_retained=True,
        numerical_checkout='f900999fcb200509dfad4fc081ce9c87fd172a16',
        controller_cpu_soft_seconds=600,controller_cpu_hard_seconds=16802,
        controller_allowance_cpu_seconds=6020,preserved_controller_ceiling=7224,software_allowance_cpu_seconds=602,
        software_wall_seconds=600,controller_wall_overhead_seconds=600,slurm_host='csis.mn1',
        primary_audit_caps=dict(cpu=7200,wall=9000),supplemental_audit_caps=dict(cpu=3600,wall=5400))
