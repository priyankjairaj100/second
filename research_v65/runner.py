"""One-attempt data-only checks/selection/audit in the pinned Linux container."""
import hashlib,json,os,resource,sys,time,traceback,unittest
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/disjoint-data-v65-20261016-a'
V63=ROOT/'local_runs/lossless-control-v63-20261016-a';V64=ROOT/'local_runs/modern-service-checks-v64-20261016-a'
CAPS={'checks':dict(cpu=300,wall=600),'data':dict(cpu=600,wall=1200),'audit':dict(cpu=600,wall=900)}
def require(x,m):
    if not x:raise ValueError(m)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def new(n,x):
    with (RUN/n).open('xb') as f:f.write(canonical(x));f.flush();os.fsync(f.fileno())
def bound(path,e):
    p=Path(path);require(p.is_file() and not any(q.is_symlink() for q in (p,*p.parents)) and p.stat().st_size==e['bytes']<=128*2**20,'Unsafe/bounded input')
    a=p.stat();b=p.read_bytes();c=p.stat();require((a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(c.st_ino,c.st_size,c.st_mtime_ns,c.st_ctime_ns) and info(b)==e,'Input changed');return b

def execute(path,expected,trial):
    require(sys.platform=='linux' and Path(path)==RUN/'registration.json' and Path(__file__).resolve()==RUN/'research_v65/runner.py' and os.environ.get('SLURM_JOB_ID','').isdigit(),'Pinned Linux Slurm path required')
    require(trial in CAPS,'Unknown trial')
    for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:require(os.environ.get(k)=='1','Single thread required')
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});cap=CAPS[trial]
    for k,v in [(resource.RLIMIT_CPU,(cap['cpu'],cap['cpu']+1)),(resource.RLIMIT_AS,(4*2**30,)*2),(resource.RLIMIT_FSIZE,(128*2**20,)*2),(resource.RLIMIT_CORE,(0,0))]:resource.setrlimit(k,v)
    raw=Path(path).read_bytes();p=json.loads(raw)
    require(raw==canonical(p) and info(raw)['sha256']==expected and p['schema']=='disjoint-c4-data-admission-v65' and p['caps']==CAPS and p['run_directory']==str(RUN) and p['allowance_cpu_seconds']==1506 and p['automatic_retry'] is False,'Registration differs')
    from research_v65 import data
    require(p['policy']==data.POLICY and p['expected_tests']==9 and len(p['historical_sources'])==432 and len(p['v63_sources'])==7 and len(p['v64_sources'])==6,'Frozen scope/census')
    require(not (RUN/(trial+'.json')).exists(),'Existing result')
    new(trial+'-start.json',dict(trial=trial,registration_sha256=expected,job_id=os.environ['SLURM_JOB_ID']))
    tick=time.perf_counter_ns();cpu=time.process_time_ns();child=resource.getrusage(resource.RUSAGE_CHILDREN);error=None;result=None
    try:
        def bindings():
            for n,h in p['historical_sources'].items():require(info((ROOT/n).read_bytes())['sha256']==h,'Historical source changed')
            for group,root in [('new_sources',RUN),('v63_sources',V63),('v64_sources',V64)]:
                for n,e in p[group].items():bound(root/n,e)
            for group in ['prior_inputs','tokenizer_runtime_files','v64_receipts']:
                for n,e in p[group].items():bound(n,e)
            from research_v61.campaign import runtime
            require(runtime()==p['base_runtime'],'Base runtime changed')
            require(data.history_inventory(ROOT)==p['history'],'Historical metadata changed')
        bindings()
        if trial=='checks':
            tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('research_v65.test_data'))
            result=dict(tests=tests.testsRun,skipped=len(tests.skipped),failures=len(tests.failures),errors=len(tests.errors),corpus_parsed=False)
            require(tests.wasSuccessful() and tests.testsRun==9 and not tests.skipped,'Linux software gate failed')
        else:
            check=json.loads((RUN/'checks.json').read_bytes());require(check['status']=='complete' and check['registration_sha256']==expected and check['result']['tests']==9 and check['result']['skipped']==0,'Passing bound checks required')
            if trial=='audit':
                previous=json.loads((RUN/'data.json').read_bytes());require(previous['status']=='complete' and previous['registration_sha256']==expected,'Passing data phase required')
            result=data.prepare(ROOT,RUN,p) if trial=='data' else data.audit(ROOT,RUN,p)
        bindings()
    except Exception as exc:error=dict(type=type(exc).__name__,message=str(exc));traceback.print_exc()
    now=resource.getrusage(resource.RUSAGE_CHILDREN);cc=round((now.ru_utime+now.ru_stime-child.ru_utime-child.ru_stime)*1e9);pc=time.process_time_ns()-cpu
    if pc+cc>(cap['cpu']+2)*10**9:error=dict(type='BudgetExceeded',message='Observed process and child CPU exceeds trial allowance')
    new(trial+'.json',dict(status='complete' if error is None else 'failed',trial=trial,registration_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],caps=cap,result=result,error=error,elapsed_ns=time.perf_counter_ns()-tick,process_cpu_ns=pc,waited_child_cpu_ns=cc,combined_observed_cpu_ns=pc+cc,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,model_inference=False,quality_evaluation=False))
    require(error is None,'Failed one-use trial; no retry')
if __name__=='__main__':
    sys.path[:0]=[str(RUN),str(ROOT)]
    require(len(sys.argv)==4,'Expected registration/hash/trial');execute(*sys.argv[1:])
