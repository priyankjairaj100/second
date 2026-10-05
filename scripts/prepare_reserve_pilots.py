"""Prepare bounded C4 and LAMBADA input pilots without model evaluation."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json, digest, atomic_write


def main():
    from tokenizers import Tokenizer
    root = Path(__file__).resolve().parents[1]
    tokfile = root/'tmp/models/distilgpt2/tokenizer.json'
    tok = Tokenizer.from_file(str(tokfile))
    meta = json.loads((root/'pilots/v10/reserve-source-metadata.json').read_bytes())
    token_source = dict(tokenizer_id='distilbert/distilgpt2',
        tokenizer_revision='2290a62682d06624634c1f46a6ad5be0f47f38aa',
        tokenizer_sha256=digest(tokfile.read_bytes()))
    corpus = json.loads((root/'tmp/data/c4/records.json').read_bytes())
    rows=[]; seen=set(); dropped=0
    for index, record in enumerate(corpus):
        key=digest(' '.join(record['text'].split()).encode())
        tokens=tok.encode(record['text'],add_special_tokens=False).ids
        if key in seen or len(tokens)<128:
            dropped+=1;continue
        seen.add(key)
        rows.append(dict(id=f'c4:en:shard0:line{index}',tokens=tokens[:128],
            document_sha256=key,url_sha256=digest(record['url'].encode()),token_offset=0))
    rows.sort(key=lambda r:digest(('c4-pilot-v1:'+r['id']).encode()))
    prepared=dict(schema='prepared-token-records-v1',provenance=dict(dataset_id='allenai/c4',
        dataset_revision=meta['allenai/c4']['revision'],split='train-shard0-prefix',license='odc-by repository tag; source text rights vary',
        **{k:v for k,v in token_source.items() if k!='tokenizer_sha256'}),
        records=[dict(id=r['id'],tokens=r['tokens'][:16]) for r in rows[:2]])
    audit=dict(schema='reserve-input-pilot-v1',dataset='c4_bounded_english',status='input_checks_passed',
        **token_source,source_records=len(corpus),eligible_records=len(rows),dropped=dropped,
        selected_ids=[r['id'] for r in rows[:16]],tokenization='no BOS/EOS; first fixed 128 tokens; preflight uses first 16',
        selected_pool_sha256=digest(canonical_json(rows)),model_evaluated=False,
        sampling_frame='bounded compressed prefix of one train shard; no corpus-uniform or independent-domain claim',
        source_redistributed=False,final_confirmation_pool_frozen=False)
    out=root/'pilots/v10/c4';out.mkdir(parents=True,exist_ok=True)
    atomic_write(out/'preflight-records.json',canonical_json(prepared))
    atomic_write(out/'input-audit.json',canonical_json(audit))
    rawfile=root/'tmp/data/lambada/data/lambada_test_en.jsonl'
    raw=rawfile.read_bytes(); examples=[json.loads(line) for line in raw.splitlines() if line]
    order=sorted(range(len(examples)),key=lambda i:digest(f'lambada-pilot-v1:{i}'.encode()))[:16]
    details=[]
    for i in order:
        text=examples[i]['text']
        context,word=text.rsplit(' ',1)
        target=' '+word
        full=tok.encode(text,add_special_tokens=False).ids
        prefix=tok.encode(context,add_special_tokens=False).ids
        continuation=tok.encode(target,add_special_tokens=False).ids
        aligned=full==prefix+continuation
        details.append(dict(id=f'lambada:en:test:{i}',text_sha256=digest(text.encode()),
            context_tokens=len(prefix),target_tokens=len(continuation),prefix_aligned=aligned,
            nonempty_target=bool(continuation),complete_tokens_sha256=digest(canonical_json(full))))
    audit=dict(schema='reserve-input-pilot-v1',dataset='lambada_openai_en',
        status='input_checks_passed' if all(r['prefix_aligned'] and r['nonempty_target'] for r in details) else 'alignment_failure',
        **token_source,revision=meta['EleutherAI/lambada_openai']['revision'],source_sha256=digest(raw),source_bytes=len(raw),
        source_records=len(examples),selected=details,model_evaluated=False,
        scoring_rule='split at final ASCII space; include leading space; score every target subtoken; no last-token shortcut',
        future_greedy_rule='generate target subtoken count; compare the complete continuation; fixed EOS policy required',
        pilot_ids_excluded_from_final_evaluation=True,source_redistributed=False,
        remaining=['underlying book-text permissions','verified task evaluator','finite model execution','full-model exactness'])
    out=root/'pilots/v10/lambada';out.mkdir(parents=True,exist_ok=True)
    atomic_write(out/'input-audit.json',canonical_json(audit))
    print(json.dumps({'c4_eligible':len(rows),'lambada_examples':len(examples),
        'lambada_pilot':len(details),'lambada_aligned':sum(x['prefix_aligned'] for x in details)}))


if __name__=='__main__':
    main()
