"""One bounded sequential constructor plus exposed-article quality evaluation."""
import gc
from pathlib import Path
import resource
import sys
import time
import traceback

from research_v44.campaign import ROOT, new, read, sha, verify, bound
from research_v44.diagnostic import require, reconstruct_fixed, parity, summarize
from src.run_store import canonical_json, digest
from src.transaction_timing import verify_command_admission


def main(plan_path):
    plan_path = Path(plan_path).absolute()
    plan = read(plan_path)
    program_path = Path(plan['program'])
    p = verify(program_path.parent)
    require(sha(program_path) == plan['program_sha256'], 'Diagnostic program binding differs')
    verify_command_admission(plan['program_sha256'],'development',
        [sys.executable,'-B','-m','research_v44.worker',str(plan_path)])
    out = Path(plan['output'])
    out.mkdir(parents=True,exist_ok=False)
    start = time.perf_counter_ns()
    result = dict(schema='exposed-quality-worker-v44',status='running',program_sha256=plan['program_sha256'],
        slurm_job_id=plan['slurm_job_id'],quality={},artifacts={},confirmation=False,acl_ready=False,
        approximate_numpy_binary64_likelihood=True,certified_inference=False,intervals=False,
        no_new_quality_inputs=True,model_target='fixed-anchor retained32/original96 versus matched sequential',
        shared_evaluator_sha256=sha(ROOT/'scripts/run_quality_v30.py'))

    def artifact(name, blob):
        result['artifacts'][name] = new(out/name,blob,raw=True)

    def mark(phase, **details):
        event = dict(phase=phase,worker_elapsed_ns=time.perf_counter_ns()-start,**details)
        new(out/f'progress-{mark.count:04d}.json',event)
        mark.count += 1
        print(canonical_json(event).decode(),flush=True)
    mark.count = 0

    def evaluate(evaluator, record, label, prefix):
        from scripts.run_quality_v30 import nll_from_logits
        tick = time.perf_counter_ns()
        nll = nll_from_logits(evaluator.logits(record['tokens'],prefix),record['tokens'])
        result['quality'].setdefault(label,[]).append(dict(id=record['id'],nll_sum=nll,
            predictions=127,mean_nll=nll/127,elapsed_ns=time.perf_counter_ns()-tick))
        mark('quality_article',model=label,record_id=record['id'],nll_sum=nll)

    try:
        from research_v38.bootstrap_target import CHECKPOINT_HASHES
        from research_v42.resource_plan import BoundTarget
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.dyadic_row_target import build_dyadic_row_target
        from src.fixed_anchor_target import build_fixed_anchor_target
        from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
        from src.target_manifest import TargetRecipe
        from src.adaptive_calibration_v30 import AdaptiveBudget
        from scripts.run_ordered_sequential_v30 import calibrate_sequential_ordered
        from scripts.run_adaptive_service_v30 import preflight_stages
        from scripts.run_quality_v30 import NumpyQualityDecoder, nearest_prefix
        from scripts.execute_gram_pilot_v35 import public_result

        old = read(bound(p['inputs']['v43_program']))
        history = read(bound(p['inputs']['historical_losses']))
        checkpoint = bound(p['inputs']['checkpoint_config']).parent
        require(bound(p['inputs']['checkpoint_weights']).parent == checkpoint, 'Checkpoint components must share a directory')
        tick = time.perf_counter_ns()
        loaded = load_gpt2_checkpoint(checkpoint,identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256'] == CHECKPOINT_HASHES, 'Common checkpoint identity changed')
        decoder = OrderedFiniteDecoder(loaded.decoder,primitive_backend='mpfr_enclosure')
        base = build_dyadic_row_target(decoder,TargetRecipe(original_token_count=96,group_count=1))
        fixed = build_fixed_anchor_target(decoder,base)
        target = BoundTarget(canonical_json(base.payload()),canonical_json(fixed.payload()))
        codes = reconstruct_fixed(bound(p['inputs']['fixed_state']).read_bytes(),
            bound(p['inputs']['fixed_model']).read_bytes(),bound_target=target,
            records=p['retained_records'],provenance=old['record_provenance'])
        require(tuple(s.stage_id for s in codes)==tuple(decoder.stage_ids), 'Complete model stage order differs')
        require(len(p['retained_records'])==1 and len(p['retained_records'][0]['tokens'])==32, 'Final retained input changed')
        budget = AdaptiveBudget(max_workspace_bytes=8*2**30,max_work_units=64_000_000_000,
            max_refinement_coordinates=16)
        admission = preflight_stages(base.stages,32,budget=budget,route='token',max_point_work_units=1_000_000_000_000)
        evaluator = NumpyQualityDecoder(loaded.decoder)
        require(set(evaluator.weights)=={s.stage_id for s in codes}, 'Evaluator/model stage extent differs')
        nearest = nearest_prefix(loaded.decoder,base.stages)
        result.update(context_elapsed_ns=time.perf_counter_ns()-tick,point_admission=admission,
            fixed_target_sha256=fixed.digest,sequential_target_sha256=base.digest,
            fixed_model_sha256=p['inputs']['fixed_model']['sha256'],code_count=42_467_328,
            original_normalization=96,retained_calibration_tokens=32,
            excluded_from_future_confirmation_ids=read(bound(p['inputs']['all_exclusions']))['excluded_from_future_confirmation_ids'])
        artifact('sequential-target.json',canonical_json(base.payload()))
        artifact('fixed-target.json',canonical_json(fixed.payload()))
        artifact('execution-provenance.json',canonical_json(dict(decoder=decoder.kernel_manifest,
            implementation=decoder.implementation_manifest,checkpoint=loaded.provenance)))
        mark('targets_and_actual_model_validated')

        # All parity controls use the same exposed articles; no old CLI is run.
        for index,record in enumerate(p['records']):
            order = ('full_precision','nearest_rounding') if index%2==0 else ('nearest_rounding','full_precision')
            for label in order:
                evaluate(evaluator,record,label,None if label=='full_precision' else nearest)
        result['historical_parity'] = parity(result['quality'],history)
        artifact('historical-parity.json',canonical_json(result['historical_parity']))
        require(result['historical_parity']['passed'], 'Historical control parity failed; new model losses are not valid')
        del nearest
        gc.collect()
        mark('all_historical_controls_passed')

        tick = time.perf_counter_ns()
        sequential,diagnostics = calibrate_sequential_ordered(decoder,base,p['retained_records'],
            budget=budget,route='token',max_point_work_units=1_000_000_000_000,
            progress=lambda row:mark('sequential_stage',stage_id=row['stage_id'],elapsed_ns=row['elapsed_ns']))
        require(len(sequential)==24 and sum(s.rows*s.columns for s in sequential)==42_467_328,
            'Sequential comparator did not produce every complete calibrated stage')
        for actual,control in zip(codes,sequential):
            require(actual.stage_id==control.stage_id and actual.shape==control.shape
                and actual.bits==control.bits==4 and actual.scale_values==control.scale_values,
                'Fixed and sequential comparator grids differ')
        artifact('sequential-model.bin',b''.join(s.packed_indices for s in sequential))
        artifact('sequential-model-metadata.json',canonical_json(dict(target_sha256=base.digest,
            stages=[s.metadata() for s in sequential])))
        artifact('sequential-diagnostics.json',canonical_json(public_result(diagnostics)))
        result['sequential_construction_elapsed_ns'] = time.perf_counter_ns()-tick
        prefixes = dict(fixed_feature={s.stage_id:s.array() for s in codes},
            sequential={s.stage_id:s.array() for s in sequential})
        for index,record in enumerate(p['records']):
            order = ('fixed_feature','sequential') if index%2==0 else ('sequential','fixed_feature')
            for label in order:
                evaluate(evaluator,record,label,prefixes[label])
        result['summary'] = summarize(result['quality'])
        result['status'] = 'complete'
        result['valid_diagnostic'] = True
        # A guard failure is a valid adverse result, never a retry trigger.
        result['development_guards_pass'] = result['summary']['development_guards_pass']
        tick = time.perf_counter_ns()
        del prefixes,sequential,codes,evaluator,decoder,loaded
        gc.collect()
        result['disposal_elapsed_ns'] = time.perf_counter_ns()-tick
        mark('diagnostic_complete',development_guards_pass=result['development_guards_pass'])
    except Exception as error:
        result.update(status='failed',valid_diagnostic=False,error_type=type(error).__name__,
            error=str(error),traceback=traceback.format_exc())
        raise
    finally:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        result.update(worker_elapsed_ns=time.perf_counter_ns()-start,max_rss_kib=usage.ru_maxrss,
            cpu_self_seconds=usage.ru_utime+usage.ru_stime,
            timing_scope='Context, parity, sequential construction, all likelihoods, writes and disposal; controller additionally charges verification before worker clock, terminal commit and exit')
        new(out/'completion.json',result)


if __name__=='__main__':
    main(sys.argv[1])
