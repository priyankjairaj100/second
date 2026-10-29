"""One-use read-only output audit. Original failed job state is preserved."""
import os,sys,json,subprocess,time,resource,signal,platform
from pathlib import Path
RUN=Path(__file__).resolve().parents[1];sys.path.insert(0,str(RUN))
from research_v133.audit import enc,ident,validate

def read(e):
    p=Path(e['path']);assert p.is_file() and not p.is_symlink()
    b=p.read_bytes();assert ident(b)=={k:e[k] for k in ('bytes','sha256')};return b

def save(p,v):
    with p.open('xb') as f:f.write(enc(v));f.flush();os.fsync(f.fileno())

def audit(p,name):
    x=p['controls'][name]; source=Path(p['producer']['path']).parent
    old=json.loads(read(p['producer']));h=ident(read(p['producer']))['sha256']
    assert h==p['producer_registration_sha256']
    for n,e in old['sources'].items():read(dict(path=str(source/n),**e))
    job=p['producer_jobs'][name]
    q=subprocess.check_output(['sacct','-X','-j',str(job),'-n','-P','--format=State,ExitCode'],text=True).strip()
    assert q=='FAILED|1:0', q
    assert not (source/name/'completion.json').exists()
    err=read(x['stderr']).decode();assert err.rstrip().endswith('TypeError: Object of type bytes is not JSON serializable')
    assert "save(out/'completion.json',r)" in err and 'research_v132/worker.py' in err
    observed={f.name for f in (source/name).iterdir()};assert observed==set(x['files'])
    raw={n:read(e) for n,e in x['files'].items()}
    attempt=json.loads(raw['attempt.json']);assert attempt==dict(registration_sha256=h,phase=name,job_id=str(job))
    checks=json.loads(read(p['qualification']));assert checks['status']=='complete' and checks['result']['tests']==331 and checks['registration_sha256']==h
    qc=subprocess.check_output(['sacct','-X','-j',checks['job_id'],'-n','-P','--format=State,ExitCode'],text=True).strip();assert qc=='COMPLETED|0:0'
    profile,role=name.split('__');bound=old['profiles'][profile];endpoint=bound['endpoints'][role]
    original=json.loads(read(endpoint['completion']));assert original['status']=='complete' and original['complete_model']
    rows=json.loads(read(old['calibration_records'][profile]))['records'];ids=original['request']['retained_ids'];retained=[r for r in rows if r['id'] in ids]
    assert [r['id'] for r in retained]==ids and len(ids)==int(role[-1])
    for e in [bound['calibration'],*bound['checkpoint'].values()]:read(e)
    anchor=json.loads(read(bound['anchor']));assert ident(enc(anchor))['sha256']==bound['anchor']['sha256']
    stages=[json.loads(raw['stage-%03d.json'%i]) for i in range(bound['blocks']*4)]
    result=validate(raw['model.bin'],anchor,json.loads(raw['codes.json']),json.loads(raw['construction.json']),stages,retained,read(endpoint['model']),old['point_policy'])
    result.update(profile=profile,role=role,retained_ids=ids,complete_model=True,producer_job_id=job,producer_state='FAILED',producer_exit_code='1:0',producer_completion_missing=True,closure='independent read-only artifact audit after JSON bytes serialization failure',quality_evaluation=False,calibration_repeated=False,native_execution_sidecar_saved=False,full_successor_state_audit_repeated=False)
    for e in x['files'].values():read(e)
    return result

def main(name,h):
    p=json.loads((RUN/'program.json').read_bytes());assert ident((RUN/'program.json').read_bytes())['sha256']==h and p['directory']==str(RUN)
    jobs=json.loads((RUN/'jobs-initial.json').read_text());assert jobs['registration_sha256']==h and str(jobs['jobs'][name])==os.environ['SLURM_JOB_ID']
    assert sys.platform=='linux' and platform.node()=='csis.mn1' and not sys.flags.optimize
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2);resource.setrlimit(resource.RLIMIT_CPU,(300,301));resource.setrlimit(resource.RLIMIT_FSIZE,(128*2**20,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    def expire(*_):raise TimeoutError('Audit cap reached')
    signal.signal(signal.SIGALRM,expire);signal.alarm(570)
    out=RUN/name;out.mkdir(exist_ok=False);start=time.monotonic()
    r=dict(schema='sequential-output-audit-v133',registration_sha256=h,job_id=os.environ['SLURM_JOB_ID'],phase=name,status='failed',error=None,result=None)
    try:
        import unittest
        test=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromName('research_v133.test_audit'));assert test.wasSuccessful() and test.testsRun==8
        for n,e in p['sources'].items():read(dict(path=str(RUN/n),**e))
        r['result']=audit(p,name);r['status']='complete'
    except BaseException as e:
        import traceback;traceback.print_exc();r['error']=dict(type=type(e).__name__,message=str(e))
    finally:
        r.update(process_cpu_seconds=time.process_time(),elapsed_seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,artifacts={})
        if r['status']=='complete':r['artifacts']['model.bin']={k:p['controls'][name]['files']['model.bin'][k] for k in ('bytes','sha256')}
        r['artifact_storage']='audited immutable producer path; model is not copied into audit output'
        save(out/'completion.json',r)
    assert r['status']=='complete',r['error']
if __name__=='__main__':main(*sys.argv[1:])
