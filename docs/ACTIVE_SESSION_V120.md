# Second V120: TACL rewrite and rendered artifacts complete

28 October 2026. The active task is the user's final TACL rewrite. Scientific work
remains closed at V119; no new cluster call, experiment, audit, collector, registration
or source change occurred. Read docs/TACL_STORY_AND_REWRITE_V120.txt and
TACL_SUBMISSION_CHECKLIST_V120.txt for the writing decision and venue rules.

The same open outputs/second-research-draft.tex now uses the unmodified official
TACL submission style. The central story is exact discrete model recovery from
lossy calibration evidence, with storage/source-access/latency choices. The first
two pages explain the problem and a changed-code toy example. All core proofs,
coefficient derivations and decision-margin reasoning are in the main paper.
All empirical claims, fixed targets, quality populations, adverse comparisons and
failure records retain their scope. Three citations were updated to published
versions. The AI-use disclosure remains, without identifying acknowledgments.

The explicit no-appendices instruction governs the default; an optional clarification
was sent because the user's same message also discussed appendices. No answer was
received before the rewrite. TACL permits restricted, unreviewed appendix material,
but the current document has none. It also prohibits external review supplements;
the evidence archive is author-side and must not be uploaded or linked for review.

Verification
- Native compiler succeeds on the final source.
- Independent PDF export of that source uses the digest-verified official portable
  Tectonic 0.17.0 helper, isolated in work/tacl-rewrite-v120. No system TeX install,
  manuscript upload, failed UI retry, or numerical runtime change was required.
- PDF: 10 content pages plus 1 reference page, A4, anonymous review header/rulers,
  all fonts embedded, author metadata empty, no first-page floats, no overfull boxes.
- All 11 pages visually inspected; unchanged rendered pages were hash-matched to
  the previously inspected pass. Final renders contain only those eleven pages.
- All labels/citations resolve, all three main proofs are present, no em dashes.
- All 10 baseline rows, 8 optimization timings, 16 matched timings/storage contrasts
  and 2 quality endpoints agree with frozen reports. The toy bound uses exact fractions.
- All 1,322 original local source counterparts verify unchanged. All 14 prior
  evidence/source ZIP components are byte-identical in the new author archive.
- The unchanged portable verifier passes the new 20-member author archive.
  Its six historical corruption/scope rejection cases were not rerun unnecessarily.

Deliverables in the chat's outputs directory:
second-tacl-submission.pdf (110,438 bytes)
SHA256 f6dd8d12b7f1cdc9fc57593749afcd3339d5df1120cff454517fec04b0c9ecee
second-research-draft.tex (69,568 bytes)
SHA256 003aff0e4ec392bb71ad6ac1235f01561825327110a892274e298c85cd41e282
second-tacl-source-v120.zip (35,338 bytes)
SHA256 8032c9e9a28ba43204a9484ae6c1f2f139e00cc29c8d3dd2141899c01d95d0d6
second-author-review-v120.zip (10,998,448 bytes)
SHA256 3fac0525bc482defe9de04c257fa48a213662d7c318c5d0a20ad74e898e308af

Repository copies are reports/manuscript_v120.tex and reports/second_tacl_v120.pdf.
Validation and package manifests are validation/v120_manuscript_checks.json and
validation/v120_packages.json. The earlier preview-service failure is historical;
it no longer blocks the independently exported, inspected delivery PDF. Native
editor preview itself was not accessed or independently page-counted.

Remaining before any actual submission: author consent/order/affiliations/contact
information, prior review/publication and concurrent-submission eligibility,
editor-facing preprint disclosures where applicable, and assigned upload filename.
Source release terms and full indirect anonymity of historical evidence remain
unresolved. None blocks preparing the present paper; none was attested or uploaded.
The user has not authorized an actual TACL submission. Keep the scheduler PAUSED.
No subagent, paid compute, new monitor, third-party message or conference submission.
