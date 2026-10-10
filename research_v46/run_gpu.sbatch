#!/bin/bash
#SBATCH --job-name=second_v46_gpu
#SBATCH --partition=gpu-short
#SBATCH --qos=cpu-short
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:a100-80gb:1
#SBATCH --mem=16G
#SBATCH --time=00:30:00
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
unset PYTHONPATH LD_PRELOAD LD_AUDIT
module load pytorch/2.10
exec /nfs_home/software/envs/pytorch-12.8/bin/python -B "$@"
