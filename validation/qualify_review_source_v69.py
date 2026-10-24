"""Bounded local fixture check for an extracted review source component.

This never admits real inputs, Linux/Slurm execution, CUDA or empirical quality.
Run with an existing CPython3.12 environment containing the required dependencies.
"""
from pathlib import Path
import argparse,datetime,hashlib,importlib.metadata,io,json,os,resource,sys,time,unittest

def within(p,root):
 try:Path(p).resolve().relative_to(root);return True
 except (ValueError,TypeError):return False

def fd_path(name,fd=-1):
 p=Path(name)
 if p.is_absolute() or fd in (-1,None):return p.resolve()
 if sys.platform=='darwin':
  import fcntl
  base=fcntl.fcntl(fd,fcntl.F_GETPATH,b'\0'*1024).split(b'\0',1)[0].decode()
 else:base=os.readlink('/proc/self/fd/'+str(fd))
 return (Path(base)/p).resolve()

def run(root,report,log,temporary):
 root=root.resolve(strict=True);report=report.resolve();log=log.resolve();temporary=temporary.resolve(strict=True)
 assert sys.dont_write_bytecode and sys.flags.isolated
 assert root.is_dir() and temporary.is_dir() and report.parent==log.parent and not report.exists() and not log.exists()
 manifest={l[66:]:l[:64] for l in (root/'MANIFEST.sha256').read_text().splitlines()}
 def unchanged():
  for name,h in manifest.items():
   p=root/name;assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==h,name
 unchanged()
 resource.setrlimit(resource.RLIMIT_CPU,(120,121));resource.setrlimit(resource.RLIMIT_FSIZE,(64*2**20,64*2**20))
 os.environ['TMPDIR']=str(temporary)
 # Libraries are already installed; only fixture-created files may be written.
 allowed={report,log};denied=[];allowed_processes=[]
 def guard(event,args):
  if event.startswith('socket.') and event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','socket.bind','socket.sendto'):
   denied.append(event);raise PermissionError('Network is excluded from source-package fixtures')
  if event=='subprocess.Popen':
   executable,argv,cwd,env=args
   valid=isinstance(argv,(list,tuple)) and len(argv)==3 and argv[:2]==['bash','-n'] and within(argv[2],root)
   if not valid:denied.append(event);raise PermissionError('Only shell syntax checks are allowed')
   allowed_processes.append([str(x) for x in argv]);return
  if event in ('os.system','os.posix_spawn','os.fork','os.forkpty','resource.setrlimit'):
   denied.append(event);raise PermissionError('Process or limit mutation is excluded from fixtures')
  if event=='open':
   name,mode,flags=args
   writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
   if writing and not isinstance(name,int) and Path(name).resolve() not in allowed and not within(name,temporary):
    denied.append('open-write');raise PermissionError('Fixture write outside the temporary directory')
  if event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.chmod','os.symlink','os.link'):
   if event in ('os.rename','os.link'):paths=[fd_path(args[0],args[2]),fd_path(args[1],args[3])]
   elif event=='os.symlink':paths=[fd_path(args[1],args[2])]
   elif event in ('os.remove','os.rmdir'):paths=[fd_path(args[0],args[1])]
   else:paths=[fd_path(args[0],args[2])]
   if any(not within(p,temporary) for p in paths):
    denied.append(event);raise PermissionError('Filesystem mutation outside fixture temporary directory')
 sys.addaudithook(guard)
 sys.path.insert(0,str(root))
 modules=[package+'.'+p.stem for package in ['research_v68','research_v69'] for p in sorted((root/package).glob('test_*.py'))]
 started=time.perf_counter_ns();cpu=time.process_time_ns()
 with log.open('x') as f:
  result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
 project={};namespaces={};external={}
 for name,m in sorted(sys.modules.items()):
  origin=getattr(m,'__file__',None)
  if name.split('.')[0] in {'src','scripts'} or name.startswith('research_v'):
   if origin:
    assert within(origin,root),(name,origin)
    p=Path(origin).resolve();project[name]=str(p.relative_to(root))
   else:
    locations=list(getattr(m,'__path__',[]));assert locations and all(within(p,root) for p in locations),(name,locations)
    namespaces[name]=[str(Path(p).resolve().relative_to(root)) for p in locations]
 for name in ['numpy','gmpy2','torch','tokenizers','pyarrow','scipy','zstandard']:
  if name in sys.modules:
   try:external[name]=importlib.metadata.version(name)
   except importlib.metadata.PackageNotFoundError:external[name]='no installed distribution metadata'
 unchanged()
 d=dict(schema='clean-review-source-fixtures-v69',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='passed' if result.wasSuccessful() and result.testsRun==114 and not result.skipped and not denied else 'failed',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),elapsed_ns=time.perf_counter_ns()-started,process_cpu_ns=time.process_time_ns()-cpu,python=sys.version,executable=sys.executable,platform=sys.platform,project_module_origins=project,project_namespace_locations=namespaces,imported_external_packages=external,source_files_checked=len(manifest),source_files_unchanged=True,denied_audit_events=denied,allowed_subprocesses=allowed_processes,network_allowed=False,python_audit_hooks_not_full_os_sandbox=True,real_submissions_allowed=False,write_scope='separate fixture temporary directory plus report/log',cpu_soft_seconds=120,cpu_hard_seconds=121,per_file_bytes=64*2**20,v68_fixture_tests=22,v69_fixture_tests=92,actual_linux_qualification=False,actual_cuda_executed=False,actual_checkpoint_loaded=False,empirical_likelihood=False,production_constructor_runtime_slurm_mocked=True,tiny_generated_cpu_likelihood_executed=True,clean_source_import_fixture_check_only=True,full_reproduction_verified=False,full_anonymity_verified=False)
 with report.open('x') as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps({k:d[k] for k in ['status','tests','failures','errors','skipped','source_files_checked','imported_external_packages','elapsed_ns']}))
 return 0 if d['status']=='passed' else 1

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--report',type=Path,required=True);p.add_argument('--log',type=Path,required=True);p.add_argument('--temporary',type=Path,required=True);a=p.parse_args();raise SystemExit(run(a.root,a.report,a.log,a.temporary))
