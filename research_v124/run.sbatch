#!/bin/bash
set -euo pipefail
root=/nfs_home/users/poonam/second-20261010
run="$root/local_runs/matched-quality-v124-20261029-a"
phase="$1"
registration="$2"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false RAYON_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=""
unset PYTHONPATH PYTHONHOME LD_PRELOAD LD_AUDIT
cd "$run"
if test "$phase" = data; then
  module load singularity/4.4.0
  manifest="$root/local_runs/cluster-setup-20261010/container-13155.sha256"
  test "$(sha256sum "$manifest" | cut -d ' ' -f1)" = 5a58e1fef1950aabf16cea4f44043b95a1f18d572a67d42dccac4b4b6d96d0b3
  sha256sum --check --status "$manifest"
  unset SINGULARITY_BINDPATH SINGULARITY_BIND APPTAINER_BINDPATH APPTAINER_BIND
  exec singularity exec --cleanenv --bind "$root:$root" --pwd "$run" \
    --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,PYTHONHASHSEED=0,OMP_NUM_THREADS=1,OPENBLAS_NUM_THREADS=1,MKL_NUM_THREADS=1,NUMEXPR_NUM_THREADS=1,TOKENIZERS_PARALLELISM=false,RAYON_NUM_THREADS=1" \
    "$root/local_runs/cluster-setup-20261010/python-3.12.14-bookworm.sif" \
    "$root/.venv-container/bin/python" -B "$run/research_v124/worker.py" "$phase" "$registration"
else
  exec /nfs_home/software/envs/pytorch-12.8/bin/python3.10 -B "$run/research_v124/worker.py" "$phase" "$registration"
fi
