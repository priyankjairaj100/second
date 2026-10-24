"""Pure reduction of already audited request clocks; never an evidence gate.

Call only after the actual frozen terminal closure and input checks. This module
cannot establish correctness, successful execution or generality from its inputs.
"""
from fractions import Fraction

CELLS = ('reference_compressed', 'reference_modern',
         'optimized_compressed', 'optimized_modern')


def require(value, message):
    if not value:
        raise ValueError(message)


def integer(value, label, positive=False):
    require(type(value) is int and value >= int(positive), label)
    return value


def phase_partition(host_ns, request, expected_stages):
    """Disjoint measured intervals plus an explicitly unattributed remainder.

    For compressed fallback, source extraction occurs inside a stage timer. Its
    diagnostic duration is not added to the stage sum. Decoder-only time is not
    separately measured by this telemetry and cannot be recovered by subtraction.
    """
    host_ns = integer(host_ns, 'Positive complete host time required', True)
    stages_count = integer(expected_stages, 'Positive stage count required', True)
    elapsed = integer(request['request_elapsed_ns'], 'Positive request time required', True)
    require(elapsed <= host_ns, 'Request clock must fit within host clock')
    require(request['arm'] in ('compressed', 'modern'), 'Only the matched stored-state requests are supported')
    timing = request['timing']
    stages = timing['stages']
    require(len(stages) == stages_count and len({r['stage_id'] for r in stages}) == stages_count,
            'Every distinct actual stage is required')
    for row in stages:
        integer(row['elapsed_ns'], 'Nonnegative stage time required')
        require(type(row['fallback']) is bool, 'Explicit fallback flag required')
    fallback = [r for r in stages if r['fallback']]
    source = integer(timing['source_extraction_ns'], 'Nonnegative source time required')
    pairs = integer(timing['neural_stage_record_pairs'], 'Nonnegative source access count required')
    require(integer(timing['encoding_and_gram_ns'], 'Nonnegative encoding time required') == 0,
            'Stored-state requests do not prepare fresh payloads')
    if fallback:
        require(request['arm'] == 'compressed' and source > 0 and pairs > 0
                and source <= max(r['elapsed_ns'] for r in fallback),
                'Fallback source traversal must be contained in a fallback stage')
    else:
        require(source == pairs == 0, 'Unexplained source access outside fallback')
    partition = dict(
        outside_request=host_ns-elapsed,
        predecessor_validation=integer(timing['predecessor_validation_ns'], 'Nonnegative validation time required'),
        stage_work_including_any_fallback=sum(r['elapsed_ns'] for r in stages),
        serialization=integer(timing['serialization_ns'], 'Nonnegative serialization time required'),
        disposal=integer(timing['disposal_ns'], 'Nonnegative disposal time required'))
    known = sum(v for k, v in partition.items() if k != 'outside_request')
    require(known <= elapsed, 'Recorded disjoint phases exceed request time')
    partition['unattributed_request_time'] = elapsed-known
    return dict(disjoint_host_partition_ns=partition,
                nested_source_extraction_ns=source,
                source_stage_record_pairs=pairs,
                fallback_stages=[r['stage_id'] for r in fallback],
                decoder_only_duration_available=False,
                remainder_is_not_a_named_operation=True)


def ratio(numerator, denominator):
    q = Fraction(integer(numerator, 'Positive ratio numerator required', True),
                 integer(denominator, 'Positive ratio denominator required', True))
    return dict(numerator=q.numerator, denominator=q.denominator)


def comparisons(rows):
    """Keep all four cells and both endpoints; ratios use complete host time.

    Rows must come from verified saved receipts. A speedup is baseline/candidate;
    a compressed time ratio is compressed/modern. No averaging, significance,
    launch decision or causal attribution to an individual optimization is made.
    """
    expected = {(cell, step) for cell in CELLS for step in (1, 2)}
    require(set(rows) == expected, 'All eight cell/endpoint observations are required')
    for row in rows.values():
        for key in ('host_elapsed_ns', 'live_state_bytes', 'checkpoint_inclusive_bytes'):
            integer(row[key], 'Positive complete observation required', True)
        require(row['checkpoint_inclusive_bytes'] >= row['live_state_bytes'], 'Checkpoint-inclusive size cannot be smaller')
    result = []
    for step in (1, 2):
        item = dict(step=step, combined_optimization_speedup={})
        for representation in ('compressed', 'modern'):
            a, b = (rows[p+'_'+representation, step] for p in ('reference', 'optimized'))
            item['combined_optimization_speedup'][representation] = ratio(a['host_elapsed_ns'], b['host_elapsed_ns'])
        a, b = (rows['optimized_'+rep, step] for rep in ('compressed', 'modern'))
        item['optimized_compressed_to_modern'] = {
            key: ratio(a[key], b[key]) for key in
            ('host_elapsed_ns', 'live_state_bytes', 'checkpoint_inclusive_bytes')}
        result.append(item)
    return result
