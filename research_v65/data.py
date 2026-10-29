"""Bounded, outcome-blind selection; no model or likelihood execution."""
import json
import re
import zlib
from pathlib import Path
from urllib.request import Request,urlopen

from research_v45.data import Exclusions, c4_row
from src.run_store import canonical_json,digest

POLICY=dict(schema='disjoint-c4-development-root-v65',dataset='allenai/c4',
 revision='1588ec454efa1a09f29cd18ddd04fe05fc8653a2',shard=2,prefix_bytes=2*2**20,
 max_decompressed_bytes=64*2**20,max_records=20000,max_text_characters=4*2**20,
 sources=13,tokens=128,offset=0,bos_eos=False,order_key='second-v65-disjoint-c4-root:',
 confirmation=False,model_inference=False,scope='fixed bounded shard-two prefix, not corpus-uniform',
 deduplication='exact IDs, full/normalized text and URL hashes, exact token prefixes of lengths16/32/64/128; not semantic deduplication')
META_NAMES={'program.json','registration.json','plan.json','input-audit.json','preflight-records.json',
 'records.json','selection.json','c4-records.json','wikitext-records.json','quality-records.json',
 'full_service_records_v30.json','heldout_quality_v30_exclusions.json'}


def require(x,m):
    if not x:raise ValueError(m)


def info(b):return dict(bytes=len(b),sha256=digest(b))


def history_inventory(root):
    paths=[p for folder in ('pilots','campaigns','local_runs') for p in sorted((root/folder).rglob('*.json'))
           if p.name in META_NAMES and not {'worker','source'} & set(p.relative_to(root).parts)
           and root/'local_runs/disjoint-data-v65-20261016-a' not in p.parents]
    require(len(paths)<=5000,'Historical file census exceeds bound')
    total=0;result={}
    for p in paths:
        require(p.is_file() and not any(q.is_symlink() for q in (p,*p.parents)) and p.stat().st_size<=2*2**20,'Unsafe historical metadata')
        total+=p.stat().st_size;require(total<=64*2**20,'Historical metadata bound')
        b=p.read_bytes();require(len(b)==p.stat().st_size,'Changed metadata extent')
        result[str(p.relative_to(root))]=info(b)
    return result


def decode_prefix(raw):
    require(type(raw) is bytes and len(raw)<=POLICY['prefix_bytes'],'Compressed prefix bound')
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
    data=decoder.decompress(raw,POLICY['max_decompressed_bytes']+1)
    require(len(data)<=POLICY['max_decompressed_bytes'] and not decoder.unconsumed_tail,'Decompressed prefix bound')
    lines=data.split(b'\n')[:-1]
    require(0<len(lines)<=POLICY['max_records'],'Complete-record bound')
    rows=[]
    for line in lines:
        require(bool(line),'Empty complete record')
        x=json.loads(line)
        require(type(x) is dict and type(x.get('text')) is str and type(x.get('url')) is str
                and len(x['text'])<=POLICY['max_text_characters'] and len(x['url'])<=65536,'Invalid or oversized record')
        rows.append(x)
    return rows


def exclusions_from(protected,history):
    require(set(protected)=={'ids','content','chunks'} and all(type(v) is list for v in protected.values()),'Protected exclusion schema')
    result=Exclusions()
    require(all(type(x) is str for values in protected.values() for x in values),'Protected exclusion values')
    require(all(re.fullmatch('[0-9a-f]{64}',x) for key in ['content','chunks'] for x in protected[key]),'Invalid protected hashes')
    result.ids.update(protected['ids']);result.content.update(protected['content']);result.chunks.update(protected['chunks'])
    for x in history:result.visit(x)
    return result


def choose(candidates,excluded):
    require(len(candidates)<=POLICY['max_records'] and len({r['id'] for r in candidates})==len(candidates),'Candidate census')
    chosen=[]
    for row in sorted(candidates,key=lambda r:digest((POLICY['order_key']+r['id']).encode())):
        if len(row['tokens'])!=128 or not excluded.disjoint(row):continue
        excluded.add(row);chosen.append(row)
        if len(chosen)==13:break
    require(len(chosen)==13,'Insufficient disjoint sources; no expansion or replacement frame')
    return chosen


def acquire():
    url=f"https://huggingface.co/datasets/allenai/c4/resolve/{POLICY['revision']}/en/c4-train.00002-of-01024.json.gz"
    req=Request(url,headers={'Range':'bytes=0-2097151','User-Agent':'second-v65-bounded-data'})
    with urlopen(req,timeout=60) as response:
        require(response.status==206,'Bounded range response required')
        extent=response.headers.get('Content-Range','')
        require(re.fullmatch(r'bytes 0-2097151/[0-9]+',extent),'Wrong content range')
        raw=response.read(POLICY['prefix_bytes']+1)
    require(len(raw)==POLICY['prefix_bytes'],'Wrong acquired prefix extent')
    return raw,dict(url=url,content_range=extent,**info(raw))


def prepare(root,run,p):
    from tokenizers import Tokenizer
    import tokenizers
    require(tokenizers.__version__==p['tokenizers_version'],'Tokenizer runtime differs')
    prior=root/'local_runs/c4-data-v45-20261010-a';out=run/'outputs';out.mkdir(exist_ok=False)
    def save(name,value,raw=False):
        b=value if raw else canonical_json(value)
        with (out/name).open('xb') as f:f.write(b)
        return info(b)
    require(history_inventory(root)==p['history'],'Historical metadata inventory changed')
    protected=json.loads((prior/'outputs/exclusions.json').read_bytes())
    history=[json.loads((root/n).read_bytes()) for n in p['history']]
    excluded=exclusions_from(protected,history)
    tokenizer=Tokenizer.from_file(str(root/'tmp/models/distilgpt2/tokenizer.json'))
    require(tokenizer.get_vocab_size()==50257,'Tokenizer vocabulary differs')
    # Exclude the entire previously inspected candidate frame, not only its13 selected records.
    oldrows=decode_prefix((prior/'outputs/shard-1-prefix.gz.part').read_bytes())
    for i,row in enumerate(oldrows):excluded.add(c4_row(i,row,1,tokenizer))
    prior_selection=json.loads((prior/'outputs/selection.json').read_bytes())
    require(len(oldrows)==prior_selection['source_files']['new_c4']['complete_records'],'Historical frame census differs')
    before={k:sorted(getattr(excluded,k)) for k in ['ids','content','chunks']}
    protected_receipt=save('exclusions-before.json',before)
    raw,source=acquire();save('shard-2-prefix.gz.part',raw,True)
    rows=decode_prefix(raw);candidates=[c4_row(i,row,2,tokenizer) for i,row in enumerate(rows)]
    chosen=choose(candidates,excluded)
    records=sorted([dict(id=r['id'],tokens=r['tokens']) for r in chosen],key=lambda r:r['id'])
    records_receipt=save('records.json',dict(records=records))
    selection=dict(schema='disjoint-c4-selection-v65',policy=POLICY,source=source,candidate_records=len(candidates),
        sampling_order_ids=[r['id'] for r in chosen],selected_metadata=[{k:v for k,v in r.items() if k!='tokens'} for r in chosen],
        records=records_receipt,exclusions_before=protected_receipt,protected_counts={k:len(v) for k,v in before.items()},
        historical_shard_one_records_excluded=len(oldrows),historical_files=len(history),tokenizers_version=tokenizers.__version__,
        source_text_redistributed=False,exact_identity_and_prefix_overlap_checks_passed=True,semantic_deduplication=False,
        model_inference=False,quality_evaluation=False,confirmation=False)
    result=save('selection.json',selection)
    save('exclusions-after.json',{k:sorted(getattr(excluded,k)) for k in ['ids','content','chunks']})
    require(history_inventory(root)==p['history'],'Historical metadata changed during selection')
    return dict(status='complete',records=records_receipt,selection=result,source_prefix=source,
        selected_records=13,calibration_tokens=1664,model_inference=False,quality_evaluation=False,confirmation=False)


def audit(root,run,p):
    """Reconstruct selection from actual saved source bytes, with no new download."""
    from tokenizers import Tokenizer
    prior=root/'local_runs/c4-data-v45-20261010-a';out=run/'outputs'
    def read(name):return json.loads((out/name).read_bytes())
    selection=read('selection.json');receipt=json.loads((run/'data.json').read_bytes())
    require(receipt['status']=='complete' and receipt['result']['selection']==info((out/'selection.json').read_bytes()),'Complete bound data receipt required')
    require(selection['policy']==POLICY and history_inventory(root)==p['history'],'Policy or history changed')
    tokenizer=Tokenizer.from_file(str(root/'tmp/models/distilgpt2/tokenizer.json'))
    excluded=exclusions_from(json.loads((prior/'outputs/exclusions.json').read_bytes()),
        [json.loads((root/n).read_bytes()) for n in p['history']])
    oldrows=decode_prefix((prior/'outputs/shard-1-prefix.gz.part').read_bytes())
    for i,row in enumerate(oldrows):excluded.add(c4_row(i,row,1,tokenizer))
    before={k:sorted(getattr(excluded,k)) for k in ['ids','content','chunks']}
    require((out/'exclusions-before.json').read_bytes()==canonical_json(before),'Actual protected exclusions differ')
    require(selection['exclusions_before']==info((out/'exclusions-before.json').read_bytes()),'Exclusion commitment differs')
    raw=(out/'shard-2-prefix.gz.part').read_bytes()
    require(len(raw)==POLICY['prefix_bytes'] and all(selection['source'][k]==v for k,v in info(raw).items()),'Actual prefix differs')
    require(selection['source']['url']==f"https://huggingface.co/datasets/allenai/c4/resolve/{POLICY['revision']}/en/c4-train.00002-of-01024.json.gz"
            and re.fullmatch(r'bytes 0-2097151/[0-9]+',selection['source']['content_range']),'Source URL/range binding differs')
    rows=decode_prefix(raw);candidates=[c4_row(i,row,2,tokenizer) for i,row in enumerate(rows)]
    chosen=choose(candidates,excluded)
    records=sorted([dict(id=r['id'],tokens=r['tokens']) for r in chosen],key=lambda r:r['id'])
    require((out/'records.json').read_bytes()==canonical_json(dict(records=records)),'Actual selected token words/order differ')
    require(selection['records']==receipt['result']['records']==info((out/'records.json').read_bytes()),'Record commitment differs')
    require(selection['sampling_order_ids']==[r['id'] for r in chosen]
            and selection['selected_metadata']==[{k:v for k,v in r.items() if k!='tokens'} for r in chosen]
            and selection['candidate_records']==len(candidates),'Selected source provenance/order differs')
    require(selection['protected_counts']=={k:len(v) for k,v in before.items()}
            and selection['historical_shard_one_records_excluded']==len(oldrows)
            and selection['historical_files']==len(p['history']),'Protected census differs')
    require((out/'exclusions-after.json').read_bytes()==canonical_json({k:sorted(getattr(excluded,k)) for k in ['ids','content','chunks']}),'Successor exclusions differ')
    require(selection['model_inference'] is False and selection['quality_evaluation'] is False and selection['confirmation'] is False
            and selection['semantic_deduplication'] is False and selection['exact_identity_and_prefix_overlap_checks_passed'] is True,'Scope differs')
    return dict(status='verified',actual_saved_prefix_retokenized=True,actual_selected_records_equal=True,
        actual_exclusion_sets_equal=True,records=info((out/'records.json').read_bytes()),selection=info((out/'selection.json').read_bytes()),
        selected_records=13,calibration_tokens=1664,independent_implementation=False,model_inference=False,quality_evaluation=False,confirmation=False)
