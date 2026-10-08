"""Registered complete-model transactions using the shared ordered finite decoder.

This worker requires live exact-command phase admission. It never launches
other trials. It records output hashes without presupposing an oracle model.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.experiment_inventory import source_hashes
from src.run_store import atomic_write, canonical_json, digest, strict_json
from src.transaction_timing import verify_command_admission

SCHEMA = 'ordered-complete-service-transaction-v30'
METHODS = ('direct_fresh','repair','indexed_fresh','model_only_fresh')
CAPS = dict(records=16*2**20,config=2**20,weights=2*2**30,
            prior_state=2*2**30,preparation_completion=64*2**20)


def require(condition,message):
    if not condition:
        raise ValueError(message)


def _sha(value,name):
    require(type(value) is str and len(value) == 64
        and all(c in '0123456789abcdef' for c in value),name+' must be a lowercase SHA256')
    return value


def required_inputs(method):
    require(method in METHODS,'unsupported ordered complete-service method')
    return {'records','config','weights'} | (
        {'prior_state','preparation_completion'} if method in ('repair','indexed_fresh') else set())


def _ids(value,name):
    require(type(value) is list and all(type(x) is str and x and '\x00' not in x for x in value),
            name+' must contain nonempty string IDs')
    require(value == sorted(set(value)),name+' must be sorted and unique')
    return tuple(value)


def validate_policy(plan):
    from src.adaptive_calibration_v30 import AdaptiveBudget
    required_inputs(plan.get('method'))
    require(plan.get('phase','feasibility') == 'feasibility','worker requires feasibility admission')
    require(plan.get('use_candidates') is False,'prior-model proposals must be disabled')
    require(plan.get('solver_backend') in ('auto','token','primal'),'unsupported point route')
    policy = plan.get('solver_budget')
    require(type(policy) is dict and set(policy) == {
        'max_workspace_bytes','max_work_units','max_refinement_coordinates'},'solver budget fields differ')
    budget = AdaptiveBudget(**policy)
    require(type(plan.get('max_point_work_units')) is int and plan['max_point_work_units'] > 0,
            'max_point_work_units must be a positive integer')
    require(type(plan.get('original_token_count')) is int and plan['original_token_count'] > 0,
            'original_token_count must be a positive integer')
    if 'expected_target' in plan and plan['expected_target'] is not None:
        _sha(plan['expected_target'],'expected_target')
    for key in ('expected_model_sha256','expected_state_sha256'):
        if key in plan and plan[key] is not None:
            _sha(plan[key],key)
    return budget


def select_records(plan,payload):
    """Bind original membership and retained selection without model access."""
    validate_policy(plan)
    require(type(payload) is dict and set(payload) == {'records'},'record payload fields differ')
    original = payload['records']
    require(type(original) is list and original,'at least one original record is required')
    for row in original:
        require(type(row) is dict and set(row) == {'id','tokens'},'record fields differ')
        require(type(row['id']) is str and row['id'] and '\x00' not in row['id'],'invalid record ID')
        tokens = row['tokens']
        require(type(tokens) is list and tokens and all(type(token) is int and 0 <= token < 2**64
            for token in tokens),'tokens require nonempty unsigned integer lists')
    all_ids = tuple(row['id'] for row in original)
    require(all_ids == tuple(sorted(set(all_ids))),'original records must use unique sorted IDs')
    require(sum(len(row['tokens']) for row in original) == plan['original_token_count'],
            'normalization count differs from complete original token count')
    retained_ids = _ids(plan.get('record_ids'),'record_ids')
    deleted_ids = _ids(plan.get('deleted_ids'),'deleted_ids')
    require(set(deleted_ids) <= set(all_ids),'deletion contains an unknown source')
    require(set(retained_ids) == set(all_ids)-set(deleted_ids),'retained membership differs from deletion')
    if plan['method'] == 'direct_fresh':
        require(not deleted_ids and retained_ids == all_ids,'preparation must include all original sources')
    retained = tuple(dict(id=row['id'],tokens=list(row['tokens'])) for row in original
                     if row['id'] in set(retained_ids))
    return tuple(dict(id=row['id'],tokens=list(row['tokens'])) for row in original),retained


def validate_preparation(plan,completion,original):
    """Check the bound trusted preparation receipt before parsing its state."""
    require(type(completion) is dict and completion.get('schema') == SCHEMA,'preparation schema differs')
    from src.ordered_fixed_service_v30 import ordered_preparer_binding
    require(completion.get('preparer_sha256') == ordered_preparer_binding(),
            'preparation uses a different feature preparer')
    implementation = completion.get('decoder_implementation_manifest')
    require(type(implementation) is dict
        and completion.get('decoder_implementation_sha256') == digest(canonical_json(implementation)),
        'preparation implementation manifest binding differs')
    require(completion.get('status') == 'complete' and completion.get('method') == 'direct_fresh',
            'prior state requires completed original preparation')
    for key in ('complete_model','complete_state','model_roundtrip_exact','state_roundtrip_canonical'):
        require(completion.get(key) is True,'preparation verification missing: '+key)
    require(completion.get('use_candidates') is False and completion.get('confirmation') is False
        and completion.get('scientific_promotion') is False,'preparation policy flags differ')
    require(completion.get('max_point_work_units') == plan['max_point_work_units'],
            'preparation request work limit differs')
    require(completion.get('source_sha256') == plan['source_sha256'],'preparation source bindings differ')
    require(completion.get('original_token_count') == plan['original_token_count'],'preparation normalization differs')
    require(completion.get('solver_backend') == plan['solver_backend']
        and completion.get('solver_budget') == plan['solver_budget'],'preparation solver policy differs')
    original_ids = [row['id'] for row in original]
    require(completion.get('original_record_ids') == original_ids
        and completion.get('retained_record_ids') == original_ids
        and completion.get('committed_record_ids') == original_ids
        and completion.get('deleted_record_ids') == [],'preparation membership differs')
    require(completion.get('original_records_sha256') == digest(canonical_json({'records':list(original)})),
            'preparation source tokens differ')
    require(completion.get('records_input_sha256') == plan['inputs']['records']['sha256'],
            'preparation record file differs')
    require(completion.get('checkpoint_files_sha256') == {
        name:plan['inputs'][key]['sha256'] for name,key in (
            ('config.json','config'),('model.safetensors','weights'))},'preparation checkpoint differs')
    require(completion.get('stage_count') == 24 and type(completion.get('stage_ids')) is list
        and len(completion['stage_ids']) == 24 and len(set(completion['stage_ids'])) == 24,
        'preparation is not a complete 24-stage model')
    require(type(completion.get('worker_transaction_elapsed_ns')) is int
        and completion['worker_transaction_elapsed_ns'] >= 0,'preparation timer is missing')
    state = completion.get('state_artifact')
    model = completion.get('model_artifact')
    for name,artifact in (('state',state),('model',model)):
        require(type(artifact) is dict and set(artifact) == {'file','bytes','sha256'},
                'invalid preparation '+name+' artifact')
        _sha(artifact['sha256'],name+' artifact')
        require(artifact['file'] == name+'.bin' and type(artifact['bytes']) is int and artifact['bytes'] > 0,
                'invalid preparation '+name+' size or filename')
    require(completion.get('artifacts') == {'model':model,'state':state},
            'preparation artifact mapping differs from named fields')
    require(state['sha256'] == plan['inputs']['prior_state']['sha256'],'prior state artifact binding differs')
    _sha(completion.get('fixed_target_sha256'),'preparation fixed target')
    _sha(completion.get('base_target_sha256'),'preparation base target')
    if plan.get('expected_target') is not None:
        require(completion['fixed_target_sha256'] == plan['expected_target'],'preparation target differs')
    return state


def preflight_stages(stages,retained_tokens,*,budget,route,max_point_work_units=48_000_000_000):
    """Admit every stage before source preparation or neural evaluation."""
    from src.adaptive_calibration_v30 import assess_routes,CalibrationWorkRefused
    require(type(max_point_work_units) is int and max_point_work_units > 0,
            'max_point_work_units must be a positive integer')
    reports = []
    total = 0
    for stage in stages:
        report = assess_routes(len(stage.weights),stage.width,retained_tokens,budget=budget)
        selected = report['selected'] if route == 'auto' else route
        report = dict(report,stage_id=stage.stage_id,requested_route=route,selected=selected)
        reports.append(report)
        if selected is None or not report['routes'][selected]['admitted']:
            raise CalibrationWorkRefused('complete model point-route preflight refused a stage',
                dict(stages=reports,all_stages_admitted=False,neural_work_started=False,
                     reserved_work_units=total,request_cap=max_point_work_units))
        total += report['routes'][selected]['work_units']
    if total > max_point_work_units:
        raise CalibrationWorkRefused('complete model exceeds cumulative point-work cap',
            dict(stages=reports,all_stages_admitted=True,request_admitted=False,neural_work_started=False,
                 reserved_work_units=total,request_cap=max_point_work_units))
    return dict(stages=reports,all_stages_admitted=True,request_admitted=True,neural_work_started=False,
                reserved_work_units=total,request_cap=max_point_work_units,
                note='structural admission only; no memory-fit or wall-time guarantee')


def _safe_path(value):
    require(type(value) is str and Path(value).is_absolute(),'input/output path must be absolute')
    path = Path(value)
    require(not path.is_symlink() and not any(parent.is_symlink() for parent in path.parents),
            'input/output paths must not contain symlinks')
    return path


def validate_inputs(plan):
    require(type(plan.get('inputs')) is dict and set(plan['inputs']) == required_inputs(plan['method']),
            'worker input access differs from method requirements')
    for name,entry in plan['inputs'].items():
        require(type(entry) is dict and set(entry) == {'path','sha256'},'invalid input binding')
        _sha(entry['sha256'],name+' input')
        path = _safe_path(entry['path'])
        require(path.is_file() and path.stat().st_size <= CAPS[name],'input missing or exceeds cap: '+name)
        with path.open('rb') as stream:
            require(hashlib.file_digest(stream,'sha256').hexdigest() == entry['sha256'],'input changed: '+name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path)
    args = parser.parse_args()
    started = time.perf_counter_ns()
    raw = args.plan.read_bytes()
    plan = strict_json(raw)
    require(type(plan) is dict,'worker plan must be an object')
    require(source_hashes(ROOT) == plan.get('source_sha256'),'source binding mismatch')
    verify_command_admission(plan['protocol_sha256'],plan.get('phase','feasibility'),
        [sys.executable,str(Path(__file__).resolve()),str(args.plan.absolute())])
    output = _safe_path(plan['output'])
    require(not output.exists() or output.is_dir() and not any(output.iterdir()),
            'cannot overwrite an existing worker output')
    output.mkdir(parents=True,exist_ok=True)
    result = dict(schema=SCHEMA,status='running',method=plan.get('method'),plan_sha256=digest(raw),
        phases=[],source_sha256=plan['source_sha256'],confirmation=False,scientific_promotion=False,
        use_candidates=False,numerical_target='fixed nearest-anchor features; not sequential calibration',
        worker_clock_scope='plan read through complete output verification; final progress/completion commits and exit excluded',
        primary_latency='outer controller transaction; worker and service clocks are nested diagnostics',
        cross_method_model_agreement_checked=False,
        expected_model_sha256=plan.get('expected_model_sha256'),
        expected_model_agreement=None,artifacts={},
        state_identity_scope='new ordered preparer binding; no equality to historical state is claimed',
        exactness_scope='certified mathematical target; independent cross-method comparison belongs to the controller')

    def save(phase,**details):
        result['phases'].append(dict(phase=phase,elapsed_ns=time.perf_counter_ns()-started,**details))
        result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json',canonical_json(result))
        print(json.dumps(result['phases'][-1],allow_nan=False),flush=True)

    def read(name):
        entry = plan['inputs'][name]
        path = _safe_path(entry['path'])
        require(path.stat().st_size <= CAPS[name],'input exceeds cap during read: '+name)
        payload = path.read_bytes()
        require(digest(payload) == entry['sha256'],'input changed during read: '+name)
        return payload

    try:
        save('input_validation_started')
        budget = validate_policy(plan)
        validate_inputs(plan)
        original,records = select_records(plan,strict_json(read('records')))
        checkpoint = _safe_path(plan['checkpoint']).resolve()
        require(Path(plan['inputs']['config']['path']).resolve() == checkpoint/'config.json'
            and Path(plan['inputs']['weights']['path']).resolve() == checkpoint/'model.safetensors',
            'checkpoint differs from bound input files')
        checkpoint_hashes = {name:plan['inputs'][key]['sha256'] for name,key in (
            ('config.json','config'),('model.safetensors','weights'))}
        result.update(solver_backend=plan['solver_backend'],solver_budget=asdict(budget),
            max_point_work_units=plan['max_point_work_units'],
            original_token_count=plan['original_token_count'],original_record_ids=[row['id'] for row in original],
            retained_record_ids=[row['id'] for row in records],deleted_record_ids=list(plan['deleted_ids']),
            original_record_lengths=[len(row['tokens']) for row in original],
            retained_record_lengths=[len(row['tokens']) for row in records],
            retained_token_count=sum(len(row['tokens']) for row in records),
            original_records_sha256=digest(canonical_json({'records':list(original)})),
            records_input_sha256=plan['inputs']['records']['sha256'],checkpoint_files_sha256=checkpoint_hashes,
            max_neural_stage_record_pairs=24*len(records),
            inputs=plan['inputs'],runtime=dict(python=sys.version,executable=sys.executable,
                affinity_cpus=sorted(os.sched_getaffinity(0)),
                thread_environment={name:os.environ.get(name) for name in (
                    'OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}))
        atomic_write(output/'plan.json',raw)
        preparation = None
        prior_artifact = None
        if plan['method'] in ('repair','indexed_fresh'):
            completion_raw = read('preparation_completion')
            preparation = strict_json(completion_raw)
            prior_artifact = validate_preparation(plan,preparation,original)
            result['preparation_completion_sha256'] = digest(completion_raw)
            result['external_preparation_worker_elapsed_ns'] = preparation['worker_transaction_elapsed_ns']
            result['external_preparation_cost_scope'] = 'prior lifetime cost; not a new request observation or speedup credit'
        save('inputs_verified')
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
        from src.target_manifest import TargetRecipe
        from src.dyadic_row_target import build_dyadic_row_target
        from src.ordered_fixed_service_v30 import OrderedFixedAnchorService,ordered_preparer_binding
        from src.ordered_lossless_service_v30 import OrderedLosslessService
        from src.fixed_lossless_state_v29 import LosslessFactorState,serialize as encode_state,parse as decode_state
        from src.compact_state import CompactState,serialize as encode_model,parse as decode_model
        from src.compact_service import model_digest
        save('checkpoint_load_started')
        loaded = load_gpt2_checkpoint(checkpoint,identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256'] == checkpoint_hashes,'loaded checkpoint provenance differs')
        decoder = OrderedFiniteDecoder(loaded.decoder,primitive_backend='mpfr_enclosure')
        result.update(decoder_implementation_manifest=decoder.implementation_manifest,
            decoder_implementation_sha256=digest(canonical_json(decoder.implementation_manifest)),
            preparer_sha256=ordered_preparer_binding())
        require(len(decoder.stage_ids) == 24,'this registered worker requires a complete 24-stage decoder')
        for row in original:
            decoder.base._tokens(row['tokens'])
        base = build_dyadic_row_target(decoder,TargetRecipe(original_token_count=plan['original_token_count'],group_count=1))
        save('point_route_preflight_started')
        result['resource_admission'] = preflight_stages(base.stages,result['retained_token_count'],
            budget=budget,route=plan['solver_backend'],max_point_work_units=plan['max_point_work_units'])
        save('point_route_preflight_complete')
        callback = lambda row:save('stage_complete',stage_metrics=row)
        service = (OrderedFixedAnchorService(decoder,base,solver_backend=plan['solver_backend'],
            coefficient_budget=budget,state_backend='factors',use_candidates=False,progress=callback,
            max_point_work_units=plan['max_point_work_units'])
            if plan['method'] == 'model_only_fresh' else
            OrderedLosslessService(decoder,base,solver_backend=plan['solver_backend'],
                coefficient_budget=budget,progress=callback,max_point_work_units=plan['max_point_work_units']))
        require(service.target.digest != base.digest,'fixed and sequential target identities collide')
        if plan.get('expected_target') is not None:
            require(service.target.digest == plan['expected_target'],'fixed target differs from registration')
        if preparation is not None:
            require(preparation['decoder_implementation_manifest'] == decoder.implementation_manifest,
                    'preparation decoder implementation differs')
            require(preparation['fixed_target_sha256'] == service.target.digest
                and preparation['base_target_sha256'] == base.digest,'prior targets differ from current request')
            require(preparation['stage_ids'] == list(decoder.stage_ids),'prior calibrated stage IDs differ')
        for name,payload in (('fixed-target',service.target.payload()),('base-target',base.payload()),
                             ('evaluator',decoder.kernel_manifest),
                             ('decoder-implementation',decoder.implementation_manifest)):
            atomic_write(output/(name+'.json'),canonical_json(payload))
        result.update(fixed_target_sha256=service.target.digest,base_target_sha256=base.digest,
            evaluator_id=decoder.evaluator_id,target_recipe=base.recipe.payload())
        save('targets_loaded')
        arguments = dict(method=plan['method'])
        if prior_artifact is not None:
            save('prior_state_load_started')
            prior_raw = read('prior_state')
            require(len(prior_raw) == prior_artifact['bytes'],'prior state byte count differs')
            prior = decode_state(prior_raw,expected_sha256=prior_artifact['sha256'])
            require(type(prior) is LosslessFactorState and prior.record_ids == tuple(row['id'] for row in original),
                    'prior state membership differs')
            require(prior.preparer_sha256 == result['preparer_sha256'],
                    'prior state feature preparer differs')
            require(prior.target_sha256 == service.target.digest and prior.anchor_target_sha256 == base.digest,
                    'prior state targets differ')
            require(all(leaf.tokens == tuple(row['tokens']) for leaf,row in zip(prior.anchors,original)),
                    'prior source tokens differ')
            prior_model_raw = encode_model(CompactState(service.target.digest,prior.stages,()))
            require(digest(prior_model_raw) == preparation['model_artifact']['sha256']
                and len(prior_model_raw) == preparation['model_artifact']['bytes'],
                'prior state model differs from preparation model artifact')
            arguments.update(prior=prior,deleted_ids=plan['deleted_ids'])
            result['prior_model_binding_verified'] = True
            save('prior_state_loaded',bytes=len(prior_raw))
            del prior_raw,prior_model_raw
        save('service_started')
        outcome = service.run(records,**arguments)
        require(outcome.diagnostics.get('decoder_implementation_manifest') == decoder.implementation_manifest
            and outcome.diagnostics.get('preparer_sha256') == result['preparer_sha256'],
            'service implementation binding differs')
        result.update(diagnostics=outcome.diagnostics,stage_count=len(outcome.stages),
            stage_ids=[stage.stage_id for stage in outcome.stages],model_sha256=model_digest(outcome.stages),
            model_code_elements=sum(stage.rows*stage.columns for stage in outcome.stages),
            model_packed_code_bytes=sum(len(stage.packed_indices) for stage in outcome.stages))
        require(result['stage_count'] == 24 and result['stage_ids'] == list(decoder.stage_ids),
                'complete calibrated model verification failed')
        require((outcome.state is None) == (plan['method'] == 'model_only_fresh'),'output contract differs')
        if plan['method'] in ('repair','indexed_fresh'):
            require(outcome.diagnostics['neural_stage_record_pairs'] == 0,'indexed method unexpectedly evaluated neural stages')
        else:
            actual_neural = outcome.diagnostics.get('neural_stage_record_pairs',0)
            if plan['method'] == 'model_only_fresh':
                actual_neural += outcome.diagnostics.get('anchor_preparation_stage_record_pairs',0)
            require(actual_neural == 24*len(records),'fresh neural traversal count differs')
        save('service_complete')
        save('model_write_started')
        model_raw = encode_model(CompactState(service.target.digest,outcome.stages,()))
        model_hash = digest(model_raw)
        checked_model = decode_model(model_raw,expected_sha256=model_hash)
        require(checked_model.target_sha256 == service.target.digest and checked_model.stages == outcome.stages
            and not checked_model.factors and encode_model(checked_model) == model_raw,'model canonical roundtrip differs')
        if plan.get('expected_model_sha256') is not None:
            result['expected_model_agreement'] = model_hash == plan['expected_model_sha256']
            require(result['expected_model_agreement'],'registered model hash differs')
        atomic_write(output/'model.bin',model_raw)
        require(digest((output/'model.bin').read_bytes()) == model_hash,'written model bytes differ')
        result.update(model_artifact=dict(file='model.bin',bytes=len(model_raw),sha256=model_hash),
                      model_roundtrip_exact=True)
        result['artifacts']['model'] = result['model_artifact']
        save('model_write_complete',bytes=len(model_raw),sha256=model_hash)
        if outcome.state is not None:
            save('state_write_started')
            require(type(outcome.state) is LosslessFactorState,'unexpected output state type')
            state_raw = encode_state(outcome.state)
            state_hash = digest(state_raw)
            checked = decode_state(state_raw,expected_sha256=state_hash)
            require(checked.preparer_sha256 == result['preparer_sha256'],
                    'committed state feature preparer differs')
            require(encode_state(checked) == state_raw and checked.stages == outcome.stages
                and checked.record_ids == tuple(row['id'] for row in records),'state canonical roundtrip differs')
            require(all(leaf.tokens == tuple(row['tokens']) for leaf,row in zip(checked.anchors,records)),
                    'committed source tokens differ')
            if plan.get('expected_state_sha256') is not None:
                require(state_hash == plan['expected_state_sha256'],'registered state hash differs')
            atomic_write(output/'state.bin',state_raw)
            require(digest((output/'state.bin').read_bytes()) == state_hash,'written state bytes differ')
            result.update(state_artifact=dict(file='state.bin',bytes=len(state_raw),sha256=state_hash),
                committed_record_ids=list(checked.record_ids),state_roundtrip_canonical=True)
            result['artifacts']['state'] = result['state_artifact']
            save('state_write_complete',bytes=len(state_raw),sha256=state_hash)
        require(source_hashes(ROOT) == plan['source_sha256'],'bound source changed during transaction')
        result.update(status='complete',complete_model=True,complete_state=outcome.state is not None,
                      worker_transaction_elapsed_ns=time.perf_counter_ns()-started)
        save('complete')
        terminal = canonical_json(result)
        with (output/'completion.json').open('xb') as stream:
            stream.write(terminal)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(output,os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        print(json.dumps(dict(phase='terminal_record_committed',sha256=digest(terminal))),flush=True)
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc))
        if hasattr(exc,'diagnostics'):
            result['failure_diagnostics'] = exc.diagnostics
        if hasattr(exc,'service_diagnostics'):
            result['failure_service_diagnostics'] = exc.service_diagnostics
        if hasattr(exc,'admission'):
            result['failure_admission'] = exc.admission
        save('failed')
        raise


if __name__ == '__main__':
    main()
