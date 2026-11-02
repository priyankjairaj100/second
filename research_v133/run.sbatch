#!/bin/bash
set -euo pipefail
root=/nfs_home/users/poonam/second-20261010
run="$root/local_runs/sequential-output-audit-v133-20261029-a"
phase="$1"
registration="$2"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false RAYON_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=""
unset PYTHONPATH PYTHONHOME LD_PRELOAD LD_AUDIT
cd "$run"
exec /nfs_home/software/envs/pytorch-12.8/bin/python3.10 -B "$run/research_v133/worker.py" "$phase" "$registration"
