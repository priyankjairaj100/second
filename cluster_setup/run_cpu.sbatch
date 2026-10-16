#!/bin/bash
#SBATCH --job-name=second_cpu
#SBATCH --partition=cpu-short
#SBATCH --qos=cpu-short
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:10:00

# Example: sbatch cluster_setup/run_cpu.sbatch IMAGE_SHA256_FILE -m unittest MODULE
# Research jobs additionally need their own prospective registration and budgets.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
manifest="${1:?Supply the verified container SHA256 file}"
shift
test "$#" -gt 0
image="$PWD/local_runs/cluster-setup-20261010/python-3.12.14-bookworm.sif"
sha256sum --check --status "$manifest"
# Also ensure the manifest names the image used by this wrapper.
test "$(wc -l < "$manifest")" -eq 1
test "$(cut -c67- "$manifest")" = "$image"
module load singularity/4.4.0
unset SINGULARITY_BINDPATH SINGULARITY_BIND APPTAINER_BINDPATH APPTAINER_BIND
exec singularity exec --cleanenv --bind "$PWD:$PWD" --pwd "$PWD" \
    --env "SLURM_JOB_ID=${SLURM_JOB_ID},PYTHONDONTWRITEBYTECODE=1,OPENBLAS_NUM_THREADS=1,OMP_NUM_THREADS=1,MKL_NUM_THREADS=1,NUMEXPR_NUM_THREADS=1,TOKENIZERS_PARALLELISM=false" \
    "$image" .venv-container/bin/python -B "$@"
