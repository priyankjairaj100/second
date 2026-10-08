"""Make conditional V31 specifications from the unchanged outcome-blind V30 selection.

This is metadata preparation only. It neither resolves empirical prerequisites nor
registers, loads a checkpoint, evaluates a model, or changes the earlier draft.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.run_store import canonical_json, strict_json

SCHEMA = 'independent-request-campaign-specification-v31'
DRAFT_HASHES = {
    'specification.json': 'aadb20d91622dcb1f0bd902bdca095012f9afc11a703f626dd0d12887c9767fb',
    'selection.json': '734f39a6ba9eced308c881c1a42469951d48ae58798097850de0eb03567f1ba2',
    'wikitext-records.json': '3ac30626b5d8aafb67b594c97795caee755609cd2a1623a7f6fd576cc14921fa',
    'c4-records.json': 'd3f140c3baea09990c5432529906d601d5b572bfe2caeb2670ae89445a51a54c',
}
COMPRESSED_POLICY_SHA256 = '94442128d5610386af241da2e68d25968ed3ec85faec7aaa77e6606af652e024'
POLICY_FIELDS = (
    'decoder_backend', 'codec_bits', 'block_size', 'solver_backend', 'solver_budget',
    'sparse_budget', 'certificate_backend', 'max_certificate_work_units',
    'max_certificate_workspace_bytes', 'max_point_work_units',
    'max_neural_stage_record_pairs', 'use_candidates', 'original_token_count', 'expected_target',
)
FIXED_TARGET = 'f0699c208284fc97ca0df7740af13337a079b04ca2bf5574dda90046d8a1c27f'
ORIGINAL_MODEL = 'd314870fa0394d426f9f03ba354ec18defc30c13a827d1091a11ad1a242f627c'
RETAINED_MODEL = '25068a9373bb477123401124f07d5e02e09939f890fa16670d04d57e052bfce8'
POINT_BUDGET = dict(max_refinement_coordinates=16, max_work_units=6000000000,
                    max_workspace_bytes=536870912)
SPARSE_BUDGET = dict(max_preconditioned_coordinates=16, max_rounds=4,
                     max_work_units=6000000000, max_workspace_bytes=1073741824)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def descriptor(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink prerequisite')
    with path.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), sha256=sha, bytes=path.stat().st_size)


def checked_json(path, expected_sha256):
    entry = descriptor(path)
    require(entry['sha256'] == expected_sha256, 'historical prerequisite changed: '+str(path))
    require(entry['bytes'] <= 16*2**20, 'metadata prerequisite is too large')
    return strict_json(Path(path).read_bytes()), entry


def checked_policy(spec):
    """Accept exactly the reviewed pilot policy; never tune from a new root."""
    rows = [t for t in spec['trials'] if t['id'] == 'repair-128-48']
    require(len(rows) == 1, 'compressed prerequisite repair is ambiguous')
    trial = rows[0]
    require(trial['script'] == 'run_compressed_service_v31.py', 'compressed worker differs')
    policy = {key: copy.deepcopy(trial['plan'][key]) for key in POLICY_FIELDS}
    expected = dict(decoder_backend='ordered', codec_bits=48, block_size=256,
        solver_backend='auto', solver_budget=POINT_BUDGET, sparse_budget=SPARSE_BUDGET,
        certificate_backend='sparse', max_certificate_work_units=96000000000,
        max_certificate_workspace_bytes=1073741824, max_point_work_units=96000000000,
        max_neural_stage_record_pairs=24, use_candidates=False, original_token_count=256,
        expected_target=FIXED_TARGET)
    require(canonical_json(policy) == canonical_json(expected), 'reviewed compressed numerical policy differs')
    require(trial['plan']['method'] == 'repair', 'compressed prerequisite method differs')
    return policy


def external_prerequisites(root):
    """Name evidence to resolve at registration; do not read pending outputs here."""
    root = Path(root)
    external = {}
    original_names = {'prepare-256': 'direct_fresh', 'original-model-256': 'model_only_fresh'}
    retained_names = {'repair-001': 'repair', 'cold-001': 'model_only_fresh',
        'indexed-001': 'indexed_fresh', 'cold-002': 'model_only_fresh',
        'repair-002': 'repair', 'repair-003': 'repair', 'cold-003': 'model_only_fresh'}
    for name, method in dict(original_names, **retained_names).items():
        original = name in original_names
        equals = dict(status='complete', schema='ordered-complete-service-transaction-v30',
            method=method, complete_model=True, original_token_count=256,
            retained_token_count=256 if original else 128, fixed_target_sha256=FIXED_TARGET)
        equals['model_artifact.sha256'] = ORIGINAL_MODEL if original else RETAINED_MODEL
        if method != 'model_only_fresh':
            equals['complete_state'] = True
        external['ordered-'+name] = dict(attempt=str(root/'campaigns/ordered_service_v30/attempts'/name),
            equals=equals)
    for name, trial, original in (('scalar-original', 'prepare-128', True),
                                  ('scalar-retained', 'repair-001', False)):
        equals = dict(status='complete', schema='adaptive-complete-service-transaction-v30',
            method='direct_fresh' if original else 'repair', complete_model=True, complete_state=True,
            original_token_count=256, retained_token_count=256 if original else 128,
            fixed_target_sha256=FIXED_TARGET)
        equals['model_artifact.sha256'] = ORIGINAL_MODEL if original else RETAINED_MODEL
        external[name] = dict(attempt=str(root/'campaigns/full_service_v30/attempts'/trial), equals=equals)
    external['matched-quality'] = dict(
        attempt=str(root/'campaigns/quality_extensions_v30/attempts/matched-quality-128'),
        equals={'status': 'complete', 'matched_quality_gate_pass': True,
            'development_safety_gate_pass': True, 'historical_control_parity_pass': True,
            'provenance.new_model_sha256': RETAINED_MODEL,
            'provenance.new_fixed_target_sha256': FIXED_TARGET,
            'provenance.new_generation_sources_verified': True})
    equalities = [dict(left='ordered-'+name, right='scalar-original', artifacts=['model'])
                  for name in original_names]
    equalities += [dict(left='ordered-'+name, right='scalar-retained', artifacts=['model'])
                   for name in retained_names]
    return external, equalities


def validate_root(root, selection, records):
    corpus = root['corpus']
    require(corpus in ('wikitext', 'c4'), 'unsupported selected corpus')
    require(type(records) is dict and set(records) == {'records'}, 'record payload differs')
    rows = records['records']
    require(len(rows) == 2, 'root must retain both preselected sources')
    ids = [row['id'] for row in rows]
    require(ids == root['source_ids'] == sorted(set(ids)), 'source membership or order differs')
    require(sorted(row['id'] for row in selection['selected'][corpus]) == ids,
        'selection provenance does not match source IDs')
    for row in rows:
        require(set(row) == {'id', 'tokens'} and len(row['tokens']) == 128,
            'source token shape differs')
        require(all(type(x) is int and 0 <= x < 50257 for x in row['tokens']), 'token outside vocabulary')
    require(root['phase_cpu_ceiling_seconds'] == 1900 and root['maximum_complete_reservations_seconds'] == 1844,
        'prospective CPU allowance differs')
    trials = root['point_trials']
    require(len(trials) == 5 and len(root['requests']) == 2, 'point program differs')
    for trial in trials:
        plan = trial['plan']
        require(trial['script'] == 'run_ordered_service_v30.py', 'point worker differs')
        require(plan['original_token_count'] == 256 and plan['expected_target'] == FIXED_TARGET,
            'original normalization or target differs')
        require(plan['solver_budget'] == POINT_BUDGET and plan['solver_backend'] == 'auto'
            and plan['max_point_work_units'] == 96000000000 and plan['use_candidates'] is False,
            'point numerical policy differs')
        require(plan['inputs']['records'] == {key: root['records'][key] for key in ('path', 'sha256')},
            'point records descriptor differs')
    require(root['compressed_request_id'] == corpus+'-delete-0', 'compressed request was changed')
    for i, request in enumerate(root['requests']):
        require(request['deleted_ids'] == [ids[i]] and request['retained_ids'] == [ids[1-i]],
            'alternative deletion branches differ')
        expected_order = ['repair', 'cold'] if (i+(corpus == 'c4')) % 2 == 0 else ['cold', 'repair']
        require(request['method_order'] == expected_order, 'balanced method order differs')


def make_spec(root, selected_root, selection, records, descriptors, policy):
    validate_root(selected_root, selection, records)
    selected_root = copy.deepcopy(selected_root)
    corpus = selected_root['corpus']
    trials = selected_root['point_trials']
    preparation = trials[0]
    request = selected_root['requests'][0]
    template = selected_root['compressed_policy']
    require(template['conversion_cpu_seconds'] == 120 and template['conversion_wall_seconds'] == 180
        and template['repair_cpu_seconds'] == 300 and template['repair_wall_seconds'] == 420,
        'prospective compressed resource ceilings differ')
    conversion_id = corpus+'-root-convert'
    conversion_plan = dict(copy.deepcopy(policy), method='convert_lossless', max_neural_stage_record_pairs=0,
        checkpoint=preparation['plan']['checkpoint'], record_ids=selected_root['source_ids'], deleted_ids=[],
        inputs={'records': copy.deepcopy(preparation['plan']['inputs']['records'])})
    conversion = dict(id=conversion_id, script='run_compressed_service_v31.py', cpu_seconds=120, wall_seconds=180,
        plan=conversion_plan,
        depends=[dict(trial=trials[-1]['id'], equals=dict(complete_model=True)),
                 dict(trial=preparation['id'], equals=dict(complete_model=True, complete_state=True))],
        inputs_from_trial={
            'lossless_completion': dict(trial=preparation['id'], completion=True),
            'lossless_model': dict(trial=preparation['id'], artifact='model'),
            'lossless_state': dict(trial=preparation['id'], artifact='state')},
        compare_to=[dict(trial=preparation['id'], artifacts=['model'])])
    repair_plan = dict(copy.deepcopy(policy), method='repair', checkpoint=preparation['plan']['checkpoint'],
        record_ids=request['retained_ids'], deleted_ids=request['deleted_ids'],
        inputs=copy.deepcopy(preparation['plan']['inputs']))
    repair = dict(id=corpus+'-delete-0-compressed', script='run_compressed_service_v31.py', cpu_seconds=300,
        wall_seconds=420, plan=repair_plan,
        depends=[dict(trial=conversion_id, equals=dict(complete_model=True, complete_state=True)),
                 dict(trial=request['cold_trial'], equals=dict(complete_model=True)),
                 dict(trial=request['repair_trial'], equals=dict(complete_model=True, complete_state=True))],
        inputs_from_trial={
            'compressed_preparation_completion': dict(trial=conversion_id, completion=True),
            'prior_state': dict(trial=conversion_id, artifact='state'),
            'reference_completion': dict(trial=request['cold_trial'], completion=True)},
        compare_to=[dict(trial=request['cold_trial'], artifacts=['model'])],
        storage_gate=dict(artifact='state', trial=request['repair_trial'], strictly_smaller=True),
        latency_gate=dict(aggregation='minimum_recorded_controller_elapsed_ns',
            trials=[request['cold_trial']], strictly_faster=True))
    trials += [conversion, repair]
    require(len(trials) == 7 and sum(t['cpu_seconds']+2 for t in trials) == 1844,
        'complete reservations must total exactly 1844 seconds')
    external, equalities = external_prerequisites(root)
    campaign = Path(root)/'campaigns'/('independent_'+corpus+'_v31')
    return dict(schema=SCHEMA, status='draft_unregistered', confirmation=False, corpus=corpus,
        campaign=str(campaign), phase_cpu_cap_seconds=1900, maximum_complete_reservations_seconds=1844,
        execution_order=[t['id'] for t in trials], trials=trials,
        prerequisite_files=copy.deepcopy(descriptors),
        prerequisite_scientific_gate=dict(campaign=str(Path(root)/'campaigns/compressed_service_v31'),
            trial='repair-128-48', all_passed=True),
        prerequisite_policy=dict(campaign=str(Path(root)/'campaigns/compressed_service_v31'),
            trial='repair-128-48', fields=list(POLICY_FIELDS)),
        external_attempts=external, external_equalities=equalities,
        resource_shape_reference='ordered-prepare-256',
        source_ids=selected_root['source_ids'], requests=selected_root['requests'],
        compressed_request_id=selected_root['compressed_request_id'],
        registration_sequence=['independent_wikitext_v31', 'independent_c4_v31'],
        registration_policy='Finish and settle WikiText before registering C4; separate immutable ledger snapshots; no pooling.',
        prerequisite_resolution='Registration must verify all external receipts, equalities, successful compressed scientific gates, and exact registered policy; no pending output hashes are invented.',
        source_binding='Current sources are frozen at registration. The earlier proposed_source_inventory is historical context only.',
        scope='Two alternative single-source deletions from one two-source development root; fixed nearest-anchor DistilGPT2 target.',
        point_preservation='The first five trial dictionaries equal the historical selected root exactly, including balanced order.',
        selection_policy='Preserve all selected IDs and token bytes; no replacement, retokenization, outcome selection, or confirmation access.',
        cost_boundary='Complete controller transactions including loading, verification, serialization, and output rereads; preparation and a fresh 48-bit conversion for this root are additional setup costs; no 40-bit state or conversion is reused.',
        reporting='Preserve every individual latency, failed or unstarted row, exact output comparison, complete state bytes, certificate acceptance, fallback, and neural work.',
        statistical_unit='One root per corpus; two correlated requests per root; no population confidence interval from four requests.',
        lifetime_limit='No per-root original model-only preparation baseline; this pilot cannot establish lifetime break-even or isolated caching overhead.',
        stop_rule='No automatic retry, source replacement, policy retuning, allowance pooling, or promotion after a failed scientific gate.',
        execution_readiness='Conditional V31 metadata after the preserved V30 latency failure; unregistered and not authorized for execution by this file; V31 scientific prerequisites remain mandatory.')


def build(root=ROOT):
    """Read only frozen inputs and policy metadata; return both prospective specs."""
    root = Path(root).absolute()
    directory = root/'campaigns/independent_requests_v30_draft'
    objects, entries = {}, {}
    for name, expected in DRAFT_HASHES.items():
        objects[name], entries[name] = checked_json(directory/name, expected)
    policy_spec, policy_entry = checked_json(root/'campaigns/compressed_service_v31.spec.json',
        COMPRESSED_POLICY_SHA256)
    policy = checked_policy(policy_spec)
    draft, selection = objects['specification.json'], objects['selection.json']
    require(draft['confirmation'] is False and draft['source_inventory_is_registered'] is False,
        'historical draft is not an unregistered development selection')
    require(draft['selection'] == entries['selection.json'], 'historical selection descriptor differs')
    require({r['corpus'] for r in draft['roots']} == {'wikitext', 'c4'} and len(draft['roots']) == 2,
        'exactly the two historical roots are required')
    output = {}
    for selected_root in draft['roots']:
        corpus = selected_root['corpus']
        entry = entries[corpus+'-records.json']
        require(selected_root['records'] == selection['token_inputs'][corpus] == entry,
            'record provenance descriptor differs')
        descriptors = dict(draft=entries['specification.json'], selection=entries['selection.json'],
            records=entry, compressed_policy=policy_entry)
        output[corpus] = make_spec(root, selected_root, selection, objects[corpus+'-records.json'],
            descriptors, policy)
    return output


def write_specs(destination, specs):
    destination = Path(destination).absolute()
    require(not destination.exists(), 'output directory already exists; prospective specs are not overwritten')
    destination.mkdir(parents=True, exist_ok=False)
    for corpus in ('wikitext', 'c4'):
        with (destination/(corpus+'.spec.json')).open('xb') as stream:
            stream.write(canonical_json(specs[corpus]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'campaigns/independent_requests_v31_ready')
    args = parser.parse_args()
    specs = build()
    write_specs(args.output, specs)
    print(json.dumps(dict(specifications=[str(args.output/(name+'.spec.json')) for name in specs],
        transactions_per_root=7, maximum_complete_reservations_seconds=1844, phase_cpu_cap_seconds=1900,
        model_inference=False, registered=False, pending_prerequisites_resolved=False)))


if __name__ == '__main__':
    main()
