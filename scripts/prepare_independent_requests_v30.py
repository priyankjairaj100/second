"""Prepare two outcome-blind development roots; never load or evaluate a model."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.run_store import canonical_json, digest

ID_PATTERN = re.compile(r'(?:wikitext2:(?:train|validation):article-row-[0-9]+|c4:en:shard0:line[0-9]+)')
HISTORY_NAMES = {'plan.json', 'program.json', 'input-audit.json', 'preflight-records.json'}
POLICY = dict(schema='independent-request-selection-policy-v30', model_inference=False,
    selection_key='independent-requests-v30:', tokens_per_source=128, sources_per_root=2,
    original_normalization=256, source_token_offset=0, bos_eos=False,
    c4_scope='complete records from the cached two-MiB prefix of English training shard zero',
    roots_are_population_samples=False, confirmation=False)


def descriptor(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        hashed = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), sha256=hashed, bytes=path.stat().st_size)


def read(path):
    return json.loads(Path(path).read_bytes())


def history_exclusions(root):
    """Read only earlier selection and plan metadata; never inspect outcomes."""
    ids, manifests = set(), {}
    for folder in ('pilots', 'campaigns'):
        for path in sorted((root/folder).rglob('*.json')):
            if path.name not in HISTORY_NAMES or {'source', 'worker', 'outputs'} & set(path.parts):
                continue
            raw = path.read_bytes()
            found = set(ID_PATTERN.findall(raw.decode('utf-8')))
            if found:
                ids.update(found)
                manifests[str(path.relative_to(root))] = descriptor(path)
    return ids, manifests


def check_prefix(prefix, records, acquisition):
    if len(prefix) != acquisition['prefix_bytes'] or digest(prefix) != acquisition['prefix_sha256']:
        raise ValueError('cached compressed C4 prefix differs from acquisition evidence')
    decoded = zlib.decompressobj(16+zlib.MAX_WBITS).decompress(prefix, 32*2**20)
    complete = []
    for line in decoded.splitlines():
        try:
            complete.append(json.loads(line))
        except json.JSONDecodeError:
            break
    if complete != records or len(records) != acquisition['complete_records']:
        raise ValueError('C4 records differ from complete records in the acquired prefix')


def c4_eligible(records, encode):
    """Reproduce the historical length and normalized-document duplicate rules."""
    seen, rows = set(), []
    for index, record in enumerate(records):
        document_hash = digest(' '.join(record['text'].split()).encode())
        tokens = list(encode(record['text']))
        if document_hash in seen or len(tokens) < 128:
            continue
        if any(type(token) is not int or not 0 <= token < 50257 for token in tokens):
            raise ValueError('token is outside the unchanged GPT-2 vocabulary')
        seen.add(document_hash)
        rows.append(dict(id=f'c4:en:shard0:line{index}', tokens=tokens[:128],
            document_sha256=document_hash, url_sha256=digest(record['url'].encode()), token_offset=0))
    rows.sort(key=lambda row:digest(('c4-pilot-v1:'+row['id']).encode()))
    return rows


def choose_root(rows, corpus, excluded_ids, forbidden_chunks=(), forbidden_documents=()):
    selected = []
    chunks, documents, urls = set(forbidden_chunks), set(forbidden_documents), set()
    candidates = sorted(rows, key=lambda row:digest((POLICY['selection_key']+corpus+':'+row['id']).encode()))
    for row in candidates:
        if row['id'] in excluded_ids:
            continue
        tokens = row['tokens'][:128]
        if len(tokens) != 128 or any(type(token) is not int or not 0 <= token < 50257 for token in tokens):
            raise ValueError('eligible source has invalid 128-token prefix')
        chunk = digest(canonical_json(tokens))
        document = row.get('normalized_text_sha256', row.get('document_sha256'))
        url = row.get('url_sha256')
        if not document or chunk in chunks or document in documents or url is not None and url in urls:
            continue
        chunks.add(chunk); documents.add(document)
        if url is not None:
            urls.add(url)
        selected.append(row)
        if len(selected) == 2:
            break
    if len(selected) != 2:
        raise ValueError('fewer than two disjoint eligible sources remain')
    return selected


def point_trials(corpus, rows, common, records_binding):
    """Return ordered lossless preparation and both prespecified paired deletions."""
    ids = sorted(row['id'] for row in rows)
    root_id = corpus+'-root'
    base = dict(common, original_token_count=256, use_candidates=False,
                inputs=dict(common['inputs'], records={k:records_binding[k] for k in ('path', 'sha256')}))
    prep = dict(id=root_id+'-prepare', script='run_ordered_service_v30.py', cpu_seconds=450,
        wall_seconds=600, plan=dict(base, method='direct_fresh', record_ids=ids, deleted_ids=[]))
    trials = [prep]
    requests = []
    for index, deleted in enumerate(ids):
        retained = [rid for rid in ids if rid != deleted]
        name = f'{corpus}-delete-{index}'
        # Balance method order across the two requests and across corpora.
        order = ('repair', 'cold') if (index+(corpus == 'c4')) % 2 == 0 else ('cold', 'repair')
        earlier = None
        for label in order:
            trial = dict(id=name+'-'+label, script='run_ordered_service_v30.py',
                cpu_seconds=180 if label == 'repair' else 300,
                wall_seconds=240 if label == 'repair' else 400,
                depends=[dict(trial=prep['id'], equals=dict(complete_model=True, complete_state=True))],
                plan=dict(base, method='repair' if label == 'repair' else 'model_only_fresh',
                          record_ids=retained, deleted_ids=[deleted]))
            if label == 'repair':
                trial['inputs_from_trial'] = dict(preparation_completion=dict(trial=prep['id'], completion=True),
                    prior_state=dict(trial=prep['id'], artifact='state'))
            if earlier is not None:
                trial['depends'].append(dict(trial=earlier, equals=dict(complete_model=True)))
                trial['compare_to'] = [dict(trial=earlier, artifacts=['model'])]
            trials.append(trial); earlier = trial['id']
        requests.append(dict(id=name, retained_ids=retained, deleted_ids=[deleted],
            repair_trial=name+'-repair', cold_trial=name+'-cold', method_order=list(order)))
    return trials, requests


def build(root, destination):
    from tokenizers import Tokenizer
    import tokenizers
    from src.experiment_inventory import source_hashes
    started = time.process_time_ns()
    paths = dict(pools=root/'tmp/data/wikitext2/prepared-pools.json',
        tokenizer=root/'tmp/models/distilgpt2/tokenizer.json',
        config=root/'tmp/models/distilgpt2/config.json', weights=root/'tmp/models/distilgpt2/model.safetensors',
        c4_records=root/'tmp/data/c4/records.json', c4_prefix=root/'tmp/data/c4/prefix.gz.part',
        c4_acquisition=root/'pilots/v10/c4-acquisition.json',
        c4_audit=root/'pilots/v10/c4/input-audit.json', wiki_audit=root/'pilots/v10/wikitext2/input-audit.json',
        source_metadata=root/'pilots/v10/reserve-source-metadata.json',
        quality_registration=root/'campaigns/quality_v30/registration.json',
        ordered_program=root/'campaigns/ordered_service_v30/program.json',
        target_reference=root/'campaigns/ordered_service_v30/attempts/prepare-256/outputs/fixed-target.json')
    inputs = {key:descriptor(path) for key,path in paths.items()}
    pools, wiki_audit, c4_audit = read(paths['pools']), read(paths['wiki_audit']), read(paths['c4_audit'])
    if any(digest(canonical_json(pools[key])) != value for key,value in wiki_audit['pool_hashes'].items()):
        raise ValueError('WikiText pools differ from original preparation')
    if inputs['tokenizer']['sha256'] != wiki_audit['tokenizer_sha256'] or inputs['tokenizer']['sha256'] != c4_audit['tokenizer_sha256']:
        raise ValueError('tokenizer differs from historical corpus preparation')
    corpus = read(paths['c4_records'])
    acquisition = read(paths['c4_acquisition'])
    if acquisition['revision'] != read(paths['source_metadata'])['allenai/c4']['revision']:
        raise ValueError('C4 acquisition and repository revisions differ')
    check_prefix(paths['c4_prefix'].read_bytes(), corpus, acquisition)
    tokenizer = Tokenizer.from_file(str(paths['tokenizer']))
    if tokenizer.get_vocab_size() != 50257:
        raise ValueError('tokenizer vocabulary changed')
    eligible = c4_eligible(corpus, lambda text:tokenizer.encode(text, add_special_tokens=False).ids)
    if len(eligible) != c4_audit['eligible_records'] or digest(canonical_json(eligible)) != c4_audit['selected_pool_sha256']:
        raise ValueError('C4 tokenization differs from the historical complete eligible pool')
    excluded, prior = history_exclusions(root)
    quality_excluded = read(paths['quality_registration'])['excluded_from_future_confirmation_ids']
    if len(set(quality_excluded)) != 20:
        raise ValueError('twenty existing quality exclusions must remain intact')
    excluded.update(quality_excluded)
    wiki = choose_root(pools['development'], 'wikitext', excluded)
    all_wiki = sum(pools.values(), [])
    protected_chunks = [digest(canonical_json(row['tokens'][:128])) for row in all_wiki]
    protected_documents = [row['normalized_text_sha256'] for row in all_wiki]
    protected_chunks += [digest(canonical_json(row['tokens'])) for row in eligible if row['id'] in excluded]
    c4 = choose_root(eligible, 'c4', excluded, protected_chunks, protected_documents)
    groups = dict(wikitext=wiki, c4=c4)
    records = {key:canonical_json(dict(records=sorted(
        [dict(id=row['id'], tokens=row['tokens'][:128]) for row in rows], key=lambda row:row['id'])))
        for key,rows in groups.items()}
    record_bindings = {key:dict(path=str(destination/(key+'-records.json')), bytes=len(raw), sha256=digest(raw))
                       for key,raw in records.items()}
    ordered = read(paths['ordered_program'])
    old = next(trial['plan'] for trial in ordered['trials'] if trial['id'] == 'prepare-256')
    common = {key:old[key] for key in ('checkpoint', 'solver_backend', 'solver_budget', 'max_point_work_units')}
    common.update(expected_target=inputs['target_reference']['sha256'],
        inputs={key:{k:inputs[key][k] for k in ('path','sha256')} for key in ('config','weights')})
    root_specs = []
    for key,rows in groups.items():
        trials, requests = point_trials(key, rows, common, record_bindings[key])
        root_specs.append(dict(id=key+'-root', corpus=key, records=record_bindings[key],
            source_ids=sorted(row['id'] for row in rows), point_trials=trials, requests=requests,
            compressed_request_id=requests[0]['id'],
            compressed_policy=dict(worker='run_compressed_service_v30.py', decoder_backend='ordered', codec_bits=40,
                block_size=256, use_candidates=False, original_token_count=256,
                conversion_cpu_seconds=120, conversion_wall_seconds=180,
                repair_cpu_seconds=300, repair_wall_seconds=420,
                source='copy the complete successful compressed128 point/certificate policy without retuning',
                conversion_inputs=['records','lossless_state','lossless_model','lossless_completion'],
                repair_inputs=['records','config','weights','prior_state','compressed_preparation_completion','reference_completion'],
                retained_reference=requests[0]['cold_trial'],
                expected_target=common['expected_target'],
                execution_readiness='template only; compressed128 prerequisite must bind exact numerical budgets before registration'),
            phase_cpu_ceiling_seconds=1900, maximum_complete_reservations_seconds=1844))
    selection = dict(schema='independent-request-input-audit-v30', status='draft_inputs_prepared', policy=POLICY,
        input_files=inputs, earlier_selection_and_plan_files=prior, earlier_designated_ids=sorted(excluded),
        counts=dict(wikitext_development=len(pools['development']), c4_source=len(corpus), c4_eligible=len(eligible)),
        selected={key:[{k:v for k,v in row.items() if k not in ('tokens','title')} for row in rows]
                  for key,rows in groups.items()},
        selection_order={key:[row['id'] for row in rows] for key,rows in groups.items()},
        preserved_quality_exclusions=quality_excluded,
        prospective_additional_development_ids=sorted(row['id'] for rows in groups.values() for row in rows),
        token_inputs=record_bindings, source_text_redistributed=False,
        tokenizer_library_version=tokenizers.__version__, preparer_source=descriptor(Path(__file__)),
        preprocessing_cpu_ns=time.process_time_ns()-started, empirical_worker_cpu_seconds=0)
    specification = dict(schema='independent-request-pilot-draft-v30', status='draft_unregistered', confirmation=False,
        scientific_promotion=False, roots=root_specs,
        prerequisite_gates=[
            'ordered full-service campaign complete; original/retained models match scalar references; all timing receipts settled',
            'compressed128 ordered pilot complete; exact retained model; complete-state savings; prospective timing guard passes',
            'matched follow-up quality passes both fixed128/sequential128 primary and fixed128/fixed16 safety gates'],
        admission='no inference or registration by this preparer; resolve and hash all gate evidence before freezing either root',
        comparison='one optimized lossless repair/cold pair per deletion; one predetermined compressed repair per root',
        statistical_unit='two disjoint development roots; two correlated requests per root; no population interval',
        accounting='charge original preparation, conversion, and every full request; no lifetime break-even claim without original model-only control',
        success='complete exactness, request-level timing, and total storage are separate; keep every loss, refusal, and unstarted row',
        extension_rule='larger or repeated runs require a new prospective phase; never replace either selected root after outcomes',
        maximum_total_phase_cpu_seconds=3800,
        proposed_source_inventory=source_hashes(root), source_inventory_is_registered=False,
        worker_sources={name:descriptor(root/'scripts'/name) for name in
                        ('run_ordered_service_v30.py','run_compressed_service_v30.py')},
        scope='fixed nearest-anchor target on DistilGPT2; C4 shard-prefix development replication, not corpus-wide or sequential repair evidence')
    return records, selection, specification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'campaigns/independent_requests_v30_draft')
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.exists():
        raise ValueError('refuse to overwrite a prepared draft')
    records, selection, spec = build(ROOT, destination)
    destination.mkdir(parents=True, exist_ok=False)
    for key,raw in records.items():
        (destination/(key+'-records.json')).write_bytes(raw)
    (destination/'selection.json').write_bytes(canonical_json(selection))
    spec['selection'] = descriptor(destination/'selection.json')
    (destination/'specification.json').write_bytes(canonical_json(spec))
    print(json.dumps(dict(status='draft_unregistered', model_inference=False, output=str(destination),
        selected_ids=selection['prospective_additional_development_ids'], preprocessing_cpu_ns=selection['preprocessing_cpu_ns'])))


if __name__ == '__main__':
    main()
