"""Prospective real-record quality control for one fixed row-grid target."""
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
    result=dict(schema='prospective-quality-control-v13',status='running',plan_sha256=digest(args.plan.read_bytes()),phases=[],quality={},scientific_gate_closed=False)
    def save(phase,**details):
        result['phases'].append(dict(phase=phase,elapsed_ns=time.perf_counter_ns()-started,**details))
        result['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json',canonical_json(result));print(json.dumps(result['phases'][-1]),flush=True)
    try:
        cp=Path(plan['checkpoint']);save('input_validation')
        for name,expected in plan['checkpoint_sha256'].items():
            with (cp/name).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
            if actual!=expected:raise ValueError('checkpoint changed')
        raw=Path(plan['evaluation_records']).read_bytes()
        if digest(raw)!=plan['evaluation_records_sha256']:raise ValueError('evaluation changed')
        evaluation=json.loads(raw)['records']
        if len(evaluation)!=4 or any(len(r['tokens'])!=16 for r in evaluation):raise ValueError('fixed four-record control required')
        import numpy as np
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        from src.row_target_manifest import build_row_target
        from src.compact_state import parse
        from src.compact_exact import CompactDyadicVector
        from src.ordered_finite import FiniteWeights
        from src.prepared_finite import PreparedFinitePrefix
        decoder=CertifiedDecoder(load_gpt2_checkpoint(cp,identity_encoding='binary64_tree_v2').decoder,primitive_backend='mpfr_enclosure')
        target=build_row_target(decoder,TargetRecipe(original_token_count=32,group_count=1))
        model_path=Path(plan['quantized_model']['path'])
        if model_path.stat().st_size>512*2**20:raise ValueError('model file exceeds cap')
        model=parse(model_path.read_bytes(),expected_sha256=plan['quantized_model']['sha256'])
        if model.target_sha256!=target.digest:raise ValueError('target mismatch')
        prefixes={'base':None,'retained_calibrated':{},'nearest_rounding':{}}
        if len(model.stages)!=len(target.stages):raise ValueError('incomplete model')
        for codes,stage in zip(model.stages,target.stages):
            if codes.stage_id!=stage.stage_id:raise ValueError('stage mismatch')
            values=codes.array()
            prefixes['retained_calibrated'][stage.stage_id]=CompactDyadicVector.from_bytes(values.astype('<f8').tobytes(),'F64').matrix(*values.shape)
            weights=FiniteWeights(stage.weights).array()
            exponents=np.asarray(stage.scale_exponents,dtype=np.int64)[:,None]
            normalized=np.ldexp(weights,-exponents)
            if not np.array_equal(np.ldexp(normalized,exponents),weights):raise ValueError('inexact normalization')
            half=1<<(stage.bits-1)
            indices=np.searchsorted(np.arange(-half+0.5,half-0.5,1.0),normalized,side='left')
            nearest=np.ldexp(indices.astype(np.float64)-half,exponents)
            prefixes['nearest_rounding'][stage.stage_id]=CompactDyadicVector.from_bytes(nearest.astype('<f8').tobytes(),'F64').matrix(*nearest.shape)
        result.update(target_sha256=target.digest,quantized_model=plan['quantized_model'],evaluation_records_sha256=plan['evaluation_records_sha256'])
        save('models_prepared')
        for label in plan['model_order']:
            evaluator=PreparedFinitePrefix(decoder,prefixes[label]);nllsum=0.;count=0;record_results=[]
            for record in evaluation:
                logits=evaluator.logits(record['tokens']);nll=0.
                for i,row in enumerate(logits[:-1]):
                    maximum=max(row);nll+=maximum+math.log(sum(math.exp(x-maximum) for x in row))-row[record['tokens'][i+1]]
                n=len(logits)-1;nllsum+=nll;count+=n
                record_results.append(dict(id=record['id'],nll_sum=nll,tokens=n))
                result['quality'][label]=dict(nll_sum=nllsum,tokens=count,perplexity=math.exp(nllsum/count),records=record_results)
                save('record_complete',model=label,record_id=record['id'])
        base=result['quality']['base']
        result['ratios_to_base']={k:math.exp((v['nll_sum']-base['nll_sum'])/base['tokens']) for k,v in result['quality'].items()}
        result.update(status='complete',scope='60 fixed development predictions; no corpus-level or confirmation inference',nll_is_not_certified_interval=True)
        save('complete')
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise


if __name__=='__main__':main()
