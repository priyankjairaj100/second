# Second V136: matched quality running, practical GPTQ comparison closed

29 October 2026. User explicitly requested actual execution. No scheduler restart.

V125 six original/fixed models completed and audited: 1920 article losses on the
V124 untouched 320-article frame. Fixed PPLs are 55.0773383/55.2139092 (Distil3/2)
and 48.0414543/47.2964273 (GPT2 3/2). Original PPLs49.2670841/41.6241075.
V131 four published-GPTQ controls completed and audited: 1280 additional losses.
Fixed/GPTQ ratios0.908293/0.923321 and0.905679/0.885381; all secondary95% paired
intervals below1. This is 7.7--11.5%lower PPL under the specified settings, not
same-target equality, general superiority, or the primary fixed/sequential guard.

V132 constructors16711--16714 saved all24/48stages and complete models, then
FAILED1:0 when their final JSON receipt attempted to serialize a bytes runtime
sidecar. No constructor was rerun and no old receipt was repaired. V133audits
16717--16720 all COMPLETED0:0. Actual source/input/model hashes, grids, stage
installation chains, certification counts, memberships and original first-stage
invariants passed independently. Original native runtime sidecars and original
worker CPU totals remain missing; Slurm accounting preserves their actual cost.
Read pilots/sequential-output-audit-v133-20261029/actual-audit.json and actual/.

V134quality16721--16724 failed before any losses because the new registration
included its data-registration hash string among file bindings. Actual totalCPU
0.466seconds; conservative carry4. V136 removes that misplaced scalar (the data
registration hash remains in prepared_data), adds four schema checks locally,
at submission and in each worker, and retains all other inputs/guards/evaluators.
Fresh four per-workerCPU caps3598; reserve14636 including carry<=14640original.
V13616725--16728 released once and running. Before any action inspect actual
jobs/receipts; do not call any old staging, submit or consumed collector again.

Analysis lock: pilots/control-quality-v136-20261029/analysis-lock.json.
Same20,000PCG64 seed124 shared article bootstrap. New four-stratum primary upper
98.75% quantile, ratios/upper<=1.05 and observed max<=1.20 remain unchanged.
Do not classify the primary gate before all four actual comparisons exist.

Prepared research_v135 minimal source-only format passes8generated tests. It
persists codes, target and retained tokens OR references, no features/Grams.
Token mode needs no external corpus; reference mode requires the retained source
provider. This is unregistered preparation, not model/timing evidence. A local
StageBinding attribute error was corrected before any registration or cluster use.

Next: close V136 all rows/terminal receipts, decide the primary quality gate,
update same manuscript and compile natively. Then register the source-only cold
comparison if scientifically justified. Operating range/precision, production
fault validation, repeated timing and clean reproduction remain pending.
Current manuscript is still verified V123 until closed-result update. The
original14ZIPs and frozen numerical sources remain unchanged. SchedulerPAUSED;
no subagents, paid compute, duplicate job, credentials, third-party message or
conference submission. All resource limits remain; GPT2grid allowance1,327,104.

Accounting note: early -X sacct snapshot returned zeroCPU for every allocation.
That snapshot is explicitly invalidated, not treated as free compute. Final
accounting must enable steps and count distinct top-level allocations once.
