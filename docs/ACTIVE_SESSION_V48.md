# Active session V48: local audit complete; cluster outcome unavailable

Updated 11 October 2026. This supersedes the execution-status statements in V47 and older snapshots. Continue from the GitHub/ChatGPT handoff on `codex/second-cluster-v42`, in `/Users/priyankjairaj/Downloads/ACL/Second`. The old `Two` and `acl2027-second` folders are excluded.

## Current blocker

One SSH connection to `172.24.16.132:22` timed out before login on 11 October. No password was submitted and no remote command ran. The user explicitly confirmed cluster access is unavailable. Stop connection attempts until access is restored. No jobs were resubmitted, cancelled or changed; no scheduled monitor was created.

The V45 terminal outcome is **unknown**. On 10 October, preparation was last observed running and its dependent workers/audits were pending. That historical observation is not a current scheduler state. Missing connectivity does not establish that the jobs stopped, completed or failed. There are no local V45 final receipts or actual model artifacts to validate.

The last confirmed cluster checkout commit is `996eec3e9c5fff3f2a1367e1dc88f7ea35bdf58b`. Subsequent V48 local/GitHub changes have not been synchronized to the cluster. Inspect its status before any later synchronization. All frozen numerical sources and historical evidence remain unchanged.

## Completed offline work

`research_v48.report` checks copied evidence and cost arithmetic without inference or ledger changes. Ten tests pass. It was exercised against the historical complete V43 binary archive: all 138 bound inputs rehashed, six sealed workers and settled debits checked, and all eight recorded model/state comparisons validated. The metadata-only mode also passed while explicitly listing absent binaries. Strict binary mode refuses that incomplete copy.

Read `research_v48/README.md`, `validation/v48_v43_full_archive.json`, `validation/v48_v43_metadata_only.json` and `validation/v48_offline_checks.json`. This is an additional local integrity check, not a new experiment or independent numerical reproduction. The successful V43 campaign charged 1,720 CPU seconds; its preceding failure charged 24, giving 1,744 within the recorded continuation scope. The observed compression/cache latency ratios remain 1.7896 and 1.6034; deployment savings remain 0.9051% and 0.4624%. No losing comparison was removed.

V47 GPU likelihood validation remains verified: all 32 comparisons on four actual V44 models and eight exposed articles passed the frozen 1e-8 mean-NLL tolerance, with maximum deviation 1.2084821332612728e-14. All 150 parameter transfers preserve binary64 words. The successful export and GPU phases charged 19 and 22 CPU seconds; the failed predecessor charged 22. The 964,501,350-byte array archive remains on the cluster. No new quality article was used and exact calibration remains on CPU. Read `docs/GPU_LIKELIHOOD_VALIDATION_V47.md`.

## Frozen V45 experiment to retrieve

Numerical source: `8550dc0`. Program SHA-256: `02c7f6cfc0240bc34f2a5faec05dfb5392b81d12e5ac4cd95279167ef99c6d50`. Remote directory: `/nfs_home/users/poonam/second-20261010/local_runs/c4-full-model-v45-20261010-a`.

The full 24-stage, 42,467,328-code experiment uses 13 C4 documents and a 1,664 -> 1,536 -> 768 token sequence. It has one disjoint development root and a fixed method order, without randomized replication. Jobs are 13228 preparation, 13229 hybrid, 13230 cached, 13231 cold, 13232 compressed, 13233 fresh retained-input oracle, 13234 primary audit and 13235 supplemental audit. Dependencies require successful predecessors; automatic retries are disabled. The model CPU ceiling is 26,412 seconds, with one thread/CPU and 16 GiB per worker. A ceiling is not a duration estimate.

The separate C4 data-selection phase completed and charged 15 CPU seconds. Its program is `4bd64a67eb44151d09d3552231630ab41a937e17e2709b662e93fc542fa994f0`; records hash `1b3dd813dc5deacb35974e28f1fbd47d14364b85202a7ad12c8c1e7fc6a53259`; selection hash `d3c31bb483b6b77587c372b7611ee21d7ac706fcfbb363dbbb0b6b812754bdb9`. Exact ID/content/token-prefix exclusions do not establish semantic decontamination or a probability sample.

After connectivity is restored, collect scheduler accounting for the original eight jobs first. Follow the read-only collection and reporting procedure in `research_v48/README.md`. Require all six sealed worker outcomes, settled ledgers, both original audits and actual bound evidence before promoting the larger-model result. Preserve any failed/cancelled jobs and partial outputs. Do not rerun attempted workers, reset reservations, change caps or touch SANW/First2 jobs. Numerical work belongs on Slurm in the pinned CPU runtime, not on the Mac or login node.

## Manuscript and scientific completion

The open `outputs/second-research-draft.tex` in the Codex workspace remains the editable master. `reports/manuscript_v48.tex` is its repository snapshot. This update dates the draft 11 October and marks V45's outcome unavailable. It preserves the verified historical findings and their limitations. Built-in compilation status is recorded in `handoff/program_v48.json`; visual layout remains unverified. No new editor tab or separate PDF is required.

The research paper is **not complete or ACL-ready**. Next comes the actual V45 outcome and quality of its resulting model; V44's normalization-96 quality does not transfer automatically to normalization 1,664. The remaining scientific obligations are an actual second checkpoint, strong lossless-codec controls, certificate/replay ablations, repeated randomized roots and deletion sequences, untouched article-level evaluation with predeclared endpoints, and a defensible novelty contribution. A poor V45 outcome must guide revision rather than be relabeled a win.

Preserve all 60 historical quality exclusions and failed attempts. The target is fixed-anchor calibration membership, not pretraining unlearning, ordinary sequential GPTQ repair or physical erasure. Local execution provides persistent files and institutional compute; it does not eliminate assistant token use. No credential is stored in the repository or output package.
