# Second V123: technical review fixes and measured saved-code changes

29 October 2026. The four requested technical edits are complete in the same open
manuscript: unresolved-only stopping, distinct box-center coefficients, actual
service fallback/refinement limits and codec step, and precise square-root
acceptance. Source inspection confirms rational fallback is disabled (rank and
exact-coordinate caps zero); numerical point refinement is capped at sixteen.
No frozen implementation, numerical limit or target was changed. Table 6 now
specifies the inherited generated tests and their actual scope.

Read docs/REVIEW_FOLLOWUP_V123.txt for the point-by-point response and
validation/v123_quality_input_readiness.json for the exact four model bindings.
The first new language-model experiment remains matched-target quality. It needs
a separately registered frame excluding every previously inspected calibration
and quality frame, qualified model loaders/references, and a finite compute plan.
No new quality or calibration execution has occurred; do not reuse old attempts.

Actual new evidence

Live SSH, Slurm and storage were reconciled. All four optimized-compressed saved
endpoint models and completion hashes were present. Unrelated First jobs were
left untouched. A separately registered read-only audit used fresh namespace
saved-code-audit-v123-20261029-a. Job 16651 completed 0:0 with 4 seconds elapsed,
3.658 scheduler CPU seconds and 3.610096228 worker CPU seconds (overlapping clocks).
The worker peak RSS was 160,480 KiB; short-interval scheduler MaxRSS 3,296 KiB is preserved.
Limits: 1 CPU, 16 GiB, 10 minutes wall, 300/301 CPU seconds. No job retry is permitted.

DistilGPT2 predecessor changes: 4,150,626 and 3,746,142 of 42,467,328 codes. GPT2: 8,993,197 and
8,080,117 of 84,934,656 codes. Thus 8.82--10.59% change per transition. All changed codes
are in stages certified without replay except 245,692 in the first GPT2 endpoint's
replayed final-block MLP up-projection. This is stage-level classification, not a
per-code necessity claim. Full stage/root-relative counts and input hashes are in
pilots/saved-code-audit-v123-20261029/result.json. This host-Python byte/integer audit
is not native numerical qualification, new quality, new roots or precision evidence.
Final remote/local source, manifest and result SHA256 agree. The completed job was
no longer in squeue; its terminal sacct receipt establishes closure.

Verification and delivery

The same final source compiles with the native editor. Independent Tectonic export
has ten content pages, one reference page, no appendices, unchanged official style
and no overfull boxes or unresolved references. Every final page was visually
inspected. All empirical table values and fifteen rendered reference destinations
pass. Reference claims/identities are unchanged from the V121/V122 primary audits.
All 1,322 frozen source/protocol counterparts and 14 historical scientific ZIPs match.

The 36-member author archive adds the new audit as flat files. Its unchanged
portable verifier checks supplied bytes and source coverage; it does not recompute
remote model results. Both inherited generated checkers reproduce their exact JSON
from extraction, and the new counter's 65,536-byte-pair/six-vector self-test passes.
The source ZIP has 8 members. This is not a clean external-input reproduction.

Downloads: Second-TACL-v123.pdf, Second-TACL-v123-Full-Evidence.zip,
Second-TACL-v123-Source.zip and Second-TACL-v123-PDF.zip (PDF only).
Same open source: outputs/second-research-draft.tex. Repository snapshots:
reports/manuscript_v123.tex and reports/second_tacl_v123.pdf.
Validation: v123_manuscript_checks.json, v123_packages.json, v123_delivery.json,
v123_native_compile.json, v123_changed_codes_audit.json and v123_reference_audit.json.

Ordered remaining work

1. Exact matched-target quality on both checkpoints and both retained endpoints.
2. Minimal source-only cold state, complete cost and source-access comparison.
3. Precision-success/margins/bound tightness, broader roots/sizes and trajectories.
4. Production verifier/abort checks, timing replication and clean reproduction.
5. Evidence-based final framing and author-owned release/submission declarations.

The detailed draft V122 evidence plan remains applicable with V123 input/counter
updates. No submission-readiness or general speedup claim is established. The old
V119 campaign remains closed. Preserve all failures, negative findings and one-use
attempts. Scheduler PAUSED; no restart, subagent, paid compute, new monitor,
third-party message or actual submission. No routine permission request is needed
for the next authorized preparation; enforce real source/resource gates.
