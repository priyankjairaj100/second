"""Bounded, one-attempt invocation of frozen V61 auditors on existing artifacts."""
from pathlib import Path, PurePosixPath
import argparse
import faulthandler
import hashlib
import json
import os
import resource
import sys
import time

ROOT = Path('/nfs_home/users/poonam/second-20261010')
RUN = ROOT/'local_runs/audit-recovery-v62-20261015-a'
CAMPAIGN = ROOT/'local_runs/full-precision-service-v61-20261014-a'
PROGRAM = '6632712f7b79b49734790fa6fc173ec7e5ee70f542fe8f8a0c3ef3ff2171ea2d'
FAILURE = 'd0ad4f1085b5c8cb5148de2a6608f8cc1d844661e7262882da2f483f5f9e8094'
LIMITS = dict(cpu_seconds=3600,cpu_hard_seconds=3601,address_space_bytes=16*2**30,
              file_size_bytes=64*2**20,slurm_wall_seconds=3900,threads=1)
THREADS = ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')


def require(value,message):
    if not value:raise ValueError(message)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def strict(raw):
    def pairs(rows):
        d={}
        for k,v in rows:
            require(k not in d,'Duplicate JSON key');d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def digest(raw):return hashlib.sha256(raw).hexdigest()


def read_bound(path,expected,*,maximum=64*2**20):
    path=Path(path)
    require(path.is_absolute() and not any(p.is_symlink() for p in (path,*path.parents)) and path.is_file(),'Unsafe or missing input')
    before=path.stat();require(before.st_size<=maximum,'Metadata exceeds bound')
    raw=path.read_bytes();after=path.stat()
    require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'Input changed during read')
    require(dict(bytes=len(raw),sha256=digest(raw))==expected,'Input commitment differs: '+str(path))
    return raw


def validate_plan(p,path,expected_sha):
    require(Path(path)==RUN/'registration.json','Unexpected recovery registration path')
    require(digest(canonical(p))==expected_sha,'Registration digest differs')
    require(p['schema']=='second-artifact-audit-recovery-v62' and p['campaign']==str(CAMPAIGN)
        and p['run_directory']==str(RUN) and p['program_sha256']==PROGRAM,'Recovery identity differs')
    require(p['failure_archive_sha256']==FAILURE and p['original_outcomes']=={'13569':'TIMEOUT','13570':'CANCELLED'},'Original failure must stay explicit')
    require(p['limits']==LIMITS and p['fresh_support_cpu_seconds']==7204,'Recovery limits changed')
    require(p['trials']==['primary','postrun'] and p['automatic_retry'] is False
        and p['numerical_execution'] is False and p['old_campaign_mutation'] is False,'Recovery scope changed')
    require(len(p['numerical_sources'])==432,'Incomplete frozen source inventory')
    require(set(p['wrapper_sources'])=={'audit_recovery.py','PROTOCOL.txt','test_audit_recovery.py'},'Recovery source inventory differs')
    for n in p['numerical_sources']:
        q=PurePosixPath(n);require(not q.is_absolute() and '..' not in q.parts and str(q)==n,'Unsafe source path')
    for n in p['metadata_inputs']:
        q=Path(n);require(q.is_absolute() and ROOT in q.parents,'Input outside frozen repository')
    require(len(p['metadata_inputs'])==1285 and len(p['binary_inputs'])==33,'Failure capture input census differs')
    return p


def new(path,value):
    with Path(path).open('xb') as f:
        f.write(canonical(value));f.flush();os.fsync(f.fileno())


def check_bindings(p):
    for name,entry in p['wrapper_sources'].items():read_bound(RUN/name,entry)
    read_bound(RUN/'failure-manifest.json',p['failure_manifest'])
    for name,expected in p['numerical_sources'].items():
        path=ROOT/name
        require(path.is_file() and not path.is_symlink() and digest(path.read_bytes())==expected,'Frozen source changed: '+name)
    for name,entry in p['metadata_inputs'].items():read_bound(Path(name),entry)
    require(digest((CAMPAIGN/'program.json').read_bytes())==PROGRAM,'Frozen program changed')
    require(all(not (CAMPAIGN/n).exists() and not (CAMPAIGN/n).is_symlink() for n in ('artifact-audit.json','postrun-audit.json')),'Original absent audit paths changed')


def check_primary_link(p):
    receipt=strict((RUN/'primary-wrapper.json').read_bytes())
    require(receipt['status']=='complete' and receipt['trial']=='primary'
        and receipt['registration_sha256']==digest(canonical(p)),'Primary wrapper not complete for this registration')
    a=strict(read_bound(RUN/'primary.json',receipt['audit_output']))
    require(a['status']=='verified' and a['program_sha256']==PROGRAM and a['slurm_job_id']==receipt['slurm_job_id'],
        'Primary output linkage differs')


def execute(plan_path,expected_sha,trial):
    require(trial in ('primary','postrun'),'Unknown audit trial')
    require(sys.platform=='linux' and os.environ.get('SLURM_JOB_ID','').isdigit(),'Linux Slurm required')
    require(all(os.environ.get(k)=='1' for k in THREADS),'Single-thread environment required')
    available=os.sched_getaffinity(0)
    require(bool(available),'No available affinity CPU')
    os.sched_setaffinity(0,{min(available)})
    require(len(os.sched_getaffinity(0))==1,'Exactly one affinity CPU required')
    resource.setrlimit(resource.RLIMIT_CPU,(LIMITS['cpu_seconds'],LIMITS['cpu_hard_seconds']))
    resource.setrlimit(resource.RLIMIT_AS,(LIMITS['address_space_bytes'],)*2)
    resource.setrlimit(resource.RLIMIT_FSIZE,(LIMITS['file_size_bytes'],)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    start,cpu=time.monotonic_ns(),time.process_time_ns()
    path=Path(plan_path);raw=path.read_bytes();p=strict(raw)
    require(raw==canonical(p),'Canonical registration required')
    validate_plan(p,path,expected_sha)
    require(Path(__file__).resolve()==RUN/'audit_recovery.py','Wrong executed recovery source path')
    for name in (trial+'.json',trial+'-wrapper.json',trial+'-start.json'):
        require(not (RUN/name).exists() and not (RUN/name).is_symlink(),'Attempt/output already exists')
    # The marker is written before reading large metadata; a failed attempt cannot be retried.
    initial=dict(schema='second-audit-recovery-attempt-v62',trial=trial,registration_sha256=expected_sha,
        slurm_job_id=os.environ['SLURM_JOB_ID'],limits=p['limits'],affinity=list(os.sched_getaffinity(0)),
        thread_environment={k:os.environ[k] for k in THREADS},status='started')
    new(RUN/(trial+'-start.json'),initial)
    faulthandler.enable();faulthandler.dump_traceback_later(180,repeat=True)
    error=None;result=None
    try:
        check_bindings(p)
        if trial=='postrun':check_primary_link(p)
        if trial=='primary':
            import unittest
            suite=unittest.defaultTestLoader.discover(str(RUN),pattern='test_audit_recovery.py')
            checked=unittest.TextTestRunner(verbosity=2).run(suite)
            require(checked.wasSuccessful() and checked.testsRun==8 and not checked.skipped,'Linux recovery fixtures failed')
            new(RUN/'software.json',dict(status='passed',tests=8,skipped=0,registration_sha256=expected_sha,
                slurm_job_id=os.environ['SLURM_JOB_ID'],scope='Wrapper boundary fixtures, not numerical evidence'))
        print(json.dumps(dict(status='audit_entered',trial=trial,slurm_job_id=os.environ['SLURM_JOB_ID'])),flush=True)
        sys.path.insert(0,str(ROOT))
        if trial=='primary':
            from research_v61.audit import audit
            result=audit(CAMPAIGN,RUN/'primary.json')
        else:
            from research_v61.postrun import audit
            result=audit(CAMPAIGN,RUN/'primary.json',RUN/'postrun.json')
        require(result['status']=='verified' and result['program_sha256']==PROGRAM,'Audit did not verify')
        require(all(result['inputs'].get(name)==entry for name,entry in p['binary_inputs'].items()),
            'Auditor did not rehash every registered binary input')
        check_bindings(p)
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc))
    finally:faulthandler.cancel_dump_traceback_later()
    receipt=dict(initial,schema='second-audit-recovery-result-v62',status='complete' if error is None else 'failed',
        error=error,elapsed_ns=time.monotonic_ns()-start,process_cpu_ns=time.process_time_ns()-cpu,
        original_audit_failure_preserved=True,old_campaign_mutated=False,numerical_execution=False,
        audit_output=None if error else dict(bytes=(RUN/(trial+'.json')).stat().st_size,sha256=digest((RUN/(trial+'.json')).read_bytes())))
    new(RUN/(trial+'-wrapper.json'),receipt)
    print(json.dumps(dict(status=receipt['status'],trial=trial,error=error)),flush=True)
    require(error is None,'Recovery failed: '+str(error))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('registration');p.add_argument('sha256');p.add_argument('trial',choices=('primary','postrun'))
    a=p.parse_args();execute(a.registration,a.sha256,a.trial)
