"""Bounded archived-feature algebra. Never loads a neural decoder or regenerates features."""
from __future__ import annotations
import argparse
from dataclasses import asdict, is_dataclass
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from src.run_store import canonical_json, digest
from src.fixed_lossless_state_v29 import parse as parse_state
from src.fixed_lossless_codec_v29 import serialize as serialize_descriptor
from src.compact_state import StageCodes, _dyadic_grid_bytes
from src.runtime_contract import capture_runtime_contract
from src.experiment_inventory import source_hashes

STAGE = 'block.0000.qkv'
DELETED = 'wikitext2:train:article-row-17380'
RETAINED = 'wikitext2:train:article-row-22925'
DEFAULT_INPUTS = {
 'original_state': ('campaigns/independent_wikitext_v32/attempts/wikitext-root-prepare/outputs/state.bin', '24bd6278cc5ee98d1a562b0f260d341e763fd9d09d68ab7b9944c68893db4d8a'),
 'retained_state': ('campaigns/independent_wikitext_v32/attempts/wikitext-delete-0-repair/outputs/state.bin', 'e8b6a4515b0ff7f25fa78d48355613ff0ae1e034fa082342dea7e7a8001c9043'),
 'weights': ('tmp/models/distilgpt2/model.safetensors', 'e1ff18884359fe8beb795a5f414feb85a6ce3d929ad019c0d958c039d2b94a1b'),
}

def require(ok, message):
    if not ok: raise ValueError(message)

def hashed(path):
    p = Path(path)
    require(p.is_file() and not p.is_symlink() and not any(x.is_symlink() for x in p.parents), 'unsafe or missing file: '+str(p))
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def new_file(path, payload):
    """Create once, fsync bytes, and never replace any previous attempt artifact."""
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f:
        f.write(payload); f.flush(); os.fsync(f.fileno())
    fd=os.open(p.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def current_sources():
    result=source_hashes(ROOT)
    for p in sorted((ROOT/'research_v35').glob('*.py')):
        result[str(p.relative_to(ROOT))]=hashed(p)
    for name in ('execute_gram_pilot_v35.py','launch_gram_pilot_v35.py'):
        result['scripts/'+name]=hashed(ROOT/'scripts'/name)
    return result

def bind_inputs(input_root=ROOT):
    result={}
    for key,(name,expected) in DEFAULT_INPUTS.items():
        p=Path(input_root)/name
        require(hashed(p)==expected, 'archived '+key+' bytes differ from pinned original')
        result[key]=dict(path=str(p.resolve()),sha256=expected,bytes=p.stat().st_size)
    return result

def verify_inputs(entries):
    if set(entries)=={'capsule'}:
        entry=entries['capsule'];p=Path(entry['path'])
        require(set(entry)=={'path','sha256','bytes'} and p.is_absolute() and hashed(p)==entry['sha256'] and p.stat().st_size==entry['bytes'],'capsule binding differs')
        return
    for key,entry in entries.items():
        require(key in DEFAULT_INPUTS and set(entry)=={'path','sha256','bytes'},'unknown input entry')
        require(entry['sha256']==DEFAULT_INPUTS[key][1],'input digest is not the declared archive')
        p=Path(entry['path'])
        require(p.is_absolute() and hashed(p)==entry['sha256'] and p.stat().st_size==entry['bytes'], 'input changed: '+key)
    require(set(entries)==set(DEFAULT_INPUTS),'missing input')

def read_archives(entries):
    original=parse_state(Path(entries['original_state']['path']).read_bytes(), expected_sha256=entries['original_state']['sha256'])
    retained=parse_state(Path(entries['retained_state']['path']).read_bytes(), expected_sha256=entries['retained_state']['sha256'])
    require(original.record_ids==(DELETED,RETAINED) and retained.record_ids==(RETAINED,), 'membership differs')
    require(original.target_sha256==retained.target_sha256, 'targets differ')
    for state in (original,retained):
        stage=state.stages[0]
        require(stage.stage_id==STAGE and stage.shape==(2304,768) and stage.grid_axis=='dyadic_row' and stage.bits==4,'first stage differs')
        require(all(a.descriptors[0].shape==(128,768) and a.descriptors[0].stage_id==STAGE for a in state.anchors),'feature shape differs')
    descriptors={a.record_id:a.descriptors[0] for a in original.anchors}
    descriptor_retained=retained.anchors[0].descriptors[0]
    require(serialize_descriptor(descriptors[RETAINED])==serialize_descriptor(descriptor_retained),'retained descriptor changed')
    return original,retained,descriptors,descriptor_retained

def decode(descriptor):
    return np.frombuffer(descriptor.binary64(),dtype='<f8').reshape(descriptor.shape).copy()

def checkpoint_rows(path):
    """Read only the first QKV tensor; Conv1D source axes are input, output."""
    with Path(path).open('rb') as f:
        raw=f.read(8);require(len(raw)==8,'truncated safetensors header')
        n=struct.unpack('<Q',raw)[0];require(0<n<=16*2**20,'oversized safetensors header')
        header=json.loads(f.read(n));entry=header['transformer.h.0.attn.c_attn.weight']
        require(entry['dtype']=='F32' and entry['shape']==[768,2304], 'unexpected QKV tensor')
        lo,hi=entry['data_offsets'];require(type(lo)is int and type(hi)is int and 0<=lo<hi and hi-lo==768*2304*4,'tensor offsets differ')
        f.seek(8+n+lo);raw=f.read(hi-lo);require(len(raw)==hi-lo,'truncated QKV tensor')
    result=np.frombuffer(raw,dtype='<f4').reshape(768,2304)[:,:4].T.astype(np.float64).copy()
    require(result.shape==(4,768) and np.isfinite(result).all(),'invalid complete weight rows')
    return result

def reference_rows(state):
    stage=state.stages[0]
    indices=stage.indices_array()[:4].copy()
    result=np.empty((4,768),dtype=np.float64)
    for r in range(4):
        grid=np.frombuffer(_dyadic_grid_bytes(stage.scale_values[r],4),dtype='<f8')
        result[r]=grid[indices[r]]
    return result

def public_result(value):
    result=asdict(value) if is_dataclass(value) else dict(value)
    result.pop('codes',None)
    def clean(x):
        if isinstance(x,np.ndarray):return dict(shape=list(x.shape),dtype=str(x.dtype),sha256=digest(x.tobytes()))
        if is_dataclass(x):return clean(asdict(x))
        if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
        if isinstance(x,(list,tuple)):return [clean(v) for v in x]
        if isinstance(x,np.generic):return x.item()
        if isinstance(x,Fraction):return [x.numerator,x.denominator]
        return x
    return clean(result)

def load_registered_inputs(entries):
    if set(entries)=={'capsule'}:
        from research_v35.archive_capsule import load_capsule
        return load_capsule(entries['capsule']['path'],entries['capsule']['sha256'])
    original,retained,descriptors,retained_descriptor=read_archives(entries)
    return dict(descriptors=descriptors,retained_descriptor=retained_descriptor,
        weights=checkpoint_rows(entries['weights']['path']),reference=reference_rows(retained),
        scales=tuple(retained.stages[0].scale_values[:4]),target=original.target_sha256)

def descriptor_bytes(descriptor):
    if hasattr(descriptor,'serialized_descriptor'):return descriptor.serialized_descriptor
    return serialize_descriptor(descriptor)

def admission(entries):
    """Only parse bytes, scan finite exponent ranges, and assess structural bounds."""
    from research_v35.exact_gram import assess_features, GramBudget
    from research_v35.direct_gram import assess_direct_gram_budget
    from src.primal_certificate_v30 import PrimalBudget
    verify_inputs(entries)
    data=load_registered_inputs(entries)
    descriptors=data['descriptors'];retained_descriptor=data['retained_descriptor']
    features=np.concatenate([decode(descriptors[rid]) for rid in (DELETED,RETAINED)])
    gram=asdict(assess_features(features.T.copy(), budget=GramBudget()))
    direct=assess_direct_gram_budget(rows=4,width=768,bits=4,budget=PrimalBudget(max_workspace_bytes=512*2**20,max_work_units=600_000_000))
    require(direct['admitted'],'component numerical admission failed')
    weights=data['weights']
    return dict(schema='archive-gram-admission-v35', no_gram_formed=True,no_codes_computed=True,
        gram=gram,direct=direct,stage_id=STAGE,rows=[0,1,2,3],width=768,original_tokens=256,retained_tokens=128,
        normalization=256,feature_sha256=digest(features.astype('<f8').tobytes()),weight_rows_sha256=digest(weights.astype('<f8').tobytes()),
        target_sha256=data['target'],descriptor_sha256={rid:digest(descriptor_bytes(d)) for rid,d in descriptors.items()},
        retained_descriptor_sha256=digest(descriptor_bytes(retained_descriptor)),
        runtime=capture_runtime_contract(), numpy_version=np.__version__)

def worker(plan_path):
    from research_v35.exact_gram import accumulate, add_grams, subtract_gram, dumps, loads, GramBudget
    from research_v35.direct_gram import certify_exact_gram
    from src.primal_certificate_v30 import PrimalBudget, prepare_primal_native
    from src.native_ball_quantizer import prepare_native_ball
    from src.native_token_coefficients_v30 import prepare_native_token_coefficients
    from src.fast_token_quantizer_v30 import native_fast_quantize_dyadic_rows
    from src.dyadic_row_quantizer import dyadic_row_scales
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_bytes());out=Path(plan['output'])
    require(not out.exists(),'attempt output already exists; no retry')
    out.mkdir(parents=True)
    record=dict(schema='archive-gram-pilot-result-v35',status='running',plan_sha256=hashed(plan_path),component_only=True,
      feature_generation_reexecuted=False,confirmation=False,arm_order=plan['arm_order'],timings_ns={},artifacts={},phases=[])
    def mark(phase):
        record['phases'].append(phase)
        new_file(out/f'progress-{len(record["phases"]):02d}.json',canonical_json(record))
        print(json.dumps({'phase':phase}),flush=True)
    def timed(name,fn):
        start=time.perf_counter_ns();value=fn();record['timings_ns'][name]=time.perf_counter_ns()-start
        return value
    def artifact(name,payload):
        new_file(out/name,payload);record['artifacts'][name]=dict(sha256=digest(payload),bytes=len(payload))
    def packed_codes(name,codes):
        require(np.array_equal(codes,reference),'codes differ from archived retained reference')
        stage=StageCodes.from_array(STAGE,codes,bits=4,grid_axis='dyadic_row',scale_values=scales)
        artifact(name,stage.packed_indices)
        return dict(codes=int(codes.size),sha256=digest(stage.packed_indices),scales_hex=[s.hex() for s in scales])
    try:
        require(current_sources()==plan['source_sha256'],'numerical or controller source changed')
        require(capture_runtime_contract()==plan['runtime'],'registered software runtime changed')
        timed('common_input_verification',lambda:verify_inputs(plan['inputs']))
        data=timed('common_archive_capsule_parse',lambda:load_registered_inputs(plan['inputs']))
        descriptors=data['descriptors'];retained_descriptor=data['retained_descriptor'];weights=data['weights'];reference=data['reference']
        scales=dyadic_row_scales(weights)
        require(scales==data['scales'],'canonical row scales differ')
        record['native_builds']=timed('common_native_build',lambda:dict(primal=prepare_primal_native(),token_loop=prepare_native_ball(),token_coefficients=prepare_native_token_coefficients()))
        mark('shared_inputs_and_native_build_complete')
        gb=GramBudget();pb=PrimalBudget(max_workspace_bytes=512*2**20,max_work_units=600_000_000)
        start=time.perf_counter_ns()
        original_features=timed('prepare_feature_decode',lambda:np.concatenate([decode(descriptors[r]) for r in (DELETED,RETAINED)]))
        original_gram=timed('prepare_exact_accumulation',lambda:add_grams(accumulate(original_features[:128].T.copy(),source_id=DELETED,normalization=256,budget=gb),accumulate(original_features[128:].T.copy(),source_id=RETAINED,normalization=256,budget=gb),budget=gb))
        original_bytes=timed('prepare_serialize',lambda:dumps(original_gram))
        artifact('original-gram.bin',original_bytes)
        original_sources=original_gram.sources
        record['original_gram_sources']=[asdict(v) for v in original_sources]
        record['timings_ns']['prepare_component_total']=time.perf_counter_ns()-start
        del original_features,original_gram,original_bytes
        mark('pooled_gram_preparation_complete')
        start=time.perf_counter_ns()
        original_gram=timed('delete_load_parse_original',lambda:loads((out/'original-gram.bin').read_bytes(),trusted_sha256=record['artifacts']['original-gram.bin']['sha256'],expected_sources=original_sources))
        deleted_features=timed('delete_feature_decode',lambda:decode(descriptors[DELETED]))
        deleted_gram=timed('delete_exact_accumulation',lambda:accumulate(deleted_features.T.copy(),source_id=DELETED,normalization=256,budget=gb))
        repaired=timed('delete_exact_subtraction',lambda:subtract_gram(original_gram,deleted_gram))
        repaired_bytes=timed('delete_serialize',lambda:dumps(repaired))
        artifact('retained-gram.bin',repaired_bytes)
        repaired_result=timed('delete_solve_certificate',lambda:certify_exact_gram(weights,repaired,ridge=Fraction(1,100),budget=pb))
        record['delete_codes']=packed_codes('delete-codes.bin',repaired_result.codes)
        record['timings_ns']['delete_component_total']=time.perf_counter_ns()-start
        record['delete_certificate']=public_result(repaired_result)
        del original_gram,deleted_gram,deleted_features,repaired
        mark('pooled_gram_deletion_complete')
        start=time.perf_counter_ns()
        retained_features=timed('cold_feature_decode',lambda:decode(retained_descriptor))
        cold_gram=timed('cold_exact_accumulation',lambda:accumulate(retained_features.T.copy(),source_id=RETAINED,normalization=256,budget=gb))
        cold_bytes=timed('cold_serialize',lambda:dumps(cold_gram))
        artifact('cold-retained-gram.bin',cold_bytes)
        require(cold_bytes==repaired_bytes,'exact pooled Gram subtraction differs from independent retained construction')
        cold_result=timed('cold_solve_certificate',lambda:certify_exact_gram(weights,cold_gram,ridge=Fraction(1,100),budget=pb))
        record['cold_codes']=packed_codes('cold-codes.bin',cold_result.codes)
        record['timings_ns']['cold_component_total']=time.perf_counter_ns()-start
        record['cold_certificate']=public_result(cold_result)
        del retained_features,cold_gram,cold_bytes,repaired_bytes
        mark('cold_gram_reconstruction_complete')
        start=time.perf_counter_ns()
        cache_features=timed('cache_feature_decode',lambda:decode(retained_descriptor))
        cache_result=timed('cache_token_solve_certificate',lambda:native_fast_quantize_dyadic_rows(weights,cache_features.T.copy(),ridge=Fraction(1,100),normalization=256))
        record['cache_codes']=packed_codes('cache-codes.bin',cache_result.codes)
        record['timings_ns']['cache_component_total']=time.perf_counter_ns()-start
        record['cache_certificate']=public_result(cache_result)
        record.update(status='complete',exact_gram_equality=True,all_three_code_arrays_equal=True,
            retained_descriptor_bytes=len(descriptor_bytes(retained_descriptor)),retained_feature_bytes=int(cache_features.nbytes),
            exact_product_contributions=151_191_552,exact_packed_additions=295_296,exact_packed_subtractions=295_296,neural_stage_traversals=0,
            claim_scope='One fixed-order four-row component development observation. No complete service speed or feature-generation revalidation.',
            excludes='Shared artifact verification, archive parsing, weight load, and native builds reported separately. Neural replay absent; original model preparation absent. No lifetime claim.',
            expansion_gate='Correct exact algebra permits designing a larger comparator; latency does not trigger automatic expansion.')
        mark('all_registered_component_checks_complete')
    except BaseException as exc:
        record.update(status='failed',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        new_file(out/'failure.json',canonical_json(record))
        raise
    raw=canonical_json(record);new_file(out/'completion.json',raw)
    print('GRAM_PILOT_TERMINAL_SHA256='+digest(raw),flush=True)
    return record

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan');args=parser.parse_args();worker(args.plan)
