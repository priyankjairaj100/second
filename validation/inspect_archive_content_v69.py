"""Bounded, non-executing content review of already-preserved metadata archives.

Never extracts payloads or copies article/token/array values into the report.
Content flags are review candidates, not blanket anonymity or safety clearance.
"""
from pathlib import Path
from collections import Counter
import argparse,datetime,hashlib,json,re,tarfile
ROOT=Path(__file__).resolve().parents[1]
PATTERNS={
 'author_or_account':r'priyankjairaj|poonam',
 'host_or_address':r'172\.24\.16\.132|csis\.(?:mn|cn)\d+',
 'local_absolute_root':r'/Users/|/nfs_home/',
 'identifying_repository':r'github\.com/priyankjairaj100/second',
 'article_identifier':r'wikitext2:(?:validation|train|test):article-row-\d+|c4:[^\s"\\]{1,120}',
}
RX={k:re.compile(v,re.I) for k,v in PATTERNS.items()}
TEXT_KEYS={'text','content','article_text','document_text','body'}
ENCODED_KEYS={'base64','b64','payload_base64','tensor_bytes'}


def payload_flags(value):
 flags=[];stack=[([],value)];nodes=0
 while stack:
  path,v=stack.pop();nodes+=1
  if nodes>1000000:raise ValueError('JSON node bound exceeded')
  if isinstance(v,dict):
   for key,child in v.items():
    # Record structural key paths, not keys that may themselves be article IDs.
    public_key='<article-id>' if RX['article_identifier'].search(key) else key
    q=path+[public_key]
    if key.lower() in TEXT_KEYS and isinstance(child,str) and len(child)>60:
     flags.append(dict(kind='long_text_field',path=q,characters=len(child)))
    if key.lower() in ENCODED_KEYS and isinstance(child,str) and len(child)>128:
     flags.append(dict(kind='encoded_payload_field',path=q,characters=len(child)))
    if key.lower() in {'tokens','input_ids','token_ids'} and isinstance(child,list) and child and all(type(n)is int for n in child):
     flags.append(dict(kind='token_array',path=q,values=len(child)))
    stack.append((q,child))
  elif isinstance(v,list):
   if len(v)>16 and all(type(n) in (int,float) for n in v):flags.append(dict(kind='numeric_array_candidate',path=path,values=len(v)))
   else:
    for i,child in enumerate(v):stack.append((path+[i],child))
 return flags,nodes


def inspect():
 inventory=json.loads((ROOT/'validation/v69_archive_member_inventory.json').read_text());out={};totals=Counter();flag_files=[]
 for name,old in inventory['archives'].items():
  p=ROOT/name;raw=p.read_bytes();assert len(raw)==old['commitment']['bytes'] and hashlib.sha256(raw).hexdigest()==old['commitment']['sha256']
  rows={};total=0
  with tarfile.open(p,'r:gz') as archive:
   for m in archive:
    q=Path(m.name);assert m.isfile() and not q.is_absolute() and '..' not in q.parts and str(q)==m.name and m.name not in rows
    assert m.size==old['member_bytes'][m.name] and m.size<=16*2**20 and total+m.size<=128*2**20 and len(rows)<2000
    total+=m.size;payload=archive.extractfile(m).read(m.size+1);assert len(payload)==m.size
    text=payload.decode('utf8');identities={k:len(rx.findall(text)) for k,rx in RX.items() if rx.search(text)}
    flags=[];nodes=None;schema=None
    if q.suffix=='.json':
     data=json.loads(text);flags,nodes=payload_flags(data)
     schema=data.get('schema') if isinstance(data,dict) else None
     if not isinstance(schema,(str,type(None))):schema='<nonstring-schema>'
    suffix=q.suffix;totals['files']+=1;totals['bytes']+=len(payload);totals['known_identity_files']+=bool(identities);totals['payload_candidate_files']+=bool(flags)
    if suffix=='.json':totals['json_files']+=1
    totals['token_array_files']+=any(f['kind']=='token_array' for f in flags)
    totals['long_text_files']+=any(f['kind']=='long_text_field' for f in flags)
    totals['encoded_payload_files']+=any(f['kind']=='encoded_payload_field' for f in flags)
    # Values are deliberately not emitted. Manual review must choose any derivative.
    row=dict(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),suffix=suffix,known_identity_match_counts=identities,json_schema=schema,json_nodes_inspected=nodes,payload_candidates=flags)
    rows[m.name]=row
    if flags:flag_files.append(dict(archive=name,member=m.name,kinds=sorted({f['kind'] for f in flags})))
   assert set(rows)==set(old['member_bytes']) and len(rows)==old['member_count'] and total==old['uncompressed_member_bytes']
  out[name]=dict(commitment=old['commitment'],member_count=len(rows),uncompressed_bytes=total,members=rows)
 assert totals['files']==2269 and totals['bytes']==33307525
 return dict(schema='historical-archive-content-review-v69',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='bounded_content_scan_complete_manual_allowlist_required',archives=out,totals=dict(totals),payload_candidate_files=flag_files,original_archives_unchanged=True,files_extracted=False,article_token_or_array_values_copied_to_report=False,content_read_only=True,code_executed=False,numerical_audits_repeated=False,full_anonymity_verified=False,scope='Strict UTF-8 and JSON traversal, known identity strings and selected raw-payload field heuristics. Flags require review; absence does not certify safety/anonymity. No final package inclusion is authorized by this report.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=inspect()
 with a.output.open('x') as f:json.dump(r,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'totals':r['totals'],'payload_candidates':r['payload_candidate_files'][:15]}))
