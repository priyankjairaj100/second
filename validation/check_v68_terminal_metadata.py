"""Portable receipt reconciliation only; no local retokenization or model inference."""
from pathlib import Path
from decimal import Decimal
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
REG='ddcf2b686ff0ed4c4401a4defa361bcd956a32d3697dbe1b71485744c513b3cb'
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def seconds(s):
    a=s.split(':');assert 2<=len(a)<=3
    return sum(Decimal(v)*60**i for i,v in enumerate(reversed(a)))
def check(path):
    with tarfile.open(path) as t:
        rows=t.getmembers();assert len(rows)==35 and len(set(x.name for x in rows))==35
        assert all(x.isfile() and not Path(x.name).is_absolute() and '..' not in Path(x.name).parts and x.size<=2**20 for x in rows)
        files={x.name:t.extractfile(x).read() for x in rows}
    j=lambda n:json.loads(files[n])
    c=j('collection.json');p=j('registration.json');jobs=j('jobs.json')
    assert info(files['registration.json'])['sha256']==REG
    assert files['registration.json']==(ROOT/'handoff/registration_v68.json').read_bytes()
    assert set(c['files'])==set(files)-{'collection.json'}
    assert all(info(files[n])==v for n,v in c['files'].items())
    assert jobs==dict(checks='15390',data='15391',audit='15392')
    assert c['registration_sha256']==REG and c['frozen_sources_verified']==469 and c['v68_sources_verified']==9
    assert c['historical_metadata_verified']==len(p['history'])==378
    assert c['historical_ledgers_verified']==len(p['historical_ledgers'])==103
    assert c['administrative_sources_verified']==1 and c['raw_corpus_or_tokens_copied'] is False
    assert c['retokenization_repeated_by_collector'] is False
    for group in ['new_sources','administrative_sources']:
        for remote,e in p[group].items():
            n=str(Path(remote).relative_to(p['directory']));assert info(files[n])==e
            local=ROOT/(n if group=='new_sources' else 'validation/'+n)
            assert info(local.read_bytes())==e
    assert p['allowance_cpu_seconds']==1506 and p['automatic_retry'] is False
    scheduler={}
    for line in c['accounting'].splitlines():
        f=line.split('|');assert len(f)==10
        if '.' in f[0]:assert f[0].split('.')[0] in jobs.values();continue
        assert f[0] in jobs.values() and f[0] not in scheduler
        assert f[2:4]==['COMPLETED','0:0'] and f[7]=='csis.mn1'
        scheduler[f[0]]=f
    assert set(scheduler)==set(jobs.values())
    costs={};previous=None
    for trial in ['checks','data','audit']:
        job=jobs[trial];r=j(trial+'.json');f=scheduler[job];start=j(trial+'-start.json')
        assert r['status']=='complete' and r['error'] is None and r['trial']==trial and r['job_id']==job
        assert r['registration_sha256']==start['registration_sha256']==REG and start['job_id']==job
        assert r['model_inference'] is False and r['quality_evaluation'] is False and r['caps']==p['caps'][trial]
        sub=j(trial+'-submission.json');intent=j(trial+'-submission-intent.json');response=j(trial+'-submission-response.json')
        assert sub['arguments']==intent['arguments'] and sub['registration_sha256']==intent['registration_sha256']==REG
        assert intent['automatic_retry'] is False and sub['job_id']==job and response['returncode']==0 and response['stdout'].strip()==job
        args=sub['arguments'];assert '--no-requeue' in args and '--mem=4G' in args
        assert ([a for a in args if a.startswith('--dependency=')]==([] if previous is None else ['--dependency=afterok:'+previous]))
        own,child,total=[r[k] for k in ['process_cpu_ns','waited_child_cpu_ns','combined_observed_cpu_ns']]
        assert all(type(x) is int and x>=0 for x in [own,child,total,r['elapsed_ns'],r['max_rss_kib']])
        assert total==own+child and total<=(r['caps']['cpu']+2)*10**9 and r['max_rss_kib']*1024<=4*2**30
        assert Decimal(total)/10**9<=seconds(f[5])+Decimal('.001')<r['caps']['cpu']+2
        assert Decimal(r['elapsed_ns'])/10**9<=seconds(f[4])+1<=r['caps']['wall']+1
        costs[trial]=dict(job_id=job,process_tree_cpu_ns=total,charged_cpu_seconds=max(1,(total+999999999)//10**9),scheduler_cpu_seconds=str(seconds(f[5])),scheduler_wall_seconds=int(seconds(f[4])))
        previous=job
    assert j('checks.json')['result']==dict(errors=0,failures=0,skips=0,tests=22,generated_fixtures_only=True)
    audit=j('audit.json')['result']
    assert audit['status']=='verified' and audit['selected_articles']==320
    assert all(audit[k] is True for k in ['actual_saved_prefix_retokenized','actual_records_equal','actual_full_candidate_inventory_equal','actual_exclusion_union_equal','implementation_shared_with_preparation'])
    s=j('outputs/selection.json');a=j('outputs/acquisition.json');out=c['output_commitments']
    assert s==j('data.json')['result'] and s['status']=='complete' and s['policy']==p['policy']
    assert s['selected_articles']==s['requested_articles']==320 and s['candidate_articles']==3801 and s['eligible_articles']==2778
    ids=s['sampling_order_ids'];assert len(ids)==len(set(ids))==320
    assert [x['id'] for x in s['selected_metadata']]==ids
    assert ids==sorted(ids,key=lambda x:(hashlib.sha256((p['policy']['order_seed']+x).encode()).hexdigest(),x))
    assert s['records']==out['records.json'] and s['exclusions_before']==out['exclusions-before.json']
    assert s['source_prefix']==out['validation-prefix.gz.part']==a['received']
    assert s['inspected_frame_permanently_reserved'] is True and s['model_inference'] is False and s['quality_evaluation'] is False
    assert a['status']=='complete' and a['error'] is None and a['automatic_retry'] is False
    assert a['received']['bytes']==8388608 and a['headers']=={'Content-Length':'8388608','Content-Range':'bytes 0-8388607/40675053'}
    assert a['whole_source_sha256_is_metadata_only'] is True and s['frame']['whole_gzip_trailer_verified'] is False
    assert s['frame']['complete_records']==3801 and s['frame']['decompressed_prefix']['bytes']==8388608
    assert s['frame']['incomplete_trailing_bytes']==2212
    return dict(status='verified_terminal_receipt_metadata',archive=info(Path(path).read_bytes()),registration_sha256=REG,
        observed_at_utc=c['captured_at_utc'],jobs=jobs,costs=costs,
        charged_cpu_seconds=sum(x['charged_cpu_seconds'] for x in costs.values()),
        process_tree_cpu_ns=sum(x['process_tree_cpu_ns'] for x in costs.values()),
        scheduler_allocation_cpu_seconds=str(sum(Decimal(x['scheduler_cpu_seconds']) for x in costs.values())),
        selected_articles=320,candidate_frame_reserved=3801,eligible_articles=2778,
        cluster_saved_byte_audit_reconciled=True,actual_raw_bytes_or_tokens_rechecked_locally=False,
        model_quality_evaluated=False,whole_source_integrity_verified=False,
        scope='Saved cluster audit and scheduler metadata; not an independent retokenization or quality result')
if __name__=='__main__':
    import sys
    print(json.dumps(check(sys.argv[1]),indent=2,sort_keys=True))
