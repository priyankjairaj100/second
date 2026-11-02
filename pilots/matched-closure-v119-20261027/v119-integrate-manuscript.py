from pathlib import Path
import json,hashlib,re
w=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2');s=w/'work/second-speed-campaign';m=w/'outputs/second-research-draft.tex'
r=json.loads((s/'v119-closed-collection/reduction.json').read_bytes());terminal=json.loads((s/'v119-closed-collection/terminal-stdout.json').read_bytes())
assert terminal['evidence']['actual_model_state_trust_pairs']==16 and terminal['status']=='verified'
contrasts=json.loads((s/'v119-closed-report/signed-contrasts.json').read_bytes());assert len(contrasts)==4 and all(float(x['complete_host_change_percent'])>0 and float(x['live_storage_change_percent'])<0 for x in contrasts)
b=m.read_bytes();prior=json.loads((s/'v119-proof-placement-precompile.json').read_bytes());assert hashlib.sha256(b).hexdigest()==prior['new_sha256']
t=b.decode()
abstract=r'''Can a smaller calibration archive recover the exact quantized model after
records are removed? We study a fixed-teacher target with exact dyadic feature
interpretation, fixed normalization and grids, and deterministic adaptive rounding.
Source-local compressed enclosures support universal decision certificates,
bounded exact replay, and canonical successor states. We prove conditional code
and state correctness; bounded completion and practical benefit require evidence.
On DistilGPT2 with $1664\to1536\to768$ calibration tokens, five service arms
match fresh reconstruction for all 42.47 million codes and each successor state.
Compression saves 9.24\% and 8.70\% of live state against a strong lossless feature
cache. After optimization, compressed requests are 0.90\% faster at one endpoint
and 12.73\% slower at the other. A hybrid exact-Gram control is faster and smaller
at the first endpoint, with source access. A separate matched DistilGPT2/GPT2
screen uses $512\to384\to256$ tokens and a prospectively fixed point-solver policy.
All sixteen model, state and trust comparisons match fresh reconstruction across
24 or 48 stages. Compression saves 7.01--7.86\% of live state but takes
1.44--2.66 times the optimized lossless request time; one GPT2 endpoint requires
source replay. Each timing is one observation. On a separate 320-article frame,
the earlier DistilGPT2 target has 0.54\% and 0.71\% higher pooled perplexity than
sequential calibration, within the frozen tolerances and bootstrap upper bounds.
The evidence supports certified reconstruction and a bounded storage/access/latency
tradeoff, with a small measured quality cost on that frame. General acceleration,
cross-architecture reliability and quality transfer remain unestablished.'''
a=t.index('\\begin{abstract}')+len('\\begin{abstract}');z=t.index('\\end{abstract}',a);t=t[:a]+'\n'+abstract+'\n'+t[z:]
old='''A complete optimization screen narrows that gap without a uniform latency win.
Untouched quality measurements show a small perplexity cost within the frozen tolerances.
The earlier failed quality guard and adaptive teacher choice remain part of the
evidence~\\evidence{E03, E12, E13, E14, E16, E17}.'''
new='''A complete optimization screen narrows that gap without a uniform latency win.
A matched screen then recovers complete DistilGPT2 and GPT2 states under a
prospectively fixed point-solver policy. Its compressed requests save storage but
lose to the optimized lossless cache at all four measured checkpoint/endpoint
settings. One GPT2 endpoint also requires replay. These results test related
checkpoint depths, not general acceleration or cross-architecture reliability.
Untouched quality measurements on the earlier DistilGPT2 target show a small
perplexity cost within the frozen tolerances. The failed quality guard and
adaptive teacher choice remain explicit~\\evidence{E03, E12, E13, E14, E16, E17, E18, E19, E20}.'''
assert t.count(old)==1;t=t.replace(old,new)
old='The packed model artifact contains code indices for all 24 calibrated affine\nstages; unchanged checkpoint components are still needed for inference.'
new='The packed model artifact contains code indices for all calibrated affine stages:\n24 in DistilGPT2 and 48 in GPT2. Unchanged checkpoint components remain necessary\nfor inference.'
assert t.count(old)==1;t=t.replace(old,new)
a=t.index('\\subsection{Related-checkpoint diagnostic}');z=t.index('\\subsection{Untouched predictive quality}',a)
section=r'''\subsection{Matched related-checkpoint screen}
An initial matched screen completed both preparations but its first GPT2 request
refused bounded certification. Nineteen unstarted dependents were cancelled.
A separate diagnostic certified all 2,359,296 codes of the implicated stage using
the existing token solver within the original limits. That stage result had no
independent fresh-stage oracle or full-model comparison; the failure and diagnostic
remain in Appendix~\ref{sec:history} and E19.

The subsequent screen uses DistilGPT2 and the 124-million-parameter GPT2
checkpoint~\cite{gpt2card}. Both receive the same four exposed 128-token records,
original-checkpoint teacher policy, fixed normalization 512, and $4\to3\to2$
deletion trajectory. The approved grid allowance is 1,327,104 entries. Before
execution, every point-valued solve in all four cells and both fresh oracles was
assigned the existing token route; box and Gram policies were unchanged. This
prospective override differs from the original dimension-based dispatcher and
changes the numerical route, not the exact target. The two sealed preparations
were reused. Each request uses a fresh process, one CPU and 16\,GiB memory on the
same host, with fixed order and uncontrolled OS cache.

All sixteen complete model, state and trust comparisons match fresh retained-data
reconstruction under both audits. This covers 42,467,328 codes across 24 stages
for DistilGPT2 and 84,934,656 across 48 stages for GPT2. The oracle reconstructs
features from retained records without reading the candidate predecessor state.
Correctness therefore survives this tested change in checkpoint depth and solver
policy. It does not establish cross-architecture generality.

'''
table=(s/'v119-closed-report/matched-table.tex').read_text().replace('normalization512','normalization 512')
section+=table+'\n'+r'''The optimization packages reduce observed request times within each representation,
but optimized compression loses to optimized modern storage in all four settings
(Table~\ref{tab:matched-token}). It takes 43.59\% and 80.92\% longer on DistilGPT2,
and 166.15\% and 88.47\% longer on GPT2. Live-state savings are respectively
7.78\%/7.01\% and 7.86\%/7.09\%; checkpoint-inclusive savings shrink to
1.84\%/1.30\% and 2.24\%/1.61\%. These are complete observed transactions, not
estimates of a stable latency distribution.

The measured phases distinguish two costs. At the three-record GPT2 endpoint,
both compressed cells fall back at the final-block MLP up-projection and execute
144 source-stage/record pairs. Optimized compressed stage work takes 1,458.767
seconds, including 695.104 seconds of source extraction, versus 476.578 seconds
for optimized modern storage. The source clock is nested and is not added again.
All other fourteen requests perform no source traversal or fallback. Even without
replay, DistilGPT2's two-record optimized compressed stage work takes 267.560
seconds versus 114.651 for modern storage. Cheaper predecessor validation,
2.266 versus 9.120 seconds, does not offset that difference. Stage work includes
certification and other operations; decoder-only time is unavailable, so the
bundled changes do not identify an isolated decoder effect.

The new numerical workers charge 14,222 CPU seconds. Including the preserved
failed-screen and diagnostic debit of 6,304 gives 20,526 within the unchanged
82,840 ceiling. All 21 new allocations, including both audits, consume between
18,213.235 and 18,214.255 scheduler CPU seconds. The reused preparation host times
are 1,389.528 seconds for DistilGPT2 and 2,992.098 for GPT2. Those preparations
built several representations and were shared across cells; their full cost
cannot be assigned exclusively to one arm or treated as zero. Historical costs,
the separate unresolved 12,602-second debit, every timing partition and all memory
observations remain in E20. Overlapping clocks are not added.

This screen supplies related-checkpoint correctness and counterexamples to an
observed speed win at every tested setting. It does not prove that every future
implementation or workload must lose. We retain the bounded tradeoff claim and
do not launch the proposed 64-request timing replication. Stable latency would
require a separately registered balanced study; repetitions of selected favorable
endpoints would not establish generality. No quality evaluation was performed for
these 512-normalized targets. The following quality results concern the earlier
1664-normalized DistilGPT2 target only~\evidence{E20}.

'''
t=t[:a]+section+t[z:]
t=t.replace('evidence summaries E01--E19,','evidence summaries E01--E20,')
old='''supplement covers E19, which preserves the failed matched screen and scoped
selected-stage certificate. The path-adapted source copies'''
new='''supplement covers E19, which preserves the failed matched screen and scoped
selected-stage certificate. The point-policy source supplement supports E20's
closed matched screen: all sixteen comparisons, both audits, all request rows,
source replays and complete accounting. The path-adapted source copies'''
assert t.count(old)==1;t=t.replace(old,new)
old='''unverified. The guide records pinned model/data revisions and publisher-declared
Apache 2.0 (DistilGPT2) and ODC-BY (C4) terms, including the additional Common
Crawl conditions.'''
new='''unverified. The guide and source supplements record pinned model/data revisions.
The pinned model cards declare Apache 2.0 (DistilGPT2) and MIT (GPT2) terms;
the data documentation declares ODC-BY (C4), with additional Common Crawl conditions.'''
assert t.count(old)==1;t=t.replace(old,new)
a=t.index('\\section{Conclusion}');z=t.index('\\label{page:main-end}',a)
t=t[:a]+r'''\section{Conclusion}
Compressed calibration evidence supports conditional code recovery and canonical
successor equality, with audited complete reconstruction on two related checkpoint
depths. The measured benefit is a modest storage tradeoff. Optimization improves
the implementation but does not establish general acceleration: compression loses
at one endpoint of the original screen and all four settings of the matched
screen. Source avoidance is also conditional; one GPT2 endpoint requires replay.
Hybrid offers a competing tradeoff when source access is allowed.
The earlier DistilGPT2 target passes both untouched quality tolerances with
slightly worse perplexity than sequential calibration. That result does not
transfer to the new targets. We retain all failures and adverse comparisons.
The contribution is a checked reconstruction contract and its measured operating
limits, with broad latency reliability and predictive transfer left unestablished.

'''+t[z:]
a=t.index('The complete comparative evidence concerns one checkpoint,');z=t.index('Exact agreement concerns the declared fixed-teacher target',a)
t=t[:a]+'''The complete comparative evidence concerns two related GPT-family checkpoints,
short calibration records and adaptive development experiments. The original
checkpoint teacher was selected after the nearest-anchor quality failure.
The disjoint-root service and untouched quality support the earlier DistilGPT2
target on one bounded article frame; eight exposed articles alone cannot establish
quality on new data. The matched screen uses four exposed records and a different
512 normalization. Its solver policy was fixed after a failed screen and selected
stage diagnostic. All sixteen later comparisons pass, but that success does not
erase the prior refusal or establish cross-architecture reliability. Timing cells
have one observation with uncontrolled OS cache; prospective balanced timing
repetitions and quality evaluation of the new targets were not performed.
'''+t[z:]
t=t.replace('The successful diagnostic motivates a prospective point-route policy,','The successful diagnostic motivated a prospective point-route policy,')
needle='Both outcomes and their costs remain explicit~\\evidence{E19}.'
assert t.count(needle)==1;t=t.replace(needle,needle+'\nThe subsequent complete matched screen is reported separately in the main text~\\evidence{E20}.')
assert all(x in t for x in ('5.92','40-bit','12.73','1.010342','1.011431','12,602'))
m.write_text(t)
(s/'v119-integration-before-compile.json').write_text(json.dumps(dict(prior_sha256=hashlib.sha256(b).hexdigest(),new_sha256=hashlib.sha256(m.read_bytes()).hexdigest(),actual_terminal=r['actual_terminal'],all_16_rows_included=True,all_four_compressed_ratios_above_one=True,new_quality_claim=False,stable_latency_claim=False,cross_architecture_claim=False,abstract_word_count=len(abstract.split())),indent=2)+'\n')
print(json.dumps({'manuscript_bytes':m.stat().st_size,'abstract_words':len(abstract.split()),'all_rows':16}))
