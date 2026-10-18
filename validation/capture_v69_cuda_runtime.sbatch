#!/bin/bash
set -euo pipefail
root=/nfs_home/users/poonam/second-20261010
run="$root/local_runs/cuda-runtime-v69-20261018-a"
test "$#" -eq 1
[[ "$1" =~ ^[0-9a-f]{64}$ ]]
cd "$root"
unset PYTHONPATH PYTHONHOME PYTHONOPTIMIZE LD_PRELOAD LD_AUDIT
module load pytorch/2.10
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 RAYON_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
exec /nfs_home/software/envs/pytorch-12.8/bin/python3.10 -B "$run/capture_v69_cuda_runtime.py" "$1"
