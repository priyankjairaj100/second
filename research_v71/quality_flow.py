"""One-use loss collection and parity barrier; no standalone launch entry.

The admitted worker must supply verified model factories, runtime/resource gates
and actual audited artifacts. Tests supply fake factories and generated tokens.
"""
from pathlib import Path
import math,time
from research_v67.io import require,write,info
from research_v68 import quality_statistics as stats
from research_v71 import parity
from src.run_store import canonical_json


def records_check(records):
    require(type(records) is list and len(records)==stats.SAMPLE,'Exactly320 admitted articles required')
    require(all(type(r) is dict and set(r)=={'id','tokens'} and type(r['id']) is str and r['id']
        and type(r['tokens']) is list and len(r['tokens'])==128
        and all(type(t) is int and 0<=t<50257 for t in r['tokens']) for r in records),'Actual record schema/vocabulary differs')
    ids=[r['id'] for r in records];require(ids==sorted(set(ids)),'Canonical distinct article IDs required')
    return info(canonical_json(dict(records=records)))


def collect(mode,records,model_factory,model_bindings,out,*,registration_sha256,cpu_reference=None):
    """Collect CPU parity or full GPU losses exactly once; preserve failures."""
    require(mode in ['cpu_parity','gpu_quality'],'Unknown quality phase')
    require(type(registration_sha256) is str and len(registration_sha256)==64
        and all(c in '0123456789abcdef' for c in registration_sha256),'Actual registration commitment required')
    record_info=records_check(records)
    require(type(model_bindings) is dict and set(model_bindings)==set(stats.MODELS)
        and all(type(v) is dict and v for v in model_bindings.values()),'Complete six-model artifact bindings required')
    out=Path(out).absolute();require(not any(p.is_symlink() for p in (out,*out.parents)),'Nonsymbolic output path required')
    out.mkdir(exist_ok=False);start=time.perf_counter_ns();events=0
    result=dict(schema='untouched-quality-collection-v71',mode=mode,status='running',
        registration_sha256=registration_sha256,records=record_info,model_bindings=model_bindings,
        quality={m:[] for m in stats.MODELS},parity=None,summary=None,error=None,active_model=None,active_article=None,
        actual_source_runtime_resource_admission_required_of_caller=True,
        collected_losses_independently_reexecuted=False)
    def mark(phase,**fields):
        nonlocal events
        write(out/f'progress-{events:04d}.json',dict(phase=phase,elapsed_ns=time.perf_counter_ns()-start,**fields));events+=1
    def evaluate(indices):
        for model in stats.MODELS:
            result['active_model']=model
            with model_factory(model) as evaluator:
                require(evaluator.binding==model_bindings[model],'Installed model binding differs before inference')
                mark('model_ready',model=model)
                for index in indices:
                    record=records[index];result['active_article']=dict(model=model,index=index,id=record['id'])
                    tick=time.perf_counter_ns();loss=evaluator.nll(record['tokens'])
                    require(type(loss) in (int,float) and math.isfinite(loss) and loss>=0,'Invalid actual likelihood')
                    row=dict(id=record['id'],predictions=127,nll_sum=float(loss),mean_nll=float(loss)/127)
                    require(len(result['quality'][model])==index,'Article cannot be repeated or skipped')
                    write(out/f'loss-{model}-{index:04d}.json',dict(model=model,index=index,elapsed_ns=time.perf_counter_ns()-tick,**row))
                    result['quality'][model].append(row)
                    mark('article_complete',model=model,index=index,id=record['id'])
                    result['active_article']=None
            result['active_model']=None
    try:
        mark('started',mode=mode)
        ids=[r['id'] for r in records[:parity.PARITY_ARTICLES]]
        if mode=='gpu_quality':
            require(type(cpu_reference) is dict and cpu_reference['schema']==result['schema']
                and cpu_reference['mode']=='cpu_parity' and cpu_reference['status']=='complete'
                and cpu_reference['error'] is None and cpu_reference['registration_sha256']==registration_sha256
                and cpu_reference['records']==record_info and cpu_reference['model_bindings']==model_bindings,
                'Complete bound CPU parity reference required')
            parity.compare(cpu_reference['quality'],cpu_reference['quality'],ids)
        else:require(cpu_reference is None,'CPU parity cannot consume another likelihood result')
        evaluate(range(parity.PARITY_ARTICLES))
        if mode=='gpu_quality':
            result['parity']=parity.compare(result['quality'],cpu_reference['quality'],ids)
            write(out/'parity.json',result['parity'])
            require(result['parity']['passed'],'All24 CPU/GPU parity pairs must pass before remaining losses')
            mark('all_six_models_passed_parity',comparisons=24)
            evaluate(range(parity.PARITY_ARTICLES,stats.SAMPLE))
            rows=[dict(id=r['id'],predictions=127,losses={m:dict(sum_nll=result['quality'][m][i]['nll_sum'],
                mean_nll=result['quality'][m][i]['mean_nll']) for m in stats.MODELS}) for i,r in enumerate(records)]
            write(out/'paired-losses.json',dict(rows=rows))
            result['summary']=stats.summarize(rows)
            # A valid adverse quality result is complete, never a retry trigger.
            write(out/'statistics.json',result['summary'])
        result['status']='complete'
    except BaseException as exc:
        result['status']='failed';result['error']=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        result.update(elapsed_ns=time.perf_counter_ns()-start,progress_events=events,
            completed_article_evaluations=sum(len(v) for v in result['quality'].values()),
            partial_losses_retained=result['status']!='complete')
        write(out/'completion.json',result)
    return result
