"""One explicit changed-target model and paired new-article quality screen."""
import argparse,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import atomic_write,canonical_json,digest
from src.experiment_inventory import source_hashes
from src.transaction_timing import verify_command_admission


def main():
    parser=argparse.ArgumentParser();parser.add_argument('plan',type=Path);args=parser.parse_args()
    raw=args.plan.read_bytes();plan=json.loads(raw);root=Path(__file__).resolve().parents[1]
    if source_hashes(root)!=plan['source_sha256']:raise ValueError('source changed')
    verify_command_admission(plan['protocol_sha256'],'feasibility',[sys.executable,str(Path(__file__).resolve()),str(args.plan.absolute())])
    output=Path(plan['output']);output.mkdir(parents=True,exist_ok=True);start=time.perf_counter_ns()
    result=dict(schema='fixed-anchor-quality-v21',status='running',plan_sha256=digest(raw),phases=[],quality={},
        confirmation=False,scientific_promotion=False,repair_timing=False,target_changed=True,
        nll_is_not_certified_interval=True)
    def save(phase,**details):
        result['phases'].append(dict(phase=phase,elapsed_ns=time.perf_counter_ns()-start,**details))
        result['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json',canonical_json(result));print(json.dumps(result['phases'][-1]),flush=True)
    def read(name):return Path(plan['inputs'][name]['path']).read_bytes()
    def generation(prefix):
        progress=json.loads(read(prefix+'_progress'));receipt=json.loads(read(prefix+'_receipt'));ph=digest(read(prefix+'_plan'))
        if (progress['status']!='complete' or receipt['outcome']['status']!='complete'
            or receipt['budget_debit']['state']!='settled' or progress['plan_sha256']!=ph
            or receipt['worker_identity']['plan_sha256']!=ph):raise ValueError('generation provenance differs')
        return progress
    try:
        save('validate_inputs')
        for name,entry in plan['inputs'].items():
            with Path(entry['path']).open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
            if actual!=entry['sha256']:raise ValueError('input changed: '+name)
        anchor_progress=generation('anchor');old_progress=generation('sequential')
        anchor_cell=anchor_progress['cells'][0]
        if anchor_cell['status']!='complete' or digest(read('anchor'))!=anchor_cell['sha256']:raise ValueError('anchor artifact binding differs')
        if digest(read('sequential_model'))!=old_progress['model_artifact']['sha256']:raise ValueError('sequential model binding differs')
        evaluation=json.loads(read('evaluation'));old_evaluation=json.loads(read('previous_evaluation'))
        records=json.loads(read('records'))['records'];calibration=next(r for r in records if r['id']==plan['program']['record_id'])
        calibration=dict(id=calibration['id'],tokens=calibration['tokens'])
        excluded=set(old_evaluation['excluded_from_future_confirmation_ids'])
        ids=[r['id'] for r in evaluation['records']]
        if len(ids)!=2 or len(set(ids))!=2 or set(ids)&excluded or any(len(r['tokens'])!=16 for r in evaluation['records']):raise ValueError('evaluation membership or length differs')
        if set(evaluation['prior_exclusions'])!=excluded:raise ValueError('exclusion chain differs')
        result['excluded_from_future_confirmation_ids']=evaluation['excluded_from_future_confirmation_ids']
        import numpy as np
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        from src.dyadic_row_target import build_dyadic_row_target
        from src.anchor_transformer import decode_anchor
        from src.fixed_anchor_service import FixedAnchorService,serialize as serialize_fixed,parse as parse_fixed
        from src.compact_state import CompactState,serialize as serialize_model,parse as parse_model
        from src.compact_service import model_digest
        from src.compact_exact import CompactDyadicVector
        from src.prepared_finite import PreparedFinitePrefix
        loaded=load_gpt2_checkpoint(plan['checkpoint'],identity_encoding='binary64_tree_v2')
        decoder=CertifiedDecoder(loaded.decoder,primitive_backend='mpfr_enclosure')
        base=build_dyadic_row_target(decoder,TargetRecipe(original_token_count=32,group_count=1))
        anchor=decode_anchor(read('anchor'))
        if anchor.target_sha256!=base.digest or anchor.record_id!=calibration['id'] or anchor.tokens!=tuple(calibration['tokens']):raise ValueError('anchor target or record differs')
        service=FixedAnchorService(decoder,base,progress=lambda d:save('stage_complete',stage_metrics=d))
        if service.target.digest==base.digest:raise ArithmeticError('different feature rules share a target identity')
        atomic_write(output/'fixed-target.json',canonical_json(service.target.payload()))
        atomic_write(output/'base-target.json',canonical_json(base.payload()))
        atomic_write(output/'evaluator.json',canonical_json(decoder.kernel_manifest))
        save('targets_loaded')
        outcome=service.run_prepared([calibration],(anchor,),preparation_receipt=dict(source='v20/attempt-002 anchor preparation',artifact_sha256=anchor_cell['sha256'],elapsed_ns=anchor_cell['elapsed_ns']))
        result.update(diagnostics=outcome.diagnostics,fixed_target_sha256=service.target.digest,base_target_sha256=base.digest,
            archived_sequential_target_sha256=old_progress['target_sha256'],model_sha256=model_digest(outcome.stages),
            external_preparation_receipt_verified_by_worker=True)
        modelraw=serialize_model(CompactState(service.target.digest,outcome.stages,()))
        atomic_write(output/'model.bin',modelraw)
        result['model_artifact']=dict(file='model.bin',bytes=len(modelraw),sha256=digest(modelraw));del modelraw
        stateraw=serialize_fixed(outcome.state)
        if serialize_fixed(parse_fixed(stateraw,expected_sha256=digest(stateraw)))!=stateraw:raise ArithmeticError('fixed state roundtrip differs')
        atomic_write(output/'state.bin',stateraw)
        result['state_artifact']=dict(file='state.bin',bytes=len(stateraw),sha256=digest(stateraw));del stateraw
        result['complete_new_target_model']=True;result['complete_new_target_state']=True
        save('model_constructed')
        sequential=parse_model(read('sequential_model'),expected_sha256=old_progress['model_artifact']['sha256'])
        if len(sequential.stages)!=len(base.stages) or sequential.factors:raise ValueError('sequential comparator model is incomplete')
        for code,stage in zip(sequential.stages,base.stages):
            if code.stage_id!=stage.stage_id or code.scale_values!=stage.scale_values or code.shape!=(len(stage.weights),stage.width):raise ValueError('sequential comparator grids differ')
        def prefix(stages):
            values={}
            for code in stages:
                matrix=code.array();values[code.stage_id]=CompactDyadicVector.from_bytes(matrix.astype('<f8').tobytes(),'F64').matrix(*matrix.shape)
            return values
        models={'fixed_anchor_calibrated':outcome.stages,'archived_sequential_calibrated':sequential.stages}
        evaluators={label:PreparedFinitePrefix(decoder,prefix(stages)) for label,stages in models.items()}
        for i,record in enumerate(evaluation['records']):
            for label in plan['program']['quality_order'][i]:
                tick=time.perf_counter_ns();save('quality_record_started',model=label,record_id=record['id'])
                logits=evaluators[label].logits(record['tokens']);nll=0.
                for j,row in enumerate(logits[:-1]):
                    maximum=max(row);nll+=maximum+math.log(sum(math.exp(x-maximum) for x in row))-row[record['tokens'][j+1]]
                if not math.isfinite(nll):raise ArithmeticError('nonfinite likelihood')
                result['quality'].setdefault(label,[]).append(dict(id=record['id'],predictions=len(logits)-1,nll_sum=nll,elapsed_ns=time.perf_counter_ns()-tick))
                del logits
                save('quality_record_complete',model=label,record_id=record['id'])
        fixed={r['id']:r for r in result['quality']['fixed_anchor_calibrated']};seq={r['id']:r for r in result['quality']['archived_sequential_calibrated']}
        if set(fixed)!=set(ids) or set(seq)!=set(ids) or any(r['predictions']!=15 for rows in result['quality'].values() for r in rows):raise ValueError('incomplete matched evaluation')
        ratios={rid:math.exp((fixed[rid]['nll_sum']-seq[rid]['nll_sum'])/15) for rid in ids}
        total=math.exp(sum(fixed[rid]['nll_sum']-seq[rid]['nll_sum'] for rid in ids)/30)
        gate=plan['program']['gate']
        result.update(status='complete',predictions_per_model=30,perplexity_ratio_to_sequential=total,per_article_ratios=ratios,
            quality_pilot_pass=total<=gate['max_aggregate_perplexity_ratio_to_sequential'] and max(ratios.values())<=gate['max_each_article_ratio'],
            observed_quality_win=total<1,scope='two new development articles only; no population or confirmation inference')
        save('complete')
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise

if __name__=='__main__':main()
