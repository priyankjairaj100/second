# V63: stronger lossless artifact control running

Snapshot 16 October 2026, 08:01:47 UTC (13:31 IST). Linux qualification 15244
completed 0:0 in 4 seconds: 21 tests, zero skips. Measurement 15245 is RUNNING;
audit 15246 is dependency-pending. This is a launch checkpoint, not a result.
Refresh scheduler state before continuation. Do not repeat the one-use submission.

The source/registration were frozen before empirical factor reads:
registration SHA256 479f7861b06933994916f1d3a22d94caed104dffdcc807c58a73dbacee5ce9d6.
Read research_v63/PROTOCOL.txt and handoff/registration_v63.json. Seven new source
files are staged under local_runs/lossless-control-v63-20261016-a/research_v63.
The clean numerical checkout remains f900999 with all 432 historical sources
unchanged. Do not synchronize reporting changes into that checkout while running.

The isolated pinned python-zstandard 0.25.0 wheel contains Zstandard 1.5.7. The
existing environment is unchanged. The fixed control extends raw/zlib6/shuffled-
zlib6 with plain/shuffled Zstandard 3, choosing minimum complete descriptor size
with fixed ties. It measures all five candidates, canonical validation and exact
binary64 words; preserves source access and retained descriptor bytes; records
full archive, trust and added dependency sizes. Existing target/model codes are
copied and checked, never recomputed. Original, 12-source and 6-source endpoint
archives must restore actual V61 state bytes; both retained-descriptor transitions
must equal independently repacked existing endpoints. The new archive is a
distinct storage format, not a relabelled V61 repair service.

All 21 local and 21 pinned Linux boundary checks passed. They include largest-shape
roundtrip, signed zero/subnormal/extreme words, malformed/truncated/extra frames,
window/dictionary limits, canonical source/model/membership checks and complete
old-state restoration. Local initial Python/package compatibility refusals are
recorded separately in validation/v63_preparation_check.json. Root source/resource
review only; no independent reviewer. Test success is not a measured size result.

The three one-attempt jobs use one CPU, 16 GiB memory and 1 GiB output-file caps.
CPU caps: 300/3600/1800 seconds; wall caps:10/65/35 minutes. The fresh 5706-CPU-second
allowance is separate from old ledgers. Dependencies require successful completion,
requeue is disabled, and any failure stops this phase without automatic retry or
limit increase. Preserve all partial files, failures and actual scheduler CPU.

Evidence workflow

After the chain is terminal and quiescent, validation/collect_v63_metadata.py can
capture bounded JSON/log/source files into a fresh archive outside the checkout.
It does not read numerical binaries or alter old files. Transfer by verified
SHA256, safely extract into a fresh directory, then run:
python3 -B validation/check_v63_metadata.py EXTRACTED --repo REPO --output FRESH.json

The checker validates source/runtime/job bindings, three actual-byte audit claims,
input/output census, all candidate receipts and complete size arithmetic. Two
metadata boundary fixtures passed; full real-output integration remains pending.
The source of any reporting-helper fix may change; registered research_v63 source
must not change after launch. Actual saved archive validation occurs in the
separate Slurm audit, not in a local metadata-only check.

Scientific decision

V62 already established V61 complete code/state agreement and linkage to the V59
exposed-quality candidate. Compression saved about 9% live state but cost 39–42%
more request time than cached lossless. Hybrid dominated at the first endpoint.
V63 asks whether ordinary stronger lossless compression removes that modest
storage advantage. It does not test deletion latency, untouched quality, fresh
calibration roots or timing replication. Do not infer a new end-to-end time by
adding codec component timings to V61 clocks. The supplied-code transition is
not calibration or a measured repair implementation.

If the actual artifact result is useful, freeze a NEW complete-service comparison
with matched point solver, full parsing/validation, startup/cache policy, all
controls and fresh actual state reconstruction. If it eliminates the proposed
advantage, preserve that finding and narrow the paper. Follow the existing
NEXT_SCIENTIFIC_GATE_V61.txt for later disjoint roots, untouched quality and
prospective repetitions. No expansion or cross-model claim is registered here.

The existing manuscript remains the compiled V62 version. Do not insert V63
results until actual artifact audits and terminal consistency checks pass.
