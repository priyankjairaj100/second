"""Fresh feature preparation and complete stage solves, never a full-model claim."""
from contextlib import nullcontext
import gc
import os
from pathlib import Path
import resource
import sys
import time
import traceback
import numpy as np
from research_v51.campaign import ROOT, ORDER, verify, completed, read, new, sha, require, snapshot
from research_v51.stage import STAGE_ID, HISTORICAL_CODE, prefix_factor, checked_feature
from research_v43 import dispatcher as dispatch
from research_v45.service import Service
from research_v50.neighbors import enabled
from src.ordered_fixed_service_v30 import prepare_ordered_leaf, ordered_preparer_binding
from src.ordered_finite import FiniteWeights
from src.compact_state import StageCodes
from src import fixed_lossless_codec_v29 as lossless, fixed_factor_codec_v26 as compressed
from src.run_store import canonical_json, digest
from src.transaction_timing import verify_command_admission
from scripts.execute_gram_pilot_v35 import public_result


def prepare(p, artifact, mark):
    service = Service(ROOT/'tmp/models/distilgpt2', 1664, p['record_provenance'], mark)
    stage = next(s for s in service.target.stages if s.stage_id == STAGE_ID)
    spec = dispatch.StageSpec.from_stage(stage, target_sha256=service.target.digest)
    require((spec.rows, spec.width, spec.normalization) == (768,3072,1664), 'Actual stage differs')
    admissions = {}
    for kind in ('point','box'):
        a = dispatch.assess_stage(spec,1664,kind=kind,block_tokens=128,max_blocks=13,resident_bytes=4*2**30)
        require(a['admitted'] and a['selected_route']=='streamed', 'Actual target not admitted')
        admissions[kind] = a
    old_provenance = read(p['inputs']['v45:prepare/outputs/execution-provenance.json']['path'])
    require(__import__('json').loads(service.provenance) == old_provenance, 'V45 target or execution binding differs')
    artifact('execution-provenance.json',service.provenance)
    artifact('base-target.json',canonical_json(service.base.payload()))
    artifact('fixed-target.json',canonical_json(service.target.payload()))
    weights = FiniteWeights(stage.weights).array()
    artifact('weights.f64',weights.astype('<f8').tobytes())
    entries = []; source_ns = 0; validation_ns = 0; encoding_ns = 0
    for index, row in enumerate(p['records']):
        tick = time.perf_counter_ns()
        block = prefix_factor(service.decoder,service.base,row,service.context)
        values = checked_feature(block.array(),3072,128)
        elapsed = time.perf_counter_ns()-tick; source_ns += elapsed
        checked_full = index == 0
        if checked_full:
            tick = time.perf_counter_ns()
            leaf = prepare_ordered_leaf(service.decoder,service.base,row,context=service.context)
            full = next(b for b in leaf.blocks if b.stage_id==STAGE_ID)
            require(full.binary64 == block.binary64, 'Real prefix does not match complete traversal')
            require(len(leaf.blocks)==24, 'Full validation traversal incomplete')
            del leaf,full
            validation_ns += time.perf_counter_ns()-tick
        tick = time.perf_counter_ns()
        names = {}
        for representation in ('lossless','compressed40'):
            blob = service.descriptor(stage,row,values,representation)
            name = f'{representation}-{index:02d}.bin'
            artifact(name,blob); names[representation]=name
        encoding_ns += time.perf_counter_ns()-tick
        entry = dict(record_id=row['id'], token_sha256=digest(canonical_json(row['tokens'])),
            features_sha256=digest(values.astype('<f8').tobytes()), descriptors=names,
            rows=128, columns=3072, prefix_stages=4, full_traversal_compared=checked_full)
        entries.append(entry)
        mark('source_prepared',record_id=row['id'],source_ns=elapsed,full_traversal_compared=checked_full)
    entry = next(e for e in service.base.payload()['stages'] if e['stage_id']==STAGE_ID)
    manifest = dict(schema='real-wide-stage-inputs-v51',stage_id=STAGE_ID,
        target_sha256=service.target.digest,anchor_target_sha256=service.base.digest,entry=entry,
        normalization=1664,total_tokens=1664,records=entries,
        ordered_preparer_sha256=ordered_preparer_binding(),prefix_wrapper_sha256=sha(ROOT/'research_v51/stage.py'))
    artifact('inputs.json',canonical_json(manifest))
    context_ns = service.load_ns
    del weights,service,block,values
    gc.collect()
    return dict(context_elapsed_ns=context_ns,
        source_prefix_elapsed_ns=source_ns,full_source_validation_elapsed_ns=validation_ns,
        encoding_elapsed_ns=encoding_ns,neural_stage_record_pairs=13*4+24,
        prefix_stage_record_pairs=13*4,validation_stage_record_pairs=24,admissions=admissions,
        full_source_validation_record=p['records'][0]['id'],manifest_sha256=digest(canonical_json(manifest)))


def solve(p, d, trial, artifact, mark):
    completion = completed(d,'prepare'); out = d/'prepare/outputs'
    manifest = read(out/'inputs.json')
    spec = dispatch.StageSpec.from_manifest(manifest['entry'],target_sha256=manifest['target_sha256'])
    weights = np.frombuffer((out/'weights.f64').read_bytes(),dtype='<f8').reshape(spec.rows,spec.width).copy()
    kind = 'box' if trial == 'compressed' else 'point'
    representation = 'compressed40' if kind == 'box' else 'lossless'
    def blocks():
        for item in manifest['records']:
            name = item['descriptors'][representation]; blob = (out/name).read_bytes()
            require(digest(blob)==completion['artifacts'][name]['sha256'],'Descriptor changed after admission')
            codec = compressed if kind=='box' else lossless
            desc = codec.parse(blob,expected_sha256=digest(blob))
            require(desc.source_sha256==item['features_sha256'] and desc.record_id==item['record_id'] and
                desc.stage_id==STAGE_ID and desc.target_sha256==manifest['target_sha256'] and
                desc.anchor_target_sha256==manifest['anchor_target_sha256'] and
                desc.token_sha256==item['token_sha256'],'Source descriptor binding differs')
            if kind=='box':
                box=desc.box(); yield np.ascontiguousarray(box.lower.T),np.ascontiguousarray(box.upper.T)
            else:
                point=checked_feature(desc.array(),3072,128).T.copy();yield point,point
    mark('solve_started',trial=trial,kind=kind,expected_codes=spec.rows*spec.width)
    tick=time.perf_counter_ns()
    with enabled() if trial!='reference' else nullcontext(None) as build:
        backend=dict(build) if build is not None else None
        answer=dispatch.solve_blocks(spec,weights,blocks(),total_tokens=1664,kind=kind,
            block_tokens=128,max_blocks=13,resident_bytes=4*2**30)
        code=StageCodes.from_array(STAGE_ID,answer.codes,grid_axis='dyadic_row',
            bits=spec.bits,scale_values=spec.scale_values)
        blob=code.packed_indices
        # A hash commitment from the incomplete V45 run is not its unavailable bytes.
        require(digest(blob)==HISTORICAL_CODE,'Complete stage differs from preserved V45 commitment')
        artifact('codes.bin',blob)
        diagnostics=public_result(answer.solver_result)
        result=dict(stage_id=STAGE_ID,kind=kind,route=answer.route,code_sha256=digest(blob),
            code_count=spec.rows*spec.width,shape=[spec.rows,spec.width],admission=answer.admission,
            diagnostics=diagnostics,backend=backend,historical_code_commitment_matches=True,
            historical_code_bytes_available=False,source_manifest_sha256=sha(out/'inputs.json'),
            no_neural_traversal=True,point_retry=False,solve_and_write_elapsed_ns=time.perf_counter_ns()-tick)
    mark('stage_certified',trial=trial,code_sha256=result['code_sha256'],route=answer.route,
        code_count=result['code_count'],solve_and_write_elapsed_ns=result['solve_and_write_elapsed_ns'])
    return result


def main(d, trial):
    d=Path(d).resolve();p=verify(d);ph=sha(d/'program.json')
    verify_command_admission(ph,trial,[sys.executable,'-B','-m','research_v51.worker',str(d),trial])
    out=d/trial/'outputs';out.mkdir();start=time.perf_counter_ns();count=0
    result=dict(schema='real-wide-stage-result-v51',status='running',program_sha256=ph,trial=trial,
        slurm_job_id=os.environ['SLURM_JOB_ID'],artifacts={},complete_model=False,quality_evaluation=False,
        confirmation=False,acl_ready=False)
    def artifact(name,blob):
        require(Path(name).name==name,'Unsafe artifact name')
        result['artifacts'][name]=new(out/name,blob,raw=True)
    def mark(phase,**details):
        nonlocal count
        if 'elapsed_ns' in details:details['component_elapsed_ns']=details.pop('elapsed_ns')
        row=dict(phase=phase,elapsed_ns=time.perf_counter_ns()-start,**details)
        new(out/f'progress-{count:04d}.json',row);count+=1
        print(canonical_json(row).decode(),flush=True)
    try:
        result['measurement']=prepare(p,artifact,mark) if trial=='prepare' else solve(p,d,trial,artifact,mark)
        result['status']='complete'
    except Exception as error:
        result.update(status='failed',error=str(error),error_type=type(error).__name__,traceback=traceback.format_exc())
        if isinstance(error,dispatch.DispatchRefused):result['refusal_diagnostics']=public_result(error.diagnostics)
        raise
    finally:
        usage=resource.getrusage(resource.RUSAGE_SELF)
        result.update(worker_elapsed_ns=time.perf_counter_ns()-start,max_rss_kib=usage.ru_maxrss,
            cpu_seconds=usage.ru_utime+usage.ru_stime,
            clock_scope='Worker includes verification, input reads, context/builds, solve, code write; controller includes shutdown.')
        new(out/'completion.json',result)


def final_check(d):
    d=Path(d);p=verify(d);results={trial:completed(d,trial) for trial in ORDER}
    code_blobs={trial:(d/trial/'outputs/codes.bin').read_bytes() for trial in ORDER[1:]}
    require(all(blob==code_blobs['reference'] for blob in code_blobs.values()),'Actual complete stage bytes differ')
    require(len(code_blobs['reference'])==768*3072//2,'Incomplete packed code tensor')
    snap=snapshot(d)
    require(snap['reserved_unknown_attempts']==0 and len(snap['attempts'])==4,'Stage phase unsettled')
    result=dict(schema='real-wide-stage-gate-v51',status='passed',program_sha256=sha(d/'program.json'),
        stage_id=STAGE_ID,code_count=768*3072,all_three_code_blobs_equal=True,
        historical_code_commitment_matches=digest(code_blobs['reference'])==HISTORICAL_CODE,
        trials={name:dict(completion_sha256=sha(d/name/'outputs/completion.json'),
            transaction_sha256=sha(d/name/'transaction.json')) for name in ORDER},budget=snap,
        complete_model=False,quality_evaluation=False,confirmation=False,acl_ready=False,
        scope='One fixed development wide stage; fixed order, no statistical speedup or full-model runtime extrapolation.')
    new(d/'gate.json',result)
    print(canonical_json(dict(status=result['status'],program_sha256=result['program_sha256'])).decode(),flush=True)


if __name__=='__main__':main(sys.argv[1],sys.argv[2])
