#!/bin/bash
# All resource requests are explicit in the registered held-job launcher.
set -euo pipefail
root=/nfs_home/users/poonam/second-20261010
run="$root/local_runs/untouched-quality-v69-20261016-a"
test "$#" -eq 2
phase="$1"
registration="$2"
[[ "$registration" =~ ^[0-9a-f]{64}$ ]]
case "$phase" in
  cpu_checks|parameters|sequential_12|sequential_6|cpu_parity|terminal) entry=entry.py ;;
  closure) entry=closure.py ;;
  *) exit 2 ;;
esac
test -n "${SLURM_JOB_ID:?}"
cd "$root"
manifest="$root/local_runs/cluster-setup-20261010/container-13155.sha256"
image="$root/local_runs/cluster-setup-20261010/python-3.12.14-bookworm.sif"
test "$(sha256sum "$manifest" | cut -d ' ' -f1)" = 5a58e1fef1950aabf16cea4f44043b95a1f18d572a67d42dccac4b4b6d96d0b3
test "$(cat "$manifest")" = "10ffb205f553197e110472e208522d0c73bcaf62e1a0571b860bf7bae49933b1  $image"
sha256sum --check --status "$manifest"
module load singularity/4.4.0
unset SINGULARITY_BINDPATH SINGULARITY_BIND APPTAINER_BINDPATH APPTAINER_BIND
unset PYTHONPATH PYTHONHOME LD_PRELOAD LD_AUDIT
args=("$registration")
if test "$phase" != closure; then args=("$phase" "$registration"); fi
exec singularity exec --cleanenv --bind "$root:$root" --pwd "$root" \
  --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,PYTHONHASHSEED=0,OMP_NUM_THREADS=1,OPENBLAS_NUM_THREADS=1,MKL_NUM_THREADS=1,NUMEXPR_NUM_THREADS=1,VECLIB_MAXIMUM_THREADS=1,BLIS_NUM_THREADS=1,RAYON_NUM_THREADS=1,TOKENIZERS_PARALLELISM=false" \
  "$image" "$root/.venv-container/bin/python" -B "$run/research_v69/$entry" "${args[@]}"
