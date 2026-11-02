"""One exclusive held-job submission. Never rerun after an uncertain outcome."""
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
R=Path('/nfs_home/users/poonam/second-20261010')
RUN=R/'local_runs/transfer-software-v81-20261023-a'

def write(name,obj):
    with (RUN/name).open('x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n')

def main(expected):
    assert Path(__file__).resolve()==RUN/'research_v81/submit.py'
    raw=(RUN/'program.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected
    p=json.loads(raw)
    assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==p['numerical_checkout']
    for name,info in p['sources'].items():
        b=(RUN/name).read_bytes()
        assert len(b)==info['bytes'] and hashlib.sha256(b).hexdigest()==info['sha256'],name
    assert not subprocess.check_output(['git','-C',str(R),'status','--short'],text=True).strip()
    for name,info in p['dependencies'].items():
        b=(Path(p['dependency_root'])/name).read_bytes()
        assert len(b)==info['bytes'] and hashlib.sha256(b).hexdigest()==info['sha256'],name
    queue=subprocess.check_output(['squeue','-u','poonam','-h','-o','%i|%j|%T'],text=True)
    rows=[line.split('|') for line in queue.splitlines()]
    assert all(row[0] in p['allowed_existing_jobs'] and row[1].startswith('second80-') for row in rows),'Unexpected account job; inspect before staging'
    dependency=p['afterany_job']
    assert dependency=='15916','Only the registered V80 terminal dependency is allowed'
    snapshot=subprocess.check_output(['scontrol','show','job',dependency],text=True)
    assert 'JobName=second80-supplemental' in snapshot,'Dependency identity differs'
    write('registration.json',{'program_sha256':expected})
    args=['sbatch','--hold','--parsable','--no-requeue','--job-name=second81-software',
        '--dependency=afterany:'+dependency,'--kill-on-invalid-dep=yes','--partition=cpu-short','--qos=cpu-short','--nodelist=csis.mn1','--ntasks=1','--cpus-per-task=1',
        '--mem=16G','--time=00:10:00','--chdir='+str(RUN),'--output='+str(RUN/'slurm-%j.log'),
        str(RUN/'research_v81/run_cpu.sbatch'),expected]
    write('submission-intent.json',dict(program_sha256=expected,command=args,
        queue_before=queue,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    done=subprocess.run(args,capture_output=True,text=True,timeout=30)
    write('submission-response.json',dict(exit=done.returncode,stdout=done.stdout,stderr=done.stderr))
    assert done.returncode==0 and done.stdout.strip().isdigit(),'Uncertain submission: inspect, never retry'
    job=done.stdout.strip()
    snapshot=subprocess.check_output(['scontrol','show','job',job],text=True)
    write('held-job.json',dict(job_id=job,snapshot=snapshot))
    assert 'JobState=PENDING' in snapshot and ('Reason=JobHeldUser' in snapshot or 'Priority=0' in snapshot)
    assert 'NumCPUs=1' in snapshot and 'TimeLimit=00:10:00' in snapshot and 'Requeue=0' in snapshot
    assert 'MinMemoryNode=16G' in snapshot and 'ReqNodeList=csis.mn1' in snapshot
    assert ('afterany:'+dependency) in snapshot,'Software must follow the complete V80 chain'
    subprocess.run(['scontrol','release',job],check=True,timeout=15)
    write('release.json',dict(job_id=job,program_sha256=expected,released=True))
    print(json.dumps(dict(job_id=job,program_sha256=expected,released=True)))

if __name__=='__main__':main(sys.argv[1])
