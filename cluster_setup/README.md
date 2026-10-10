# Current local and cluster environment: V44

Use `docs/ACTIVE_SESSION_V44.md` and `handoff/program_v44.json` for current results and restart instructions. The original V42 setup notes below retain their historical cutoff; the complete V43 service now exists and its tiny two-deletion pilot passed.

The fresh Mac checkout is `/Users/priyankjairaj/Downloads/ACL/Second`. The cluster checkout is `/nfs_home/users/poonam/second-20261010`, reached as `poonam` at `172.24.16.132`. Passwords are entered interactively and are never stored in this repository. Do not use either old `Two` or `acl2027-second` checkout as the continuation source.

Exact CPU experiments use the verified Bookworm Singularity image, CPython 3.12.14, NumPy 2.3.5, and gmpy2 2.3.2. The pinned `gelu_new` quality evaluator uses NumPy tanh; SciPy is absent and this fact is bound in V44 runtime registration. Job 13149 verified one A100 80GB PCIe through PyTorch 2.10.0+cu128 with a synthetic batch. Exact quantization remains on CPU; GPU quality needs a prospective CPU/GPU parity check before use.

Submit through Slurm on `csis.mn1`; the earlier `cn1` user-resolution failure remains recorded. Confirm current account resources before a new allocation. A bounded software-check example (no model inference):

```bash
sbatch --no-requeue --nodelist=csis.mn1 --mem=16G --time=00:10:00 \
  --output=local_runs/cluster-setup-20261010/software-%j.log \
  cluster_setup/run_cpu.sbatch \
  local_runs/cluster-setup-20261010/container-13155.sha256 \
  -m unittest research_v43_postrun.test_audit research_v44.test_diagnostic
```

The wrapper defaults to 8 GiB and ten minutes; those defaults are not an empirical admission. Every new empirical campaign needs its own reviewed target, runtime binding, CPU/memory ceilings, fresh path, and one-use ledger. Do not rerun completed V43 or V44 registrations. An SSH authentication failure/refusal requires attention rather than repeated retries.

## Historical setup-only notes

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


## Validated GPU likelihood path, V47

The A100 evaluator now passes all 32 already exposed V44 likelihood comparisons at a frozen absolute mean-NLL tolerance of 1e-8. Exact calibration remains in the pinned CPU container. See `../docs/GPU_LIKELIHOOD_VALIDATION_V47.md`.

The CPU snapshot export avoids constructing the certified CPU decoder in the incompatible shared GPU runtime. Its 964.5 MB parameter archive remains under `local_runs/cpu-parameters-v47-20261010-a/outputs/` on the cluster. Both the export and successful GPU parity ledgers are settled; do not rerun those one-use directories. Future evaluations require a fresh registration and preserved exclusions.

The larger V45 CPU experiment is independently active. See `../docs/ACTIVE_SESSION_V47.md` for job IDs and frozen source boundaries.
