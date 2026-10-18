"""Read actual saved loss rows, parity barrier and statistics without inference."""
from pathlib import Path
from research_v67.io import read,require,info
from research_v71 import quality_flow as flow,parity
from research_v68 import quality_statistics as stats
from src.run_store import canonical_json,strict_json


def audit(directory,records,model_bindings,*,registration_sha256,cpu_directory=None,
          expected_statistics_numpy_version=None):
    directory=Path(directory);inputs={}
    def obj(name):
        raw=read(directory/name,maximum=8*2**20);value=strict_json(raw)
        require(type(value) is dict and canonical_json(value)==raw,'Canonical saved loss metadata required')
        inputs[name]=info(raw);return value
    c=obj('completion.json');mode=c['mode'];require(mode in ['cpu_parity','gpu_quality'],'Recognized complete quality phase required')
    require(c['schema']=='untouched-quality-collection-v71' and c['status']=='complete' and c['error'] is None
        and c['registration_sha256']==registration_sha256 and c['model_bindings']==model_bindings
        and c['records']==flow.records_check(records) and c['active_model'] is None and c['active_article'] is None
        and c['partial_losses_retained'] is False,'Complete bound collection receipt required')
    require(all(type(c[k]) is int and c[k]>=0 for k in ['progress_events','elapsed_ns','completed_article_evaluations']), 'Nonnegative integral receipt counts/clocks required')
    count=parity.PARITY_ARTICLES if mode=='cpu_parity' else stats.SAMPLE
    quality={m:[] for m in stats.MODELS};expected_names={'completion.json'}
    for model in stats.MODELS:
        for index in range(count):
            name=f'loss-{model}-{index:04d}.json';actual=obj(name);expected_names.add(name)
            require(set(actual)=={'model','index','elapsed_ns','id','predictions','nll_sum','mean_nll'}
                and actual['model']==model and actual['index']==index and actual['id']==records[index]['id']
                and type(actual['predictions']) is int and actual['predictions']==127
                and type(actual['elapsed_ns']) is int and actual['elapsed_ns']>=0,'Saved actual model/article loss binding differs')
            quality[model].append({k:actual[k] for k in ['id','predictions','nll_sum','mean_nll']})
    require(quality==c['quality'] and c['completed_article_evaluations']==len(stats.MODELS)*count,'Completion differs from actual saved loss rows')
    events=[dict(phase='started',mode=mode)]
    def extend(indices):
        for model in stats.MODELS:
            events.append(dict(phase='model_ready',model=model))
            events.extend(dict(phase='article_complete',model=model,index=i,id=records[i]['id']) for i in indices)
    extend(range(parity.PARITY_ARTICLES));ids=[r['id'] for r in records[:parity.PARITY_ARTICLES]]
    subset={m:rows[:parity.PARITY_ARTICLES] for m,rows in quality.items()}
    if mode=='cpu_parity':
        parity.compare(subset,subset,ids)
        require(c['parity'] is None and c['summary'] is None and cpu_directory is None
            and expected_statistics_numpy_version is None,'CPU parity cannot claim full quality')
    else:
        require(cpu_directory is not None and Path(cpu_directory).absolute()!=directory.absolute(),'Separate actual CPU loss artifacts required')
        cpu_report=audit(cpu_directory,records,model_bindings,registration_sha256=registration_sha256)
        cpu_reference=strict_json(read(Path(cpu_directory)/'completion.json',cpu_report['artifacts']['completion.json'],maximum=8*2**20))
        require(type(cpu_reference) is dict and cpu_reference['status']=='complete' and cpu_reference['mode']=='cpu_parity'
            and cpu_reference['registration_sha256']==registration_sha256 and cpu_reference['records']==c['records']
            and cpu_reference['model_bindings']==model_bindings and cpu_reference['error'] is None,'Audited bound CPU reference required')
        p=parity.compare(subset,cpu_reference['quality'],ids)
        require(p['passed'] and p==c['parity']==obj('parity.json'),'Actual parity rows or barrier differ')
        events.append(dict(phase='all_six_models_passed_parity',comparisons=24));extend(range(parity.PARITY_ARTICLES,stats.SAMPLE))
        rows=[dict(id=r['id'],predictions=127,losses={m:dict(sum_nll=quality[m][i]['nll_sum'],mean_nll=quality[m][i]['mean_nll']) for m in stats.MODELS}) for i,r in enumerate(records)]
        require(obj('paired-losses.json')==dict(rows=rows),'Paired loss artifact differs from actual article files')
        summary=stats.summarize(rows);recomputation_numpy_version=summary['bootstrap']['numpy_version']
        observed=obj('statistics.json')
        require(type(expected_statistics_numpy_version) is str and expected_statistics_numpy_version
            and observed['bootstrap']['numpy_version']==expected_statistics_numpy_version,
            'Statistics runtime must match the prospectively bound GPU NumPy version')
        # Version provenance differs from numerical equality. Keep both versions;
        # every recomputed number and decision must still match exactly.
        summary['bootstrap']['numpy_version']=expected_statistics_numpy_version
        require(summary==c['summary']==observed,'Reported quality/statistics differ from actual losses')
        expected_names|={'parity.json','paired-losses.json','statistics.json'}
    require(c['progress_events']==len(events),'Complete ordered progress census required')
    previous=0
    for index,expected in enumerate(events):
        name=f'progress-{index:04d}.json';value=obj(name);elapsed=value.pop('elapsed_ns');expected_names.add(name)
        require(type(elapsed) is int and previous<=elapsed<=c['elapsed_ns'] and value==expected,'Actual progress order or clock differs')
        previous=elapsed
    require({p.name for p in directory.iterdir()}==expected_names,'Unexpected or missing quality output')
    for name,e in inputs.items():read(directory/name,e,maximum=8*2**20,retain=False)
    if mode=='gpu_quality':
        for name,e in cpu_report['artifacts'].items():read(Path(cpu_directory)/name,e,maximum=8*2**20,retain=False)
    return dict(status='verified',mode=mode,actual_loss_files_compared=len(stats.MODELS)*count,
        actual_progress_and_parity_barrier_checked=True,statistics_recomputed=mode=='gpu_quality',
        all_endpoint_gates_pass=c['summary']['all_endpoint_gates_pass'] if mode=='gpu_quality' else None,
        actual_cpu_reference_audit=cpu_report if mode=='gpu_quality' else None,
        statistics_numpy_version=expected_statistics_numpy_version,
        recomputation_numpy_version=recomputation_numpy_version if mode=='gpu_quality' else None,
        numerical_statistics_equal_across_declared_runtimes=mode=='gpu_quality',
        artifacts=inputs,actual_model_runtime_and_budget_audits_still_required=True,
        independent_likelihood_reexecution=False,shared_statistics_implementation=True)
