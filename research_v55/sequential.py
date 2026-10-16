"""Bounded sequential calibration with the unchanged V43 stage dispatcher.

Each stream receives the previous certified calibrated matrix. Fixed-anchor
features and archived state are never inputs. The numerical counterfactual is
the original sequential target; this is a quality comparator, not repair timing.
"""
import time
import numpy as np
from research_v43 import dispatcher as dispatch
from research_v43.campaign import require
from src.compact_service import _records
from src.compact_state import StageCodes
from src.ordered_finite import FiniteWeights
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder, ordered_sequential_features
from src.run_store import canonical_json,digest
from scripts.execute_gram_pilot_v35 import public_result


def calibrate(decoder,target,records,*,policy=dispatch.ResourcePolicy(),progress=None):
    start=time.perf_counter_ns()
    require(type(decoder) is OrderedFiniteDecoder,'Explicit ordered sequential decoder required')
    require(progress is None or callable(progress),'Progress must be callable')
    stages=tuple(target.stages)
    require(tuple(s.stage_id for s in stages)==tuple(decoder.stage_ids),'Complete ordered stage target required')
    for index,stage in enumerate(stages):
        require(len(stage.dependencies)==index and set(stage.dependencies)==set(decoder.stage_ids[:index])
            and stage.bits==4,'Complete sequential dependency prefix and four-bit grids required')
    rows=_records(decoder,records)
    require(bool(rows),'Nonempty retained sequential record set required')
    tokens=sum(len(ids) for _,ids in rows);block_tokens=max(len(ids) for _,ids in rows)
    specs=[];admission=[]
    for stage in stages:
        spec=dispatch.StageSpec.from_stage(stage,target_sha256=target.digest)
        report=dispatch.assess_stage(spec,tokens,kind='point',block_tokens=block_tokens,
            max_blocks=len(rows),policy=policy,resident_bytes=4*2**30)
        require(report['admitted'],'Sequential stage resource admission refused: '+stage.stage_id)
        specs.append(spec);admission.append(report)
    require(sum(r['work_units'] for r in admission)<=policy.max_request_work_units,
        'Sequential request work admission refused')
    metrics=dict(schema='dispatched-sequential-calibration-v55',target_sha256=target.digest,
        implementation='ordered-finite-decoder-v30',
        implementation_manifest_sha256=digest(canonical_json(decoder.implementation_manifest)),
        feature_rule='each stage uses all preceding certified calibrated outputs',
        records=len(rows),retained_tokens=tokens,neural_stage_record_pairs=0,
        prior_model_access=False,prior_factor_access=False,point_admission=admission,
        admission_elapsed_ns=time.perf_counter_ns()-start,stages=[])
    streams={};outputs=[];previous=None
    try:
        for index,(stage,spec) in enumerate(zip(stages,specs)):
            tick=time.perf_counter_ns();blocks=[]
            for rid,ids in rows:
                if index==0:
                    streams[rid]=ordered_sequential_features(decoder,ids)
                    sid,values=next(streams[rid])
                else:sid,values=streams[rid].send(previous)
                require(sid==stage.stage_id,'Sequential feature stream stage differs')
                point=np.ascontiguousarray(np.asarray(values,dtype=np.float64).T)
                require(point.shape==(stage.width,len(ids)) and np.isfinite(point).all(),
                    'Sequential feature shape or words invalid')
                blocks.append((point,point));metrics['neural_stage_record_pairs']+=1
            feature_ns=time.perf_counter_ns()-tick
            weights=FiniteWeights(stage.weights).array();solve_tick=time.perf_counter_ns()
            solved=dispatch.solve_blocks(spec,weights,blocks,total_tokens=tokens,kind='point',
                block_tokens=block_tokens,max_blocks=len(rows),policy=policy,resident_bytes=4*2**30)
            solve_ns=time.perf_counter_ns()-solve_tick
            code=StageCodes.from_array(stage.stage_id,solved.codes,grid_axis='dyadic_row',
                bits=stage.bits,scale_values=stage.scale_values)
            outputs.append(code);previous=solved.codes
            row=dict(stage_id=stage.stage_id,feature_tokens=tokens,input_width=stage.width,
                output_rows=spec.rows,route=solved.route,
                installed_parent_stage_id=stages[index-1].stage_id if index else None,
                installed_parent_packed_sha256=digest(outputs[index-1].packed_indices) if index else None,
                feature_elapsed_ns=feature_ns,solver_elapsed_ns=solve_ns,
                elapsed_ns=time.perf_counter_ns()-tick,solver_diagnostics=public_result(solved.solver_result))
            metrics['stages'].append(row)
            if progress is not None:progress(row)
            del blocks,weights,solved,point,values
        metrics['service_elapsed_ns']=time.perf_counter_ns()-start
        return tuple(outputs),metrics
    except Exception as error:
        metrics.update(aborted=True,completed_stages=len(outputs),service_elapsed_ns=time.perf_counter_ns()-start)
        error.service_diagnostics=metrics;error.diagnostics=metrics
        raise
    finally:
        for stream in streams.values():stream.close()
