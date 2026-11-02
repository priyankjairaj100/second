"""Generated arithmetic/refusal probes; no empirical data or success claim."""
from copy import deepcopy
from pathlib import Path
import datetime, hashlib, json, platform, subprocess, sys, tempfile
from research_v68.quality_statistics import summarize, MODELS
from validation.check_v71_completed_losses import arithmetic, obj
from validation.check_v71_campaign_metadata import load,check
R=Path(__file__).resolve().parents[1]
def fixture(delta):
    rows=[]
    for i in range(320):
        sums={m:127*(2+(i%11)/20) for m in MODELS}
        sums['candidate_12']+=127*(delta+(i%7-3)/10000)
        sums['candidate_6']+=127*(delta/2+(i%5-2)/10000)
        rows.append(dict(id=f'generated-{i:04d}',predictions=127,
            losses={m:dict(sum_nll=v,mean_nll=v/127) for m,v in sums.items()}))
    return rows
results=[]
for delta in (.001,.15):
    rows=fixture(delta);summary=summarize(rows);endpoints=arithmetic(rows,summary)
    assert all(x['gate_pass'] for x in endpoints.values()) is (delta==.001)
    results.append(dict(generated_delta=delta,observed_joint_gate=delta==.001))
rows=fixture(.001);summary=summarize(rows)
mutations={
 'reordered_articles':lambda r,s:r.reverse(),
 'wrong_prediction_count':lambda r,s:r[0].update(predictions=126),
 'omitted_model':lambda r,s:r[0]['losses'].pop('original'),
 'altered_pooled_mean':lambda r,s:s['models']['original'].update(mean_nll=99),
 'altered_paired_difference':lambda r,s:s['endpoints']['12']['article_paired_mean_nll'][0].update(difference=99),
 'altered_maximum':lambda r,s:s['endpoints']['6'].update(log_maximum_article_ratio=99),
 'altered_bootstrap_decision':lambda r,s:s['endpoints']['12'].update(uncertainty_guard_pass=False),
 'altered_joint_gate':lambda r,s:s.update(all_endpoint_gates_pass=False)}
rejected=[]
for name,mutate in mutations.items():
    r,s=deepcopy(rows),deepcopy(summary);mutate(r,s)
    try:arithmetic(r,s)
    except (AssertionError,KeyError,ValueError):rejected.append(name)
    else:raise AssertionError('Mutation unexpectedly accepted: '+name)
for name,raw in [('duplicate_json',b'{"x":1,"x":2}'),('nonfinite_json',b'{"x":NaN}')]:
    try:obj(raw)
    except (AssertionError,ValueError):rejected.append(name)
    else:raise AssertionError('Invalid JSON accepted')
latest=check(load(R/'campaigns/csis_v71_metadata_20261018_f.tar.gz'))
assert latest['terminal_quality_result_verified'] is False
with tempfile.TemporaryDirectory() as temp:
    output=Path(temp)/'must-not-exist.json'
    process=subprocess.run([sys.executable,'-m','validation.check_v71_completed_losses',
        'csis_v71_metadata_20261018_f.tar.gz','nonexistent-losses.tar.gz',str(output)],
        cwd=R,capture_output=True,text=True)
    assert process.returncode!=0 and 'Actual complete terminal/cost audit required first' in process.stderr
    assert not output.exists()
rejected.append('pending_terminal_metadata')
files=['validation/collect_v71_completed_losses.py','validation/check_v71_completed_losses.py',
       'validation/check_v71_loss_reporting_preparation.py']
report=dict(schema='v71-saved-loss-reporting-preparation',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 status='generated_arithmetic_and_refusal_checks_passed',generated_examples=results,rejected_probes=rejected,
 actual_terminal_success_path_exercised=False,actual_loss_files_collected=False,actual_quality_result=False,
 pending_snapshot_refused_as_final=True,registered_sources_changed=False,python_version=platform.python_version(),
 scope='Preparatory reporting-only checks; no registered job, neural evaluation or actual complete loss bundle executed.',
 sources={n:dict(bytes=(R/n).stat().st_size,sha256=hashlib.sha256((R/n).read_bytes()).hexdigest()) for n in files})
p=R/'validation/v71_loss_reporting_preparation.json'
with p.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({k:report[k] for k in ['status','rejected_probes','actual_terminal_success_path_exercised','actual_quality_result']}))
