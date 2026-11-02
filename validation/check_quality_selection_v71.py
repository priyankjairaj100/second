"""Reconcile saved selection/hash metadata without reading text, tokens or models.

This separate stdlib implementation checks the metadata decisions, not the
correctness of tokenization or the actual corpus-to-hash correspondence.
"""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import re
import tarfile

R = Path(__file__).resolve().parents[1]
ARCHIVE = R / 'campaigns/csis_v71_selection_metadata_20261018_a.tar.gz'
REG = '3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
SHA = re.compile('[0-9a-f]{64}')
KEYS = {'registration', 'checks', 'data', 'audit', 'selection', 'inventory',
        'before', 'after', 'acquisition', 'frame_audit'}


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def info(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result, 'Duplicate JSON key'
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def load(path=ARCHIVE):
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        assert len(members) == len({m.name for m in members}) == 13
        assert sum(m.size for m in members) <= 16 * 2**20
        assert all(m.isfile() and '/' not in m.name and m.name.endswith('.json')
                   and m.size <= 8 * 2**20 for m in members)
        return {m.name: archive.extractfile(m).read() for m in members}


def reconcile_selection(x):
    before, after = x['before'], x['after']
    selection, inventory = x['selection'], x['inventory']
    full = x['frame_audit']['result']['complete_token_hashes']
    for excluded in (before, after):
        assert set(excluded) == {'ids', 'content', 'chunks'}
        assert all(type(values) is list and all(type(v) is str for v in values)
                   and values == sorted(set(values)) for values in excluded.values())
        assert all(SHA.fullmatch(v) for key in ('content', 'chunks') for v in excluded[key])
    prior = {k: set(v) for k, v in before.items()}
    seen = {k: set() for k in before}
    expected = {k: set(v) for k, v in before.items()}
    rows = inventory['candidates']
    assert len(rows) == len(full) == selection['candidate_articles'] == 3801
    assert inventory['frame'] == selection['frame']
    assert selection['frame']['complete_records'] == 3801
    assert selection['frame']['whole_gzip_trailer_verified'] is False
    assert [r['line_index'] for r in rows] == list(range(3801))
    assert [f['id'] for f in full] == [r['id'] for r in rows]
    content_keys = ('body_sha256', 'normalized_text_sha256', 'url_sha256')

    def reasons(row, protected):
        result = []
        if row['available_tokens'] < 128:
            result.append('short_record')
        if row['id'] in protected['ids']:
            result.append('id_overlap')
        if any(row[k] in protected['content'] for k in content_keys):
            result.append('content_or_url_overlap')
        if any(v in protected['chunks'] for v in row['token_prefixes'].values()):
            result.append('token_prefix_overlap')
        return result

    short = 0
    for row, token in zip(rows, full):
        assert set(row) == {'id', 'line_index', 'available_tokens', *content_keys,
                            'token_prefixes', 'eligible', 'exclusion_reasons'}
        assert row['id'] == 'c4:en:validation:shard1:line' + str(row['line_index'])
        assert type(row['available_tokens']) is int and row['available_tokens'] >= 0
        assert all(type(row[k]) is str and SHA.fullmatch(row[k]) for k in content_keys)
        count = min(128, row['available_tokens'])
        assert set(token) == {'id', 'token_count', 'tokens_sha256'}
        assert type(token['token_count']) is int and token['token_count'] == count
        assert type(token['tokens_sha256']) is str and SHA.fullmatch(token['tokens_sha256'])
        assert set(row['token_prefixes']) == {str(n) for n in (16, 32, 64, 128) if count >= n}
        assert all(type(v) is str and SHA.fullmatch(v) for v in row['token_prefixes'].values())
        if str(count) in row['token_prefixes']:
            assert token['tokens_sha256'] == row['token_prefixes'][str(count)]
        if count == 0:
            assert token['tokens_sha256'] == info(canonical([]))['sha256']
        why = reasons(row, prior)
        if not why:
            why = ['within_frame_' + reason for reason in reasons(row, seen)]
        assert type(row['eligible']) is bool and row['eligible'] == (not why)
        assert row['exclusion_reasons'] == why
        for destination in (seen, expected):
            destination['ids'].add(row['id'])
            destination['content'].update(row[k] for k in content_keys)
            destination['chunks'].update(row['token_prefixes'].values())
            if count:
                destination['chunks'].add(token['tokens_sha256'])
        short += count < 128
    assert after == {k: sorted(v) for k, v in expected.items()}, 'Exact full-frame union differs'
    assert short == x['frame_audit']['result']['short_records'] == 1021
    seed = selection['policy']['order_seed']
    assert seed == 'second-v68-untouched-quality-frame-before-loss:'
    eligible = sorted((r['id'] for r in rows if r['eligible']),
                      key=lambda rid: (hashlib.sha256((seed + rid).encode()).hexdigest(), rid))
    assert eligible == inventory['eligible_ids_in_sampling_order']
    assert len(eligible) == selection['eligible_articles'] == 2778
    selected = eligible[:320]
    assert selection['sampling_order_ids'] == selected
    assert selection['selected_articles'] == selection['requested_articles'] == 320
    byid = {r['id']: r for r in rows}
    expected_selected = [dict(
        id=rid, line_index=byid[rid]['line_index'], available_tokens=byid[rid]['available_tokens'],
        **{k: byid[rid][k] for k in content_keys}, token_offset=0, split='validation') for rid in selected]
    assert selection['selected_metadata'] == expected_selected
    history = x['historical-quality-exclusions']['excluded_from_future_confirmation_ids']
    assert len(history) == len(set(history)) == 60 and set(history) <= prior['ids']
    return dict(frame_records=3801,eligible_records=2778,selected_records=320,short_records=1021,
                historical_quality_ids_preserved=60,
                before_counts={k: len(v) for k, v in before.items()},
                after_counts={k: len(v) for k, v in after.items()},
                all_eligibility_reasons_recomputed=True,exact_inspected_frame_union=True,
                fixed_sampling_order_recomputed=True,selected_metadata_matches=True)


def check(files):
    observation = parse(files['collection.json'])
    assert observation['registration_sha256'] == REG
    assert observation['files'] == {n: info(b) for n, b in files.items() if n != 'collection.json'}
    assert files['registration-v71.json'] == (R / 'handoff/registration_v71_quality.json').read_bytes()
    assert info(files['registration-v71.json'])['sha256'] == REG
    assert observation['collector_sha256'] == info((R / 'validation/collect_quality_selection_v71.py').read_bytes())['sha256']
    assert all(observation[k] is False for k in ('raw_corpus_or_token_bodies_collected',
        'model_or_checkpoint_binaries_read', 'model_inference', 'job_submitted', 'selected_records_body_read'))
    p = parse(files['registration-v71.json'])
    x = {name: parse(files[name + '.json']) for name in KEYS | {'historical-quality-exclusions'}}
    for name in KEYS:
        entry = p['inputs']['quality'][name]
        assert info(files[name + '.json']) == {k: entry[k] for k in ('bytes', 'sha256')}
        assert observation['roles'][name + '.json'] == entry
        assert canonical(x[name]) == files[name + '.json']
    registration = x['registration']
    assert files['registration.json'] == (R / 'handoff/registration_v68.json').read_bytes()
    prior_entry = registration['inputs']['quality_exclusions']
    assert observation['roles']['historical-quality-exclusions.json'] == prior_entry
    assert info(files['historical-quality-exclusions.json']) == {k: prior_entry[k] for k in ('bytes', 'sha256')}
    for phase in ('checks', 'data', 'audit'):
        receipt = x[phase]
        assert receipt['status'] == 'complete' and receipt['error'] is None and receipt['trial'] == phase
        assert receipt['registration_sha256'] == info(files['registration.json'])['sha256']
        assert receipt['model_inference'] is False and receipt['quality_evaluation'] is False
    assert x['selection'] == x['data']['result']
    assert x['selection']['policy'] == registration['policy']
    assert x['selection']['exclusions_before'] == info(files['before.json'])
    for role, entry in [('source_prefix', p['inputs']['prefix']), ('records', p['inputs']['quality']['records'])]:
        assert x['selection'][role] == {k: entry[k] for k in ('bytes', 'sha256')}
    assert x['acquisition']['received'] == x['selection']['source_prefix']
    assert x['acquisition']['whole_source_sha256_is_metadata_only'] is True
    frame = x['frame_audit']
    assert frame['schema'] == 'complete-frame-exclusion-audit-v70' and frame['status'] == 'complete'
    assert frame['error'] is None and frame['job_id'] == '15404'
    assert frame['registration_sha256'] == info((R / 'handoff/registration_v70_frame.json').read_bytes())['sha256']
    assert frame['result']['actual_exact_exclusion_union'] is True
    for name in ('before', 'after', 'inventory', 'selection', 'acquisition'):
        assert frame['result']['inputs'][name] == info(files[name + '.json'])
    for name in ('records', 'prefix'):
        assert frame['result']['inputs'][name] == x['selection']['records' if name == 'records' else 'source_prefix']
    return x, reconcile_selection(x), observation


def main():
    files = load()
    x, facts, observation = check(files)
    probes = {}
    bad = copy.deepcopy(x)
    bad['after']['ids'].pop()
    mutations = [('removed_frame_id', bad)]
    bad = copy.deepcopy(x)
    bad['selection']['sampling_order_ids'][0:2] = list(reversed(bad['selection']['sampling_order_ids'][0:2]))
    mutations.append(('reordered_selected_ids', bad))
    bad = copy.deepcopy(x)
    bad['inventory']['candidates'][0]['eligible'] = not bad['inventory']['candidates'][0]['eligible']
    mutations.append(('changed_eligibility', bad))
    bad = copy.deepcopy(x)
    token = next(f for f in bad['frame_audit']['result']['complete_token_hashes']
                 if 0 < f['token_count'] < 128 and f['token_count'] not in (16, 32, 64))
    token['tokens_sha256'] = '0' * 64
    mutations.append(('changed_short_token_hash', bad))
    for name, changed in mutations:
        try:
            reconcile_selection(changed)
        except (AssertionError, KeyError, ValueError):
            probes[name] = 'rejected'
        else:
            raise AssertionError('Metadata mutation accepted: ' + name)
    report = dict(
        schema='v71-selection-metadata-reconciliation',
        verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        observed_at_utc=observation['captured_at_utc'],
        status='registered_metadata_and_selection_equations_verified',
        archive=dict(path=str(ARCHIVE.relative_to(R)), **info(ARCHIVE.read_bytes())),
        members=len(files), metadata_bytes=sum(map(len, files.values())),
        registration_sha256=REG, **facts, refusal_probes=probes,
        selected_token_bytes_read=False, source_prefix_read=False, retokenization_repeated=False,
        corpus_to_hash_correspondence_recomputed=False, empirical_likelihoods_read=False,
        scientific_quality_result=False, model_inference=False, new_job=False,
        full_historical_input_closure=False, review_component_prepared=False,
        scope='Actual registered hash/selection metadata and deterministic metadata decisions only. '
              'Actual V68/V70 saved-prefix/token audits remain the source for correspondence; '
              'this is not an independent tokenization or quality validation.')
    out = R / 'validation/v71_selection_metadata_reconciliation.json'
    with out.open('x') as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('status', 'archive', 'frame_records', 'eligible_records', 'selected_records', 'refusal_probes')}))


if __name__ == '__main__':
    main()
