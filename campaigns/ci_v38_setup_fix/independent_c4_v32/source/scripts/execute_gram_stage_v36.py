"""Full first-QKV stage over the frozen V35 exact-Gram numerical kernels.

This independently registered stage follow-up has 2,304 complete output rows.
Its features and target are unchanged; it is still not a complete-model run.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from fractions import Fraction
import json
import re
from pathlib import Path
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from src.run_store import canonical_json,digest
from src.compact_state import StageCodes
from src.runtime_contract import capture_runtime_contract
from scripts.execute_gram_pilot_v35 import (new_file,hashed,require,decode,descriptor_bytes,public_result,current_sources as v35_sources)
from research_v36.archive_stage_capsule import (load_capsule,capsule_files,STAGE,ROWS,WIDTH)
from research_v35.archive_capsule import DELETED,RETAINED

def current_sources():
    result=v35_sources()
    for p in sorted((ROOT/'research_v36').glob('*.py')):
        result[str(p.relative_to(ROOT))]=hashed(p)
    for name in ('execute_gram_stage_v36.py','launch_gram_stage_v36.py'):
        result['scripts/'+name]=hashed(ROOT/'scripts'/name)
    return result

def bind_inputs(capsule):
    p=Path(capsule).resolve();sha=hashed(p);metadata,files=capsule_files(p,sha)
    return dict(capsule=dict(path=str(p),sha256=sha,bytes=p.stat().st_size),dependencies=files)

def verify_inputs(entries):
    require(type(entries)is dict and set(entries)=={'capsule','dependencies'},'stage input fields differ')
    entry=entries['capsule'];p=Path(entry['path'])
    require(set(entry)=={'path','sha256','bytes'} and p.is_absolute() and hashed(p)==entry['sha256'] and p.stat().st_size==entry['bytes'],'stage capsule binding differs')
    metadata,files=capsule_files(p,entry['sha256'])
    require(files==entries['dependencies'],'complete stage capsule dependency closure differs')

def load_registered_inputs(entries):
    return load_capsule(entries['capsule']['path'],entries['capsule']['sha256'])

def admission(entries):
    from research_v35.exact_gram import assess_features,GramBudget
    from research_v35.direct_gram import assess_direct_gram_budget
    from src.primal_certificate_v30 import PrimalBudget
    verify_inputs(entries);data=load_registered_inputs(entries)
    descriptors=data['descriptors'];features=np.concatenate([decode(descriptors[rid]) for rid in (DELETED,RETAINED)])
    gram=asdict(assess_features(features.T.copy(),budget=GramBudget()))
    direct=assess_direct_gram_budget(rows=ROWS,width=WIDTH,bits=4,budget=PrimalBudget(max_workspace_bytes=512*2**20,max_work_units=6_000_000_000))
    require(direct['admitted'],'full-stage numerical admission failed')
    return dict(schema='archive-gram-stage-admission-v36',no_gram_formed=True,no_codes_computed=True,
        gram=gram,direct=direct,stage_id=STAGE,rows=list(range(ROWS)),width=WIDTH,original_tokens=256,retained_tokens=128,
        normalization=256,feature_sha256=digest(features.astype('<f8').tobytes()),weight_rows_sha256=digest(data['weights'].astype('<f8').tobytes()),
        target_sha256=data['target'],descriptor_sha256={rid:digest(descriptor_bytes(d)) for rid,d in descriptors.items()},
        retained_descriptor_sha256=digest(descriptor_bytes(data['retained_descriptor'])),runtime=capture_runtime_contract(),numpy_version=np.__version__)

def scientific_refusal(exc):
    """Only declared certificate-bound failures are scientific observations.

    Runtime, allocation, compiler, admission, and integrity errors stay fatal.
    The pinned native ABI uses status3 for an unresolved rounding cell and
    status2 in npc_column for a finite coefficient enclosure failure.
    """
    from research_v35.direct_gram import DirectGramUnresolved
    from src.low_rank_certified import LowRankUnresolved
    message=str(exc)
    if isinstance(exc,DirectGramUnresolved):
        return bool(re.fullmatch(r'primal native row verification failed: status=3, row=\d+, coordinate=\d+',message)
            or re.fullmatch(r'direct Gram coefficient enclosure failed at coordinate \d+: status=2',message)
            or re.fullmatch(r'primal rounding cell unresolved at coordinate \d+, row \d+',message))
    return isinstance(exc,LowRankUnresolved) and bool(re.fullmatch(r'exact fallback budget exceeded at coordinate \d+; no codes committed',message))

def worker(plan_path):
    from research_v35.exact_gram import accumulate, add_grams, subtract_gram, dumps, loads, GramBudget
    from research_v35.direct_gram import certify_exact_gram
    from src.primal_certificate_v30 import PrimalBudget, prepare_primal_native
    from src.native_ball_quantizer import prepare_native_ball
    from src.native_token_coefficients_v30 import prepare_native_token_coefficients
    from src.fast_token_quantizer_v30 import native_fast_quantize_dyadic_rows
    from src.dyadic_row_quantizer import dyadic_row_scales
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_bytes());out=Path(plan['output'])
    require(not out.exists(),'attempt output already exists; no retry')
    out.mkdir(parents=True)
    record=dict(schema='archive-gram-stage-result-v36',status='running',plan_sha256=hashed(plan_path),component_only=True,
      feature_generation_reexecuted=False,confirmation=False,arm_order=plan['arm_order'],timings_ns={},artifacts={},phases=[],arm_outcomes={key:{'status':'unstarted'} for key in ('delete','cold','cache')})
    def mark(phase):
        record['phases'].append(phase)
        new_file(out/f'progress-{len(record["phases"]):02d}.json',canonical_json(record))
        print(json.dumps({'phase':phase}),flush=True)
    def timed(name,fn):
        start=time.perf_counter_ns();value=fn();record['timings_ns'][name]=time.perf_counter_ns()-start
        return value
    def artifact(name,payload):
        new_file(out/name,payload);record['artifacts'][name]=dict(sha256=digest(payload),bytes=len(payload))
    def packed_codes(name,codes):
        require(np.array_equal(codes,reference),'codes differ from archived retained reference')
        stage=StageCodes.from_array(STAGE,codes,bits=4,grid_axis='dyadic_row',scale_values=scales)
        artifact(name,stage.packed_indices)
        return dict(codes=int(codes.size),sha256=digest(stage.packed_indices),scales_hex=[s.hex() for s in scales])
    def solve_arm(key,clock,fn):
        tick=time.perf_counter_ns()
        try:
            result=fn()
        except Exception as exc:
            if not scientific_refusal(exc):raise
            record['arm_outcomes'][key]=dict(status='scientific_refusal',error_type=type(exc).__name__,error=str(exc),codes_committed=False,timing_scope='Incomplete certificate-attempt time; not complete reconstruction latency; no speed ratio is defined.')
            return None
        finally:
            record['timings_ns'][clock]=time.perf_counter_ns()-tick
        record[key+'_codes']=packed_codes(key+'-codes.bin',result.codes)
        record[key+'_certificate']=public_result(result)
        record['arm_outcomes'][key]=dict(status='certified',codes_committed=True)
        return result
    try:
        require(current_sources()==plan['source_sha256'],'numerical or controller source changed')
        require(capture_runtime_contract()==plan['runtime'],'registered software runtime changed')
        timed('common_input_verification',lambda:verify_inputs(plan['inputs']))
        data=timed('common_archive_capsule_parse',lambda:load_registered_inputs(plan['inputs']))
        descriptors=data['descriptors'];retained_descriptor=data['retained_descriptor'];weights=data['weights'];reference=data['reference']
        scales=dyadic_row_scales(weights)
        require(scales==data['scales'],'canonical row scales differ')
        record['native_builds']=timed('common_native_build',lambda:dict(primal=prepare_primal_native(),token_loop=prepare_native_ball(),token_coefficients=prepare_native_token_coefficients()))
        mark('shared_inputs_and_native_build_complete')
        gb=GramBudget();pb=PrimalBudget(max_workspace_bytes=512*2**20,max_work_units=6_000_000_000)
        start=time.perf_counter_ns()
        original_features=timed('prepare_feature_decode',lambda:np.concatenate([decode(descriptors[r]) for r in (DELETED,RETAINED)]))
        original_gram=timed('prepare_exact_accumulation',lambda:add_grams(accumulate(original_features[:128].T.copy(),source_id=DELETED,normalization=256,budget=gb),accumulate(original_features[128:].T.copy(),source_id=RETAINED,normalization=256,budget=gb),budget=gb))
        original_bytes=timed('prepare_serialize',lambda:dumps(original_gram))
        artifact('original-gram.bin',original_bytes)
        original_sources=original_gram.sources
        record['original_gram_sources']=[asdict(v) for v in original_sources]
        record['timings_ns']['prepare_component_total']=time.perf_counter_ns()-start
        del original_features,original_gram,original_bytes
        mark('pooled_gram_preparation_complete')
        start=time.perf_counter_ns()
        original_gram=timed('delete_load_parse_original',lambda:loads((out/'original-gram.bin').read_bytes(),trusted_sha256=record['artifacts']['original-gram.bin']['sha256'],expected_sources=original_sources))
        deleted_features=timed('delete_feature_decode',lambda:decode(descriptors[DELETED]))
        deleted_gram=timed('delete_exact_accumulation',lambda:accumulate(deleted_features.T.copy(),source_id=DELETED,normalization=256,budget=gb))
        repaired=timed('delete_exact_subtraction',lambda:subtract_gram(original_gram,deleted_gram))
        repaired_bytes=timed('delete_serialize',lambda:dumps(repaired))
        artifact('retained-gram.bin',repaired_bytes)
        repaired_result=solve_arm('delete','delete_solve_certificate',lambda:certify_exact_gram(weights,repaired,ridge=Fraction(1,100),budget=pb))
        record['timings_ns']['delete_component_total']=time.perf_counter_ns()-start
        del original_gram,deleted_gram,deleted_features,repaired
        mark('pooled_gram_deletion_complete')
        start=time.perf_counter_ns()
        retained_features=timed('cold_feature_decode',lambda:decode(retained_descriptor))
        cold_gram=timed('cold_exact_accumulation',lambda:accumulate(retained_features.T.copy(),source_id=RETAINED,normalization=256,budget=gb))
        cold_bytes=timed('cold_serialize',lambda:dumps(cold_gram))
        artifact('cold-retained-gram.bin',cold_bytes)
        require(cold_bytes==repaired_bytes,'exact pooled Gram subtraction differs from independent retained construction')
        cold_result=solve_arm('cold','cold_solve_certificate',lambda:certify_exact_gram(weights,cold_gram,ridge=Fraction(1,100),budget=pb))
        record['timings_ns']['cold_component_total']=time.perf_counter_ns()-start
        del retained_features,cold_gram,cold_bytes,repaired_bytes
        mark('cold_gram_reconstruction_complete')
        start=time.perf_counter_ns()
        cache_features=timed('cache_feature_decode',lambda:decode(retained_descriptor))
        cache_result=solve_arm('cache','cache_token_solve_certificate',lambda:native_fast_quantize_dyadic_rows(weights,cache_features.T.copy(),ridge=Fraction(1,100),normalization=256))
        record['timings_ns']['cache_component_total']=time.perf_counter_ns()-start
        all_certified=all(row['status']=='certified' for row in record['arm_outcomes'].values())
        record.update(status='complete',exact_gram_equality=True,all_three_code_arrays_equal=True if all_certified else None,scientific_gate_passed=all_certified,
            retained_descriptor_bytes=len(descriptor_bytes(retained_descriptor)),retained_feature_bytes=int(cache_features.nbytes),
            exact_product_contributions=151_191_552,exact_packed_additions=295_296,exact_packed_subtractions=295_296,neural_stage_traversals=0,
            cross_version_clock_scope='V36 includes diagnostic dataclass serialization inside every arm total; V35 recorded that conversion after its arm total.',
            claim_scope='One fixed-order complete-first-stage development observation. No complete service speed or feature-generation revalidation.',
            excludes='Shared artifact verification, archive parsing, weight load, and native builds reported separately. Neural replay absent; original model preparation absent. No lifetime claim.',
            expansion_gate='Correct exact algebra permits designing a larger comparator; latency does not trigger automatic expansion.')
        mark('all_registered_component_checks_complete')
    except BaseException as exc:
        record.update(status='failed',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        new_file(out/'failure.json',canonical_json(record))
        raise
    raw=canonical_json(record);new_file(out/'completion.json',raw)
    print('GRAM_STAGE_TERMINAL_SHA256='+digest(raw),flush=True)
    return record

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan');args=parser.parse_args();worker(args.plan)
