"""Offline scalar arithmetic only; no neural or bootstrap reexecution."""
from pathlib import Path
import json,math
MODELS=('original','nearest','candidate_12','sequential_12','candidate_6','sequential_6')
def arithmetic(rows,summary):
    assert len(rows)==320 and [r['id'] for r in rows]==sorted({r['id'] for r in rows})
    for row in rows:
        assert set(row)=={'id','predictions','losses'} and type(row['predictions']) is int and row['predictions']==127
        assert set(row['losses'])==set(MODELS)
        for loss in row['losses'].values():
            assert set(loss)=={'sum_nll','mean_nll'}
            assert all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in loss.values())
            assert loss['mean_nll']==loss['sum_nll']/127
    assert summary['articles']==320 and summary['predictions_per_model']==40640
    for model in MODELS:
        mean=math.fsum(float(row['losses'][model]['sum_nll']) for row in rows)/40640
        assert mean==summary['models'][model]['mean_nll'], 'Pooled model NLL differs'
    endpoints={}
    for endpoint in (12,6):
        differences=[float(row['losses']['candidate_'+str(endpoint)]['sum_nll'])-
                     float(row['losses']['sequential_'+str(endpoint)]['sum_nll']) for row in rows]
        paired=[v/127 for v in differences]; pooled=math.fsum(differences)/40640; maximum=max(paired)
        observed=summary['endpoints'][str(endpoint)]
        assert pooled==observed['log_pooled_ratio'] and maximum==observed['log_maximum_article_ratio']
        assert observed['article_paired_mean_nll']==[dict(id=r['id'],difference=d) for r,d in zip(rows,paired)]
        pooled_pass=pooled<=math.log(1.05);maximum_pass=maximum<=math.log(1.20)
        assert observed['observed_pooled_guard_pass'] is pooled_pass
        assert observed['observed_maximum_guard_pass'] is maximum_pass
        # Reevaluate the frozen threshold on the reported upper bound; no bootstrap is claimed here.
        uncertainty_pass=observed['log_one_sided_97_5_upper']<=math.log(1.05)
        assert observed['uncertainty_guard_pass'] is uncertainty_pass
        gate=pooled_pass and maximum_pass and uncertainty_pass
        assert observed['gate_pass'] is gate
        endpoints[str(endpoint)]=dict(log_pooled_ratio=pooled,log_maximum_article_ratio=maximum,
            observed_pooled_guard_pass=pooled_pass,observed_maximum_guard_pass=maximum_pass,
            reported_bootstrap_upper_guard_pass=uncertainty_pass,gate_pass=gate)
    assert summary['all_endpoint_gates_pass'] is all(e['gate_pass'] for e in endpoints.values())
    return endpoints

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    rows=json.loads((root/'E17_paired_losses.json').read_text())['rows']
    stats=json.loads((root/'E17_statistics.json').read_text())
    result=arithmetic(rows,stats)
    print(json.dumps(dict(status='saved_scalar_arithmetic_verified',endpoints=result,bootstrap_reexecuted=False,neural_inference_reexecuted=False),sort_keys=True))
