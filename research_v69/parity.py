"""Six-model binary64 parity on a fixed four-article subset; no inference here."""
import math
from research_v68.quality_statistics import MODELS
from research_v67.io import require
PARITY_ARTICLES=4
PREDICTIONS=127
TOLERANCE=1e-8


def compare(observed,reference,ids):
    require(type(ids) is list and len(ids)==PARITY_ARTICLES and ids==sorted(set(ids))
        and all(type(i) is str and i for i in ids),'Four fixed distinct sorted parity articles required')
    require(set(observed)==set(reference)==set(MODELS),'All six actual models required')
    checks=[]
    for label in MODELS:
        tables=[]
        for source in [observed,reference]:
            rows=source[label]
            require(type(rows) is list and len(rows)==len(ids) and [r['id'] for r in rows]==ids,'Complete ordered parity article rows required')
            for row in rows:
                require(type(row['predictions']) is int and row['predictions']==PREDICTIONS
                    and type(row['nll_sum']) in (int,float) and math.isfinite(row['nll_sum']) and row['nll_sum']>=0
                    and type(row['mean_nll']) in (int,float) and math.isfinite(row['mean_nll'])
                    and abs(row['mean_nll']-row['nll_sum']/PREDICTIONS)<=1e-12,'Invalid actual loss or prediction count')
            tables.append(rows)
        for current,old in zip(*tables):
            delta=abs(current['nll_sum']-old['nll_sum'])/PREDICTIONS
            checks.append(dict(model=label,id=current['id'],absolute_mean_nll_deviation=delta,
                threshold=TOLERANCE,passed=delta<=TOLERANCE))
    return dict(passed=all(c['passed'] for c in checks),checks=checks,
        maximum_absolute_mean_nll_deviation=max(c['absolute_mean_nll_deviation'] for c in checks),
        actual_parameter_artifact_binding_performed=False,
        scope='Twenty-four paired likelihood values only; caller must audit actual model/data/runtime bindings')
