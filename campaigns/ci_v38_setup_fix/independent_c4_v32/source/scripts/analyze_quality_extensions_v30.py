"""Audit existing six-model quality evidence without neural inference."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import analyze_full_service_v30 as common
from scripts.launch_quality_extensions_v30 import checked_external, verify_external_equalities
from scripts.run_followup_quality_v30 import (OLD_LABELS, policy_for_mode, validate_new_generation,
    validate_reused_articles, validate_sequential_generation, validate_sequential_implementation)
from scripts.run_quality_v30 import check_generation
from src.compact_state import parse
from src.experiment_inventory import source_hashes
from src.run_store import canonical_json, digest
from src.service_terminal_evidence_v30 import verify_completed

require, hashed, read_json = common.require, common.hashed, common.read_json
TRIALS = ('sequential-128', 'matched-quality-128')
LABELS = ('full_precision', 'nearest_rounding', 'fixed16', 'sequential16', 'fixed128', 'sequential128')


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-13, abs_tol=1e-12)


def recompute(result, registration, first):
    """Recompute every paired comparison directly from saved article NLLs."""
    import numpy as np
    policy = policy_for_mode(True)
    require(result['policy'] == policy, 'prospective matched policy changed')
    ids = [row['id'] for row in registration['records']]
    require(len(ids) == len(set(ids)) == 8, 'eight distinct registered articles are required')
    require(set(result['quality']) == set(LABELS), 'all six models are required')
    tables, losses, totals = {}, {}, {}
    for label in LABELS:
        rows = result['quality'][label]
        table = {row['id']:row for row in rows}
        require(len(rows) == 8 and set(table) == set(ids), 'model article inventory differs')
        require(all(row['predictions'] == 127 and math.isfinite(row['nll_sum'])
            and row['nll_sum'] >= 0 and close(row['mean_nll'], row['nll_sum']/127) for row in rows),
            'invalid article NLL or prediction count')
        tables[label] = table
        losses[label] = np.array([table[rid]['nll_sum'] for rid in ids], dtype=np.float64)
        total = float(losses[label].sum())
        totals[label] = dict(nll_sum=total, predictions=1016, mean_nll=total/1016, perplexity=math.exp(total/1016))
        saved = result['summary']['totals'][label]
        require(saved.keys() == totals[label].keys() and all(close(saved[k],v) for k,v in totals[label].items()),
                'saved model totals differ from article sums')
    expected_parity = {}
    for label, old_label in OLD_LABELS.items():
        history = {row['id']:row for row in first['quality'][old_label]}
        for rid in ids:
            expected_parity[label,rid] = abs(tables[label][rid]['nll_sum']-history[rid]['nll_sum'])/127
    parity = {(row['model'],row['id']):row['mean_nll_deviation'] for row in result['parity']}
    require(len(result['parity']) == 32 and parity == expected_parity, 'historical parity table differs')
    parity_pass = max(parity.values()) <= policy['historical_parity_max_mean_nll_deviation']
    rng = np.random.default_rng(policy['bootstrap_seed'])
    samples = rng.integers(0, 8, size=(policy['bootstrap_repetitions'],8))
    comparisons = {}
    for reference in LABELS:
        if reference == 'fixed128':
            continue
        difference = losses['fixed128']-losses[reference]
        ratio = math.exp(float(difference.sum())/1016)
        per_article = {rid:math.exp(float(value)/127) for rid,value in zip(ids,difference)}
        interval = np.exp(np.quantile(difference[samples].sum(axis=1)/1016,[.025,.975],method='linear')).tolist()
        saved = result['summary']['fixed128_comparisons'][reference]
        require(close(saved['perplexity_ratio'],ratio) and close(saved['mean_nll_difference'],float(difference.sum())/1016),
                'saved aggregate paired estimate differs')
        require(saved['article_perplexity_ratios'].keys() == per_article.keys()
            and all(close(saved['article_perplexity_ratios'][rid], value) for rid,value in per_article.items()),
            'saved article ratios differ')
        require(all(close(a,b) for a,b in zip(saved['bootstrap_95_percentile_ratio'],interval))
            and len(saved['bootstrap_95_percentile_ratio']) == 2 and saved['descriptive_only'] is True,
            'saved descriptive interval differs')
        comparisons[reference] = dict(perplexity_ratio=ratio,percent_change=100*(ratio-1),
            bootstrap_95_percentile_ratio=interval,article_perplexity_ratios=per_article,
            article_wins=sum(value<1 for value in per_article.values()),
            article_losses=sum(value>1 for value in per_article.values()),
            article_ties=sum(value==1 for value in per_article.values()),
            maximum_article_ratio=max(per_article.values()),comparison_scope=saved['comparison_scope'])
    def passes(reference):
        row = comparisons[reference]
        return row['perplexity_ratio'] <= policy['max_aggregate_ratio'] and row['maximum_article_ratio'] <= policy['max_each_article_ratio']
    gates = dict(matched_quality_gate_pass=passes('sequential128'),
                 development_safety_gate_pass=passes('fixed16'),historical_control_parity_pass=parity_pass)
    require(all(result[name] is value for name,value in gates.items()), 'terminal gate disagrees with saved losses')
    require(all(result['summary'][name] is gates[name] for name in ('matched_quality_gate_pass','development_safety_gate_pass')),
            'summary gate disagrees with saved losses')
    require(result['summary']['bootstrap'] == dict(unit='whole paired article',repetitions=10000,seed=31,
        interval='percentile2.5%,97.5%; linear quantile',scope='adaptive reused development articles; no population or confirmation inference'),
        'bootstrap reporting policy differs')
    require(result['primary_comparison_control'] == 'sequential128'
        and result['primary_observed_win'] is (comparisons['sequential128']['perplexity_ratio'] < 1),
        'primary result direction differs')
    return dict(totals=totals,comparisons=comparisons,gates=gates,all_three_gates_pass=all(gates.values()),
        historical_parity=dict(comparisons=32,maximum_mean_nll_deviation=max(parity.values()),threshold=1e-8),
        per_article=[dict(id=rid,predictions=127,nll_sum={label:tables[label][rid]['nll_sum'] for label in LABELS},
            fixed128_over_sequential128=comparisons['sequential128']['article_perplexity_ratios'][rid],
            fixed128_over_fixed16=comparisons['fixed16']['article_perplexity_ratios'][rid]) for rid in ids])


def analyze(campaign):
    started = time.process_time_ns()
    campaign = Path(campaign).absolute(); evidence = {}
    def bind(path):
        path = Path(path).absolute()
        evidence[str(path)] = dict(bytes=path.stat().st_size,sha256=hashed(path))
    program, protocol, registration = [read_json(campaign/name) for name in ('program.json','protocol.json','registration.json')]
    ph, qh = hashed(campaign/'program.json'), hashed(campaign/'protocol.json')
    require(registration['program_sha256'] == ph and registration['protocol_sha256'] == qh
        and protocol['program_sha256'] == ph, 'registration binding differs')
    require(protocol['phase_cpu_seconds'] == {'feasibility':program['phase_cpu_cap_seconds']}, 'phase cap differs')
    require(tuple(row['id'] for row in program['trials']) == TRIALS, 'trial inventory differs')
    require({p.name for p in (campaign/'attempts').iterdir() if p.is_dir()} == set(TRIALS), 'unreported or missing attempts')
    require(source_hashes(campaign/'source') == program['source_sha256'], 'frozen worker sources changed')
    for name,expected in program['controller_sha256'].items():
        require(hashed(campaign/'source'/name) == expected, 'frozen controller source differs')
    require(hashed(campaign/'registered-launcher.py') == program['controller_sha256']['scripts/launch_quality_extensions_v30.py'],
            'registered launcher differs')
    for name,expected in program['historical_frozen_ledgers'].items():
        require(hashed(ROOT/name) == expected, 'historical ledger changed'); bind(ROOT/name)
    external = checked_external(program['external_attempts'], require_bindings=True)
    equalities = verify_external_equalities(external,program['external_equalities'])
    require(equalities == program['external_equality_checks'], 'registered equality checks differ')
    for parent in external.values():
        for name in parent['evidence']:
            bind(Path(parent['attempt'])/name)
    results, plans, receipts, clocks = {}, {}, [], []
    for trial in program['trials']:
        attempt = campaign/'attempts'/trial['id']; result = verify_completed(attempt)
        plan = read_json(attempt/'plan.json')
        common.verify_plan(campaign,trial,plan,program,ph,qh,results)
        transaction,receipt,identity = [read_json(attempt/name) for name in ('transaction.json','worker/result.json','worker/identity.json')]
        common.verify_worker_schedule(campaign,trial,transaction,identity,registration,program)
        require(receipt['budget_debit']['reserved_cpu_seconds'] == trial['cpu_seconds']+2, 'reservation differs')
        require(result['confirmation'] is False and result['scientific_promotion'] is False, 'development scope changed')
        for dependency in trial.get('depends',[]):
            require(dependency['trial'] in results, 'dependency was not earlier')
            require(all(results[dependency['trial']][key] == value for key,value in dependency.get('equals',{}).items()),
                    'registered dependency gate failed')
        results[trial['id']], plans[trial['id']] = result, plan; receipts.append(receipt)
        clocks.append(dict(trial=trial['id'],controller_seconds=transaction['controller_elapsed_ns']/1e9,
            observed_cpu_seconds=receipt['resource_usage']['total_cpu_ns']/1e9,
            charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],peak_rss_bytes=result['peak_rss_bytes']))
        for path in attempt.rglob('*'):
            if path.is_file() and path.suffix in ('.json','.txt','.log'):
                bind(path)
        for entry in plan['inputs'].values():bind(entry['path'])
    budget = common.verify_final_budget(campaign,program,qh,receipts)
    seq, quality = results[TRIALS[0]], results[TRIALS[1]]
    sqplan, plan = plans[TRIALS[0]], plans[TRIALS[1]]
    require(quality['schema'] == 'adaptive-quality-followup-v30' and quality['matched_sequential128_comparator'] is True
        and quality['adaptive_followup'] is True and quality['new_evaluation_articles'] is False
        and quality['new_exclusions'] is False and quality['predictions_per_model'] == 1016
        and quality['nll_is_not_certified_interval'] is True, 'quality scope differs')
    inputs=plan['inputs']; reg=read_json(inputs['first_registration']['path'])
    first=verify_completed(Path(inputs['first_completion']['path']).parent.parent)
    pools=read_json(inputs['pools']['path']);records=validate_reused_articles(reg,first,pools)
    require(quality['excluded_from_future_confirmation_ids'] == reg['excluded_from_future_confirmation_ids'], 'exclusions changed')
    new_attempt=Path(inputs['new_completion']['path']).parent.parent
    new=verify_completed(new_attempt);new_plan=read_json(new_attempt/'plan.json')
    require(source_hashes(new_attempt.parents[1]/'source') == new_plan['source_sha256'], 'fixed128 generation sources changed')
    original=read_json(new_plan['inputs']['records']['path'])
    checkpoint={name:inputs[key]['sha256'] for name,key in (('config.json','config'),('model.safetensors','weights'))}
    fixed_binding={key:new['model_artifact'][key] for key in ('sha256','bytes')}
    validate_new_generation(new,new_plan,original,checkpoint_hashes=checkpoint,model_binding=fixed_binding)
    validate_sequential_generation(seq,sqplan,original,checkpoint_hashes=checkpoint,
        model_binding={key:seq['model_artifact'][key] for key in ('sha256','bytes')},fixed_completion=new)
    implementation_path=campaign/'attempts/sequential-128/outputs/implementation.json'
    validate_sequential_implementation(seq,plan['policy'],implementation_path.read_bytes(),campaign/'source/src')
    for filename,field in (('sequential-target.json','sequential_target_sha256'),
                            ('fixed-target-reference.json','fixed_target_sha256')):
        require(hashed(campaign/'attempts/sequential-128/outputs'/filename) == seq[field], 'saved sequential target manifest differs')
    for filename,field in (('base-target.json','base_target_sha256'),('fixed-target.json','fixed_target_sha256')):
        require(hashed(new_attempt/'outputs'/filename) == new[field], 'saved fixed128 target manifest differs')
    require(seq['source_sha256'] == program['source_sha256'] and set(seq['artifacts']) == {'model','implementation'},
            'sequential source or artifact contract differs')
    require(seq['diagnostics']['neural_stage_record_pairs'] == 24 and seq['model_code_elements'] == 42467328,
            'sequential traversal or code coverage differs')
    legacy={key:inputs[key] for key in reg['inputs']}
    _,_,fixed16raw=check_generation(legacy,'fixed');_,_,seq16raw=check_generation(legacy,'sequential')
    models={label:parse(raw) for label,raw in (('fixed16',fixed16raw),('sequential16',seq16raw),
        ('fixed128',Path(inputs['new_model']['path']).read_bytes()),
        ('sequential128',Path(inputs['new_sequential_model']['path']).read_bytes()))}
    expected_targets=dict(fixed16=first['inference']['model_targets']['fixed_feature'],
        sequential16=first['inference']['model_targets']['sequential'],fixed128=new['fixed_target_sha256'],
        sequential128=seq['sequential_target_sha256'])
    for label,model in models.items():
        require(len(model.stages) == 24 and not model.factors and model.target_sha256 == expected_targets[label],
                'complete model target differs: '+label)
    for group in zip(*(model.stages for model in models.values())):
        original_stage=group[0]
        for other in group[1:]:
            require((original_stage.stage_id,original_stage.shape,original_stage.bits,original_stage.grid_axis,original_stage.scale_values)
                == (other.stage_id,other.shape,other.bits,other.grid_axis,other.scale_values), 'six-model grids differ')
    provenance=quality['provenance']
    require(provenance['new_model_sha256'] == inputs['new_model']['sha256'] == new['model_artifact']['sha256']
        and provenance['new_completion_sha256'] == hashed(new_attempt/'outputs/completion.json')
        and provenance['new_plan_sha256'] == hashed(new_attempt/'plan.json'), 'fixed128 provenance differs')
    require(provenance['sequential128']['model_sha256'] == seq['model_artifact']['sha256']
        and provenance['sequential128']['completion_sha256'] == hashed(campaign/'attempts/sequential-128/outputs/completion.json')
        and provenance['sequential128']['plan_sha256'] == seq['plan_sha256'], 'sequential provenance differs')
    require(provenance['shared_evaluator_sha256'] == reg['worker_source_sha256']['scripts/run_quality_v30.py']
        == program['source_sha256']['scripts/run_quality_v30.py'], 'quality evaluator changed')
    statistics=recompute(quality,reg,first)
    for name in ('program.json','protocol.json','registration.json','registered-launcher.py','phase-cpu-budget/ledger.json'):
        bind(campaign/name)
    for name in program['source_sha256']:bind(campaign/'source'/name)
    analysis_sources=['scripts/analyze_quality_extensions_v30.py','scripts/analyze_full_service_v30.py',
        'scripts/launch_quality_extensions_v30.py','scripts/run_followup_quality_v30.py','scripts/run_quality_v30.py',
        'src/run_store.py','src/service_terminal_evidence_v30.py','src/phase_budget.py','src/compact_state.py']
    for name in analysis_sources:bind(ROOT/name)
    return dict(schema='quality-extension-audit-v30',status='complete_evidence_verified',model_inference=False,
        confirmation=False,scientific_promotion=False,program_sha256=ph,protocol_sha256=qh,
        completion_sha256={name:hashed(campaign/'attempts'/name/'outputs/completion.json') for name in TRIALS},
        target_scope='fixed nearest-anchor versus sequential calibration; matched128 retained tokens and original256 normalization',
        article_scope='eight reused development articles, 127 predictions each; no population superiority inference',
        uncertainty_scope='whole paired-article descriptive bootstrap; 10000 draws, seed31, two-sided percentile95%',
        preserved_exclusions=reg['excluded_from_future_confirmation_ids'],external_model_equalities=equalities,
        model_sha256=dict(fixed16=inputs['fixed_model']['sha256'],sequential16=inputs['sequential_model']['sha256'],
            fixed128=inputs['new_model']['sha256'],sequential128=seq['model_artifact']['sha256']),
        trials=clocks,phase_budget=budget,evidence_sha256=evidence,
        analysis_source_sha256={name:hashed(ROOT/name) for name in analysis_sources},
        analysis_cpu_ns=time.process_time_ns()-started,**statistics)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,default=ROOT/'campaigns/quality_extensions_v30')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=analyze(args.campaign)
    with args.output.open('xb') as stream:stream.write(canonical_json(report))
    print(json.dumps(dict(status=report['status'],gates=report['gates'],
        matched_ratio=report['comparisons']['sequential128']['perplexity_ratio'],
        analysis_cpu_ns=report['analysis_cpu_ns'],sha256=hashed(args.output))))
