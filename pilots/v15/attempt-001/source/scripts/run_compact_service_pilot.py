"""Bounded complete transactions for the factor_identity_v1 service family."""
import argparse
import hashlib
import json
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
    result=dict(schema='compact-complete-transaction-v13',status='running',method=plan['method'],
        state_family='factor_identity_v1',scientific_promotion=False,repair_speed_evidence=False,
        plan_sha256=digest(args.plan.read_bytes()),phases=[])
    def save(phase,**details):
        result['phases'].append(dict(phase=phase,elapsed_ns=time.perf_counter_ns()-started,**details))
        result['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json',canonical_json(result));print(json.dumps(result['phases'][-1]),flush=True)
    try:
        save('input_validation');cp=Path(plan['checkpoint'])
        for name,expected in plan['checkpoint_sha256'].items():
            with (cp/name).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
            if actual!=expected:raise ValueError('checkpoint bytes changed')
        raw=Path(plan['records']).read_bytes()
        if digest(raw)!=plan['records_sha256']:raise ValueError('record bytes changed')
        original=json.loads(raw)['records'];deleted=plan['deleted_record_ids']
        if len(set(deleted))!=len(deleted) or not set(deleted)<=set(r['id'] for r in original):raise ValueError('invalid deletion')
        records=[{'id':r['id'],'tokens':r['tokens']} for r in original if r['id'] not in deleted]
        if any(len(r['tokens'])!=16 for r in original) or len(original)!=2:raise ValueError('diagnostic requires the frozen two-record pilot')
        result.update(original_record_ids=[r['id'] for r in original],retained_record_ids=[r['id'] for r in records],deleted_record_ids=deleted)
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        if plan.get('grid_axis','row')=='dyadic_row':
            from src.dyadic_row_target import build_dyadic_row_target as constructor
        else:
            from src.row_target_manifest import build_row_target as constructor
        loaded=load_gpt2_checkpoint(cp,identity_encoding='binary64_tree_v2')
        decoder=CertifiedDecoder(loaded.decoder,primitive_backend='mpfr_enclosure')
        target=constructor(decoder,TargetRecipe(original_token_count=32,group_count=1))
        atomic_write(output/'target.json',canonical_json(target.payload()))
        atomic_write(output/'evaluator.json',canonical_json(decoder.kernel_manifest))
        result.update(target_sha256=target.digest,evaluator_id=decoder.evaluator_id,grid_axis=plan.get('grid_axis','row'))
        save('target_constructed')
        from src.compact_state import parse,serialize,CompactState
        from src.compact_service import CompactIdentityService,model_digest
        prior=None
        if plan.get('prior_state'):
            priorpath=Path(plan['prior_state']['path'])
            if priorpath.stat().st_size>512*2**20:raise ValueError('prior file exceeds the worker file cap')
            priorraw=priorpath.read_bytes()
            prior=parse(priorraw,expected_sha256=plan['prior_state']['sha256'])
            save('prior_state_loaded',bytes=len(priorraw));del priorraw
        service=CompactIdentityService(decoder,target,solver_backend=plan.get('solver_backend','reference'),progress=lambda row:save('stage_complete',stage_metrics=row))
        arguments=dict(method=plan['method'])
        if prior is not None:
            arguments.update(prior=prior,deleted_ids=sorted(set(prior.record_ids)-set(r['id'] for r in records)))
        outcome=service.run(records,**arguments)
        result['diagnostics']=outcome.diagnostics
        result['model_sha256']=model_digest(outcome.stages)
        modelraw=serialize(CompactState(target.digest,outcome.stages,()))
        atomic_write(output/'model.bin',modelraw)
        result['model_artifact']=dict(bytes=len(modelraw),sha256=digest(modelraw),file='model.bin')
        del modelraw
        if outcome.state is not None:
            stateraw=serialize(outcome.state)
            checked=parse(stateraw,expected_sha256=digest(stateraw))
            if serialize(checked)!=stateraw:raise ArithmeticError('state canonical roundtrip changed bytes')
            atomic_write(output/'state.bin',stateraw)
            result['state_artifact']=dict(bytes=len(stateraw),sha256=digest(stateraw),file='state.bin')
            result['committed_record_ids']=list(checked.record_ids)
            del stateraw,checked
        result.update(status='complete',complete_model=True,complete_state=outcome.state is not None)
        save('complete')
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise


if __name__=='__main__':main()
