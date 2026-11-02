"""Prospective bounded untouched-quality selection. Unregistered preparation.

No network or corpus access occurs on import. Selection and saved-byte audit use
one implementation; they are not independent implementation replication.
"""
from pathlib import Path
import json,re,zlib
from urllib.request import Request,urlopen
from research_v45.data import Exclusions,c4_row,TOKENIZER_SHA
from research_v65.data import exclusions_from,decode_prefix as old_decode_prefix
from src.run_store import canonical_json,digest,strict_json
from research_v67.io import read,write,require,info

POLICY=dict(schema='untouched-c4-validation-frame-v68',dataset='allenai/c4',
 revision='1588ec454efa1a09f29cd18ddd04fe05fc8653a2',split='validation',shard=1,
 filename='en/c4-validation.00001-of-00008.json.gz',source_total_bytes=40675053,
 whole_source_sha256_metadata='db4c23d7a336032de37dfe2f3ed39653c8afd94004d4e8d9c73c03222299292c',
 transfer_bytes=8*2**20,decompressed_prefix_bytes=8*2**20,max_records=20000,
 max_text_characters=4*2**20,max_url_characters=65536,articles=320,tokens=128,predictions=127,
 token_offset=0,bos_eos=False,order_seed='second-v68-untouched-quality-frame-before-loss:',
 order_rule='SHA256(UTF8(order_seed+record_id)), tie by record_id',
 frame_deduplication_order='original complete-record line order, before sample ranking',
 model_inference=False,quality_evaluation=False,
 sample_scope='pseudorandom ordering within one bounded validation frame; not corpus-uniform',
 overlap_scope='exact ID/body/normalized-text/URL and16/32/64/128token prefixes; not semantic or arbitrary substring overlap')
V65_REG='13d9ecb7ddb9ee37ba05498387af490a5e6f16879340c4ec301bbe2aaf5f08d2'
AFTER_SHA='3df013adfa9647b0fb5e61feb86b013fdc396689d8460082d5f78f7663de9fa2'
PREFIX_SHA='2dd5205d5d2819eedbcedab9beddcefdd3be6735c0bf5c7c63b4a56b07986bfa'


def url(policy=POLICY):
    return f"https://huggingface.co/datasets/allenai/c4/resolve/{policy['revision']}/{policy['filename']}"


def acquire(directory,policy=POLICY):
    """One bounded transfer. Preserve partial bytes and a receipt on any failure."""
    directory=Path(directory).absolute();path=directory/'validation-prefix.gz.part'
    require(directory.is_dir() and not any(p.is_symlink() for p in (directory,*directory.parents)),'Unsafe acquisition directory')
    if path.exists() or (directory/'acquisition.json').exists():raise FileExistsError('One-use acquisition already exists')
    status='failed';error=None;response_headers={};count=0
    try:
        with path.open('xb') as out:
            req=Request(url(policy),headers={'Range':f"bytes=0-{policy['transfer_bytes']-1}",'User-Agent':'second-v68-bounded-quality-frame'})
            with urlopen(req,timeout=60) as response:
                response_headers={k:response.headers.get(k) for k in ['Content-Range','Content-Length']}
                require(response.status==206,'Exact bounded range response required')
                expected=f"bytes 0-{policy['transfer_bytes']-1}/{policy['source_total_bytes']}"
                require(response_headers['Content-Range']==expected,'Pinned source range/total extent differs')
                if response_headers['Content-Length'] is not None:
                    require(response_headers['Content-Length']==str(policy['transfer_bytes']),'Content length differs')
                while count<=policy['transfer_bytes']:
                    b=response.read(min(65536,policy['transfer_bytes']+1-count))
                    if not b:break
                    out.write(b);out.flush();count+=len(b)
                import os
                os.fsync(out.fileno())
                require(count==policy['transfer_bytes'],'Wrong transferred prefix extent')
        status='complete'
    except BaseException as exc:
        error=dict(type=type(exc).__name__,http_code=getattr(exc,'code',None))
        raise
    finally:
        # Never record redirected signed URLs or response cookies. No retry.
        if path.exists():
            write(directory/'acquisition.json',dict(status=status,error=error,url=url(policy),
                method='GET',automatic_retry=False,headers=response_headers,
                received=read(path,retain=False,maximum=policy['transfer_bytes']+1),
                whole_source_sha256_is_metadata_only=True,
                whole_source_sha256_metadata=policy['whole_source_sha256_metadata']))
    return read(path,maximum=policy['transfer_bytes'])


def decode_frame(raw,policy=POLICY):
    require(type(raw) is bytes and len(raw)==policy['transfer_bytes'],'Exact acquired prefix extent required')
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
    prefix=decoder.decompress(raw,policy['decompressed_prefix_bytes'])
    require(len(prefix)==policy['decompressed_prefix_bytes'],'Compressed range did not supply fixed decompressed frame; no expansion')
    lines=prefix.split(b'\n')[:-1]
    require(0<len(lines)<=policy['max_records'],'Bounded complete-record census required')
    records=[]
    for line in lines:
        require(bool(line),'Empty complete record refused')
        value=strict_json(line)
        require(type(value) is dict and type(value.get('text')) is str and type(value.get('url')) is str
            and len(value['text'])<=policy['max_text_characters'] and len(value['url'])<=policy['max_url_characters'],'Invalid or oversized complete record')
        records.append(value)
    return records,dict(decompressed_prefix=info(prefix),complete_records=len(records),
        incomplete_trailing_bytes=len(prefix)-sum(len(line)+1 for line in lines),
        compressed_bytes_consumed_at_most=len(raw),whole_gzip_trailer_verified=False)


def row(index,item,tokenizer,policy=POLICY):
    r=c4_row(index,item,policy['shard'],tokenizer)
    r['id']=f"c4:en:validation:shard{policy['shard']}:line{index}"
    r['line_index']=index;r['split']='validation'
    return r


def serialized_exclusions(excluded):
    return {k:sorted(getattr(excluded,k)) for k in ['ids','content','chunks']}


def protected_from_v65(after,prior_prefix,history,tokenizer):
    """Add EVERY old shard-two candidate, not only V65's thirteen selections."""
    require(info(after)['sha256']==AFTER_SHA and info(prior_prefix)['sha256']==PREFIX_SHA,'Audited V65 exclusion/frame identities differ')
    protected=strict_json(after);require(canonical_json(protected)==after,'Canonical protected exclusions required')
    excluded=exclusions_from(protected,history)
    old=old_decode_prefix(prior_prefix)
    for i,item in enumerate(old):excluded.add(c4_row(i,item,2,tokenizer))
    require(len(old)==2349,'Audited full prior candidate-frame census differs')
    return excluded


def reasons(r,excluded,policy=POLICY):
    result=[]
    if len(r['tokens'])!=policy['tokens']:result.append('short_record')
    if r['id'] in excluded.ids:result.append('id_overlap')
    if any(r[k] in excluded.content for k in ['normalized_text_sha256','body_sha256','url_sha256']):result.append('content_or_url_overlap')
    if any(digest(canonical_json(r['tokens'][:n])) in excluded.chunks for n in [16,32,64,128] if len(r['tokens'])>=n):result.append('token_prefix_overlap')
    return result


def select(candidates,protected,policy=POLICY):
    """Complete deterministic deduplicated frame, then outcome-blind sampling."""
    require(type(candidates) is list and 0<len(candidates)<=policy['max_records'],'Candidate census')
    require([r['line_index'] for r in candidates]==list(range(len(candidates)))
        and len({r['id'] for r in candidates})==len(candidates),'Complete source line order and distinct IDs required')
    frame_seen=Exclusions();eligible=[];inventory=[]
    for r in candidates:
        require(set(r)=={'id','tokens','available_tokens','body_sha256','normalized_text_sha256','url_sha256','token_offset','line_index','split'}
            and r['id']==f"c4:en:validation:shard{policy['shard']}:line{r['line_index']}"
            and r['split']=='validation' and r['token_offset']==0 and type(r['available_tokens']) is int
            and r['available_tokens']>=len(r['tokens']) and len(r['tokens'])==min(policy['tokens'],r['available_tokens'])
            and all(type(t) is int and 0<=t<50257 for t in r['tokens'])
            and all(re.fullmatch('[0-9a-f]{64}',r[k]) for k in ['body_sha256','normalized_text_sha256','url_sha256']), 'Candidate structure or vocabulary differs')
        prior=reasons(r,protected,policy);within=reasons(r,frame_seen,policy) if not prior else []
        why=prior or (['within_frame_'+x for x in within] if within else [])
        if not why:eligible.append(r)
        frame_seen.add(r)
        inventory.append(dict(id=r['id'],line_index=r['line_index'],available_tokens=r['available_tokens'],
            body_sha256=r['body_sha256'],normalized_text_sha256=r['normalized_text_sha256'],url_sha256=r['url_sha256'],
            token_prefixes={str(n):digest(canonical_json(r['tokens'][:n])) for n in [16,32,64,128] if len(r['tokens'])>=n},
            eligible=not bool(why),exclusion_reasons=why))
    eligible.sort(key=lambda r:(digest((policy['order_seed']+r['id']).encode('utf-8')),r['id']))
    chosen=eligible[:policy['articles']]
    # Permanently reserve the entire inspected frame, not only selected articles.
    successor=exclusions_from(serialized_exclusions(protected),[])
    for r in candidates:successor.add(r)
    return dict(status='complete' if len(chosen)==policy['articles'] else 'underfilled',
        chosen=chosen,candidates=inventory,eligible_ids_in_sampling_order=[r['id'] for r in eligible],
        exclusions_after=serialized_exclusions(successor),requested_articles=policy['articles'])


def materialize(directory,raw,tokenizer,protected,policy=POLICY):
    """Persist full selection evidence before refusing an underfilled frame."""
    directory=Path(directory);items,frame=decode_frame(raw,policy)
    candidates=[row(i,item,tokenizer,policy) for i,item in enumerate(items)]
    decision=select(candidates,protected,policy)
    before=canonical_json(serialized_exclusions(protected))
    write(directory/'exclusions-before.json',before,raw=True)
    write(directory/'exclusions-after.json',decision['exclusions_after'])
    write(directory/'candidate-inventory.json',dict(candidates=decision['candidates'],frame=frame,
        eligible_ids_in_sampling_order=decision['eligible_ids_in_sampling_order']))
    records=sorted([dict(id=r['id'],tokens=r['tokens']) for r in decision['chosen']],key=lambda r:r['id'])
    committed=write(directory/'records.json',dict(records=records))
    selection=dict(schema='untouched-c4-selection-v68',status=decision['status'],policy=policy,source_prefix=info(raw),frame=frame,
        records={k:committed[k] for k in ['bytes','sha256']},requested_articles=policy['articles'],selected_articles=len(records),
        selected_metadata=[{k:v for k,v in r.items() if k!='tokens'} for r in decision['chosen']],
        sampling_order_ids=[r['id'] for r in decision['chosen']],eligible_articles=len(decision['eligible_ids_in_sampling_order']),
        candidate_articles=len(candidates),exclusions_before=info(before),
        inspected_frame_permanently_reserved=True,model_inference=False,quality_evaluation=False,semantic_deduplication=False)
    write(directory/'selection.json',selection)
    require(selection['status']=='complete','Insufficient disjoint articles; preserved underfilled frame; no retry/expansion')
    return selection


def audit_saved(directory,tokenizer,protected,policy=POLICY):
    """Read saved bytes; do not download, choose another seed or evaluate a model."""
    directory=Path(directory);raw=read(directory/'validation-prefix.gz.part',maximum=policy['transfer_bytes'])
    source_raw=read(directory/'acquisition.json');source=strict_json(source_raw)
    require(canonical_json(source)==source_raw,'Canonical acquisition receipt required')
    require(source['status']=='complete' and source['received']==info(raw) and source['url']==url(policy)
        and source['method']=='GET' and source['automatic_retry'] is False
        and source['whole_source_sha256_is_metadata_only'] is True
        and source['whole_source_sha256_metadata']==policy['whole_source_sha256_metadata']
        and source['headers']['Content-Range']==f"bytes 0-{policy['transfer_bytes']-1}/{policy['source_total_bytes']}", 'Complete actual source acquisition binding required')
    items,frame=decode_frame(raw,policy);decision=select([row(i,x,tokenizer,policy) for i,x in enumerate(items)],protected,policy)
    require(decision['status']=='complete','Underfilled frame cannot pass audit')
    records=sorted([dict(id=r['id'],tokens=r['tokens']) for r in decision['chosen']],key=lambda r:r['id'])
    actual_records=read(directory/'records.json');require(actual_records==canonical_json(dict(records=records)),'Actual selected token words/order differ')
    require(read(directory/'exclusions-before.json')==canonical_json(serialized_exclusions(protected))
        and read(directory/'exclusions-after.json')==canonical_json(decision['exclusions_after']), 'Actual exclusion union differs')
    expected_inventory=dict(candidates=decision['candidates'],frame=frame,eligible_ids_in_sampling_order=decision['eligible_ids_in_sampling_order'])
    require(read(directory/'candidate-inventory.json')==canonical_json(expected_inventory),'Actual full candidate inventory differs')
    selection=strict_json(read(directory/'selection.json'))
    expected=dict(schema='untouched-c4-selection-v68',status='complete',policy=policy,source_prefix=info(raw),frame=frame,
        records=info(actual_records),requested_articles=policy['articles'],selected_articles=len(records),
        selected_metadata=[{k:v for k,v in r.items() if k!='tokens'} for r in decision['chosen']],
        sampling_order_ids=[r['id'] for r in decision['chosen']],eligible_articles=len(decision['eligible_ids_in_sampling_order']),
        candidate_articles=len(items),exclusions_before=info(canonical_json(serialized_exclusions(protected))),
        inspected_frame_permanently_reserved=True,model_inference=False,quality_evaluation=False,semantic_deduplication=False)
    require(selection==expected and read(directory/'selection.json')==canonical_json(expected),'Selection metadata or scope differs')
    return dict(status='verified',actual_saved_prefix_retokenized=True,actual_records_equal=True,
        actual_full_candidate_inventory_equal=True,actual_exclusion_union_equal=True,selected_articles=len(records),
        implementation_shared_with_preparation=True,model_inference=False,quality_evaluation=False)
