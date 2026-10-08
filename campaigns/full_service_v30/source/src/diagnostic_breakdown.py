"""Artifact-verified exclusive attribution inside one diagnostic transaction.

This decomposes an instrumented observation; it never corrects or predicts a
clean clock. Unknown overhead remains an explicit residual. Category durations
come only from verified nonoverlapping root windows and exclusive nested spans.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .run_store import canonical_json, digest, strict_json
from .transaction_timing import BOUNDARY

CLOCK = 'time.perf_counter_ns_system_monotonic'
CATEGORY_MAP = {
    'extraction':'extraction',
    'cache_feature_extraction':'feature_extraction_overhead',
    'proof_verification':'proof_verification',
    'bound_query':'proof_bound_query',
    'replay_feature_evaluation':'retained_replay',
    'cache_replay_feature_evaluation':'retained_replay',
    'fresh_feature_evaluation':'fresh_features',
    'cache_fresh_feature_evaluation':'fresh_features',
    'cache_deleted_feature_evaluation':'deleted_features',
    'factor_rounding':'factorization_rounding',
    'cache_factor_rounding':'factorization_rounding',
    'validation_metadata':'metadata_validation',
    'cache_validation':'metadata_validation',
    'persisted_state_reload':'loading',
    'serialization':'serialization',
    'cache_serialization':'serialization',
    'durable_output':'durable_output',
    'artifact_output':'artifact_commit_overhead',
    'artifact_diagnostics':'diagnostic_overhead',
    'certificate_diagnostics':'diagnostic_overhead',
    'provider_diagnostics':'diagnostic_overhead',
    'gram_accumulation':'gram_accumulation',
    'cache_gram_accumulation':'gram_accumulation',
    'exact_gram':'gram_accumulation',
    'source_access':'source_access',
    'cache_retained_source_access':'source_access',
    'deleted_payload_lookup':'source_access',
    'retained_payload_selection':'source_access',
    'service_overhead':'service_overhead',
}
REQUIRED_CATEGORIES = ('loading','extraction','proof_verification','retained_replay',
                       'factorization_rounding','metadata_validation','serialization','durable_output','cleanup')


def _int(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name+' requires nonnegative integer nanoseconds')
    return value


def _window(value, *, clock=False):
    if type(value) is not dict or (clock and value.get('clock')!=CLOCK):
        raise ValueError('unsupported diagnostic timing window clock')
    start,end,wall=(_int(value.get(name),name) for name in ('start_ns','end_ns','wall_ns'))
    if end < start or end-start != wall:
        raise ValueError('diagnostic window duration differs from endpoints')
    return (start,end,wall)


def _disjoint(windows):
    ordered=sorted(windows)
    if any(left[1]>right[0] for left,right in zip(ordered,ordered[1:])):
        raise ValueError('diagnostic timing windows overlap')
    return ordered


def _partition(observer):
    begin,end,total=_window(observer.get('observer_clock'),clock=True)
    if total!=_int(observer.get('observed_wall_ns'),'observed_wall_ns'):
        raise ValueError('observer clock differs from recorded total')
    spans=observer.get('timing_detail_spans',observer.get('timing_spans'))
    if type(spans) is not list or not spans:
        raise ValueError('missing diagnostic outer partition')
    cursor=0; result=[]
    for span in spans:
        start,stop,wall=(_int(span.get(k),k) for k in ('start_offset_ns','end_offset_ns','wall_ns'))
        if start!=cursor or stop-start!=wall:
            raise ValueError('outer diagnostic partition overlaps or has gaps')
        result.append((begin+start,begin+stop,span['name'])); cursor=stop
    if cursor!=total:
        raise ValueError('outer diagnostic partition does not equal total')
    return begin,end,total,result


def decompose_records(observer, child):
    """Pure checked arithmetic; only artifact loader below issues verified output."""
    begin,end,total,spans=_partition(observer)
    result={'schema':'diagnostic-transaction-breakdown-v1','verified_artifacts':False,
        'measurement_boundary':BOUNDARY,'observed_wall_ns':total,
        'category_map_sha256':digest(canonical_json(CATEGORY_MAP)),
        'timing_use':'diagnostic attribution only; not clean latency or an overhead correction',
        'scope':'exclusive internal spans plus explicit unclassified residual; no nested timer addition'}
    mode=(child or {}).get('execution_mode')
    telemetry=(child or {}).get('service_telemetry',{})
    attribution=mode=='diagnostic' and telemetry.get('instrumented') is True
    categories=defaultdict(int); counts=defaultdict(int); roots=[]; unavailable=[]; unknown=[]
    execution=[(a,b) for a,b,name in spans if name in ('worker_execution_until_cleanup','worker_execution_and_cleanup')]
    cleanup_known=any(name=='ordinary_process_cleanup' for _,_,name in spans)
    if not execution:
        attribution=False
        unavailable.append('worker execution coordinates unavailable')
    # Only disjoint explicitly recorded observer cleanup is reassigned. Other
    # controller overhead retains its original phase label.
    adopted=_disjoint([_window(value) for value in observer.get('adopted_cleanup_windows',[])])
    for a,b,_ in adopted:
        if a<begin or b>end:
            raise ValueError('cleanup window escapes transaction')
    for a,b,name in spans:
        cuts=sum(max(0,min(b,y)-max(a,x)) for x,y,_ in adopted)
        if cuts>b-a:
            raise ValueError('cleanup attribution double counts an interval')
        if name=='ordinary_process_cleanup':
            if cuts:
                raise ValueError('ordinary and adopted cleanup intervals overlap')
            categories['cleanup']+=b-a
        elif name in ('worker_execution_until_cleanup','worker_execution_and_cleanup'):
            if cuts:
                raise ValueError('adopted cleanup overlaps child execution')
            categories['unclassified_worker_execution']+=b-a
        else:
            categories[name]+=b-a-cuts
    categories['cleanup']+=sum(wall for _,_,wall in adopted)
    if attribution:
        if telemetry.get('timing_clock')!=CLOCK or telemetry.get('timing_windows_omitted')!=0:
            unavailable.append('service root windows unavailable, custom, or truncated')
        else:
            windows=_disjoint([_window(x) for x in telemetry.get('timing_windows',[])])
            timings=telemetry.get('timings')
            if type(timings) is not dict:
                raise ValueError('diagnostic exclusive timings are missing')
            cost=0; mapped=defaultdict(int); mapped_calls=defaultdict(int)
            for name,item in timings.items():
                if type(name) is not str or type(item) is not dict:
                    raise ValueError('invalid exclusive diagnostic category')
                duration=_int(item.get('exclusive_ns'),name)
                calls=_int(item.get('calls'),name+' calls')
                category=CATEGORY_MAP.get(name,'unmapped_service_category')
                if name not in CATEGORY_MAP:
                    unknown.append(name)
                mapped[category]+=duration; mapped_calls[category]+=calls; cost+=duration
            if cost!=_int(telemetry.get('total_exclusive_ns'),'exclusive total') or cost!=sum(x[2] for x in windows):
                raise ValueError('exclusive service sum differs from its disjoint root windows')
            roots.extend((a,b,'service') for a,b,_ in windows)
            for name,value in mapped.items(): categories[name]+=value
            for name,value in mapped_calls.items(): counts[name]+=value
            categories['unclassified_worker_execution']-=cost
        preflight=(child or {}).get('preflight',{})
        measurements=(('loading','loading_measurement'),('chart_construction','chart_construction_measurement'))
        for category,key in measurements:
            metric=preflight.get(key)
            if metric is None:
                if category!='chart_construction' or child.get('output_contract')!='model_only':
                    unavailable.append(key+' unavailable')
                continue
            window=metric.get('timing_window')
            if window is None:
                unavailable.append(key+' has no diagnostic coordinates'); continue
            a,b,wall=_window(window,clock=True)
            if _int(metric.get('wall_time_ns'),key)!=wall:
                raise ValueError('preflight measurement differs from its timing window')
            roots.append((a,b,category)); categories[category]+=wall; counts[category]+=1
            categories['unclassified_worker_execution']-=wall
    else:
        unavailable.append('detailed diagnostic profile unavailable')
    _disjoint([(a,b,b-a) for a,b,_ in roots])
    for a,b,_ in roots:
        if not any(left<=a<=b<=right for left,right in execution):
            raise ValueError('child diagnostic window escapes measured worker execution')
    if any(value<0 for value in categories.values()):
        raise ValueError('diagnostic components exceed their enclosing span')
    if sum(categories.values())!=total:
        raise ValueError('diagnostic accounting differs from complete observed wall time')
    for category in REQUIRED_CATEGORIES:
        categories.setdefault(category,0)
    if not cleanup_known:
        unavailable.append('ordinary worker cleanup has no separate coordinates')
    completed=(observer.get('outcome',{}).get('status')=='complete' and
               (child or {}).get('outcome',{}).get('status')=='complete')
    if not completed:
        unavailable.append('transaction or child did not complete successfully')
    result.update(status='attributed' if attribution and not unavailable and not unknown else 'partial',
        named_attribution_complete=attribution and not unavailable and not unknown and categories['unclassified_worker_execution']==0,
        execution_mode=mode,categories_ns=dict(sorted(categories.items())),
        category_calls=dict(sorted(counts.items())),accounting_sum_ns=sum(categories.values()),
        child_diagnostic_windows=[{'start_ns':a,'end_ns':b,'component':kind} for a,b,kind in sorted(roots)],
        unavailable_components=unavailable,unmapped_telemetry_categories=sorted(unknown),
        residual_ns=categories['unclassified_worker_execution'],
        residual_meaning='unclassified worker preparation, startup/imports, untimed leaf/control work, exit, waiting and scheduling; no specific category inferred',
        zero_semantics='zero means no measured span in this observation, not evidence that the operation is universally free')
    return result


def diagnostic_breakdown(row, *, expected_target=None):
    """Read and verify the original observation; never launch a model or worker."""
    from .measured_comparison import verify_role, _read_ref
    from .transaction_timing import verify_observer_receipt
    verify_role(row,expected_target)
    observer_path=Path(row['timing_receipt_path'])
    observer=verify_observer_receipt(observer_path.parent)
    child=None
    if row.get('child_receipt_path') is not None:
        raw=_read_ref({'path':row['child_receipt_path'],'sha256':row['child_receipt_sha256']})
        child=strict_json(raw)
    result=decompose_records(observer,child)
    result.update(verified_artifacts=True,role=row['role'],target_manifest_sha256=row['target_manifest_sha256'],
        observer_identity_sha256=row['observer_identity_sha256'],observer_attempt=observer['attempt'],
        observer_receipt_sha256=row['timing_receipt_sha256'],child_receipt_sha256=row.get('child_receipt_sha256'),
        source_sha256=observer['source_sha256'],transaction_outcome=observer['outcome'])
    return result


def diagnostic_report(comparison_root):
    """Attribute each available arm of one verified measured comparison."""
    from .measured_comparison import verify_measured_archive, METHODS
    comparison=verify_measured_archive(comparison_root)
    target=comparison['target_manifest_sha256']
    rows={'setup':comparison['setup'],**comparison['methods']}
    return {'schema':'diagnostic-comparison-breakdown-v1','verified_artifacts':True,
        'plan_sha256':comparison['plan_sha256'],'target_manifest_sha256':target,
        'clean_latency_claimed':False,
        'roles':{name:diagnostic_breakdown(rows[name],expected_target=target) if rows[name].get('timing_receipt_path')
                 else {'status':'not_started','observed_wall_ns':None} for name in ('setup',*METHODS)}}
