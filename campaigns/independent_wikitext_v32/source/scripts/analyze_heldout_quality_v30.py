"""Strict archive-only analysis of the prospective forty-article quality phase."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import analyze_full_service_v30 as common
from scripts.launch_heldout_quality_v30 import checked_external
from scripts.run_heldout_quality_v30 import LABELS,POLICY,validate_selection
from src.compact_state import parse
from src.experiment_inventory import source_hashes
from src.run_store import canonical_json,digest
from src.service_terminal_evidence_v30 import verify_completed

require,hashed,read_json=common.require,common.hashed,common.read_json


def equal(a,b):return math.isclose(a,b,rel_tol=1e-13,abs_tol=1e-12)


def recompute(result,records):
    import numpy as np
    ids=[row['id'] for row in records]
    require(len(ids)==len(set(ids))==40 and set(result['quality'])==set(LABELS),'complete forty-article inventory differs')
    values={};tables={};totals={}
    for label in LABELS:
        rows=result['quality'][label];table={row['id']:row for row in rows}
        require(len(rows)==40 and set(table)==set(ids),'model article inventory differs')
        require(all(row['predictions']==127 and math.isfinite(row['nll_sum']) and row['nll_sum']>=0
            and equal(row['mean_nll'],row['nll_sum']/127) for row in rows),'invalid article losses or token counts')
        tables[label]=table;values[label]=np.array([table[rid]['nll_sum'] for rid in ids],dtype=np.float64)
        loss=float(values[label].sum());totals[label]=dict(nll_sum=loss,predictions=5080,mean_nll=loss/5080,perplexity=math.exp(loss/5080))
        require(result['summary']['totals'][label].keys()==totals[label].keys()
            and all(equal(result['summary']['totals'][label][key],value) for key,value in totals[label].items()),'saved aggregate loss differs')
    contrasts={}
    for reference in ('sequential128','nearest_rounding','full_precision'):
        differences=values['fixed128']-values[reference]
        ratios={rid:math.exp(float(value/127)) for rid,value in zip(ids,differences)}
        ratio=math.exp(float(differences.sum()/5080))
        expected=dict(perplexity_ratio=ratio,mean_nll_difference=float(differences.sum()/5080),
            article_perplexity_ratios=ratios,maximum_article_ratio=max(ratios.values()),
            article_wins=sum(value<1 for value in ratios.values()),article_losses=sum(value>1 for value in ratios.values()),
            primary=reference=='sequential128')
        saved=result['summary']['contrasts'][reference]
        require(set(saved)==set(expected),'comparison fields differ')
        for key,value in expected.items():
            if isinstance(value,dict):require(saved[key].keys()==value.keys() and all(equal(saved[key][rid],v) for rid,v in value.items()),'article ratio differs')
            elif isinstance(value,bool):require(saved[key] is value,'primary contrast changed')
            else:require(equal(saved[key],value),'paired contrast differs')
        contrasts[reference]=dict(expected,percent_change=100*(ratio-1))
    rng=np.random.default_rng(POLICY['bootstrap_seed'])
    draws=rng.integers(0,40,size=(POLICY['bootstrap_repetitions'],40))
    differences=values['fixed128']-values['sequential128']
    bootstrap_ratios=np.exp(differences[draws].sum(axis=1)/5080)
    upper=float(np.quantile(bootstrap_ratios,.95,method='linear'))
    require(equal(result['summary']['primary_bootstrap_upper_ratio'],upper),'one-sided bootstrap upper statistic differs')
    primary=contrasts['sequential128']
    guards=dict(bootstrap_upper_pass=upper<=1.05,aggregate_ratio_pass=primary['perplexity_ratio']<=1.05,
                per_article_ratio_pass=primary['maximum_article_ratio']<=1.20)
    require(result['summary']['guards']==guards and result['bounded_pool_confirmation_gate_pass'] is all(guards.values())
        and result['summary']['bounded_pool_confirmation_gate_pass'] is all(guards.values()),'reported quality guard differs')
    require(result['summary']['bootstrap']==dict(repetitions=20000,seed=20271008,unit='whole paired article',quantile=.95,
        method=POLICY['bootstrap_method'],interpretation='article-mixture stability guard for the fixed pool; no guaranteed population coverage'),
        'bootstrap interpretation or recipe differs')
    return dict(totals=totals,contrasts=contrasts,primary_bootstrap_upper_ratio=upper,guards=guards,
        bounded_pool_confirmation_gate_pass=all(guards.values()),
        per_article=[dict(id=rid,predictions=127,nll_sum={label:tables[label][rid]['nll_sum'] for label in LABELS},
            fixed_over_sequential=contrasts['sequential128']['article_perplexity_ratios'][rid],
            fixed_over_nearest=contrasts['nearest_rounding']['article_perplexity_ratios'][rid],
            fixed_over_full_precision=contrasts['full_precision']['article_perplexity_ratios'][rid]) for rid in ids])


def analyze(campaign):
    started=time.process_time_ns();campaign=Path(campaign).absolute();evidence={}
    def bind(path):
        path=Path(path).absolute();evidence[str(path)]=dict(sha256=hashed(path),bytes=path.stat().st_size)
    program,protocol,registration=[read_json(campaign/name) for name in ('program.json','protocol.json','registration.json')]
    ph,qh=hashed(campaign/'program.json'),hashed(campaign/'protocol.json')
    require(registration['program_sha256']==ph and registration['protocol_sha256']==qh and protocol['program_sha256']==ph,
            'registration binding differs')
    require(program['confirmation'] is True and program['phase_cpu_cap_seconds']==600
        and protocol['phase_cpu_seconds']=={'feasibility':600},'registered scope or budget differs')
    require(len(program['trials'])==1 and program['trials'][0]['id']=='quality-40'
        and program['trials'][0]['script']=='run_heldout_quality_v30.py','registered trial differs')
    require({p.name for p in (campaign/'attempts').iterdir() if p.is_dir()}=={'quality-40'},'extra or missing attempts')
    require(source_hashes(campaign/'source')==program['source_sha256'],'frozen numerical sources changed')
    for name,expected in program['controller_sha256'].items():
        require(hashed(campaign/'source'/name)==expected,'frozen controller source changed');bind(campaign/'source'/name)
    require(hashed(campaign/'registered-launcher.py')==program['controller_sha256']['scripts/launch_heldout_quality_v30.py'],
            'registered launcher changed')
    for name,expected in program['historical_frozen_ledgers'].items():
        require(hashed(ROOT/name)==expected,'earlier ledger changed');bind(ROOT/name)
    external=checked_external(program['external_attempts'],require_bindings=True)
    for entry in external.values():
        for name in entry['evidence']:bind(Path(entry['attempt'])/name)
    trial=program['trials'][0];attempt=campaign/'attempts/quality-40';result=verify_completed(attempt)
    plan=read_json(attempt/'plan.json');common.verify_plan(campaign,trial,plan,program,ph,qh,{})
    transaction,receipt,identity=[read_json(attempt/name) for name in ('transaction.json','worker/result.json','worker/identity.json')]
    common.verify_worker_schedule(campaign,trial,transaction,identity,registration,program)
    require(receipt['budget_debit']['reserved_cpu_seconds']==trial['cpu_seconds']+2,'reserved CPU differs')
    budget=common.verify_final_budget(campaign,program,qh,[receipt])
    require(result['schema']=='heldout-bounded-pool-quality-v30' and result['confirmation'] is True
        and result['scientific_promotion'] is False and result['population_coverage_claimed'] is False
        and result['model_outputs_frozen'] is True and result['nll_is_not_certified_interval'] is True
        and result['predictions_per_model']==5080 and result['policy']==POLICY,'scientific scope differs')
    inputs=plan['inputs'];selection=read_json(inputs['selection']['path']);pools=read_json(inputs['pools']['path'])
    development=read_json(inputs['development_registration']['path']);records=validate_selection(selection,pools,development)
    require(result['article_ids']==[row['id'] for row in records],'held-out article order differs')
    require(result['excluded_from_future_confirmation_ids']==selection['prospective_all_excluded_ids']
        and len(result['excluded_from_future_confirmation_ids'])==60,'complete sixty-document exclusions missing')
    for path,entry in selection['exposure_audit']['metadata_files'].items():
        require(hashed(path)==entry['sha256'] and Path(path).stat().st_size==entry['bytes'],'earlier exposure evidence changed');bind(path)
    previous=verify_completed(Path(inputs['development_completion']['path']).parent.parent)
    fixed=verify_completed(Path(inputs['fixed_completion']['path']).parent.parent)
    sequential=verify_completed(Path(inputs['sequential_completion']['path']).parent.parent)
    frozen=dict(fixed128=inputs['fixed_model']['sha256'],sequential128=inputs['sequential_model']['sha256'])
    require(frozen==selection['frozen_model_sha256']==result['provenance']['frozen_model_sha256'],'frozen model identities differ')
    require(frozen['fixed128']==previous['provenance']['new_model_sha256']==fixed['model_artifact']['sha256']
        and frozen['sequential128']==previous['provenance']['sequential128']['model_sha256']==sequential['model_artifact']['sha256'],
        'model identities differ from prospective development outputs')
    require(fixed['base_target_sha256']==sequential['sequential_target_sha256'],'matched target equation differs')
    a=parse(Path(inputs['fixed_model']['path']).read_bytes());b=parse(Path(inputs['sequential_model']['path']).read_bytes())
    require(a.target_sha256==fixed['fixed_target_sha256'] and b.target_sha256==sequential['sequential_target_sha256']
        and len(a.stages)==len(b.stages)==24 and not a.factors and not b.factors,'complete model targets differ')
    for x,y in zip(a.stages,b.stages):
        require((x.stage_id,x.shape,x.bits,x.grid_axis,x.scale_values)==(y.stage_id,y.shape,y.bits,y.grid_axis,y.scale_values),
                'matched four-bit grids differ')
    require(result['provenance']['selection_sha256']==inputs['selection']['sha256']
        and result['provenance']['development_completion_sha256']==inputs['development_completion']['sha256']
        and result['provenance']['quality_evaluator_sha256']==selection['quality_evaluator_sha256']
        ==previous['provenance']['shared_evaluator_sha256']==program['source_sha256']['scripts/run_quality_v30.py'],
        'evaluation provenance differs')
    stats=recompute(result,records)
    for name in ('program.json','protocol.json','registration.json','registered-launcher.py','phase-cpu-budget/ledger.json'):bind(campaign/name)
    for name in program['source_sha256']:bind(campaign/'source'/name)
    for path in attempt.rglob('*'):
        if path.is_file() and path.suffix in ('.json','.txt','.log'):bind(path)
    for entry in inputs.values():bind(entry['path'])
    sources=['scripts/analyze_heldout_quality_v30.py','scripts/analyze_full_service_v30.py','scripts/launch_heldout_quality_v30.py',
        'scripts/run_heldout_quality_v30.py','src/run_store.py','src/phase_budget.py','src/service_terminal_evidence_v30.py','src/compact_state.py']
    for name in sources:bind(ROOT/name)
    return dict(schema='heldout-bounded-pool-quality-audit-v30',status='complete_evidence_verified',model_inference=False,
        confirmation=True,confirmation_scope=POLICY['confirmation_scope'],population_coverage_claimed=False,
        scientific_promotion=False,program_sha256=ph,protocol_sha256=qh,
        completion_sha256=hashed(attempt/'outputs/completion.json'),frozen_model_sha256=frozen,
        prior_excluded_ids=selection['prior_excluded_ids'],newly_excluded_ids=[row['id'] for row in records],
        excluded_from_future_confirmation_ids=selection['prospective_all_excluded_ids'],
        phase_budget=budget,controller_seconds=transaction['controller_elapsed_ns']/1e9,
        observed_cpu_seconds=receipt['resource_usage']['total_cpu_ns']/1e9,charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],
        peak_rss_bytes=result['peak_rss_bytes'],evidence_sha256=evidence,
        analysis_source_sha256={name:hashed(ROOT/name) for name in sources},analysis_cpu_ns=time.process_time_ns()-started,**stats)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--campaign',type=Path,default=ROOT/'campaigns/heldout_quality_v30')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--exclusions',type=Path,required=True)
    args=parser.parse_args();report=analyze(args.campaign)
    with args.output.open('xb') as stream:stream.write(canonical_json(report))
    exclusions=dict(schema='quality-confirmation-exclusions-v30',prior_excluded_ids=report['prior_excluded_ids'],
        newly_excluded_ids=report['newly_excluded_ids'],excluded_from_future_confirmation_ids=report['excluded_from_future_confirmation_ids'],
        reason='prospectively designated held-out phase; excluded regardless of passing or failing quality guards',
        completion_sha256=report['completion_sha256'],audit_sha256=hashed(args.output),historical_twenty_article_registration_unchanged=True)
    with args.exclusions.open('xb') as stream:stream.write(canonical_json(exclusions))
    print(json.dumps(dict(status=report['status'],guards=report['guards'],primary_ratio=report['contrasts']['sequential128']['perplexity_ratio'],
        bootstrap_upper=report['primary_bootstrap_upper_ratio'],exclusions=60,audit_sha256=hashed(args.output),
        exclusions_sha256=hashed(args.exclusions),analysis_cpu_ns=report['analysis_cpu_ns'])))
