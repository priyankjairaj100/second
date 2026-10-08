"""Admitted complete transactions for the fixed-feature minimal-state target."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.experiment_inventory import source_hashes
from src.run_store import atomic_write, canonical_json, digest
from src.transaction_timing import verify_command_admission

METHODS = ('prepare', 'direct_fresh', 'model_only_fresh', 'repair', 'indexed_fresh')
ORIGINAL_IDS = ('wikitext2:train:article-row-27113', 'wikitext2:train:article-row-5326')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def select_records(plan, payload):
    """Validate frozen two-record membership before loading any model."""
    require(plan.get('method') in METHODS, 'unsupported V23 method')
    require(type(plan.get('use_candidates')) is bool, 'use_candidates must be Boolean')
    require(plan.get('phase', 'feasibility') == 'feasibility', 'V23 requires feasibility admission')
    original = payload.get('records') if type(payload) is dict else None
    require(type(original) is list and len(original) == 2, 'V23 requires exactly two original records')
    require(all(type(r) is dict and set(r) == {'id', 'tokens'} for r in original), 'invalid source record fields')
    require(tuple(r['id'] for r in original) == ORIGINAL_IDS, 'original record IDs or order differ')
    require(all(type(r['tokens']) is list and len(r['tokens']) == 16
        and all(type(t) is int and 0 <= t < 2**64 for t in r['tokens']) for r in original),
        'V23 requires sixteen unsigned token IDs per original record')
    if plan['method'] == 'prepare':
        wanted, deleted = ORIGINAL_IDS, ()
        require(not plan['use_candidates'], 'original preparation has no prior model proposals')
    else:
        wanted, deleted = ORIGINAL_IDS[1:], ORIGINAL_IDS[:1]
        if plan['method'] == 'direct_fresh':
            require(not plan['use_candidates'], 'direct fresh has no prior model proposals')
    require(type(plan.get('record_ids')) is list and tuple(plan['record_ids']) == wanted,
            'selected record IDs differ from the registered mode')
    require(type(plan.get('deleted_ids')) is list and tuple(plan['deleted_ids']) == deleted,
            'deletion IDs differ from the registered mode')
    return tuple(dict(id=r['id'], tokens=list(r['tokens'])) for r in original if r['id'] in wanted)


def required_inputs(plan):
    expected = {'records', 'config', 'weights'}
    if plan['method'] in ('repair', 'indexed_fresh'):
        expected |= {'prior_state', 'prior_progress', 'prior_receipt', 'prior_plan'}
    elif plan['method'] == 'model_only_fresh' and plan['use_candidates']:
        expected |= {'prior_model', 'prior_progress', 'prior_receipt', 'prior_plan'}
    return expected


def validate_generation(plan, prior_plan, progress, receipt, prior_plan_sha256):
    require(progress.get('status') == 'complete' and progress.get('complete_model') is True,
            'prior model generation is incomplete')
    require(receipt.get('status') == 'complete' and receipt.get('outcome', {}).get('status') == 'complete'
        and receipt['outcome'].get('returncode') == 0
        and receipt.get('budget_debit', {}).get('state') == 'settled', 'prior worker receipt is incomplete')
    require(progress.get('plan_sha256') == prior_plan_sha256
        and receipt.get('worker_identity', {}).get('plan_sha256') == prior_plan_sha256,
        'prior generation plan bindings differ')
    require(prior_plan.get('source_sha256') == plan['source_sha256'], 'prior generation used different frozen sources')
    require(prior_plan.get('method') == 'prepare' and prior_plan.get('record_ids') == list(ORIGINAL_IDS)
        and progress.get('retained_record_ids') == list(ORIGINAL_IDS), 'prior generation is not original preparation')
    artifact_key = 'state_artifact' if plan['method'] in ('repair', 'indexed_fresh') else 'model_artifact'
    input_key = 'prior_state' if artifact_key == 'state_artifact' else 'prior_model'
    artifact = progress.get(artifact_key)
    require(type(artifact) is dict and artifact.get('sha256') == plan['inputs'][input_key]['sha256'],
            'prior artifact differs from generation receipt')
    if artifact_key == 'state_artifact':
        require(progress.get('complete_state') is True, 'prior complete state is missing')
    return artifact


def software_checks():
    """Run small plan/provenance fixtures. This never loads or executes a model."""
    import copy
    payload = {'records':[{'id':rid, 'tokens':[0]*16} for rid in ORIGINAL_IDS]}
    prepare = dict(method='prepare', use_candidates=False, record_ids=list(ORIGINAL_IDS), deleted_ids=[])
    checks = 0
    require(len(select_records(prepare, payload)) == 2, 'prepare fixture failed')
    checks += 1
    for method in METHODS[1:]:
        plan = dict(method=method, use_candidates=False, record_ids=list(ORIGINAL_IDS[1:]),
                    deleted_ids=list(ORIGINAL_IDS[:1]))
        require(select_records(plan, payload)[0]['id'] == ORIGINAL_IDS[1], 'retained fixture failed')
        checks += 1

    def rejects(call):
        nonlocal checks
        try:
            call()
        except ValueError:
            checks += 1
        else:
            raise AssertionError('invalid software fixture was accepted')

    reversed_payload = {'records':list(reversed(payload['records']))}
    rejects(lambda:select_records(prepare, reversed_payload))
    invalid_token = copy.deepcopy(payload)
    invalid_token['records'][0]['tokens'][0] = True
    rejects(lambda:select_records(prepare, invalid_token))
    rejects(lambda:select_records(dict(prepare, use_candidates=True), payload))
    rejects(lambda:select_records(dict(prepare, deleted_ids=[ORIGINAL_IDS[0]]), payload))
    cold = dict(method='model_only_fresh', use_candidates=False)
    warm = dict(cold, use_candidates=True)
    require(required_inputs(cold) == {'records', 'config', 'weights'}, 'cold access fixture failed')
    require('prior_model' in required_inputs(warm) and 'prior_state' not in required_inputs(warm),
            'warm model-only access fixture failed')
    checks += 2
    plan = dict(method='repair', source_sha256={'file':'f'*64}, inputs={'prior_state':{'sha256':'a'*64}})
    old_plan = dict(method='prepare', source_sha256=plan['source_sha256'], record_ids=list(ORIGINAL_IDS))
    progress = dict(status='complete', complete_model=True, complete_state=True, plan_sha256='b'*64,
        retained_record_ids=list(ORIGINAL_IDS), state_artifact={'sha256':'a'*64})
    receipt = dict(status='complete', outcome={'status':'complete','returncode':0},
        budget_debit={'state':'settled'}, worker_identity={'plan_sha256':'b'*64})
    validate_generation(plan, old_plan, progress, receipt, 'b'*64)
    checks += 1
    rejects(lambda:validate_generation(plan, old_plan, progress, receipt, 'c'*64))
    rejects(lambda:validate_generation(plan, dict(old_plan, source_sha256={}), progress, receipt, 'b'*64))
    rejects(lambda:validate_generation(plan, old_plan, progress, dict(receipt, budget_debit={'state':'reserved'}), 'b'*64))
    rejects(lambda:validate_generation(plan, old_plan, dict(progress, state_artifact={'sha256':'c'*64}), receipt, 'b'*64))
    return dict(scope='software fixtures only; no model execution', checks=checks, passed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path, nargs='?')
    parser.add_argument('--software-checks', action='store_true')
    args = parser.parse_args()
    if args.software_checks:
        require(args.plan is None, 'software checks accept no research plan')
        print(json.dumps(software_checks()))
        return
    require(args.plan is not None, 'a research plan is required')
    start = time.perf_counter_ns()
    raw = args.plan.read_bytes()
    plan = json.loads(raw)
    root = Path(__file__).resolve().parents[1]
    require(source_hashes(root) == plan['source_sha256'], 'source binding mismatch')
    verify_command_admission(plan['protocol_sha256'], plan.get('phase', 'feasibility'),
        [sys.executable, str(Path(__file__).resolve()), str(args.plan.absolute())])
    output = Path(plan['output'])
    require(not any((output/name).exists() for name in ('progress.json', 'model.bin', 'state.bin')),
            'cannot overwrite an existing worker result')
    output.mkdir(parents=True, exist_ok=True)
    result = dict(schema='fixed-feature-complete-transaction-v23', status='running',
        method=plan['method'], plan_sha256=digest(raw), phases=[], state_family='fixed_anchor_calibration_v1',
        storage_schema='source_local_exact_factors_v1', solver_backend='native_ball',
        use_candidates=plan['use_candidates'], confirmation=False, scientific_promotion=False,
        repair_speed_evidence=False, numerical_target='fixed nearest-anchor features; not sequential calibration',
        outer_clock_scope='worker body from plan read through output verification; final progress commit and exit excluded',
        primary_latency='outer controller transaction; external worker receipt wall time is the secondary clock')

    def save(phase, **details):
        result['phases'].append(dict(phase=phase, elapsed_ns=time.perf_counter_ns()-start, **details))
        result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json', canonical_json(result))
        print(json.dumps(result['phases'][-1]), flush=True)

    def read(name, cap=512*2**20):
        path = Path(plan['inputs'][name]['path'])
        require(path.stat().st_size <= cap, 'input exceeds declared worker read cap: '+name)
        value = path.read_bytes()
        require(digest(value) == plan['inputs'][name]['sha256'], 'input changed during loading: '+name)
        return value

    try:
        save('input_validation_started')
        require(type(plan['inputs']) is dict and set(plan['inputs']) == required_inputs(plan),
                'worker inputs differ from mode requirements')
        for name, entry in plan['inputs'].items():
            require(type(entry) is dict and set(entry) == {'path', 'sha256'}, 'invalid input binding')
            with Path(entry['path']).open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            require(actual == entry['sha256'], 'input changed: '+name)
        records = select_records(plan, json.loads(read('records', 2**20)))
        result.update(original_record_ids=list(ORIGINAL_IDS), retained_record_ids=[r['id'] for r in records],
                      deleted_record_ids=list(plan['deleted_ids']))
        checkpoint = Path(plan['checkpoint']).resolve()
        require(Path(plan['inputs']['config']['path']).resolve() == checkpoint/'config.json'
            and Path(plan['inputs']['weights']['path']).resolve() == checkpoint/'model.safetensors',
            'checkpoint path differs from bound input files')
        prior_progress = prior_artifact = None
        if 'prior_plan' in plan['inputs']:
            prior_raw = read('prior_plan', 8*2**20)
            prior_progress = json.loads(read('prior_progress', 8*2**20))
            prior_receipt = json.loads(read('prior_receipt', 2**20))
            prior_artifact = validate_generation(plan, json.loads(prior_raw), prior_progress,
                                                 prior_receipt, digest(prior_raw))
            result['prior_generation_plan_sha256'] = digest(prior_raw)
            result['prior_generation_receipt_sha256'] = plan['inputs']['prior_receipt']['sha256']
        save('inputs_verified')
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        from src.dyadic_row_target import build_dyadic_row_target
        from src.fixed_anchor_service import FixedAnchorService, serialize as serialize_state, parse as parse_state
        from src.fixed_factor_state import FixedFactorState
        from src.compact_state import CompactState, serialize as serialize_model, parse as parse_model
        from src.compact_service import model_digest
        save('checkpoint_load_started')
        loaded = load_gpt2_checkpoint(checkpoint, identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256'] == {
            'config.json':plan['inputs']['config']['sha256'],
            'model.safetensors':plan['inputs']['weights']['sha256']}, 'loaded checkpoint provenance differs')
        decoder = CertifiedDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
        base = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=32, group_count=1))
        service = FixedAnchorService(decoder, base, state_backend='factors', solver_backend='native_ball',
            use_candidates=plan['use_candidates'], progress=lambda row:save('stage_complete', stage_metrics=row))
        require(service.target.digest != base.digest, 'fixed and sequential target identities collide')
        atomic_write(output/'fixed-target.json', canonical_json(service.target.payload()))
        atomic_write(output/'base-target.json', canonical_json(base.payload()))
        atomic_write(output/'evaluator.json', canonical_json(decoder.kernel_manifest))
        result.update(fixed_target_sha256=service.target.digest, base_target_sha256=base.digest,
                      evaluator_id=decoder.evaluator_id)
        save('targets_loaded')
        arguments = dict(method='direct_fresh' if plan['method'] == 'prepare' else plan['method'])
        if prior_progress is not None:
            require(prior_progress['fixed_target_sha256'] == service.target.digest
                and prior_progress['base_target_sha256'] == base.digest, 'prior numerical targets differ')
        if plan['method'] in ('repair', 'indexed_fresh'):
            save('prior_state_load_started')
            prior_raw = read('prior_state')
            require(len(prior_raw) == prior_artifact['bytes'], 'prior state length differs')
            prior = parse_state(prior_raw, expected_sha256=prior_artifact['sha256'])
            require(type(prior) is FixedFactorState, 'prior does not use minimal fixed-factor storage')
            require(prior.record_ids == ORIGINAL_IDS, 'prior state membership differs')
            arguments.update(prior=prior, deleted_ids=plan['deleted_ids'])
            save('prior_state_loaded', bytes=len(prior_raw))
            del prior_raw
        elif plan['method'] == 'model_only_fresh' and plan['use_candidates']:
            save('prior_model_load_started')
            prior_raw = read('prior_model')
            require(len(prior_raw) == prior_artifact['bytes'], 'prior model length differs')
            seed = parse_model(prior_raw, expected_sha256=prior_artifact['sha256'])
            require(not seed.factors and seed.target_sha256 == service.target.digest,
                    'warm model-only seed has factors or a different target')
            arguments['initial_model'] = seed
            save('prior_model_loaded', bytes=len(prior_raw))
            del prior_raw
        save('service_started')
        outcome = service.run(records, **arguments)
        result['diagnostics'] = outcome.diagnostics
        result['stage_count'] = len(outcome.stages)
        result['stage_ids'] = [stage.stage_id for stage in outcome.stages]
        result['model_code_elements'] = sum(stage.rows*stage.columns for stage in outcome.stages)
        result['model_packed_code_bytes'] = sum(len(stage.packed_indices) for stage in outcome.stages)
        require(result['stage_ids'] == list(decoder.stage_ids), 'incomplete model stage output')
        result['model_sha256'] = model_digest(outcome.stages)
        save('service_complete')
        save('model_write_started')
        model_raw = serialize_model(CompactState(service.target.digest, outcome.stages, ()))
        model_check = parse_model(model_raw, expected_sha256=digest(model_raw))
        require(model_check.stages == outcome.stages and not model_check.factors, 'model roundtrip differs')
        atomic_write(output/'model.bin', model_raw)
        require(digest((output/'model.bin').read_bytes()) == digest(model_raw), 'written model bytes differ')
        result['model_artifact'] = dict(file='model.bin', bytes=len(model_raw), sha256=digest(model_raw))
        save('model_write_complete', bytes=len(model_raw))
        del model_raw, model_check
        if outcome.state is not None:
            save('state_write_started')
            require(type(outcome.state) is FixedFactorState, 'unexpected output state representation')
            state_raw = serialize_state(outcome.state)
            checked = parse_state(state_raw, expected_sha256=digest(state_raw))
            require(serialize_state(checked) == state_raw, 'complete state canonical roundtrip differs')
            require(checked.stages == outcome.stages and checked.record_ids == tuple(r['id'] for r in records),
                    'complete state model or membership differs')
            atomic_write(output/'state.bin', state_raw)
            require(digest((output/'state.bin').read_bytes()) == digest(state_raw), 'written state bytes differ')
            result['state_artifact'] = dict(file='state.bin', bytes=len(state_raw), sha256=digest(state_raw))
            result['committed_record_ids'] = list(checked.record_ids)
            result['state_factor_bytes'] = sum(len(block.binary64) for leaf in checked.anchors for block in leaf.blocks)
            save('state_write_complete', bytes=len(state_raw))
            del state_raw, checked
        require((outcome.state is None) == (plan['method'] == 'model_only_fresh'), 'output contract differs')
        result.update(status='complete', complete_model=True, complete_state=outcome.state is not None,
                      worker_transaction_elapsed_ns=time.perf_counter_ns()-start)
        save('complete')
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        save('failed')
        raise


if __name__ == '__main__':
    main()
