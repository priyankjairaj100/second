"""Read-only manuscript transcription/arithmetic check against preserved reports.

Does not repeat inference, calibration, binary audits, or a scientific review.
Printed units and rounding are checked, not inferred from tests or partial jobs.
"""
from pathlib import Path
from decimal import Decimal
import argparse, datetime, hashlib, json, math, re, sys

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    'v58': 'validation/v58_terminal_metadata_check.json',
    'v59': 'validation/v59_terminal_metadata_check.json',
    'v62': 'validation/v62_recovery_metadata_check.json',
    'v63': 'validation/v63_terminal_metadata_check.json',
    'h58': 'handoff/program_v58.json',
    'h62': 'handoff/program_v62.json',
}


def digest(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def dec(value):
    return Decimal(str(value))


def fmt(value, places=0):
    return format(dec(value), f',.{places}f')


def pct(numerator, denominator, saving=False):
    ratio = dec(numerator) / dec(denominator)
    return 100 * (1 - ratio if saving else ratio - 1)


def normalized(text):
    return ' '.join(text.split())


def check(text, evidence):
    v58, v59, v62, v63, h58, h62 = (evidence[k] for k in INPUTS)
    checks = []
    def boolean(name, ok, sources):
        checks.append(dict(name=name, passed=bool(ok), sources=sources))
    def passage(name, expected, sources, scope=None):
        haystack = text if scope is None else scope
        count = normalized(haystack).count(normalized(expected))
        checks.append(dict(name=name, expected_text=expected, occurrences=count,
                           passed=count > 0, sources=sources))
    def section(start, end):
        if text.count(start) != 1 or text.count(end) != 1:
            return ''
        return text.split(start, 1)[1].split(end, 1)[0]

    # Every table row and column must agree, including order and endpoint labels.
    blocks = re.findall(r'\\begin\{table\*\}(.*?)\\end\{table\*\}', text, re.S)
    tables = [b for b in blocks if r'\label{tab:v61}' in b]
    rows = []
    if len(tables) == 1:
        for line in tables[0].splitlines():
            if '&' in line and re.search(r'\d', line):
                rows.append([v.strip().removesuffix(r'\\').strip() for v in line.split('&')])
    names = [('cached', 'Cached lossless'), ('cold', 'Cold reconstruction'),
             ('hybrid', 'Hybrid exact Gram'), ('compressed', 'Compressed 48-bit')]
    expected_rows = []
    t = v62['timings']
    for endpoint, tokens in enumerate([1536, 768]):
        for i, (arm, label) in enumerate(names):
            expected_rows.append([fmt(tokens) if i == 0 else '', label,
                fmt(dec(t[arm]['request_elapsed_ns'][endpoint]) / 10**9, 3),
                fmt(dec(t[arm]['live_state_bytes'][endpoint]) / 10**6, 3),
                fmt(dec(t[arm]['complete_deployment_bytes'][endpoint]) / 10**6, 3)])
    boolean('eight_table_rows_exact_order_labels_units_and_rounding', rows == expected_rows,
            ['v62:timings'])
    # Check all individual cells as well, to make a failed transcription localizable.
    for i, expected in enumerate(expected_rows):
        for j in range(2, 5):
            checks.append(dict(name=f'table_row_{i+1}_column_{j+1}',
                expected_text=expected[j], observed=rows[i][j] if i < len(rows) and j < len(rows[i]) else None,
                passed=i < len(rows) and j < len(rows[i]) and rows[i][j] == expected[j],
                sources=['v62:timings']))

    near = section(r'\paragraph{Nearest-anchor service and failed quality guard.}',
                   r'\paragraph{Adaptive full-precision-anchor screen (V59).}')
    adaptive = section(r'\paragraph{Adaptive full-precision-anchor screen (V59).}',
                       r'\paragraph{Original-checkpoint service (V61; recovered audits V62).}')
    service = section(r'\paragraph{Original-checkpoint service (V61; recovered audits V62).}',
                      r'\paragraph{Stronger lossless artifact control (V63).}')
    modern = section(r'\paragraph{Stronger lossless artifact control (V63).}',
                     r'\paragraph{Research decision.}')
    abstract = section(r'\begin{abstract}', r'\end{abstract}')
    boolean('all_scoped_sections_found', all([near, adaptive, service, modern, abstract]), ['manuscript'])

    oldt = v58['v54']['timings']
    savings = [fmt(pct(oldt['compressed']['live_state_bytes'][i], oldt['cached']['live_state_bytes'][i], True), 2) for i in range(2)]
    slower = [fmt(pct(oldt['compressed']['request_elapsed_ns'][i], oldt['cached']['request_elapsed_ns'][i]), 2) for i in range(2)]
    passage('nearest_anchor_storage_and_latency',
        f'Compression saves {savings[0]}\\% and {savings[1]}\\% of live state but takes {slower[0]}\\% and {slower[1]}\\% longer than the lossless cache.',
        ['v58:v54.timings'], near)
    passage('nearest_anchor_worker_and_failed_costs',
        f"numerical workers charge {fmt(v58['v54']['current_worker_cpu_seconds'])} CPU seconds; including the failed earlier preparation gives {fmt(v58['v54']['total_continuation_cpu_seconds'])} seconds.",
        ['v58:v54'], near)
    q = v58['cpu_quality']; a = v59['result']['quality']
    total, comparison = q['totals'], q['fixed_feature_comparisons']['sequential']
    boolean('nearest_anchor_guard_direction', q['guards'] == dict(every_article_pass=True, pooled_pass=False)
        and q['development_guards_pass'] is False and comparison['pooled_perplexity_ratio'] > q['thresholds']['max_pooled_fixed_over_sequential'], ['v58:cpu_quality'])
    passage('nearest_anchor_ppl_and_failed_guard',
        f"The nearest-anchor model's PPL is {fmt(total['fixed_feature']['perplexity'],5)}, versus {fmt(total['sequential']['perplexity'],5)} for sequential calibration: ratio {fmt(comparison['pooled_perplexity_ratio'],6)} exceeds the unchanged {fmt(q['thresholds']['max_pooled_fixed_over_sequential'],2)} guard.",
        ['v58:cpu_quality'], near)
    passage('nearest_anchor_tail_guard',
        f"The maximum article ratio, {fmt(comparison['max_article_ratio'],6)}, passes the separate {fmt(q['thresholds']['max_article_fixed_over_sequential'],2)} guard, but the overall gate fails.", ['v58:cpu_quality'], near)
    passage('nearest_anchor_all_eight_adverse', 'Loss is higher on all eight articles.', ['v58:cpu_quality.fixed_feature_comparisons.sequential'], near)
    boolean('nearest_anchor_eight_and_predictions', comparison['articles_fixed_higher'] == 8 and all(v['predictions'] == 1016 for v in total.values()), ['v58:cpu_quality'])
    passage('eight_article_prediction_count', 'Eight previously exposed articles supply 1,016 predictions per model', ['v58:cpu_quality.totals'], near)
    passage('full_precision_and_nearest_ppl',
        f"Full precision and nearest rounding have PPL {fmt(total['full_precision']['perplexity'],5)} and {fmt(total['nearest_rounding']['perplexity'],5)}.", ['v58:cpu_quality.totals'], near)
    passage('quality_cpu_charge', f"The quality worker charges {fmt(h58['v55_cpu_seconds'])} CPU seconds.", ['h58:v55_cpu_seconds'], near)
    passage('gpu_cpu_charge', f"Its {fmt(h58['v56_cpu_seconds'])}-CPU-second charge is separate.", ['h58:v56_cpu_seconds'], near)
    g = v58['gpu_parity']
    passage('gpu_pair_count', f"reproduces all {g['comparisons']} same-model article losses", ['v58:gpu_parity'], near)
    boolean('gpu_threshold_and_pass', g['passed'] is True and g['threshold'] == 1e-8, ['v58:gpu_parity'])
    passage('gpu_maximum_deviation', '$'+format(g['maximum_absolute_mean_nll_deviation']/1e-14, '.2f')+r'\times10^{-14}$', ['v58:gpu_parity.maximum_absolute_mean_nll_deviation'], near)

    candidate = a['totals']['full_precision_anchor']; comp = a['candidate_comparisons']['sequential']
    boolean('quality_ratios_recomputed_from_means',
        math.isclose(math.exp(candidate['mean_nll']-a['totals']['sequential']['mean_nll']),comp['pooled_perplexity_ratio'],rel_tol=1e-13)
        and math.isclose(math.exp(total['fixed_feature']['mean_nll']-total['sequential']['mean_nll']),comparison['pooled_perplexity_ratio'],rel_tol=1e-13), ['v58:cpu_quality','v59:result.quality'])
    passage('adaptive_candidate_ppl_nll_ratios',
        f"Its pooled PPL is {fmt(candidate['perplexity'],5)} (mean NLL {fmt(candidate['mean_nll'],6)}), giving candidate/sequential ratio {fmt(comp['pooled_perplexity_ratio'],6)} and maximum article ratio {fmt(comp['max_article_ratio'],6)}.", ['v59:result.quality'], adaptive)
    boolean('adaptive_guard_direction', a['guards'] == dict(every_article_pass=True, pooled_pass=True) and a['development_guards_pass'] is True, ['v59:result.quality'])
    passage('adaptive_guard_values', f"Both unchanged guards, {fmt(a['thresholds']['max_pooled_candidate_over_sequential'],2)} pooled and {fmt(a['thresholds']['max_article_candidate_over_sequential'],2)} per article, pass.", ['v59:result.quality'], adaptive)
    boolean('adaptive_article_directions', (comp['articles_candidate_lower'],comp['articles_candidate_higher'],a['candidate_comparisons']['fixed_feature']['articles_candidate_lower']) == (5,3,8), ['v59:result.quality.candidate_comparisons'])
    passage('adaptive_article_directions_text', 'Loss is lower on five articles and higher on three than sequential calibration, and lower on all eight than nearest-anchor calibration', ['v59:result.quality.candidate_comparisons'], adaptive)
    passage('adaptive_over_nearest_anchor_ratio', f"the latter pooled PPL ratio is {fmt(a['candidate_comparisons']['fixed_feature']['pooled_perplexity_ratio'],6)}.", ['v59:result.quality'], adaptive)
    passage('adaptive_full_precision_regression', f"Candidate PPL remains {fmt(pct(candidate['perplexity'],a['totals']['full_precision']['perplexity']),2)}\\% above the unquantized checkpoint.", ['v59:result.quality.totals'], adaptive)
    passage('adaptive_constructor_and_transaction', f"its constructor took {fmt(dec(v59['result']['constructor_elapsed_ns'])/10**9,3)} seconds and its complete worker transaction {fmt(dec(v59['result']['controller_transaction_elapsed_ns'])/10**9,3)} seconds.", ['v59:result'], adaptive)
    boolean('adaptive_historical_parity', v59['result']['historical_control_parity']['checked_losses'] == 32 and v59['result']['historical_control_parity']['max_absolute_mean_nll_deviation'] == 0, ['v59:result.historical_control_parity'])
    passage('adaptive_historical_parity_text', 'All 32 V55 control losses reproduced with zero observed mean-NLL deviation', ['v59:result.historical_control_parity'], adaptive)

    savings = [fmt(pct(t['compressed']['live_state_bytes'][i],t['cached']['live_state_bytes'][i],True),2) for i in range(2)]
    slowdown = [fmt(pct(t['compressed']['request_elapsed_ns'][i],t['cached']['request_elapsed_ns'][i]),2) for i in range(2)]
    deploy = [fmt(pct(t['compressed']['complete_deployment_bytes'][i],t['cached']['complete_deployment_bytes'][i],True),2) for i in range(2)]
    passage('service_live_saving_and_slowdown', f'Compression saves {savings[0]}\\% and {savings[1]}\\% of live state against cached lossless, but requests take {slowdown[0]}\\% and {slowdown[1]}\\% longer.', ['v62:timings'], service)
    passage('abstract_service_tradeoff', f'compression saves {savings[0]}\\% and {savings[1]}\\% of live state but takes {slowdown[0]}\\% and {slowdown[1]}\\% longer than cached lossless repair.', ['v62:timings'], abstract)
    passage('service_checkpoint_inclusive_savings', f'Including the checkpoint reduces savings to {deploy[0]}\\% and {deploy[1]}\\%.', ['v62:timings'], service)
    boolean('service_hybrid_first_endpoint_dominance', t['hybrid']['live_state_bytes'][0]<t['compressed']['live_state_bytes'][0] and t['hybrid']['request_elapsed_ns'][0]<t['compressed']['request_elapsed_ns'][0], ['v62:timings'])
    boolean('service_cached_fastest_both_endpoints', all(t['cached']['request_elapsed_ns'][i] < t[arm]['request_elapsed_ns'][i] for i in range(2) for arm in ['cold','hybrid','compressed']), ['v62:timings'])
    lifetimes = []
    for arm,_ in names:
        value=t[arm]['attributed_preparation_ns']+t[arm]['transaction_elapsed_ns']
        boolean('lifetime_sum_'+arm,value==t[arm]['attributed_two_deletion_lifetime_ns'],['v62:timings.'+arm])
        lifetimes.append(fmt(dec(value)/10**9,3))
    passage('attributed_two_request_costs', f"totals {lifetimes[0]} seconds for cached lossless, {lifetimes[1]} for cold, {lifetimes[2]} for hybrid and {lifetimes[3]} for compression.", ['v62:timings'], service)
    passage('numerical_worker_debits', f"The six numerical workers charged {fmt(v62['charged_worker_cpu_seconds'])} CPU seconds against their frozen {fmt(v62['phase_cap_cpu_seconds'])}-second allowance.", ['v62:charged_worker_cpu_seconds','v62:phase_cap_cpu_seconds'], service)
    def cpu_seconds(value):
        parts=value.split(':');return sum((dec(x)*60**i for i,x in enumerate(reversed(parts))),Decimal(0))
    recovery=sum((cpu_seconds(row['total_cpu']) for row in h62['scheduler_accounting']['recovery'].values()),Decimal(0))
    failure=cpu_seconds(h62['scheduler_accounting']['original']['13569']['total_cpu'])
    boolean('scheduler_support_cpu_sums', recovery==dec(h62['recovery_scheduler_cpu_seconds']) and failure==dec(h62['old_failed_audit_cpu_seconds']), ['h62:scheduler_accounting'])
    passage('recovery_cpu_cost', f'with {fmt(recovery,3)} scheduler CPU seconds combined.', ['h62:scheduler_accounting.recovery'], service)
    passage('failed_original_cpu_cost', f'The failed original audit consumed another {fmt(failure,3)} CPU seconds.', ['h62:scheduler_accounting.original.13569'], service)
    walls=[row['elapsed_seconds'] for row in h62['scheduler_accounting']['recovery'].values()]
    passage('recovery_walls', 'both completed in '+ ' and '.join(f'{n//60}:{n%60:02}' for n in walls)+' wall time', ['h62:scheduler_accounting.recovery'], service)

    endpoints={row['retained_records']:row for row in v63['summary']}
    a12,a6=endpoints[12],endpoints[6]
    passage('modern_exact_live_bytes', f"At 12 and 6 retained records, live state falls from {fmt(a12['old_live_bytes'])} and {fmt(a6['old_live_bytes'])} bytes to {fmt(a12['new_live_bytes'])} and {fmt(a6['new_live_bytes'])} bytes, reductions of {fmt(pct(a12['new_live_bytes'],a12['old_live_bytes'],True),3)}\\% and {fmt(pct(a6['new_live_bytes'],a6['old_live_bytes'],True),3)}\\%.", ['v63:summary'], modern)
    passage('compression_vs_modern', f"Uncertain compression remains {fmt(pct(t['compressed']['live_state_bytes'][0],a12['new_live_bytes'],True),2)}\\% and {fmt(pct(t['compressed']['live_state_bytes'][1],a6['new_live_bytes'],True),2)}\\% smaller than this stronger lossless archive.", ['v62:timings.compressed.live_state_bytes','v63:summary'], modern)
    added=v63['added_control_source_bytes']+v63['added_dependency_bytes']
    passage('codec_plus_source_footprint', f'The pinned codec installation and added control source occupy {fmt(added)} bytes', ['v63:added_control_source_bytes','v63:added_dependency_bytes'], modern)
    boolean('extra_dependency_reverses_small_saving',all(row['new_checkpoint_plus_added_dependency_bytes']>row['old_checkpoint_inclusive_bytes'] for row in v63['summary']), ['v63:summary'])
    passage('abstract_nearest_anchor_adverse_percent', f"a {fmt(pct(total['fixed_feature']['perplexity'],total['sequential']['perplexity']),2)}\\% perplexity regression beyond a {fmt((dec(q['thresholds']['max_pooled_fixed_over_sequential'])-1)*100)}\\% tolerance.", ['v58:cpu_quality'], abstract)
    return checks


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manuscript',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not sys.flags.optimize
    text=args.manuscript.read_text();evidence={};bindings={}
    manifest={line[66:]:line[:64] for line in (ROOT/'MANIFEST.sha256').read_text().splitlines()}
    for key,path in INPUTS.items():
        raw=(ROOT/path).read_bytes();bindings[path]=digest(raw)
        assert bindings[path]['sha256']==manifest[path]
        evidence[key]=json.loads(raw)
    checks=check(text,evidence);errors=[x['name'] for x in checks if not x['passed']]
    # In-memory falsification probes leave the actual document/evidence untouched.
    mutations={
        'alter_one_table_time':text.replace('4,083.951 & 368.133','4,083.950 & 368.133',1),
        'swap_table_size_columns':text.replace('4,083.951 & 368.133 & 720.958','4,083.951 & 720.958 & 368.133',1),
        'reverse_adverse_quality_statement':text.replace('but the overall gate fails.','but the overall gate passes.',1),
    }
    detected={name:value!=text and any(not r['passed'] for r in check(value,evidence)) for name,value in mutations.items()}
    report=dict(schema='manuscript-number-check-v69',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='passed_transcription_and_arithmetic_only' if not errors and all(detected.values()) else 'failed',
        manuscript=digest(text.encode()),inputs=bindings,checks=checks,check_count=len(checks),failed_checks=errors,
        tamper_probes_detected=detected,table_rows=8,table_numeric_cells=24,
        local_inference_calibration_or_binary_audit=False,archived_metadata_audits_rerun=False,
        scope='Selected empirical table, quality figures, percentages and resource totals against previously verified report bytes; not every number in the manuscript or a new scientific result.',
        actual_empirical_jobs_launched=False,submission_ready=False)
    with args.output.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ['status','check_count','failed_checks','tamper_probes_detected','table_rows','table_numeric_cells']}))
    if errors or not all(detected.values()):raise SystemExit(1)


if __name__=='__main__':main()
