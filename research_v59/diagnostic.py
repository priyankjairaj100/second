"""Pure loss, packed-code, and exposure checks for one prospective anchor screen.

An adverse guard is a valid development result. No inference, calibration,
population interval, repair-state contract, or acceptance claim is established
by these descriptive checks.
"""
import math

from research_v55.diagnostic import (
    ARTICLE_IDS, finite_exp, reconstruct_fixed, reconstruct_sequential, require,
)
from research_v59.campaign import GUARDS, PARITY_TOLERANCE
from src.run_store import digest


CONTROL_LABELS = ('full_precision', 'nearest_rounding', 'fixed_feature', 'sequential')
CANDIDATE_LABEL = 'full_precision_anchor'
LABELS = (*CONTROL_LABELS, CANDIDATE_LABEL)


def _table(rows):
    require(type(rows) is list and len(rows) == 8
        and tuple(r['id'] for r in rows) == ARTICLE_IDS, 'Exactly the ordered eight exposed articles are required')
    for row in rows:
        require(type(row['predictions']) is int and row['predictions'] == 127
            and type(row['nll_sum']) in (int, float) and math.isfinite(row['nll_sum']),
            'Finite loss and 127 predictions required')
        if 'mean_nll' in row:
            require(row['mean_nll'] == row['nll_sum']/127, 'Stored mean NLL differs from its raw loss')
        if 'elapsed_ns' in row:
            require(type(row['elapsed_ns']) is int and row['elapsed_ns'] >= 0, 'Invalid loss timing')
    return {r['id']: r for r in rows}


def parity(quality, previous):
    """Check all 32 prior losses, including the two actual calibrated models."""
    require(set(quality) in (set(CONTROL_LABELS), set(LABELS)), 'All four old controls are required')
    require(previous['status'] == 'complete' and set(previous['quality']) == set(CONTROL_LABELS),
        'Complete frozen V55 four-model losses required')
    checks = []
    for label in CONTROL_LABELS:
        current, old = _table(quality[label]), _table(previous['quality'][label])
        for rid in ARTICLE_IDS:
            deviation = abs(current[rid]['nll_sum']-old[rid]['nll_sum'])/127
            checks.append(dict(model=label, record_id=rid, absolute_mean_nll_deviation=deviation,
                threshold=PARITY_TOLERANCE, passed=deviation <= PARITY_TOLERANCE))
    return dict(passed=all(r['passed'] for r in checks), checks=checks,
        checked_losses=32, max_absolute_mean_nll_deviation=max(r['absolute_mean_nll_deviation'] for r in checks),
        scope='All 32 frozen V55 full-precision, nearest, actual fixed-feature and actual sequential losses')


def summarize(quality):
    require(set(quality) == set(LABELS), 'Exactly four controls and one candidate are required')
    tables = {label: _table(quality[label]) for label in LABELS}
    totals, comparisons = {}, {}
    for label, table in tables.items():
        loss = math.fsum(table[rid]['nll_sum'] for rid in ARTICLE_IDS)
        totals[label] = dict(nll_sum=loss, predictions=1016, mean_nll=loss/1016,
            perplexity=finite_exp(loss/1016))
    for reference in CONTROL_LABELS:
        deltas = [tables[CANDIDATE_LABEL][rid]['nll_sum']-tables[reference][rid]['nll_sum'] for rid in ARTICLE_IDS]
        ratios = {rid: delta/127 for rid, delta in zip(ARTICLE_IDS, deltas)}
        pooled, maximum = math.fsum(deltas)/1016, max(ratios.values())
        comparisons[reference] = dict(pooled_log_perplexity_ratio=pooled,
            pooled_perplexity_ratio=finite_exp(pooled), article_log_perplexity_ratios=ratios,
            article_perplexity_ratios={rid: finite_exp(value) for rid, value in ratios.items()},
            max_article_log_ratio=maximum, max_article_ratio=finite_exp(maximum),
            articles_candidate_lower=sum(value < 0 for value in ratios.values()),
            articles_candidate_equal=sum(value == 0 for value in ratios.values()),
            articles_candidate_higher=sum(value > 0 for value in ratios.values()))
    primary = comparisons['sequential']
    guards = dict(pooled_pass=primary['pooled_log_perplexity_ratio'] <= math.log(GUARDS['max_pooled_candidate_over_sequential']),
        every_article_pass=primary['max_article_log_ratio'] <= math.log(GUARDS['max_article_candidate_over_sequential']))
    return dict(totals=totals, candidate_comparisons=comparisons, thresholds=GUARDS,
        guards=guards, development_guards_pass=all(guards.values()), inferential_interval=None,
        confirmation=False, acl_ready=False,
        ratio_overflow_rule='null perplexity/ratio means exp exceeded binary64; finite log values determine guards',
        scope='One adaptively chosen candidate on eight exposed articles; no population, superiority, service-performance or submission-readiness claim')


def reconstruct_candidate(blob, metadata, *, target_sha256, controls):
    """Reuse byte/grid reconstruction only; no nearest-anchor BoundTarget."""
    return reconstruct_sequential(blob, metadata, target_sha256=target_sha256, fixed=controls)


def first_stage_invariant(candidate, fixed, sequential, *, expected_sha256):
    require(len(candidate) == len(fixed) == len(sequential) == 24, 'Every model must contain all 24 stages')
    for row in zip(candidate, fixed, sequential):
        first = row[0]
        require(all(s.stage_id == first.stage_id and s.shape == first.shape and s.bits == first.bits == 4
            and s.grid_axis == first.grid_axis == 'dyadic_row' and s.scale_values == first.scale_values for s in row),
            'Candidate and frozen controls must use identical complete grids')
    hashes = dict(candidate=digest(candidate[0].packed_indices), fixed_feature=digest(fixed[0].packed_indices),
        sequential=digest(sequential[0].packed_indices))
    require(all(value == expected_sha256 for value in hashes.values()), 'Frozen first-stage packed-code invariant failed')
    require(candidate[0].packed_indices == fixed[0].packed_indices == sequential[0].packed_indices,
        'First-stage actual packed bytes differ')
    return dict(passed=True, stage_id=candidate[0].stage_id, packed_sha256=expected_sha256,
        model_hashes=hashes, actual_packed_bytes_equal=True,
        reason='First-stage features precede every installed teacher or calibrated matrix')


def check_result(result, previous, parity_artifact):
    require(result['status'] == 'complete' and result['valid_diagnostic'] is True, 'Quality worker incomplete')
    observed = parity(result['quality'], previous)
    require(observed['passed'] and observed == result['historical_parity'] == parity_artifact,
        'All 32 historical parity controls must reproduce')
    summary = summarize(result['quality'])
    require(summary == result['summary'] and result['development_guards_pass'] == summary['development_guards_pass'],
        'Reported summary or guards differ from raw losses')
    return summary


def check_progress(events, quality, stages, first_stage, guards_pass):
    """Verify all reported losses and that candidate work followed the parity gate."""
    expected = [('targets_and_actual_models_validated', {})]
    for label in CONTROL_LABELS:
        for row in quality[label]:
            expected.append(('quality_article', dict(model=label, record_id=row['id'], nll_sum=row['nll_sum'])))
    expected.extend([('all_historical_controls_passed', dict(checked_losses=32)), ('candidate_construction_started', {})])
    for stage in stages:
        expected.append(('candidate_stage', dict(stage_id=stage['stage_id'], elapsed_ns=stage['elapsed_ns'],
            output_code_sha256=stage['output_code_sha256'])))
    expected.append(('candidate_model_validated', dict(first_stage_packed_sha256=first_stage['packed_sha256'])))
    for row in quality[CANDIDATE_LABEL]:
        expected.append(('quality_article', dict(model=CANDIDATE_LABEL, record_id=row['id'], nll_sum=row['nll_sum'])))
    expected.append(('diagnostic_complete', dict(development_guards_pass=guards_pass)))
    require(len(events) == len(expected), 'Progress extent differs')
    previous_time = -1
    for event, (phase, details) in zip(events, expected):
        require(set(event) == {'phase', 'worker_elapsed_ns', *details}
            and event['phase'] == phase and all(event[k] == v for k, v in details.items()),
            'Progress order, loss, gate or stage differs')
        require(type(event['worker_elapsed_ns']) is int and event['worker_elapsed_ns'] >= previous_time,
            'Progress time must be nondecreasing')
        previous_time = event['worker_elapsed_ns']
    return dict(events=len(events), historical_losses_before_candidate=32,
        candidate_stages=len(stages), candidate_losses=8, parity_before_candidate=True)
