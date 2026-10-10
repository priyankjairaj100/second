"""Outcome-blind C4 shard-one selection; no checkpoint or model execution."""
from pathlib import Path
import re
import zlib
from urllib.request import Request, urlopen

from research_v43.campaign import ROOT, require, read, sha, new
from src.run_store import canonical_json, digest

REVISION = '1588ec454efa1a09f29cd18ddd04fe05fc8653a2'
WIKI_REVISION = 'b08601e04326c79dfdd32d625aee71d232d685c3'
TOKENIZER_SHA = '8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6'
PREFIX_BYTES = 2*2**20
POLICY = dict(schema='independent-c4-scale-input-policy-v45', dataset='allenai/c4',
    revision=REVISION, shard=1, prefix_bytes=PREFIX_BYTES, max_decompressed_bytes=64*2**20,
    order_key='second-v45-independent-c4-root:', sources=13, tokens=128, bos_eos=False,
    offset=0, confirmation=False, no_model_inference=True,
    scope='Deterministic hash order within a two-MiB compressed shard-one prefix; not corpus uniform.',
    exclusion='All prior archived designated IDs/content commitments/token prefixes; entire historical C4 shard-zero prefix; all historical WikiText train/validation prepared pools. Exact hashes only, not semantic deduplication.')
META_NAMES = {'program.json','registration.json','plan.json','input-audit.json',
    'preflight-records.json','records.json','selection.json','c4-records.json',
    'wikitext-records.json','quality-records.json','full_service_records_v30.json',
    'heldout_quality_v30_exclusions.json'}
ID_PATTERN = re.compile(r'(?:wikitext2:(?:train|validation|test):article-row-[0-9]+|c4:en:shard[0-9]+:line[0-9]+)')


def history_files():
    return [p for folder in ('pilots','campaigns') for p in sorted((ROOT/folder).rglob('*.json'))
        if p.name in META_NAMES and not {'worker','source'} & set(p.parts)]


def inventory():
    return {str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in history_files()}


class Exclusions:
    def __init__(self):
        self.ids, self.content, self.chunks = set(), set(), set()

    def tokens(self, tokens):
        if isinstance(tokens,list) and tokens and all(type(t) is int and 0<=t<50257 for t in tokens):
            for n in (16,32,64,128):
                if len(tokens)>=n:self.chunks.add(digest(canonical_json(tokens[:n])))
            self.chunks.add(digest(canonical_json(tokens)))

    def visit(self, value, key=''):
        if isinstance(value,dict):
            for k,v in value.items():self.visit(v,k)
        elif isinstance(value,list):
            if key=='tokens':self.tokens(value)
            else:
                for v in value:self.visit(v,key)
        elif isinstance(value,str):
            self.ids.update(ID_PATTERN.findall(value))
            if re.fullmatch('[0-9a-f]{64}',value) and any(s in key for s in ('text','body','document','url','token')):
                self.content.add(value)

    def add(self, row):
        self.ids.add(row['id']);self.tokens(row['tokens'])
        self.content.update(row[k] for k in ('normalized_text_sha256','body_sha256','url_sha256') if k in row)

    def disjoint(self, row):
        return (row['id'] not in self.ids and
            not any(row.get(k) in self.content for k in ('normalized_text_sha256','body_sha256','url_sha256')) and
            not any(digest(canonical_json(row['tokens'][:n])) in self.chunks for n in (16,32,64,128)))


def decode_prefix(raw):
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
    data=decoder.decompress(raw, POLICY['max_decompressed_bytes']+1)
    require(len(data)<=POLICY['max_decompressed_bytes'] and not decoder.unconsumed_tail,
        'Decompressed prefix exceeds bound')
    import json
    rows=[json.loads(line) for line in data.split(b'\n')[:-1] if line]
    require(rows and all(isinstance(r,dict) and isinstance(r.get('text'),str) and isinstance(r.get('url'),str) for r in rows),
        'Invalid complete C4 records')
    return rows


def acquire_prefix(shard, destination):
    url=f'https://huggingface.co/datasets/allenai/c4/resolve/{REVISION}/en/c4-train.{shard:05d}-of-01024.json.gz'
    request=Request(url,headers={'Range':f'bytes=0-{PREFIX_BYTES-1}','User-Agent':'second-v45-bounded-data'})
    with urlopen(request,timeout=60) as response:
        require(response.status==206,'Server did not honor bounded prefix request')
        content_range=response.headers.get('Content-Range','')
        require(re.fullmatch(r'bytes 0-2097151/[0-9]+',content_range),'Unexpected prefix range')
        raw=response.read(PREFIX_BYTES+1)
    require(len(raw)==PREFIX_BYTES,'Prefix extent differs')
    rows=decode_prefix(raw)
    if shard==0:
        old=read(ROOT/'pilots/v10/c4-acquisition.json')
        require(digest(raw)==old['prefix_sha256'] and len(rows)==old['complete_records'],
            'Historical C4 frame differs')
    new(destination/f'shard-{shard}-prefix.gz.part',raw,raw=True)
    return rows,dict(url=url,revision=REVISION,content_range=content_range,bytes=len(raw),sha256=digest(raw),complete_records=len(rows))


def c4_row(index, item, shard, tokenizer):
    tokens=tokenizer.encode(item['text'],add_special_tokens=False).ids
    require(all(type(t) is int and 0<=t<50257 for t in tokens),'Tokenizer vocabulary differs')
    return dict(id=f'c4:en:shard{shard}:line{index}',tokens=tokens[:128],available_tokens=len(tokens),
        body_sha256=digest(item['text'].encode()),normalized_text_sha256=digest(' '.join(item['text'].split()).encode()),
        url_sha256=digest(item['url'].encode()),token_offset=0)


def protected_wiki(tokenizer,destination):
    """Reconstruct and verify historical prepared-pool hashes; evaluate no model."""
    import pyarrow.parquet as pq
    from scripts.prepare_wikitext_pilot import articles
    audit=read(ROOT/'pilots/v10/wikitext2/input-audit.json')
    pools={k:[] for k in ('development','confirmation','evaluation')};seen=set();bindings={}
    for split in ('train','validation'):
        filename=f'{split}-00000-of-00001.parquet'
        expected=next(v for k,v in audit['source_files'].items() if k.endswith('/'+filename))
        path=ROOT/'tmp/data/wikitext2/wikitext-2-raw-v1'/filename
        if not path.exists():
            url=f'https://huggingface.co/datasets/Salesforce/wikitext/resolve/{WIKI_REVISION}/wikitext-2-raw-v1/{filename}'
            with urlopen(Request(url,headers={'User-Agent':'second-v45-overlap-audit'}),timeout=60) as response:
                require(response.status==200,'Historical WikiText asset response differs')
                raw=response.read(expected['bytes']+1)
            require(len(raw)==expected['bytes'] and digest(raw)==expected['sha256'],'Historical WikiText bytes differ')
            new(path,raw,raw=True)
        require(path.stat().st_size==expected['bytes'] and sha(path)==expected['sha256'],'Historical WikiText pin differs')
        bindings[split]=dict(path=str(path),**expected)
        texts=pq.read_table(path,columns=['text']).column('text').to_pylist()
        for article in articles(texts):
            body=''.join(text for _,text in article['rows']);normalized=' '.join(body.split());key=digest(normalized.encode())
            if not normalized or key in seen:continue
            seen.add(key);tokens=tokenizer.encode(body,add_special_tokens=False).ids
            if len(tokens)<128:continue
            phase='evaluation' if split=='validation' else ('confirmation' if int(digest(('phase-v1:'+key).encode()),16)%5==0 else 'development')
            rid=f'wikitext2:{split}:article-row-{article["start_row"]}'
            pools[phase].append(dict(id=rid,document_id=rid,title=article['title'],source_split=split,
                start_row=article['start_row'],end_row=article['rows'][-1][0],normalized_text_sha256=key,
                body_sha256=digest(body.encode()),token_offset=0,available_tokens=len(tokens),tokens=tokens[:128]))
    owner=set()
    for phase in pools:
        pools[phase].sort(key=lambda r:digest(('pilot-order-v1:'+r['id']).encode()))
        filtered=[]
        for row in pools[phase]:
            h=digest(canonical_json(row['tokens']))
            if h not in owner:owner.add(h);filtered.append(row)
        pools[phase]=filtered
        require(digest(canonical_json(filtered))==audit['pool_hashes'][phase],'Historical WikiText pool reconstruction differs')
    return pools,bindings


def choose(candidates, exclusions):
    selected=[]
    for row in sorted(candidates,key=lambda r:digest((POLICY['order_key']+r['id']).encode())):
        if len(row['tokens'])!=128 or not exclusions.disjoint(row):continue
        exclusions.add(row);selected.append(row)
        if len(selected)==13:break
    require(len(selected)==13,'Insufficient independent eligible sources; do not expand or replace frame automatically')
    return selected


def prepare(destination, historical):
    import tokenizers
    from tokenizers import Tokenizer
    destination=Path(destination);require(not destination.exists(),'Data output is one-use')
    require(inventory()==historical,'Historical source/exclusion metadata changed')
    tokenizer_path=ROOT/'tmp/models/distilgpt2/tokenizer.json'
    require(sha(tokenizer_path)==TOKENIZER_SHA,'Tokenizer bytes differ')
    tokenizer=Tokenizer.from_file(str(tokenizer_path));require(tokenizer.get_vocab_size()==50257,'Vocabulary differs')
    exclusions=Exclusions()
    for name in historical:exclusions.visit(read(ROOT/name))
    original_counts=dict(ids=len(exclusions.ids),content=len(exclusions.content),chunks=len(exclusions.chunks))
    destination.mkdir(parents=True)
    old,old_binding=acquire_prefix(0,destination)
    for index,row in enumerate(old):exclusions.add(c4_row(index,row,0,tokenizer))
    pools,wiki_bindings=protected_wiki(tokenizer,destination)
    for rows in pools.values():
        for row in rows:exclusions.add(row)
    protected=dict(ids=sorted(exclusions.ids),content=sorted(exclusions.content),chunks=sorted(exclusions.chunks))
    new(destination/'exclusions.json',protected)
    newrows,new_binding=acquire_prefix(1,destination)
    candidates=[c4_row(i,row,1,tokenizer) for i,row in enumerate(newrows)]
    selected=choose(candidates,exclusions)
    records=sorted([dict(id=r['id'],tokens=r['tokens']) for r in selected],key=lambda r:r['id'])
    new(destination/'records.json',dict(records=records))
    selection=dict(schema='independent-c4-scale-selection-v45',policy=POLICY,
        historical_files=historical,initial_archived_exclusion_counts=original_counts,
        protected_exclusion_sha256=sha(destination/'exclusions.json'),
        protected_counts={k:len(v) for k,v in protected.items()},
        all_historical_wiki_pool_hashes_verified=True,wiki_pool_sizes={k:len(v) for k,v in pools.items()},
        source_files=dict(historical_c4=old_binding,new_c4=new_binding,wiki=wiki_bindings,
            tokenizer=dict(path=str(tokenizer_path),sha256=TOKENIZER_SHA,bytes=tokenizer_path.stat().st_size)),
        tokenizer_version=tokenizers.__version__,candidate_records=len(candidates),
        sampling_order_ids=[r['id'] for r in selected],selected_metadata=[{k:v for k,v in r.items() if k!='tokens'} for r in selected],
        selected_records_sha256=sha(destination/'records.json'),no_model_inference=True,
        exact_hash_overlap_checks_passed=True,semantic_near_duplicate_detection=False,
        source_text_redistributed=False,confirmation=False)
    new(destination/'selection.json',selection)
    require(inventory()==historical,'Historical metadata changed during data selection')
    return dict(status='complete',selected_records=13,tokens_per_record=128,
        records_sha256=sha(destination/'records.json'),selection_sha256=sha(destination/'selection.json'),
        no_model_inference=True,protected_counts=selection['protected_counts'])
