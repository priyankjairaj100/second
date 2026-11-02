"""Finite held admission chain; exclusive intent, captured IDs, no retry."""
import datetime,hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/matched-transfer-admission-v82-20261023-a'
ORDER=('checks','fetch','distilgpt2','gpt2','close')
WALL={'checks':'00:10:00','fetch':'00:10:00','distilgpt2':'00:25:00','gpt2':'00:25:00','close':'00:10:00'}

def fields(snapshot):
    pairs=[word.split('=',1) for word in snapshot.split() if '=' in word]
    if len({key for key,value in pairs})!=len(pairs):raise ValueError('Duplicate Slurm fields')
    return dict(pairs)

def held_ok(snapshot,name,dependency):
    f=fields(snapshot)
    exact=dict(JobState='PENDING',NumCPUs='1',Requeue='0',MinMemoryNode='16G',ReqNodeList='csis.mn1',
        TimeLimit=WALL[name],JobName='second82-'+name)
    return (all(f.get(k)==v for k,v in exact.items()) and (f.get('Reason')=='JobHeldUser' or f.get('Priority')=='0')
        and re.fullmatch(r'afterok:'+re.escape(dependency)+r'(?:\((?:unfulfilled|fulfilled)\))?',f.get('Dependency','')) is not None)

def write(name,x):
    # Controller json_read requires exact canonical bytes, including no newline.
    with (RUN/name).open('x') as f:
        json.dump(x,f,sort_keys=True,separators=(',',':'),allow_nan=False);f.flush();os.fsync(f.fileno())

def main(expected):
    assert Path(__file__).resolve()==RUN/'research_v82/submit.py'
    raw=(RUN/'program.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==expected;p=json.loads(raw)
    assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()==p['numerical_checkout']
    assert not subprocess.check_output(['git','-C',str(ROOT),'status','--short'],text=True).strip()
    for name,e in p['new_sources'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        b=(RUN/name).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'],name
    queue=subprocess.check_output(['squeue','-u','poonam','-h','-o','%i|%j|%T'],text=True)
    known={str(i):'second80-' for i in range(15905,15917)};known['15917']='second81-software'
    for row in queue.splitlines():
        ident,name,state=row.split('|');assert ident in known and name.startswith(known[ident]),'Unexpected account job; inspect before launch'
    dep='15917';upstream=subprocess.check_output(['scontrol','show','job',dep],text=True)
    assert fields(upstream).get('JobName')=='second81-software','Known upstream gate required'
    write('registration.json',dict(program_sha256=expected))
    write('chain-intent.json',dict(program_sha256=expected,order=list(ORDER),queue_before=queue,upstream=upstream,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    jobs={}
    for name in ORDER:
        args=['sbatch','--hold','--parsable','--no-requeue','--job-name=second82-'+name,'--dependency=afterok:'+dep,'--kill-on-invalid-dep=yes',
            '--partition=cpu-short','--qos=cpu-short','--nodelist=csis.mn1','--ntasks=1','--cpus-per-task=1','--mem=16G','--time='+WALL[name],
            '--chdir='+str(RUN),'--output='+str(RUN/(name+'-%j.log')),str(RUN/'research_v82/run_cpu.sbatch'),name,expected]
        write(name+'-intent.json',dict(command=args,program_sha256=expected))
        result=subprocess.run(args,capture_output=True,text=True,timeout=30)
        write(name+'-response.json',dict(exit=result.returncode,stdout=result.stdout,stderr=result.stderr))
        assert result.returncode==0 and result.stdout.strip().isdigit(),'Uncertain submission: inspect, never retry'
        job=result.stdout.strip();snapshot=subprocess.check_output(['scontrol','show','job',job],text=True)
        write(name+'-submission.json',dict(job_id=job,program_sha256=expected,dependency=dep,snapshot=snapshot))
        assert held_ok(snapshot,name,dep),'Held constraints differ; leave held and inspect'
        jobs[name]=job;dep=job
    write('held-chain.json',dict(jobs=jobs,program_sha256=expected))
    for name,job in jobs.items():
        subprocess.run(['scontrol','release',job],check=True,timeout=15)
        write(name+'-release.json',dict(job_id=job,released=True,program_sha256=expected))
    write('released-chain.json',dict(jobs=jobs,program_sha256=expected,released=True))
    print(json.dumps(dict(jobs=jobs,program_sha256=expected,released=True)))
if __name__=='__main__':main(sys.argv[1])
