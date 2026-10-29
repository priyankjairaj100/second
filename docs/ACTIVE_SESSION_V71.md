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

## Expanded installed notice preparation

While the existing quality chain runs, a bounded read-only observer inspected the
shared GPU Python installation without importing Torch, initializing CUDA, reading
model/data, installing packages or submitting a job. Snapshot A only searched
dist-info notice trees. Snapshot B additionally follows installed RECORD notice
entries; it recovers cuSPARSELt's notice and other installation-relative notices.
Both observations and the initial collector source remain preserved. This is
reporting work, not a numerical campaign or a historical runtime requalification.

The new staged reports/development-dependency-notices-v71.zip has99 members,
456767 bytes, SHA25645e860d785c7838ccc3945b3581d2f38b98791dea7baf812554ff1adf56d66ca.
It retains all five earlier CPU/publisher texts unchanged and adds35 CUDA/Python
notice/attribution texts with installed metadata. All28 distributions reachable
from Torch and NumPy through active installed Requires-Dist on Linux/x86_64/
Python3.10.19 without extras have a notice. All32 active version constraints pass;
the213 declared edges, including inactive extras, remain visible. All34 distribution
notice files match installed RECORD hashes; the Python license is separately
observed. The28-distribution graph was recomputed locally from raw METADATA, and
clean extraction, manifest and three missing/altered-file refusal checks pass.
Original upstream authorship is retained. Observer B's metadata-read window used
0.256759977 process CPU seconds. This excludes interpreter startup, imports and tar
serialization; it is neither the total observer cost nor an empirical worker debit.

Read validation/v71_expanded_dependency_notices.json. The raw snapshot B is
validation/v71_installed_cuda_notices_20261018_b.tar.gz,362296 bytes,
SHA2563a2714c8f9dca1bbb6c5c30aa093f00b305b3a440dae6910ed54284f01ba3219.
Exact current Torch/NumPy version strings match the admitted runtime record, but
this later notice observation does not retroactively bind frozen binaries or prove
source equivalence. It does not identify every dynamically loaded native library.
GPU-node driver/system/compiler/container notices, CPU GMP/MPFR/MPC attribution,
tokenizers Rust correspondence, and author-controlled project release terms remain.

This component is prepared for the next coherent bundle, not silently substituted
into the current six-component guide. The guide, existing bundle, manuscript and
all frozen sources remain byte-unchanged. On integration update its archive binding
and rerun the full component checks. No new quality result is available here.

## Latest running observation,18 October12:24:50UTC

Snapshot C confirms the same three completed and sealed phases,79 settled worker
CPU seconds, and sequential12 job15408 running with11/24 saved progress receipts.
All five successors remain dependency-pending. No likelihood result or terminal
quality decision exists. Read validation/v71_campaign_metadata_20261018_c.json
and campaigns/csis_v71_metadata_20261018_c.tar.gz. The active reservation and
registered ceilings are unchanged; no job was submitted or repeated.

## Integrated development bundle and selection metadata,18 October12:48:49UTC

Snapshot D confirms three completed/sealed phases,79 settled worker CPU seconds,
sequential12 job15408 running with15/24 saved stage-progress receipts and all five
successors dependency-pending. No quality likelihood or terminal decision exists.
Read validation/v71_campaign_metadata_20261018_d.json and its uniquely named raw
archive. No job was submitted, retried or changed. The numerical checkout remains
at f900999; all575 numerical/protocol and five administrative commitments match.

A bounded reporting-only collector captured the ten registered quality-metadata
roles and60 historical quality exclusions without reading model, article or token
bodies. The raw13-member archive is campaigns/csis_v71_selection_metadata_20261018_a.tar.gz,
6202754 bytes, SHA2560b538dc3d3ea3e161c63354593fbc379264ce06bc2d9c3bfd42c0f6349fbb863.
A separate metadata implementation reproduces every saved eligibility reason,
2778 eligible records, the fixed320-record sample and exact successor exclusion
union for all3801 inspected records, including1021 short records. Four semantic
mutation probes reject removed frame IDs, changed eligibility or short full-token
hashes, and reordered selections. This does not retokenize, re-read corpus/prefix,
or establish quality. Actual corpus-to-hash correspondence remains supported by
V68/V70's original saved-prefix audits using the shared tokenizer.

One local probe-preparation error assumed a record shorter than16 tokens, but the
actual minimum was16. The baseline metadata check had already passed. The error
and prior checker source hash are preserved; the corrected probe selects a short
record of nonstandard prefix length from the1007 available records. No registered
source, empirical attempt or data was changed. See
validation/v71_selection_probe_preparation_error.json and
validation/v71_selection_metadata_reconciliation.json.

The new development-selection-metadata-v71.zip contains15 members and eleven
metadata files. Ten are original bytes; one registration has reversible identifier
mapping. Eleven typed roundtrips and five checker-function AST comparisons pass.
The portable read-only checker and missing/changed/extra-file probes pass from
clean extraction. Private derivation details stay outside the anonymous component.
Historical hashes can remain indirectly linkable; full anonymity is not claimed.

The new development-reproduction-guide-v71b.zip binds six companion ZIPs and the
expanded installed notices. Its clean-extraction and altered/missing/extra-file
checks pass. Seven review components now contain721 members; including the same
paper and new navigation,723 text files pass manifests,16 evidence references,
six protocol links and known direct-identifier checks. A broad name scan matched
one legitimate upstream SymPy author, Priyank Patel, whose attribution is preserved.
This is not the project author's identity. Full indirect anonymity remains open.

The integrated local outputs/second-development-review-v71b.zip is8860660 bytes,
SHA2567e7693ccc17fb9461055db2b746e36cbd6a710099faf9572374545d71d2239e1.
Its ten members roundtrip exactly. Read reports/REVIEW_PACKAGE_README_V71B.txt,
validation/v71b_cross_component_review.json and validation/v71b_development_bundle.json.
Earlier component reports describe their creation-time staged state; this new
bundle is the explicit integration checkpoint. All older bundles/components and
existing manuscript bytes remain unchanged. No new native compilation is claimed
for this packaging-only change; the prior native success remains the last check.
No separate PDF or new editor tab was created. This is a DEVELOPMENT bundle, not
submission-ready. Actual quality/cost closure, justified timing decision, complete
historical inputs, remaining rights/notices, rendered layout, indirect anonymity
and author-controlled final details still remain.

## Citation and native-notice scope checkpoint,18 October13:02:55UTC

Snapshot E has sequential12 job15408 running with19/24 stage receipts. The first
three sealed workers remain completed,79 settled CPU seconds; all five successors
are dependency-pending. No untouched likelihood or terminal quality result exists.
Read validation/v71_campaign_metadata_20261018_e.json and the new raw archive.
The same single submission and all frozen sources/resources are preserved.

A current primary-source/deposited-metadata review now supports all seven
bibliographic identities. In particular, a bounded public Crossref API request
recovered IEEE's deposited Exact-Fun metadata, verifying author order, title,
ICDM2023 and pages1439--1444. Web-tool DOI/API requests failed and IEEE presented
a robot screen; those failures were not bypassed or treated as success. The normal
public metadata API request succeeded without fetching the publisher PDF. Its raw
response is preserved. The historical author-version proof comparison retains its
prior scope, without a fresh full-proof claim. All seven bibliography keys are
used, eight citation groups resolve, and eight reference uses match fourteen
unique labels. Read docs/CITATION_CHECK_V71.txt and its two validation records.

A separate bounded CPU installation observer recovered seven notices from four
distributions and declared29 native entries. The local checker matches56 RECORD
entry commitments to frozen pins and directly hashes four metadata files against
those pins; it does not re-read binary bodies or establish build/source identity.
Four earlier notice texts are unchanged. Three additional NumPy notices outside
the earlier distribution-only scan are preserved for the next bundle assembly.
Tokenizers still lacks an installed notice in the inspected RECORD; its existing
publisher-source license is retained with that limitation. Exact GMP/MPFR/MPC
source correspondence, Rust/native/system attribution and release terms remain.

The first observer stopped before archive output on zstandard RECORD's unhashed
self-entry. Its source/error/empty output are preserved. The revised reporting
observer only exempts that self-entry from the RECORD digest requirement and
instead verifies actual RECORD bytes against the frozen registration pin.
This was not a registered job or numerical gate, and no experiment was retried.
Read docs/CPU_NOTICE_SCOPE_V71.txt and
validation/v71_cpu_notice_inventory_reconciliation.json.

The V71B development bundle and existing open manuscript remain byte-unchanged.
The additional notices are not silently substituted into its manifest. One native
app inventory attempt again returned 'Sky Computer Use service startup request
failed'; no further UI attempt, replacement editor, new tab or separate PDF was
made. Actual page/layout review remains unverified. The next scientific action
is to audit the existing quality chain when its dependent phases finish.

## Additional notice integration,18 October2026

The next ready packaging task is complete. New development-dependency-notices-v71c.zip
adds all three observed NumPy notice texts, preserves96 earlier non-index payloads
byte-for-byte, and contains43 unchanged upstream notice/attribution texts in102
members. Source/version/path scope and RECORD commitments are included; no native
binary, source correspondence or full license-clearance claim is added. Clean
extraction, exact manifests and altered/missing-file refusals pass.

The new development-reproduction-guide-v71c.zip binds this archive and the same
five other companion ZIPs. Seven components now pass724-member/726-text-file
inventory, manifest,16 evidence-reference, six protocol-link and known-direct-
identifier checks. The prior213 source-fixture result is bound to unchanged source
bytes; it is not rerun or relabelled as numerical reproduction. Existing selection
metadata and both E16 actual-audit derivatives remain byte-identical. The new guide
passes clean extraction and corrupt/missing/extra-file refusal checks.

The integrated outputs/second-development-review-v71c.zip is8864723 bytes,
SHA2563eb894ccde54fa32ca47dc20f096224dd92dca1e2b12f1f879e1da66702f58c8.
All ten bundle members roundtrip exactly. Read reports/REVIEW_PACKAGE_README_V71C.txt,
validation/v71c_development_bundle.json and validation/v71c_cross_component_review.json.
The older V71/V71B bundles and all previous components are preserved. The existing
manuscript/source editor remains unchanged; no compilation, separate PDF or new
tab was needed for this packaging-only update.

At this checkpoint the latest sealed snapshot remains E,13:02:55UTC, with19/24
sequential12 stage receipts and no final quality result. A later read-only Slurm
check at13:08UTC still found15408 running and all five successors pending. No
job was launched or retried. Await the already submitted chain and actual seals
before interpreting quality. Full native/source attribution, historical input
reproduction, indirect anonymity, actual rendered pages and author-controlled final
facts remain open. This bundle remains DEVELOPMENT, not submission-ready.


## Sequential12 completion and saved-loss reporting preparation,18 October13:24UTC

Snapshot F verifies four completed original worker seals, including15408. Its
24-stage sequential construction reports an actual saved-code audit of42,467,328
codes; the worker debit is5392 CPU seconds and all settled worker charges total5471.
The original limits, controller/worker clocks and Slurm allocation reconcile.
Model/code bodies were not fetched or independently reconstructed locally. Job15409
was running with5/24 stage receipts;15410--15413 remain dependency-pending. No
untouched likelihood or quality decision exists. All jobs remain the single
original submission; the numerical checkout remains clean at f900999.

A supplementary reporting collector/checker is prepared to inspect the original
1944 saved scalar losses only after actual terminal and external closure success.
It recomputes standard-library pooled NLL, paired log ratios and observed maxima,
checks24 parity pairs and reported guard logic. It does not rerun bootstrap draws,
model construction or inference and does not alter the registered acceptance rule.
Two generated favorable/adverse examples and eleven refusal probes pass; actual
complete collection and its success path remain unexercised. Nothing was deployed
or executed on CSIS. Read docs/SAVED_LOSS_REPORTING_V71.txt.

The V71C bundle and existing manuscript are unchanged. Continue the existing chain
then make the evidence-based quality and timing decisions; full submission gates
remain open. No source, resource ceiling, one-use attempt or exclusion was changed.
