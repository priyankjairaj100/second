"""Registered real-data bound screen; rejection blocks timing expansion."""
import argparse,hashlib,json,resource,sys,time
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
    result=dict(schema='anchor-screen-v20',plan_sha256=digest(raw),status='running',phases=[],
        confirmation=False,scientific_promotion=False,complete_model_repair=False,
        cells=[dict(name=n,status='unstarted') for n in ('anchor_preparation','unchanged_first_factor','changed_factor_bound','sixteen_row_certificate','full_stage_certificate','endpoint_witness')])
    def save(phase,**details):
        result['phases'].append(dict(phase=phase,elapsed_ns=time.perf_counter_ns()-start,**details))
        result['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json',canonical_json(result));print(json.dumps(result['phases'][-1]),flush=True)
    def reject(index,exc):
        result['cells'][index].update(status='rejected',error_type=type(exc).__name__,error=str(exc))
        result.update(status='rejected_pending_witness',feasibility_pass=False)
        save('screen_rejected',cell=result['cells'][index]['name'])
    try:
        save('validate_inputs')
        for name,entry in plan['inputs'].items():
            with Path(entry['path']).open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
            if actual!=entry['sha256']:raise ValueError('input changed: '+name)
        import numpy as np
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        from src.dyadic_row_target import build_dyadic_row_target
        from src.compact_state import parse
        from src.ordered_finite import FiniteWeights
        from src.anchor_transformer import prepare_anchor,prepare_context,bound_stage,encode_anchor,decode_anchor,AnchorBoundUnresolved
        from src.dyadic_box_certificate import certify_dyadic_box
        from src.token_box_certificate import TokenBoxUnresolved
        loaded=load_gpt2_checkpoint(plan['checkpoint'],identity_encoding='binary64_tree_v2')
        decoder=CertifiedDecoder(loaded.decoder,primitive_backend='mpfr_enclosure')
        target=build_dyadic_row_target(decoder,TargetRecipe(original_token_count=32,group_count=1))
        expected=json.loads(Path(plan['inputs']['retained_progress']['path']).read_bytes())
        old_plan_raw=Path(plan['inputs']['retained_plan']['path']).read_bytes()
        old_receipt=json.loads(Path(plan['inputs']['retained_receipt']['path']).read_bytes())
        if (expected['status']!='complete' or old_receipt['outcome']['status']!='complete'
            or old_receipt['budget_debit']['state']!='settled'
            or old_receipt['worker_identity']['plan_sha256']!=digest(old_plan_raw)
            or expected['plan_sha256']!=digest(old_plan_raw)):
            raise ValueError('archived oracle has incomplete provenance')
        state=parse(Path(plan['inputs']['retained_state']['path']).read_bytes(),expected_sha256=expected['state_artifact']['sha256'])
        rebound=plan['program']['scope'].endswith('_current_runtime')
        if not rebound and state.target_sha256!=target.digest:raise ValueError('target differs from archived oracle')
        result['archived_target_sha256']=state.target_sha256
        atomic_write(output/'target.json',canonical_json(target.payload()))
        atomic_write(output/'evaluator.json',canonical_json(decoder.kernel_manifest))
        records=json.loads(Path(plan['inputs']['records']['path']).read_bytes())['records']
        record=next(r for r in records if r['id']==plan['program']['record_id'])
        record={'id':record['id'],'tokens':record['tokens']}
        if set(state.record_ids)!={record['id']}:raise ValueError('oracle membership differs')
        result.update(target_sha256=target.digest,record_id=record['id'],tokens=len(record['tokens']))
        save('target_loaded')
        first=target.stages[0];stage=target.stages[1]
        factors={(f.record_id,f.stage_id):f for f in state.factors}
        if rebound:
            from src.sequential_finite import sequential_features
            from src.native_ball_quantizer import native_quantize_dyadic_rows
            from src.compact_state import StageCodes
            tick=time.perf_counter_ns();save('current_oracle_started')
            stream=sequential_features(decoder,record['tokens'])
            sid,first_values=next(stream);first_values=np.asarray(first_values,dtype=np.float64)
            if sid!=first.stage_id:raise ArithmeticError('fresh first stage differs')
            first_codes=native_quantize_dyadic_rows(FiniteWeights(first.weights).array(),first_values.T.copy(),
                first.scale_values,bits=first.bits,ridge=first.ridge,normalization=first.normalization,
                max_exact_rank=64,max_exact_coordinates=16,max_refinement_coordinates=64).codes
            installed_first=StageCodes.from_array(first.stage_id,first_codes,grid_axis='dyadic_row',bits=first.bits,scale_values=first.scale_values)
            sid,changed_values=stream.send(first_codes);stream.close()
            changed_values=np.asarray(changed_values,dtype=np.float64)
            if sid!=stage.stage_id:raise ArithmeticError('fresh second stage differs')
            oracle=native_quantize_dyadic_rows(FiniteWeights(stage.weights).array(),changed_values.T.copy(),
                stage.scale_values,bits=stage.bits,ridge=stage.ridge,normalization=stage.normalization,
                max_exact_rank=64,max_exact_coordinates=16,max_refinement_coordinates=64).codes
            result['current_oracle']=dict(elapsed_ns=time.perf_counter_ns()-tick,
                first_codes_sha256=digest(first_codes.astype('<f8').tobytes()),second_codes_sha256=digest(oracle.astype('<f8').tobytes()),
                first_codes_equal_archived=bool(np.array_equal(first_codes,state.stages[0].array())),
                second_codes_equal_archived=bool(np.array_equal(oracle,state.stages[1].array())),
                changed_factors_equal_archived=bool(np.array_equal(changed_values,factors[(record['id'],stage.stage_id)].array())))
            save('current_oracle_complete')
        else:
            first_values=factors[(record['id'],first.stage_id)].array()
            changed_values=factors[(record['id'],stage.stage_id)].array()
            installed_first=state.stages[0];oracle=state.stages[1].array()
        tick=time.perf_counter_ns();result['cells'][0]['status']='running';save('preparation_started')
        context=prepare_context(decoder,target)
        result['anchor_context_values']=context.initial_matrix_values
        anchor=prepare_anchor(decoder,target,record,context=context)
        encoded=encode_anchor(anchor)
        if encode_anchor(decode_anchor(encoded))!=encoded:raise ArithmeticError('anchor canonical roundtrip differs')
        atomic_write(output/'anchor.bin',encoded)
        result['cells'][0].update(status='complete',elapsed_ns=time.perf_counter_ns()-tick,bytes=len(encoded),sha256=digest(encoded))
        save('anchor_prepared')
        factors={(f.record_id,f.stage_id):f for f in state.factors}
        first=target.stages[0];box=bound_stage(decoder,target,anchor,(),first.stage_id,context=context)
        truth=first_values
        if not box.singleton or not np.array_equal(box.lower,truth):raise ArithmeticError('unchanged first factor differs')
        result['cells'][1].update(status='complete',equal=True);save('first_factor_verified')
        def endpoint_witness():
            from src.anchor_transformer import anchor_factor
            from src.native_ball_quantizer import native_quantize_dyadic_rows
            stage=target.stages[1];tick=time.perf_counter_ns()
            result['cells'][5]['status']='running';save('endpoint_witness_started')
            weights=FiniteWeights(stage.weights).array()[:16]
            features=anchor_factor(anchor,stage.stage_id).T.copy()
            point=native_quantize_dyadic_rows(weights,features,tuple(stage.scale_values[:16]),
                bits=stage.bits,ridge=stage.ridge,normalization=stage.normalization,
                max_exact_rank=64,max_exact_coordinates=16,max_refinement_coordinates=64)
            actual=oracle[:16]
            differences=np.argwhere(point.codes!=actual)
            proof=None
            if len(differences):
                r,c=map(int,differences[0]);proof=dict(row=r,coordinate=c,
                    anchor_factor_code_hex=float(point.codes[r,c]).hex(),
                    retained_factor_code_hex=float(actual[r,c]).hex())
            result['cells'][5].update(status='complete',elapsed_ns=time.perf_counter_ns()-tick,
                compared_values=int(actual.size),changed_codes=int(len(differences)),witness=proof,
                anchor_codes_sha256=digest(point.codes.astype('<f8').tobytes()),actual_codes_sha256=digest(actual.astype('<f8').tobytes()),
                anchor_containing_constant_box_impossible=bool(len(differences)))
            result['status']='complete'
            save('endpoint_witness_complete')
        stage=target.stages[1]
        if stage.stage_id!='block.0000.attn_out':raise ValueError('screen stage changed')
        prefix=(installed_first,)
        tick=time.perf_counter_ns();result['cells'][2]['status']='running';save('changed_bound_started')
        bound_work={}
        try:box=bound_stage(decoder,target,anchor,prefix,stage.stage_id,context=context,diagnostics=bound_work)
        except AnchorBoundUnresolved as exc:
            result['cells'][2].update(elapsed_ns=time.perf_counter_ns()-tick,bound_work=bound_work)
            reject(2,exc);endpoint_witness();return
        truth=changed_values
        if not box.contains(truth):raise ArithmeticError('proved feature box excludes exact archived factors')
        result['cells'][2].update(status='complete',contains_exact=True,elapsed_ns=time.perf_counter_ns()-tick,
            bound_work=bound_work,max_box_width_hex=float(np.max(box.upper-box.lower)).hex(),uncertain_values=int(np.count_nonzero(box.lower!=box.upper)))
        save('changed_bound_verified')
        weights=FiniteWeights(stage.weights).array()
        for index,count in ((3,16),(4,weights.shape[0])):
            result['cells'][index]['status']='running';tick=time.perf_counter_ns();save('certificate_started',rows=count)
            try:
                certificate=certify_dyadic_box(weights[:count],box.lower.T.copy(),box.upper.T.copy(),
                    tuple(stage.scale_values[:count]),bits=stage.bits,ridge=stage.ridge,normalization=stage.normalization,
                    max_exact_rank=64,max_exact_coordinates=16,max_refinement_coordinates=16)
            except TokenBoxUnresolved as exc:reject(index,exc);endpoint_witness();return
            if not np.array_equal(certificate.codes,oracle[:count]):raise ArithmeticError('certificate differs from exact reference')
            result['cells'][index].update(status='complete',equal=True,elapsed_ns=time.perf_counter_ns()-tick)
            save('certificate_verified',rows=count)
        result['cells'][5].update(status='not_required',reason='all screen cells passed')
        result.update(status='complete',feasibility_pass=True);save('screen_complete')
    except Exception as exc:
        result.update(status='failed',feasibility_pass=False,error_type=type(exc).__name__,error=str(exc));save('failed');raise

if __name__=='__main__':main()
