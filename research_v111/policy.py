"""Prospective all-point token selection; target and certificates unchanged.

All point solves choose the existing token implementation before consuming
features. Boxes and Gram retain their original policies. No cross-route retry.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import threading
from research_v43 import dispatcher
from research_v111.config import POLICY

_ACTIVE=False


def identity():
    return dict(policy=POLICY,adapter_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                point_route='token',box_and_gram_policy='unchanged',cross_route_retry=False)


@contextmanager
def point_token():
    global _ACTIVE
    if _ACTIVE or threading.active_count()!=1:
        raise RuntimeError('Fresh single-thread point-policy scope required')
    original=dispatcher.assess_stage
    metadata=dict(identity(),closed=False,point_assessments=0,other_assessments=0)
    def assess(spec,total_tokens,**options):
        if options.get('kind','point')=='point':
            if options.get('route','auto') not in ('auto','token'):
                raise ValueError('Explicit non-token point route outside registered policy')
            options['route']='token';metadata['point_assessments']+=1
        else:metadata['other_assessments']+=1
        result=original(spec,total_tokens,**options)
        if options.get('kind','point')=='point':
            result=dict(result,selection_policy=POLICY)
        elif options.get('kind')=='box':
            fallback=original(spec,total_tokens,**dict(options,kind='point',route='token'))
            cap=options.get('policy',dispatcher.ResourcePolicy()).max_stage_work_units
            if not fallback['admitted'] or result['work_units']+fallback['work_units']>cap:
                raise dispatcher.DispatchRefused('Box plus point-token fallback exceeds stage limit',result)
            result=dict(result,box_and_point_fallback_work_units=result['work_units']+fallback['work_units'])
        return result
    _ACTIVE=True;dispatcher.assess_stage=assess
    try:yield metadata
    finally:
        dispatcher.assess_stage=original;metadata['closed']=True;_ACTIVE=False


@contextmanager
def execution(cell):
    from research_v79.implementation import execution as original_execution
    with original_execution(cell) as metadata:
        with point_token() as policy:
            metadata['point_route_policy']=policy
            yield metadata


def verify_metadata(metadata):
    if not (all(metadata.get(k)==v for k,v in identity().items())
            and metadata.get('closed') is True
            and type(metadata.get('point_assessments')) is int and metadata['point_assessments']>0
            and type(metadata.get('other_assessments')) is int and metadata['other_assessments']>=0):
        raise ValueError('Complete exact point-policy execution identity required')
    return True


def verify_routes(completion,stage_count):
    """Check recorded solver admissions, in addition to scoped policy metadata."""
    groups=[completion['request']['timing']] if 'request' in completion else [s['common_timing'] for s in completion['steps']]
    for group in groups:
        rows=group['stages']
        if len(rows)!=stage_count or len({r['stage_id'] for r in rows})!=stage_count:
            raise ValueError('Complete distinct stage route census required')
        for row in rows:
            admission=row['admission']
            if admission['kind']=='point' and not (row['route']==admission['selected_route']=='token'
                    and admission['selection_policy']==POLICY):
                raise ValueError('Actual point solve did not use registered token policy')
            if 'request' not in completion and admission['kind']!='point':
                raise ValueError('Fresh oracle must use point inputs')
    return True
