"""Recover pinned data and select real development articles before model work."""
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen

from research_v39.policy import ROOT, ORIGINAL_RECORDS, TOKENS, require, read, sha, new
from src.run_store import canonical_json, digest

ASSETS = {
    'tokenizer': dict(path='tmp/models/distilgpt2/tokenizer.json',
        url='https://huggingface.co/distilbert/distilgpt2/resolve/2290a62682d06624634c1f46a6ad5be0f47f38aa/tokenizer.json',
        sha256='8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6', bytes=1355256),
    'train': dict(path='tmp/data/wikitext2/wikitext-2-raw-v1/train-00000-of-00001.parquet',
        url='https://huggingface.co/datasets/Salesforce/wikitext/resolve/b08601e04326c79dfdd32d625aee71d232d685c3/wikitext-2-raw-v1/train-00000-of-00001.parquet',
        sha256='e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7', bytes=6357543),
}


def recover_assets():
    from scripts.recover_assets_v32 import restore_checkpoint
    checkpoint = restore_checkpoint()
    for entry in ASSETS.values():
        path = ROOT / entry['path']
        if path.exists():
            require(path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], 'Existing asset differs')
            continue
        request = Request(entry['url'], headers={'User-Agent': 'calibration-scale-v39'})
        with urlopen(request, timeout=60) as response:
            require(response.status == 200, 'Asset response is incomplete')
            payload = response.read(entry['bytes'] + 1)
        require(len(payload) == entry['bytes'] and digest(payload) == entry['sha256'], 'Asset identity differs')
        new(path, payload, raw=True)
    return dict(checkpoint=checkpoint, data=ASSETS, no_model_inference=True)


def select(output, artifact):
    import pyarrow.parquet as pq
    from tokenizers import Tokenizer
    from scripts.prepare_wikitext_pilot import articles
    for entry in ASSETS.values():
        path = ROOT / entry['path']
        require(path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], 'Data asset changed')
    tokenizer = Tokenizer.from_file(str(ROOT / ASSETS['tokenizer']['path']))
    require(tokenizer.get_vocab_size() == 50257, 'Vocabulary differs')
    texts = pq.read_table(ROOT / ASSETS['train']['path'], columns=['text']).column('text').to_pylist()
    seen, candidates = set(), []
    for article in articles(texts):
        body = ''.join(text for _, text in article['rows'])
        normalized = ' '.join(body.split())
        key = digest(normalized.encode())
        if not normalized or key in seen:
            continue
        seen.add(key)
        # The existing article partition reserves residue zero for confirmation.
        if int(digest(('phase-v1:' + key).encode()), 16) % 5 == 0:
            continue
        tokens = tokenizer.encode(body, add_special_tokens=False).ids
        if len(tokens) < TOKENS:
            continue
        require(all(type(t) is int and 0 <= t < 50257 for t in tokens), 'Invalid token')
        rid = f'wikitext2:train:article-row-{article["start_row"]}'
        candidates.append(dict(id=rid, tokens=tokens[:TOKENS], body_sha256=digest(body.encode()),
            normalized_text_sha256=key, available_tokens=len(tokens), start_row=article['start_row']))
    candidates.sort(key=lambda row: digest(('pilot-order-v1:' + row['id']).encode()))
    unique, token_hashes = [], set()
    for row in candidates:
        token_hash = digest(canonical_json(row['tokens']))
        if token_hash not in token_hashes:
            unique.append(row)
            token_hashes.add(token_hash)
    selected = unique[:ORIGINAL_RECORDS]
    require(len(selected) == ORIGINAL_RECORDS, 'Insufficient real development articles')
    records = sorted([dict(id=row['id'], tokens=row['tokens']) for row in selected], key=lambda row: row['id'])
    selection = dict(schema='scale-development-selection-v39', original_records=ORIGINAL_RECORDS,
        tokens_per_record=TOKENS, sampling_order_ids=[row['id'] for row in selected],
        selected_metadata=[{k: v for k, v in row.items() if k != 'tokens'} for row in selected],
        source_files=ASSETS, candidate_articles=len(unique), inference=False, confirmation=False,
        scope='Deterministic development sample. Some articles were exposed in earlier development; no independent confirmation.',
        phase_rule='Existing train article residue rule; confirmation residue zero excluded.',
        selection_rule='First thirteen distinct development token chunks in the existing pilot hash order.',
        normalization='Published article-body concatenation, no BOS/EOS, first 128 tokens, no repeated or synthetic rows.')
    artifact('records.json', canonical_json({'records': records}))
    artifact('selection.json', canonical_json(selection))
    return dict(selected_record_count=len(records), tokens_per_record=TOKENS, original_tokens=ORIGINAL_RECORDS * TOKENS,
                selected_ids=[row['id'] for row in records], model_inference_performed=False)
