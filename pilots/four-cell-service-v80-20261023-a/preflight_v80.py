from pathlib import Path
import subprocess,shlex,json,hashlib
W=Path(__file__).resolve().parent
R=Path('/Users/priyankjairaj/Downloads/ACL/Second')
s=json.loads((W/'v79-snapshot.json').read_text());d=R/'pilots/service-integration-v79-20261023-a';d.mkdir(exist_ok=True)
for name,text in s['files'].items():
 p=d/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_text()==text
 else:p.write_text(text)
(d/'terminal-snapshot.json').write_text(json.dumps(s,indent=2)+'\n')
(d/'program_v79.json').write_bytes((R/'research_v79/program.json').read_bytes())
remote='''import pathlib,json,hashlib,subprocess,datetime
r=pathlib.Path('/nfs_home/users/poonam/second-20261010');o=r/'local_runs/disjoint-service-v67-20261016-a'
def info(path):
 p=pathlib.Path(path);h=hashlib.sha256();n=0
 assert not any(q.is_symlink() for q in (p,*p.parents)) and p.is_file()
 with p.open('rb') as f:
  while b:=f.read(2**20):h.update(b);n+=len(b)
 return dict(bytes=n,sha256=h.hexdigest())
p=json.loads((o/'program.json').read_text())
q=subprocess.check_output(['squeue','-u','poonam','-h','-o','%i|%j|%T'],text=True)
assert not q.strip() and not (r/'local_runs/four-cell-service-v80-20261023-a').exists()
assert subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip()==p['numerical_checkout']
assert not subprocess.check_output(['git','-C',str(r),'status','--short'],text=True).strip()
for group in ('prior_sources','dependency_files','historical_ledgers'):
 for path,e in p[group].items():assert info(path)==e,path
for key,e in p['inputs'].items():assert info(e['path'])=={k:e[k] for k in ('bytes','sha256')},key
cpath=r/'local_runs/service-integration-v79-20261023-a/completion.json';c=json.loads(cpath.read_text())
assert c['status']=='complete' and c['job_id']=='15903'
acc=subprocess.check_output(['sacct','-j','15903','-n','-P','--format=JobIDRaw,State,ExitCode'],text=True)
assert '15903|COMPLETED|0:0' in acc
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),queue=q,inputs=p['inputs'],prior_sources=p['prior_sources'],dependency_files=p['dependency_files'],historical_ledgers=p['historical_ledgers'],runtime=p['runtime'],shared_checkpoint_bytes=p['shared_checkpoint_bytes'],v79_completion=dict(path=str(cpath),**info(cpath)),v79_accounting=acc,base_target=pathlib.Path(p['inputs']['base_target']['path']).read_text())))
'''
x=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-o','PubkeyAuthentication=no','csis','python3 -c '+shlex.quote(remote)],capture_output=True,text=True,timeout=60)
if x.returncode:print(x.stderr);raise SystemExit(x.returncode)
a=json.loads(x.stdout);a['transport_stderr']=x.stderr
(W/'v80-preflight.json').write_text(json.dumps(a,indent=2)+'\n')
print({k:a[k] for k in ['captured_utc','queue','v79_completion','v79_accounting']})
