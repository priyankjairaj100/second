"""Single held submission of a separately registered accounting-only recovery."""
import sys,subprocess,json,re,hashlib,os
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/quality-cost-recovery-v72-20261018-a'
if __name__=='__main__':sys.path.insert(0,str(ROOT/'local_runs/untouched-quality-v71-20261018-a'))
from research_v71.submission import fields,duration,memory,partition

def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def call(args):
    r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert len(r.stdout)+len(r.stderr)<128*2**10
    return dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
def checked(args):
    r=call(args);assert r['returncode']==0,r;return r['stdout'].strip()
def save(n,o):
    with (RUN/n).open('xb') as f:f.write(canonical(o));f.flush();os.fsync(f.fileno())
def verify_inputs(p):
    for group in ['frozen_sources','new_sources']:
        for n,e in p[group].items():
            path=Path(n);assert path.is_file() and not path.is_symlink() and info(path.read_bytes())==e
    for e in p['inputs'].values():
        path=Path(e['path']);assert path.is_file() and not path.is_symlink() and info(path.read_bytes())=={k:e[k] for k in ['bytes','sha256']}
def inspect(raw,job,registration):
    f=fields(raw)
    expected=dict(JobId=job,JobName='second72-cost-audit',JobState='PENDING',Reason='JobHeldUser',Priority='0',
        Account='faculty',QOS='cpu-short',Partition='cpu-short',Requeue='0',Restarts='0',NumCPUs='1',NumTasks='1',
        BatchFlag='1',WorkDir=str(ROOT),Command=str(RUN/'research_v72/run_cpu.sbatch'),StdIn='/dev/null',
        StdOut=str(RUN/('slurm-'+job+'.log')),StdErr=str(RUN/('slurm-'+job+'.log')),
        KillOInInvalidDependent='Yes',Comment='second-v72:'+registration,Dependency='(null)',
        ReqNodeList='csis.mn1',ExcNodeList='(null)')
    assert all(f.get(k)==v for k,v in expected.items()) and f.get('CPUs/Task')=='1' and f.get('NumNodes') in {'1','1-1'}
    assert re.fullmatch(r'poonam\(\d+\)',f.get('UserId',''))
    assert duration(f['TimeLimit'])==1200 and memory(f['MinMemoryNode'])==4*2**30
    tres=fields(f['ReqTRES'].replace(',',' '))
    assert tres.get('cpu')=='1' and tres.get('node')=='1' and memory(tres['mem'])==4*2**30 and set(tres)<={'cpu','node','mem','billing'}
    return f

def main(expected):
    assert sys.platform=='linux' and Path(__file__).resolve()==RUN/'research_v72/submit_once.py'
    raw=(RUN/'program.json').read_bytes();p=json.loads(raw)
    assert canonical(p)==raw and info(raw)['sha256']==expected and p['directory']==str(RUN)
    assert not any((RUN/n).exists() for n in ['launch-intent.json','job-binding.json','attempt.json','receipt.json'])
    verify_inputs(p)
    assert checked(['git','rev-parse','HEAD'])=='f900999fcb200509dfad4fc081ce9c87fd172a16'
    assert not checked(['git','status','--porcelain'])
    assert not any('second' in row.lower() for row in checked(['squeue','-h','-u','poonam','-o','%i|%j|%T']).splitlines())
    policy=partition(checked(['scontrol','show','partition','cpu-short','-o']),'cpu-short')
    assert policy==p['partition'] and duration(policy['MaxTime'])>=1200
    accounting=checked(['sacct','-n','-P','-j',','.join(str(j) for j in range(15405,15414)),
        '--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS'])
    assert accounting==Path(p['inputs']['scheduler']['path']).read_text().strip()
    args=['sbatch','--parsable','--hold','--no-requeue','--kill-on-invalid-dep=yes','--nodes=1','--ntasks=1','--cpus-per-task=1',
        '--partition=cpu-short','--qos=cpu-short','--account=faculty','--mem=4G','--time=00:20:00','--nodelist=csis.mn1',
        '--job-name=second72-cost-audit','--comment=second-v72:'+expected,'--chdir='+str(ROOT),
        '--output='+str(RUN/'slurm-%j.log'),'--error='+str(RUN/'slurm-%j.log'),str(RUN/'research_v72/run_cpu.sbatch'),expected]
    save('launch-intent.json',dict(registration_sha256=expected,arguments=args,automatic_retry=False))
    response=call(args);save('submission-response.json',response)
    job=response['stdout'].strip();assert response['returncode']==0 and re.fullmatch(r'\d+',job),'Unknown submit response; inspect, never retry'
    raw_job=checked(['scontrol','show','job',job,'-o']);f=inspect(raw_job,job,expected)
    save('held-verification.json',dict(raw=raw_job,fields=f))
    save('job-binding.json',dict(job_id=job,registration_sha256=expected,submission_state='held-before-release'))
    verify_inputs(p)
    queue=checked(['squeue','-h','-u','poonam','-o','%i|%j|%T'])
    assert {line.split('|')[0] for line in queue.splitlines() if 'second' in line.lower()}=={job}
    inspect(checked(['scontrol','show','job',job,'-o']),job,expected)
    save('release-intent.json',dict(job_id=job,registration_sha256=expected))
    response=call(['scontrol','release',job]);save('release-response.json',response)
    assert response['returncode']==0,'Unknown release response; inspect, never retry'
    print(canonical(dict(job_id=job,registration_sha256=expected,submitted_once=True,released=True)).decode())
if __name__=='__main__':main(*sys.argv[1:])
