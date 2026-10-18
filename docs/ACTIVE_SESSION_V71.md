# Second active handoff: V71, 18 October 2026

Read this handoff and CONTINUOUS_RESEARCH_QUEUE.md first. Historical V69/V68/V67
handoffs and all original registrations, failures and archives remain preserved.
This is a reporting checkpoint, not a new result merely because a job was launched.

## Current execution

Access is restored. The numerical checkout remains clean at
f900999fcb200509dfad4fc081ce9c87fd172a16. Never pull reporting commits there.
Repository: priyankjairaj100/second, branch codex/second-cluster-v42, draft PR1.
Root: /nfs_home/users/poonam/second-20261010.
Local repository: /Users/priyankjairaj/Downloads/ACL/Second.
Reuse the existing SSH master if alive; credentials are never stored. Stop repeated
attempts on transport failure and inspect jobs before any later launch.

At 11:51:36 UTC, V71 CPU checks15405, CUDA checks15406 and parameters15407 were
COMPLETED0:0. Sequential12 job15408 was RUNNING166 seconds; sequential6 15409,
CPU parity15410, GPU quality15411, terminal15412 and closure15413 were dependency
pending. They were each submitted exactly once, all held/bound/verified before
release. Do not rerun submission.py or any entry/worker. The existing chain advances
without further laptop commands. No untouched-quality conclusion is available.

Actual receipts show103 Linux tests with zero failures/errors/skips,24 generated
CPU/CUDA comparisons within the1e-8 mean-NLL threshold, and all78 checkpoint
parameter arrays equal to the original saved export. CUDA qualification uses tiny
generated data and is not checkpoint quality. The parameter audit actually loaded
the pinned checkpoint on the cluster; local review checks receipt commitments only.
The three settled workers charge30,12,37 CPU seconds respectively. The first
sequential worker reserves14402; a reservation is not an observed debit.

Registration: handoff/registration_v71_quality.json, SHA256
3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c.
Remote run: local_runs/untouched-quality-v71-20261018-a.
Total ceiling44726 CPU seconds:39616 workers,4808 controllers,302 closure.
Sequential workers each have14400 soft CPU seconds. CPU host csis.mn1; CUDA host
csis.cn4 with one A100,16GiB physical reservation and8GiB allocator ceiling.
CUDA virtual address reservation128TiB does not imply physical allocation.
These are limits, not an ETA. All40 V71 sources are frozen. There are575 distinct
registered numerical/protocol sources across current and failed histories, plus
five separately checked administrative sources; current V71 imports532.

Snapshot: campaigns/csis_v71_metadata_20261018_a.tar.gz,125 files,160969 bytes,
SHA256 de1364ba5aa891abfc686294865560c4dc4d9e1319cc297862424cf879d2ca2b.
validation/v71_active_reconciliation_20261018_a.json checks completed receipt,
output hash, registration, job and ledger metadata. It does not contain all worker
seal artifacts or model binaries and is not an independent numerical audit.

## Newly closed scientific evidence

V67 jobs15261--15275 all completed0:0. The two actual cluster terminal audits
finished17 October00:10:59 and00:11:17 UTC and were recovered18 October. All ten
five-arm/two-endpoint full model/state comparisons equal fresh reconstruction.
The portable reconciliation verifies their commitments and cost graph; it does
not repeat numerical reconstruction locally. Read docs/TERMINAL_EVIDENCE_V71.txt.

At12 and6 retained records, compression saves9.38% and8.83% live state relative
to cached lossless, with17.82% and46.46% slower requests. Against modern lossless
it saves9.24% and8.70%, with13.69% and50.48% slower requests. Including the common
checkpoint reduces modern-relative savings to4.71% and3.10%. Modern's codec adds
23870575 installed bytes. Hybrid is smaller and faster at the first endpoint,
but reads retained sources; compression is smaller and faster than hybrid at the
second endpoint while both caches are faster. Internal compression fallback rows
68/2 remain explicit and distinct from zero stage-level replay/refusal.

The scientific decision is a scoped storage/source-access/latency tradeoff, not a
speed win. Keep the original5.92% nearest-anchor quality failure and the adaptive
full-precision-teacher history. This one fixed-order trajectory provides no timing
confidence interval, broad reliability or untouched quality. Continue the already
planned disjoint quality evaluation without changing the target, thresholds or
sample to improve the outcome. Timing replication depends on the intended claim.

V68 data jobs15390--15392 completed0:0. One bounded8MiB compressed range and8MiB
expanded prefix yielded3801 complete articles,2778 eligible and320 selected.
The entire3801-record inspected frame is reserved, as are the previous60 quality
IDs and2349-record calibration frame. Actual cluster saved-prefix retokenization
passed. No full gzip-trailer or whole-source byte validation is claimed.
Combined process CPU24.675861322 seconds, rounded charges26, scheduler26.362;
these overlap. Registration ddcf2b686ff0ed4c4401a4defa361bcd956a32d3697dbe1b71485744c513b3cb
is preserved along with the nine frozen sources. Names dated20261016 were prepared
then; registration and execution actually occurred18 October.

## Failed admission and separately registered correction

V69 quality job15395 failed before its first worker, with 'Entire inspected frame
must remain excluded'. Its eight dependents15396--15403 were cancelled without
allocation. Preserve the source40, registration d176bb08cea9c7ef0ded9294d75f47234c5b93f772cddf9c84b0908cbfdd43f1,
failed controller receipt and2.007 scheduler CPU seconds. No likelihoods or model
construction ran in this failed campaign. No registered job was retried.

The legacy exclusion store includes each nonempty complete token sequence in
addition to standard16/32/64/128 prefixes. V69 reconstructed only the standard
prefixes, omitting1007 distinct hashes contributed by1021 short records. Content
and article-ID sets already matched. We did not weaken exact equality to a subset.

V70 job15404 separately retokenized the same saved prefix with the same tokenizer,
repeated the saved-data audit and bound all3801 complete-token hashes. Exact
exclusion equality passed. No new data, changed selections or model inference.
Registration1120b96623394d9a4bf4314b6167b824b350a5665f4a446f781edbc67ef7bf84;
process+children10.045330793 seconds, rounded11; scheduler10.631. Three new
numerical files and one administrative launcher are frozen. This audit uses the
same tokenizer implementation; it is not independent algorithmic validation.

V71 binds the actual V70 receipt/job/scheduler and all ordered full-token hashes,
retaining exact union equality, the same320 selected articles, V67 candidates,
V55 sequential constructor, practical guards and resource caps. It is a new
corrected registration and namespace, not a retry. Its97 local fixtures preceded
registration; the subsequent103 Linux checks include six unchanged V55 fixtures.

CUDA observer15394 completed0:0 on csis.cn4, with no CUDA initialization/model/
quality-data access. Its original held-job launcher stopped on Slurm's literal
NumNodes=1-1 representation. A separately recorded administrative release verified
and released that same held job once. No second observer was submitted. Runtime
receipt SHA d17aec042160d38d8b683462eb05f27e735c1935526f71a53410d912671b1901;
Python3.10.19,NumPy2.2.6,Torch2.10.0+cu128,driver570.158.01. Runtime capture is not
CUDA qualification; actual generated qualification is job15406.

Before V69 registration only its submission.py,test_submission.py and PROTOCOL.txt
were changed to admit observed Slurm1/1-1 node spelling and generic GPU ReqTRES
with exact typed-A100 TresPerNode. KillOInInvalidDependent=Yes remained required.
All40 source bytes now match the actual V69 registration. Local Python3.9 test
errors, an intermediate fixture failure and earlier preflight schema errors remain
in validation logs; they are not actual scientific outcomes. Frozen-source checker
initially assumed digest objects for the runtime observer, whose schema stores
strings; this reporting-only mismatch was corrected after equal hashes were seen.

## Paper and artifacts

The existing open outputs/second-research-draft.tex was updated in place; its
reporting mirror is reports/manuscript_v70.tex. It now reports the closed disjoint
service, the strongest modern control and the unchanged adverse history. Its
native compiler succeeds;81 selected numeric checks and four tamper probes pass.
Proofs and the older eight-row service table are preserved. Current SHA256:
65d02e6048156fc1d2270368d8fa7efae192511f79e5aa9d00fc3820a772db0a.
No replacement editor or separate PDF was created. Actual pagination/rendered
layout remain unverified; the working-draft status and quality uncertainty remain.

A sixth companion, reports/development-service-evidence-v70.zip, adds E16: both
actual disjoint-service audit derivatives and all ten comparisons/costs. Five files,
124857 bytes; SHA256684ca47fd16985c32f5faf0dd7bab81f3bbe9dda297a87455dfb84c0a0ce2dc4.
Three typed roundtrips and two dropped-field probes pass; known direct identities
are mapped. Full indirect anonymity and reproduction are not established.
The private derivation map stays OUTSIDE anonymous review packaging. The original
five components remain byte-unchanged; the older source component predates the
three V69 submission fixes and V70/V71 sources and is not the final executable
source package. Read reports/REVIEW_PACKAGE_README_V71.txt.

## Next actions, in order

1. Reconcile jobs15405--15413 and actual files before acting. Preserve every attempt.
2. Let sequential12/6, CPU reference, GPU evaluation and both terminal/cost gates
   run. Collect full seals and actual loss/audit receipts after completion; check
   the closure's own final Slurm allocation externally. No quality claim from tests.
3. Use the frozen decision rule even for negative quality; do not resample or change
   guards. Any execution defect needs a separate documented registration.
4. While jobs run, complete current-source packaging, input/receipt navigation,
   notice inventory, manuscript consistency and terminal reporting preparation.
5. Decide timing replication only with a justified claim and separate prospective
   registration. No automatic larger model/transfer or favorable-root sweep.
6. Finish actual page/layout, anonymity, licensing, author facts and final clean
   package. The requested long/short format preference is still unanswered.

The same15-minute heartbeat remains active; no new monitor/delegation is authorized.
No paid compute, third-party messages or conference submission. Root review is not
independent peer review. The paper and submission bundle are not complete.

## Current-source package update

A new development-source-review-v71.zip now contains577 source/protocol/helper
copies plus README, checker and manifest. All original source commitments match;
45 copies have reversible identifier replacements and541 Python ASTs preserve
all other structure/constants. Clean extraction passed213 generated local tests
with zero failures/errors/skips,192 project modules and three namespace packages
loaded solely from extraction. CPU62.552978 seconds; no denied audit events.
This is not new Linux/CUDA qualification or empirical reproduction. The expected
refusal fixtures emit intentional tracebacks. The old v69c source ZIP is preserved.

A new development-reproduction-guide-v71.zip binds all five companion ZIPs, all ten
quality-input groups and observed CUDA/runtime commitments, under mapped paths.
Its six files pass clean extraction and corruption/missing/extra-file refusal
checks. No external input was acquired. The six current components total615
archive members; with paper/navigation,617 text files pass manifest,16 evidence
reference, six protocol-link and known direct-identity checks. Full historical
input-body closure, transitive notices and indirect anonymity remain unverified.

The E16 ZIP uses ordinary byte members with permissions but no explicit Unix file
type, which first triggered a reporting-checker assertion. The checker now accepts
regular or unspecified regular byte members while rejecting links/devices/dirs.
No receipt, archive, experiment source or empirical gate was changed by that fix.

See validation/v71_cross_component_review.json, validation/v71_review_source_fixtures.json
and validation/v71_reproduction_guide_check.json. Use the V71 navigation page;
the old source/guide are historical components, not the current reading order.

## Latest sealed-worker checkpoint,18 October12:07:00UTC

Sequential12 job15408 remains running with7/24 saved stage-progress receipts; the
first three jobs remain complete and15409--15413 dependency-pending. Snapshot B
includes all six sealed artifacts and terminal status for each completed worker.
The portable checker now reads actual limits/command/seal files, verifies exact
settled ledger charges and reconciles controller/child clocks to terminal scheduler
rows. All three pass; total settled numerical debits79 seconds. The14402-second
sequential reservation remains live, not a measured charge. No quality conclusion.

Read validation/v71_campaign_metadata_20261018_b.json and campaigns/csis_v71_metadata_20261018_b.tar.gz.
The updated reporting-only collector also knows the actual closure/receipt.json and
scheduler.txt paths, includes bounded sequential progress, and keeps model/token
binaries out. The numerical registration and575 sources are unchanged.

Seven reporting probes reject missing/changed sealed artifacts, underreported
scheduler costs, wrong registration, unsettled debit and false terminal completion;
a fake positive closure while jobs run stays pending. This exercises the actual
partial path, NOT the complete terminal success path. That path still requires
actual completed receipts. See validation/v71_reporting_refusal_probes.json.

On actual completion collect a fresh uniquely named snapshot with
validation/collect_v71_metadata.py, then run the read-only
validation.check_v71_campaign_metadata module with archive and NEW output names.
It requires eight completed seals, ledger/cost equality,1920 actual loss-file and24
CPU-reference comparisons reported by the cluster audit, and the closure's own
terminal allocation. Report negative quality as completed evidence. Do not relaunch.
The observer does not independently reconstruct omitted model/loss bodies; keep
that limitation explicit. Active/failed snapshots cannot become terminal success.

The existing manuscript still compiles but preview inspection failed once with
'Sky Computer Use service startup request failed'. No further preview retry or new
tab/PDF was attempted. Actual page count/layout remain unverified. The prepared
local second-development-review-v71.zip is a checked DEVELOPMENT bundle, not a
final submission; the existing source remains open and unchanged by this update.
