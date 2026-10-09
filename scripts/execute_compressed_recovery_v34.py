"""Registered conversion and bounded repair from canonical compressed factors.

Conversion verifies earlier lossless evidence and every decoded factor.
Repair never receives those exact factors as solver inputs. Every worker
requires live command admission and records complete output evidence.
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
sys.path.insert(0, str(ROOT))
from scripts.run_adaptive_service_v30 import (
    SCHEMA as LOSSLESS_SCHEMA, _safe_path, _sha, require,
    select_records as select_point_records, preflight_stages,
)
from scripts.run_ordered_service_v30 import SCHEMA as ORDERED_LOSSLESS_SCHEMA
from src.experiment_inventory import source_hashes
from src.run_store import atomic_write, canonical_json, digest, strict_json
from scripts.verify_terminal_recovery_v34 import verify_completed
from src.transaction_timing import verify_command_admission

SCHEMA = 'native-box-compressed-service-transaction-v31'
METHODS = ('convert_lossless', 'repair', 'indexed_fresh')
CAPS = dict(records=16*2**20, config=2**20, weights=2*2**30,
    lossless_state=512*2**20, lossless_model=512*2**20, lossless_completion=64*2**20,
    prior_state=512*2**20, compressed_preparation_completion=64*2**20,
    reference_completion=64*2**20)


def required_inputs(method):
    require(method in METHODS, 'unsupported compressed method')
    if method == 'convert_lossless':
        return {'records', 'lossless_state', 'lossless_model', 'lossless_completion'}
    return {'records', 'config', 'weights', 'prior_state',
            'compressed_preparation_completion', 'reference_completion'}


def validate_policy(plan):
    from src.adaptive_calibration_v30 import AdaptiveBudget
    from src.sparse_box_certificate_v30 import SparseCertificateBudget
    required_inputs(plan.get('method'))
    require(plan.get('phase', 'feasibility') == 'feasibility', 'worker requires feasibility admission')
    require(plan.get('use_candidates') is False, 'prior model proposals must remain disabled')
    require(plan.get('decoder_backend') == 'ordered', 'V31 requires the reviewed ordered decoder')
    require(plan.get('codec_bits') == 48 and type(plan['codec_bits']) is int,
            'V31 follow-up requires forty-eight-bit descriptors')
    require(plan.get('block_size') == 256 and type(plan['block_size']) is int,
            'initial compressed pilot requires block size 256')
    require(plan.get('solver_backend') in ('auto', 'token', 'primal'), 'unsupported point route')
    require(plan.get('certificate_backend') == 'sparse', 'unsupported certificate route')
    point = plan.get('solver_budget')
    require(type(point) is dict and set(point) == {
        'max_workspace_bytes', 'max_work_units', 'max_refinement_coordinates'}, 'point budget fields differ')
    sparse = plan.get('sparse_budget')
    require(type(sparse) is dict and set(sparse) == {
        'max_work_units', 'max_workspace_bytes', 'max_preconditioned_coordinates', 'max_rounds'},
        'sparse budget fields differ')
    for key, minimum in (('max_point_work_units', 1), ('max_certificate_work_units', 0),
                         ('max_neural_stage_record_pairs', 0), ('original_token_count', 1)):
        require(type(plan.get(key)) is int and plan[key] >= minimum, 'invalid '+key)
    require(plan.get('expected_target') is not None, 'registered fixed target is required')
    _sha(plan['expected_target'], 'expected_target')
    for key in ('expected_model_sha256', 'expected_state_sha256'):
        if plan.get(key) is not None:
            _sha(plan[key], key)
    if plan['method'] == 'convert_lossless':
        require(plan['max_neural_stage_record_pairs'] == 0, 'conversion must permit zero neural traversals')
    point_budget, sparse_budget = AdaptiveBudget(**point), SparseCertificateBudget(**sparse)
    workspace = plan.get('max_certificate_workspace_bytes')
    require(type(workspace) is int and 0 < workspace <= 2**30,
            'certificate workspace must be explicit and at most one GiB')
    if plan['decoder_backend'] == 'scalar':
        require(workspace == point_budget.max_workspace_bytes,
                'scalar certificate workspace must equal its point-policy workspace')
    return point_budget, sparse_budget


def expected_preparer(decoder_backend):
    require(decoder_backend in ('scalar', 'ordered'), 'unsupported decoder backend')
    if decoder_backend == 'ordered':
        from src.ordered_fixed_service_v30 import ordered_preparer_binding
        return ordered_preparer_binding()
    from src.fixed_factor_state import preparer_binding
    return preparer_binding()


def lossless_schema(plan):
    return ORDERED_LOSSLESS_SCHEMA if plan['decoder_backend'] == 'ordered' else LOSSLESS_SCHEMA


def validate_backend_metadata(plan, completion):
    """Preserve the original preparer identity; never relabel historical factors."""
    backend = plan['decoder_backend']
    if completion.get('schema') == SCHEMA:
        require(completion.get('decoder_backend') == backend, 'compressed decoder backend differs')
        require(completion.get('preparer_sha256') == expected_preparer(backend), 'compressed preparer differs')
        require(completion.get('max_certificate_workspace_bytes') == plan['max_certificate_workspace_bytes'],
                'compressed certificate workspace policy differs')
    else:
        require(completion.get('schema') == lossless_schema(plan), 'lossless decoder backend differs')
    if backend == 'ordered':
        require(completion.get('preparer_sha256') == expected_preparer(backend), 'ordered preparer differs')
        manifest = completion.get('decoder_implementation_manifest')
        require(type(manifest) is dict
            and completion.get('decoder_implementation_sha256') == digest(canonical_json(manifest)),
            'ordered implementation manifest differs')
    elif completion.get('preparer_sha256') is not None:
        require(completion['preparer_sha256'] == expected_preparer(backend), 'scalar preparer differs')


def select_records(plan, payload):
    validate_policy(plan)
    translated = dict(plan, method='direct_fresh' if plan['method'] == 'convert_lossless' else plan['method'])
    return select_point_records(translated, payload)


def validate_inputs(plan):
    require(type(plan.get('inputs')) is dict and set(plan['inputs']) == required_inputs(plan['method']),
            'declared compressed input access differs')
    for name, entry in plan['inputs'].items():
        require(type(entry) is dict and set(entry) == {'path', 'sha256'}, 'invalid input binding')
        _sha(entry['sha256'], name+' input')
        path = _safe_path(entry['path'])
        require(path.is_file() and path.stat().st_size <= CAPS[name], 'input missing or exceeds cap: '+name)
        with path.open('rb') as stream:
            require(hashlib.file_digest(stream, 'sha256').hexdigest() == entry['sha256'], 'input changed: '+name)


def verify_registered_completion(entry):
    """Verify a declared completion and its immutable registered evidence closure.

The closure includes its worker artifacts, outputs, program, protocol,
registration, and frozen source directory. No historical file is changed.
"""
    path = _safe_path(entry['path'])
    require(path.name == 'completion.json' and path.parent.name == 'outputs',
            'completion input must identify an original terminal artifact')
    def metadata(location):
        location = _safe_path(str(location))
        require(location.is_file() and location.stat().st_size <= 64*2**20,
                'historical metadata is missing or exceeds cap')
        return location.read_bytes()

    require(digest(metadata(path)) == entry['sha256'], 'completion input changed')
    attempt = path.parent.parent
    campaign = attempt.parent.parent
    program_raw = metadata(campaign/'program.json')
    protocol_raw = metadata(campaign/'protocol.json')
    program = strict_json(program_raw)
    protocol = strict_json(protocol_raw)
    registration = strict_json(metadata(campaign/'registration.json'))
    registered_plan = strict_json(metadata(attempt/'plan.json'))
    require(registration['program_sha256'] == digest(program_raw)
        and registration['protocol_sha256'] == digest(protocol_raw)
        and protocol['program_sha256'] == digest(program_raw), 'historical registration binding differs')
    require(registered_plan['program_sha256'] == digest(program_raw)
        and registered_plan['protocol_sha256'] == digest(protocol_raw)
        and registered_plan['source_sha256'] == program['source_sha256'], 'historical plan binding differs')
    source_root = _safe_path(str(campaign/'source'))
    require(source_hashes(source_root) == program['source_sha256'], 'historical frozen source changed')
    result = verify_completed(attempt)
    require(result.get('source_sha256') == program['source_sha256'], 'historical result source binding differs')
    transaction_raw = metadata(attempt/'transaction.json')
    transaction = strict_json(transaction_raw)
    require(type(transaction.get('controller_elapsed_ns')) is int and transaction['controller_elapsed_ns'] >= 0,
            'historical complete transaction clock is missing')
    require(type(result.get('worker_transaction_elapsed_ns')) is int
        and result['worker_transaction_elapsed_ns'] >= 0, 'historical worker clock is missing')
    require(digest(metadata(path)) == entry['sha256'], 'completion changed during verification')
    evidence = dict(completion_sha256=entry['sha256'], plan_sha256=result['plan_sha256'],
        program_sha256=digest(program_raw), protocol_sha256=digest(protocol_raw),
        transaction_sha256=digest(transaction_raw), receipt_sha256=transaction['receipt_sha256'],
        controller_elapsed_ns=transaction['controller_elapsed_ns'],
        worker_elapsed_ns=result['worker_transaction_elapsed_ns'],
        frozen_source_files_verified=len(program['source_sha256']),
        scope='verified original receipt and registered source; current file reads remain measured request work')
    return result, evidence, attempt


def validate_original_metadata(plan, completion, original, *, schema, method):
    require(completion.get('schema') == schema and completion.get('method') == method
        and completion.get('status') == 'complete', 'original preparation kind differs')
    validate_backend_metadata(plan, completion)
    for field in ('complete_model', 'complete_state', 'model_roundtrip_exact', 'state_roundtrip_canonical'):
        require(completion.get(field) is True, 'original preparation evidence missing: '+field)
    require(completion.get('confirmation') is False and completion.get('scientific_promotion') is False
        and completion.get('use_candidates') is False, 'preparation policy flags differ')
    ids = [row['id'] for row in original]
    require(completion.get('original_record_ids') == ids and completion.get('retained_record_ids') == ids
        and completion.get('committed_record_ids') == ids and completion.get('deleted_record_ids') == [],
        'original preparation membership differs')
    require(completion.get('original_token_count') == plan['original_token_count'], 'original normalization differs')
    require(completion.get('original_records_sha256') == digest(canonical_json({'records': list(original)})),
            'original source tokens differ')
    require(completion.get('records_input_sha256') == plan['inputs']['records']['sha256'], 'record file differs')
    require(completion.get('fixed_target_sha256') == plan['expected_target'], 'fixed target differs')
    _sha(completion.get('base_target_sha256'), 'base target')
    require(completion.get('stage_count') == 24 and type(completion.get('stage_ids')) is list
        and len(completion['stage_ids']) == 24 and len(set(completion['stage_ids'])) == 24,
        'preparation must contain all twenty-four stages')
    require(completion.get('solver_backend') == plan['solver_backend']
        and completion.get('solver_budget') == plan['solver_budget']
        and completion.get('max_point_work_units') == plan['max_point_work_units'],
        'preparation and repair point policies differ')
    require(completion.get('target_recipe') == dict(schema='fixed-target-recipe-v1', bits=4,
        group_count=1, max_grid_entries=1000000, original_token_count=plan['original_token_count'], ridge=[1,100]),
        'preparation target recipe differs')


def validate_reference(plan, reference, original, retained, preparation):
    require(reference.get('schema') == lossless_schema(plan) and reference.get('status') == 'complete',
            'retained reference schema or status differs')
    validate_backend_metadata(plan, reference)
    require(reference.get('complete_model') is True and reference.get('model_roundtrip_exact') is True,
            'retained reference model is incomplete')
    require(reference.get('method') in ('repair', 'indexed_fresh', 'model_only_fresh'), 'reference method differs')
    for key in ('fixed_target_sha256', 'base_target_sha256', 'original_records_sha256',
                'original_record_ids', 'original_token_count', 'checkpoint_files_sha256', 'stage_ids',
                'solver_backend', 'solver_budget', 'max_point_work_units', 'records_input_sha256',
                'target_recipe', 'evaluator_id'):
        require(reference.get(key) == preparation.get(key), 'retained reference differs: '+key)
    if plan['decoder_backend'] == 'ordered':
        for key in ('preparer_sha256', 'decoder_implementation_manifest', 'decoder_implementation_sha256'):
            require(reference.get(key) == preparation.get(key), 'ordered retained reference differs: '+key)
    require(reference.get('retained_record_ids') == [row['id'] for row in retained]
        and reference.get('deleted_record_ids') == list(plan['deleted_ids']), 'reference deletion differs')
    require(reference.get('original_records_sha256') == digest(canonical_json({'records': list(original)})),
            'reference original source tokens differ')
    require(reference.get('use_candidates') is False and reference.get('confirmation') is False
        and reference.get('scientific_promotion') is False, 'reference policy flags differ')
    if plan.get('expected_model_sha256') is not None:
        require(reference['model_artifact']['sha256'] == plan['expected_model_sha256'],
                'registered reference model differs')


def verify_state_model(state, model_raw, records):
    from src.compact_state import CompactState, serialize
    require(state.record_ids == tuple(row['id'] for row in records), 'state membership differs')
    require(all(leaf.tokens == tuple(row['tokens']) for leaf, row in zip(state.anchors, records)),
            'state source tokens differ')
    require(serialize(CompactState(state.target_sha256, state.stages, ())) == model_raw,
            'state model bytes differ from verified complete model')


def convert_verified_state(lossless, model_raw, records, *, decoder_backend='ordered', codec_bits=48):
    """Convert trusted lossless factors and explicitly check every enclosure."""
    from src.fixed_lossless_state_v29 import LosslessFactorState, to_factor_state
    from src.fixed_compressed_state_v26 import from_factor_state
    require(type(codec_bits) is int and codec_bits == 48, 'V31 conversion requires forty-eight bits')
    require(type(lossless) is LosslessFactorState, 'conversion requires the lossless state family')
    require(lossless.preparer_sha256 == expected_preparer(decoder_backend), 'unsupported source preparer identity')
    verify_state_model(lossless, model_raw, records)
    tick = time.perf_counter_ns()
    exact = to_factor_state(lossless)
    decode_ns = time.perf_counter_ns()-tick
    verify_state_model(exact, model_raw, records)
    tick = time.perf_counter_ns()
    compressed = from_factor_state(exact, bits=codec_bits, block_size=256)
    encode_ns = time.perf_counter_ns()-tick
    tick = time.perf_counter_ns()
    count = values = source_bytes = 0
    require(len(lossless.anchors) == len(exact.anchors) == len(compressed.anchors),
            'conversion record count differs')
    for source, restored, packed in zip(lossless.anchors, exact.anchors, compressed.anchors):
        require(source.record_id == restored.record_id == packed.record_id, 'conversion source order differs')
        require(len(source.descriptors) == len(restored.blocks) == len(packed.descriptors),
                'conversion stage count differs')
        for original_descriptor, factor, descriptor in zip(source.descriptors, restored.blocks, packed.descriptors):
            require(original_descriptor.binary64() == factor.binary64, 'lossless decoded factor bytes differ')
            require(descriptor.source_sha256 == original_descriptor.source_sha256 == digest(factor.binary64),
                    'conversion source hash differs')
            require(descriptor.shape == (factor.token_count, factor.width)
                and descriptor.stage_id == factor.stage_id, 'conversion factor dimensions or stage differ')
            require(descriptor.box().contains(factor.array()), 'compressed evidence excludes its exact source')
            count += 1
            values += factor.token_count*factor.width
            source_bytes += len(factor.binary64)
    verify_state_model(compressed, model_raw, records)
    for key in ('target_sha256', 'anchor_target_sha256', 'decoder_sha256',
                'provider_sha256', 'anchor_sha256', 'preparer_sha256'):
        require(getattr(compressed, key) == getattr(lossless, key), 'conversion provenance differs: '+key)
    return compressed, dict(schema='verified-lossless-to-compressed-conversion-v31',
        decoded_exact_factors=count, checked_enclosures=count, exact_factor_values=values,
        decoded_source_bytes=source_bytes, lossless_factor_decode_elapsed_ns=decode_ns,
        compressed_encoding_elapsed_ns=encode_ns, containment_audit_elapsed_ns=time.perf_counter_ns()-tick,
        every_source_hash_verified=True, every_enclosure_contains_source=True,
        complete_original_model_preserved=True, neural_stage_record_pairs=0,
        point_solver_stages=0, conversion_uses_no_quantizer=True,
        scope='conversion from trusted original preparation; no free-preparation or repair-speed claim')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    args = parser.parse_args()
    started = time.perf_counter_ns()
    plan_raw = args.plan.read_bytes()
    plan = strict_json(plan_raw)
    require(type(plan) is dict, 'plan must contain an object')
    require(source_hashes(ROOT) == plan.get('source_sha256'), 'worker source binding differs')
    verify_command_admission(plan['protocol_sha256'], plan.get('phase', 'feasibility'),
        [sys.executable, str(Path(__file__).resolve()), str(args.plan.absolute())])
    output = _safe_path(plan['output'])
    require(not output.exists() or output.is_dir() and not any(output.iterdir()), 'cannot overwrite worker output')
    output.mkdir(parents=True, exist_ok=True)
    result = dict(schema=SCHEMA, status='running', method=plan.get('method'), plan_sha256=digest(plan_raw),
        source_sha256=plan['source_sha256'], phases=[], confirmation=False, scientific_promotion=False,
        use_candidates=False, numerical_target='fixed nearest-anchor features; not sequential calibration',
        trusted_preparation_required=True, artifacts={},
        worker_clock_scope='plan read through complete output verification; terminal commits and exit excluded',
        primary_latency='outer complete transaction; nested worker and service clocks must not be added',
        evidence_access_scope='declared input files plus registered evidence closures for completion inputs',
        runtime=dict(python=sys.version, executable=sys.executable,
            affinity_cpus=sorted(os.sched_getaffinity(0)),
            thread_environment={name:os.environ.get(name) for name in (
                'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}))

    def save(phase, **details):
        result['phases'].append(dict(phase=phase, elapsed_ns=time.perf_counter_ns()-started, **details))
        result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json', canonical_json(result))
        print(json.dumps(result['phases'][-1], allow_nan=False), flush=True)

    def read(name):
        entry = plan['inputs'][name]
        path = _safe_path(entry['path'])
        require(path.stat().st_size <= CAPS[name], 'input exceeds cap during read: '+name)
        raw = path.read_bytes()
        require(digest(raw) == entry['sha256'], 'input changed during read: '+name)
        return raw

    try:
        save('input_validation_started')
        point_budget, sparse_budget = validate_policy(plan)
        validate_inputs(plan)
        original, records = select_records(plan, strict_json(read('records')))
        result.update(inputs=plan['inputs'], decoder_backend=plan['decoder_backend'],
            solver_backend=plan['solver_backend'], solver_budget=asdict(point_budget),
            certificate_backend=plan['certificate_backend'], sparse_budget=asdict(sparse_budget),
            codec_bits=48, block_size=256, max_point_work_units=plan['max_point_work_units'],
            max_certificate_work_units=plan['max_certificate_work_units'],
            max_certificate_workspace_bytes=plan['max_certificate_workspace_bytes'],
            max_neural_stage_record_pairs=plan['max_neural_stage_record_pairs'],
            original_token_count=plan['original_token_count'], original_record_ids=[row['id'] for row in original],
            retained_record_ids=[row['id'] for row in records], deleted_record_ids=list(plan['deleted_ids']),
            original_record_lengths=[len(row['tokens']) for row in original],
            retained_record_lengths=[len(row['tokens']) for row in records],
            retained_token_count=sum(len(row['tokens']) for row in records),
            original_records_sha256=digest(canonical_json({'records': list(original)})),
            records_input_sha256=plan['inputs']['records']['sha256'])
        atomic_write(output/'plan.json', plan_raw)
        from src.compact_state import CompactState, serialize as encode_model, parse as decode_model
        from src.fixed_compressed_state_v26 import serialize as encode_state, parse as decode_state
        reference = reference_attempt = None
        if plan['method'] == 'convert_lossless':
            save('lossless_preparation_verification_started')
            preparation, receipt, _ = verify_registered_completion(plan['inputs']['lossless_completion'])
            validate_original_metadata(plan, preparation, original, schema=lossless_schema(plan), method='direct_fresh')
            for kind in ('model', 'state'):
                require(preparation[kind+'_artifact']['sha256'] == plan['inputs']['lossless_'+kind]['sha256'],
                        'declared lossless '+kind+' differs from its verified receipt')
            result['external_lossless_preparation'] = receipt
            result['external_preparation_cost_scope'] = 'original lifetime cost; conversion is additional measured work'
            from src.fixed_lossless_state_v29 import parse as decode_lossless
            save('lossless_state_parse_started')
            tick = time.perf_counter_ns()
            raw = read('lossless_state')
            require(len(raw) == preparation['state_artifact']['bytes'], 'lossless state byte count differs')
            prior = decode_lossless(raw, expected_sha256=plan['inputs']['lossless_state']['sha256'])
            result['lossless_state_parse_elapsed_ns'] = time.perf_counter_ns()-tick
            model_raw = read('lossless_model')
            require(len(model_raw) == preparation['model_artifact']['bytes'], 'lossless model byte count differs')
            require(prior.target_sha256 == preparation['fixed_target_sha256']
                and prior.anchor_target_sha256 == preparation['base_target_sha256'], 'lossless targets differ')
            save('conversion_started')
            tick = time.perf_counter_ns()
            state, diagnostics = convert_verified_state(prior, model_raw, original,
                decoder_backend=plan['decoder_backend'], codec_bits=plan['codec_bits'])
            result['conversion_elapsed_ns'] = time.perf_counter_ns()-tick
            result['diagnostics'] = diagnostics
            result['containment_verified_for_all_factors'] = True
            result['original_lossless_completion_sha256'] = receipt['completion_sha256']
            del raw, prior
            save('conversion_complete')
        else:
            save('compressed_preparation_verification_started')
            preparation, receipt, _ = verify_registered_completion(plan['inputs']['compressed_preparation_completion'])
            validate_original_metadata(plan, preparation, original, schema=SCHEMA, method='convert_lossless')
            require(preparation.get('source_sha256') == plan['source_sha256'], 'compressed preparation source differs')
            require(preparation.get('codec_bits') == 48 and preparation.get('block_size') == 256
                and preparation.get('containment_verified_for_all_factors') is True,
                'trusted compressed containment evidence is missing')
            require(preparation['state_artifact']['sha256'] == plan['inputs']['prior_state']['sha256'],
                    'compressed state differs from verified preparation')
            result['external_compressed_conversion'] = receipt
            result['external_lossless_preparation'] = preparation['external_lossless_preparation']
            result['external_preparation_cost_scope'] = 'original preparation plus conversion are prior lifetime costs; neither is free'
            save('reference_verification_started')
            reference, reference_receipt, reference_attempt = verify_registered_completion(plan['inputs']['reference_completion'])
            validate_reference(plan, reference, original, records, preparation)
            result['retained_reference_evidence'] = reference_receipt
            result['retained_reference_cost_scope'] = (
                'prior oracle generation is experiment validation cost; current verification reads are request work; '
                'no reference model or exact reference factors are passed to the numerical service')
            checkpoint = _safe_path(plan['checkpoint']).resolve()
            expected_checkpoint = {name: plan['inputs'][key]['sha256'] for name, key in (
                ('config.json', 'config'), ('model.safetensors', 'weights'))}
            require(Path(plan['inputs']['config']['path']).resolve() == checkpoint/'config.json'
                and Path(plan['inputs']['weights']['path']).resolve() == checkpoint/'model.safetensors',
                'checkpoint paths differ from bound inputs')
            require(preparation['checkpoint_files_sha256'] == expected_checkpoint, 'checkpoint differs from preparation')
            from src.checkpoint_adapter import load_gpt2_checkpoint
            from src.target_manifest import TargetRecipe
            from src.dyadic_row_target import build_dyadic_row_target
            if plan['decoder_backend'] == 'ordered':
                from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder as Decoder
                from src.native_box_compressed_service_v31 import NativeBoxCompressedService as Service
            else:
                from src.certified_transformer import CertifiedDecoder as Decoder
                from src.adaptive_compressed_service_v30 import AdaptiveCompressedService as Service
            save('checkpoint_load_started')
            loaded = load_gpt2_checkpoint(checkpoint, identity_encoding='binary64_tree_v2')
            require(loaded.provenance['files_sha256'] == expected_checkpoint, 'loaded checkpoint provenance differs')
            decoder = Decoder(loaded.decoder, primitive_backend='mpfr_enclosure')
            if plan['decoder_backend'] == 'ordered':
                require(decoder.implementation_manifest == preparation['decoder_implementation_manifest'],
                        'current ordered implementation differs from prepared factors')
            require(list(decoder.stage_ids) == preparation['stage_ids'], 'complete decoder stages differ')
            for row in original:
                decoder.base._tokens(row['tokens'])
            base = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=plan['original_token_count'], group_count=1))
            require(base.digest == preparation['base_target_sha256'], 'current base target differs')
            result['fallback_point_admission'] = preflight_stages(base.stages, result['retained_token_count'],
                budget=point_budget, route=plan['solver_backend'], max_point_work_units=plan['max_point_work_units'])
            certificate_options = (dict(max_certificate_workspace_bytes=plan['max_certificate_workspace_bytes'])
                if plan['decoder_backend'] == 'ordered' else {})
            service = Service(decoder, base, bits=48, block_size=256,
                solver_backend=plan['solver_backend'], certificate_backend=plan['certificate_backend'],
                coefficient_budget=point_budget, sparse_budget=sparse_budget,
                max_point_work_units=plan['max_point_work_units'],
                max_certificate_work_units=plan['max_certificate_work_units'],
                max_neural_stage_record_pairs=plan['max_neural_stage_record_pairs'],
                progress=lambda row: save('stage_complete', stage_metrics=row), **certificate_options)
            require(service.target.digest == plan['expected_target'], 'current fixed target differs')
            save('compressed_state_parse_started')
            tick = time.perf_counter_ns()
            raw = read('prior_state')
            require(len(raw) == preparation['state_artifact']['bytes'], 'compressed state byte count differs')
            prior = decode_state(raw, expected_sha256=plan['inputs']['prior_state']['sha256'])
            require(prior.record_ids == tuple(row['id'] for row in original), 'compressed original membership differs')
            prior_model = encode_model(CompactState(prior.target_sha256, prior.stages, ()))
            require(digest(prior_model) == preparation['model_artifact']['sha256']
                and len(prior_model) == preparation['model_artifact']['bytes'], 'compressed prior model differs')
            verify_state_model(prior, prior_model, original)
            result['compressed_state_parse_elapsed_ns'] = time.perf_counter_ns()-tick
            del raw, prior_model
            save('service_started')
            outcome = service.run(records, method=plan['method'], prior=prior, deleted_ids=plan['deleted_ids'])
            state = outcome.state
            result['diagnostics'] = outcome.diagnostics
            require(outcome.diagnostics['neural_stage_record_pairs'] <= plan['max_neural_stage_record_pairs'],
                    'service exceeded its neural traversal policy')
            model_raw = encode_model(CompactState(state.target_sha256, outcome.stages, ()))
            save('service_complete')
        for key in ('fixed_target_sha256', 'base_target_sha256', 'checkpoint_files_sha256', 'target_recipe', 'evaluator_id'):
            result[key] = preparation[key]
        require(state.preparer_sha256 == expected_preparer(plan['decoder_backend']), 'output preparer differs')
        result['preparer_sha256'] = state.preparer_sha256
        if plan['decoder_backend'] == 'ordered':
            for key in ('decoder_implementation_manifest', 'decoder_implementation_sha256'):
                result[key] = preparation[key]
        result.update(stage_count=len(state.stages), stage_ids=[stage.stage_id for stage in state.stages],
            model_code_elements=sum(stage.rows*stage.columns for stage in state.stages),
            model_packed_code_bytes=sum(len(stage.packed_indices) for stage in state.stages))
        require(result['stage_count'] == 24 and result['stage_ids'] == preparation['stage_ids'], 'model stages differ')
        checked_model = decode_model(model_raw, expected_sha256=digest(model_raw))
        require(checked_model.stages == state.stages and checked_model.target_sha256 == plan['expected_target'],
                'model canonical roundtrip differs')
        if plan.get('expected_model_sha256') is not None:
            require(digest(model_raw) == plan['expected_model_sha256'], 'registered model hash differs')
        if reference is not None:
            save('reference_model_comparison_started')
            artifact = reference['model_artifact']
            reference_raw = (reference_attempt/'outputs'/artifact['file']).read_bytes()
            require(digest(reference_raw) == artifact['sha256'] and len(reference_raw) == artifact['bytes'],
                    'reference model changed after verification')
            require(model_raw == reference_raw, 'compressed output differs from complete retained reference')
            result['retained_reference_model_byte_equal'] = True
        state_raw = encode_state(state)
        checked = decode_state(state_raw, expected_sha256=digest(state_raw))
        require(encode_state(checked) == state_raw and checked.stages == state.stages,
                'compressed state canonical roundtrip differs')
        verify_state_model(checked, model_raw, records)
        if plan.get('expected_state_sha256') is not None:
            require(digest(state_raw) == plan['expected_state_sha256'], 'registered state hash differs')
        for name, payload in (('model', model_raw), ('state', state_raw)):
            atomic_write(output/(name+'.bin'), payload)
            require(digest((output/(name+'.bin')).read_bytes()) == digest(payload), 'written '+name+' differs')
            artifact = dict(file=name+'.bin', bytes=len(payload), sha256=digest(payload))
            result[name+'_artifact'] = artifact
            result['artifacts'][name] = dict(artifact)
        require(source_hashes(ROOT) == plan['source_sha256'], 'bound source changed during transaction')
        result.update(status='complete', complete_model=True, complete_state=True,
            committed_record_ids=list(checked.record_ids), model_roundtrip_exact=True, state_roundtrip_canonical=True,
            worker_transaction_elapsed_ns=time.perf_counter_ns()-started)
        save('complete')
        terminal = canonical_json(result)
        with (output/'completion.json').open('xb') as stream:
            stream.write(terminal)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(output, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        print(json.dumps(dict(phase='terminal_record_committed', sha256=digest(terminal))), flush=True)
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        for source, destination in (('diagnostics', 'failure_diagnostics'),
                                    ('service_diagnostics', 'failure_service_diagnostics'),
                                    ('admission', 'failure_admission')):
            if hasattr(exc, source):
                result[destination] = getattr(exc, source)
        save('failed')
        raise


if __name__ == '__main__':
    main()
