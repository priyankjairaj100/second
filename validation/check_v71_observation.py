"""Check a bounded active snapshot without promoting it to a terminal audit."""
from pathlib import Path
import hashlib,json,sys,tarfile

R=Path(__file__).resolve().parents[1]
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def check(path):
    with tarfile.open(path) as t:
        members=t.getmembers()
        assert len(members)<200 and len({m.name for m in members})==len(members)
        assert all(m.isfile() and m.size<4*2**20 and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        assert sum(m.size for m in members)<16*2**20
        f={m.name:t.extractfile(m).read() for m in members}
    c=json.loads(f['collection.json']);p=json.loads(f['program.json']);reg=info(f['program.json'])['sha256']
    assert f['program.json']==(R/'handoff/registration_v71_quality.json').read_bytes()
    assert reg==c['registration_sha256']=='3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
    assert c['files']=={n:info(b) for n,b in f.items() if n!='collection.json'}
    assert c['frozen_numerical_sources_verified']==575 and c['model_or_corpus_bytes_collected'] is False
    for name,e in p['new_sources'].items():assert info(f[str(Path(name).relative_to(p['directory']))])==e
    rows={r[0]:r for line in c['accounting'].splitlines() if (r:=line.split('|'))[0].isdigit()}
    assert set(rows)==set(c['jobs'].values())
    ledger=json.loads(f['budget/ledger.json']);completed={}
    for phase,job in c['jobs'].items():
        binding=json.loads(f[phase+'/job-binding.json'])
        assert binding['job_id']==job and binding['phase']==phase and binding['registration_sha256']==reg
        name=phase+'/entry.json'
        if name not in f or rows[job][1]!='COMPLETED':continue
        entry=json.loads(f[name]);done_raw=f[phase+'/outputs/completion.json'];done=json.loads(done_raw)
        worker=json.loads(f[phase+'/worker/result.json']);identity=json.loads(f[phase+'/worker/identity.json'])
        assert rows[job][2]=='0:0' and entry['status']==done['status']=='complete'
        assert entry['error'] is done['error'] is None and entry['job_id']==done['job_id']==job
        assert entry['registration_sha256']==done['registration_sha256']==reg
        assert identity['identity']==dict(registration_sha256=reg,phase=phase)
        assert entry['outputs']['completion.json']==info(done_raw)
        assert worker['outcome']['status']=='complete' and worker['outcome']['returncode']==0
        debit=worker['budget_debit'];assert debit==ledger['attempts'][worker['budget_attempt_id']] and debit['state']=='settled'
        assert debit['observed_cpu_ns']==worker['resource_usage']['total_cpu_ns']
        assert debit['charged_cpu_seconds']==max(1,(debit['observed_cpu_ns']+999999999)//10**9)
        completed[phase]=dict(job_id=job,charged_worker_cpu_seconds=debit['charged_cpu_seconds'],
            completion=info(done_raw),result=done['result'])
    cpu=json.loads(f['cpu_checks/outputs/checks.json'])
    assert cpu==dict(empirical_quality=False,errors=0,failures=0,includes_unchanged_v55_numerical_fixtures=True,skips=0,tests=103)
    cuda=completed['cuda_checks']['result'];assert cuda['status']=='complete' and cuda['error'] is None
    assert cuda['actual_checkpoint_loaded'] is False and cuda['empirical_quality'] is False
    assert len(cuda['comparisons'])==24 and all(x['passed'] and x['mean_nll_absolute_difference']<=cuda['threshold'] for x in cuda['comparisons'])
    pars=completed['parameters']['result'];assert pars['actual_checkpoint_reference_compared'] is True
    assert pars['parameters']['actual_all_parameter_words_equal'] is True and pars['parameters']['arrays']==78
    assert pars['checkpoint']==p['inputs']['checkpoint']
    for phase in completed:completed[phase].pop('result')
    return dict(schema='v71-active-metadata-check',status='verified_partial_observation',
        observed_at_utc=c['captured_at_utc'],archive=info(Path(path).read_bytes()),
        registration_sha256=reg,jobs={phase:dict(job_id=job,state=rows[job][1],exit_code=rows[job][2],elapsed_seconds=int(rows[job][3])) for phase,job in c['jobs'].items()},
        completed=completed,cpu_tests=cpu,generated_cuda_comparisons=24,all_parameter_arrays_compared=78,
        active_reservations={k:v for k,v in ledger['attempts'].items() if v['state']=='reserved'},
        settled_worker_cpu_seconds=sum(v['charged_cpu_seconds'] for v in ledger['attempts'].values() if v['state']=='settled'),
        frozen_numerical_sources_verified=575,full_worker_seal_artifacts_rechecked_locally=False,
        model_bytes_compared_locally=False,terminal_quality_result_verified=False,
        scope='Partial metadata only; checkpoint-array equality is reported by the completed actual cluster audit. Remaining actual model, loss and cost gates still required.')
if __name__=='__main__':
    result=check(R/'campaigns'/sys.argv[1]);out=R/'validation'/sys.argv[2]
    assert not out.exists();out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['completed','active_reservations']}))
