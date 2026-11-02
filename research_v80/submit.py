"""Exclusive held submissions: separate checks gate, then finite dependent chain."""
import datetime,hashlib,json,math,os,subprocess,sys
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/four-cell-service-v80-20261023-a'

def command(args):return subprocess.check_output(args,text=True,timeout=30).strip()
def save(name,obj):
    with (RUN/name).open('x') as f:
        json.dump(obj,f,sort_keys=True,separators=(',',':'));f.flush();os.fsync(f.fileno())
def info(path):
    p=Path(path);assert p.is_file() and not any(q.is_symlink() for q in (p,*p.parents))
    h=hashlib.sha256();count=0
    with p.open('rb') as f:
        while b:=f.read(2**20):h.update(b);count+=len(b)
    return dict(bytes=count,sha256=h.hexdigest())
def submit_held(name,operation,wall,sha,dependency=None):
    minutes=math.ceil(wall/60);clock=f'{minutes//60:02d}:{minutes%60:02d}:00'
    args=['sbatch','--hold','--parsable','--no-requeue','--kill-on-invalid-dep=yes',
        '--partition=cpu-short','--qos=cpu-short','--nodelist=csis.mn1','--ntasks=1','--cpus-per-task=1',
        '--mem=16G','--time='+clock,'--job-name=second80-'+name,'--chdir='+str(ROOT),
        '--output='+str(RUN/(name+'-%j.log'))]
    if dependency:args.append('--dependency=afterok:'+dependency)
    args.extend([str(RUN/'research_v80/run_cpu.sbatch'),operation,sha])
    if operation=='run':args.append(name)
    save(name+'-submission-intent.json',dict(arguments=args,program_sha256=sha,automatic_retry=False))
    response=subprocess.run(args,capture_output=True,text=True,timeout=30)
    save(name+'-submission-response.json',dict(exit=response.returncode,stdout=response.stdout,stderr=response.stderr))
    assert response.returncode==0 and response.stdout.strip().isdigit(),'Unknown submission outcome; inspect, never retry'
    job=response.stdout.strip();snapshot=command(['scontrol','show','job',job])
    row=dict(name=name,job_id=job,program_sha256=sha,arguments=args,snapshot=snapshot)
    save(name+'-submission.json',row)
    for wanted in ['JobState=PENDING','NumCPUs=1','TimeLimit='+clock,'Requeue=0','MinMemoryNode=16G','ReqNodeList=csis.mn1']:
        assert wanted in snapshot,wanted
    assert 'Reason=JobHeldUser' in snapshot or 'Priority=0' in snapshot
    return row

def main(mode,sha):
    assert mode in ('checks','chain') and Path(__file__).resolve()==RUN/'research_v80/submit.py'
    assert info(RUN/'program.json')['sha256']==sha
    p=json.loads((RUN/'program.json').read_text())
    assert command(['git','-C',str(ROOT),'rev-parse','HEAD'])==p['numerical_checkout']
    assert not command(['git','-C',str(ROOT),'status','--short'])
    queue=command(['squeue','-u','poonam','-h','-o','%i|%j|%T'])
    assert not queue,'Account queue changed; inspect before launch'
    for group in ('prior_sources','new_sources','dependency_files','historical_ledgers'):
        for path,e in p[group].items():assert info(path)==e,path
    for e in p['inputs'].values():assert info(e['path'])=={k:e[k] for k in ('bytes','sha256')}
    if mode=='checks':
        save('registration.json',dict(program_sha256=sha))
        sequence=[('checks','checks',p['software_wall_seconds'])]
        dependency=None
    else:
        assert json.loads((RUN/'registration.json').read_text())==dict(program_sha256=sha)
        gate=json.loads((RUN/'software-completion.json').read_text())
        assert gate['status']=='complete' and gate['program_sha256']==sha and gate['tests']==p['expected_tests']
        assert gate['errors']==gate['failures']==gate['skipped']==0 and gate['empirical_execution'] is False
        job=json.loads((RUN/'checks-submission.json').read_text())['job_id'];dependency=job
        accounting=command(['sacct','-n','-P','-j',job,'--format=JobIDRaw,State,ExitCode'])
        assert f'{job}|COMPLETED|0:0' in accounting
        assert not (RUN/'budget').exists()
        assert all(not (RUN/n).exists() and not (RUN/(n+'-entry-start.json')).exists() for n in p['trial_order'])
        sequence=[(n,'run',p['trials'][n]['wall_seconds']+p['controller_wall_overhead_seconds']) for n in p['trial_order']]
        sequence += [(n,n,p[n+'_audit_caps']['wall']) for n in ('primary','supplemental')]
        save('chain-submission-intent.json',dict(program_sha256=sha,sequence=sequence,software_completion=info(RUN/'software-completion.json'),software_accounting=accounting,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),queue_before=queue,automatic_retry=False))
    jobs=[]
    for name,operation,wall in sequence:
        row=submit_held(name,operation,wall,sha,dependency);jobs.append(row);dependency=row['job_id']
    save(mode+'-held-chain.json',dict(program_sha256=sha,jobs=jobs))
    for row in jobs:
        subprocess.run(['scontrol','release',row['job_id']],check=True,timeout=15)
        save(row['name']+'-release.json',dict(program_sha256=sha,job_id=row['job_id'],released=True))
    save(mode+'-released-chain.json',dict(program_sha256=sha,jobs=[dict(name=r['name'],job_id=r['job_id']) for r in jobs]))
    print(json.dumps(dict(program_sha256=sha,jobs=[dict(name=r['name'],job_id=r['job_id']) for r in jobs])))

if __name__=='__main__':main(*sys.argv[1:])
