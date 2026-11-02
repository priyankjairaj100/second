#!/bin/bash
# All resource requests are explicit in the registered held-job launcher.
set -euo pipefail
root=/nfs_home/users/poonam/second-20261010
run="$root/local_runs/untouched-quality-v71-20261018-a"
test "$#" -eq 2
phase="$1"
registration="$2"
[[ "$registration" =~ ^[0-9a-f]{64}$ ]]
case "$phase" in cuda_checks|gpu_quality) ;; *) exit 2 ;; esac
test -n "${SLURM_JOB_ID:?}"
cd "$root"
unset PYTHONPATH PYTHONHOME PYTHONOPTIMIZE LD_PRELOAD LD_AUDIT
module load pytorch/2.10
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 RAYON_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
exec /nfs_home/software/envs/pytorch-12.8/bin/python3.10 -B "$run/research_v71/entry.py" "$phase" "$registration"
