"""Portable full first-stage archive, with bounded UTF-8 payload shards.

All data are extracted from previously evaluated real archives. Export does
not compute a Gram or new quantization. The manifest authenticates exact
archived features, complete FP32 base weights, and retained reference codes.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.run_store import canonical_json,strict_json
from src.compact_state import StageCodes
from src.dyadic_row_quantizer import dyadic_row_scales
from research_v35.archive_capsule import load_capsule as load_feature_capsule
from scripts.execute_gram_pilot_v35 import bind_inputs,read_archives,new_file,hashed,require

FEATURE_FILE='data/gram_v35/wikitext-firststage.json'
FEATURE_SHA='59bf847f2765fc788a93fe53374aa91e7853d2981a18d46b1084d0807cf6c775'
STAGE='block.0000.qkv'
ROWS,WIDTH=2304,768
MAX_SHARD=512*1024
MAX_MANIFEST=256*1024
MAX_RAW={'weights':ROWS*WIDTH*4,'reference_indices':ROWS*WIDTH//2,'scales':ROWS*8}

def sha(raw):return hashlib.sha256(raw).hexdigest()

def _safe_file(path,maximum):
    p=Path(path)
    require(p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents),'unsafe artifact file')
    require(0<p.stat().st_size<=maximum,'artifact exceeds bound')
    return p.read_bytes()

def checkpoint_stage(path):
    """Read one FP32 Conv1D tensor, transposed into full output rows."""
    with Path(path).open('rb') as f:
        raw=f.read(8);require(len(raw)==8,'truncated safetensors header')
        size=struct.unpack('<Q',raw)[0];require(0<size<=16*2**20,'header exceeds bound')
        header=json.loads(f.read(size));entry=header['transformer.h.0.attn.c_attn.weight']
        require(entry['dtype']=='F32' and entry['shape']==[WIDTH,ROWS],'first QKV dimensions differ')
        lo,hi=entry['data_offsets'];require(type(lo)is int and type(hi)is int and 0<=lo<hi and hi-lo==MAX_RAW['weights'],'invalid tensor offsets')
        f.seek(8+size+lo);raw=f.read(hi-lo);require(len(raw)==hi-lo,'truncated QKV tensor')
    array=np.frombuffer(raw,dtype='<f4').reshape(WIDTH,ROWS).T.copy()
    require(np.isfinite(array).all(),'nonfinite stage weights')
    return array

def _write_payload(directory,name,raw):
    require(name in MAX_RAW and len(raw)==MAX_RAW[name],'payload shape differs')
    compressed=zlib.compress(raw,9);shards=[]
    step=MAX_SHARD//4*3
    for i,start in enumerate(range(0,len(compressed),step)):
        encoded=base64.b64encode(compressed[start:start+step]);filename=f'{name}-{i:03d}.b64'
        require(len(encoded)<=MAX_SHARD,'encoded shard exceeds bound')
        new_file(directory/filename,encoded)
        shards.append(dict(file=filename,bytes=len(encoded),sha256=sha(encoded)))
    return dict(encoding='zlib-base64-shards-v1',raw_bytes=len(raw),raw_sha256=sha(raw),
        compressed_bytes=len(compressed),compressed_sha256=sha(compressed),shards=shards)

def _read_payload(directory,name,entry):
    require(type(entry)is dict and set(entry)=={'encoding','raw_bytes','raw_sha256','compressed_bytes','compressed_sha256','shards'},'payload entry differs')
    require(entry['encoding']=='zlib-base64-shards-v1' and entry['raw_bytes']==MAX_RAW[name],'payload schema or extent differs')
    require(type(entry['compressed_bytes'])is int and 0<entry['compressed_bytes']<=MAX_RAW[name]+65536,'compressed bound exceeded')
    require(type(entry['shards'])is list and 1<=len(entry['shards'])<=32,'shard count exceeds bound')
    parts=[]
    for i,chunk in enumerate(entry['shards']):
        require(type(chunk)is dict and set(chunk)=={'file','bytes','sha256'} and chunk['file']==f'{name}-{i:03d}.b64','shard name/order differs')
        encoded=_safe_file(directory/chunk['file'],MAX_SHARD)
        require(len(encoded)==chunk['bytes'] and sha(encoded)==chunk['sha256'],'shard binding differs')
        raw=base64.b64decode(encoded,validate=True)
        require(base64.b64encode(raw)==encoded,'noncanonical base64 shard')
        parts.append(raw)
    compressed=b''.join(parts)
    require(len(compressed)==entry['compressed_bytes'] and sha(compressed)==entry['compressed_sha256'],'compressed payload differs')
    decoder=zlib.decompressobj();raw=decoder.decompress(compressed,MAX_RAW[name]+1)
    require(len(raw)==MAX_RAW[name] and decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data,'compressed payload truncated, oversized, or trailing')
    require(sha(raw)==entry['raw_sha256'],'decoded payload digest differs')
    return raw

def capsule_files(path,expected_sha256):
    """Return every authenticated file for complete registration closure."""
    p=Path(path);raw=_safe_file(p,MAX_MANIFEST)
    require(sha(raw)==expected_sha256,'stage capsule manifest differs')
    j=strict_json(raw);require(canonical_json(j)==raw,'noncanonical stage capsule')
    require(type(j)is dict and set(j)=={'schema','stage','rows','width','normalization','ridge','bits','target','feature_capsule','payloads','reference_values_sha256','provenance'},'capsule fields differ')
    require(j['schema']=='full-stage-real-archive-capsule-v36' and j['stage']==STAGE and j['rows']==ROWS and j['width']==WIDTH and j['normalization']==256 and j['ridge']==[1,100] and j['bits']==4,'stage target differs')
    require(j['feature_capsule']=={'file':FEATURE_FILE,'sha256':FEATURE_SHA},'shared feature capsule differs')
    require(set(j['payloads'])==set(MAX_RAW),'payload membership differs')
    files={str(p.resolve()):dict(sha256=expected_sha256,bytes=len(raw))}
    f=ROOT/FEATURE_FILE;require(hashed(f)==FEATURE_SHA,'shared feature capsule changed')
    files[str(f.resolve())]=dict(sha256=FEATURE_SHA,bytes=f.stat().st_size)
    for name,entry in j['payloads'].items():
        _read_payload(p.parent,name,entry)
        for item in entry['shards']:
            files[str((p.parent/item['file']).resolve())]=dict(sha256=item['sha256'],bytes=item['bytes'])
    return j,files

def load_capsule(path,expected_sha256):
    p=Path(path);j,files=capsule_files(p,expected_sha256)
    feature=load_feature_capsule(ROOT/FEATURE_FILE,FEATURE_SHA)
    require(j['target']==feature['target'],'feature and complete stage targets differ')
    weights32=np.frombuffer(_read_payload(p.parent,'weights',j['payloads']['weights']),dtype='<f4').reshape(ROWS,WIDTH)
    weights=weights32.astype(np.float64)
    require(np.isfinite(weights).all(),'nonfinite full-stage weights')
    scales=tuple(float(x) for x in np.frombuffer(_read_payload(p.parent,'scales',j['payloads']['scales']),dtype='<f8'))
    require(scales==dyadic_row_scales(weights),'full-stage canonical scales differ')
    packed=_read_payload(p.parent,'reference_indices',j['payloads']['reference_indices'])
    stage=StageCodes(STAGE,ROWS,WIDTH,'dyadic_row',4,(),packed,scales)
    reference=stage.array()
    require(sha(reference.astype('<f8').tobytes())==j['reference_values_sha256'],'full-stage reference values differ')
    require(np.array_equal(weights[:4],feature['weights']) and np.array_equal(reference[:4],feature['reference']),'first four rows differ from existing capsule')
    return dict(descriptors=feature['descriptors'],retained_descriptor=feature['retained_descriptor'],weights=weights,
        reference=reference,scales=scales,target=j['target'],metadata=j,files=files)

def create_capsule(directory):
    directory=Path(directory);require(not directory.exists(),'capsule directory already exists; no overwrite')
    inputs=bind_inputs();original,retained,descriptors,retained_descriptor=read_archives(inputs)
    feature=load_feature_capsule(ROOT/FEATURE_FILE,FEATURE_SHA)
    weights32=checkpoint_stage(inputs['weights']['path']);weights=weights32.astype(np.float64)
    stage=retained.stages[0];require(stage.shape==(ROWS,WIDTH) and stage.stage_id==STAGE,'retained stage differs')
    scales=tuple(stage.scale_values);require(scales==dyadic_row_scales(weights),'retained grid differs from base weights')
    reference=stage.array()
    require(np.array_equal(feature['weights'],weights[:4]) and np.array_equal(feature['reference'],reference[:4]),'shared capsule row prefix differs')
    for rid,d in descriptors.items():require(feature['descriptors'][rid].binary64()==d.binary64(),'shared exact feature words differ')
    directory.mkdir(parents=True)
    payloads={'weights':_write_payload(directory,'weights',weights32.astype('<f4').tobytes()),
        'reference_indices':_write_payload(directory,'reference_indices',stage.packed_indices),
        'scales':_write_payload(directory,'scales',np.asarray(scales,dtype='<f8').tobytes())}
    manifest=dict(schema='full-stage-real-archive-capsule-v36',stage=STAGE,rows=ROWS,width=WIDTH,normalization=256,ridge=[1,100],bits=4,target=original.target_sha256,
        feature_capsule=dict(file=FEATURE_FILE,sha256=FEATURE_SHA),payloads=payloads,reference_values_sha256=sha(reference.astype('<f8').tobytes()),
        provenance=dict(original_inputs={key:dict(path=str(Path(entry['path']).relative_to(ROOT)),sha256=entry['sha256'],bytes=entry['bytes']) for key,entry in inputs.items()},
            original_codec_parsing_verified=True,shared_feature_words_verified=True,weight_storage='full first-QKV FP32 weights; exact conversion to binary64 on load',
            feature_generation_reexecuted=False,new_quantization_performed=False,gram_formed=False,extraction_source_sha256=sha(Path(__file__).read_bytes())))
    raw=canonical_json(manifest);require(len(raw)<=MAX_MANIFEST,'manifest exceeds bound');new_file(directory/'manifest.json',raw)
    restored=load_capsule(directory/'manifest.json',sha(raw))
    require(np.array_equal(restored['weights'],weights) and np.array_equal(restored['reference'],reference),'full-stage roundtrip differs')
    return dict(manifest=str(directory/'manifest.json'),sha256=sha(raw),manifest_bytes=len(raw),shard_count=sum(len(p['shards']) for p in payloads.values()),
        total_shard_bytes=sum(x['bytes'] for p in payloads.values() for x in p['shards']),maximum_shard_bytes=max(x['bytes'] for p in payloads.values() for x in p['shards']),
        rows=ROWS,width=WIDTH,codes=ROWS*WIDTH,new_quantization_performed=False,gram_formed=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--export',required=True,type=Path);a=p.parse_args();print(json.dumps(create_capsule(a.export),sort_keys=True))
