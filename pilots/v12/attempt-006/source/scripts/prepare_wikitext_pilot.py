"""Prepare real article-disjoint pilot inputs. Never evaluate a model."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json, atomic_write


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def articles(rows):
    """A single equals pair denotes an article; nested headings stay inside it."""
    current = None
    for index, text in enumerate(rows):
        stripped = text.strip()
        if re.fullmatch(r"= [^=].*[^=] =", stripped) and not stripped.startswith("= ="):
            if current is not None:
                yield current
            current = dict(title=stripped[2:-2].strip(), start_row=index, rows=[])
        elif current is not None:
            current['rows'].append((index, text))
        elif stripped:
            raise ValueError('nonempty text before first article')
    if current is not None:
        yield current


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--tokenizer', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    import pyarrow.parquet as pq
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(args.tokenizer))
    if tokenizer.get_vocab_size() != 50257:
        raise ValueError('expected unchanged GPT-2 tokenizer vocabulary')
    raw_files = {}
    pools = {'development': [], 'confirmation': [], 'evaluation': []}
    seen = set()
    dropped = 0
    for split in ('train', 'validation'):
        file = args.data / f'wikitext-2-raw-v1/{split}-00000-of-00001.parquet'
        raw_files[str(file)] = {'sha256': sha(file.read_bytes()), 'bytes': file.stat().st_size}
        rows = pq.read_table(file, columns=['text']).column('text').to_pylist()
        for article in articles(rows):
            # Keep published characters. Join source rows without stripping their spaces.
            body = ''.join(text for _, text in article['rows'])
            normalized = ' '.join(body.split())
            key = sha(normalized.encode())
            if not normalized or key in seen:
                dropped += 1
                continue
            seen.add(key)
            tokens = tokenizer.encode(body, add_special_tokens=False).ids
            if len(tokens) < 128:
                dropped += 1
                continue
            if any(type(t) is not int or not 0 <= t < 50257 for t in tokens):
                raise ValueError('token outside vocabulary')
            # Fixed article-based partition. No selection uses a model result.
            phase = 'evaluation' if split == 'validation' else (
                'confirmation' if int(sha(('phase-v1:' + key).encode()), 16) % 5 == 0 else 'development')
            rid = f'wikitext2:{split}:article-row-{article["start_row"]}'
            pools[phase].append(dict(id=rid, document_id=rid, title=article['title'],
                source_split=split, start_row=article['start_row'], end_row=article['rows'][-1][0],
                normalized_text_sha256=key, body_sha256=sha(body.encode()), token_offset=0,
                available_tokens=len(tokens), tokens=tokens[:128]))
    for name in pools:
        pools[name].sort(key=lambda r: sha(('pilot-order-v1:' + r['id']).encode()))
    # Exclude exact prepared-chunk duplicates across phases before selecting roots.
    owner = {}
    for name in ('development', 'confirmation', 'evaluation'):
        filtered = []
        for row in pools[name]:
            h = sha(canonical_json(row['tokens']))
            if h in owner:
                dropped += 1
                continue
            owner[h] = name
            filtered.append(row)
        pools[name] = filtered
    roots = [[row['id'] for row in pools['development'][i*8:(i+1)*8]] for i in range(2)]
    provenance = dict(dataset_id='Salesforce/wikitext',
        dataset_revision='b08601e04326c79dfdd32d625aee71d232d685c3', split='train',
        license='card tags CC-BY-SA-3.0/GFDL; prose CC-BY-SA-4.0; raw redistribution withheld',
        tokenizer_id='distilbert/distilgpt2', tokenizer_revision='2290a62682d06624634c1f46a6ad5be0f47f38aa')
    record_map = {r['id']: r for rows in pools.values() for r in rows}
    pilot = dict(schema='prepared-token-records-v1', provenance=provenance,
        records=[dict(id=rid, tokens=record_map[rid]['tokens'][:16]) for rid in roots[0][:2]])
    selected = [record_map[rid] for root in roots for rid in root]
    audit = dict(schema='wikitext-pilot-input-audit-v1', source_files=raw_files,
        tokenizer_sha256=sha(args.tokenizer.read_bytes()), vocabulary_size=50257,
        normalization='published body row concatenation; no BOS/EOS; token offset zero; no repacking',
        article_rule='single equals heading; nested headings retained',
        phase_rule='train hash residue zero mod five confirmation; other train development; validation evaluation',
        counts={k:len(v) for k,v in pools.items()}, dropped_empty_short_or_duplicate=dropped,
        roots=roots, root_sampling='deterministic diagnostic partition; no population inference',
        selected_documents=[{k:v for k,v in row.items() if k!='tokens'} for row in selected],
        pool_hashes={k:sha(canonical_json(v)) for k,v in pools.items()},
        inference=False, model_work_executed=False,
        license_resolution='Source card conflict remains explicit. Do not redistribute source corpus.')
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in [('input-audit.json', audit), ('preflight-records.json', pilot)]:
        path = args.output / name
        data = canonical_json(value)
        if path.exists() and path.read_bytes() != data:
            raise ValueError('refuse to replace frozen input: ' + str(path))
        atomic_write(path, data)
    # Full token pools remain local; only selected pilot tokens enter the repository.
    atomic_write(args.data / 'prepared-pools.json', canonical_json(pools))
    print(json.dumps({'counts':audit['counts'], 'pilot_records':2, 'tokens_per_record':16}))


if __name__ == '__main__':
    main()
