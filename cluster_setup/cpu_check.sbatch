#!/bin/bash
#SBATCH --job-name=second_cpu_setup
#SBATCH --partition=cpu-short
#SBATCH --qos=cpu-short
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:10:00

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
unset PYTHONPATH LD_PRELOAD LD_AUDIT
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TOKENIZERS_PARALLELISM=false
exec .venv/bin/python -B -m cluster_setup.cpu_check "local_runs/cluster-setup-20261010/cpu-${SLURM_JOB_ID}"
