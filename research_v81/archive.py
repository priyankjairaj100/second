"""Prospective 24/48-stage, four-record modern archive. Not qualified.

Distinct framing and profile guards; unchanged canonical V63 factor codec and
V61 target/state contracts. Actual checkpoint trust belongs to registration and
fresh teacher reconstruction, not to metadata validation.
"""
from dataclasses import dataclass
import struct

from research_v61 import state as old
from research_v61.target import BoundTarget
from src.compact_state import StageCodes
from src.run_store import canonical_json
from research_v63 import codec
from research_v81.profile import validate_geometry, validate_records

MAGIC=b'V81ARC\x00\x00'
SCHEMA='matched-depth-modern-state-archive-v81'
MAX_BYTES=1024*2**20
MAX_HEADER=4*2**20


def require(v,m):
    if not v:raise ValueError(m)


@dataclass(frozen=True)
class View:
    target: BoundTarget
    records: tuple
    stage_codes: tuple
    source_payloads: tuple
    def source_map(self):return {(s,r):b for s,r,b in self.source_payloads}


def descriptor(blob,stage,record,target):
    d=codec.parse(blob,limits=codec.LoadLimits(max_bytes=8*2**20,max_values=393216,max_tokens=128,max_width=3072))
    require(d.target_sha256==old.sha(target.fixed_payload) and d.anchor_target_sha256==old.sha(target.anchor_payload)
        and d.stage_id==stage.stage_id and d.record_id==record.record_id
        and d.token_sha256==record.token_sha256 and d.shape==(len(record.tokens),stage.width),'Source identity/shape differs')
    return d


def pack(target,records,codes,payloads):
    require(type(target) is BoundTarget,'Exact V61 numerical reference required')
    profile=validate_geometry(old._object(target.anchor_payload))
    limits=old.StateLimits(max_bytes=MAX_BYTES,max_records=4,max_tokens=512,max_stages=48)
    records=old._records(records,target,limits);codes=tuple(codes);stages=target.stages
    validate_records(records)
    require(len(codes)==len(stages) in (24,48),'Complete registered stage codes required')
    require(set(payloads)=={(s.stage_id,r.record_id) for s in stages for r in records},'Complete source census required')
    anchor=old._object(target.anchor_payload);parts=[target.anchor_payload,target.fixed_payload];rows=[]
    for stage,code,grid in zip(stages,codes,anchor['stages']):
        require(type(code) is StageCodes and code.stage_id==stage.stage_id and code.shape==(stage.rows,stage.width)
            and code.bits==stage.bits and code.grid_axis=='dyadic_row' and not code.scale_exponents
            and [x.hex() for x in code.scale_values]==grid['row_scale_hex'],'Stage codes or grids differ')
        StageCodes(code.stage_id,code.rows,code.columns,code.grid_axis,code.bits,code.scale_exponents,code.packed_indices,code.scale_values)
        parts.append(code.packed_indices);sources=[]
        for record in records:
            blob=payloads[stage.stage_id,record.record_id];descriptor(blob,stage,record,target)
            sources.append(dict(record_id=record.record_id,**old._blob(blob)));parts.append(blob)
        rows.append(dict(code=code.metadata(),sources=sources))
    header=canonical_json(dict(schema=SCHEMA,profile=profile,codec_sha256=codec.codec_binding(),anchor_target=old._blob(target.anchor_payload),
        reference_target=old._blob(target.fixed_payload),records=[r.metadata() for r in records],stages=rows))
    require(len(header)<=MAX_HEADER and 16+len(header)+sum(map(len,parts))<=MAX_BYTES,'Archive exceeds bound')
    return b''.join((MAGIC,struct.pack('<Q',len(header)),header,*parts))


def unpack(data):
    require(type(data) is bytes and 16<=len(data)<=MAX_BYTES and data[:8]==MAGIC,'Invalid archive extent/magic')
    n=struct.unpack_from('<Q',data,8)[0];require(n<=MAX_HEADER and n<=len(data)-16,'Header bound')
    h=old._object(data[16:16+n]);offset=16+n
    require(set(h)=={'schema','profile','codec_sha256','anchor_target','reference_target','records','stages'}
        and h['schema']==SCHEMA and h['codec_sha256']==codec.codec_binding(),'Archive format/runtime differs')
    def chunk(entry):
        nonlocal offset
        require(type(entry) is dict and set(entry)=={'nbytes','sha256'},'Invalid chunk fields')
        size=entry['nbytes'];require(type(size) is int and 0<=size<=len(data)-offset,'Chunk exceeds file')
        raw=data[offset:offset+size];offset+=size
        require(old.sha(raw)==old._digest(entry['sha256']),'Chunk hash differs');return raw
    target=BoundTarget(chunk(h['anchor_target']),chunk(h['reference_target']))
    require(h['profile']==validate_geometry(old._object(target.anchor_payload)),'Archive profile/geometry differs')
    require(type(h['records']) is list and len(h['records'])<=4,'Record bound')
    records=[]
    for r in h['records']:
        require(type(r) is dict and set(r)=={'record_id','tokens','token_sha256','provenance'} and type(r['tokens']) is list,'Invalid record')
        record=old.Record(r['record_id'],tuple(r['tokens']),canonical_json(r['provenance']))
        require(record.metadata()==r,'Record binding differs');records.append(record)
    records=tuple(records)
    require(type(h['stages']) is list and len(h['stages'])==len(target.stages),'Stage census differs')
    codes=[];payloads={}
    for stage,row in zip(target.stages,h['stages']):
        require(type(row) is dict and set(row)=={'code','sources'},'Stage fields differ')
        c=row['code'];require(type(c) is dict and set(c)=={'stage_id','rows','columns','grid_axis','bits','nbytes','sha256','scale_values_hex'} and type(c['scale_values_hex']) is list,'Code fields differ')
        code=StageCodes(c['stage_id'],c['rows'],c['columns'],c['grid_axis'],c['bits'],(),chunk({k:c[k] for k in ('nbytes','sha256')}),tuple(float.fromhex(x) for x in c['scale_values_hex']))
        require(code.metadata()==c,'Code encoding differs');codes.append(code)
        require(type(row['sources']) is list and len(row['sources'])==len(records),'Source census differs')
        for record,entry in zip(records,row['sources']):
            require(type(entry) is dict and set(entry)=={'record_id','nbytes','sha256'} and entry['record_id']==record.record_id,'Source order differs')
            payloads[stage.stage_id,record.record_id]=chunk({k:entry[k] for k in ('nbytes','sha256')})
    require(offset==len(data),'Trailing bytes')
    require(pack(target,records,codes,payloads)==data,'Noncanonical archive')
    return View(target,records,tuple(codes),tuple((s,r,b) for (s,r),b in payloads.items()))


def restore(view):
    """Canonical V29 re-encoding is migration/validation cost, not codec decoding."""
    from src import fixed_lossless_codec_v29 as prior
    sources={}
    for sid,rid,blob in view.source_payloads:
        d=codec.parse(blob)
        sources[sid,rid]=prior.serialize(prior.encode_factor(d.array(),target_sha256=d.target_sha256,
            anchor_target_sha256=d.anchor_target_sha256,record_id=rid,token_sha256=d.token_sha256,stage_id=sid))
    return old.build_state(view.target,view.records,view.stage_codes,'lossless',source_payloads=sources)


def transition(previous,records,codes):
    records=tuple(records);before={r.record_id:r for r in previous.records}
    require(all(before.get(r.record_id)==r for r in records),'Successor is not a retained subset')
    keep={r.record_id for r in records}
    return pack(previous.target,records,codes,{(s,r):b for s,r,b in previous.source_payloads if r in keep})
