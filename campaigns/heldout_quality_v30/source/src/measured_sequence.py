"""Matched complete-transaction sequences over immutable original inputs.

Every role is observed separately. Preparation is performed once per system;
request i consumes the preceding verified committed repair state. Research
verification is outside each production-role clock. No data are downloaded.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import time

from .experiment_campaign import _phase_caps
from .experiment_inventory import _workload_map, source_hashes
from .experiment_runner import _integer, _local, _read_json, _referenced_json, _sha, _text
from .run_store import RunStore, read_completed, atomic_write, canonical_json, digest, strict_json
from .sequence_campaign import (build_sequence_campaign, validate_sequence_campaign,
    sequence_manifest_payload, sequence_manifest_binding, _confirmation_product)
from .transaction_timing import BOUNDARY, transaction_source_hashes, _snapshot
from .worker_control import WorkerLimits
from .runtime_contract import capture_runtime_contract, validate_runtime_contract, verify_runtime_contract

METHODS = ('repair', 'indexed_fresh', 'direct_fresh', 'model_only_fresh')
SCHEMA = 'calibration-measured-sequence-campaign-v1'


def measured_sequence_orders(seed, root_id, sequence_id, repeat_index):
    from .request_workload import SeedStream
    _integer(repeat_index, 'repeat index')
    stream=SeedStream(seed, root_id+'/'+sequence_id+'/measured-sequence-order')
    base=stream.permutation(METHODS)
    block,shift=divmod(repeat_index,4)
    if block%2: base=list(reversed(base))
    order=base[shift:]+base[:shift]
    prep=['setup','model_only_fresh']
    if (repeat_index+int(digest(canonical_json([seed,root_id,sequence_id]))[:8],16))%2: prep.reverse()
    return order,prep


def build_measured_sequence_plan(*, manifest_path, manifest, target_manifest_sha256,
                                worker_limits, sources, method_order=METHODS,
                                preparation_order=('setup','model_only_fresh'), execution_mode='clean', runtime_contract=None, quality=False):
    if type(quality) is not bool:raise ValueError('quality requires a Boolean')
    plan = {'schema':'calibration-measured-sequence-plan-v1',
        'manifest_path':str(manifest_path), 'manifest_payload':sequence_manifest_payload(manifest),
        'manifest_binding_sha256':sequence_manifest_binding(manifest),
        'target_manifest_sha256':_sha(target_manifest_sha256),
        'worker_limits':WorkerLimits.from_payload(worker_limits).payload(),
        'source_sha256':sources,'method_order':list(method_order),
        'preparation_order':list(preparation_order),'execution_mode':execution_mode,
        'runtime_contract':runtime_contract or capture_runtime_contract(),'quality':'heldout_nll' if quality else 'none'}
    _validate_plan_payload(plan)
    return plan


def _validate_plan_payload(plan):
    fields = {'schema','manifest_path','manifest_payload','manifest_binding_sha256',
        'target_manifest_sha256','worker_limits','source_sha256','method_order','preparation_order','execution_mode','runtime_contract','quality'}
    if type(plan) is not dict or set(plan)!=fields or plan['schema']!='calibration-measured-sequence-plan-v1':
        raise ValueError('invalid measured sequence plan')
    if plan['quality'] not in ('none','heldout_nll'):raise ValueError('invalid sequence quality policy')
    validate_runtime_contract(plan['runtime_contract'])
    _text(plan['manifest_path'],'sequence manifest path')
    if (sequence_manifest_payload(plan['manifest_payload']) != plan['manifest_payload'] or
        sequence_manifest_binding(plan['manifest_payload']) != _sha(plan['manifest_binding_sha256'])):
        raise ValueError('sequence plan manifest binding differs')
    if sorted(plan['method_order']) != sorted(METHODS) or len(plan['method_order'])!=4:
        raise ValueError('sequence requires exactly four measured roles')
    if sorted(plan['preparation_order']) != ['model_only_fresh','setup']:
        raise ValueError('sequence requires each preparation exactly once')
    if plan['execution_mode'] not in ('clean','diagnostic'):
        raise ValueError('invalid sequence execution mode')
    _sha(plan['target_manifest_sha256'])
    WorkerLimits.from_payload(plan['worker_limits'])


def derive_step_manifest(manifest, manifest_path, step):
    """Preserve original records/M0; only cumulative deletion and request ID vary."""
    schedule = manifest['requests']
    if type(step) is not int or step < -1 or step >= len(schedule):
        raise ValueError('invalid measured sequence step')
    result = strict_json(canonical_json({k:v for k,v in manifest.items() if k not in ('sequence_id','requests')}))
    result.update(schema='calibration-run-v1',
        request_id=manifest['sequence_id']+':initial' if step==-1 else schedule[step]['request_id'],
        deleted_ids=[rid for item in schedule[:step+1] for rid in item['deleted_ids']])
    base = Path(manifest_path).parent
    for field in ('checkpoint','calibration','heldout','protocol'):
        result[field]['path'] = str(_local(base,result[field]['path']))
    return result


def validate_measured_sequence_plan(path, *, execute=False, inventory_path=None, inventory_run_id=None):
    path = Path(path).absolute()
    plan, raw = _read_json(path)
    _validate_plan_payload(plan)
    verify_runtime_contract(plan['runtime_contract'])
    if raw != canonical_json(plan):
        raise ValueError('measured sequence plan requires canonical bytes')
    if plan['source_sha256'] != transaction_source_hashes():
        raise ValueError('measured sequence source hashes differ')
    manifest_path = _local(path.parent,plan['manifest_path'])
    manifest, manifest_raw = _read_json(manifest_path)
    if sequence_manifest_binding(manifest)!=plan['manifest_binding_sha256']:
        raise ValueError('sequence manifest differs from measured plan')
    protocol, protocol_raw = _referenced_json(manifest_path.parent,manifest['protocol'])
    phase = manifest.get('phase')
    if phase not in ('software_test','feasibility','development','confirmation'):
        raise ValueError('invalid measured sequence phase')
    if execute and phase!='software_test' and 'experiments_paused' in str(protocol.get('status','')):
        raise ValueError('the protocol keeps research experiments paused')
    calibration, _ = _referenced_json(manifest_path.parent,manifest['calibration'])
    from .sequence_runner import validate_requests
    validate_requests(manifest['requests'],[r['id'] for r in calibration['records']])
    limits = WorkerLimits.from_payload(plan['worker_limits']); limits.check_host()
    caps = _phase_caps({'entries':[{'phase':phase}]},protocol,limits)
    if (inventory_path is None)!=(inventory_run_id is None):
        raise ValueError('sequence inventory path and run ID are required together')
    if execute and phase=='confirmation' and inventory_path is None:
        raise ValueError('measured sequence confirmation requires frozen ordered inventory')
    evidence = None
    if inventory_path is not None:
        checked,item = verify_measured_sequence_membership(inventory_path,inventory_run_id,path,execute=execute)
        evidence = {'kind':'measured','path':str(checked['inventory_path']),
            'sha256':checked['inventory_sha256'],'run_id':inventory_run_id,'plan_path':str(path)}
    return {'plan':plan,'plan_path':path,'plan_sha256':digest(raw),'manifest':manifest,
        'manifest_path':manifest_path,'manifest_sha256':digest(manifest_raw),
        'protocol':protocol,'protocol_sha256':digest(protocol_raw),
        'protocol_path':_local(manifest_path.parent,manifest['protocol']['path']),
        'limits':limits,'phase_cpu_seconds':caps,'inventory_evidence':evidence,
        'original_record_ids':[r['id'] for r in calibration['records']],'runtime_contract':plan['runtime_contract']}


def build_measured_sequence_campaign(*, campaign_id, protocol_path, workloads, runs, worker_limits, sources):
    """Runs bind plan_path/plan and the matching manifest_path/manifest/target."""
    legacy_runs=[]; plans=[]
    for run in runs:
        if set(run)!={'run_id','plan_path','plan','manifest_path','manifest','target_manifest_sha256'}:
            raise ValueError('invalid measured sequence run specification')
        _validate_plan_payload(run['plan'])
        legacy_runs.append({k:run[k] for k in ('run_id','manifest_path','manifest','target_manifest_sha256')})
        plans.append({'run_id':run['run_id'],'plan_path':str(run['plan_path']),
            'plan_payload':run['plan'],'plan_sha256':digest(canonical_json(run['plan']))})
    legacy=build_sequence_campaign(campaign_id=campaign_id,protocol_path=protocol_path,
        workloads=workloads,runs=legacy_runs,worker_limits=worker_limits,sources=source_hashes(Path(__file__).resolve().parents[1]))
    result={'schema':SCHEMA,'ordered_inventory':legacy,'plans':plans,'source_sha256':sources}
    validate_measured_sequence_campaign(result)
    return result


def validate_measured_sequence_campaign(payload):
    if type(payload) is not dict or set(payload)!={'schema','ordered_inventory','plans','source_sha256'} or payload['schema']!=SCHEMA:
        raise ValueError('invalid measured sequence inventory schema')
    legacy=payload['ordered_inventory']; validate_sequence_campaign(legacy)
    entries={e['run_id']:e for e in legacy['entries']}
    seen=set(); paths=set(); configurations={}
    workloads=_workload_map(legacy['workloads'])
    for row in payload['plans']:
        if set(row)!={'run_id','plan_path','plan_payload','plan_sha256'} or row['run_id'] not in entries or row['run_id'] in seen:
            raise ValueError('measured sequence plans must match every ordered entry once')
        seen.add(row['run_id'])
        if row['plan_path'] in paths: raise ValueError('duplicate sequence plan path')
        paths.add(row['plan_path'])
        plan=row['plan_payload']; _validate_plan_payload(plan); entry=entries[row['run_id']]
        if digest(canonical_json(plan))!=row['plan_sha256']:
            raise ValueError('measured sequence plan digest differs')
        if (plan['manifest_payload']!=entry['manifest_payload'] or
            plan['target_manifest_sha256']!=entry['target_manifest_sha256'] or
            plan['worker_limits']!=legacy['worker_limits'] or plan['source_sha256']!=payload['source_sha256']):
            raise ValueError('measured sequence plan differs from ordered inventory')
        order,prep=measured_sequence_orders(workloads[entry['root_id']][0]['seed'],
            entry['root_id'],entry['sequence_id'],entry['repeat_index'])
        if plan['method_order']!=order or plan['preparation_order']!=prep:
            raise ValueError('measured sequence role/preparation order differs from frozen counterbalance')
        mode=configurations.setdefault(entry['configuration_id'],(plan['execution_mode'],plan['runtime_contract'],plan['quality']))
        if mode!=(plan['execution_mode'],plan['runtime_contract'],plan['quality']):
            raise ValueError('one measured sequence configuration mixes execution modes')
    if seen!=set(entries): raise ValueError('measured sequence inventory has missing plans')


def validate_measured_sequence_campaign_files(path, *, execute=False):
    path=Path(path).absolute(); payload,raw=_read_json(path)
    validate_measured_sequence_campaign(payload)
    if raw!=canonical_json(payload): raise ValueError('measured inventory requires canonical bytes')
    if payload['source_sha256']!=transaction_source_hashes() or payload['ordered_inventory']['source_sha256']!=source_hashes(Path(__file__).resolve().parents[1]):
        raise ValueError('measured sequence inventory source hashes differ')
    legacy=payload['ordered_inventory']
    for row in payload['plans']:verify_runtime_contract(row['plan_payload']['runtime_contract'])
    protocol_path=_local(path.parent,legacy['protocol_path']); protocol,protocol_raw=_read_json(protocol_path)
    if protocol.get('planned_inventory_sha256')!=digest(raw): raise ValueError('protocol does not bind measured sequence inventory')
    _confirmation_product(legacy,protocol)
    limits=WorkerLimits.from_payload(legacy['worker_limits']);limits.check_host()
    workloads=_workload_map(legacy['workloads']);plans={r['run_id']:r for r in payload['plans']};checked=[]
    resolved=set()
    for entry in legacy['entries']:
        row=plans[entry['run_id']];plan_path=_local(path.parent,row['plan_path']); plan,plan_raw=_read_json(plan_path)
        if plan!=row['plan_payload'] or digest(plan_raw)!=row['plan_sha256'] or plan_raw!=canonical_json(plan):
            raise ValueError('external measured sequence plan differs')
        manifest_path=_local(path.parent,entry['manifest_path'])
        if _local(plan_path.parent,plan['manifest_path'])!=manifest_path or manifest_path in resolved:
            raise ValueError('measured sequence manifest path differs or aliases another run')
        resolved.add(manifest_path);manifest,manifest_raw=_read_json(manifest_path)
        if sequence_manifest_binding(manifest)!=entry['manifest_binding_sha256']:
            raise ValueError('external sequence manifest differs')
        if (_local(manifest_path.parent,manifest['protocol']['path'])!=protocol_path or
            manifest['protocol']['sha256']!=digest(protocol_raw)):
            raise ValueError('sequence protocol reference differs')
        calibration,_=_referenced_json(manifest_path.parent,manifest['calibration'])
        if [r['id'] for r in calibration['records']]!=workloads[entry['root_id']][0]['original_record_ids']:
            raise ValueError('sequence record order differs from frozen workload')
        if execute and entry['phase']!='software_test' and 'experiments_paused' in str(protocol.get('status','')):
            raise ValueError('the protocol keeps research experiments paused')
        if entry['phase']=='confirmation' and (protocol.get('schema')!='calibration-protocol-v1' or
                protocol.get('status')!='frozen_confirmation' or protocol.get('blocked_fields')!=[]):
            raise ValueError('confirmation requires frozen unblocked protocol')
        checked.append({'entry':entry,'plan_path':plan_path,'plan':plan,'manifest_path':manifest_path,
                        'manifest':manifest,'manifest_sha256':digest(manifest_raw)})
    return {'inventory_path':path,'inventory_sha256':digest(raw),'inventory':payload,
        'protocol':protocol,'protocol_path':protocol_path,'protocol_sha256':digest(protocol_raw),
        'source_sha256':payload['source_sha256'],'checked':checked,'limits':limits,
        'phase_cpu_seconds':_phase_caps(legacy,protocol,limits)}


def verify_measured_sequence_membership(inventory_path,run_id,plan_path,*,execute=False):
    checked=validate_measured_sequence_campaign_files(inventory_path,execute=execute)
    rows=[r for r in checked['checked'] if r['entry']['run_id']==run_id]
    if len(rows)!=1 or rows[0]['plan_path']!=Path(plan_path).absolute():
        raise ValueError('measured sequence plan is absent from frozen inventory')
    return checked,rows[0]


def verify_measured_sequence_manifest(inventory_path,run_id,plan_path,manifest_path,sequence_step=None,*,execute=True):
    checked,item=verify_measured_sequence_membership(inventory_path,run_id,plan_path,execute=execute)
    expected=derive_step_manifest(item['manifest'],item['manifest_path'],sequence_step)
    actual,raw=_read_json(Path(manifest_path).absolute())
    if actual!=expected or raw!=canonical_json(expected):
        raise ValueError('derived sequence role manifest differs from frozen step')
    return {'inventory_sha256':checked['inventory_sha256'],'protocol_sha256':checked['protocol_sha256'],
        'source_sha256':checked['source_sha256'],'target_manifest_sha256':item['entry']['target_manifest_sha256'],
        'manifest_sha256':digest(raw),'manifest_path':str(Path(manifest_path).absolute()),
        'plan_sha256':digest(canonical_json(item['plan'])),'execution_mode':item['plan']['execution_mode'],'runtime_contract':item['plan']['runtime_contract'],'quality':item['plan']['quality']}


def _write_bound(path, payload):
    raw=canonical_json(payload);path=Path(path)
    if path.exists():
        if path.is_symlink() or path.read_bytes()!=raw:
            raise ValueError('immutable measured sequence artifact changed')
    else:
        atomic_write(path,raw)
    return {'path':str(path.absolute()),'sha256':digest(raw)}


def _reference(reference):
    if type(reference) is not dict or not {'path','sha256'}<=set(reference) or set(reference)-{'path','sha256','bytes'}:
        raise ValueError('invalid sequence artifact reference')
    path=Path(reference['path']).absolute()
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('sequence artifact reference contains a symlink')
    raw=path.read_bytes()
    if digest(raw)!=_sha(reference['sha256']): raise ValueError('sequence artifact reference changed')
    return strict_json(raw),raw


def _lineage_record(reference):
    record,raw=_reference(reference)
    path=Path(reference['path']); identity,_=_read_json(path.parent/'identity.json')
    if read_completed(path.parent,identity)!=record:
        raise ValueError('sequence predecessor is not an immutable committed receipt')
    if record.get('schema')!='measured-sequence-state-commit-v1' or record.get('outcome')!='complete':
        raise ValueError('sequence predecessor did not verify exact state')
    _reference(record['state_reference'])
    rows=record.get('verification_rows')
    if type(rows) is not dict or 'repair' not in rows or 'model_only_fresh' not in rows:
        raise ValueError('predecessor lacks its verified role receipts')
    models=set()
    for role,row in rows.items():
        receipts={}
        if not _row_complete(row):raise ValueError('predecessor contains an unsuccessful role')
        for field in ('child_receipt','timing_receipt'):
            reference={'path':row[field+'_path'],'sha256':row[field+'_sha256']}
            receipt,_=_reference(reference);receipts[field]=receipt
            directory=Path(reference['path']).parent
            identity,_=_read_json(directory/'identity.json')
            if read_completed(directory,identity)!=receipt:
                raise ValueError('predecessor role receipt is not sealed')
            if field=='timing_receipt' and not receipt.get('eligible_fresh_transaction_latency'):
                raise ValueError('predecessor has no eligible complete observation')
            if field=='child_receipt' and receipt.get('outcome',{}).get('status')!='complete':
                raise ValueError('predecessor child did not complete')
        if receipts['timing_receipt'].get('transaction_result_sha256')!=row['child_receipt_sha256']:
            raise ValueError('predecessor observation belongs to a different child receipt')
        if role=='repair' and receipts['child_receipt'].get('artifact',{}).get('state_sha256')!=row['state_reference']['sha256']:
            raise ValueError('predecessor state is not its repair child artifact')
        from .measured_comparison import _common_model
        _,original_model=_reference(row['original_model_reference'])
        child=receipts['child_receipt']
        expected=child.get('model_artifact',{}).get('sha256') if role=='model_only_fresh' else child.get('artifact',{}).get('model_sha256')
        if expected!=row['original_model_reference']['sha256']:
            raise ValueError('predecessor model differs from original child artifact')
        child_target=child.get('target_manifest_sha256',child.get('metadata',{}).get('target_manifest_sha256'))
        if child_target!=record['target_manifest_sha256']:
            raise ValueError('predecessor child target differs')
        common=_common_model(original_model,record['target_manifest_sha256'])
        _,saved_common=_reference(row['model_reference'])
        if saved_common!=common:raise ValueError('predecessor common model was not derived from its child')
        models.add(digest(common))
    if len(models)!=1 or record['model_reference']['sha256'] not in models:
        raise ValueError('predecessor complete models disagree')
    if record['state_reference']!=_pair(rows['repair']['state_reference']):
        raise ValueError('predecessor state differs from its verified repair output')
    return record


def validate_sequence_context(request,manifest,records,old):
    """Charged validation uses only the previous state-producing transaction.

    Research commits, oracle artifacts, common-model copies, and observer files
    are not inputs to this service-side transition.
    """
    context=request['sequence_context']
    fields={'plan_path','sequence_sha256','step_index','previously_deleted_ids','newly_deleted_ids',
            'predecessor_child_reference'}
    if type(context) is not dict or set(context)!=fields:
        raise ValueError('invalid measured sequence context')
    evidence=request.get('inventory')
    checked=validate_measured_sequence_plan(context['plan_path'],execute=True,
        inventory_path=None if evidence is None else evidence['path'],
        inventory_run_id=None if evidence is None else evidence['run_id'])
    index=_integer(context['step_index'],'sequence step index')
    if checked['plan_sha256']!=context['sequence_sha256'] or request['plan_sha256']!=checked['plan_sha256']:
        raise ValueError('sequence context differs from bound plan')
    expected=derive_step_manifest(checked['manifest'],checked['manifest_path'],index)
    if manifest!=expected: raise ValueError('sequence child manifest differs from frozen step')
    previous=[rid for r in checked['manifest']['requests'][:index] for rid in r['deleted_ids']]
    newly=checked['manifest']['requests'][index]['deleted_ids']
    if context['previously_deleted_ids']!=previous or context['newly_deleted_ids']!=newly:
        raise ValueError('sequence child deletion provenance differs')
    reference=context['predecessor_child_reference']
    predecessor,_=_reference(reference)
    directory=Path(reference['path']).parent
    identity,_=_read_json(directory/'identity.json')
    if read_completed(directory,identity)!=predecessor or predecessor.get('outcome',{}).get('status')!='complete':
        raise ValueError('sequence predecessor child did not commit successfully')
    role='setup' if index==0 else 'repair'
    prior_manifest=derive_step_manifest(checked['manifest'],checked['manifest_path'],index-1)
    prior_request,_=_read_json(directory/predecessor['attempt']/'request.json')
    prior_binding=digest(canonical_json(prior_manifest))
    if (predecessor.get('role')!=role or prior_request.get('role')!=role or
        predecessor.get('plan_sha256')!=checked['plan_sha256'] or prior_request.get('plan_sha256')!=checked['plan_sha256'] or
        predecessor.get('manifest_sha256')!=prior_binding or prior_request.get('manifest_sha256')!=prior_binding or
        prior_request.get('source_sha256')!=request['source_sha256'] or
        prior_request.get('target_manifest_sha256')!=checked['plan']['target_manifest_sha256'] or
        predecessor.get('metadata',{}).get('target_manifest_sha256')!=checked['plan']['target_manifest_sha256'] or
        prior_request.get('execution_mode')!=request.get('execution_mode')):
        raise ValueError('sequence predecessor lineage differs from previous frozen request')
    prior_context=prior_request.get('sequence_context')
    if index==0:
        if prior_context is not None:raise ValueError('initial preparation has unexpected sequence predecessor')
    elif (type(prior_context) is not dict or prior_context.get('step_index')!=index-1 or
          prior_context.get('sequence_sha256')!=checked['plan_sha256']):
        raise ValueError('sequence predecessor belongs to another step')
    stem='original' if role=='setup' else role
    expected_state={'path':str(directory/predecessor['attempt']/(stem+'-state.json')),
                    'sha256':predecessor['artifact']['state_sha256']}
    if _pair(request['original_state'])!=expected_state:
        raise ValueError('sequence predecessor lineage differs from supplied state')
    _reference(expected_state)
    _reference({'path':str(directory/predecessor['attempt']/(stem+'-model.json')),
                'sha256':predecessor['artifact']['model_sha256']})
    expected_live={r.record_id:r.content_digest for r in records if r.record_id not in set(previous)}
    if old is None or {r.record_id:r.content_digest for r in old.records}!=expected_live:
        raise ValueError('sequence entering state differs from live original records')
    return newly


def _role_checked(checked,work,step):
    manifest=derive_step_manifest(checked['manifest'],checked['manifest_path'],step)
    path=work/'manifests'/('initial.json' if step==-1 else f'step-{step:04d}.json')
    reference=_write_bound(path,manifest)
    evidence=checked['inventory_evidence']
    if evidence is not None: evidence=dict(evidence,sequence_step=step)
    plan=dict(checked['plan'])
    return dict(checked,plan=plan,manifest=manifest,manifest_path=path,
        manifest_sha256=reference['sha256'],source_sha256=checked['plan']['source_sha256'],
        inventory_evidence=evidence,execution_mode=checked['plan']['execution_mode'],
        target_manifest_sha256=checked['plan']['target_manifest_sha256'],
        budget_config={'protocol_path':str(checked['protocol_path']),
            'protocol_sha256':checked['protocol_sha256'],'phase':manifest['phase']}
            if manifest['phase']!='software_test' or 'software_test' in checked['protocol'].get('resources',{}).get('phase_cpu_hour_caps',{}) else None)


def _row_complete(row):
    return row.get('status') in ('complete','pending_verification') and type(row.get('complete_wall_time_ns')) is int and row['complete_wall_time_ns']>0


def _not_started():
    return {'status':'not_started','failure':{'kind':'not_started'},'complete_wall_time_ns':None}


def _pair(reference):
    return {k:reference[k] for k in ('path','sha256')}


def _model_hash(row):
    return row.get('common_model_sha256') or row.get('model_reference',{}).get('sha256')


def _commit_lineage(root,checked,index,state,model,retained,previous,verified_roles):
    state=_pair(state)
    identity={'schema':'measured-sequence-commit-identity-v1','sequence_sha256':checked['plan_sha256'],
        'step_index':index,'predecessor_result_sha256':None if previous is None else previous['sha256']}
    store=RunStore(root,identity); saved=store.completed()
    record={'schema':'measured-sequence-state-commit-v1','status':'complete','outcome':'complete',
        'sequence_sha256':checked['plan_sha256'],'target_manifest_sha256':checked['plan']['target_manifest_sha256'],
        'step_index':index,'state_reference':state,'model_reference':model,'retained_ids':retained,
        'predecessor_result_reference':previous,'verification_rows':verified_roles}
    if saved is None:
        store.claim()
        try:
            store.write_artifact('binding.json',canonical_json(record));saved=store.finish(record)
        finally:store.close()
    else:
        for key,value in record.items():
            if saved.get(key)!=value:raise ValueError('saved measured sequence lineage differs')
    _reference(state);_reference(model)
    return {'path':str(store.root/'result.json'),'sha256':digest(canonical_json(saved))}


def _lifetime(preparation,steps):
    result={}
    for system in ('repair','indexed_fresh','model_only_fresh'):
        prep=preparation['model_only_fresh' if system=='model_only_fresh' else 'repair']
        rows=[step['methods'][system] for step in steps]
        initial=prep.get('complete_wall_time_ns') if _row_complete(prep) else None
        times=[r['complete_wall_time_ns'] for r in rows if _row_complete(r)]
        complete=initial is not None and len(times)==len(rows) and all(step['status']=='complete' for step in steps)
        result[system]={'complete':complete,'preparation_wall_ns':initial,
            'request_wall_ns':sum(times) if len(times)==len(rows) else None,
            'observed_completed_transaction_wall_ns':(initial or 0)+sum(times),
            'total_wall_ns':initial+sum(times) if complete else None,
            'planned_requests':len(rows),'completed_requests':len(times),
            'observed_attempt_wall_ns':sum(row.get('wall_time_ns',0) or 0 for row in [prep,*rows]),
            'all_attempt_costs_known':complete,
            'preparation_shared_with':'repair' if system=='indexed_fresh' else
                                      'indexed_fresh' if system=='repair' else None}
    return result


def _verify_rows(result):
    from .measured_comparison import verify_role
    for row in result['preparation'].values():
        if row.get('timing_receipt_path'):
            verify_role(row,expected_target=result['target_manifest_sha256'])
    for step in result['steps']:
        for row in [*step['methods'].values(),step.get('quality',{})]:
            if row.get('timing_receipt_path'):
                verify_role(row,expected_target=result['target_manifest_sha256'])
    previous=result.get('initial_commit')
    if previous is not None:
        predecessor=_lineage_record(previous)
        if predecessor['step_index']!=-1 or predecessor['sequence_sha256']!=result['plan_sha256']:
            raise ValueError('initial measured sequence lineage differs')
    for step in result['steps']:
        if step['status']!='complete':break
        commit=_lineage_record(step['commit_reference'])
        if (commit['predecessor_result_reference']!=previous or commit['step_index']!=step['step_index'] or
            commit['sequence_sha256']!=result['plan_sha256'] or
            commit['state_reference']!=_pair(step['methods']['repair']['state_reference']) or
            step['predecessor_result_sha256']!=previous['sha256'] or
            step['predecessor_state_sha256']!=_lineage_record(previous)['state_reference']['sha256']):
            raise ValueError('measured sequence predecessor chain differs')
        hashes={_model_hash(row) for row in step['methods'].values()}
        states={step['methods'][role]['state_reference']['sha256'] for role in ('repair','indexed_fresh','direct_fresh')}
        if len(hashes)!=1 or None in hashes or len(states)!=1:
            raise ValueError('measured sequence outputs differ from fresh oracle')
        previous=step['commit_reference']
    if result['lifetime']!=_lifetime(result['preparation'],result['steps']):
        raise ValueError('measured sequence lifetime accounting differs')


def _verify_slot(row,role,slot,step,plan,identity,manifest,work,preceding=None):
    if not row.get('timing_receipt_path'):
        if row!=_not_started() and row!={'status':'not_requested'}:
            raise ValueError('unmeasured sequence role has invented fields')
        return
    from .measured_comparison import verify_role_slot
    expected_manifest=derive_step_manifest(manifest,Path(identity['manifest_path']),step)
    manifest_path=work/'manifests'/('initial.json' if step==-1 else f'step-{step:04d}.json')
    verify_role_slot(row,root=slot,plan_sha256=identity['plan_sha256'],
        manifest_path=manifest_path,manifest_sha256=digest(canonical_json(expected_manifest)),role=role)
    if manifest_path.read_bytes()!=canonical_json(expected_manifest):
        raise ValueError('sequence slot manifest differs from frozen schedule')
    if (row.get('role')!=role or row.get('execution_mode')!=plan['execution_mode'] or
        row['measured_manifest_reference']['path']!=str(slot/'requests'/(role+'-measured.json')) or
        row['request_reference']['path']!=str(slot/'requests'/(role+'.json'))):
        raise ValueError('sequence row belongs to another planned role slot')
    measured,_=_reference(row['measured_manifest_reference'])
    request,_=_reference(row['request_reference'])
    if (measured['identity']['plan_sha256']!=identity['plan_sha256'] or
        measured['identity']['role']!=role or measured['limits']!=plan['worker_limits'] or
        measured['source_sha256']!=plan['source_sha256'] or
        measured['input_sha256'].get(str(manifest_path))!=digest(canonical_json(expected_manifest)) or
        measured['input_sha256'].get(identity['plan_path'])!=identity['plan_sha256'] or
        measured['input_sha256'].get(expected_manifest['protocol']['path'])!=identity['protocol_sha256']):
        raise ValueError('sequence role observation differs from planned inputs')
    if role!='model_only_fresh':
        if request.get('manifest_path')!=str(manifest_path) or request.get('plan_sha256')!=identity['plan_sha256']:
            raise ValueError('sequence leaf request differs from planned slot')
        if role in ('repair','indexed_fresh'):
            if preceding is None or request.get('original_state')!=_pair(preceding['state_reference']):
                raise ValueError('sequence leaf uses a different predecessor state')
            reference={'path':preceding['child_receipt_path'],'sha256':preceding['child_receipt_sha256']}
            context=request.get('sequence_context',{})
            if context.get('predecessor_child_reference')!=reference or context.get('step_index')!=step:
                raise ValueError('sequence leaf uses a different predecessor child receipt')
        elif role=='direct_fresh' and (request.get('original_state') is not None or request.get('sequence_context') is not None):
            raise ValueError('direct fresh must not depend on predecessor state')


def verify_measured_sequence_archive(output):
    root=Path(output).absolute();identity,_=_read_json(root/'identity.json')
    result=read_completed(root,identity)
    if result is None: raise ValueError('measured sequence is not durably sealed')
    if result.get('schema')!='calibration-measured-sequence-v1':raise ValueError('unsupported measured sequence result')
    plan_raw=(root/result['attempt']/'plan.json').read_bytes()
    if digest(plan_raw)!=result['plan_sha256']:raise ValueError('sequence saved plan differs')
    plan=strict_json(plan_raw);_validate_plan_payload(plan)
    original,original_raw=_read_json(Path(identity['manifest_path']))
    if digest(original_raw)!=identity['manifest_sha256'] or sequence_manifest_binding(original)!=plan['manifest_binding_sha256']:
        raise ValueError('sequence original manifest changed')
    _verify_slot(result['preparation']['repair'],'setup',root/'work'/'preparation',-1,plan,identity,original,root/'work')
    _verify_slot(result['preparation']['model_only_fresh'],'model_only_fresh',root/'work'/'preparation',-1,plan,identity,original,root/'work')
    preceding=result['preparation']['repair']
    schedule=plan['manifest_payload']['requests'];removed=[]
    if len(schedule)!=len(result['steps']):raise ValueError('sequence planned steps changed')
    for index,(planned,step) in enumerate(zip(schedule,result['steps'])):
        for role,row in step['methods'].items():
            _verify_slot(row,role,root/'work'/'steps'/f'step-{index:04d}',index,plan,identity,original,root/'work',preceding)
        if step.get('quality',{}).get('timing_receipt_path'):
            _verify_slot(step['quality'],'quality',root/'work'/'steps'/f'step-{index:04d}',index,plan,identity,original,root/'work')
        if step['status']=='complete':preceding=step['methods']['repair']
        removed+=planned['deleted_ids']
        if (step['request_id']!=planned['request_id'] or step['newly_deleted_ids']!=planned['deleted_ids'] or
            step['cumulative_deleted_ids']!=removed or set(step['methods'])!=set(METHODS)):
            raise ValueError('sequence result differs from planned request provenance')
    if result['archive_snapshot']!=_snapshot(root/'work'):
        raise ValueError('measured sequence nested archive changed')
    _verify_rows(result)
    return result


def run_measured_sequence(plan_path,output,*,validate_only=False,inventory_path=None,inventory_run_id=None):
    from .measured_comparison import invoke_role
    checked=validate_measured_sequence_plan(plan_path,execute=not validate_only,
        inventory_path=inventory_path,inventory_run_id=inventory_run_id)
    if validate_only:return {'status':'validated','plan_sha256':checked['plan_sha256']}
    identity={'schema':'measured-sequence-identity-v1','plan_sha256':checked['plan_sha256'],
        'manifest_sha256':checked['manifest_sha256'],'protocol_sha256':checked['protocol_sha256'],
        'plan_path':str(checked['plan_path']),'manifest_path':str(checked['manifest_path']),
        'inventory':checked['inventory_evidence']}
    store=RunStore(output,identity);previous=store.completed()
    if previous is not None:return verify_measured_sequence_archive(output)
    store.claim();work=store.root/'work';work.mkdir(exist_ok=True)
    schedule=checked['manifest']['requests'];deleted=[]
    result={'schema':'calibration-measured-sequence-v1','status':'running','outcome':'failed',
        'plan_sha256':checked['plan_sha256'],'target_manifest_sha256':checked['plan']['target_manifest_sha256'],
        'source_sha256':checked['plan']['source_sha256'],'protocol_sha256':checked['protocol_sha256'],
        'metadata':{k:checked['manifest'][k] for k in ('sequence_id','root_id','configuration_id','repeat_index','phase')},
        'measurement_boundary':BOUNDARY,'execution_mode':checked['plan']['execution_mode'],
        'preparation':{'repair':_not_started(),'model_only_fresh':_not_started()},
        'steps':[],'quality_policy':checked['plan']['quality'],'research_verification_wall_ns':0,
        'clock_exclusions':'observer final receipts; sequence scheduling, lineage commits, research equality/quality; identical for all systems',
        'storage_contract':'trusted archive retains predecessors; live returned state only'}
    for i,item in enumerate(schedule):
        deleted+=item['deleted_ids']
        result['steps'].append({'step_index':i,'request_id':item['request_id'],'newly_deleted_ids':item['deleted_ids'],
            'cumulative_deleted_ids':list(deleted),'status':'not_started','methods':{m:_not_started() for m in METHODS},
            'quality':_not_started() if checked['plan']['quality']=='heldout_nll' else {'status':'not_requested'}})
    try:
        store.write_artifact('plan.json',canonical_json(checked['plan']))
        initial_checked=_role_checked(checked,work,-1)
        for role in checked['plan']['preparation_order']:
            key='repair' if role=='setup' else role
            result['preparation'][key]=invoke_role(initial_checked,work/'preparation',role)
            store.write_status(result)
        prep=result['preparation']; state=prep['repair'].get('state_reference');commit=None
        if (all(_row_complete(row) for row in prep.values()) and
                _model_hash(prep['repair'])==_model_hash(prep['model_only_fresh'])):
            for row in prep.values():row.update(status='complete',exact_model_equal=True)
            commit=_commit_lineage(work/'commits'/'initial',checked,-1,state,
                prep['repair']['model_reference'],checked['original_record_ids'],None,prep)
            result['initial_commit']=commit
        else:
            result['failure']={'kind':'preparation_failed_or_model_mismatch'}
        removed=[]
        for step in result['steps']:
            if commit is None:break
            index=step['step_index'];entering=state
            step.update(status='running',predecessor_state_sha256=entering['sha256'],predecessor_result_sha256=commit['sha256'])
            context={'plan_path':str(checked['plan_path']),'sequence_sha256':checked['plan_sha256'],
                'step_index':index,'previously_deleted_ids':list(removed),'newly_deleted_ids':step['newly_deleted_ids'],
                'predecessor_child_reference':{
                    'path':(prep['repair'] if index==0 else result['steps'][index-1]['methods']['repair'])['child_receipt_path'],
                    'sha256':(prep['repair'] if index==0 else result['steps'][index-1]['methods']['repair'])['child_receipt_sha256']}}
            role_checked=_role_checked(checked,work,index)
            for role in checked['plan']['method_order']:
                step['methods'][role]=invoke_role(role_checked,work/'steps'/f'step-{index:04d}',role,
                    original_state=entering if role in ('repair','indexed_fresh') else None,
                    sequence_context=context if role in ('repair','indexed_fresh') else None)
                store.write_status(result)
            start=time.perf_counter_ns()
            rows=step['methods'];hashes={_model_hash(row) for row in rows.values()}
            state_hashes={rows[role].get('state_reference',{}).get('sha256') for role in ('repair','indexed_fresh','direct_fresh')}
            valid=all(_row_complete(row) for row in rows.values()) and len(hashes)==1 and None not in hashes and len(state_hashes)==1 and None not in state_hashes
            step['exact_model_equal']=valid;step['exact_state_equal']=valid
            result['research_verification_wall_ns']+=time.perf_counter_ns()-start
            if not valid:
                step.update(status='failed',failure={'kind':'role_failed_or_exactness_mismatch'})
                result['failure']={'kind':'step_failed','step_index':index};break
            for role,row in rows.items():
                row.update(status='complete',exact_model_equal=True,exact_state_equal=None if role=='model_only_fresh' else True)
            removed+=step['newly_deleted_ids'];state=rows['repair']['state_reference']
            retained=[rid for rid in checked['original_record_ids'] if rid not in set(removed)]
            commit=_commit_lineage(work/'commits'/f'step-{index:04d}',checked,index,state,
                rows['repair']['model_reference'],retained,commit,rows)
            step.update(status='complete',commit_reference=commit,retained_ids=retained)
            if checked['plan']['quality']=='heldout_nll':
                step['quality']=invoke_role(role_checked,work/'steps'/f'step-{index:04d}', 'quality',
                    original_state=prep['repair']['state_reference'], quality_states={
                        'original':prep['repair']['state_reference'],
                        'direct_fresh':rows['direct_fresh']['state_reference'],'repair':state})
            store.write_status(result)
        if all(step['status']=='complete' and step['quality']['status'] in ('complete','not_requested')
               for step in result['steps']):result['outcome']='complete'
    except BaseException as exc:
        for step in result['steps']:
            if step['status']=='running':step.update(status='failed',failure={'kind':'controller_error'})
        result['failure']={'kind':'controller_error','type':type(exc).__name__,'message':str(exc)}
        if isinstance(exc,(KeyboardInterrupt,SystemExit)):
            result['status']='interrupted';store.write_status(result);raise
    finally:
        if result['status']!='interrupted':
            result.update(status='complete',lifetime=_lifetime(result['preparation'],result['steps']),archive_snapshot=_snapshot(work))
            result['controller_completion_means']='archive sealed; inspect outcome and every planned role'
            try:
                store.write_artifact('lineage.json',canonical_json(result['steps']))
                result=store.finish(result)
            finally:store.close()
        else:store.close()
    return result


def run_measured_sequence_campaign(path,output,*,validate_only=False):
    checked=validate_measured_sequence_campaign_files(path,execute=not validate_only)
    if validate_only:return {'status':'validated','planned_sequences':len(checked['checked'])}
    identity={'schema':'measured-sequence-campaign-identity-v1','inventory_sha256':checked['inventory_sha256'],
        'protocol_sha256':checked['protocol_sha256'],'source_sha256':checked['source_sha256']}
    store=RunStore(output,identity);saved=store.completed()
    if saved is not None:
        for row in saved['runs']:
            root=store.root/'runs'/row['run_id']
            if row.get('archive_snapshot') is not None and _snapshot(root)!=row['archive_snapshot']:
                raise ValueError('measured campaign nested sequence archive changed')
            if row.get('result_sha256') is not None:
                child=verify_measured_sequence_archive(root)
                if digest(canonical_json(child))!=row['result_sha256']:raise ValueError('measured campaign sequence result changed')
        return saved
    store.claim()
    rows=[{'run_id':item['entry']['run_id'],'status':'not_started','failure':{'kind':'not_started'}} for item in checked['checked']]
    result={'schema':'measured-sequence-campaign-result-v1','status':'running','outcome':'failed','runs':rows}
    try:
        store.write_artifact('inventory.json',canonical_json(checked['inventory']))
        for item,row in zip(checked['checked'],rows):
            run_id=row['run_id'];root=store.root/'runs'/run_id
            try:
                child=run_measured_sequence(item['plan_path'],root,
                    inventory_path=checked['inventory_path'],inventory_run_id=run_id)
                row.clear();row.update(run_id=run_id,status=child['outcome'],result_sha256=digest(canonical_json(child)),
                    result_path='runs/'+run_id+'/result.json',archive_snapshot=_snapshot(root))
            except BaseException as exc:
                row.update(status='failed',failure={'kind':'controller_error','type':type(exc).__name__,'message':str(exc)},
                    archive_snapshot=_snapshot(root) if root.is_dir() else None)
                if isinstance(exc,(KeyboardInterrupt,SystemExit)):
                    store.write_status(result);raise
            store.write_status(result)
        result.update(status='complete',outcome='complete' if all(r['status']=='complete' for r in rows) else 'failed')
        store.write_artifact('runs.json',canonical_json(rows));return store.finish(result)
    finally:store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--campaign',action='store_true');parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--inventory',type=Path);parser.add_argument('--inventory-run-id')
    args=parser.parse_args()
    result=run_measured_sequence_campaign(args.plan,args.output,validate_only=args.validate_only) if args.campaign else run_measured_sequence(
        args.plan,args.output,validate_only=args.validate_only,inventory_path=args.inventory,inventory_run_id=args.inventory_run_id)
    print(canonical_json(result).decode())
    return 0 if result.get('outcome','complete')=='complete' else 1
