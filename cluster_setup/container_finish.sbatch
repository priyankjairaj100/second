#!/bin/bash
#SBATCH --job-name=second_container_finish
#SBATCH --partition=cpu-short
#SBATCH --qos=cpu-short
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:10:00

# Finish environment creation from an already verified image after a setup failure.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
manifest="${1:?Supply the existing image SHA256 file}"
image="$PWD/local_runs/cluster-setup-20261010/python-3.12.14-bookworm.sif"
sha256sum --check --status "$manifest"
test "$(wc -l < "$manifest")" -eq 1
test "$(cut -c67- "$manifest")" = "$image"
test ! -e .venv-container
module load singularity/4.4.0
unset SINGULARITY_BINDPATH SINGULARITY_BIND APPTAINER_BINDPATH APPTAINER_BIND
singularity exec --cleanenv --bind "$PWD:$PWD" --pwd "$PWD" "$image" /bin/bash -s <<'INNER'
set -euo pipefail
python -m venv .venv-container
.venv-container/bin/python -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: --require-hashes -r requirements-ci-v38.txt
.venv-container/bin/python -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: -r requirements-scale-v39.txt socksio==1.0.0
.venv-container/bin/python -m pip check
.venv-container/bin/python -m pip freeze > local_runs/cluster-setup-20261010/container-requirements-resolved.txt
INNER
bash cluster_setup/run_cpu.sbatch "$manifest" -m cluster_setup.cpu_check \
    "local_runs/cluster-setup-20261010/cpu-container-${SLURM_JOB_ID}"
bash cluster_setup/run_cpu.sbatch "$manifest" -m cluster_setup.final_check
