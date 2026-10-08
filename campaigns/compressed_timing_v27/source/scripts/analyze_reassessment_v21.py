"""Recompute the v20/v21 conclusions from immutable worker evidence."""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.experiment_inventory import source_hashes
from src.pilot_budget import inherited_allowance
from src.run_store import canonical_json


def main():
    root=Path(__file__).resolve().parents[1]
    def read(path):return json.loads((root/path).read_bytes())
    def sha(path):return hashlib.sha256((root/path).read_bytes()).hexdigest()
    evidence={}
    def verified_attempt(path, complete=True):
        plan=read(path+'/plan.json')
        receipt=read(path+'/worker/result.json')
        assert receipt['budget_debit']['state']=='settled'
        assert receipt['worker_identity']['plan_sha256']==sha(path+'/plan.json')
        assert source_hashes(root/path/'source')==plan['source_sha256']
        if complete:assert receipt['outcome']['status']=='complete'
        evidence[path]=dict(receipt_sha256=sha(path+'/worker/result.json'),
            plan_sha256=sha(path+'/plan.json'),outcome=receipt['outcome'],
            charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'])
        if complete:
            progress=read(path+'/outputs/progress.json')
            assert progress['status']=='complete'
            assert progress['plan_sha256']==sha(path+'/plan.json')
            evidence[path]['progress_sha256']=sha(path+'/outputs/progress.json')
            return progress
    verified_attempt('pilots/v20/attempt-001',complete=False)
    bound=verified_attempt('pilots/v20/attempt-002')
    quality=verified_attempt('pilots/v21/attempt-001')
    witness=next(c for c in bound['cells'] if c['name']=='endpoint_witness')
    assert witness['changed_codes']==252 and witness['compared_values']==12288
    values=quality['quality']
    fixed={x['id']:x for x in values['fixed_anchor_calibrated']}
    seq={x['id']:x for x in values['archived_sequential_calibrated']}
    assert set(fixed)==set(seq) and len(fixed)==2
    assert all(x['predictions']==15 for group in (fixed,seq) for x in group.values())
    ratios={k:math.exp((fixed[k]['nll_sum']-seq[k]['nll_sum'])/15) for k in fixed}
    aggregate=math.exp(sum(fixed[k]['nll_sum']-seq[k]['nll_sum'] for k in fixed)/30)
    assert ratios==quality['per_article_ratios']
    assert aggregate==quality['perplexity_ratio_to_sequential']
    program=read('pilots/v21/attempt-001/program.json')
    gate=program['gate']
    passed=(aggregate<=gate['max_aggregate_perplexity_ratio_to_sequential']
            and max(ratios.values())<=gate['max_each_article_ratio'])
    assert passed==quality['quality_pilot_pass']
    assert quality['fixed_target_sha256']!=quality['base_target_sha256']
    assert len(quality['diagnostics']['stages'])==24
    assert quality['complete_new_target_state'] and quality['complete_new_target_model']
    for label in ('model','state'):
        artifact=quality[label+'_artifact']
        path='pilots/v21/attempt-001/outputs/'+artifact['file']
        assert sha(path)==artifact['sha256'] and (root/path).stat().st_size==artifact['bytes']
    charged,left=inherited_allowance(root)
    phases=quality['phases']
    construction=next(x['elapsed_ns'] for x in phases if x['phase']=='model_constructed')
    first=next(x['elapsed_ns'] for x in phases if x['phase']=='quality_record_started')
    summary=dict(schema='reevaluation-verification-v21',evidence=evidence,
        original_sequential_speedup_established=False,
        anchor_centered_witness=dict(changed_codes=252,compared_values=12288,
            scope='checked stage and record; any constant-output set containing both endpoints fails'),
        explicit_changed_target=True,quality_pilot_pass=passed,
        perplexity_ratio_to_sequential=aggregate,per_article_ratios=ratios,
        predictions_per_model=30,confirmation=False,repair_timing=False,
        scientific_program_complete=False,novelty_established=False,
        fixed_target_sha256=quality['fixed_target_sha256'],
        base_target_sha256=quality['base_target_sha256'],
        model_sha256=quality['model_sha256'],model_artifact=quality['model_artifact'],
        state_artifact=quality['state_artifact'],
        archived_preparation_elapsed_ns=quality['diagnostics']['external_preparation_elapsed_ns'],
        model_to_first_evaluation_setup_elapsed_ns=first-construction,
        setup_scope='comparator parsing, compact code conversion, and both evaluator constructions',
        quality_exclusions=quality['excluded_from_future_confirmation_ids'],
        charged_cpu_seconds=charged,remaining_cpu_seconds=left,
        cap_cpu_seconds=10800,no_budget_reset=True)
    (root/'pilots/v21/summary.json').write_bytes(canonical_json(summary))
    print(json.dumps(dict(verified=True,quality_pilot_pass=passed,ratio=aggregate,
                         remaining_cpu_seconds=left)))


if __name__=='__main__':main()
