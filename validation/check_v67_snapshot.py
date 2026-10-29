"""Check a bounded metadata snapshot. Never substitutes for actual binary audits."""
from pathlib import Path
import hashlib,json,math,sys,tarfile
R=Path(__file__).resolve().parents[1]
SHA='11e0db146e79330852f550a1cc3b2dd7568a66cdfe8006b004dca3840149cc30'
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def check(path):
    path=Path(path);assert path.is_file() and not path.is_symlink() and path.stat().st_size<64*2**20
    files={};total=0
    with tarfile.open(path,'r:gz') as archive:
        for m in archive:
            name=Path(m.name)
            assert m.isfile() and not name.is_absolute() and '..' not in name.parts and str(name)==m.name
            assert m.name not in files and name.suffix in {'.json','.py','.txt','.log'} and 0<=m.size<8*2**20
            assert len(files)<1000 and total+m.size<64*2**20
            files[m.name]=archive.extractfile(m).read(m.size+1);assert len(files[m.name])==m.size;total+=m.size
    def obj(n):
        x=json.loads(files[n]);assert canonical(x)==files[n];return x
    s=obj('collection.json');assert s['schema']=='v67-metadata-snapshot' and s['program_sha256']==SHA
    assert set(files)==set(s['files'])|{'collection.json'} and s['frozen_sources_verified']==469
    assert s['numerical_binaries_copied'] is False and s['actual_model_state_audit_repeated_locally'] is False
    assert not set(s['volatile_files_omitted'])&set(files)
    for n,e in s['files'].items():assert info(files[n])==e
    p=obj('program.json');assert info(files['program.json'])['sha256']==SHA
    assert files['program.json']==(R/'handoff/registration_v67.json').read_bytes()
    assert obj('registration.json')==dict(program_sha256=SHA)
    run=Path(p['directory']);root=run.parents[1]
    assert len(p['prior_sources'])==456 and len(p['new_sources'])==13
    for name,e in p['prior_sources'].items():
        parts=Path(name).relative_to(root).parts
        local=R/Path(*(parts if parts[0]!='local_runs' else parts[2:]));assert info(local.read_bytes())==e
    for name,e in p['new_sources'].items():
        n=str(Path(name).relative_to(run));assert info(files[n])==e==info((R/n).read_bytes())
    c=obj('software-completion.json')
    assert c['program_sha256']==SHA and c['status']=='complete' and c['tests']==64
    assert c['errors']==c['failures']==c['skipped']==0 and c['empirical_execution'] is False
    jobs=obj('chain-submission.json')['jobs'];assert [j['name'] for j in jobs]==p['trial_order']+['primary','supplemental']
    assert [j['job_id'] for j in jobs]==[str(j) for j in range(15262,15276)]
    previous='15261'
    for j in jobs:
        name=j['name'];a=j['arguments'];assert obj(name+'-submission.json')==j
        assert obj(name+'-submission-intent.json')['arguments']==a
        for expected in ['--dependency=afterok:'+previous,'--no-requeue','--kill-on-invalid-dep=yes','--nodelist=csis.mn1','--mem=16G']:
            assert expected in a
        wall=p['trials'][name]['wall_seconds']+600 if name in p['trials'] else p[name+'_audit_caps']['wall']
        minutes=math.ceil(wall/60);assert f'--time={minutes//60:02d}:{minutes%60:02d}:00' in a
        assert (a[-3:]==['run',SHA,name]) if name in p['trials'] else (a[-2:]==[name,SHA])
        previous=j['job_id']
    states={}
    for line in s['accounting'].splitlines():
        columns=line.split('|')
        if columns[0] in ['15261']+[j['job_id'] for j in jobs]:
            assert columns[0] not in states and len(columns)>=10
            states[columns[0]]=dict(name=columns[1],state=columns[2],exit_code=columns[3],elapsed=columns[4],
                total_cpu=columns[5],node=columns[7],start=columns[8],end=columns[9])
    assert set(states)=={'15261'}|{j['job_id'] for j in jobs}
    assert states['15261']['state']=='COMPLETED' and states['15261']['exit_code']=='0:0'
    for j in jobs:assert states[j['job_id']]['name']=='second67-'+j['name']
    terminal=[kind+'-audit.json' for kind in ['primary','supplemental']]
    assert s['terminal_receipts_present']==all(name in files for name in terminal)
    progress={}
    for trial in p['trial_order']:
        names=sorted(n for n in files if n.startswith(trial+'/outputs/progress-') and n.endswith('.json'))
        rows=[obj(n) for n in names]
        progress[trial]=dict(events=len(rows),last=rows[-1] if rows else None,
            completion_receipt_present=trial+'/outputs/completion.json' in files)
    return dict(status='verified_snapshot_metadata_only',archive=info(path.read_bytes()),copied_files=len(files),
        frozen_sources_verified=469,program_sha256=SHA,captured_at_utc=s['captured_at_utc'],
        jobs=states,queue=s['queue'],progress=progress,volatile_files_omitted=s['volatile_files_omitted'],
        terminal_receipts_present=s['terminal_receipts_present'],actual_model_state_audit_repeated_locally=False,
        numerical_result_verified=False,scientific_decision_requires_terminal_binary_and_cost_audits=True)

if __name__=='__main__':print(json.dumps(check(sys.argv[1]),sort_keys=True,indent=2))
