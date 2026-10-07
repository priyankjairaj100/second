"""Fixed prospective comparison of finer row grids on new real articles."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json,atomic_write,digest
from src.experiment_inventory import source_hashes
from src.transaction_timing import verify_command_admission


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);args=p.parse_args()
    plan=json.loads(args.plan.read_bytes());root=Path(__file__).resolve().parents[1]
    if source_hashes(root)!=plan['source_sha256']:raise ValueError('source binding mismatch')
    verify_command_admission(plan['protocol_sha256'],'feasibility',[sys.executable,str(Path(__file__).resolve()),str(args.plan.absolute())])
    output=Path(plan['output']);output.mkdir(parents=True,exist_ok=True);started=time.perf_counter_ns()
    result=dict(schema='dyadic-row-quality-control-v14',status='running',plan_sha256=digest(args.plan.read_bytes()),phases=[],quality={},scientific_gate_closed=False)
    def save(phase,**details):
        result['phases'].append(dict(phase=phase,elapsed_ns=time.perf_counter_ns()-started,**details))
        result['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json',canonical_json(result));print(json.dumps(result['phases'][-1]),flush=True)
    try:
        save('input_validation');cp=Path(plan['checkpoint'])
        for name,expected in plan['checkpoint_sha256'].items():
            with (cp/name).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
            if actual!=expected:raise ValueError('checkpoint changed')
        def read_bound(item):
            raw=Path(item['path']).read_bytes()
            if digest(raw)!=item['sha256']:raise ValueError('bound input changed')
            return raw
        evaluation=json.loads(read_bound(plan['evaluation']))
        if len(evaluation['records'])!=4 or any(len(r['tokens'])!=16 for r in evaluation['records']):raise ValueError('fixed four-record control required')
        fine_plan=json.loads(read_bound(plan['dyadic_generation']));reference_plan=json.loads(read_bound(plan['power2_generation']))
        if fine_plan['records_sha256']!=reference_plan['records_sha256'] or fine_plan['deleted_record_ids']!=reference_plan['deleted_record_ids']:
            raise ValueError('quantized model calibration membership differs')
        import numpy as np
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        from src.row_target_manifest import build_row_target
        from src.dyadic_row_target import build_dyadic_row_target
        from src.compact_state import parse
        from src.compact_exact import CompactDyadicVector
        from src.ordered_finite import FiniteWeights
        from src.prepared_finite import PreparedFinitePrefix
        decoder=CertifiedDecoder(load_gpt2_checkpoint(cp,identity_encoding='binary64_tree_v2').decoder,primitive_backend='mpfr_enclosure')
        recipe=TargetRecipe(original_token_count=32,group_count=1)
        fine=build_dyadic_row_target(decoder,recipe);reference=build_row_target(decoder,recipe)
        model=parse(read_bound(plan['power2_model']))
        index=json.loads(read_bound(plan['dyadic_index']))
        if model.target_sha256!=reference.digest or index['target_sha256']!=fine.digest:raise ValueError('quality target mismatch')
        if [r['stage_id'] for r in index['stages']]!=[s.stage_id for s in fine.stages]:raise ValueError('incomplete dyadic model')
        if [s.stage_id for s in model.stages]!=[s.stage_id for s in reference.stages]:raise ValueError('incomplete power2 model')
        prefixes={'base':None,'dyadic_calibrated':{},'power2_calibrated':{},'dyadic_nearest':{}}
        def compact(values):return CompactDyadicVector.from_bytes(values.astype('<f8',copy=False).tobytes(),'F64').matrix(*values.shape)
        for codes,stage,entry in zip(model.stages,fine.stages,index['stages']):
            prefixes['power2_calibrated'][stage.stage_id]=compact(codes.array())
            raw=(Path(plan['dyadic_index']['path']).parent/entry['codes_file']).read_bytes()
            if digest(raw)!=entry['codes_sha256'] or entry['shape']!=[len(stage.weights),stage.width]:raise ValueError('dyadic model bytes or shape changed')
            prefixes['dyadic_calibrated'][stage.stage_id]=CompactDyadicVector.from_bytes(raw,'F64').matrix(*entry['shape'])
            weights=FiniteWeights(stage.weights).array();scale=np.asarray(stage.scale_values,dtype=np.float64)
            half=1<<(stage.bits-1)
            # The target constructor guarantees exact dyadic midpoint products.
            boundaries=scale[:,None]*np.arange(-half+0.5,half-0.5,1.0)[None,:]
            indices=(weights[:,:,None]>boundaries[:,None,:]).sum(axis=-1)
            nearest=(indices.astype(np.float64)-half)*scale[:,None]
            prefixes['dyadic_nearest'][stage.stage_id]=compact(nearest)
        result.update(targets={'dyadic':fine.digest,'power2':reference.digest},calibration_record_file_sha256=fine_plan['records_sha256'],deleted_record_ids=fine_plan['deleted_record_ids'],evaluation_sha256=plan['evaluation']['sha256'])
        atomic_write(output/'dyadic-target.json',canonical_json(fine.payload()));atomic_write(output/'power2-target.json',canonical_json(reference.payload()))
        save('models_prepared')
        for label in evaluation['model_order']:
            evaluator=PreparedFinitePrefix(decoder,prefixes[label]);save('prefix_prepared',model=label)
            nllsum=0.;count=0;rows=[]
            for record in evaluation['records']:
                logits=evaluator.logits(record['tokens']);nll=0.
                for i,row in enumerate(logits[:-1]):
                    maximum=max(row);nll+=maximum+math.log(sum(math.exp(x-maximum) for x in row))-row[record['tokens'][i+1]]
                n=len(logits)-1;nllsum+=nll;count+=n;rows.append(dict(id=record['id'],nll_sum=nll,tokens=n))
                result['quality'][label]=dict(nll_sum=nllsum,tokens=count,perplexity=math.exp(nllsum/count),records=rows)
                save('record_complete',model=label,record_id=record['id'])
        base=result['quality']['base']
        if {v['tokens'] for v in result['quality'].values()}!={60}:raise ValueError('quality count mismatch')
        result['ratios_to_base']={k:math.exp((v['nll_sum']-base['nll_sum'])/base['tokens']) for k,v in result['quality'].items()}
        result.update(status='complete',scope='60 new development predictions; no corpus or confirmation inference',nll_is_not_certified_interval=True)
        save('complete')
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise


if __name__=='__main__':main()
