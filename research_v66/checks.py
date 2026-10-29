"""One-attempt software-only Linux check runner; no empirical inputs."""
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time
import traceback
import unittest

ROOT=Path('/nfs_home/users/poonam/second-20261010')
PRIOR=ROOT/'local_runs/lossless-control-v63-20261016-a'
V64=ROOT/'local_runs/modern-service-checks-v64-20261016-a'
V65=ROOT/'local_runs/disjoint-data-v65-20261016-a'
RUN=ROOT/'local_runs/complete-service-checks-v66-20261016-a'
TEST_NAMES=['research_v63.test_control','research_v63.test_runner','research_v64.test_service','research_v64.test_linux','research_v66.test_operations','research_v66.test_linux']
CAPS=dict(cpu=300,hard_cpu=301,wall=600,address_space_bytes=16*2**30,file_bytes=8*2**20)


def require(value,message):
    if not value:raise ValueError(message)


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def new(name,value):
    with (RUN/name).open('xb') as f:f.write(canonical(value));f.flush();os.fsync(f.fileno())


def bound(path,expected):
    p=Path(path)
    require(p.is_file() and not any(q.is_symlink() for q in (p,*p.parents)),'Unsafe input')
    a=p.stat();require(a.st_size==expected['bytes'] and a.st_size<=128*2**20,'Bounded input extent')
    b=p.read_bytes();c=p.stat()
    require((a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(c.st_ino,c.st_size,c.st_mtime_ns,c.st_ctime_ns)
            and sha(b)==expected['sha256'],'Input changed')
    return b


def execute(path,expected):
    require(sys.platform=='linux' and Path(path)==RUN/'registration.json'
            and Path(__file__).resolve()==RUN/'research_v66/checks.py'
            and os.environ.get('SLURM_JOB_ID','').isdigit(),'Pinned Linux Slurm path required')
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        require(os.environ.get(k)=='1','Single thread required')
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_CPU,(CAPS['cpu'],CAPS['hard_cpu']))
    resource.setrlimit(resource.RLIMIT_AS,(CAPS['address_space_bytes'],)*2)
    resource.setrlimit(resource.RLIMIT_FSIZE,(CAPS['file_bytes'],)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    raw=Path(path).read_bytes();p=json.loads(raw)
    require(raw==canonical(p) and sha(raw)==expected and p['schema']=='complete-service-software-qualification-v66'
            and p['caps']==CAPS and p['test_names']==TEST_NAMES and p['expected_tests']==44
            and p['run_directory']==str(RUN) and p['empirical_execution'] is False
            and p['automatic_retry'] is False and p['allowance_cpu_seconds']==602,'Registration differs')
    require(len(p['historical_sources'])==432 and len(p['v63_sources'])==7 and len(p['v64_sources'])==6 and len(p['v65_sources'])==5,'Frozen source census')
    require(not (RUN/'completion.json').exists(),'Existing completion')
    new('start.json',dict(status='started',slurm_job_id=os.environ['SLURM_JOB_ID'],registration_sha256=expected))
    tick=time.perf_counter_ns();cpu=time.process_time_ns();child_before=resource.getrusage(resource.RUSAGE_CHILDREN);result=None;error=None
    try:
        def bindings():
            for n,h in p['historical_sources'].items():
                require(not Path(n).is_absolute() and '..' not in Path(n).parts,'Unsafe source path')
                require(sha((ROOT/n).read_bytes())==h,'Historical source changed')
            for group,root in [('new_sources',RUN),('v63_sources',PRIOR),('v64_sources',V64),('v65_sources',V65),('dependency_files',PRIOR/'deps')]:
                for n,e in p[group].items():
                    require(not Path(n).is_absolute() and '..' not in Path(n).parts,'Unsafe source path')
                    bound(root/n,e)
            for key,e in p['prior_software_data_receipts'].items():bound(Path(key),e)
            for name in ('registration.json','audit.json'):
                bound(PRIOR/name,p['v63_receipts'][name])
            from research_v61.campaign import runtime
            require(runtime()==p['base_runtime'],'Runtime changed')
        bindings()
        receipt=json.loads((PRIOR/'audit.json').read_bytes())
        require(receipt['status']=='complete' and receipt['result']['status']=='verified','Completed V63 audit required')
        suite=unittest.defaultTestLoader.loadTestsFromNames(TEST_NAMES)
        tests=unittest.TextTestRunner(verbosity=2).run(suite)
        result=dict(tests=tests.testsRun,skipped=len(tests.skipped),failures=len(tests.failures),errors=len(tests.errors),
                    fixture_only=True,actual_tiny_numerical_case=True,five_arms_fresh_state_fixture=True,empirical_inputs_opened=False)
        require(tests.wasSuccessful() and tests.testsRun==44 and not tests.skipped,'Software gate failed')
        bindings()
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc));traceback.print_exc()
    child_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    child_cpu_ns=round(((child_after.ru_utime+child_after.ru_stime)-(child_before.ru_utime+child_before.ru_stime))*1e9)
    process_cpu_ns=time.process_time_ns()-cpu
    if process_cpu_ns+child_cpu_ns > p['allowance_cpu_seconds']*10**9:
        error=dict(type='BudgetExceeded',message='Observed process and waited-child CPU exceeds fresh allowance')
    new('completion.json',dict(status='complete' if error is None else 'failed',error=error,result=result,
        slurm_job_id=os.environ['SLURM_JOB_ID'],registration_sha256=expected,caps=CAPS,
        process_cpu_ns=process_cpu_ns,waited_child_cpu_ns=child_cpu_ns,combined_observed_cpu_ns=process_cpu_ns+child_cpu_ns,elapsed_ns=time.perf_counter_ns()-tick,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,empirical_execution=False))
    require(error is None,'Qualification failed; preserve, no retry')


if __name__=='__main__':
    sys.path[:0]=[str(PRIOR/'deps'),str(RUN),str(V65),str(V64),str(PRIOR),str(ROOT)]
    require(len(sys.argv)==3,'Expected registration path and hash')
    execute(*sys.argv[1:])
