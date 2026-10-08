"""Prospective fixed-model evaluation on the forty remaining validation articles."""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.run_store import atomic_write,canonical_json,digest
from src.experiment_inventory import source_hashes
from src.service_terminal_evidence_v30 import verify_completed
from src.transaction_timing import verify_command_admission
from scripts.run_quality_v30 import NumpyQualityDecoder,nearest_prefix,nll_from_logits

LABELS=('full_precision','nearest_rounding','fixed128','sequential128')
POLICY=dict(schema='heldout-bounded-pool-quality-policy-v30',articles=40,tokens_per_article=128,
    primary_control='sequential128',max_aggregate_ratio=1.05,max_each_article_ratio=1.20,
    bootstrap_repetitions=20000,bootstrap_seed=20271008,bootstrap_quantile=.95,
    bootstrap_method='linear quantile of perplexity ratios from whole paired article resamples',
    max_bootstrap_upper_ratio=1.05,confirmation_scope='prospective confirmation within the fixed forty-article remainder',
    population_coverage_claimed=False,secondary_controls_descriptive=True,automatic_scientific_promotion=False)
INPUTS={'selection','pools','development_registration','development_completion','fixed_completion','fixed_model',
        'sequential_completion','sequential_model','config','weights','tokenizer'}


def require(value,message):
    if not value:raise ValueError(message)


def bound(entry):
    require(type(entry) is dict and set(entry) in ({'path','sha256'},{'path','sha256','bytes'}),'input descriptor differs')
    path=Path(entry['path']);require(path.is_absolute() and path.is_file() and not path.is_symlink(),'unsafe input path')
    raw=path.read_bytes();require(digest(raw)==entry['sha256'] and ('bytes' not in entry or len(raw)==entry['bytes']),
                               'input bytes differ: '+str(path))
    return raw


def validate_selection(selection,pools,development):
    require(selection.get('schema')=='heldout-quality-selection-v30' and selection.get('model_inference') is False,
            'selection provenance differs')
    old=development['excluded_from_future_confirmation_ids']
    require(len(old)==len(set(old))==20 and selection['prior_excluded_ids']==old,'twenty prior exclusions differ')
    expected=[dict(id=row['id'],tokens=row['tokens'][:128]) for row in pools['evaluation'] if row['id'] not in set(old)]
    records=selection['records'];ids=[row['id'] for row in records]
    require(records==expected and len(ids)==len(set(ids))==40,'held-out selection is not the complete fixed remainder')
    require(all(len(row['tokens'])==128 and all(type(t) is int and 0<=t<50257 for t in row['tokens']) for row in records),
            'held-out token prefix differs')
    require(not set(ids)&{row['id'] for row in pools['confirmation']},'training confirmation reserve accessed')
    require(selection['prospective_all_excluded_ids']==sorted(set(old)|set(ids)), 'prospective sixty-document exclusions differ')
    require(selection['exposure_audit']['remaining_id_collisions']==[]
        and selection['exposure_audit']['observed_metadata_ids']==sorted(old),'archive exposure audit differs')
    return records


def summarize(quality,records):
    import numpy as np
    ids=[row['id'] for row in records]
    require(len(ids)==len(set(ids))==40 and set(quality)==set(LABELS),'complete four-model forty-article table required')
    losses={}
    for label in LABELS:
        rows=quality[label];table={row['id']:row for row in rows}
        require(len(rows)==40 and set(table)==set(ids)
            and all(row['predictions']==127 and math.isfinite(row['nll_sum']) and row['nll_sum']>=0 for row in rows),
            'model article losses or counts differ')
        losses[label]=np.array([table[rid]['nll_sum'] for rid in ids])
    predictions=40*127
    totals={label:dict(nll_sum=float(values.sum()),predictions=predictions,mean_nll=float(values.sum()/predictions),
        perplexity=math.exp(float(values.sum()/predictions))) for label,values in losses.items()}
    contrasts={}
    for reference in ('sequential128','nearest_rounding','full_precision'):
        delta=losses['fixed128']-losses[reference]
        ratios={rid:math.exp(float(value/127)) for rid,value in zip(ids,delta)}
        contrasts[reference]=dict(perplexity_ratio=math.exp(float(delta.sum()/predictions)),
            mean_nll_difference=float(delta.sum()/predictions),article_perplexity_ratios=ratios,
            maximum_article_ratio=max(ratios.values()),article_wins=sum(value<1 for value in ratios.values()),
            article_losses=sum(value>1 for value in ratios.values()),primary=reference=='sequential128')
    rng=np.random.default_rng(POLICY['bootstrap_seed'])
    indices=rng.integers(0,40,size=(POLICY['bootstrap_repetitions'],40))
    delta=losses['fixed128']-losses['sequential128']
    samples=np.exp(delta[indices].sum(axis=1)/predictions)
    upper=float(np.quantile(samples,POLICY['bootstrap_quantile'],method='linear'))
    primary=contrasts['sequential128']
    guards=dict(bootstrap_upper_pass=upper<=POLICY['max_bootstrap_upper_ratio'],
        aggregate_ratio_pass=primary['perplexity_ratio']<=POLICY['max_aggregate_ratio'],
        per_article_ratio_pass=primary['maximum_article_ratio']<=POLICY['max_each_article_ratio'])
    return dict(totals=totals,contrasts=contrasts,primary_bootstrap_upper_ratio=upper,guards=guards,
        bounded_pool_confirmation_gate_pass=all(guards.values()),
        bootstrap=dict(repetitions=20000,seed=20271008,unit='whole paired article',quantile=.95,
            method=POLICY['bootstrap_method'],interpretation='article-mixture stability guard for the fixed pool; no guaranteed population coverage'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);args=parser.parse_args()
    raw=args.plan.read_bytes();plan=json.loads(raw)
    require(source_hashes(ROOT)==plan['source_sha256'] and plan['policy']==POLICY,'source or prospective policy differs')
    require(set(plan['inputs'])==INPUTS,'declared input access differs')
    verify_command_admission(plan['protocol_sha256'],'feasibility',[sys.executable,str(Path(__file__).resolve()),str(args.plan.absolute())])
    output=Path(plan['output']);require(not output.exists() or not any(output.iterdir()),'cannot overwrite held-out evidence')
    output.mkdir(parents=True,exist_ok=True);started=time.perf_counter_ns()
    result=dict(schema='heldout-bounded-pool-quality-v30',status='running',plan_sha256=digest(raw),policy=POLICY,
        confirmation=True,confirmation_scope=POLICY['confirmation_scope'],population_coverage_claimed=False,
        scientific_promotion=False,model_outputs_frozen=True,quality={},phases=[],nll_is_not_certified_interval=True)
    def save(phase,**details):
        event=dict(phase=phase,elapsed_ns=time.perf_counter_ns()-started,**details)
        result['phases'].append(event);result['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json',canonical_json(result));print(json.dumps(event),flush=True)
    try:
        save('input_verification_started');inputs=plan['inputs']
        for entry in inputs.values():bound(entry)
        selection=json.loads(bound(inputs['selection']));pools=json.loads(bound(inputs['pools']))
        development=json.loads(bound(inputs['development_registration']))
        records=validate_selection(selection,pools,development)
        require(selection['policy']==POLICY and selection['pools_sha256']==inputs['pools']['sha256'], 'selection policy binding differs')
        require(selection['tokenizer_sha256']==inputs['tokenizer']['sha256'], 'selection tokenizer differs')
        for path,entry in selection['exposure_audit']['metadata_files'].items():
            require(digest(Path(path).read_bytes())==entry['sha256'],'earlier exposure evidence changed')
        previous_path=Path(inputs['development_completion']['path'])
        previous=verify_completed(previous_path.parent.parent)
        require(previous==json.loads(bound(inputs['development_completion'])),'development terminal differs')
        require(all(previous.get(key) is True for key in ('matched_quality_gate_pass','development_safety_gate_pass','historical_control_parity_pass')),
                'development quality prerequisites did not pass')
        require(previous['excluded_from_future_confirmation_ids']==selection['prior_excluded_ids'],'development exclusions changed')
        from src.compact_state import parse
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.runtime_contract import capture_runtime_contract
        models={};generation={}
        for label,key in (('fixed128','fixed'),('sequential128','sequential')):
            path=Path(inputs[key+'_completion']['path']);result_generation=verify_completed(path.parent.parent)
            require(result_generation['model_artifact']['sha256']==inputs[key+'_model']['sha256']==selection['frozen_model_sha256'][label],
                    'frozen model identity differs')
            require(result_generation['original_token_count']==256 and result_generation['retained_token_count']==128
                and result_generation['complete_model'] is True and result_generation['model_code_elements']==42467328,
                'calibrated model scope differs')
            models[label]=parse(bound(inputs[key+'_model']));generation[label]=result_generation
            require(len(models[label].stages)==24 and not models[label].factors,'incomplete calibrated model')
        require(inputs['fixed_model']['sha256']==previous['provenance']['new_model_sha256']
            and inputs['sequential_model']['sha256']==previous['provenance']['sequential128']['model_sha256'],
            'models differ from the completed development follow-up')
        require(models['fixed128'].target_sha256==generation['fixed128']['fixed_target_sha256']
            and models['sequential128'].target_sha256==generation['sequential128']['sequential_target_sha256']
            and generation['fixed128']['base_target_sha256']==generation['sequential128']['sequential_target_sha256'],
            'calibration target binding differs')
        for left,right in zip(models['fixed128'].stages,models['sequential128'].stages):
            require((left.stage_id,left.shape,left.bits,left.grid_axis,left.scale_values)==
                (right.stage_id,right.shape,right.bits,right.grid_axis,right.scale_values) and left.bits==4,'calibrated grids differ')
        helper_hash=digest((ROOT/'scripts/run_quality_v30.py').read_bytes())
        require(helper_hash==previous['provenance']['shared_evaluator_sha256']==selection['quality_evaluator_sha256'],
                'shared numerical evaluator changed')
        checkpoint={name:inputs[key]['sha256'] for name,key in (('config.json','config'),('model.safetensors','weights'))}
        require(all(value['checkpoint_files_sha256']==checkpoint for value in generation.values()),'calibration checkpoint differs')
        loaded=load_gpt2_checkpoint(plan['checkpoint'],identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256']==checkpoint,'loaded checkpoint differs')
        evaluator=NumpyQualityDecoder(loaded.decoder)
        require(list(evaluator.weights)==[s.stage_id for s in models['fixed128'].stages],'checkpoint stage order differs')
        prefixes=dict(full_precision=None,nearest_rounding=nearest_prefix(loaded.decoder,models['fixed128'].stages),
            **{label:{s.stage_id:s.array() for s in model.stages} for label,model in models.items()})
        runtime=canonical_json(capture_runtime_contract());atomic_write(output/'runtime.json',runtime)
        result.update(artifacts=dict(runtime=dict(file='runtime.json',bytes=len(runtime),sha256=digest(runtime))),
            provenance=dict(selection_sha256=inputs['selection']['sha256'],frozen_model_sha256=selection['frozen_model_sha256'],
                development_completion_sha256=inputs['development_completion']['sha256'],quality_evaluator_sha256=helper_hash,
                checkpoint_files_sha256=checkpoint),article_ids=[row['id'] for row in records],
            excluded_from_future_confirmation_ids=selection['prospective_all_excluded_ids'])
        save('models_verified')
        for index,record in enumerate(records):
            order=LABELS[index%4:]+LABELS[:index%4]
            for label in order:
                save('quality_started',model=label,record_id=record['id'])
                nll=nll_from_logits(evaluator.logits(record['tokens'],prefixes[label]),record['tokens'])
                result['quality'].setdefault(label,[]).append(dict(id=record['id'],predictions=127,nll_sum=nll,mean_nll=nll/127))
                save('quality_complete',model=label,record_id=record['id'])
        result['summary']=summarize(result['quality'],records)
        result.update(status='complete',predictions_per_model=5080,
            bounded_pool_confirmation_gate_pass=result['summary']['bounded_pool_confirmation_gate_pass'])
        save('complete');terminal=canonical_json(result)
        with (output/'completion.json').open('xb') as stream:
            stream.write(terminal);stream.flush();os.fsync(stream.fileno())
        print(json.dumps(dict(terminal_sha256=digest(terminal))),flush=True)
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise


if __name__=='__main__':main()
