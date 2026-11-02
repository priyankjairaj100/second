"""Unregistered fixed matched launcher. Inspect fresh job state before use."""
import datetime,hashlib,json,math,os,subprocess,sys
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/matched-complete-service-v84-20261023-a'
def require(ok,message):
    if not ok:raise ValueError(message)
def call(args):return subprocess.check_output(args,text=True,timeout=30).strip()
def info(path):
    p=Path(path);require(p.is_file() and not any(x.is_symlink() for x in (p,*p.parents)),'Regular pinned source required')
    h=hashlib.sha256();n=0
    with p.open('rb') as f:
        while b:=f.read(2**20):h.update(b);n+=len(b)
    return dict(bytes=n,sha256=h.hexdigest())
def save(name,value):
    with (RUN/name).open('x') as f:json.dump(value,f,sort_keys=True,separators=(',',':'),allow_nan=False);f.flush();os.fsync(f.fileno())
def fields(raw):
    rows=[x.split('=',1) for x in raw.split() if '=' in x];require(len({x[0] for x in rows})==len(rows),'Duplicate scheduler fields');return dict(rows)
def held_ok(raw,name,clock,dependency):
    f=fields(raw);wanted=dict(JobState='PENDING',JobName='second84-'+name,NumCPUs='1',Requeue='0',MinMemoryNode='16G',ReqNodeList='csis.mn1',TimeLimit=clock)
    import re
    return all(f.get(k)==v for k,v in wanted.items()) and (f.get('Reason')=='JobHeldUser' or f.get('Priority')=='0') and (f.get('Dependency')=='(null)' if dependency is None else re.fullmatch(r'afterok:'+re.escape(dependency)+r'(?:\((?:unfulfilled|fulfilled)\))?',f.get('Dependency','')) is not None)
def main(mode,expected):
    require(mode in ('checks','chain') and Path(__file__).resolve()==RUN/'research_v84/submit.py','Literal new finite launcher required')
    require(info(RUN/'program.json')['sha256']==expected,'New program commitment differs');p=json.loads((RUN/'program.json').read_bytes())
    require(call(['git','-C',str(ROOT),'rev-parse','HEAD'])==p['numerical_checkout'] and not call(['git','-C',str(ROOT),'status','--short']),'Frozen clean numerical checkout required')
    queue=call(['squeue','-u','poonam','-h','-o','%i|%j|%T']);require(not queue,'Inspect unexpected active account jobs before launch')
    for name,e in p['sources'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Relative source required');require(info(RUN/name)==e,'New source changed')
    for e in p['terminal_gates'].values():require(info(e['path'])=={k:e[k] for k in ('bytes','sha256')},'Actual terminal prerequisite changed')
    for entries in p['admitted_targets'].values():
        for e in entries.values():require(info(e['path'])=={k:e[k] for k in ('bytes','sha256')},'Actual admitted target changed')
    if mode=='checks':
        save('registration.json',dict(program_sha256=expected));sequence=[('checks','checks',[],600)];dependency=None
    else:
        require(json.loads((RUN/'registration.json').read_text())==dict(program_sha256=expected),'Separate registry required')
        gate=json.loads((RUN/'software-completion.json').read_text());require(gate['status']=='complete' and gate['error'] is None and gate['program_sha256']==expected and gate['tests']==p['expected_tests'] and gate['failures']==gate['errors']==gate['skipped']==0,'Exact Linux software gate required')
        dependency=json.loads((RUN/'checks-submission.json').read_text())['job_id'];accounting=call(['sacct','-nP','-j',dependency,'--format=JobIDRaw,State,ExitCode'])
        require([r.split('|') for r in accounting.splitlines() if r.split('|')[0]==dependency]==[[dependency,'COMPLETED','0:0']],'Software terminal state differs')
        require(not (RUN/'budget').exists() and all(not (RUN/t).exists() for t in p['trial_order']),'Prior matched attempt exists; retry prohibited')
        sequence=[(t.replace('/','--'),'run',[t],p['trials'][t]['wall_seconds']+600) for t in p['trial_order']]+[(k,k,[],p[k+'_audit_caps']['wall']) for k in ('primary','supplemental')]
    save(mode+'-chain-intent.json',dict(program_sha256=expected,sequence=sequence,queue_before=queue,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    jobs=[]
    for name,operation,arguments,wall in sequence:
        minutes=math.ceil(wall/60);clock=f'{minutes//60:02d}:{minutes%60:02d}:00'
        args=['sbatch','--hold','--parsable','--no-requeue','--kill-on-invalid-dep=yes','--partition=cpu-short','--qos=cpu-short','--nodelist=csis.mn1','--ntasks=1','--cpus-per-task=1','--mem=16G','--time='+clock,'--job-name=second84-'+name,'--chdir='+str(ROOT),'--output='+str(RUN/(name+'-%j.log'))]
        if dependency:args.append('--dependency=afterok:'+dependency)
        args.extend([str(RUN/'research_v84/run_cpu.sbatch'),operation,expected,*arguments]);save(name+'-intent.json',dict(arguments=args,program_sha256=expected))
        answer=subprocess.run(args,capture_output=True,text=True,timeout=30);save(name+'-response.json',dict(exit=answer.returncode,stdout=answer.stdout,stderr=answer.stderr))
        require(answer.returncode==0 and answer.stdout.strip().isdigit(),'Uncertain submission; inspect, never retry')
        job=answer.stdout.strip();snapshot=call(['scontrol','show','job',job]);row=dict(name=name,job_id=job,program_sha256=expected,operation=operation,arguments=arguments,dependency=dependency,snapshot=snapshot);save(name+'-submission.json',row)
        require(held_ok(snapshot,name,clock,dependency),'Held constraints differ; leave held and inspect');jobs.append(row);dependency=job
    save(mode+'-held-chain.json',dict(program_sha256=expected,jobs=jobs))
    for row in jobs:
        subprocess.run(['scontrol','release',row['job_id']],check=True,timeout=15);save(row['name']+'-release.json',dict(program_sha256=expected,job_id=row['job_id'],released=True))
    save(mode+'-released-chain.json',dict(program_sha256=expected,jobs=jobs));print(json.dumps(dict(jobs=jobs,program_sha256=expected)))
if __name__=='__main__':main(*sys.argv[1:])
