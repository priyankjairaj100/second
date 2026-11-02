#!/bin/bash
set -euo pipefail
root=/nfs_home/users/poonam/second-20261010
run="$root/local_runs/token-stage-diagnostic-v110-20261026-a"
test "$#" -ge 2
[[ "$2" =~ ^[0-9a-f]{64}$ ]]
test -n "${SLURM_JOB_ID:?}"
cd "$run"
manifest="$root/local_runs/cluster-setup-20261010/container-13155.sha256"
image="$root/local_runs/cluster-setup-20261010/python-3.12.14-bookworm.sif"
test "$(sha256sum "$manifest" | cut -d ' ' -f1)" = 5a58e1fef1950aabf16cea4f44043b95a1f18d572a67d42dccac4b4b6d96d0b3
sha256sum --check --status "$manifest"
module load singularity/4.4.0
unset SINGULARITY_BINDPATH SINGULARITY_BIND APPTAINER_BINDPATH APPTAINER_BIND
unset PYTHONPATH PYTHONHOME LD_PRELOAD LD_AUDIT
exec singularity exec --cleanenv --bind "$root:$root" --pwd "$run" \
  --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,PYTHONHASHSEED=0,OMP_NUM_THREADS=1,OPENBLAS_NUM_THREADS=1,MKL_NUM_THREADS=1,NUMEXPR_NUM_THREADS=1,VECLIB_MAXIMUM_THREADS=1,BLIS_NUM_THREADS=1" \
  "$image" "$root/.venv-container/bin/python" -B "$run/research_v110/entry.py" "$@"
