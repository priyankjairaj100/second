"""Registered sequential-calibration quality comparator with bounded solving.

Features use each preceding calibrated output. They never use fixed anchor
matrices. This is a different target from fixed-feature repair, so its time
must not become a matched repair speed baseline.
"""
import argparse
from dataclasses import asdict,fields
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_adaptive_service_v30 import (
    CAPS,_safe_path,require,select_records,validate_inputs,validate_policy,preflight_stages,
)
from src.experiment_inventory import source_hashes
from src.run_store import atomic_write,canonical_json,digest,strict_json
from src.transaction_timing import verify_command_admission

SCHEMA = 'sequential-quality-comparison-v30'


def validate_comparison_plan(plan):
    """Require model-only access. expected_target denotes the sequential target."""
    budget = validate_policy(plan)
    require(plan['method'] == 'model_only_fresh','sequential quality comparison requires model_only_fresh')
    require(plan.get('expected_state_sha256') is None,'sequential quality comparison has no state output')
    return budget


def calibrate_sequential(decoder,target,records,*,budget,route,max_point_work_units,progress=None):
    """Calibrate complete sequential prefixes using the shared bounded solver.

    This helper supports small software fixtures. The research CLI separately
    requires twenty-four stages. No prior model or source factor is accepted.
    """
    import numpy as np
    from src.adaptive_calibration_v30 import quantize_adaptive_dyadic_rows
    from src.compact_service import _records
    from src.compact_state import StageCodes
    from src.ordered_finite import FiniteWeights
    from src.sequential_finite import sequential_features
    started = time.perf_counter_ns()
    require(progress is None or callable(progress),'progress must be callable')
    stages = tuple(target.stages)
    require(tuple(stage.stage_id for stage in stages) == tuple(decoder.stage_ids),
            'sequential target must contain every decoder stage in order')
    for i,stage in enumerate(stages):
        require(len(stage.dependencies) == i and set(stage.dependencies) == set(decoder.stage_ids[:i]),
                'sequential target must declare the complete calibrated prefix')
        require(stage.bits == 4,'adaptive sequential comparison requires four-bit grids')
    rows = _records(decoder,records)
    tokens = sum(len(token_ids) for _,token_ids in rows)
    admission = preflight_stages(stages,tokens,budget=budget,route=route,
                                max_point_work_units=max_point_work_units)
    metrics = dict(schema='bounded-sequential-calibration-v30',target_sha256=target.digest,
        feature_rule='each stage uses all preceding calibrated outputs',
        records=len(rows),retained_tokens=tokens,neural_stage_record_pairs=0,
        prior_model_access=False,prior_factor_access=False,point_admission=admission,
        admission_elapsed_ns=time.perf_counter_ns()-started,feature_elapsed_ns=0,
        weights_elapsed_ns=0,solver_elapsed_ns=0,code_pack_elapsed_ns=0,stages=[],
        timing_scope='in-memory calibration including preflight, features, solving, packing, and callbacks')
    streams,outputs = {},[]
    previous = None
    try:
        for i,stage in enumerate(stages):
            stage_start = time.perf_counter_ns()
            tick = time.perf_counter_ns()
            blocks = []
            for rid,token_ids in rows:
                if i == 0:
                    streams[rid] = sequential_features(decoder,token_ids)
                    stage_id,values = next(streams[rid])
                else:
                    stage_id,values = streams[rid].send(previous)
                require(stage_id == stage.stage_id,'streamed sequential stage order differs')
                block = np.asarray(values,dtype=np.float64)
                require(block.shape == (len(token_ids),stage.width),'streamed feature dimensions differ')
                blocks.append(block)
                metrics['neural_stage_record_pairs'] += 1
            features = (np.concatenate(blocks,axis=0).T.copy() if blocks else
                        np.empty((stage.width,0),dtype=np.float64))
            feature_ns = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            weights = FiniteWeights(stage.weights).array()
            weights_ns = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            solved = quantize_adaptive_dyadic_rows(weights,features,stage.scale_values,
                bits=stage.bits,significant_bits=24,ridge=stage.ridge,normalization=stage.normalization,
                route=route,budget=budget,candidate=None)
            solver_ns = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            codes = StageCodes.from_array(stage.stage_id,solved.codes,grid_axis='dyadic_row',
                bits=stage.bits,scale_values=stage.scale_values)
            pack_ns = time.perf_counter_ns()-tick
            outputs.append(codes)
            # The same certified matrix reaches every retained stream.
            previous = solved.codes
            diagnostic = dict(stage_id=stage.stage_id,feature_tokens=tokens,
                input_width=stage.width,output_rows=len(stage.weights),
                installed_parent_stage_id=stages[i-1].stage_id if i else None,
                installed_parent_packed_sha256=digest(outputs[i-1].packed_indices) if i else None,
                feature_elapsed_ns=feature_ns,weights_elapsed_ns=weights_ns,
                solver_elapsed_ns=solver_ns,code_pack_elapsed_ns=pack_ns,
                elapsed_ns=time.perf_counter_ns()-stage_start,
                solver_diagnostics={field.name:getattr(solved,field.name) for field in fields(solved)
                                    if field.name != 'codes'})
            metrics['stages'].append(diagnostic)
            for name in ('feature_elapsed_ns','weights_elapsed_ns','solver_elapsed_ns','code_pack_elapsed_ns'):
                metrics[name] += diagnostic[name]
            if progress is not None:
                progress(diagnostic)
        metrics['service_elapsed_ns'] = time.perf_counter_ns()-started
        return tuple(outputs),metrics
    except Exception as exc:
        metrics.update(aborted=True,completed_stages=len(outputs),service_elapsed_ns=time.perf_counter_ns()-started)
        exc.service_diagnostics = metrics
        exc.diagnostics = metrics
        raise
    finally:
        for stream in streams.values():
            stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path)
    args = parser.parse_args()
    started = time.perf_counter_ns()
    raw = args.plan.read_bytes()
    plan = strict_json(raw)
    require(type(plan) is dict,'comparison plan must be an object')
    require(source_hashes(ROOT) == plan.get('source_sha256'),'source binding mismatch')
    verify_command_admission(plan['protocol_sha256'],plan.get('phase','feasibility'),
        [sys.executable,str(Path(__file__).resolve()),str(args.plan.absolute())])
    output = _safe_path(plan['output'])
    require(not output.exists() or output.is_dir() and not any(output.iterdir()),
            'cannot overwrite an existing comparison output')
    output.mkdir(parents=True,exist_ok=True)
    result = dict(schema=SCHEMA,status='running',method='model_only_fresh',phases=[],
        comparison_role='sequential_quality',repair_speed_comparator=False,
        numerical_target='sequential calibrated ancestor features; not fixed anchor calibration',
        plan_sha256=digest(raw),source_sha256=plan['source_sha256'],confirmation=False,
        scientific_promotion=False,use_candidates=False,complete_state=False,
        worker_clock_scope='plan read through complete model verification; terminal commits and exit excluded',
        primary_latency='outer controller transaction; this different-target comparator does not establish repair speed',
        exactness_scope='certified sequential mathematical target; not equality to the fixed-feature target',
        cross_target_model_equality_claimed=False)

    def save(phase,**details):
        result['phases'].append(dict(phase=phase,elapsed_ns=time.perf_counter_ns()-started,**details))
        result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json',canonical_json(result))
        print(json.dumps(result['phases'][-1],allow_nan=False),flush=True)

    def read(name):
        entry = plan['inputs'][name]
        path = _safe_path(entry['path'])
        require(path.stat().st_size <= CAPS[name],'input exceeds read cap: '+name)
        value = path.read_bytes()
        require(digest(value) == entry['sha256'],'input changed during loading: '+name)
        return value

    try:
        save('input_validation_started')
        budget = validate_comparison_plan(plan)
        validate_inputs(plan)
        original,records = select_records(plan,strict_json(read('records')))
        checkpoint = _safe_path(plan['checkpoint']).resolve()
        require(Path(plan['inputs']['config']['path']).resolve() == checkpoint/'config.json'
            and Path(plan['inputs']['weights']['path']).resolve() == checkpoint/'model.safetensors',
            'checkpoint path differs from bound inputs')
        checkpoint_hashes = {name:plan['inputs'][key]['sha256'] for name,key in (
            ('config.json','config'),('model.safetensors','weights'))}
        result.update(solver_backend=plan['solver_backend'],solver_budget=asdict(budget),
            max_point_work_units=plan['max_point_work_units'],original_token_count=plan['original_token_count'],
            original_record_ids=[row['id'] for row in original],retained_record_ids=[row['id'] for row in records],
            deleted_record_ids=list(plan['deleted_ids']),original_record_lengths=[len(row['tokens']) for row in original],
            retained_record_lengths=[len(row['tokens']) for row in records],
            retained_token_count=sum(len(row['tokens']) for row in records),
            original_records_sha256=digest(canonical_json({'records':list(original)})),
            records_input_sha256=plan['inputs']['records']['sha256'],checkpoint_files_sha256=checkpoint_hashes,
            max_neural_stage_record_pairs=24*len(records),inputs=plan['inputs'],
            runtime=dict(python=sys.version,executable=sys.executable,affinity_cpus=sorted(os.sched_getaffinity(0)),
                thread_environment={name:os.environ.get(name) for name in (
                    'OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}))
        atomic_write(output/'plan.json',raw)
        save('inputs_verified')
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        from src.dyadic_row_target import build_dyadic_row_target
        from src.fixed_anchor_target import build_fixed_anchor_target
        from src.compact_state import CompactState,serialize as encode_model,parse as decode_model
        from src.compact_service import model_digest
        save('checkpoint_load_started')
        loaded = load_gpt2_checkpoint(checkpoint,identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256'] == checkpoint_hashes,'checkpoint provenance differs')
        decoder = CertifiedDecoder(loaded.decoder,primitive_backend='mpfr_enclosure')
        require(len(decoder.stage_ids) == 24,'registered sequential worker requires twenty-four decoder stages')
        for row in original:
            decoder.base._tokens(row['tokens'])
        target = build_dyadic_row_target(decoder,TargetRecipe(original_token_count=plan['original_token_count'],group_count=1))
        fixed_target = build_fixed_anchor_target(decoder,target)
        require(fixed_target.digest != target.digest,'fixed and sequential target identities collide')
        if plan.get('expected_target') is not None:
            require(target.digest == plan['expected_target'],'registered sequential target differs')
        for name,payload in (('sequential-target',target.payload()),('fixed-target-reference',fixed_target.payload()),
                             ('evaluator',decoder.kernel_manifest)):
            atomic_write(output/(name+'.json'),canonical_json(payload))
        result.update(sequential_target_sha256=target.digest,base_target_sha256=target.digest,
            fixed_target_sha256=fixed_target.digest,evaluator_id=decoder.evaluator_id,target_recipe=target.recipe.payload())
        save('targets_loaded')
        save('point_route_preflight_started')
        result['resource_admission'] = preflight_stages(target.stages,result['retained_token_count'],
            budget=budget,route=plan['solver_backend'],max_point_work_units=plan['max_point_work_units'])
        save('point_route_preflight_complete')
        save('service_started')
        stages,diagnostics = calibrate_sequential(decoder,target,records,budget=budget,
            route=plan['solver_backend'],max_point_work_units=plan['max_point_work_units'],
            progress=lambda row:save('stage_complete',stage_metrics=row))
        result.update(diagnostics=diagnostics,stage_count=len(stages),stage_ids=[stage.stage_id for stage in stages],
            model_sha256=model_digest(stages),model_code_elements=sum(stage.rows*stage.columns for stage in stages),
            model_packed_code_bytes=sum(len(stage.packed_indices) for stage in stages))
        require(result['stage_count'] == 24 and result['stage_ids'] == list(decoder.stage_ids),
                'sequential model is incomplete')
        require(diagnostics['neural_stage_record_pairs'] == 24*len(records),'sequential traversal count differs')
        save('service_complete')
        save('model_write_started')
        model_raw = encode_model(CompactState(target.digest,stages,()))
        model_hash = digest(model_raw)
        checked = decode_model(model_raw,expected_sha256=model_hash)
        require(checked.target_sha256 == target.digest and checked.stages == stages and not checked.factors
            and encode_model(checked) == model_raw,'sequential model canonical roundtrip differs')
        if plan.get('expected_model_sha256') is not None:
            require(model_hash == plan['expected_model_sha256'],'registered sequential model hash differs')
        atomic_write(output/'model.bin',model_raw)
        require(digest((output/'model.bin').read_bytes()) == model_hash,'written sequential model differs')
        result.update(model_artifact=dict(file='model.bin',bytes=len(model_raw),sha256=model_hash),
            model_roundtrip_exact=True,complete_model=True)
        save('model_write_complete',bytes=len(model_raw),sha256=model_hash)
        require(source_hashes(ROOT) == plan['source_sha256'],'source changed during comparison transaction')
        result.update(status='complete',worker_transaction_elapsed_ns=time.perf_counter_ns()-started)
        save('complete')
        terminal = canonical_json(result)
        with (output/'completion.json').open('xb') as stream:
            stream.write(terminal)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(output,os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        print(json.dumps(dict(phase='terminal_record_committed',sha256=digest(terminal))),flush=True)
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc))
        for attribute,field in (('diagnostics','failure_diagnostics'),
                ('service_diagnostics','failure_service_diagnostics'),('admission','failure_admission')):
            if hasattr(exc,attribute):
                result[field] = getattr(exc,attribute)
        save('failed')
        raise


if __name__ == '__main__':
    main()
