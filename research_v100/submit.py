"""New held, single-use five-allocation chain; never repair historical attempts."""
from pathlib import Path
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import datetime,json,re,subprocess
from research_v100 import protocol
from research_v100.config import ROOT,RUN,OPERATIONS as ORDER,ORDER as TRIAL_ORDER,name as operation_name,wall
from research_v100.records import writer
from research_v100.host import admit
from research_v100.closure import review
from research_v90.recovery_gate import JOBS
from research_v100.gate import verify as verify_gate
from research_v100 import campaign
from research_v86.admission import EXPECTED,terminal_disposition
from research_v83.accounting import scheduler_rows
from research_v83.terminal import Inputs
from research_v80.io import require,json_read
FIELDS='--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'


def call(args):return subprocess.check_output(args,text=True,timeout=30).strip()

def fields(raw):
    rows=[word.split('=',1) for word in raw.split() if '=' in word]
    require(len({r[0] for r in rows})==len(rows),'Duplicate scheduler fields')
    return dict(rows)

def clock(operation):
    seconds=wall(operation);return f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}'

def held_ok(raw,name,dependency):
    f=fields(raw);wanted=dict(JobState='PENDING',JobName='second100-'+operation_name(name),NumCPUs='1',Requeue='0',MinMemoryNode='16G',
        ReqNodeList='csis.mn1',TimeLimit=clock(name),Partition='cpu-short',QOS='cpu-short')
    dep=f.get('Dependency','')
    return all(f.get(k)==v for k,v in wanted.items()) and (f.get('Reason')=='JobHeldUser' or f.get('Priority')=='0') and (
        dep=='(null)' if dependency is None else re.fullmatch(r'afterok:'+re.escape(dependency)+r'(?:\((?:unfulfilled|fulfilled)\))?',dep) is not None)


def inspect_upstream(program):
    b=program['target_terminal'];gate,_,_=verify_gate(b['path'],{k:b[k] for k in ('bytes','sha256')})
    require(gate==program['target_gate'],'Actual reopened target gate differs')
    report=json_read(b['path']);scheduler_rows(call(['sacct','-nP','-j',','.join(r['job_id'] for r in report['jobs'].values()),FIELDS]),report['jobs'])
    scheduler_rows(call(['sacct','-nP','-j',','.join(r['job_id'] for r in JOBS.values()),FIELDS]),JOBS)
    terminal_disposition(call(['sacct','-nP','-j',','.join(EXPECTED),'--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList']))


def main(mode,expected):
    require(Path(__file__).resolve()==RUN/'research_v100/submit.py' and mode in ('checks','chain'),'Literal new launcher required')
    require(not (RUN/(mode+'-chain-intent.json')).exists(),'One-use launcher intent already consumed')
    p=campaign.verify(prerequisite=False,registered=mode!='checks')
    require(campaign.sha(RUN/'program.json')==expected,'Exact new program differs')
    require(call(['git','-C',str(ROOT),'rev-parse','HEAD'])==p['numerical_checkout'] and not call(['git','-C',str(ROOT),'status','--short']),
        'Frozen clean numerical checkout required')
    queue=call(['squeue','-u','poonam','-h','-o','%i|%j|%T']);require(not queue,'Inspect unexpected active jobs before any launch')
    inspect_upstream(p)
    names=['checks'] if mode=='checks' else list(ORDER[1:]);dependency=None
    if mode=='chain':
        submission=json_read(RUN/'checks-submission.json');dependency=submission['job_id']
        protocol.allocation('checks',expected,dependency,require_release=True)
        jobs={'checks':dict(job_id=dependency,name='second100-checks')}
        scheduled=scheduler_rows(call(['sacct','-nP','-j',dependency,FIELDS]),jobs)
        inputs=Inputs();review('checks',p,expected,inputs,scheduled['checks']);inputs.unchanged()
        require(not (RUN/'budget').exists() and all(not (RUN/x).exists() for x in ('distilgpt2','gpt2')),'Prior target/fetch attempt exists; no retry')
    requested,snapshot,admission=admit(p,names[0]);records=writer()
    if mode=='checks':records.write('registration.json',dict(program_sha256=expected))
    records.write(mode+'-chain-intent.json',dict(program_sha256=expected,sequence=names,queue_before=queue,
        storage_requests=requested,storage_snapshot=snapshot,storage_admission=admission,
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    jobs=[]
    for operation in names:
        name=operation_name(operation)
        args=['sbatch','--hold','--parsable','--no-requeue','--kill-on-invalid-dep=yes','--partition=cpu-short','--qos=cpu-short',
            '--nodelist=csis.mn1','--ntasks=1','--cpus-per-task=1','--mem=16G','--time='+clock(operation),'--job-name=second100-'+name,
            '--chdir='+str(ROOT),'--output='+str(RUN/(name+'-%j.log'))]
        if dependency:args.append('--dependency=afterok:'+dependency)
        args.extend([str(RUN/'research_v100/run_cpu.sbatch'),operation,expected])
        records.write(name+'-intent.json',dict(arguments=args,program_sha256=expected))
        result=subprocess.run(args,capture_output=True,text=True,timeout=30)
        records.write(name+'-response.json',dict(exit=result.returncode,stdout=result.stdout,stderr=result.stderr))
        require(result.returncode==0 and result.stdout.strip().isdigit(),'Uncertain submission; inspect, never retry')
        job=result.stdout.strip();state=call(['scontrol','show','job',job])
        row=dict(name=name,operation=operation,arguments=[],job_id=job,dependency=dependency,program_sha256=expected,snapshot=state)
        records.write(name+'-submission.json',row)
        require(held_ok(state,operation,dependency),'Held constraints differ; leave held and inspect')
        jobs.append(row);dependency=job
    records.write(mode+'-held-chain.json',dict(program_sha256=expected,jobs=jobs))
    for row in jobs:
        subprocess.run(['scontrol','release',row['job_id']],check=True,timeout=15)
        records.write(row['name']+'-release.json',dict(program_sha256=expected,job_id=row['job_id'],released=True))
    records.write(mode+'-released-chain.json',dict(program_sha256=expected,jobs=jobs))
    print(json.dumps(dict(program_sha256=expected,jobs=jobs)))

if __name__=='__main__':main(*sys.argv[1:])
