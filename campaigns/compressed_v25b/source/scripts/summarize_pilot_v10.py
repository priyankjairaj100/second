"""Verify bounded diagnostic artifacts. Never promote a full-model claim."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import digest, strict_json, read_completed, canonical_json, atomic_write


def main():
    root=Path(__file__).resolve().parents[1]/'pilots/v10'
    rows=[]
    for corpus,scalar,fast,scalar_worker,fast_worker in [
        ('wikitext2','feature-diagnostic','wikitext2-accelerated','feature-worker','wikitext2-accelerated-worker'),
        ('c4_bounded_english','c4-scalar','c4-accelerated','c4-scalar-worker','c4-accelerated-worker')]:
        outputs=[];workers=[]
        for folder,worker in [(scalar,scalar_worker),(fast,fast_worker)]:
            p=root/folder/'progress.json';data=strict_json(p.read_bytes())
            if data['status']!='complete':raise ValueError('incomplete diagnostic: '+folder)
            events={}
            for event in data['stages']:
                key=(event['stage'],event['record_id'])
                if key in events:raise ValueError('duplicate diagnostic stage record')
                raw=(root/folder/event['features_file']).read_bytes()
                if event['status']!='complete' or digest(raw)!=event['features_sha256']:
                    raise ValueError('diagnostic feature artifact differs')
                if len(raw)!=8*event['shape'][0]*event['shape'][1]:
                    raise ValueError('feature shape or byte length differs')
                events[key]=(event,raw)
            identity=strict_json((root/worker/'identity.json').read_bytes())
            receipt=read_completed(root/worker,identity)
            if receipt is None or receipt['outcome']['status']!='complete':
                raise ValueError('incomplete worker')
            plan=strict_json(Path(identity['command'][2]).read_bytes())
            if digest(canonical_json(plan))!=data['plan_sha256']:
                raise ValueError('worker plan differs from feature result')
            outputs.append((events,plan));workers.append(receipt)
        a,pa=outputs[0];b,pb=outputs[1]
        if set(a)!=set(b) or len(a)!=8:raise ValueError('diagnostic denominator differs')
        for field in ['checkpoint_sha256','records_sha256','stages','protocol_sha256']:
            if pa[field]!=pb[field]:raise ValueError('unmatched diagnostic inputs')
        equal=all(a[k][0]['shape']==b[k][0]['shape'] and a[k][1]==b[k][1] for k in a)
        if not equal:raise ValueError('exact feature mismatch')
        ns=[r['outcome']['elapsed_wall_ns'] for r in workers]
        rows.append(dict(dataset=corpus,records=2,tokens_per_record=16,stage_record_pairs=8,
            matching_binary64_values=sum(len(a[k][1])//8 for k in a),all_features_bitwise_equal=equal,
            scalar_worker_seconds=ns[0]/1e9,prototype_worker_seconds=ns[1]/1e9,
            diagnostic_worker_ratio=ns[0]/ns[1],
            scalar_peak_rss_bytes=workers[0]['resource_usage']['max_rss_kib']*1024,
            prototype_peak_rss_bytes=workers[1]['resource_usage']['max_rss_kib']*1024,
            stage_timings=[dict(stage=k[0],record_id=k[1],scalar_seconds=a[k][0]['elapsed_ns']/1e9,
                prototype_seconds=b[k][0]['elapsed_ns']/1e9) for k in sorted(a)],
            observations_per_method=1,confidence_interval=None,full_model_win=None,
            worker_boundary='limited worker elapsed through cleanup; excludes final controller accounting; not complete repair observer',
            scope='unquantized first-block features only; no quantizer, repair, certificate, state, quality, or lifetime'))
    ledger=strict_json((root/'phase-cpu-budget/ledger.json').read_bytes())
    charged=sum(r['charged_cpu_seconds'] for r in ledger['attempts'].values())
    if any(r['state']!='settled' for r in ledger['attempts'].values()):
        raise ValueError('unresolved worker budget reservation')
    result=dict(schema='real-diagnostic-pilot-summary-v1',date='2026-10-05',rows=rows,
        charged_worker_cpu_seconds=charged,cap_worker_cpu_seconds=10800,
        production_sources_modified=False,full_model_experiments_completed=0,
        promotion='blocked_by_dense_full_model_resource_plan',full_model_speedup_established=False)
    atomic_write(root/'summary.json',canonical_json(result))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
    for row in rows:print(row['dataset'],row['diagnostic_worker_ratio'],row['matching_binary64_values'])


if __name__=='__main__':main()
