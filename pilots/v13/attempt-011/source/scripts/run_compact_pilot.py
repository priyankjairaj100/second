"""Bounded real-checkpoint admission diagnostic. Never a repair speed claim."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import struct
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json, atomic_write, digest
from src.experiment_inventory import source_hashes
from src.transaction_timing import verify_command_admission


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path)
    args=parser.parse_args()
    plan=json.loads(args.plan.read_bytes())
    root=Path(__file__).resolve().parents[1]
    if source_hashes(root)!=plan['source_sha256']:raise ValueError('source binding mismatch')
    verify_command_admission(plan['protocol_sha256'],'feasibility',[sys.executable,str(Path(__file__).resolve()),str(args.plan.absolute())])
    output=Path(plan['output']);output.mkdir(parents=True,exist_ok=True)
    result={'schema':'compact-real-pilot-v12','status':'running','mode':plan['mode'],
            'plan_sha256':digest(args.plan.read_bytes()),'full_model_repair':False,
            'complete_repair_speed_evidence':False,'phases':[],'records':[]}
    started=time.perf_counter_ns()
    def save(phase=None,**details):
        if phase:result['phases'].append({'phase':phase,'elapsed_ns':time.perf_counter_ns()-started,**details})
        result['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json',canonical_json(result))
        if phase:print(json.dumps(result['phases'][-1]),flush=True)
    try:
        save('input_validation')
        cp=Path(plan['checkpoint'])
        for name,expected in plan['checkpoint_sha256'].items():
            with (cp/name).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
            if actual!=expected:raise ValueError('checkpoint digest mismatch: '+name)
        path=Path(plan['records'])
        if digest(path.read_bytes())!=plan['records_sha256']:raise ValueError('records changed')
        records=json.loads(path.read_bytes())['records']
        if len(records)!=2 or any(len(r['tokens'])!=16 for r in records):raise ValueError('pilot expects two real records of sixteen tokens')
        deleted=plan.get('deleted_record_ids',[])
        if len(set(deleted))!=len(deleted) or not set(deleted)<=set(r['id'] for r in records):raise ValueError('invalid deletion membership')
        result['original_record_ids']=[r['id'] for r in records]
        records=[r for r in records if r['id'] not in deleted]
        if not records:raise ValueError('this pilot requires at least one retained record')
        result['retained_record_ids']=[r['id'] for r in records]
        result['deleted_record_ids']=deleted
        result['fixed_original_normalization']=32
        from src.compact_preflight import inspect_compact_forward_config
        from src.target_manifest import TargetRecipe
        admission=inspect_compact_forward_config(cp,TargetRecipe(original_token_count=32,group_count=1),max_record_tokens=16).payload()
        result['compact_plan']=admission
        if not admission['allowed_by_plan']:raise ValueError('compact admission rejected')
        save('checkpoint_loading')
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        loaded=load_gpt2_checkpoint(cp,identity_encoding=plan['parameter_identity_encoding'])
        decoder=CertifiedDecoder(loaded.decoder,primitive_backend=plan['primitive_backend'])
        result['checkpoint_provenance']=loaded.provenance
        result['evaluator_id']=decoder.evaluator_id
        atomic_write(output/'evaluator.json',canonical_json(decoder.kernel_manifest))
        save('checkpoint_loaded')
        from src.target_manifest import build_target,TargetRecipe
        if plan.get('grid_axis','column')=='row':
            from src.row_target_manifest import build_row_target
            constructor=build_row_target
        else:constructor=build_target
        target=constructor(decoder,TargetRecipe(original_token_count=32,group_count=1),
            weight_digest_encoding=plan['weight_digest_encoding'])
        result['grid_axis']=plan.get('grid_axis','column')
        atomic_write(output/'target.json',canonical_json(target.payload()))
        result['target_sha256']=target.digest
        save('target_constructed',stages=len(target.stages))
        if plan['mode']=='load_forward':
            for record in records:
                before=time.perf_counter_ns()
                logits=decoder.logits(record['tokens'])
                h=hashlib.sha256()
                nll=0.0
                for index,row in enumerate(logits):
                    for value in row:h.update(struct.pack('<d',value))
                    if index+1<len(record['tokens']):
                        maximum=max(row)
                        logz=maximum+math.log(sum(math.exp(x-maximum) for x in row))
                        nll+=logz-row[record['tokens'][index+1]]
                result['records'].append({'id':record['id'],'status':'complete','shape':[len(logits),len(logits[0])],
                  'logits_sha256':h.hexdigest(),'elapsed_ns':time.perf_counter_ns()-before,
                  'next_token_count':len(record['tokens'])-1,'diagnostic_nll_sum':nll,
                  'nll_is_not_certified_interval':True})
                save('record_forward_complete',record_id=record['id'])
        elif plan['mode']=='model_quality':
            from src.compact_exact import CompactDyadicVector
            comparison=plan['comparison_model'];index_path=Path(comparison['index'])
            if digest(index_path.read_bytes())!=comparison['index_sha256']:raise ValueError('quality model index changed')
            model_index=json.loads(index_path.read_bytes())
            model_plan_path=Path(comparison['plan'])
            if digest(model_plan_path.read_bytes())!=comparison['plan_sha256']:raise ValueError('quality model plan changed')
            model_plan=json.loads(model_plan_path.read_bytes())
            if model_plan['records_sha256']!=plan['records_sha256']:raise ValueError('quality model source mismatch')
            model_deleted=model_plan.get('deleted_record_ids',[])
            if len(model_deleted)!=len(set(model_deleted)) or not set(model_deleted)<=set(result['original_record_ids']):raise ValueError('quality model deletion metadata invalid')
            result['deleted_record_ids']=model_deleted
            result['retained_record_ids']=[rid for rid in result['original_record_ids'] if rid not in model_deleted]
            result['quality_model_plan_sha256']=comparison['plan_sha256']
            if model_index['target_sha256']!=target.digest:raise ValueError('quality target mismatch')
            if [s['stage_id'] for s in model_index['stages']]!=[s.stage_id for s in target.stages]:raise ValueError('quality requires complete model')
            prefix={}
            for row,stage in zip(model_index['stages'],target.stages):
                if row['shape']!=[len(stage.weights),stage.width]:raise ValueError('quality model shape mismatch')
                raw=(index_path.parent/row['codes_file']).read_bytes()
                if digest(raw)!=row['codes_sha256']:raise ValueError('quality codes changed')
                prefix[stage.stage_id]=CompactDyadicVector.from_bytes(raw,'F64').matrix(*row['shape'])
            eval_path=Path(plan['evaluation_records'])
            if digest(eval_path.read_bytes())!=plan['evaluation_records_sha256']:raise ValueError('evaluation records changed')
            evaluation=json.loads(eval_path.read_bytes())['records']
            if len(evaluation)!=2 or any(len(r['tokens'])!=16 or not r['id'].startswith('wikitext2:validation:') for r in evaluation):raise ValueError('quality expects two disjoint validation records')
            if set(r['id'] for r in evaluation)&set(result['original_record_ids']):raise ValueError('evaluation overlaps calibration')
            result['quality']={}
            for label,installed in [('base',None),('retained_quantized',prefix)]:
                from src.prepared_finite import PreparedFinitePrefix
                evaluator=PreparedFinitePrefix(decoder,installed)
                save('quality_prefix_validated',model=label)
                total=0.0;count=0;rows=[]
                for record in evaluation:
                    before=time.perf_counter_ns();logits=evaluator.logits(record['tokens']);nll=0.0
                    for i,row in enumerate(logits[:-1]):
                        maximum=max(row)
                        nll+=maximum+math.log(sum(math.exp(x-maximum) for x in row))-row[record['tokens'][i+1]]
                    total+=nll;count+=len(logits)-1
                    rows.append({'id':record['id'],'nll_sum':nll,'tokens':len(logits)-1,'elapsed_ns':time.perf_counter_ns()-before})
                    save('quality_record_complete',model=label,record_id=record['id'])
                result['quality'][label]={'nll_sum':total,'tokens':count,'perplexity':math.exp(total/count),'records':rows}
            result['quality']['retained_to_base_perplexity_ratio']=math.exp((result['quality']['retained_quantized']['nll_sum']-result['quality']['base']['nll_sum'])/result['quality']['base']['tokens'])
            result['quality']['scope']='two fixed heldout records; ordinary floating NLL; no precision, population, or gate claim'
            result['quality']['scientific_quality_gate_closed']=False
        elif plan['mode'] in ('first_stage_quantization','full_quantization'):
            import numpy as np
            from src.sequential_finite import sequential_features
            from src.low_rank_certified import certified_token_codes
            # The finite-only planner excludes installed codes and exact fallback.
            # Add explicit planning allowances. The bounded worker remains required.
            parameters=sum(len(s.weights)*s.width for s in target.stages)
            rank=sum(len(r['tokens']) for r in records)
            widest=max(s.width for s in target.stages)
            extra=16*parameters+64*widest*rank+128*rank*rank+512*2**20
            quant_plan=dict(schema='token-quantizer-planning-v12',planning_bytes=admission['planning_bytes']+extra,
                budget_bytes=6*2**30,allowed_by_plan=admission['planning_bytes']+extra<=6*2**30,
                memory_bound_proved=False,exclusions=['canonical response state','unbounded rational integer growth'],
                scope='model codes only; exact fallback has count limits and external worker limits')
            result['token_quantization_plan']=quant_plan
            if not quant_plan['allowed_by_plan']:raise ValueError('token quantizer planning rejected')
            ordered=sorted(records,key=lambda r:r['id'])
            streams=[sequential_features(decoder,r['tokens']) for r in ordered]
            current=[next(stream) for stream in streams]
            comparison=plan.get('comparison_model')
            prior_streams=None
            if comparison:
                index_path=Path(comparison['index'])
                if digest(index_path.read_bytes())!=comparison['index_sha256']:raise ValueError('comparison index changed')
                prior_index=json.loads(index_path.read_bytes())
                if prior_index['target_sha256']!=target.digest or comparison['target_sha256']!=target.digest:raise ValueError('comparison target mismatch')
                prior_streams=[sequential_features(decoder,r['tokens']) for r in ordered]
                prior_current=[next(stream) for stream in prior_streams]
            result['stages']=[]
            for stage_index,stage in enumerate(target.stages):
                if any(sid!=stage.stage_id for sid,_ in current):raise ValueError('incremental stage mismatch')
                features=np.concatenate([np.asarray(rows,dtype=np.float64) for _,rows in current],axis=0).T.copy()
                feature_comparison=[]
                old_codes=None
                if prior_streams:
                    old_stage=prior_index['stages'][stage_index]
                    if old_stage['stage_id']!=stage.stage_id:raise ValueError('comparison stage mismatch')
                    raw=(index_path.parent/old_stage['codes_file']).read_bytes()
                    if digest(raw)!=old_stage['codes_sha256']:raise ValueError('comparison codes changed')
                    old_codes=np.frombuffer(raw,dtype='<f8').reshape(old_stage['shape'])
                    for record,(_,now),(sid,previous) in zip(ordered,current,prior_current):
                        if sid!=stage.stage_id:raise ValueError('comparison stream mismatch')
                        a=np.asarray(now,dtype=np.float64);b=np.asarray(previous,dtype=np.float64)
                        feature_comparison.append({'record_id':record['id'],'values':a.size,
                            'changed_binary64_values':int(np.count_nonzero(a.view(np.uint64)!=b.view(np.uint64))),
                            'maximum_absolute_change_diagnostic':float(np.max(np.abs(a-b)))})
                weights=stage.weights.float_array()
                before=time.perf_counter_ns()
                save('quantization_start',stage_id=stage.stage_id,rank=rank)
                if plan.get('grid_axis','column')=='row':
                    from src.row_scaled_quantizer import quantize_row_scaled
                    quantized=quantize_row_scaled(weights,features,stage.scale_exponents,bits=stage.bits,ridge=stage.ridge,
                        normalization=stage.normalization,max_exact_rank=64,max_exact_coordinates=16,max_refinement_coordinates=64)
                else:
                    quantized=certified_token_codes(weights,features,stage.grids,ridge=stage.ridge,
                        normalization=stage.normalization,max_exact_rank=64,max_exact_coordinates=16,max_refinement_coordinates=64)
                raw=quantized.codes.astype('<f8',copy=False).tobytes()
                name=stage.stage_id+'.codes.bin'
                atomic_write(output/name,raw)
                row=dict(stage_id=stage.stage_id,shape=list(quantized.codes.shape),codes_sha256=digest(raw),
                    codes_file=name,interval_decisions=quantized.interval_decisions,exact_decisions=quantized.exact_decisions,
                    exact_coordinates=list(quantized.exact_coordinates),refined_coordinates=list(quantized.refined_coordinates),
                    quantizer_ns=time.perf_counter_ns()-before)
                row['feature_comparison']=feature_comparison
                row['max_coefficient_error_squared']=quantized.max_coefficient_error_squared
                if old_codes is not None:
                    row['changed_codes']=int(np.count_nonzero(old_codes.view(np.uint64)!=quantized.codes.view(np.uint64)))
                    row['compared_codes']=int(old_codes.size)
                result['stages'].append(row)
                save('quantization_complete',stage_id=stage.stage_id)
                if plan['mode']=='first_stage_quantization':break
                if stage_index+1<len(target.stages):
                    current=[stream.send(quantized.codes) for stream in streams]
                    if prior_streams:prior_current=[stream.send(old_codes) for stream in prior_streams]
            result['full_model_quantization']=len(result['stages'])==len(target.stages)
            result['canonical_repair_state']=False
            atomic_write(output/'model-index.json',canonical_json({'target_sha256':target.digest,'stages':result['stages']}))
        else:raise ValueError('unsupported pilot mode')
        result['status']='complete';save('complete')
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise


if __name__=='__main__':main()
