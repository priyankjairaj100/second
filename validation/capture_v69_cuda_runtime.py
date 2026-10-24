"""Once-only registered runtime inventory; no model/data/inference/CUDA initialization."""
import sys,os,resource,signal,time,platform,json,hashlib
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/cuda-runtime-v69-20261018-a'
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(b):return hashlib.sha256(b).hexdigest()
def write(n,o):
    with (RUN/n).open('xb') as f:f.write(canonical(o));f.flush();os.fsync(f.fileno())
def main(expected):
    tick=time.perf_counter_ns();raw=(RUN/'program.json').read_bytes();p=json.loads(raw)
    assert digest(raw)==expected and raw==canonical(p) and p['directory']==str(RUN)
    assert Path(__file__).resolve()==RUN/'capture_v69_cuda_runtime.py' and sys.platform=='linux' and sys.flags.optimize==0 and sys.dont_write_bytecode
    assert os.environ.get('SLURM_JOB_ID','').isdigit() and platform.node() in p['hosts']
    assert sys.executable==p['interpreter'] and os.environ.get('CUBLAS_WORKSPACE_CONFIG')==':4096:8'
    assert all(os.environ.get(n)=='1' for n in p['thread_variables'])
    cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
    def fail(*a):raise TimeoutError('Registered runtime inventory bound reached')
    signal.signal(signal.SIGXCPU,fail);signal.signal(signal.SIGALRM,fail);signal.alarm(600)
    for k,v in [(resource.RLIMIT_CPU,(300,301)),(resource.RLIMIT_AS,(128*2**40,)*2),(resource.RLIMIT_FSIZE,(16*2**20,)*2),(resource.RLIMIT_CORE,(0,0))]:resource.setrlimit(k,v)
    write('attempt.json',dict(registration_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],host=platform.node(),affinity_cpus=[cpu]))
    result=dict(schema='cuda-runtime-inventory-receipt-v69',status='failed',error=None,registration_sha256=expected,
        job_id=os.environ['SLURM_JOB_ID'],host=platform.node(),model_inference=False,quality_data_read=False)
    try:
        for n,h in p['sources'].items():assert digest((ROOT/n).read_bytes())==h,n
        for n,h in p['new_sources'].items():assert digest((RUN/n).read_bytes())==h,n
        assert digest(Path(p['historical_registration']).read_bytes())==p['historical_registration_sha256']
        sys.path.insert(0,str(ROOT))
        from research_v47.campaign import runtime
        r=runtime()
        import torch
        assert not torch.cuda.is_initialized()
        for name,m in list(sys.modules.items()):
            if name.split('.')[0] in {'src','scripts'} or name.startswith('research_v'):
                f=getattr(m,'__file__',None)
                if f:
                    rel=str(Path(f).resolve().relative_to(ROOT));assert rel in p['sources'] and digest(Path(f).read_bytes())==p['sources'][rel]
        write('runtime.json',r)
        result.update(status='complete',runtime_sha256=digest(canonical(r)),cuda_initialized=False,source_files_verified=len(p['sources']))
    except BaseException as e:result['error']=dict(type=type(e).__name__,message=str(e))
    child=resource.getrusage(resource.RUSAGE_CHILDREN)
    result.update(process_cpu_ns=time.process_time_ns(),waited_child_cpu_ns=round((child.ru_utime+child.ru_stime)*1e9),elapsed_ns=time.perf_counter_ns()-tick,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    write('receipt.json',result)
    assert result['status']=='complete',result['error']
if __name__=='__main__':main(*sys.argv[1:])
