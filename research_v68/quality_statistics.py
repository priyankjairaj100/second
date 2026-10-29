"""Paired article-level quality statistics; no model loading or inference.

Unregistered preparation. An outer artifact audit must bind actual model bytes,
article selection, and raw evaluator losses before these statistics are evidence.
"""
import math
import numpy as np

MODELS=('original','nearest','candidate_12','sequential_12','candidate_6','sequential_6')
ENDPOINTS=(12,6)
SAMPLE=320
PREDICTIONS=127
DRAWS=20_000
# Fixed before any untouched frame or loss is acquired; PCG64, not global RNG.
SEED=int.from_bytes(b'second-quality68','big')
POOLED_LIMIT=1.05
TAIL_LIMIT=1.20


def require(condition,message):
    if not condition:raise ValueError(message)


def finite_number(value):
    return type(value) in (int,float) and math.isfinite(value)


def safe_exp(value):
    """Keep valid adverse log evidence even when its exponential overflows."""
    return math.exp(value) if value<=math.log(np.finfo(np.float64).max) else None


def validate(rows,expected_articles=SAMPLE,expected_predictions=PREDICTIONS):
    require(type(rows) is list and len(rows)==expected_articles,'Exact registered article count required')
    require(type(expected_articles) is int and expected_articles>=2,'At least two article units required')
    ids=[];nll=[];counts=[]
    for r in rows:
        require(type(r) is dict and set(r)=={'id','predictions','losses'},'Exact article schema required')
        require(type(r['id']) is str and r['id'] and r['id'] not in ids,'Distinct identified article units required')
        require(type(r['predictions']) is int and r['predictions']==expected_predictions>0,'Registered prediction count required')
        require(type(r['losses']) is dict and set(r['losses'])==set(MODELS),'All six matched model losses required')
        sums=[]
        for model in MODELS:
            e=r['losses'][model]
            require(type(e) is dict and set(e)=={'sum_nll','mean_nll'},'Both raw sum and mean NLL required')
            require(all(finite_number(e[k]) and e[k]>=0 for k in e),'Nonfinite/negative NLL refused')
            require(math.isclose(e['mean_nll'],e['sum_nll']/r['predictions'],rel_tol=1e-12,abs_tol=1e-12),'Loss sum/mean mismatch')
            sums.append(float(e['sum_nll']))
        ids.append(r['id']);counts.append(r['predictions']);nll.append(sums)
    require(ids==sorted(ids),'Canonical article order required')
    return ids,np.asarray(counts,dtype=np.int64),np.asarray(nll,dtype=np.float64)


def summarize(rows,*,expected_articles=SAMPLE,expected_predictions=PREDICTIONS,draws=DRAWS,seed=SEED):
    ids,counts,sums=validate(rows,expected_articles,expected_predictions)
    require(type(draws) is int and draws>=20,'Explicit bootstrap draw count required')
    require(type(seed) is int and 0<=seed<2**128,'Fixed unsigned128bit seed required')
    total=int(counts.sum());indices={m:i for i,m in enumerate(MODELS)}
    paired=np.column_stack([sums[:,indices['candidate_'+str(e)]]-sums[:,indices['sequential_'+str(e)]] for e in ENDPOINTS])
    article=paired/counts[:,None]
    pooled=np.asarray([math.fsum(float(v) for v in paired[:,j])/total for j in range(2)])
    # Whole article indices are shared by both endpoints. All model losses travel
    # together conceptually; controls do not affect the paired differences.
    rng=np.random.Generator(np.random.PCG64(seed));boot=np.empty((draws,2),dtype=np.float64)
    for start in range(0,draws,256):
        stop=min(draws,start+256);sample=rng.integers(0,len(ids),size=(stop-start,len(ids)),dtype=np.int64)
        boot[start:stop]=paired[sample].sum(axis=1)/counts[sample].sum(axis=1)[:,None]
    require(np.isfinite(boot).all(),'Bootstrap arithmetic overflow refused')
    endpoints={}
    for j,e in enumerate(ENDPOINTS):
        quantiles=np.quantile(boot[:,j],[.025,.975],method='higher')
        upper=float(quantiles[1]);maximum=float(article[:,j].max());observed=float(pooled[j])
        endpoints[str(e)]=dict(log_pooled_ratio=observed,pooled_ratio=safe_exp(observed),
            log_two_sided_95_percentile_interval=[float(x) for x in quantiles],
            two_sided_95_percentile_interval=[safe_exp(float(x)) for x in quantiles],
            log_one_sided_97_5_upper=upper,one_sided_97_5_upper=safe_exp(upper),
            log_maximum_article_ratio=maximum,maximum_article_ratio=safe_exp(maximum),
            article_paired_mean_nll=[dict(id=ids[i],difference=float(article[i,j])) for i in range(len(ids))],
            article_difference_quantiles={str(q):float(v) for q,v in zip([0,.25,.5,.75,1],np.quantile(article[:,j],[0,.25,.5,.75,1],method='higher'))},
            observed_pooled_guard_pass=observed<=math.log(POOLED_LIMIT),
            uncertainty_guard_pass=upper<=math.log(POOLED_LIMIT),
            observed_maximum_guard_pass=maximum<=math.log(TAIL_LIMIT))
        endpoints[str(e)]['gate_pass']=all(endpoints[str(e)][k] for k in ['observed_pooled_guard_pass','uncertainty_guard_pass','observed_maximum_guard_pass'])
    models={}
    for model,col in indices.items():
        mean=math.fsum(float(x) for x in sums[:,col])/total
        models[model]=dict(mean_nll=mean,perplexity=safe_exp(mean))
    return dict(schema='prospective-paired-quality-statistics-v68',articles=len(ids),predictions_per_model=total,
        models=models,endpoints=endpoints,all_endpoint_gates_pass=all(r['gate_pass'] for r in endpoints.values()),
        bootstrap=dict(draws=draws,seed=seed,bit_generator='PCG64',article_pairing_shared=True,
            quantile_method='higher',numpy_version=np.__version__,familywise_nominal_alpha=.05,primary_endpoints=2),
        interpretation='Approximate paired article bootstrap on the admitted bounded frame; no population-tail or generalization guarantee.',
        actual_loss_artifact_validation_performed=False,exponential_overflow_reported_as_null=True)
