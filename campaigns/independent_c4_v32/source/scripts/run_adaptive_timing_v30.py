"""V30 bounded adaptive point solver with unchanged V29 state and request."""
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
CAPS = dict(records=2**20, config=2**20, weights=512*2**20,
            prior_state=128*2**20, archive_summary=8*2**20, archive_plan=2**20)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def required_inputs(method):
    require(method in ('repair', 'indexed_fresh', 'model_only_fresh'), 'unsupported V29 method')
    return {'records', 'config', 'weights'} | (
        {'prior_state', 'archive_summary', 'archive_plan'} if method != 'model_only_fresh' else set())


def select_records(plan, payload):
    required_inputs(plan.get('method'))
    require(plan.get('phase', 'feasibility') == 'feasibility', 'V29 requires feasibility admission')
    require(plan.get('use_candidates') is False, 'V29 requires no prior-model proposals')
    require(plan.get('record_ids') == list(ORIGINAL_IDS[1:])
        and plan.get('deleted_ids') == list(ORIGINAL_IDS[:1]), 'registered deletion differs')
    require(plan.get('expected_model_sha256') == EXPECTED_MODEL
        and type(plan.get('expected_state_sha256')) is str
        and len(plan['expected_state_sha256']) == 64, 'expected output hashes differ')
    original = payload.get('records') if type(payload) is dict else None
    require(type(original) is list and len(original) == 2, 'two original records are required')
    require(all(type(row) is dict and set(row) == {'id', 'tokens'} for row in original), 'record fields differ')
    require(tuple(row['id'] for row in original) == ORIGINAL_IDS, 'original record order differs')
    require(all(type(row['tokens']) is list and len(row['tokens']) == 16
        and all(type(token) is int and 0 <= token < 2**64 for token in row['tokens']) for row in original),
        'each original record requires sixteen unsigned tokens')
    return original, (dict(id=original[1]['id'], tokens=list(original[1]['tokens'])),)


def validate_archive(plan, archive_plan, summary, archive_plan_hash, root):
    require(summary.get('schema') == 'lossless-state-archive-audit-v29'
        and archive_plan.get('schema') == 'lossless-state-archive-audit-plan-v29', 'archive schema differs')
    require(summary.get('status') == 'complete' and summary.get('plan_sha256') == archive_plan_hash,
            'archive is incomplete or its plan binding differs')
    for key in ('artifacts_saved', 'all_complete_models_preserved',
                'all_retained_descriptors_unchanged', 'all_state_roundtrips_canonical'):
        require(summary.get(key) is True, 'archive verification incomplete: '+key)
    hashes = archive_plan.get('source_hashes')
    require(type(hashes) is dict and hashes and summary.get('source_hashes') == hashes,
            'archive source bindings differ')
    for name, expected in hashes.items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'unsafe archive source path')
        require(digest((root/path).read_bytes()) == expected, 'archive source changed: '+name)
    artifact = summary['generations']['prepare-001']
    require(artifact['complete_state_sha256'] == plan['inputs']['prior_state']['sha256'],
            'original lossless state binding differs')
    require(type(artifact['complete_state_bytes']) is int and artifact['complete_state_bytes'] > 0
        and artifact.get('source_count') == 2 and artifact.get('roundtrip_exact') is True,
        'original archive verification differs')
    retained = summary['generations']['repair-001']
    require(retained['model_sha256'] == EXPECTED_MODEL
        and retained['complete_state_sha256'] == plan['expected_state_sha256']
        and retained.get('roundtrip_exact') is True, 'retained archive output binding differs')
    return artifact


def software_checks():
    """Check worker contracts with small software fixtures only."""
    import copy
    import tempfile
    payload = {'records': [dict(id=rid, tokens=[0]*16) for rid in ORIGINAL_IDS]}
    plan = dict(method='repair', use_candidates=False, record_ids=list(ORIGINAL_IDS[1:]),
        deleted_ids=list(ORIGINAL_IDS[:1]), expected_model_sha256=EXPECTED_MODEL,
        expected_state_sha256='1'*64)
    require(select_records(plan, payload)[1][0]['id'] == ORIGINAL_IDS[1], 'valid record fixture failed')
    require(required_inputs('model_only_fresh') == {'records', 'config', 'weights'}, 'cold access differs')
    require(required_inputs('repair') == required_inputs('indexed_fresh') == set(CAPS), 'indexed access differs')
    checks = 3
    bad = copy.deepcopy(payload); bad['records'][0]['tokens'][0] = True
    cases = [(dict(plan, use_candidates=True), payload), (plan, bad),
             (dict(plan, deleted_ids=[]), payload), (dict(plan, expected_state_sha256=None), payload),
             (dict(plan, method='other'), payload), (plan, {'records':list(reversed(payload['records']))})]
    for invalid_plan, invalid_payload in cases:
        try: select_records(invalid_plan, invalid_payload)
        except ValueError: checks += 1
        else: raise AssertionError('invalid worker fixture accepted')
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder); (root/'src').mkdir()
        (root/'src/codec.py').write_bytes(b'software source fixture')
        hashes = {'src/codec.py':digest((root/'src/codec.py').read_bytes())}
        archive_plan = dict(schema='lossless-state-archive-audit-plan-v29',source_hashes=hashes)
        summary = dict(schema='lossless-state-archive-audit-v29',status='complete',plan_sha256='a'*64,
            source_hashes=hashes, artifacts_saved=True, all_complete_models_preserved=True,
            all_retained_descriptors_unchanged=True, all_state_roundtrips_canonical=True,
            generations={'prepare-001':dict(complete_state_sha256='b'*64,complete_state_bytes=123,
                source_count=2,roundtrip_exact=True), 'repair-001':dict(model_sha256=EXPECTED_MODEL,
                complete_state_sha256='1'*64,roundtrip_exact=True)})
        bound = dict(inputs={'prior_state':{'sha256':'b'*64}},expected_state_sha256='1'*64)
        validate_archive(bound,archive_plan,summary,'a'*64,root);checks += 1
        mutations = [dict(summary,status='incomplete'),dict(summary,plan_sha256='c'*64),
                     dict(summary,all_state_roundtrips_canonical=False),dict(summary,source_hashes={})]
        for item in mutations:
            try:validate_archive(bound,archive_plan,item,'a'*64,root)
            except ValueError:checks += 1
            else:raise AssertionError('invalid archive fixture accepted')
    return dict(scope='software fixtures only; no model execution',checks=checks,passed=True)


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
    result = dict(schema='adaptive-lossless-complete-transaction-v30', status='running',
        method=plan['method'], plan_sha256=digest(raw), phases=[], use_candidates=False,
        solver_backend='auto', certificate_backend=None, evidence='lossless exact feature words',
        max_neural_stage_record_pairs=24, confirmation=False, scientific_promotion=False,
        numerical_target='fixed nearest-anchor features; not sequential calibration',
        worker_clock_scope='plan read through complete output verification; final progress and completion commits and exit excluded',
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
        if plan['method'] != 'model_only_fresh':
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
        from src.adaptive_fixed_service_v30 import AdaptiveFixedAnchorService as FixedAnchorService
        from src.adaptive_lossless_service_v30 import AdaptiveLosslessService as FixedLosslessService
        from src.fixed_lossless_state_v29 import LosslessFactorState, serialize as encode_state, parse as decode_state
        from src.compact_state import CompactState, serialize as encode_model, parse as decode_model
        from src.compact_service import model_digest
        save('checkpoint_load_started')
        loaded = load_gpt2_checkpoint(checkpoint, identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256'] == {name:plan['inputs'][key]['sha256']
            for name, key in (('config.json', 'config'), ('model.safetensors', 'weights'))}, 'checkpoint provenance differs')
        decoder = CertifiedDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
        base = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=32, group_count=1))
        from dataclasses import asdict
        from src.calibration_admission_v29 import StageShape, assess_calibration_admission
        admission = assess_calibration_admission(
            tuple(StageShape(s.stage_id, s.width, len(s.weights)) for s in base.stages),
            retained_tokens=sum(len(row['tokens']) for row in records), process_cap_bytes=6*2**30)
        result['resource_admission'] = asdict(admission)
        require(not admission.ruled_out, 'request exceeds a necessary memory lower bound')
        callback = lambda row:save('stage_complete', stage_metrics=row)
        service = (FixedLosslessService(decoder, base, solver_backend='auto', progress=callback)
            if plan['method'] != 'model_only_fresh' else FixedAnchorService(decoder, base, state_backend='factors',
                solver_backend='auto', use_candidates=False, progress=callback))
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
            prior = decode_state(prior_raw, expected_sha256=plan['inputs']['prior_state']['sha256'])
            require(type(prior) is LosslessFactorState and prior.record_ids == ORIGINAL_IDS,
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
            require(type(outcome.state) is LosslessFactorState, 'unexpected output state type')
            state_raw = encode_state(outcome.state)
            checked = decode_state(state_raw, expected_sha256=plan['expected_state_sha256'])
            require(encode_state(checked) == state_raw and checked.stages == outcome.stages
                and checked.record_ids == tuple(row['id'] for row in records), 'state canonical roundtrip differs')
            atomic_write(output/'state.bin', state_raw)
            require(digest((output/'state.bin').read_bytes()) == plan['expected_state_sha256'], 'written state differs from expected hash')
            result['state_artifact'] = dict(file='state.bin', bytes=len(state_raw), sha256=digest(state_raw))
            result['committed_record_ids'] = list(checked.record_ids)
            save('state_write_complete', bytes=len(state_raw))
        result['artifacts'] = {'model':dict(result['model_artifact'])}
        if 'state_artifact' in result:
            result['artifacts']['state'] = dict(result['state_artifact'])
        result.update(status='complete', complete_model=True, complete_state=outcome.state is not None,
                      worker_transaction_elapsed_ns=time.perf_counter_ns()-start)
        save('complete')
        # An immutable second terminal record exposes any later progress discrepancy.
        terminal = canonical_json(result)
        with (output/'completion.json').open('xb') as stream:
            stream.write(terminal)
            stream.flush()
            import os
            os.fsync(stream.fileno())
        print(json.dumps(dict(phase='terminal_record_committed',sha256=digest(terminal))),flush=True)
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        if hasattr(exc, 'diagnostics'):
            result['diagnostics'] = exc.diagnostics
        save('failed')
        raise


if __name__ == '__main__':
    main()
