"""Supplementary saved-loss arithmetic check using Python's standard library.

The registered terminal audit remains authoritative. This does not repeat neural
inference, bootstrap draws, or model/state construction. It never changes a gate.
"""
from pathlib import Path
import hashlib, json, math, sys, tarfile
MODELS=('original','nearest','candidate_12','sequential_12','candidate_6','sequential_6')
REG='3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
R=Path(__file__).resolve().parents[1]
def info(raw): return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def obj(raw):
    def pairs(values):
        out={}
        for k,v in values:
            assert k not in out, 'Duplicate JSON key';out[k]=v
        return out
    def invalid(value): raise ValueError('Nonfinite JSON number: '+value)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
def load(path):
    with tarfile.open(path) as t:
        members=t.getmembers()
        assert len(members)<2000 and len({m.name for m in members})==len(members)
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and m.size<8*2**20 for m in members)
        assert sum(m.size for m in members)<32*2**20
        return {m.name:t.extractfile(m).read() for m in members}
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

def check(files,metadata):
    # Caller must first require success from check_v71_campaign_metadata on a final archive.
    assert all(files[n]==metadata[n] for n in ['program.json','terminal/outputs/completion.json','closure/receipt.json'])
    assert info(files['program.json'])['sha256']==REG
    envelope=obj(files['collection.json'])
    assert envelope['schema']=='v71-terminal-scalar-loss-observation' and envelope['registration_sha256']==REG
    assert envelope['scalar_loss_files']==1944 and envelope['model_or_token_bodies_read'] is False and envelope['likelihood_reexecuted'] is False
    assert envelope['files']=={n:info(b) for n,b in files.items() if n!='collection.json'}
    terminal=obj(metadata['terminal/outputs/completion.json'])['result'];audit=terminal['loss_audit']
    collections={};quality={};expected={'collection.json','program.json','terminal/outputs/completion.json','closure/receipt.json'}
    for phase,count,pins in [('cpu_parity',4,audit['actual_cpu_reference_audit']['artifacts']),('gpu_quality',320,audit['artifacts'])]:
        prefix=phase+'/outputs/losses/'
        names=['completion.json']+[f'loss-{m}-{i:04d}.json' for m in MODELS for i in range(count)]
        if phase=='gpu_quality':names+=['paired-losses.json','statistics.json','parity.json']
        for name in names:
            expected.add(prefix+name);assert info(files[prefix+name])==pins[name]
        c=obj(files[prefix+'completion.json']);collections[phase]=c
        assert c['registration_sha256']==REG and c['status']=='complete' and c['error'] is None and c['mode']==phase
        quality[phase]={}
        for model in MODELS:
            rows=[]
            for i in range(count):
                r=obj(files[prefix+f'loss-{model}-{i:04d}.json'])
                assert set(r)=={'model','index','elapsed_ns','id','predictions','nll_sum','mean_nll'}
                assert r['model']==model and type(r['index']) is int and r['index']==i
                assert type(r['predictions']) is int and r['predictions']==127
                assert type(r['elapsed_ns']) is int and r['elapsed_ns']>=0
                rows.append({k:r[k] for k in ['id','predictions','nll_sum','mean_nll']})
            quality[phase][model]=rows
        assert quality[phase]==c['quality'] and c['completed_article_evaluations']==6*count
    assert set(files)==expected, 'Unexpected or missing scalar-loss archive member'
    cpu,gpu=(collections[k] for k in ['cpu_parity','gpu_quality'])
    assert cpu['records']==gpu['records'] and cpu['model_bindings']==gpu['model_bindings']==terminal['model_bindings']
    ids=[r['id'] for r in quality['gpu_quality']['original']]
    assert len(ids)==320 and ids==sorted(set(ids))
    parity_differences=[]
    for model in MODELS:
        assert [r['id'] for r in quality['gpu_quality'][model]]==ids
        assert [r['id'] for r in quality['cpu_parity'][model]]==ids[:4]
        for a,b in zip(quality['cpu_parity'][model],quality['gpu_quality'][model][:4]):
            assert a['predictions']==b['predictions']==127
            assert all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in [a['nll_sum'],a['mean_nll']])
            assert a['mean_nll']==a['nll_sum']/127
            delta=abs(a['mean_nll']-b['mean_nll']);assert delta<=1e-8;parity_differences.append(delta)
    rows=[dict(id=id_,predictions=127,losses={m:dict(sum_nll=quality['gpu_quality'][m][i]['nll_sum'],
        mean_nll=quality['gpu_quality'][m][i]['mean_nll']) for m in MODELS}) for i,id_ in enumerate(ids)]
    prefix='gpu_quality/outputs/losses/'
    assert obj(files[prefix+'paired-losses.json'])==dict(rows=rows)
    summary=obj(files[prefix+'statistics.json']);assert summary==gpu['summary']
    assert obj(files[prefix+'parity.json'])==gpu['parity']
    endpoints=arithmetic(rows,summary)
    assert terminal['quality_guard_pass'] is summary['all_endpoint_gates_pass']
    return dict(schema='v71-supplementary-saved-loss-arithmetic',status='verified_saved_scalar_arithmetic',
        scalar_losses_checked=1944,paired_articles=320,parity_comparisons=24,max_parity_mean_nll_difference=max(parity_differences),
        endpoints=endpoints,quality_guard_pass=summary['all_endpoint_gates_pass'],
        independent_arithmetic_implementation=True,independent_bootstrap_recomputation=False,
        independent_neural_evaluation=False,model_bytes_read=False,registered_terminal_gate_changed=False,
        scope='Supplementary root reporting check; shared original losses and terminal commitments, not independent experimental replication.')

def main():
    from validation.check_v71_campaign_metadata import load as load_metadata, check as check_metadata
    metadata=load_metadata(R/'campaigns'/sys.argv[1]);status=check_metadata(metadata)
    assert status['terminal_quality_result_verified'] is True, 'Actual complete terminal/cost audit required first'
    source=R/'campaigns'/sys.argv[2];result=check(load(source),metadata)
    result.update(archive=info(source.read_bytes()),terminal_metadata_archive=info((R/'campaigns'/sys.argv[1]).read_bytes()))
    with (R/'validation'/sys.argv[3]).open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
