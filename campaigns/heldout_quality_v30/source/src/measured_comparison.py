"""Matched single-request transactions with separately charged research checks.

Every method executes in a fresh limited process under the same enclosing
observer boundary. The model-only control returns no deletion index. Complete
canonical equality applies only to the three canonical-state methods.
"""
from __future__ import annotations

from pathlib import Path
import sys
import time

from .experiment_campaign import _phase_caps
from .experiment_inventory import manifest_binding, manifest_payload
from .experiment_runner import _read_json, _referenced_json, _local, _sha, _integer, _text, _failure
from .isolated_comparison import isolated_source_hashes
from .run_store import RunStore, atomic_write, canonical_json, digest, strict_json, read_completed
from .transaction_timing import BOUNDARY, CACHE_MODES, measure_command, transaction_source_hashes
from .worker_control import WorkerLimits

METHODS = ('model_only_fresh','repair','indexed_fresh','direct_fresh')
STATE_METHODS = ('repair','indexed_fresh','direct_fresh')
CACHE_MODE = 'measured_method_transactions_os_cache_uncontrolled'
SCHEMA = 'calibration-measured-comparison-v1'


def measured_source_hashes(repository=None):
    return transaction_source_hashes(repository)


def build_measured_plan(*, manifest_path, manifest, target_manifest_sha256, worker_limits,
                        sources, method_order, quality=False, execution_mode='clean'):
    if type(quality) is not bool or execution_mode not in ('clean','diagnostic'):
        raise ValueError('invalid measured quality or execution policy')
    if type(method_order) is not list or sorted(method_order) != sorted(METHODS):
        raise ValueError('measured plan requires each of four methods exactly once')
    return {'schema':'calibration-measured-plan-v1','manifest_path':manifest_path,
        'manifest_payload':manifest_payload(manifest),'manifest_binding_sha256':manifest_binding(manifest),
        'target_manifest_sha256':_sha(target_manifest_sha256),
        'worker_limits':WorkerLimits.from_payload(worker_limits).payload(),'source_sha256':sources,
        'method_order':list(method_order),'quality':'heldout_nll' if quality else 'none',
        'execution_mode':execution_mode}


def validate_measured_plan(path, *, execute=False, inventory_path=None, inventory_run_id=None):
    path=Path(path).absolute(); plan,raw=_read_json(path)
    fields={'schema','manifest_path','manifest_payload','manifest_binding_sha256','target_manifest_sha256',
            'worker_limits','source_sha256','method_order','quality','execution_mode'}
    if type(plan) is not dict or set(plan)!=fields or plan['schema']!='calibration-measured-plan-v1':
        raise ValueError('invalid measured plan schema or fields')
    if raw!=canonical_json(plan):
        raise ValueError('measured plan requires canonical JSON')
    if plan['source_sha256']!=measured_source_hashes():
        raise ValueError('measured sources differ from frozen plan')
    if plan['quality'] not in ('none','heldout_nll') or plan['execution_mode'] not in ('clean','diagnostic'):
        raise ValueError('invalid measured execution policy')
    if type(plan['method_order']) is not list or sorted(plan['method_order'])!=sorted(METHODS):
        raise ValueError('measured plan requires all four methods once')
    _sha(plan['target_manifest_sha256'])
    bound=plan['manifest_payload']
    if manifest_payload(bound)!=bound or manifest_binding(bound)!=_sha(plan['manifest_binding_sha256']):
        raise ValueError('invalid normalized measured manifest binding')
    manifest_path=_local(path.parent,plan['manifest_path']); manifest,manifest_raw=_read_json(manifest_path)
    if manifest_binding(manifest)!=plan['manifest_binding_sha256']:
        raise ValueError('measured run manifest differs from frozen plan')
    for name in ('root_id','request_id','configuration_id'):
        _text(manifest.get(name),name)
    _integer(manifest.get('repeat_index'),'repeat_index')
    if manifest.get('phase') not in ('software_test','feasibility','development','confirmation'):
        raise ValueError('invalid measured phase')
    if sorted(manifest.get('method_order',[]))!=sorted(STATE_METHODS):
        raise ValueError('standard manifest requires all canonical-state methods')
    protocol,protocol_raw=_referenced_json(manifest_path.parent,manifest['protocol'])
    protocol_path=_local(manifest_path.parent,manifest['protocol']['path'])
    if execute and manifest['phase']!='software_test' and 'experiments_paused' in str(protocol.get('status','')):
        raise ValueError('protocol keeps research experiments paused')
    if (inventory_path is None)!=(inventory_run_id is None):
        raise ValueError('measured inventory requires both path and run ID')
    if execute and manifest['phase']=='confirmation' and inventory_path is None:
        raise ValueError('measured confirmation requires frozen inventory evidence')
    limits=WorkerLimits.from_payload(plan['worker_limits']); limits.check_host()
    caps=_phase_caps({'entries':[{'phase':manifest['phase']}]*(5+int(plan['quality']!='none'))},protocol,limits)
    evidence=None
    if inventory_path is not None:
        from .measured_inventory import verify_measured_membership
        verified,item=verify_measured_membership(inventory_path,inventory_run_id,path,execute=execute)
        if (item['manifest_sha256']!=digest(manifest_raw)
                or item['entry']['measured_plan_sha256']!=digest(raw)
                or item['entry']['target_manifest_sha256']!=plan['target_manifest_sha256']):
            raise ValueError('measured inventory bindings differ')
        caps=verified['phase_cpu_seconds']
        evidence={'kind':'measured','path':str(verified['inventory_path']),
            'sha256':verified['inventory_sha256'],'run_id':inventory_run_id,'plan_path':str(path)}
    explicit_caps=protocol.get('resources',{}).get('phase_cpu_hour_caps',{})
    budget=None if manifest['phase']=='software_test' and 'software_test' not in explicit_caps else {
        'protocol_path':str(protocol_path),'protocol_sha256':digest(protocol_raw),'phase':manifest['phase']}
    return {'plan':plan,'raw':raw,'plan_path':path,'plan_sha256':digest(raw),
        'manifest':manifest,'manifest_path':manifest_path,'manifest_sha256':digest(manifest_raw),
        'protocol':protocol,'protocol_path':protocol_path,'protocol_sha256':digest(protocol_raw),
        'limits':limits,'phase_cpu_seconds':caps,'inventory_evidence':evidence,'budget_config':budget,
        'source_sha256':plan['source_sha256'],'execution_mode':plan['execution_mode'],
        'target_manifest_sha256':plan['target_manifest_sha256']}


def _write_immutable(path,raw):
    path=Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('symbolic measured artifact path')
    if path.exists():
        if not path.is_file() or path.read_bytes()!=raw:
            raise ValueError('measured artifact changed across attempts')
    else:
        atomic_write(path,raw)
    return {'path':str(path.absolute()),'sha256':digest(raw),'bytes':len(raw)}


def _ref(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents):
        raise ValueError('missing or symbolic measured artifact')
    raw=path.read_bytes()
    return {'path':str(path.absolute()),'sha256':digest(raw),'bytes':len(raw)}


def _read_ref(reference):
    if type(reference) is not dict or not {'path','sha256'}<=set(reference):
        raise ValueError('invalid measured artifact reference')
    actual=_ref(reference['path'])
    if actual['sha256']!=reference['sha256'] or ('bytes' in reference and actual['bytes']!=reference['bytes']):
        raise ValueError('measured artifact hash differs')
    return Path(reference['path']).read_bytes()


def _sealed(root):
    root=Path(root)
    identity,_=_read_json(root/'identity.json')
    record=read_completed(root,identity)
    if record is None:
        raise ValueError('required measured receipt is not sealed')
    return record


def _common_model(raw,target):
    payload=strict_json(raw)
    if raw!=canonical_json(payload):
        raise ValueError('model artifact is not canonical JSON')
    schema=payload.get('schema')
    if schema=='quantized-target-model-v1':
        if set(payload)!={'schema','target_manifest_sha256','stages'} or payload['target_manifest_sha256']!=target:
            raise ValueError('model-only artifact target differs')
    elif schema=='quantized-stage-model-v1':
        if set(payload)!={'schema','manifest','stages'}:
            raise ValueError('canonical-state model fields differ')
        _sha(payload['manifest'])
    else:
        raise ValueError('unsupported measured model schema')
    stages=payload['stages']
    if type(stages) is not list or not stages:
        raise ValueError('model requires stage outputs')
    names=[]
    for stage in stages:
        if type(stage) is not dict or set(stage)!={'stage_id','codes'}:
            raise ValueError('invalid stage output')
        _text(stage['stage_id'],'stage_id'); names.append(stage['stage_id'])
        if type(stage['codes']) is not list or not stage['codes']:
            raise ValueError('stage codes must be a nonempty matrix')
        width=None
        for row in stage['codes']:
            if type(row) is not list or not row or (width is not None and len(row)!=width):
                raise ValueError('stage code matrix is not rectangular')
            width=len(row)
            for pair in row:
                if (type(pair) is not list or len(pair)!=2 or any(type(x) is not int for x in pair)
                        or pair[1]<=0):
                    raise ValueError('stage codes require exact rational pairs')
                from fractions import Fraction
                q=Fraction(*pair)
                if [q.numerator,q.denominator]!=pair:
                    raise ValueError('stage code rational is not canonical')
    if len(set(names))!=len(names):
        raise ValueError('model stage identities repeat')
    return canonical_json({'schema':'quantized-target-model-v1','target_manifest_sha256':target,'stages':stages})


def _instrumentation(child,mode):
    state=child.get('instrumentation_state',child.get('instrumentation'))
    if child.get('execution_mode',state.get('mode') if isinstance(state,dict) else None)!=mode or type(state) is not dict or state.get('mode')!=mode:
        raise ValueError('child lacks its frozen instrumentation contract')
    flags=('python_profiler_active','python_trace_active','allocation_tracing_active',
           'global_monitoring_active','monitoring_tools_allocated','detailed_service_telemetry')
    if (state.get('schema')!='calibration-instrumentation-v1' or
            any(type(state.get(k)) is not bool for k in flags) or
            (mode=='clean' and any(state[k] for k in flags)) or
            state.get('required_arithmetic_counters_retained') is not True):
        raise ValueError('invalid clean instrumentation evidence')
    return state


def _extract_row(role,observer,child,child_root,root,target,mode, *, write=True):
    row={'role':role,'status':'pending_verification','output_contract':observer['output_contract'],
         'execution_mode':mode,'wall_time_ns':observer['observed_wall_ns'],
         'complete_wall_time_ns':observer['complete_transaction_wall_ns'],
         'timing_eligible':observer['eligible_fresh_transaction_latency'],
         'exact_model_equal':None,'exact_state_equal':None,
         'state_equality_applicable':role in STATE_METHODS,
         'target_manifest_sha256':target,'service_boundary':BOUNDARY,
         'profiler_active':mode!='clean'}
    row['observer_instrumentation_state']=_instrumentation(observer,mode)
    if observer.get('instrumentation_state_end')!=observer['instrumentation_state']:
        raise ValueError('observer instrumentation changed across the measured boundary')
    row['observer_attempt']=observer['attempt']
    row['worker_outcome']=observer.get('worker_outcome')
    row['worker_resource_usage']=observer.get('worker_resource_usage')
    if observer['outcome']['status']!='complete' or not observer['eligible_fresh_transaction_latency']:
        row.update(status='failed',complete_wall_time_ns=None,
                   failure={'kind':'incomplete_transaction','observer_outcome':observer['outcome']})
        return row
    if child is None:
        raise ValueError('successful observation lacks child receipt')
    state=_instrumentation(child,mode); row['instrumentation_state']=state
    child_target=child.get('target_manifest_sha256',child.get('metadata',{}).get('target_manifest_sha256'))
    if child_target!=target:
        raise ValueError('measured child has a different target')
    if role=='quality':
        row.update(status='complete',quality=child['quality'],state_equality_applicable=False)
        return row
    if role=='model_only_fresh':
        model_path=child_root/child['attempt']/'model.json'
        row['artifact']=child['model_artifact']
    else:
        stem='original' if role=='setup' else role
        model_path=child_root/child['attempt']/(stem+'-model.json')
        state_path=child_root/child['attempt']/(stem+'-state.json')
        row['state_reference']=_ref(state_path)
        row['artifact']=child['artifact']
        if row['state_reference']['sha256']!=child['artifact']['state_sha256']:
            raise ValueError('state artifact differs from child summary')
        row.update(service_manifest_sha256=child['service_manifest_sha256'],
                   chart_sha256=child['metadata']['chart_sha256'])
    row['original_model_reference']=_ref(model_path)
    expected=child['model_artifact']['sha256'] if role=='model_only_fresh' else child['artifact']['model_sha256']
    if row['original_model_reference']['sha256']!=expected:
        raise ValueError('model artifact differs from child summary')
    common=_common_model(model_path.read_bytes(),target)
    common_path=root/'verified-models'/(role+'.json')
    row['model_reference']=_write_immutable(common_path,common) if write else _ref(common_path)
    if not write and common_path.read_bytes()!=common:
        raise ValueError('common model differs from original model artifact')
    row['common_model_sha256']=digest(common)
    if role=='setup':
        row.update(status='complete',exact_model_equal=None,exact_state_equal=None)
    return row


def _extract_checked_row(role,observer,child,child_root,root,target,mode, *, write=True):
    """Retain a finished transaction whose output fails cross-layer checks."""
    try:
        return _extract_row(role,observer,child,child_root,root,target,mode,write=write)
    except (ValueError,KeyError,TypeError) as exc:
        return {'role':role,'status':'failed','output_contract':observer['output_contract'],
            'execution_mode':mode,'wall_time_ns':observer['observed_wall_ns'],
            'complete_wall_time_ns':None,'timing_eligible':False,
            'exact_model_equal':None,'exact_state_equal':None,
            'state_equality_applicable':role in STATE_METHODS,'target_manifest_sha256':target,
            'service_boundary':BOUNDARY,'profiler_active':mode!='clean',
            'observer_instrumentation_state':observer.get('instrumentation_state'),
            'observer_attempt':observer['attempt'],'worker_outcome':observer.get('worker_outcome'),
            'worker_resource_usage':observer.get('worker_resource_usage'),
            'failure':{'kind':'output_verification_failure','type':type(exc).__name__,'message':str(exc)}}


def invoke_role(checked,root,role,original_state=None,sequence_context=None,quality_states=None):
    """Run or verify one immutable measured leaf; suitable for lifetime callers."""
    if role not in (*METHODS,'setup','quality'):
        raise ValueError('unsupported measured role')
    root=Path(root).absolute(); target=checked['target_manifest_sha256']; mode=checked['execution_mode']
    if checked['source_sha256']!=measured_source_hashes():
        raise ValueError('measured role sources changed')
    transaction=root/'transactions'/role; observer_root=root/'observations'/role
    inputs={str(checked['manifest_path']):checked['manifest_sha256'],
            str(checked['protocol_path']):checked['protocol_sha256'],str(checked['plan_path']):checked['plan_sha256']}
    evidence=checked.get('inventory_evidence')
    if evidence is not None:
        inputs[evidence['path']]=evidence['sha256']
    if role=='model_only_fresh':
        from .model_fresh import model_fresh_command
        kwargs={'execution_mode':mode}
        if evidence:
            kwargs.update(inventory_path=evidence['path'],inventory_run_id=evidence['run_id'],plan_path=evidence['plan_path'])
            if 'sequence_step' in evidence:
                kwargs['sequence_step']=evidence['sequence_step']
        command=model_fresh_command(checked['manifest_path'],transaction,**kwargs)
        output_contract='model_only'
        request={'schema':'measured-model-request-v1','command':command,'target_manifest_sha256':target}
    else:
        original_state=None if original_state is None else {k:original_state[k] for k in ('path','sha256')}
        request={'schema':'isolated-child-request-v1','role':role,
            'manifest_path':str(checked['manifest_path']),'manifest_sha256':checked['manifest_sha256'],
            'source_sha256':isolated_source_hashes(),'target_manifest_sha256':target,
            'plan_sha256':checked['plan_sha256'],'output':str(transaction),'original_state':original_state,
            'execution_mode':mode}
        if evidence is not None:
            request['inventory']=dict(evidence)
        if sequence_context is not None:
            request['sequence_context']=sequence_context
        if quality_states is not None:
            request['quality_states']={name:{k:ref[k] for k in ('path','sha256')} for name,ref in quality_states.items()}
        request_path=root/'requests'/(role+'.json')
        _write_immutable(request_path,canonical_json(request))
        command=[sys.executable,'-m','src.isolated_comparison','--child',str(request_path)]
        output_contract='quality_evaluation' if role=='quality' else 'canonical_state'
    request_ref=_write_immutable(root/'requests'/(role+'.json'),canonical_json(request))
    inputs[request_ref['path']]=request_ref['sha256']
    measured={'schema':'measured-transaction-v1','command':command,'transaction_root':str(transaction),
        'cwd':str(Path(__file__).resolve().parents[1]),'cache_mode':CACHE_MODES[0],
        'output_contract':output_contract,'limits':checked['limits'].payload(),
        'source_sha256':checked['source_sha256'],'input_sha256':inputs,'budget':checked.get('budget_config'),
        'identity':{'plan_sha256':checked['plan_sha256'],'role':role,'request_sha256':request_ref['sha256']}}
    measured_ref=_write_immutable(root/'requests'/(role+'-measured.json'),canonical_json(measured))
    from .instrumentation import instrumentation_scope
    with instrumentation_scope(mode):
        observation=measure_command(command,transaction,observer_root,checked['limits'],
            identity={'measured_manifest_sha256':measured_ref['sha256'],'role':role},
            source_sha256=checked['source_sha256'],input_sha256=inputs,output_contract=output_contract,
            budget_config=checked.get('budget_config'),cwd=measured['cwd'])
    observed=observation['receipt']
    child=None
    if (transaction/'result.json').is_file():
        try:
            child=_sealed(transaction)
        except ValueError:
            if observed['outcome']['status']=='complete':
                raise
    row=_extract_checked_row(role,observed,child,transaction,root,target,mode)
    row.update(request_reference=request_ref,measured_manifest_reference=measured_ref,
        timing_receipt_path=str(observer_root/'result.json'),timing_receipt_sha256=digest((observer_root/'result.json').read_bytes()),
        child_receipt_path=str(transaction/'result.json') if (transaction/'result.json').is_file() else None,
        child_receipt_sha256=digest((transaction/'result.json').read_bytes()) if (transaction/'result.json').is_file() else None,
        observer_identity_sha256=observed['identity_sha256'])
    return row


def _row_references(role, root, observer):
    transaction=root/'transactions'/role; observer_root=root/'observations'/role
    result=transaction/'result.json'
    return {'request_reference':_ref(root/'requests'/(role+'.json')),
        'measured_manifest_reference':_ref(root/'requests'/(role+'-measured.json')),
        'timing_receipt_path':str(observer_root/'result.json'),
        'timing_receipt_sha256':digest((observer_root/'result.json').read_bytes()),
        'child_receipt_path':str(result) if result.is_file() else None,
        'child_receipt_sha256':digest(result.read_bytes()) if result.is_file() else None,
        'observer_identity_sha256':observer['identity_sha256']}


def verify_role_slot(row, *, root, plan_sha256, manifest_path, manifest_sha256, role=None):
    """Bind an original observation to one expected parent slot before reuse."""
    root=Path(root).absolute(); manifest_path=Path(manifest_path).absolute()
    role=row.get('role') if role is None else role
    if row.get('role')!=role or role not in (*METHODS,'setup','quality'):
        raise ValueError('measured observation belongs to a different parent role')
    paths={'request_reference':root/'requests'/(role+'.json'),
           'measured_manifest_reference':root/'requests'/(role+'-measured.json')}
    for key,wanted in paths.items():
        if row.get(key,{}).get('path')!=str(wanted):
            raise ValueError('measured observation belongs to a different parent slot')
    if row.get('timing_receipt_path')!=str(root/'observations'/role/'result.json') or (
            row.get('child_receipt_path') is not None and
            row['child_receipt_path']!=str(root/'transactions'/role/'result.json')):
        raise ValueError('measured receipt path differs from its parent slot')
    measured=strict_json(_read_ref(row['measured_manifest_reference']))
    request=strict_json(_read_ref(row['request_reference']))
    if (measured['identity'].get('plan_sha256')!=plan_sha256 or
            measured['identity'].get('role')!=role or
            measured['input_sha256'].get(str(manifest_path))!=manifest_sha256 or
            measured['transaction_root']!=str(root/'transactions'/role)):
        raise ValueError('measured observation plan or manifest differs from parent slot')
    if role=='model_only_fresh':
        if request.get('command')!=measured['command'] or measured['command'][2]!=str(manifest_path):
            raise ValueError('model-only command differs from parent manifest')
    elif (request.get('manifest_path')!=str(manifest_path) or request.get('manifest_sha256')!=manifest_sha256
            or request.get('plan_sha256')!=plan_sha256 or request.get('role')!=role):
        raise ValueError('measured child request differs from its parent slot')
    return row


def verify_role(row, expected_target=None):
    """Verify immutable leaf facts; caller must derive its own cross-arm equality."""
    from .transaction_timing import verify_observer_receipt
    if type(row) is not dict or row.get('role') not in (*METHODS,'setup','quality'):
        raise ValueError('invalid measured role row')
    role=row['role']; root=Path(row['measured_manifest_reference']['path']).parent.parent
    measured_raw=_read_ref(row['measured_manifest_reference']); measured=strict_json(measured_raw)
    request_raw=_read_ref(row['request_reference']); request=strict_json(request_raw)
    observer_root=root/'observations'/role; transaction=root/'transactions'/role
    observer=verify_observer_receipt(observer_root)
    identity=strict_json((observer_root/'identity.json').read_bytes())
    wanted={'measured_manifest_sha256':digest(measured_raw),'role':role}
    if identity['identity']!=wanted or measured['identity']['request_sha256']!=digest(request_raw):
        raise ValueError('measured observer request binding differs')
    for key in ('command','transaction_root','cwd','cache_mode','output_contract','source_sha256','input_sha256','budget'):
        if identity[key]!=measured[key]:
            raise ValueError('measured wrapper differs from observer: '+key)
    if measured['limits']!=identity['limits'] or measured['transaction_root']!=str(transaction):
        raise ValueError('measured role transaction path or limits differ')
    target=row['target_manifest_sha256']
    if expected_target is not None and target!=expected_target:
        raise ValueError('measured role target differs from caller')
    if request['target_manifest_sha256']!=target:
        raise ValueError('measured role request target differs')
    if role!='model_only_fresh' and (request.get('role')!=role or request.get('execution_mode')!=row['execution_mode']):
        raise ValueError('measured role identity or instrumentation differs from its request')
    child=None
    if (transaction/'result.json').is_file():
        try:
            child=_sealed(transaction)
        except ValueError:
            if observer['outcome']['status']=='complete':
                raise
    if child is not None and role!='model_only_fresh':
        if (transaction/child['attempt']/'request.json').read_bytes()!=request_raw:
            raise ValueError('child committed a different measured request')
        if child.get('plan_sha256')!=request['plan_sha256'] or child.get('manifest_sha256')!=request['manifest_sha256']:
            raise ValueError('child manifest or plan binding differs')
    expected=_extract_checked_row(role,observer,child,transaction,root,target,row['execution_mode'],write=False)
    expected.update(_row_references(role,root,observer))
    # Sequence/comparison parents own terminal status and exactness. Every other
    # field is rederived from the original observer, child, and model artifacts.
    mutable={'status','exact_model_equal','exact_state_equal','failure'}
    if {k:v for k,v in row.items() if k not in mutable}!={k:v for k,v in expected.items() if k not in mutable}:
        raise ValueError('measured role convenience fields differ from verified evidence')
    if expected['status']=='failed' and row!=expected:
        raise ValueError('failed measured transaction was promoted or altered')
    if row.get('status') not in ('pending_verification','complete','failed'):
        raise ValueError('invalid measured terminal status')
    if any(row.get(k) is not None and type(row.get(k)) is not bool for k in ('exact_model_equal','exact_state_equal')):
        raise ValueError('invalid measured equality field')
    if role=='model_only_fresh' and row.get('exact_state_equal') is not None:
        raise ValueError('model-only output has no canonical state equality contract')
    return expected


def _not_started(role,kind):
    return {'role':role,'status':'not_started','output_contract':'model_only' if role=='model_only_fresh' else
        'quality_evaluation' if role=='quality' else 'canonical_state','wall_time_ns':None,
        'complete_wall_time_ns':None,'exact_model_equal':None,'exact_state_equal':None,
        'state_equality_applicable':role in STATE_METHODS,'failure':{'kind':kind}}


def _finalize_methods(methods):
    """Recompute exactness from common codes and full canonical state bytes."""
    rows={name:dict(value) for name,value in methods.items()}
    available={name:row for name,row in rows.items() if row.get('timing_eligible') is True and
               row.get('model_reference') is not None}
    direct=available.get('direct_fresh'); plain=available.get('model_only_fresh')
    for name,row in available.items():
        row.pop('failure',None)
        if direct is None or plain is None:
            row.update(status='failed',exact_model_equal=None,exact_state_equal=None,
                       failure={'kind':'independent_oracle_unavailable'})
            continue
        model=(_read_ref(row['model_reference'])==_read_ref(direct['model_reference'])==_read_ref(plain['model_reference']))
        state=None
        if name in STATE_METHODS:
            state=(_read_ref(row['state_reference'])==_read_ref(direct['state_reference']) and
                   row['service_manifest_sha256']==direct['service_manifest_sha256'] and
                   row['chart_sha256']==direct['chart_sha256'])
        row.update(status='complete' if model and state is not False else 'failed',
                   exact_model_equal=model,exact_state_equal=state)
        if row['status']=='failed':
            row['failure']={'kind':'exact_output_mismatch'}
    return rows


def _archive_tree(root):
    from .transaction_timing import _snapshot
    return {name:_snapshot(root/name) if (root/name).is_dir() else {}
            for name in ('requests','transactions','observations','verified-models')}


def _comparison_identity(checked):
    return {'schema':'measured-comparison-identity-v1','plan_path':str(checked['plan_path']),
        'plan_sha256':checked['plan_sha256'],'manifest_sha256':checked['manifest_sha256'],
        'protocol_sha256':checked['protocol_sha256'],'source_sha256':checked['source_sha256'],
        'inventory':checked['inventory_evidence']}


def verify_measured_archive(output_root, result=None):
    """Read-only archive validation, including failed/missing planned outcomes."""
    root=Path(output_root).absolute()
    if root.is_file():
        root=root.parent
    identity=strict_json((root/'identity.json').read_bytes())
    saved=strict_json((root/'result.json').read_bytes())
    sealed=read_completed(root,identity)
    if result is not None and saved!=result:
        raise ValueError('provided measured result differs from sealed archive')
    evidence=identity.get('inventory')
    checked=validate_measured_plan(identity['plan_path'],execute=False,
        inventory_path=None if evidence is None else evidence['path'],
        inventory_run_id=None if evidence is None else evidence['run_id'])
    if identity!=_comparison_identity(checked):
        raise ValueError('measured archive identity differs from frozen inputs')
    if sealed is None:
        from .isolated_comparison import _verify_unfinished_artifacts
        from .transaction_timing import verify_observer_receipt
        _verify_unfinished_artifacts(root,saved)
        if saved.get('identity_sha256')!=digest(canonical_json(identity)):
            raise ValueError('partial measured result identity differs')
        snapshot_path=root/saved['attempt']/'partial-archive-tree.json'
        if snapshot_path.exists() and strict_json(snapshot_path.read_bytes())!=_archive_tree(root):
            raise ValueError('partial measured archive artifact tree changed')
        # A killed controller may never have saved its role row. Validate every
        # committed receipt nonetheless; no missing observation is synthesized.
        for observer in sorted((root/'observations').glob('*')) if (root/'observations').is_dir() else ():
            if (observer/'result.json').is_file():
                record=strict_json((observer/'result.json').read_bytes())
                if record.get('status')=='complete':
                    verify_observer_receipt(observer)
                else:
                    _verify_unfinished_artifacts(observer,record)
        for row in [saved.get('setup',{}),*saved.get('methods',{}).values(),saved.get('quality',{})]:
            if row.get('timing_receipt_path'):
                verify_role_slot(row,root=root,plan_sha256=checked['plan_sha256'],
                    manifest_path=checked['manifest_path'],manifest_sha256=checked['manifest_sha256'])
                verify_role(row,checked['target_manifest_sha256'])
        return saved
    snapshot=strict_json((root/saved['attempt']/'archive-tree.json').read_bytes())
    if snapshot!=_archive_tree(root):
        raise ValueError('measured archive artifact tree changed')
    payload=strict_json((root/saved['attempt']/'comparison.json').read_bytes())
    if payload!={k:v for k,v in saved.items() if k not in ('identity_sha256','attempt','artifacts')}:
        raise ValueError('measured result differs from committed comparison artifact')
    if (root/saved['attempt']/'plan.json').read_bytes()!=checked['raw']:
        raise ValueError('saved measured plan artifact differs')
    if (saved.get('schema')!=SCHEMA or saved.get('cache_mode')!=CACHE_MODE or
            saved.get('service_boundary')!=BOUNDARY or saved.get('planned_methods')!=list(METHODS) or
            set(saved.get('methods',{}))!=set(METHODS)):
        raise ValueError('invalid measured comparison contract')
    manifest=checked['manifest']
    for key in ('root_id','request_id','configuration_id','repeat_index','phase'):
        if saved[key]!=manifest[key]:
            raise ValueError('measured identity field differs: '+key)
    comparisons={'plan_sha256':checked['plan_sha256'],'measured_plan_sha256':checked['plan_sha256'],'run_manifest_sha256':checked['manifest_sha256'],
        'protocol_sha256':checked['protocol_sha256'],'source_sha256':checked['source_sha256'],
        'target_manifest_sha256':checked['target_manifest_sha256'],'execution_mode':checked['execution_mode'],
        'method_order':checked['plan']['method_order'],'inventory_evidence':checked['inventory_evidence']}
    if any(saved.get(k)!=v for k,v in comparisons.items()):
        raise ValueError('measured result input convenience fields differ')
    base={}
    for name,row in saved['methods'].items():
        if row.get('role')!=name:
            raise ValueError('measured method row belongs to another role')
        if row['status']=='not_started':
            expected=_not_started(name,'setup_unavailable')
            if row!=expected or name not in ('repair','indexed_fresh') or saved['setup']['status']=='complete':
                raise ValueError('invalid missing method outcome')
            base[name]=row
        else:
            verify_role_slot(row,root=root,plan_sha256=checked['plan_sha256'],
                manifest_path=checked['manifest_path'],manifest_sha256=checked['manifest_sha256'],role=name)
            base[name]=verify_role(row,checked['target_manifest_sha256'])
    for key in ('setup','quality'):
        row=saved[key]
        if row.get('role')!=key:
            raise ValueError('measured auxiliary row belongs to another role')
        if row['status']!='not_started':
            verify_role_slot(row,root=root,plan_sha256=checked['plan_sha256'],
                manifest_path=checked['manifest_path'],manifest_sha256=checked['manifest_sha256'],role=key)
            if verify_role(row,checked['target_manifest_sha256'])!=row:
                raise ValueError('setup or quality convenience fields differ')
    if checked['plan']['quality']=='none':
        if saved['quality']!=_not_started('quality','not_requested'):
            raise ValueError('unrequested quality outcome differs')
    elif saved['quality']['status']=='not_started':
        if saved['quality']!=_not_started('quality','state_unavailable') or (
                saved['setup'].get('state_reference') is not None and
                all(saved['methods'][n].get('state_reference') for n in ('repair','direct_fresh'))):
            raise ValueError('requested quality was omitted without a missing dependency')
    if saved['methods']!=_finalize_methods(base):
        raise ValueError('measured exactness or terminal status differs from artifacts')
    wanted='complete' if all(row['status']=='complete' for row in saved['methods'].values()) and (
        checked['plan']['quality']=='none' or saved['quality']['status']=='complete') else 'failed'
    if saved['outcome']!={'status':wanted}:
        raise ValueError('measured terminal outcome differs')
    return saved


verify_measured_comparison = verify_measured_archive
verify_measured_comparison_archive = verify_measured_archive


def run_measured_comparison(plan_path, output, *, validate_only=False, inventory_path=None, inventory_run_id=None):
    checked=validate_measured_plan(plan_path,execute=not validate_only,inventory_path=inventory_path,
                                   inventory_run_id=inventory_run_id)
    if validate_only:
        return {'schema':'measured-plan-validation-v1','status':'validated','plan_sha256':checked['plan_sha256'],
            'empirical_work_executed':False,'checkpoint_parameters_loaded':False,
            'confirmation_inventory_verified':checked['inventory_evidence'] is not None,
            'phase_cpu_seconds':checked['phase_cpu_seconds']}
    store=RunStore(output,_comparison_identity(checked)); previous=store.completed()
    if previous is not None:
        return verify_measured_archive(store.root,previous)
    if (store.root/'result.json').exists():
        verify_measured_archive(store.root)
    store.claim(); root=store.root; manifest=checked['manifest']; plan=checked['plan']
    result={key:manifest[key] for key in ('root_id','request_id','configuration_id','repeat_index','phase')}
    result.update(schema=SCHEMA,status='running',outcome={'status':'failed'},cache_mode=CACHE_MODE,
        service_boundary=BOUNDARY,planned_methods=list(METHODS),method_order=plan['method_order'],
        execution_mode=checked['execution_mode'],source_sha256=checked['source_sha256'],
        target_manifest_sha256=checked['target_manifest_sha256'],protocol_sha256=checked['protocol_sha256'],
        run_manifest_sha256=checked['manifest_sha256'],plan_sha256=checked['plan_sha256'],measured_plan_sha256=checked['plan_sha256'],
        inventory_evidence=checked['inventory_evidence'],
        methods={name:_not_started(name,'setup_unavailable') for name in METHODS},
        setup=_not_started('setup','not_started'),quality=_not_started('quality','not_requested'),
        measurement_contract={'method':'one complete fresh process including loading, required validation, outputs, child and worker commits, cleanup, observer input/output verification',
            'external':'setup, cross-method equality, common-model copies, quality evaluation, final observer and comparison receipts',
            'preparation':'setup builds canonical original state and is reported separately',
            'cache':'OS caches uncontrolled; every leaf process is fresh',
            'input_reader':'all arms parse the original calibration input before filtering deletions',
            'baseline':'model_only_fresh returns codes; canonical methods return model and deletion state',
            'clean':'optional Python diagnostics disabled; required arithmetic counters retained; native profiling unobserved'})
    interrupted=None
    try:
        store.write_artifact('plan.json',checked['raw']); store.write_status(result)
        result['setup']=invoke_role(checked,root,'setup')
        original=result['setup'].get('state_reference') if result['setup']['status']=='complete' else None
        store.write_status(result)
        for role in plan['method_order']:
            if role in ('repair','indexed_fresh') and original is None:
                continue
            result['methods'][role]=invoke_role(checked,root,role,original_state=original if role in ('repair','indexed_fresh') else None)
            store.write_status(result)
        start=time.perf_counter_ns()
        result['methods']=_finalize_methods(result['methods'])
        result['external_exact_verification_wall_ns']=time.perf_counter_ns()-start
        if plan['quality']!='none':
            needed={name:result['methods'][name].get('state_reference') for name in ('direct_fresh','repair')}
            if original is not None and all(needed.values()):
                result['quality']=invoke_role(checked,root,'quality',quality_states={'original':original,**needed})
            else:
                result['quality']=_not_started('quality','state_unavailable')
        complete=all(row['status']=='complete' for row in result['methods'].values()) and (
            plan['quality']=='none' or result['quality']['status']=='complete')
        result['outcome']={'status':'complete' if complete else 'failed'}
        result['status']='complete'
        store.write_artifact('archive-tree.json',canonical_json(_archive_tree(root)))
        store.write_artifact('comparison.json',canonical_json(result))
        return store.finish(result)
    except BaseException as exc:
        result.update(status='failed',failure=_failure(exc))
        store.write_artifact('partial-archive-tree.json',canonical_json(_archive_tree(root)))
        store.write_status(result)
        raise
    finally:
        store.close()
