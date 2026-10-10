"""Run and preserve the single declared GPU parity attempt."""
import gc
import resource
import sys
import time
import traceback
from pathlib import Path
from research_v46.campaign import read,sha,new,bound,verify,require
from src.run_store import canonical_json
from src.transaction_timing import verify_command_admission


def main(plan_path):
    plan_path=Path(plan_path).absolute();plan=read(plan_path);program=Path(plan['program'])
    p=verify(program.parent)
    require(sha(program)==plan['program_sha256'],'Plan binding differs')
    verify_command_admission(plan['program_sha256'],'development',
        [sys.executable,'-B','-m','research_v46.worker',str(plan_path)])
    out=Path(plan['output']);out.mkdir(exist_ok=False);tick=time.perf_counter_ns()
    result=dict(schema='cuda-likelihood-parity-result-v46',status='running',
        program_sha256=plan['program_sha256'],quality={},confirmation=False,acl_ready=False,
        exact_calibration_equivalence=False,certified_inference=False,new_quality_inputs=False)
    try:
        import torch
        from research_v46.evaluator import TorchQualityDecoder,compare
        from scripts.run_quality_v30 import NumpyQualityDecoder,nearest_prefix
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.compact_state import StageCodes
        from research_v42.resource_plan import BoundTarget
        from research_v44.diagnostic import reconstruct_fixed
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch.use_deterministic_algorithms(True)
        require(torch.cuda.is_available() and torch.cuda.device_count()==1,'Exactly one CUDA device is required')
        memory=torch.cuda.get_device_properties(0).total_memory
        torch.cuda.set_per_process_memory_fraction(p['gpu_allocator_bytes']/memory,0)
        torch.cuda.reset_peak_memory_stats()
        v44=read(bound(p['inputs']['v44_program']));reference=read(bound(p['inputs']['v44_completion']))
        old=read(bound(v44['inputs']['v43_program']))
        target=BoundTarget(bound(p['inputs']['base_target']).read_bytes(),bound(p['inputs']['fixed_target']).read_bytes())
        fixed=reconstruct_fixed(bound(v44['inputs']['fixed_state']).read_bytes(),
            bound(v44['inputs']['fixed_model']).read_bytes(),bound_target=target,
            records=v44['retained_records'],provenance=old['record_provenance'])
        metadata=read(bound(p['inputs']['sequential_metadata']))
        require(metadata['target_sha256']==sha(bound(p['inputs']['base_target'])),'Sequential target differs')
        blob=bound(p['inputs']['sequential_model']).read_bytes();offset=0;sequential=[]
        for entry,control in zip(metadata['stages'],fixed):
            part=blob[offset:offset+entry['nbytes']];offset+=entry['nbytes']
            stage=StageCodes(entry['stage_id'],entry['rows'],entry['columns'],entry['grid_axis'],entry['bits'],
                (),part,tuple(float.fromhex(x) for x in entry['scale_values_hex']))
            require(stage.metadata()==entry and stage.stage_id==control.stage_id
                and stage.shape==control.shape and stage.scale_values==control.scale_values,'Sequential stage/grid differs')
            sequential.append(stage)
        require(offset==len(blob) and len(sequential)==len(metadata['stages'])==24,'Sequential extent differs')
        loaded=load_gpt2_checkpoint(bound(v44['inputs']['checkpoint_config']).parent,
            identity_encoding='binary64_tree_v2')
        reference_evaluator=NumpyQualityDecoder(loaded.decoder)
        evaluator=TorchQualityDecoder(reference_evaluator)
        require(len(evaluator.weights)==24,'Complete decoder required')
        result.update(device=torch.cuda.get_device_name(0),torch=torch.__version__,
            dtype='float64',tf32=False,amp=False,deterministic_algorithms=True,
            context_elapsed_ns=time.perf_counter_ns()-tick)
        with torch.inference_mode():
            for label in ('full_precision','nearest_rounding','fixed_feature','sequential'):
                if label=='full_precision':prefix=None
                elif label=='nearest_rounding':prefix=evaluator.prefix(nearest_prefix(loaded.decoder,fixed))
                else:
                    codes=fixed if label=='fixed_feature' else sequential
                    prefix=evaluator.prefix({s.stage_id:s.array() for s in codes})
                for index,record in enumerate(p['records']):
                    torch.cuda.synchronize();start=time.perf_counter_ns()
                    loss=evaluator.nll(record['tokens'],prefix)
                    torch.cuda.synchronize();elapsed=time.perf_counter_ns()-start
                    result['quality'].setdefault(label,[]).append(dict(id=record['id'],nll_sum=loss,
                        predictions=127,elapsed_ns=elapsed))
                    if label=='full_precision' and index==0:
                        cpu=next(r for r in reference['quality'][label] if r['id']==record['id'])
                        require(abs(loss-cpu['nll_sum'])/127<=p['threshold'],'First real CUDA batch parity failed')
                        result['first_actual_batch_parity_passed']=True
                    new(out/f'progress-{label}-{index}.json',dict(model=label,record_id=record['id'],
                        nll_sum=loss,elapsed_ns=elapsed))
                del prefix;gc.collect()
        result['parity']=compare(result['quality'],reference['quality'],[r['id'] for r in p['records']],p['threshold'])
        result.update(status='complete',valid_diagnostic=True,parity_passed=result['parity']['passed'],
            copied_arrays_with_bitwise_roundtrip=evaluator.copied_arrays,
            peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
            peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved())
        require(result['peak_cuda_reserved_bytes']<=p['gpu_allocator_bytes'],'GPU allocator budget exceeded')
    except Exception as error:
        result.update(status='failed',valid_diagnostic=False,error_type=type(error).__name__,
            error=str(error),traceback=traceback.format_exc())
        raise
    finally:
        usage=resource.getrusage(resource.RUSAGE_SELF)
        result.update(worker_elapsed_ns=time.perf_counter_ns()-tick,max_rss_kib=usage.ru_maxrss,
            cpu_self_seconds=usage.ru_utime+usage.ru_stime,
            scope='32 exposed likelihood comparisons only; timings are not a controlled speed comparison')
        new(out/'completion.json',result)


if __name__=='__main__':main(sys.argv[1])
