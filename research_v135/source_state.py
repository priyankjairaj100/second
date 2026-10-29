"""Canonical packed models plus retained tokens/references, without feature caches.

This is a storage format, not a fresh model oracle. Equality of numerical codes
must be established by a separately registered constructor. Token-carrying states
do not require the external corpus to replay; reference-only states do.
"""
from dataclasses import dataclass
import struct
from research_v61.target import BoundTarget
from research_v61.state import Record
from src.compact_state import StageCodes
from src.run_store import canonical_json,digest,strict_json
MAGIC=b'SRCONLY1'
MAX_BYTES=128*2**20
MAX_HEADER=16*2**20

def require(ok,message):
    if not ok:raise ValueError(message)

@dataclass(frozen=True)
class View:
    target: BoundTarget
    records: tuple
    codes: tuple
    mode: str
    sources: tuple

def pack(target,records,codes,mode='tokens'):
    require(type(target)is BoundTarget and mode in ('tokens','references'),'Bound target and explicit source mode required')
    require(type(records)is tuple and records and all(type(r)is Record for r in records),'Nonempty immutable records required')
    require([r.record_id for r in records]==sorted({r.record_id for r in records}),'Distinct canonical membership required')
    require(type(codes)is tuple and len(codes)==len(target.stages),'Complete code tuple required')
    chunks=[];metadata=[]
    for c,s,grid in zip(codes,target.stages,strict_json(target.anchor_payload)['stages']):
        require(type(c)is StageCodes and c.stage_id==s.stage_id and c.shape==(s.rows,s.width) and c.bits==4 and c.grid_axis=='dyadic_row' and [v.hex() for v in c.scale_values]==grid['row_scale_hex'],'Code target/grid/order mismatch')
        chunks.append(c.packed_indices);metadata.append(c.metadata())
    sources=[]
    for r in records:
        d=r.metadata();d['token_count']=len(r.tokens)
        if mode=='references':del d['tokens']
        sources.append(d)
    h=canonical_json(dict(schema='source-only-state-v135',mode=mode,anchor=strict_json(target.anchor_payload),fixed=strict_json(target.fixed_payload),records=sources,stages=metadata))
    require(len(h)<=MAX_HEADER,'Header cap exceeded');out=MAGIC+struct.pack('<Q',len(h))+h+b''.join(chunks)
    require(len(out)<=MAX_BYTES,'Archive cap exceeded');return out

def unpack(blob,provider=None):
    require(type(blob)is bytes and 16<=len(blob)<=MAX_BYTES and blob[:8]==MAGIC,'Bound source-only frame required')
    n=struct.unpack_from('<Q',blob,8)[0];require(0<n<=MAX_HEADER and 16+n<=len(blob),'Header extent invalid')
    raw=blob[16:16+n];h=strict_json(raw)
    require(canonical_json(h)==raw and set(h)=={'schema','mode','anchor','fixed','records','stages'} and h['schema']=='source-only-state-v135','Canonical exact header schema required')
    require(h['mode'] in ('tokens','references'),'Unknown source mode')
    target=BoundTarget(canonical_json(h['anchor']),canonical_json(h['fixed']));records=[]
    require(h['records'] and [r['record_id'] for r in h['records']]==sorted({r['record_id'] for r in h['records']}),'Canonical nonempty records required')
    for r in h['records']:
        keys={'record_id','token_sha256','token_count','provenance'}|({'tokens'} if h['mode']=='tokens' else set())
        require(set(r)==keys,'Unexpected retained source fields')
        if h['mode']=='tokens':tokens=tuple(r['tokens'])
        else:
            if provider is None:raise PermissionError('Retained reference unavailable')
            tokens=tuple(provider(r['record_id'],r['provenance']))
        item=Record(r['record_id'],tokens,canonical_json(r['provenance']))
        require(len(tokens)==r['token_count'] and item.token_sha256==r['token_sha256'],'Retained source words changed');records.append(item)
    require(len(h['stages'])==len(target.stages),'Incomplete stage extent');codes=[];offset=16+n
    for s,m,grid in zip(target.stages,h['stages'],h['anchor']['stages']):
        count=(s.rows*s.width*4+7)//8;payload=blob[offset:offset+count]
        c=StageCodes(s.stage_id,s.rows,s.width,'dyadic_row',4,(),payload,tuple(float.fromhex(v) for v in grid['row_scale_hex']))
        require(c.metadata()==m,'Stage payload/grid mismatch');codes.append(c);offset+=count
    require(offset==len(blob),'Trailing model bytes')
    v=View(target,tuple(records),tuple(codes),h['mode'],tuple(h['records']))
    require(pack(v.target,v.records,v.codes,v.mode)==blob,'Noncanonical source-only state')
    return v

def successor(view,retained_ids,codes):
    require(type(view)is View and type(retained_ids)is tuple and retained_ids==tuple(sorted(set(retained_ids))),'Canonical retained ID tuple required')
    by={r.record_id:r for r in view.records};require(retained_ids and set(retained_ids)<=set(by),'Missing or empty retained membership')
    return pack(view.target,tuple(by[i] for i in retained_ids),codes,view.mode)
