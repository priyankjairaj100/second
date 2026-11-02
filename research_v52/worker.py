"""Encode48 and certify the same prepared source boxes, without neural access."""
from pathlib import Path
import os
import resource
import sys
import time
import traceback
import numpy as np
from research_v43.campaign import read,new,sha,require
from research_v43 import dispatcher as dispatch
from research_v50.neighbors import enabled
from research_v51.stage import STAGE_ID,HISTORICAL_CODE
from src import fixed_lossless_codec_v29 as lossless,fixed_factor_codec_v26 as codec
from src.compact_state import StageCodes
from src.run_store import canonical_json,digest
from src.transaction_timing import verify_command_admission
from scripts.execute_gram_pilot_v35 import public_result

PRECISION=48


def encode_checked(raw,item,manifest):
    desc=lossless.parse(raw,expected_sha256=digest(raw))
    require(desc.source_sha256==item['features_sha256'] and desc.record_id==item['record_id'] and
        desc.stage_id==STAGE_ID and desc.target_sha256==manifest['target_sha256'] and
        desc.anchor_target_sha256==manifest['anchor_target_sha256'] and desc.token_sha256==item['token_sha256'],
        'Exact source binding differs')
    values=desc.array()
    encoded=codec.encode_factor(values,target_sha256=desc.target_sha256,anchor_target_sha256=desc.anchor_target_sha256,
        record_id=desc.record_id,token_sha256=desc.token_sha256,stage_id=desc.stage_id,bits=PRECISION,block_size=256)
    blob=codec.serialize(encoded);restored=codec.parse(blob,expected_sha256=digest(blob));box=restored.box()
    require(restored.bits==48 and restored.block_size==256 and restored.source_sha256==desc.source_sha256 and
        np.all(box.lower<=values) and np.all(values<=box.upper),'48-bit containment failed')
    return blob


def compare_codes(actual,expected,count,expected_hash):
    require(len(actual)*2==count and actual==expected and digest(actual)==expected_hash,
        'Complete point/box code bytes differ')


def main(directory):
    from research_v52.campaign import verify
    d=Path(directory).resolve();p=verify(d);ph=sha(d/'program.json')
    verify_command_admission(ph,'precision48',[sys.executable,'-B','-m','research_v52.worker',str(d)])
    out=d/'outputs';out.mkdir();start=time.perf_counter_ns();progress=0
    result=dict(schema='precision48-stage-result-v52',program_sha256=ph,status='running',artifacts={},
        slurm_job_id=os.environ['SLURM_JOB_ID'],complete_model=False,quality_evaluation=False,confirmation=False,
        acl_ready=False,new_quality_data=False,source_neural_traversals=0,point_retry=False)
    def artifact(name,blob):
        result['artifacts'][name]=new(out/name,blob,raw=True)
    def mark(phase,**details):
        nonlocal progress
        row=dict(phase=phase,elapsed_ns=time.perf_counter_ns()-start,**details)
        new(out/f'progress-{progress:04d}.json',row);progress+=1
        print(canonical_json(row).decode(),flush=True)
    try:
        prepared=Path(p['v51_directory'])/'prepare/outputs';manifest=read(prepared/'inputs.json')
        spec=dispatch.StageSpec.from_manifest(manifest['entry'],target_sha256=manifest['target_sha256'])
        admission=dispatch.assess_stage(spec,1664,kind='box',block_tokens=128,max_blocks=13,resident_bytes=4*2**30)
        require(admission['admitted'] and admission['selected_route']=='streamed','Actual box stage refused')
        tick=time.perf_counter_ns();names=[]
        for i,item in enumerate(manifest['records']):
            raw=(prepared/item['descriptors']['lossless']).read_bytes()
            blob=encode_checked(raw,item,manifest);name=f'compressed48-{i:02d}.bin'
            artifact(name,blob);names.append(name)
            mark('source_encoded',record_id=item['record_id'],descriptor_bytes=len(blob))
        result['encoding_and_containment_ns']=time.perf_counter_ns()-tick
        result['feature_descriptor_bytes']=sum(result['artifacts'][name]['bytes'] for name in names)
        result['source_manifest_sha256']=sha(prepared/'inputs.json')
        def blocks():
            for name in names:
                raw=(out/name).read_bytes()
                require(digest(raw)==result['artifacts'][name]['sha256'],'Encoded descriptor changed')
                box=codec.parse(raw,expected_sha256=digest(raw)).box()
                yield np.ascontiguousarray(box.lower.T),np.ascontiguousarray(box.upper.T)
        weights=np.frombuffer((prepared/'weights.f64').read_bytes(),dtype='<f8').reshape(768,3072).copy()
        mark('solve_started',bits=48,code_count=2359296)
        tick=time.perf_counter_ns()
        with enabled() as build:
            result['backend']=dict(build)
            answer=dispatch.solve_blocks(spec,weights,blocks(),total_tokens=1664,kind='box',
                block_tokens=128,max_blocks=13,resident_bytes=4*2**30)
            code=StageCodes.from_array(STAGE_ID,answer.codes,grid_axis='dyadic_row',bits=4,scale_values=spec.scale_values)
            blob=code.packed_indices
            compare_codes(blob,(Path(p['v51_directory'])/'candidate/outputs/codes.bin').read_bytes(),2359296,HISTORICAL_CODE)
            artifact('codes.bin',blob)
            result.update(solve_and_write_elapsed_ns=time.perf_counter_ns()-tick,code_count=2359296,
                code_sha256=digest(blob),diagnostics=public_result(answer.solver_result),
                admission=answer.admission,actual_point_code_bytes_equal=True,status='complete')
            mark('stage_certified',code_sha256=digest(blob),code_count=2359296)
    except Exception as error:
        result.update(status='failed',error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
        if isinstance(error,dispatch.DispatchRefused):result['refusal_diagnostics']=public_result(error.diagnostics)
        raise
    finally:
        use=resource.getrusage(resource.RUSAGE_SELF)
        result.update(worker_elapsed_ns=time.perf_counter_ns()-start,max_rss_kib=use.ru_maxrss,
            cpu_seconds=use.ru_utime+use.ru_stime,external_v51_preparation_charge=430,
            timing_scope='Verification, bound source reads, encoding/containment, native build, solve and code write. Historical neural preparation is reused and charged separately; this is not service latency.')
        new(out/'completion.json',result)


if __name__=='__main__':main(sys.argv[1])
