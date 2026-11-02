# One new full-precision-anchor screen prepared; Linux gate pending

Updated 14 October 2026. Continue from this file and `handoff/program_v59.json`.
V59 is an additive source/protocol preparation checkpoint. **No V59 numerical
experiment has been registered, submitted, or executed.** The V54/V55/V56
results and their adverse findings remain frozen; see `docs/ACTIVE_SESSION_V58.md`.

## Decision and implementation

Investigate one concrete target change on the exact root that failed V55's
quality guard: replace the fixed nearest-rounded feature teacher with the
original full-precision checkpoint teacher. Calibrated output weights never
feed later candidate features. This preserves source-local features while
changing the calibration target explicitly. Full-precision anchoring is not
claimed as novel, and may still fail to calibrate the deployed quantized model.

The source audit found no concrete mismatch in the prior normalization, grids,
ridge, finite kernel, or model installation. Copied sealed metadata gives the
same first-QKV packed digest for the fixed and sequential models, with different
digests at every later stage. This is consistent with their different predecessor
feature rules. It is not a local reinspection of the uncopied model binaries or
proof that the new candidate will improve quality.

Historical V23/V29 plans proposed full-precision fixed-anchor controls, but no
completed calibrated four-bit instance was found. Earlier successful nearest-
anchor configurations and the unquantized quality control do not answer this
question. Do not return to an easier historical root or replace the comparator.

`research_v59/PROTOCOL.txt` declares one complete 24-stage candidate on the same
six retained C4 records (768 tokens), original normalization 1664, checkpoint,
four-bit dyadic24 grids, ridge, order and ties. It reuses the actual V55 sequential
model and V54 fixed model as controls. All 32 previous losses must reproduce
within 1e-8 before candidate construction. Candidate quality uses the same eight
exposed articles and unchanged 1.05 pooled / 1.20 every-article limits. All sixty
historical exclusions persist. An adverse result is retained without retry.

The implementation adds a new target identity, an immutable original-weight
feature stream, admission before all feature work, a one-use worker and CPU
ledger, and a read-only packed-code/loss/receipt auditor. It constructs a model
only; it does not implement or validate a full-precision-anchor repair service.
Historical numerical sources and state validators are unchanged.

## Checks and resource boundary

Static review checked the inherited bindings against copied V55 metadata and
reviewed the teacher-weight/data lifecycle. A dependency-order bug found during
review was fixed: target dependencies are canonically sorted, so the prefix
check now compares cardinality and membership. The complete software suite
still must run on pinned Linux; syntax and static review do not replace it.

The prospective worker has one constructor, 144 teacher stage-record advances,
and 40 serial article evaluations. It releases each expanded control prefix
before the next model and before calibration. It uses newly computed admission
reports and a separate 14,402 CPU-second phase cap, with soft CPU 14,400 seconds,
wall 18,000 seconds, 16 GiB process/Slurm memory and one CPU/thread. These are
abort ceilings, not an ETA, transferred historical budget, or fit guarantee.
No GPU allocation is needed for this CPU finite-arithmetic screen.

## Access and safe continuation

One bounded password-only SSH connection was attempted on 14 October. The
server returned `Permission denied (publickey,password,keyboard-interactive)`
before a password prompt. No password was submitted and no remote command or
submission ran. Access attempts stopped. Current cluster state was not refreshed.
The last verified cluster commit remains the **13 October observation**:
`0da0e5f64aa7fbfd9d09488415d58cb036aa022c`. Do not present it as today's live state.

After access is restored:

1. Read this protocol and inspect cluster Git status/HEAD, the existing jobs,
   runtime manifest and both old campaign roots before any mutation. Do not
   duplicate a launcher, software job or partially submitted chain.
2. Review the V59 source and static-check receipt. Synchronize this committed
   branch by a clean fast-forward only. Preserve unrelated cluster work.
3. Inspect the fresh paths named in `cluster_setup/v59_pipeline.sh`. The one-use
   chain runs software checks, registration, quality, then audit under `afterok`
   dependencies. The registration verifies the full pinned runtime, source and
   input bindings; no candidate numerical work can precede passing fixtures.
4. A fixture or execution failure requires inspection and a newly declared
   continuation. Never rerun that launcher or reset a ledger. A quality guard
   failure is a valid result and its auditor still runs.
5. Retrieve the actual receipt/artifacts and account for software, registration
   and audit allocations separately. Do not infer scientific success from Slurm
   completion or from the software gate.

The proposed paths are `local_runs/continuation-v59-20261014-a`,
`local_runs/full-precision-anchor-v59-20261014-a`, and
`local_runs/v59-software-a.json`. These are reserved names in source, not evidence
that remote directories or jobs exist. No scheduler IDs are available for V59.

If the quality screen passes, a separately registered complete-state service
comparison against cached, cold and hybrid controls is still required. V54's
modest storage savings and slower cached comparison do not transfer to the new
target. Independent roots/checkpoints, untouched quality, repeated costs and a
defensible submission contribution remain unresolved. **The paper is not ready
for ACL submission.** The open manuscript and its V58 snapshot retain verified
results; no speculative V59 numbers or favorable conclusions were inserted.

The SANW2 semantic-negative-weighting reviews concern another manuscript.
They have not been applied to Second.
