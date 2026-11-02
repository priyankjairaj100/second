"""One-use software entry. Its only inputs are source bytes and generated data."""
import datetime,hashlib,json,os,platform,resource,shutil,signal,subprocess,sys,time,traceback
from pathlib import Path
RUN=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(RUN))

def write(path,obj):
    with path.open('x') as f:
        json.dump(obj,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

def verify(program):
    for name,info in program['sources'].items():
        p=RUN/name
        if p.is_symlink() or not p.is_file():raise ValueError('Unsafe source '+name)
        raw=p.read_bytes()
        if len(raw)!=info['bytes'] or hashlib.sha256(raw).hexdigest()!=info['sha256']:
            raise ValueError('Source mismatch '+name)

def main(expected):
    if sys.platform!='linux' or platform.node()!='csis.mn1' or not os.environ.get('SLURM_JOB_ID','').isdigit():
        raise ValueError('Pinned Linux Slurm host required')
    raw=(RUN/'program.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Program hash mismatch')
    program=json.loads(raw)
    if json.loads((RUN/'registration.json').read_text())!={'program_sha256':expected}:raise ValueError('Registration mismatch')
    resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2)
    resource.setrlimit(resource.RLIMIT_FSIZE,(2*2**30,)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_CPU,(300,301))
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    signal.signal(signal.SIGXCPU,lambda *args: (_ for _ in ()).throw(RuntimeError('CPU limit')))
    start=time.perf_counter_ns();cpu=time.process_time_ns()
    child=resource.getrusage(resource.RUSAGE_CHILDREN)
    write(RUN/'entry-start.json',dict(program_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),affinity=sorted(os.sched_getaffinity(0))))
    error=None;steps=[];runtime={}
    try:
        verify(program)
        import numpy,gmpy2
        if platform.python_version()!='3.12.14' or numpy.__version__!='2.3.5' or gmpy2.version()!='2.3.2':
            raise ValueError('Pinned Python/numerical runtime differs')
        for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
            if os.environ.get(key)!='1':raise ValueError('Thread environment differs')
        runtime=dict(python=sys.version,numpy=numpy.__version__,gmpy2=gmpy2.version(),machine=platform.machine(),
            compiler=subprocess.check_output(['cc','--version'],text=True).splitlines()[0])
        out=RUN/'outputs';out.mkdir()
        codec=out/'codec';codec.mkdir()
        for name in ('check.py','decode.c','fast_decode.py'):
            shutil.copyfile(RUN/'research_v75'/name,codec/name)
        def run(name,args,cwd):
            tick=time.perf_counter_ns()
            with (out/(name+'.log')).open('xb') as log:
                done=subprocess.run(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=550)
            steps.append(dict(name=name,exit=done.returncode,elapsed_ns=time.perf_counter_ns()-tick))
            if done.returncode:raise RuntimeError(name+' failed')
            usage=resource.getrusage(resource.RUSAGE_CHILDREN)
            used=(time.process_time_ns()-cpu)/1e9+usage.ru_utime+usage.ru_stime-child.ru_utime-child.ru_stime
            if used>602:raise RuntimeError('Aggregate software CPU cap exceeded')
        run('codec',[sys.executable,'-B',str(codec/'check.py'),str(RUN)],codec)
        report=json.loads((codec/'software-results.json').read_text())
        assert all(v['tests']==8 and v['passed'] and 'skipped=' not in v['log'] for v in report['legacy_tests'].values())
        assert report['differential_cases']==dict(valid=40,mutated=6810,boundary=1600,accepted_mutations=2710,rejected_mutations=4100)
        run('sanitize-build',['cc','-std=c11','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all',
            '-fno-omit-frame-pointer','-Wall','-Wextra','-Werror',str(RUN/'research_v76/sanitize_driver.c'),'-o','sanitize'],codec)
        run('sanitize',[str(codec/'sanitize')],codec)
        run('tokens',[sys.executable,'-B','-m','research_v76.check_tokens',str(out/'token-results.json')],RUN)
        report=json.loads((out/'token-results.json').read_text())
        assert report['coefficient_parity_cases']==16 and len(report['benchmarks'])==6
        assert all(v==dict(count=21,errors=0,failures=0,skips=0) for v in report['legacy_tests'].values())
        verify(program)
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=str(exc));traceback.print_exc()
    usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    child_ns=round((usage.ru_utime+usage.ru_stime-child.ru_utime-child.ru_stime)*1e9)
    own=time.process_time_ns()-cpu
    if own+child_ns>602*10**9:error=dict(type='BudgetExceeded',message='Aggregate CPU above602 seconds')
    files={str(p.relative_to(RUN)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        for p in (RUN/'outputs').rglob('*') if p.is_file() and (p.suffix in ('.json','.log','.so') or p.name=='sanitize')}
    receipt=dict(status='complete' if error is None else 'failed',error=error,steps=steps,runtime=runtime,
        program_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],hostname=platform.node(),
        process_cpu_ns=own,waited_child_cpu_ns=child_ns,aggregate_cpu_ns=own+child_ns,
        elapsed_ns=time.perf_counter_ns()-start,maximum_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        waited_child_maximum_rss_kib=usage.ru_maxrss,outputs=files,empirical_execution=False,
        finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write(RUN/'completion.json',receipt)
    if error:raise RuntimeError('V76 one-use qualification failed; do not retry')

if __name__=='__main__':main(sys.argv[1])
