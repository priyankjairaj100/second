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
        from src.compact_preflight import inspect_compact_forward_config
        from src.target_manifest import TargetRecipe
        admission=inspect_compact_forward_config(cp,TargetRecipe(original_token_count=32,group_count=1),max_record_tokens=16).payload()
        result['compact_plan']=admission
        if not admission['allowed_by_plan']:raise ValueError('compact admission rejected')
        save('checkpoint_loading')
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        loaded=load_gpt2_checkpoint(cp)
        decoder=CertifiedDecoder(loaded.decoder)
        result['checkpoint_provenance']=loaded.provenance
        result['evaluator_id']=decoder.evaluator_id
        save('checkpoint_loaded')
        from src.target_manifest import build_target,TargetRecipe
        target=build_target(decoder,TargetRecipe(original_token_count=32,group_count=1))
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
        else:raise ValueError('unsupported pilot mode')
        result['status']='complete';save('complete')
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise


if __name__=='__main__':main()
