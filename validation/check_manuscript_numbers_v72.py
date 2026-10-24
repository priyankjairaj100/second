"""Bind manuscript quality statements to saved, separately audited actual losses."""
from pathlib import Path
import datetime,hashlib,json,re
from validation.check_manuscript_numbers_v70 import check as old,norm,R

def check(text):
    checks=old(text)
    assert sum(c['name']=='untouched_quality_not_inferred' for c in checks)==1
    checks=[c for c in checks if c['name']!='untouched_quality_not_inferred']
    p=R/'reports/review-quality-v72'
    stats=json.loads((p/'E17_statistics.json').read_bytes());s=json.loads((p/'E17_summary.json').read_bytes())
    assert s['quality_guard_pass'] and s['original_closure_failed'] and stats['all_endpoint_gates_pass']
    body=text.split(r'\paragraph{Untouched two-endpoint quality (V71/V72).}')[1].split(r'\paragraph{Research decision.}')[0]
    abstract=text.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0]
    def passage(name,expected,scope=body):
        checks.append(dict(name=name,expected_text=expected,passed=norm(expected) in norm(scope),sources=['E17_statistics.json','E17_summary.json']))
    for e,v in stats['endpoints'].items():
        passage('quality_table_'+e,f"{e} & {v['pooled_ratio']:.6f} & {v['one_sided_97_5_upper']:.6f} & {v['maximum_article_ratio']:.6f}")
        passage('quality_interval_'+e,'['+', '.join(f'{x:.6f}' for x in v['two_sided_95_percentile_interval'])+']')
    for role,v in stats['models'].items():passage('quality_ppl_'+role,f"{v['perplexity']:.4f}")
    for name,phrase in {
        'articles':f"on {s['articles']} articles",'frame':f"frame of {s['sample_frame_complete_records']:,} complete records",
        'eligible':f"from {s['eligible_records']:,} eligible records",'predictions':f"{s['predictions_per_article']} predictions from a 128-token sequence",
        'bootstrap':f"{s['bootstrap_draws']:,} draws shared",'upper':'one-sided 97.5\\%',
        'pooled_guard':f"upper bounds must be at most {s['pooled_guard']:.2f}",
        'max_guard':f"at most {s['observed_maximum_guard']:.2f}",'familywise':'nominal familywise level of 95\\%',
        'gpu_count':f"all {s['actual_gpu_losses']:,} GPU and {s['actual_cpu_losses']} CPU losses",
        'parity':r'$1.155\times10^{-14}$','worker_cpu':f"workers charge {s['numerical_worker_charged_cpu_seconds']:,} CPU seconds",
        'scheduler_cpu':f"{s['combined_scheduler_cpu_ns']/1e9:,.3f} scheduler CPU seconds",
        'adverse_interpretation':'a small quality cost, not an improvement','failed_accounting':'A final accounting job failed',
        'recovery_no_inference':'without repeating inference','evidence':r'\evidence{E17}',
    }.items():passage('quality_'+name,phrase)
    a,b=[100*(stats['endpoints'][e]['pooled_ratio']-1) for e in ['12','6']]
    passage('abstract_quality_cost',f'{a:.2f}\\% and {b:.2f}\\%',abstract)
    # Retain the mathematical claims and proofs exactly; new results do not license new theory.
    oldtext=(R/'reports/manuscript_v70.tex').read_text()
    for env in ['theorem','proof','equation','align','lemma','proposition']:
        pattern=r'\\begin\{'+env+r'\*?\}.*?\\end\{'+env+r'\*?\}'
        prior=re.findall(pattern,oldtext,re.S);current=re.findall(pattern,text,re.S)
        checks.append(dict(name='unchanged_'+env+'_environments',passed=prior==current,count=len(prior),sources=['manuscript_v70.tex']))
    return checks
if __name__=='__main__':
    text=(R/'reports/manuscript_v72.tex').read_text();checks=check(text)
    probes={}
    for a,b in [('1.005421','1.005422'),('1.011431','1.011430'),('7,588.049','7,588.048'),('60.1053','60.1054'),('9.24\\%','9.25\\%')]:
        altered=text.replace(a,b);probes[a]=altered!=text and any(not c['passed'] for c in check(altered))
    result=dict(status='passed' if all(c['passed'] for c in checks) and all(probes.values()) else 'failed',check_count=len(checks),checks=checks,
        failed_checks=[c['name'] for c in checks if not c['passed']],tamper_probes=probes,manuscript_sha256=hashlib.sha256(text.encode()).hexdigest(),
        empirical_execution=False,old_pending_quality_check_replaced_explicitly=True)
    with (R/'validation/v72_manuscript_numbers.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print({k:result[k] for k in ['status','check_count','failed_checks','tamper_probes']});assert result['status']=='passed'
