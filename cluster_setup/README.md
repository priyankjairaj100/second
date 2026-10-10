# Local and Slurm setup

Continue from `docs/ACTIVE_SESSION_V41.md` and `handoff/program_v41.json`.
These setup tools do not execute historical campaign controllers or change their ledgers.
The `research_v42` planner is a prospective software check, not a complete repair service.

## Local editing

Use an independent Python 3.12 environment and the current checkout's dependencies:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-local.txt
.venv/bin/python -B -m unittest research_v42.test_resource_plan
```

The Mac supports editing and selected software fixtures. It does not satisfy the Linux numerical contract.
Never substitute another checkout's uncommitted implementation or reuse historical runtime identities.

## Cluster setup

Submit from the repository root. Check current account-wide resources before each submission.
The scripts request small Slurm allocations; none performs research inference or modifies historical evidence.
They write fresh directories under the ignored `local_runs/cluster-setup-20261010/` tree.
Create that parent directory before submission.

The CPU tools need Linux, pinned NumPy and gmpy2, a C compiler, and the recorded floating-point environment.
The native Rocky environment can fail the historical library-name checks after resolving versioned glibc filenames.
Preserve that failure. Do not change numerical code, counterfeit runtime evidence, or loosen checks to hide it.

`container_check.sbatch` uses the installed Singularity module to prepare an official Python 3.12.14 Bookworm image.
It creates an independent `.venv-container`, installs hash-pinned numerical wheels, captures a SIF SHA-256,
and runs the unchanged numerical environment checks and focused software suites.
The image provides a compatible userland. Its runtime identity remains distinct from historical GitHub runners.
The script refuses to overwrite an existing image; inspect existing evidence before a new setup attempt.

```bash
sbatch --output=local_runs/cluster-setup-20261010/container-%j.log cluster_setup/container_check.sbatch
```

After successful setup, use the matching `container-JOB_ID.sha256` with the reusable wrapper.
It verifies the exact image and uses a clean container environment, the current repository bind,
and single-threaded numerical libraries. It does not use GPU library injection.

```bash
sbatch --output=local_runs/cluster-setup-20261010/check-%j.log \
  cluster_setup/run_cpu.sbatch local_runs/cluster-setup-20261010/container-JOB_ID.sha256 \
  -m unittest research_v42.test_resource_plan
```

`gpu_smoke.sbatch` checks one allocated A100 using the existing cluster PyTorch module.
It uses a tiny synthetic batch. Success proves CUDA access only; it does not establish equivalence with the exact CPU target.
The GPU environment is separate from the pinned CPU environment.

`assets.sbatch` restores only the pinned DistilGPT2 checkpoint, tokenizer, and WikiText training parquet.
It verifies expected hashes and byte counts without model inference or historical output reconstruction.

## Scientific admission

Setup success does not admit a full-model experiment.
Generate a fresh resource plan with:

```bash
.venv/bin/python -B -m research_v42.resource_plan --output local_runs/NEW-resource-plan.json
```

The planner includes complete token row/refinement costs and reports all 24 stages.
It preserves original normalization, target identities, and existing limits.
All complete requests remain refused until service residency, source access, fallback,
canonical successor-state verification, and a fresh empirical registration are reviewed.

Preserve all sixty historical quality exclusions. Reacquiring the same evaluation articles does not make them untouched.
Keep full logs on disk and use compact summaries in chat. No credentials belong in code or evidence publications.
