"""Admitted complete compressed repair and matched cold reconstruction."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.experiment_inventory import source_hashes
from src.run_store import atomic_write, canonical_json, digest, strict_json
from src.transaction_timing import verify_command_admission

ORIGINAL_IDS = ('wikitext2:train:article-row-27113', 'wikitext2:train:article-row-5326')
EXPECTED_MODEL = 'd27c824322d0399f99a78c2b9d7e369e6b9a547085fa1cc25f92703536962927'
EXPECTED_STATE = '6504eb947c23de439f6fd96f2f6b496e606f00032a124cd92bd744a1d8d2ac36'
EXPECTED_PRIOR = '6590ee5d21954939651404f18ed252338973ee70adeec518a9e7d863b8a97ff1'
CAPS = dict(records=2**20, config=2**20, weights=512*2**20,
            prior_state=128*2**20, archive_summary=8*2**20, archive_plan=2**20)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def required_inputs(method):
    require(method in ('repair', 'model_only_fresh'), 'unsupported V28 method')
    return {'records', 'config', 'weights'} | (
        {'prior_state', 'archive_summary', 'archive_plan'} if method == 'repair' else set())


def select_records(plan, payload):
    required_inputs(plan.get('method'))
    require(plan.get('phase', 'feasibility') == 'feasibility', 'V28 requires feasibility admission')
    require(plan.get('use_candidates') is False, 'V28 requires no prior-model proposals')
    require(plan.get('record_ids') == list(ORIGINAL_IDS[1:])
        and plan.get('deleted_ids') == list(ORIGINAL_IDS[:1]), 'registered deletion differs')
    require(plan.get('expected_model_sha256') == EXPECTED_MODEL
        and plan.get('expected_state_sha256') == EXPECTED_STATE, 'expected output hashes differ')
    original = payload.get('records') if type(payload) is dict else None
    require(type(original) is list and len(original) == 2, 'two original records are required')
    require(all(type(row) is dict and set(row) == {'id', 'tokens'} for row in original), 'record fields differ')
    require(tuple(row['id'] for row in original) == ORIGINAL_IDS, 'original record order differs')
    require(all(type(row['tokens']) is list and len(row['tokens']) == 16
        and all(type(token) is int and 0 <= token < 2**64 for token in row['tokens']) for row in original),
        'each original record requires sixteen unsigned tokens')
    return original, (dict(id=original[1]['id'], tokens=list(original[1]['tokens'])),)


def validate_archive(plan, archive_plan, summary, archive_plan_hash, root):
    require(summary.get('schema') == 'compressed-state-archive-audit-v26'
        and archive_plan.get('schema') == 'compressed-state-archive-audit-plan-v26', 'archive schema differs')
    require(summary.get('status') == 'complete' and summary.get('plan_sha256') == archive_plan_hash,
            'archive is incomplete or its plan binding differs')
    for key in ('artifacts_saved', 'all_complete_models_preserved',
                'all_retained_descriptors_unchanged', 'all_state_roundtrips_canonical'):
        require(summary.get(key) is True, 'archive verification is incomplete: '+key)
    require(summary.get('bits') == archive_plan.get('bits') == [40]
        and summary.get('block_size') == archive_plan.get('block_size') == 256, 'archive codec settings differ')
    hashes = archive_plan.get('source_hashes')
    require(type(hashes) is dict and hashes and summary.get('source_hashes') == hashes,
            'archive source bindings differ')
    for name, expected in hashes.items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'unsafe archive source path')
        require(digest((root/path).read_bytes()) == expected, 'archive source changed: '+name)
    for name in ('src/fixed_compressed_state_v26.py', 'src/fixed_factor_codec_v26.py'):
        require(archive_plan.get('reviewed_source_hashes', {}).get(name) == hashes.get(name)
            and summary.get('reviewed_source_hashes', {}).get(name) == hashes.get(name),
            'archive reviewed source binding differs')
    artifact = summary['generations']['prepare-001']['precisions']['40']
    require(artifact['complete_state_sha256'] == EXPECTED_PRIOR
        == plan['inputs']['prior_state']['sha256'], 'original compressed state binding differs')
    require(type(artifact['complete_state_bytes']) is int and artifact['complete_state_bytes'] > 0
        and artifact.get('source_count') == 2, 'original compressed state size or membership differs')
    for key in ('all_source_containment_checks_passed', 'artifact_reloaded_equal',
                'canonical_roundtrip', 'complete_model_bytes_equal'):
        require(artifact.get(key) is True, 'original archive verification is incomplete: '+key)
    return artifact


def software_checks():
    """Check input contracts only. No model or research data is loaded."""
    import copy
    import tempfile
    payload = {'records': [dict(id=rid, tokens=[0]*16) for rid in ORIGINAL_IDS]}
    plan = dict(method='repair', use_candidates=False, record_ids=list(ORIGINAL_IDS[1:]),
        deleted_ids=list(ORIGINAL_IDS[:1]), expected_model_sha256=EXPECTED_MODEL, expected_state_sha256=EXPECTED_STATE)
    require(select_records(plan, payload)[1][0]['id'] == ORIGINAL_IDS[1], 'valid record fixture failed')
    require(required_inputs('model_only_fresh') == {'records', 'config', 'weights'}, 'cold access fixture failed')
    require(required_inputs('repair') == set(CAPS), 'repair access fixture failed')
    checks = 3
    bad_payload = copy.deepcopy(payload)
    bad_payload['records'][0]['tokens'][0] = True
    cases = [(dict(plan, use_candidates=True), payload), (plan, bad_payload),
             (dict(plan, deleted_ids=[]), payload), (dict(plan, expected_state_sha256='0'*64), payload),
             (dict(plan, method='indexed_fresh'), payload),
             (plan, {'records': list(reversed(payload['records']))})]
    for invalid_plan, invalid_payload in cases:
        try:
            select_records(invalid_plan, invalid_payload)
        except ValueError:
            checks += 1
        else:
            raise AssertionError('invalid software fixture was accepted')
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        (root/'src').mkdir()
        names = ('src/fixed_compressed_state_v26.py', 'src/fixed_factor_codec_v26.py')
        for name in names:
            (root/name).write_bytes(b'software provenance fixture')
        hashes = {name:digest((root/name).read_bytes()) for name in names}
        old_plan = dict(schema='compressed-state-archive-audit-plan-v26', bits=[40], block_size=256,
                        source_hashes=hashes, reviewed_source_hashes=hashes)
        artifact = dict(complete_state_sha256=EXPECTED_PRIOR, complete_state_bytes=123, source_count=2,
            all_source_containment_checks_passed=True, artifact_reloaded_equal=True,
            canonical_roundtrip=True, complete_model_bytes_equal=True)
        summary = dict(schema='compressed-state-archive-audit-v26', status='complete', plan_sha256='a'*64,
            bits=[40], block_size=256, source_hashes=hashes, reviewed_source_hashes=hashes,
            artifacts_saved=True, all_complete_models_preserved=True, all_retained_descriptors_unchanged=True,
            all_state_roundtrips_canonical=True, generations={'prepare-001':{'precisions':{'40':artifact}}})
        bound = dict(inputs={'prior_state':{'sha256':EXPECTED_PRIOR}})
        validate_archive(bound, old_plan, summary, 'a'*64, root)
        checks += 1
        mutations = (dict(summary, status='incomplete'), dict(summary, plan_sha256='b'*64),
                     dict(summary, all_state_roundtrips_canonical=False), dict(summary, reviewed_source_hashes={}))
        bad_containment = copy.deepcopy(summary)
        bad_containment['generations']['prepare-001']['precisions']['40']['all_source_containment_checks_passed'] = False
        for invalid in (*mutations, bad_containment):
            try:
                validate_archive(bound, old_plan, invalid, 'a'*64, root)
            except ValueError:
                checks += 1
            else:
                raise AssertionError('invalid archive fixture was accepted')
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
    plan = strict_json(raw)
    require(source_hashes(ROOT) == plan['source_sha256'], 'source binding mismatch')
    verify_command_admission(plan['protocol_sha256'], plan.get('phase', 'feasibility'),
        [sys.executable, str(Path(__file__).resolve()), str(args.plan.absolute())])
    output = Path(plan['output'])
    require(not output.exists() or not any(output.iterdir()), 'cannot overwrite an existing worker output')
    output.mkdir(parents=True, exist_ok=True)
    result = dict(schema='compressed-complete-transaction-v28', status='running',
        method=plan['method'], plan_sha256=digest(raw), phases=[], use_candidates=False,
        solver_backend='native_ball', certificate_backend='ball', bits=40, block_size=256,
        max_neural_stage_record_pairs=24, confirmation=False, scientific_promotion=False,
        numerical_target='fixed nearest-anchor features; not sequential calibration',
        worker_clock_scope='plan read through complete output verification; final progress commit and exit excluded',
        primary_latency='outer controller transaction; worker body and receipt clocks are secondary')

    def save(phase, **details):
        result['phases'].append(dict(phase=phase, elapsed_ns=time.perf_counter_ns()-start, **details))
        result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json', canonical_json(result))
        print(json.dumps(result['phases'][-1]), flush=True)

    def read(name):
        path = Path(plan['inputs'][name]['path'])
        require(path.stat().st_size <= CAPS[name], 'input exceeds read cap: '+name)
        value = path.read_bytes()
        require(digest(value) == plan['inputs'][name]['sha256'], 'input changed during loading: '+name)
        return value

    try:
        save('input_validation_started')
        require(type(plan['inputs']) is dict and set(plan['inputs']) == required_inputs(plan['method']),
                'worker inputs differ from method requirements')
        for name, entry in plan['inputs'].items():
            require(type(entry) is dict and set(entry) == {'path', 'sha256'}, 'invalid input binding')
            path = Path(entry['path'])
            require(path.stat().st_size <= CAPS[name], 'input exceeds read cap: '+name)
            with path.open('rb') as stream:
                require(hashlib.file_digest(stream, 'sha256').hexdigest() == entry['sha256'], 'input changed: '+name)
        original, records = select_records(plan, strict_json(read('records')))
        checkpoint = Path(plan['checkpoint']).resolve()
        require(Path(plan['inputs']['config']['path']).resolve() == checkpoint/'config.json'
            and Path(plan['inputs']['weights']['path']).resolve() == checkpoint/'model.safetensors',
            'checkpoint path differs from bound input files')
        result.update(original_record_ids=list(ORIGINAL_IDS), retained_record_ids=[row['id'] for row in records],
            deleted_record_ids=list(plan['deleted_ids']))
        artifact = None
        if plan['method'] == 'repair':
            archive_raw = read('archive_plan')
            artifact = validate_archive(plan, strict_json(archive_raw), strict_json(read('archive_summary')),
                                        digest(archive_raw), ROOT)
            result['archive_plan_sha256'] = digest(archive_raw)
            result['archive_summary_sha256'] = plan['inputs']['archive_summary']['sha256']
        save('inputs_verified')
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        from src.dyadic_row_target import build_dyadic_row_target
        from src.fixed_anchor_service import FixedAnchorService
        from src.fixed_compressed_service_v28 import FixedCompressedService
        from src.fixed_compressed_state_v26 import CompressedFactorState, serialize as encode_state, parse as decode_state
        from src.compact_state import CompactState, serialize as encode_model, parse as decode_model
        from src.compact_service import model_digest
        save('checkpoint_load_started')
        loaded = load_gpt2_checkpoint(checkpoint, identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256'] == {name:plan['inputs'][key]['sha256']
            for name, key in (('config.json', 'config'), ('model.safetensors', 'weights'))}, 'checkpoint provenance differs')
        decoder = CertifiedDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
        base = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=32, group_count=1))
        callback = lambda row:save('stage_complete', stage_metrics=row)
        service = (FixedCompressedService(decoder, base, bits=40, block_size=256, solver_backend='native_ball',
            certificate_backend='ball', max_neural_stage_record_pairs=24, progress=callback)
            if plan['method'] == 'repair' else FixedAnchorService(decoder, base, state_backend='factors',
                solver_backend='native_ball', use_candidates=False, progress=callback))
        require(service.target.digest != base.digest, 'fixed and sequential target identities collide')
        for name, payload in (('fixed-target', service.target.payload()), ('base-target', base.payload()),
                              ('evaluator', decoder.kernel_manifest)):
            atomic_write(output/(name+'.json'), canonical_json(payload))
        result.update(fixed_target_sha256=service.target.digest, base_target_sha256=base.digest,
                      evaluator_id=decoder.evaluator_id)
        save('targets_loaded')
        arguments = dict(method=plan['method'])
        if artifact is not None:
            save('prior_state_load_started')
            prior_raw = read('prior_state')
            require(len(prior_raw) == artifact['complete_state_bytes'], 'prior state size differs')
            prior = decode_state(prior_raw, expected_sha256=EXPECTED_PRIOR)
            require(type(prior) is CompressedFactorState and prior.record_ids == ORIGINAL_IDS,
                    'prior state type or membership differs')
            require(prior.target_sha256 == service.target.digest and prior.anchor_target_sha256 == base.digest,
                    'prior numerical targets differ')
            require(all(leaf.tokens == tuple(row['tokens']) for leaf, row in zip(prior.anchors, original)),
                    'prior source tokens differ')
            arguments.update(prior=prior, deleted_ids=plan['deleted_ids'])
            save('prior_state_loaded', bytes=len(prior_raw))
            del prior_raw
        save('service_started')
        outcome = service.run(records, **arguments)
        result.update(diagnostics=outcome.diagnostics, stage_count=len(outcome.stages),
            stage_ids=[stage.stage_id for stage in outcome.stages], model_sha256=model_digest(outcome.stages),
            model_code_elements=sum(stage.rows*stage.columns for stage in outcome.stages),
            model_packed_code_bytes=sum(len(stage.packed_indices) for stage in outcome.stages))
        require(result['stage_ids'] == list(decoder.stage_ids), 'incomplete calibrated model')
        require((outcome.state is None) == (plan['method'] == 'model_only_fresh'), 'output contract differs')
        save('service_complete')
        save('model_write_started')
        model_raw = encode_model(CompactState(service.target.digest, outcome.stages, ()))
        model = decode_model(model_raw, expected_sha256=plan['expected_model_sha256'])
        require(model.stages == outcome.stages and not model.factors, 'model roundtrip differs')
        atomic_write(output/'model.bin', model_raw)
        require(digest((output/'model.bin').read_bytes()) == EXPECTED_MODEL, 'written model differs from expected hash')
        result['model_artifact'] = dict(file='model.bin', bytes=len(model_raw), sha256=digest(model_raw))
        save('model_write_complete', bytes=len(model_raw))
        if outcome.state is not None:
            save('state_write_started')
            require(type(outcome.state) is CompressedFactorState, 'unexpected output state type')
            state_raw = encode_state(outcome.state)
            checked = decode_state(state_raw, expected_sha256=plan['expected_state_sha256'])
            require(encode_state(checked) == state_raw and checked.stages == outcome.stages
                and checked.record_ids == tuple(row['id'] for row in records), 'state canonical roundtrip differs')
            atomic_write(output/'state.bin', state_raw)
            require(digest((output/'state.bin').read_bytes()) == EXPECTED_STATE, 'written state differs from expected hash')
            result['state_artifact'] = dict(file='state.bin', bytes=len(state_raw), sha256=digest(state_raw))
            result['committed_record_ids'] = list(checked.record_ids)
            save('state_write_complete', bytes=len(state_raw))
        result.update(status='complete', complete_model=True, complete_state=outcome.state is not None,
                      worker_transaction_elapsed_ns=time.perf_counter_ns()-start)
        save('complete')
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        if hasattr(exc, 'diagnostics'):
            result['diagnostics'] = exc.diagnostics
        save('failed')
        raise


if __name__ == '__main__':
    main()
