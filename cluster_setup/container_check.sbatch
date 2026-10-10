#!/bin/bash
#SBATCH --job-name=second_container_setup
#SBATCH --partition=cpu-short
#SBATCH --qos=cpu-short
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module load singularity/4.4.0
# The inherited cluster value uses an invalid source:ro mount shorthand.
# Use the explicit repository bind below; do not change the user's login setup.
unset SINGULARITY_BINDPATH SINGULARITY_BIND APPTAINER_BINDPATH APPTAINER_BIND
export SINGULARITY_CACHEDIR="$PWD/local_runs/cluster-setup-20261010/container-cache"
export SINGULARITY_TMPDIR="$PWD/local_runs/cluster-setup-20261010/container-tmp"
mkdir -p "$SINGULARITY_CACHEDIR" "$SINGULARITY_TMPDIR"
image="$PWD/local_runs/cluster-setup-20261010/python-3.12.14-bookworm.sif"
if test -e "$image"; then
    echo 'Container output already exists; inspect it before another setup attempt.' >&2
    exit 2
fi
singularity pull "$image" docker://python:3.12.14-bookworm
sha256sum "$image" > "local_runs/cluster-setup-20261010/container-${SLURM_JOB_ID}.sha256"
singularity inspect --json "$image" > "local_runs/cluster-setup-20261010/container-${SLURM_JOB_ID}.json"
singularity exec --cleanenv --bind "$PWD:$PWD" --pwd "$PWD" "$image" /bin/bash -s <<'INNER'
set -euo pipefail
unset PYTHONPATH LD_PRELOAD LD_AUDIT
python -m venv .venv-container
.venv-container/bin/python -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: --require-hashes -r requirements-ci-v38.txt
.venv-container/bin/python -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: -r requirements-scale-v39.txt socksio==1.0.0
.venv-container/bin/python -m pip check
.venv-container/bin/python -m pip freeze > local_runs/cluster-setup-20261010/container-requirements-resolved.txt
INNER
singularity exec --cleanenv --bind "$PWD:$PWD" --pwd "$PWD" \
    --env "SLURM_JOB_ID=${SLURM_JOB_ID},PYTHONDONTWRITEBYTECODE=1,OPENBLAS_NUM_THREADS=1,OMP_NUM_THREADS=1,MKL_NUM_THREADS=1,NUMEXPR_NUM_THREADS=1,TOKENIZERS_PARALLELISM=false" \
    "$image" .venv-container/bin/python -B -m cluster_setup.cpu_check \
    "local_runs/cluster-setup-20261010/cpu-container-${SLURM_JOB_ID}"
