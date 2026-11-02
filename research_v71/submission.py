"""One-use held-job submission controls; standard library only on login host.

This unregistered adapter is not an instruction to launch. It requires the
immutable campaign, actual completed V67/V68 input receipts and source bytes,
fresh scheduler admission, and a clean inherited numerical checkout. All jobs
remain held until their exact resource requests and bound identities are saved.
An ambiguous submission or release stops without retry, cancellation or rollback.
"""
from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,sys

ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/untouched-quality-v71-20261018-a'
CHECKOUT='f900999fcb200509dfad4fc081ce9c87fd172a16'
ORDER=('cpu_checks','cuda_checks','parameters','sequential_12','sequential_6','cpu_parity','gpu_quality','terminal','closure')
GPU={'cuda_checks','gpu_quality'}
WALL=(1500,1500,1500,18600,18600,3000,7800,3000,900)
NODES={'csis.mn1','csis.cn1','csis.cn2','csis.cn3','csis.cn4'}
MANIFEST=ROOT/'local_runs/cluster-setup-20261010/container-13155.sha256'
MANIFEST_SHA='5a58e1fef1950aabf16cea4f44043b95a1f18d572a67d42dccac4b4b6d96d0b3'
IMAGE=ROOT/'local_runs/cluster-setup-20261010/python-3.12.14-bookworm.sif'
IMAGE_SHA='10ffb205f553197e110472e208522d0c73bcaf62e1a0571b860bf7bae49933b1'
CPU=ROOT/'.venv-container/bin/python'
CUDA=Path('/nfs_home/software/envs/pytorch-12.8/bin/python3.10')
PARTITION_KEYS=('PartitionName','AllowGroups','AllowAccounts','AllowQos','Nodes','State','MaxTime','MaxMemPerNode','MaxCPUsPerNode')


def resources():
    """Standard-library copy; fixture equality checks the worker's full design."""
    caps={n:dict(cpu_seconds=c,wall_seconds=w-600) for n,c,w in zip(ORDER[:-1],
        (600,600,600,14400,14400,1800,5400,1800),WALL[:-1])}
    return dict(schema='quality-execution-resource-design-v71',phases=caps,
        worker_allowance_cpu_seconds=39616,controller_cpu_soft_seconds=600,
        controller_cpu_hard_seconds=14402,controller_allowance_cpu_seconds=4808,
        slurm_wall_overhead_seconds=600,host_memory_bytes=16*2**30,
        cpu_address_space_bytes=16*2**30,cuda_address_space_bytes=128*2**40,
        gpu_allocator_bytes=8*2**30,file_size_bytes=2*2**30,threads=1,
        automatic_retry=False,no_concurrent_second_empirical_work=True,
        post_exit_closure=dict(cpu_soft_seconds=300,cpu_hard_seconds=301,cpu_allowance_seconds=302,
            wall_seconds=900,address_space_bytes=4*2**30,file_size_bytes=128*2**20,
            independent_slurm_job=True,external_reporting_observer_excluded=True),
        final_scheduler_and_closure_accounting_required=True,registered=False)


def require(ok,message):
    if not ok:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def info(raw):return dict(bytes=len(raw),sha256=sha(raw))


def read(path,expected=None,maximum=128*2**20,retain=True):
    path=Path(path);require(path.is_absolute() and '..' not in path.parts
        and not any(p.is_symlink() for p in (path,*path.parents)) and path.is_file(),'Regular absolute nonsymbolic input required')
    before=path.stat();require(before.st_size<=maximum,'Bounded input required')
    h=hashlib.sha256();size=0;chunks=[]
    with path.open('rb') as stream:
        while True:
            raw=stream.read(2**20)
            if not raw:break
            size+=len(raw);require(size<=maximum,'Input grew beyond bound');h.update(raw)
            if retain:chunks.append(raw)
    after=path.stat()
    signature=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    require(signature(before)==signature(after),'Input changed during read')
    actual=dict(bytes=size,sha256=h.hexdigest());require(expected is None or actual==expected,'Actual input commitment differs')
    return b''.join(chunks) if retain else actual


def obj(path,expected=None):
    raw=read(path,expected,maximum=64*2**20);value=json.loads(raw)
    require(type(value) is dict and canonical(value)==raw,'Canonical actual JSON object required')
    return value


def write(path,value):
    path=Path(path);raw=canonical(value)
    require(len(raw)<=8*2**20 and path.is_absolute() and not any(p.is_symlink() for p in (path,*path.parents)),
        'Safe bounded exclusive output required')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())


def fields(raw):
    require(type(raw) is str and len(raw)<=128*2**10,'Bounded scheduler metadata required')
    result={}
    for item in raw.split():
        require('=' in item,'Keyed scheduler metadata required')
        k,v=item.split('=',1);require(k not in result,'Duplicate scheduler field');result[k]=v
    return result


def duration(value):
    m=re.fullmatch(r'(?:(\d+)-)?(\d{1,2}):(\d{2}):(\d{2})',value)
    require(m is not None,'Finite canonical scheduler wall limit required')
    d,h,mm,s=m.groups();require(int(mm)<60 and int(s)<60 and (d is None or int(h)<24),'Canonical scheduler time required')
    return int(d or 0)*86400+int(h)*3600+int(mm)*60+int(s)


def memory(value):
    m=re.fullmatch(r'(\d+)([KMGTP]?)',value)
    require(m is not None,'Literal scheduler memory required')
    n,u=m.groups();return int(n)*1024**({'':2,'K':1,'M':2,'G':3,'T':4,'P':5}[u])


def partition(raw,name):
    f=fields(raw);r={k:f[k] for k in PARTITION_KEYS}
    require(r['PartitionName']==name and r['State']=='UP'
        and all(r[k]=='ALL' for k in ['AllowGroups','AllowAccounts','AllowQos'])
        and int(r['MaxCPUsPerNode'])>=1 and memory(r['MaxMemPerNode'])>=16*2**30,
        'Current partition cannot admit the declared account/resources')
    require(duration(r['MaxTime'])>0,'Finite actual partition time limit required')
    return r


def policy(p):
    require(p['schema']=='untouched-quality-campaign-v71' and p['directory']==str(RUN)
        and p['registered'] is True and p['automatic_retry'] is False
        and p['submission_policy']=='hold-bind-release-once-sequential-afterok','Actual once-only campaign required')
    require(p['resources']==resources(),'Unchanged complete phase caps required')
    require(p['interpreters']==dict(cpu=str(CPU),cuda=str(CUDA)) and p['hosts']['cpu']==['csis.mn1'],
        'Bound inherited CPU and separate CUDA commands required')
    require(type(p['hosts']['cuda']) is list and p['hosts']['cuda']==sorted(set(p['hosts']['cuda']))
        and p['hosts']['cuda'] and set(p['hosts']['cuda'])<=NODES-{'csis.mn1'},'Admitted CUDA node pool required')
    launch=p['launch']
    require(set(launch)=={'schema','partitions','partition_hosts','qos_max_wall','account','qos'}
        and launch['schema']=='held-slurm-launch-policy-v71' and launch['qos']=='cpu-short'
        and launch['account']=='faculty' and set(launch['partitions'])==set(launch['partition_hosts'])=={'cpu','cuda'},
        'Exact separately registered scheduler policy required')
    require(duration(launch['qos_max_wall'])>=max(WALL),'Observed QoS wall limit is too short')
    for kind,name in [('cpu','cpu-short'),('cuda','gpu-short')]:
        f=launch['partitions'][kind]
        require(set(f)==set(PARTITION_KEYS) and partition(' '.join(k+'='+v for k,v in f.items()),name)==f,
            'Actual registered partition admission differs')
        hosts=launch['partition_hosts'][kind]
        require(type(hosts) is list and hosts==sorted(NODES) and set(p['hosts'][kind])<=set(hosts),
            'Complete fixed CSIS partition membership required')
        require(duration(f['MaxTime'])>=max(WALL[i] for i,n in enumerate(ORDER) if (n in GPU)==(kind=='cuda')),
            'Registered phase exceeds observed partition wall limit')
    return launch


def arguments(p,phase,previous=None):
    launch=policy(p);require(phase in ORDER,'Declared single phase required')
    index=ORDER.index(phase);require((index==0 and previous is None) or
        (index>0 and type(previous) is str and previous.isdigit()),'Exact prior job ID required')
    kind='cuda' if phase in GPU else 'cpu';wall=WALL[index];h=wall//3600;m=wall//60%60;s=wall%60
    command=['sbatch','--parsable','--hold','--no-requeue','--kill-on-invalid-dep=yes',
        '--nodes=1','--ntasks=1','--cpus-per-task=1','--partition='+launch['partitions'][kind]['PartitionName'],
        '--qos='+launch['qos'],'--account='+launch['account'],'--mem='+('4G' if phase=='closure' else '16G'),
        '--time={:02d}:{:02d}:{:02d}'.format(h,m,s),'--job-name=second71-'+phase,
        '--comment=second-v71:'+sha(canonical(p))+':'+phase,'--chdir='+str(ROOT),
        '--output='+str(RUN/phase/'slurm-%j.log'),'--error='+str(RUN/phase/'slurm-%j.log')]
    if previous is not None:command.append('--dependency=afterok:'+previous)
    if kind=='cpu':command.append('--nodelist=csis.mn1')
    else:
        command.append('--gres=gpu:a100-80gb:1')
        excluded=sorted(set(launch['partition_hosts']['cuda'])-set(p['hosts']['cuda']))
        require(excluded,'Non-GPU login node must remain excluded')
        command.append('--exclude='+','.join(excluded))
    command += [str(RUN/'research_v71'/('run_gpu.sbatch' if kind=='cuda' else 'run_cpu.sbatch')),phase,sha(canonical(p))]
    return command


def invoke(arguments):
    require(type(arguments) is list and arguments and all(type(s) is str and s for s in arguments),
        'Literal nonempty command required')
    env={k:v for k,v in os.environ.items() if not k.startswith('SBATCH_')}
    completed=subprocess.run(arguments,cwd=str(ROOT),env=env,stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=30)
    require(len(completed.stdout)+len(completed.stderr)<=128*2**10,'Bounded scheduler response required')
    return dict(arguments=arguments,returncode=completed.returncode,stdout=completed.stdout,stderr=completed.stderr)


def checked(call,arguments):
    r=call(arguments);require(r['returncode']==0,'Scheduler query failed: '+arguments[0]);return r['stdout'].strip()


def live_policy(p,call=invoke):
    launch=policy(p)
    for kind,name in [('cpu','cpu-short'),('cuda','gpu-short')]:
        actual=partition(checked(call,['scontrol','show','partition',name,'-o']),name)
        require(actual==launch['partitions'][kind],'Actual partition limits changed since registration')
        hosts=checked(call,['scontrol','show','hostnames',actual['Nodes']]).splitlines()
        require(sorted(hosts)==launch['partition_hosts'][kind],'Partition membership changed')
    qos=checked(call,['sacctmgr','-n','-P','show','qos','cpu-short','format=Name,MaxWall'])
    require(qos=='cpu-short|'+launch['qos_max_wall'],'Actual QoS wall limit changed')
    return launch


def held(p,phase,job,previous,call=invoke):
    require(type(job) is str and job.isdigit(),'Literal returned job ID required')
    raw=checked(call,['scontrol','show','job',job,'-o']);f=fields(raw);kind='cuda' if phase in GPU else 'cpu'
    expected=dict(JobId=job,JobName='second71-'+phase,JobState='PENDING',Reason='JobHeldUser',Priority='0',
        Account='faculty',QOS='cpu-short',Partition=p['launch']['partitions'][kind]['PartitionName'],
        Requeue='0',Restarts='0',NumCPUs='1',NumTasks='1',BatchFlag='1',
        WorkDir=str(ROOT),Command=str(RUN/'research_v71'/('run_gpu.sbatch' if kind=='cuda' else 'run_cpu.sbatch')),
        StdIn='/dev/null',StdOut=str(RUN/phase/('slurm-'+job+'.log')),StdErr=str(RUN/phase/('slurm-'+job+'.log')),
        KillOInInvalidDependent='Yes',Comment='second-v71:'+sha(canonical(p))+':'+phase)
    require(all(f.get(k)==v for k,v in expected.items()) and f.get('CPUs/Task')=='1' and f.get('NumNodes') in {'1','1-1'}
        and re.fullmatch(r'poonam\(\d+\)',f.get('UserId','')),'Actual held allocation identity/resources differ')
    require(duration(f['TimeLimit'])==WALL[ORDER.index(phase)]
        and memory(f['MinMemoryNode'])==(4 if phase=='closure' else 16)*2**30,
        'Actual held wall/memory request differs')
    require(f['Dependency']==('(null)' if previous is None else 'afterok:'+previous+'(unfulfilled)'),
        'Held single-success dependency differs')
    tres=fields(f['ReqTRES'].replace(',',' '))
    require(tres.get('cpu')=='1' and tres.get('node')=='1' and memory(tres['mem'])==memory(f['MinMemoryNode']),
        'Actual requested CPU/node/memory resources differ')
    allowed={'cpu','node','mem','billing'}
    if kind=='cuda':
        allowed|={'gres/gpu','gres/gpu:a100-80gb'}
        require(tres.get('gres/gpu')=='1' and tres.get('gres/gpu:a100-80gb','1')=='1'
            and f.get('TresPerNode')=='gres/gpu:a100-80gb:1' and f['ReqNodeList']=='(null)',
            'Exactly one typed GPU and scheduler-selected node required')
        actual=set(checked(call,['scontrol','show','hostnames',f['ExcNodeList']]).splitlines())
        require(actual==set(p['launch']['partition_hosts']['cuda'])-set(p['hosts']['cuda']),
            'Actual node exclusion pool differs')
    else:require(f['ReqNodeList']=='csis.mn1' and f['ExcNodeList']=='(null)','Inherited CPU node request differs')
    require(set(tres)<=allowed,'Unregistered requested scheduler resource')
    return dict(raw=raw,fields=f,phase=phase,job_id=job,actual_held_job_verified=True)


def preflight(p,call=invoke):
    """No model, calibration, tokenizer or likelihood execution on the login host."""
    live_policy(p,call)
    require(checked(call,['git','rev-parse','HEAD'])==CHECKOUT and not checked(call,['git','status','--porcelain']),
        'Clean inherited numerical checkout required')
    queue=checked(call,['squeue','-h','-u','poonam','-o','%i|%j|%T'])
    require(not any('second' in row.lower() for row in queue.splitlines()),'Existing Second job; no competing or duplicate launch')
    inputs=p['inputs']
    def leaf(e):
        require(type(e) is dict and set(e)=={'path','bytes','sha256'},'Exact immutable input leaf required')
        h={k:e[k] for k in ['bytes','sha256']};read(Path(e['path']),h,maximum=2*2**30,retain=False)
        return h
    for group,entries in inputs.items():
        if type(entries) is dict and set(entries)=={'path','bytes','sha256'}:leaf(entries)
        else:
            require(type(entries) is dict,'Exact input groups required')
            for e in entries.values():leaf(e)
    def input_object(group,name):
        e=inputs[group][name];return obj(Path(e['path']),{k:e[k] for k in ['bytes','sha256']})
    v67=input_object('service','v67_program');v68=input_object('quality','registration')
    require(inputs['service']['v67_program']['sha256']=='11e0db146e79330852f550a1cc3b2dd7568a66cdfe8006b004dca3840149cc30'
        and inputs['quality']['registration']['sha256']==p['v68_sha256'],'Predecessor registration differs')
    for n in ['v67_primary','v67_supplemental']:
        q=input_object('service',n);require(q['status']=='verified' and q['program_sha256']==inputs['service']['v67_program']['sha256'],
            'Both completed V67 terminal audits required before even held submission')
    for n in ['v67_primary_entry','v67_supplemental_entry']:
        q=input_object('service',n);require(q['status']=='complete' and q['error'] is None,'Both completed V67 entries required')
    for n in ['checks','data','audit']:
        q=input_object('quality',n);require(q['status']=='complete' and q['error'] is None
            and q['registration_sha256']==p['v68_sha256'],'Actual V68 success required before held submission')
    require(input_object('quality','audit')['result']['status']=='verified','Actual V68 saved-data audit required')
    for group in [v67['prior_sources'],v67['new_sources'],v68['new_sources'],p['new_sources'],p['dependency_files'],p['historical_ledgers']]:
        for path,e in group.items():read(Path(path),e,maximum=128*2**20,retain=False)
    e=inputs['gpu_registration'];gpu=obj(Path(e['path']),{k:e[k] for k in ['bytes','sha256']})
    require(e['sha256']=='620076c67ae79ee56de784ecd4c6e49ef3b4b22f45742f72956821b1e416cf54','Historical GPU sources must be bound')
    for path,h in gpu['sources'].items():require(read(ROOT/path,retain=False)['sha256']==h,'Frozen historical GPU source changed')
    manifest=read(MANIFEST,maximum=4096)
    require(sha(manifest)==MANIFEST_SHA and manifest==(IMAGE_SHA+'  '+str(IMAGE)+'\n').encode(),
        'Inherited container manifest differs')
    require(read(IMAGE,maximum=2*2**30,retain=False)['sha256']==IMAGE_SHA,'Inherited CPU image changed')
    return dict(queue=queue,actual_input_source_container_bytes_checked=True,
        actual_numerical_checks_deferred_to_first_bounded_worker=True)


def before_release(p,expected,jobs,call):
    require(obj(RUN/'program.json')==p and obj(RUN/'registration.json')==dict(program_sha256=expected),
        'Registration changed while jobs were held')
    for path,e in p['new_sources'].items():read(Path(path),e,retain=False)
    live_policy(p,call)
    queue=checked(call,['squeue','-h','-u','poonam','-o','%i|%j|%T'])
    actual={row.split('|')[0] for row in queue.splitlines() if 'second' in row.lower()}
    require(actual=={r['job_id'] for r in jobs},'Competing or missing Second jobs before release')
    for row in jobs:held(p,row['phase'],row['job_id'],row['previous_job_id'],call)


def launch(expected,call=invoke):
    p=obj(RUN/'program.json');require(sha(canonical(p))==expected and obj(RUN/'registration.json')==dict(program_sha256=expected),
        'Immutable campaign registration required')
    policy(p);require(not (RUN/'launch-intent.json').exists() and all(not (RUN/n).exists() for n in ORDER),
        'One-use launch or phase path already exists; reconcile instead of retry')
    admission=preflight(p,call)
    write(RUN/'launch-intent.json',dict(registration_sha256=expected,admission=admission,
        phases=list(ORDER),automatic_retry=False,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    jobs=[];error=None
    try:
        previous=None
        for phase in ORDER:
            arguments_=arguments(p,phase,previous)
            write(RUN/phase/'submission-intent.json',dict(arguments=arguments_,registration_sha256=expected))
            response=call(arguments_);write(RUN/phase/'submission-response.json',response)
            job=response['stdout'].strip()
            require(response['returncode']==0 and re.fullmatch(r'[0-9]+',job) is not None
                and job not in {r['job_id'] for r in jobs},'Unknown/failed/duplicate submission response; do not retry')
            row=dict(phase=phase,job_id=job,previous_job_id=previous);jobs.append(row)
            actual=held(p,phase,job,previous,call);write(RUN/phase/'held-verification.json',actual)
            write(RUN/phase/'job-binding.json',dict(schema='quality-held-job-binding-v71',
                registration_sha256=expected,phase=phase,job_id=job,submission_state='held-before-release'))
            previous=job
        # Recheck all nine while none can run, then release descendants first.
        # The first CPU phase is released last; every successor still has afterok.
        before_release(p,expected,jobs,call)
        write(RUN/'chain-ready.json',dict(registration_sha256=expected,jobs=jobs,all_nine_held_and_bound=True))
        for row in reversed(jobs):
            phase=row['phase'];args=['scontrol','release',row['job_id']]
            write(RUN/phase/'release-intent.json',dict(arguments=args,registration_sha256=expected))
            response=call(args);write(RUN/phase/'release-response.json',response)
            require(response['returncode']==0,'Unknown/failed release; inspect actual jobs without repeating commands')
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        write(RUN/'launch-completion.json',dict(status='complete' if error is None else 'failed',error=error,
            registration_sha256=expected,jobs=jobs,automatic_retry=False,all_uncertain_outcomes_preserved=True,
            no_automatic_cancellation_or_rollback=True))
    return jobs


if __name__=='__main__':
    require(sys.platform=='linux' and Path(__file__).resolve()==RUN/'research_v71/submission.py'
        and len(sys.argv)==2,'Pinned Linux one-use submission entry required')
    print(canonical(dict(jobs=launch(sys.argv[1]))).decode('ascii'))
