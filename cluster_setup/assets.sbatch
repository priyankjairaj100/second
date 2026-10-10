#!/bin/bash
#SBATCH --job-name=second_pinned_assets
#SBATCH --partition=cpu-short
#SBATCH --qos=cpu-short
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
unset PYTHONPATH LD_PRELOAD LD_AUDIT
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
.venv/bin/python -B - <<'PY'
import json
import os
from pathlib import Path
from research_v39.data import recover_assets
from scripts.recover_assets_v32 import checkpoint_inventory

assert os.environ.get('SLURM_JOB_ID'), 'Slurm allocation required'
output = Path('local_runs/cluster-setup-20261010') / ('assets-' + os.environ['SLURM_JOB_ID'])
output.mkdir(parents=True, exist_ok=False)
report = dict(schema='second-pinned-asset-setup-v1', model_inference=False,
              historical_binary_reproduction=False, empirical_worker_launched=False)
try:
    report['recovery'] = recover_assets()
    report['checkpoint'] = checkpoint_inventory()
    assert report['checkpoint']['checkpoint_verified']
    report['passed'] = True
except Exception as exc:
    report.update(passed=False, error=str(exc))
    raise
finally:
    (output / 'summary.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps(dict(passed=True, output=str(output))))
PY
