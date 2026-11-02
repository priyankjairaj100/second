from pathlib import Path
import datetime,hashlib,io,json,subprocess,tarfile
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/disjoint-data-v65-20261016-a'
V63=ROOT/'local_runs/lossless-control-v63-20261016-a';V64=ROOT/'local_runs/modern-service-checks-v64-20261016-a'
OUT=Path('/tmp/second-v65-data-terminal-20261016-a.tar.gz');REG='13d9ecb7ddb9ee37ba05498387af490a5e6f16879340c4ec301bbe2aaf5f08d2'
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def cmd(*a):return subprocess.check_output(a,cwd=ROOT,text=True,timeout=30)
def bounded(path):
    assert path.is_file() and not any(q.is_symlink() for q in (path,*path.parents)) and path.stat().st_size<=128*2**20
    a=path.stat();b=path.read_bytes();c=path.stat()
    assert (a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(c.st_ino,c.st_size,c.st_mtime_ns,c.st_ctime_ns)
    return b
def scheduler():
    assert not cmd('squeue','-h','-j','15255,15256,15257','-o','%i|%T').strip()
    result=cmd('sacct','-n','-P','-j','15255,15256,15257','--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,MaxRSS,Start,End')
    rows={f[0]:f for f in [s.split('|') for s in result.splitlines()]}
    assert all(rows[n+s][1:3]==['COMPLETED','0:0'] for n in ['15255','15256','15257'] for s in ['','.batch'])
    return result
assert not OUT.exists();first=scheduler()
assert cmd('git','rev-parse','HEAD').strip()=='f900999fcb200509dfad4fc081ce9c87fd172a16' and not cmd('git','status','--porcelain').strip()
raw=bounded(RUN/'registration.json');assert info(raw)['sha256']==REG;p=json.loads(raw)
for n,h in p['historical_sources'].items():assert info(bounded(ROOT/n))['sha256']==h
for group,base in [('new_sources',RUN),('v63_sources',V63),('v64_sources',V64),('history',ROOT)]:
    for n,e in p[group].items():assert info(bounded(base/n))==e
for group in ['prior_inputs','tokenizer_runtime_files','v64_receipts']:
    for n,e in p[group].items():assert info(bounded(Path(n)))==e
paths=sorted(RUN.glob('*.json'))+sorted(RUN.glob('*.log'))+[RUN/n for n in p['new_sources']]+[RUN/'outputs/selection.json']
files={str(path.relative_to(RUN)):bounded(path) for path in paths}
assert len(files)==len(paths) and sum(map(len,files.values()))<2**20
omitted={str(path.relative_to(RUN)):info(bounded(path)) for path in sorted((RUN/'outputs').iterdir()) if str(path.relative_to(RUN)) not in files}
assert set(omitted)=={'outputs/records.json','outputs/shard-2-prefix.gz.part','outputs/exclusions-before.json','outputs/exclusions-after.json'}
checks,data,audit=[json.loads(files[n+'.json']) for n in ['checks','data','audit']]
for n,receipt,job in [('checks',checks,'15255'),('data',data,'15256'),('audit',audit,'15257')]:
    assert receipt['status']=='complete' and receipt['error'] is None and receipt['trial']==n and receipt['job_id']==job and receipt['registration_sha256']==REG
    assert receipt['caps']==p['caps'][n] and receipt['process_cpu_ns']+receipt['waited_child_cpu_ns']==receipt['combined_observed_cpu_ns']
    assert receipt['combined_observed_cpu_ns']<=(p['caps'][n]['cpu']+2)*10**9 and receipt['elapsed_ns']<=p['caps'][n]['wall']*10**9
    assert receipt['model_inference'] is False and receipt['quality_evaluation'] is False
assert checks['result']==dict(tests=9,skipped=0,failures=0,errors=0,corpus_parsed=False)
selection=json.loads(files['outputs/selection.json'])
assert data['result']['selection']==audit['result']['selection']==info(files['outputs/selection.json'])
assert data['result']['records']==audit['result']['records']==selection['records']==omitted['outputs/records.json']
assert selection['exclusions_before']==omitted['outputs/exclusions-before.json']
assert all(data['result']['source_prefix'][k]==selection['source'][k]==v for k,v in omitted['outputs/shard-2-prefix.gz.part'].items())
assert all(audit['result'][k] is True for k in ['actual_saved_prefix_retokenized','actual_selected_records_equal','actual_exclusion_sets_equal'])
assert audit['result']['independent_implementation'] is False and audit['result']['selected_records']==13 and audit['result']['calibration_tokens']==1664
assert sum(r['combined_observed_cpu_ns'] for r in [checks,data,audit])<=1506*10**9
last=scheduler();assert last==first
assert all(bounded(RUN/n)==b for n,b in files.items()) and all(info(bounded(RUN/n))==e for n,e in omitted.items())
files['collection-manifest.json']=canonical(dict(schema='v65-data-terminal-capture',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),registration_sha256=REG,files={n:info(b) for n,b in files.items()},omitted_files=omitted,scheduler=last,historical_sources_verified=432,v63_sources_verified=7,v64_sources_verified=6,new_sources_verified=5,historical_metadata_files_verified=len(p['history']),actual_data_audit_verified=True,source_text_and_tokens_exported=False,model_inference=False,quality_evaluation=False))
with OUT.open('xb') as f:
    with tarfile.open(fileobj=f,mode='w|gz') as t:
        for n,b in sorted(files.items()):
            member=tarfile.TarInfo(n);member.size=len(b);member.mode=0o600;t.addfile(member,io.BytesIO(b))
print(json.dumps(dict(path=str(OUT),files=len(files),**info(OUT.read_bytes()))))
