#!/bin/bash
#SBATCH --job-name=second_cuda_setup
#SBATCH --partition=gpu-short
#SBATCH --qos=cpu-short
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:a100-80gb:1
#SBATCH --mem=8G
#SBATCH --time=00:05:00

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
unset PYTHONPATH LD_PRELOAD LD_AUDIT
# The shared GPU environment is isolated from the exact CPU environment.
module load pytorch/2.10
/nfs_home/software/envs/pytorch-12.8/bin/python -B - <<'PY'
import json
import os
from pathlib import Path
import torch

assert os.environ.get('SLURM_JOB_ID'), 'Slurm allocation required'
output = Path('local_runs/cluster-setup-20261010') / ('gpu-' + os.environ['SLURM_JOB_ID'])
output.mkdir(parents=True, exist_ok=False)
report = dict(schema='second-cuda-engineering-smoke-v1', torch=torch.__version__,
              cuda_build=torch.version.cuda, cuda_available=torch.cuda.is_available(),
              slurm_job_id=os.environ['SLURM_JOB_ID'], synthetic_fixture=True,
              research_target_equivalence_established=False, empirical_evidence=False)
try:
    assert report['cuda_available'], 'CUDA is not available'
    torch.manual_seed(0)
    layer = torch.nn.Linear(16, 8).cuda()
    batch = torch.randn(4, 16, device='cuda')
    with torch.no_grad():
        answer = layer(batch)
    torch.cuda.synchronize()
    assert answer.is_cuda and answer.shape == (4, 8) and torch.isfinite(answer).all().item()
    report.update(passed=True, device=torch.cuda.get_device_name(0),
                  device_count=torch.cuda.device_count(),
                  device_memory_bytes=torch.cuda.get_device_properties(0).total_memory,
                  batch_shape=list(batch.shape), result_shape=list(answer.shape))
except Exception as exc:
    report.update(passed=False, error=str(exc))
    raise
finally:
    (output / 'summary.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps(report))
PY
