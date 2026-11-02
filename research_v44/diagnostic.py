"""Pure validation, code reconstruction, and descriptive quality summaries."""
import math

from research_v43.state import Record, validate_state
from src.run_store import canonical_json, digest


LABELS = ('full_precision', 'nearest_rounding', 'fixed_feature', 'sequential')
ARTICLE_ROWS = (2525, 2237, 132, 2115, 2352, 1040, 3636, 1299)
ARTICLE_IDS = tuple('wikitext2:validation:article-row-'+str(i) for i in ARTICLE_ROWS)
PARITY_TOLERANCE = 1e-8
GUARDS = dict(max_pooled_fixed_over_sequential=1.05, max_article_fixed_over_sequential=1.20)


def require(value, message):
    if not value:
        raise ValueError(message)


def finite_exp(value):
    """Keep a valid adverse diagnostic even when its PPL exceeds binary64."""
    try:
        return math.exp(value)
    except OverflowError:
        return None


def validate_exposed(registration, history):
    records = registration['records']
    require(tuple(r['id'] for r in records) == ARTICLE_IDS, 'Exactly the eight exposed V30 articles are required')
    require(all(r['document_id'] == r['id'] and len(r['tokens']) == 128
        and all(type(t) is int and 0 <= t < 50257 for t in r['tokens']) for r in records),
        'Historical article payload or token extent differs')
    require(set(ARTICLE_IDS) <= set(registration['excluded_from_future_confirmation_ids']),
        'All diagnostic articles must already be excluded')
    require(history['status'] == 'complete' and history['registration_sha256'] == digest(canonical_json(registration)),
        'Historical losses do not bind the exposed registration')
    for label in ('full_precision', 'nearest_rounding'):
        table = history['quality'][label]
        require(len(table) == 8 and {r['id'] for r in table} == set(ARTICLE_IDS), 'Historical control losses incomplete')
        require(all(r['predictions'] == 127 and math.isfinite(r['nll_sum']) for r in table),
            'Historical control losses or counts invalid')
    return records


def reconstruct_fixed(state_blob, model_blob, *, bound_target, records, provenance):
    """Recover exact row-grid values from the validated V43 packed state."""
    expected = tuple(Record(r['id'], tuple(r['tokens']), canonical_json(provenance[r['id']])) for r in records)
    state = validate_state(state_blob, expected_target=bound_target, expected_records=expected)
    require(state.representation == 'compressed40', 'Use the audited actual compressed successor')
    require(len(state.stage_codes) == 24 and sum(s.rows*s.columns for s in state.stage_codes) == 42_467_328,
        'The actual complete 24-stage model is required')
    packed = b''.join(s.packed_indices for s in state.stage_codes)
    require(len(model_blob) == 21_233_664 and packed == model_blob, 'Model export differs from the actual state codes')
    return state.stage_codes


def parity(quality, history):
    checks = []
    for label in ('full_precision', 'nearest_rounding'):
        rows = quality.get(label, [])
        require(len(rows) == 8 and {r['id'] for r in rows} == set(ARTICLE_IDS), 'Parity control extent incomplete')
        old = {r['id']:r for r in history['quality'][label]}
        for row in rows:
            require(row['predictions'] == old[row['id']]['predictions'] == 127
                and math.isfinite(row['nll_sum']), 'Parity loss/count invalid')
            deviation = abs(row['nll_sum']-old[row['id']]['nll_sum']) / 127
            checks.append(dict(model=label, record_id=row['id'], absolute_mean_nll_deviation=deviation,
                threshold=PARITY_TOLERANCE, passed=deviation <= PARITY_TOLERANCE))
    return dict(passed=all(r['passed'] for r in checks), checks=checks,
        scope='All sixteen full-precision/nearest losses on the same eight already exposed articles')


def summarize(quality):
    require(set(quality) == set(LABELS), 'All four declared models are required')
    tables = {}
    for label in LABELS:
        rows = quality[label]
        require(len(rows) == 8 and {r['id'] for r in rows} == set(ARTICLE_IDS), 'Matched article set incomplete')
        require(all(r['predictions'] == 127 and math.isfinite(r['nll_sum']) for r in rows),
            'Nonfinite loss or prediction extent differs')
        tables[label] = {r['id']:r for r in rows}
    totals = {}
    for label, table in tables.items():
        loss = math.fsum(table[rid]['nll_sum'] for rid in ARTICLE_IDS)
        totals[label] = dict(nll_sum=loss, predictions=1016, mean_nll=loss/1016,
            perplexity=finite_exp(loss/1016))
    comparisons = {}
    for reference in ('sequential', 'nearest_rounding', 'full_precision'):
        deltas = [tables['fixed_feature'][rid]['nll_sum']-tables[reference][rid]['nll_sum'] for rid in ARTICLE_IDS]
        log_ratios = {rid:d/127 for rid,d in zip(ARTICLE_IDS,deltas)}
        pooled = math.fsum(deltas)/1016
        maximum = max(log_ratios.values())
        comparisons[reference] = dict(pooled_perplexity_ratio=finite_exp(pooled),
            pooled_log_perplexity_ratio=pooled,article_log_perplexity_ratios=log_ratios,
            article_perplexity_ratios={rid:finite_exp(v) for rid,v in log_ratios.items()},
            max_article_ratio=finite_exp(maximum),max_article_log_ratio=maximum,
            articles_fixed_lower=sum(v < 0 for v in log_ratios.values()),
            articles_fixed_equal=sum(v == 0 for v in log_ratios.values()),
            articles_fixed_higher=sum(v > 0 for v in log_ratios.values()))
    primary = comparisons['sequential']
    guards = dict(pooled_pass=primary['pooled_log_perplexity_ratio'] <= math.log(GUARDS['max_pooled_fixed_over_sequential']),
        every_article_pass=primary['max_article_log_ratio'] <= math.log(GUARDS['max_article_fixed_over_sequential']))
    return dict(totals=totals, fixed_feature_comparisons=comparisons, thresholds=GUARDS,
        guards=guards, development_guards_pass=all(guards.values()),
        inferential_interval=None, confirmation=False, acl_ready=False,
        ratio_overflow_rule='null perplexity/ratio means exp exceeded binary64; finite log values determine guards',
        scope='Adaptive diagnostic on eight previously exposed articles; no population, superiority, or submission-readiness claim')
