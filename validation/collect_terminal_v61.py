"""Capture frozen V61 terminal metadata; never run this while its jobs are active.

Usage on the cluster (helper outside the frozen checkout):
  python3 -B /tmp/collect_terminal_v61.py /tmp/second-v61-terminal.tar.gz

The destination must be new and outside the repository. Every known job must
be terminal at two matching scheduler snapshots. --failure-capture additionally
allows only PENDING(DependencyNeverSatisfied) successors of a recorded failed
job, with no active computation. No job, source, ledger or campaign file is
modified. Numerical binaries are statted, never read/copied.
Failures and incomplete receipts are preserved with explicit failure scope.
This is a collector, not a replacement for the scientific or portable audit.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path('/nfs_home/users/poonam/second-20261010')
CAMPAIGN = 'full-precision-service-v61-20261014-a'
LAUNCH = 'continuation-v61-20261014-a'
SOFTWARE_LAUNCH = 'continuation-v61-software-20261014-a'
SOFTWARE = 'v61-software-a.json'
PROGRAM_SHA = '6632712f7b79b49734790fa6fc173ec7e5ee70f542fe8f8a0c3ef3ff2171ea2d'
EXPECTED_COMMIT = 'f900999fcb200509dfad4fc081ce9c87fd172a16'
SOURCE_COUNT = 432
JOBS = dict(checks='13561',register='13562',prepare='13563',cached='13564',cold='13565',
    hybrid='13566',compressed='13567',oracle='13568',audit='13569',postrun='13570')
TRIALS = ('prepare','cached','cold','hybrid','compressed','oracle')
TERMINAL_STATES = {'COMPLETED','CANCELLED','FAILED','TIMEOUT','NODE_FAIL','BOOT_FAIL',
    'OUT_OF_MEMORY','PREEMPTED','DEADLINE','REVOKED','SPECIAL_EXIT'}
COPY_SUFFIXES = {'.json','.log','.txt','.tsv','.py','.sh','.sbatch'}
BINARY_SUFFIXES = {'.bin','.npz','.npy','.safetensors','.gz','.part','.pt','.pth'}
MAX_FILE_BYTES = 32*2**20
MAX_TOTAL_BYTES = 256*2**20
MAX_FILES = 8192
MAX_INPUTS = 8192
MAX_COMMAND_BYTES = 2**20
COMMAND_TIMEOUT = 25
WALL_SECONDS = 180


def require(condition,message):
    if not condition:raise ValueError(message)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def strict(data):
    def object_pairs(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'Duplicate JSON key')
            result[key]=value
        return result
    return json.loads(data,object_pairs_hook=object_pairs,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON number: '+value)))


def info(data):
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def commitment(value):
    require(type(value) is dict and type(value.get('bytes')) is int and value['bytes'] >= 0
        and type(value.get('sha256')) is str and len(value['sha256']) == 64
        and all(c in '0123456789abcdef' for c in value['sha256']), 'Invalid input commitment')
    return {key:value[key] for key in ('bytes','sha256')}


def safe_relative(value):
    require(type(value) is str and value,'Missing relative path')
    path=PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and str(path)==value,'Unsafe relative path: '+value)
    return path


def signature(path):
    require(path.is_absolute() and not any(p.is_symlink() for p in (path,*path.parents)), 'Symbolic input refused: '+str(path))
    s=path.stat()
    require(stat.S_ISREG(s.st_mode),'Regular input required: '+str(path))
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def parse_accounting(text,jobs=JOBS,*,allow_blocked=False):
    result={}
    for line in text.splitlines():
        if not line.strip():continue
        row=line.split('|')
        if row[-1]=='':row.pop()
        require(len(row)==8 and row[0] in jobs.values() and row[0] not in result,'Ambiguous/missing scheduler columns')
        state=row[2].split()[0].rstrip('+')
        require(state in TERMINAL_STATES or (allow_blocked and state=='PENDING'),
            'Nonterminal or unknown Slurm state: '+row[0]+' '+row[2])
        result[row[0]]=dict(job_name=row[1],state=state,raw_state=row[2],exit_code=row[3],
            elapsed_seconds=row[4],total_cpu=row[5],start=row[6],end=row[7])
    require(set(result)==set(jobs.values()),'Incomplete scheduler accounting')
    return result


def blocked_jobs(queue,rows,*,failure_capture=False,jobs=JOBS):
    pending={}
    for line in queue.splitlines():
        if not line.strip():continue
        columns=line.split('|')
        require(len(columns)==3 and columns[0] in jobs.values() and columns[0] not in pending,
            'Ambiguous scheduler queue')
        job,state,reason=columns
        require(failure_capture and state=='PENDING' and reason=='DependencyNeverSatisfied',
            'V61 jobs still queued/running; capture refused')
        pending[job]=dict(state=state,reason=reason)
    require(set(pending)=={job for job,row in rows.items() if row['state']=='PENDING'},
        'Queue and accounting nonterminal census disagree')
    order=list(jobs.values())
    for job in pending:
        ancestors=[previous for previous in order[:order.index(job)]
            if rows[previous]['state'] in TERMINAL_STATES
            and (rows[previous]['state']!='COMPLETED' or rows[previous]['exit_code']!='0:0')]
        require(bool(ancestors),'Blocked dependency has no recorded failed ancestor: '+job)
        pending[job]['failed_ancestors']=ancestors
    return pending


class Collector:
    def __init__(self,root=ROOT,command=None,*,failure_capture=False):
        self.root=Path(root).resolve();self.base=self.root/'local_runs'
        self.contents={};self.remote_paths={};self.signatures={};self.excluded={}
        self.expected={};self.references={};self.issues=[];self.audit_inventories={}
        self.historical_ledgers={}
        self._command=command
        self.failure_capture=failure_capture

    def command(self,args):
        if self._command is not None:return self._command(args)
        with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as error:
            p=subprocess.run(args,cwd=self.root,stdout=output,stderr=error,timeout=COMMAND_TIMEOUT,
                env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'},check=False)
            require(output.tell()<=MAX_COMMAND_BYTES and error.tell()<=MAX_COMMAND_BYTES,'Command output exceeds bound')
            output.seek(0);error.seek(0)
            data=output.read().decode();message=error.read().decode(errors='replace')
            require(p.returncode==0,'Read-only command failed: '+args[0]+' '+message[:4096])
            return data

    def repository_identity(self):
        require(self.command(['git','rev-parse','HEAD']).strip()==EXPECTED_COMMIT,'Numerical HEAD changed')
        require(not self.command(['git','status','--porcelain']).strip(),'Frozen checkout is not clean')

    def scheduler(self):
        ids=','.join(JOBS.values())
        queue=self.command(['squeue','-h','-j',ids,'-o','%i|%T|%R'])
        require(self.failure_capture or not queue.strip(),'V61 jobs still queued/running; capture refused')
        args=['sacct','-X','-n','-P','-j',ids,'--format=JobIDRaw,JobName%64,State%40,ExitCode,ElapsedRaw,TotalCPU,Start,End']
        accounting=self.command(args);rows=parse_accounting(accounting,allow_blocked=self.failure_capture)
        pending=blocked_jobs(queue,rows,failure_capture=self.failure_capture)
        steps=self.command(['sacct','-n','-P','-j',ids,'--format=JobIDRaw,JobName%64,State%40,ExitCode,ElapsedRaw,TotalCPU,MaxRSS,Start,End'])
        return dict(scheduler=accounting,scheduler_steps=steps,jobs=rows,queue=queue,blocked=pending)

    def path(self,remote):
        path=Path(remote)
        require(path.is_absolute() and self.root in path.parents,'Input outside frozen repository: '+remote)
        relative=str(path.relative_to(self.root));safe_relative(relative)
        return path

    def archive_path(self,path):
        relative=str(path.relative_to(self.base)) if self.base in path.parents else None
        if relative==SOFTWARE or (relative is not None and relative.split('/')[0] in (CAMPAIGN,LAUNCH,SOFTWARE_LAUNCH)):
            return relative
        return 'repository/'+str(path.relative_to(self.root))

    def add_expected(self,remote,value,reference):
        self.path(remote)
        value=commitment(value)
        require(len(self.expected)<MAX_INPUTS or remote in self.expected,'Input census exceeds bound')
        if remote in self.expected and self.expected[remote]!=value:
            self.issues.append(dict(kind='conflicting_input_commitments',path=remote,reference=reference,
                previous=self.expected[remote],current=value))
        else:self.expected[remote]=value
        self.references.setdefault(remote,[]).append(reference)

    def capture(self,path,*,source=False):
        path=Path(path).absolute();remote=str(path);self.path(remote)
        if remote in self.remote_paths:return self.contents[self.remote_paths[remote]]
        if not path.exists():
            self.excluded[remote]=dict(kind='missing',status='NOT revalidated',exists=False)
            self.issues.append(dict(kind='missing_bound_input',path=remote));return None
        before=signature(path)
        if path.suffix not in COPY_SUFFIXES:
            self.excluded[remote]=dict(kind='numerical_binary' if path.suffix in BINARY_SUFFIXES else 'unselected_file',
                status='NOT revalidated',exists=True,observed_bytes=before[2],binary_contents_read=False)
            self.signatures[remote]=before
            return None
        require(before[2]<=MAX_FILE_BYTES,'Metadata file exceeds bound: '+remote)
        require(len(self.contents)<MAX_FILES,'Copied file census exceeds bound')
        require(sum(map(len,self.contents.values()))+before[2]<=MAX_TOTAL_BYTES,'Metadata total exceeds bound')
        with path.open('rb') as stream:data=stream.read(MAX_FILE_BYTES+1)
        require(len(data)==before[2] and signature(path)==before,'Input changed during capture: '+remote)
        name=self.archive_path(path);safe_relative(name)
        require(name not in self.contents,'Archive path collision')
        self.contents[name]=data;self.remote_paths[remote]=name;self.signatures[remote]=before
        if source:require(info(data)['sha256']==self.program['sources'][str(path.relative_to(self.root))],'Frozen source changed: '+remote)
        return data

    def json(self,path,*,required=True):
        data=self.capture(path)
        if data is None:
            require(not required,'Required metadata missing: '+str(path));return None
        try:
            value=strict(data)
            require(type(value) is dict,'JSON object required')
        except (ValueError,UnicodeError,TypeError) as error:
            if required:raise
            self.issues.append(dict(kind='invalid_terminal_json',path=str(path),error=str(error)));return None
        return value

    def trees(self):
        census={};directories={}
        def failed(error):raise error
        for name in (CAMPAIGN,LAUNCH,SOFTWARE_LAUNCH):
            start=self.base/name
            require(start.is_dir() and not start.is_symlink(),'Required campaign/launch directory missing')
            for directory,dirs,files in os.walk(start,followlinks=False,onerror=failed):
                metadata=Path(directory).stat()
                directories[str(directory)]=(metadata.st_dev,metadata.st_ino,metadata.st_mtime_ns,metadata.st_ctime_ns)
                require(len(census)+len(directories)+len(dirs)+len(files)<=MAX_FILES,'Campaign directory census exceeds bound')
                for child in dirs:
                    require(not (Path(directory)/child).is_symlink(),'Symbolic directory refused')
                for child in files:
                    path=Path(directory)/child;census[str(path)]=signature(path)
        return dict(files=census,directories=directories)

    def artifact_map(self,value,label):
        mapping=value.get('artifacts',{})
        if type(mapping) is not dict:
            self.issues.append(dict(kind='invalid_artifact_inventory',receipt=label));return {}
        return mapping

    def inspect_receipts(self):
        successes=[]
        for trial in TRIALS:
            root=self.base/CAMPAIGN/trial
            complete=self.json(root/'outputs/completion.json',required=False)
            tx=self.json(root/'transaction.json',required=False)
            sealed=self.json(root/'worker/result.json',required=False)
            outcome=sealed.get('outcome') if sealed is not None else None
            succeeded=(complete is not None and complete.get('status')=='complete' and complete.get('complete_model') is True
                and complete.get('program_sha256')==PROGRAM_SHA and tx is not None and sealed is not None
                and sealed.get('status')=='complete' and type(outcome) is dict and outcome.get('status')=='complete'
                and outcome.get('returncode')==0 and tx.get('worker_outcome')==outcome)
            successes.append(succeeded)
            if not succeeded:self.issues.append(dict(kind='worker_failed_or_incomplete',trial=trial))
            if complete is not None:
                for name,entry in self.artifact_map(complete,'completion:'+trial).items():
                    safe_relative(name);require('/' not in name,'Nested declared worker output refused')
                    self.add_expected(str(root/'outputs'/name),entry,'completion:'+trial)
            if sealed is not None:
                attempt=sealed.get('attempt')
                if type(attempt) is str and attempt.startswith('attempt-') and attempt[8:].isdigit():
                    for name,entry in self.artifact_map(sealed,'worker_seal:'+trial).items():
                        safe_relative(name);require('/' not in name,'Nested sealed artifact refused')
                        self.add_expected(str(root/'worker'/attempt/name),entry,'worker_seal:'+trial)
                else:self.issues.append(dict(kind='invalid_worker_attempt',trial=trial))
        return all(successes)

    def inspect_audits(self):
        valid=[]
        for label,name,schema in (
            ('primary','artifact-audit.json','complete-full-precision-service-artifact-audit-v61'),
            ('postrun','postrun-audit.json','complete-full-precision-service-additive-artifact-audit-v61')):
            path=self.base/CAMPAIGN/name;a=self.json(path,required=False)
            ok=(a is not None and a.get('status')=='verified' and a.get('schema')==schema
                and a.get('program_sha256')==PROGRAM_SHA and a.get('campaign')==str(self.base/CAMPAIGN)
                and type(a.get('inputs')) is dict and bool(a['inputs']))
            valid.append(ok)
            if not ok:self.issues.append(dict(kind='audit_failed_or_incomplete',audit=label))
            if a is not None and type(a.get('inputs')) is dict:
                require(len(a['inputs'])<=MAX_INPUTS,'Audit input census exceeds bound')
                self.audit_inventories[label]=dict(audit_file=self.archive_path(path),inputs=a['inputs'])
                for remote,entry in a['inputs'].items():self.add_expected(remote,entry,'audit:'+label)
        return all(valid)

    def rehash(self):
        for remote,before in self.signatures.items():
            path=Path(remote)
            require(signature(path)==before,'Input changed before final capture: '+remote)
            if remote in self.remote_paths:
                hashed=hashlib.sha256();count=0
                with path.open('rb') as stream:
                    while chunk:=stream.read(2**20):
                        count+=len(chunk);require(count<=MAX_FILE_BYTES,'Input grew beyond bound');hashed.update(chunk)
                require(signature(path)==before and dict(bytes=count,sha256=hashed.hexdigest())==info(self.contents[self.remote_paths[remote]]),
                    'Input bytes changed before final capture: '+remote)

    def collect(self):
        start=time.monotonic();self.repository_identity();before_scheduler=self.scheduler()
        program_path=self.base/CAMPAIGN/'program.json'
        self.program=self.json(program_path)
        require(info(self.contents[self.archive_path(program_path)])['sha256']==PROGRAM_SHA,'Registered program SHA changed')
        require(canonical(self.program)==self.contents[self.archive_path(program_path)]
            and self.program['registered_source_commit']==EXPECTED_COMMIT and len(self.program['sources'])==SOURCE_COUNT
            and self.program['directory']==str(self.base/CAMPAIGN),'Program source identity differs')
        require(self.json(self.base/CAMPAIGN/'registration.json')==dict(program_sha256=PROGRAM_SHA),'Registration differs')
        launch=self.capture(self.base/LAUNCH/'source-commit.txt').decode().strip()
        require(launch==EXPECTED_COMMIT,'Launch source commit differs')
        jobs=[line.split('\t') for line in self.capture(self.base/LAUNCH/'jobs.tsv').decode().splitlines()]
        require(jobs==[[key,value] for key,value in JOBS.items() if key!='checks'],'Launch job census differs')
        software=self.json(self.base/SOFTWARE)
        require(software.get('status')=='passed' and software.get('tests')==205 and software.get('skipped')==0
            and software.get('sources')==self.program['sources'] and software.get('runtime')==self.program['runtime']
            and software.get('source_and_runtime_unchanged') is True and software.get('real_model_inference') is False
            and software.get('slurm_job_id')==JOBS['checks'],'Pinned software receipt differs')
        before_tree=self.trees()
        for remote in sorted(before_tree['files']):self.capture(Path(remote))
        self.capture(self.base/SOFTWARE_LAUNCH/f'checks-{JOBS["checks"]}.log')
        for name,expected in self.program['sources'].items():
            safe_relative(name);path=self.root/name;data=self.capture(path,source=True)
            require(data is not None and info(data)['sha256']==expected,'Frozen source changed: '+name)
        for key,entry in self.program['inputs'].items():self.add_expected(entry['path'],entry,'program:'+key)
        for name,expected in self.program['historical_ledgers'].items():
            safe_relative(name);path=self.root/name;data=self.capture(path)
            ok=data is not None and info(data)['sha256']==expected
            self.historical_ledgers[str(path)]=dict(expected_sha256=expected,verified=ok,
                observed_bytes=len(data) if data is not None else None,archive_file=self.remote_paths.get(str(path)))
            if not ok:self.issues.append(dict(kind='historical_ledger_missing_or_changed',path=str(path),expected_sha256=expected))
        workers_complete=self.inspect_receipts();audits_verified=self.inspect_audits()
        for remote,expected in self.expected.items():
            data=self.capture(self.path(remote))
            if data is not None and info(data)!=expected:
                self.issues.append(dict(kind='bound_metadata_mismatch',path=remote,expected=expected,observed=info(data)))
            if remote in self.excluded:
                self.excluded[remote]['expected']=expected
                if self.excluded[remote].get('exists') and self.excluded[remote]['observed_bytes']!=expected['bytes']:
                    self.issues.append(dict(kind='uncopied_input_size_mismatch',path=remote,expected_bytes=expected['bytes'],observed_bytes=self.excluded[remote]['observed_bytes']))
        require(self.trees()==before_tree,'Campaign/launch file census changed during capture')
        self.rehash();self.repository_identity();after_scheduler=self.scheduler()
        require(before_scheduler==after_scheduler,'Scheduler/accounting changed during capture; retry later')
        scheduler_success=all(row['state']=='COMPLETED' and row['exit_code']=='0:0' for row in after_scheduler['jobs'].values())
        reported_success=scheduler_success and workers_complete and audits_verified and not self.issues
        scope='terminal_success_receipts_metadata_only' if reported_success else 'terminal_failure_or_incomplete_receipts_metadata_only'
        if after_scheduler['blocked']:scope='quiescent_dependency_failure_metadata_only'
        manifest=dict(schema='second-terminal-v61-metadata-v1',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            cluster_commit=EXPECTED_COMMIT,program_sha256=PROGRAM_SHA,source_files_verified=SOURCE_COUNT,
            terminal=not bool(after_scheduler['blocked']),quiescent=True,
            capture_scope=scope,reported_success=reported_success,portable_scientific_validation_performed=False,
            files={name:info(data) for name,data in self.contents.items()},repository_paths=self.remote_paths,
            audit_input_inventories=self.audit_inventories,expected_input_commitments=self.expected,input_references=self.references,
            historical_ledger_bindings=self.historical_ledgers,
            inputs_not_copied=self.excluded,capture_issues=self.issues,
            scheduler=after_scheduler['scheduler'],scheduler_steps=after_scheduler['scheduler_steps'],scheduler_jobs=after_scheduler['jobs'],
            scheduler_queue=after_scheduler['queue'],blocked_dependency_jobs=after_scheduler['blocked'],
            limits=dict(max_file_bytes=MAX_FILE_BYTES,max_total_bytes=MAX_TOTAL_BYTES,max_files=MAX_FILES,
                max_inputs=MAX_INPUTS,command_timeout_seconds=COMMAND_TIMEOUT,wall_seconds=WALL_SECONDS),
            captured_metadata_bytes=sum(map(len,self.contents.values())),capture_elapsed_seconds=time.monotonic()-start,
            final_metadata_bytes_rehashed=True,source_and_campaign_census_unchanged=True,
            excluded_binary_contents_rehashed=False,numerical_inference_or_calibration_executed=False,
            scope='Terminal metadata and existing receipts only. Declared binary SHA values are commitments from receipts; no new local/collector binary proof. Failed, cancelled, unsealed, or incomplete work remains explicit. No jobs, sources, ledgers or campaign files modified.')
        encoded=json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n'
        require(len(encoded)<=MAX_FILE_BYTES and sum(map(len,self.contents.values()))+len(encoded)<=MAX_TOTAL_BYTES,'Manifest-inclusive metadata exceeds bound')
        self.contents['collection-manifest.json']=encoded
        return manifest


def write_archive(destination,contents,root=ROOT):
    destination=Path(destination)
    require(destination.is_absolute() and destination.name.endswith('.tar.gz') and Path(root).resolve() not in destination.parents,
        'Use a new .tar.gz destination outside the frozen checkout')
    require(destination.parent.is_dir() and not any(p.is_symlink() for p in destination.parents),'Unsafe/missing destination parent')
    # O_EXCL refuses regular files and symlinks; never overwrite or replace.
    with destination.open('xb') as output:
        with tarfile.open(fileobj=output,mode='w|gz') as archive:
            for name,data in sorted(contents.items()):
                safe_relative(name);member=tarfile.TarInfo(name);member.size=len(data);member.mode=0o600
                archive.addfile(member,io.BytesIO(data))
        output.flush();os.fsync(output.fileno())
    hashed=hashlib.sha256()
    with destination.open('rb') as stream:
        while chunk:=stream.read(2**20):hashed.update(chunk)
    return dict(path=str(destination),bytes=destination.stat().st_size,sha256=hashed.hexdigest())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('new_archive',type=Path)
    parser.add_argument('--failure-capture',action='store_true',help='Also allow stable PENDING(DependencyNeverSatisfied) successors of failed jobs; never cancel jobs.')
    args=parser.parse_args()
    require(not args.new_archive.exists() and not args.new_archive.is_symlink(),'Destination already exists')
    if hasattr(signal,'SIGALRM'):
        signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Collector wall bound exceeded')))
        signal.alarm(WALL_SECONDS)
    collector=Collector(failure_capture=args.failure_capture);manifest=collector.collect();archive=write_archive(args.new_archive,collector.contents)
    if hasattr(signal,'SIGALRM'):signal.alarm(0)
    print(json.dumps(dict(archive,capture_scope=manifest['capture_scope'],copied_files=len(manifest['files']),
        uncopied_inputs=len(manifest['inputs_not_copied']),capture_issues=len(manifest['capture_issues'])),sort_keys=True))


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,TypeError,OSError,TimeoutError,subprocess.SubprocessError) as error:
        print(json.dumps(dict(status='capture_refused',error_type=type(error).__name__,error=str(error))),file=sys.stderr)
        raise SystemExit(1)
