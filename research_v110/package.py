"""Preserve the exact V104 source archive and add only the diagnostic namespace."""
import ast,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
from research_v80.io import require,read,info
from research_v101.package import tar_extent
from research_v110.software import SUITES
from research_v110.storage_plan import build,requests
from src.run_store import strict_json,canonical_json
ARCHIVE_SHA='e305f782fced1853c00d42d5504c1bcbad5ce8ac520a51f8d7e18b56315324c0'
HOST_MODULES=('config','records','storage_plan','contracts','protocol','mapping','host',
              'entry','closure','dispatch_failure','campaign','software','prepare','submit','package')


def extracted_check(files):
    with tempfile.TemporaryDirectory(prefix='second110-extracted-') as temporary:
        root=Path(temporary).resolve()
        for n,b in files.items():
            target=root/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
        command='''import contextlib,importlib,pathlib,sys,unittest,json
root=pathlib.Path(sys.argv[1]);sys.path.insert(0,str(root))
for name in json.loads(sys.argv[2]):importlib.import_module('research_v110.'+name)
with contextlib.redirect_stdout(sys.stderr):
 r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(['research_v110.test_diagnostic','research_v110.test_dispatch','research_v110.test_prepare_boundary']))
assert r.wasSuccessful() and r.testsRun==19 and not r.skipped
for name,module in list(sys.modules.items()):
 if name.startswith(('research_v','src.')) and getattr(module,'__file__',None):
  assert pathlib.Path(module.__file__).resolve().is_relative_to(root),name
print(json.dumps(dict(tests=19,isolated=True,source_only=True)))
'''
        env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')}
        r=subprocess.run([sys.executable,'-I','-B','-c',command,str(root),json.dumps(HOST_MODULES)],
            cwd=root,env=env,capture_output=True,text=True,timeout=60)
        require(r.returncode==0,'Extracted source check failed: '+r.stderr[-12000:])
        return json.loads(r.stdout)


def main(parent_archive,gate_path,destination):
    repo=Path(__file__).resolve().parents[1]
    require(read(parent_archive,maximum=64*2**20,retain=False)['sha256']==ARCHIVE_SHA,'Exact original archive required')
    files={}
    with tarfile.open(parent_archive,'r:') as tar:
        members=tar.getmembers();require(len(members)==1217 and all(m.isfile() for m in members)
            and len({m.name for m in members})==1217,'Exact original member census required')
        inv=strict_json(tar.extractfile('inventory.json').read())
        for n,e in inv.items():
            require(not Path(n).is_absolute() and '..' not in Path(n).parts,'Safe member required')
            b=tar.extractfile(n).read();require(info(b)==e,'Original bytes changed')
            if (repo/n).exists():read(repo/n,e,maximum=64*2**20,retain=False)
            files[n]=b
    for path in sorted((repo/'research_v110').iterdir()):
        if path.is_file() and path.suffix in ('.py','.sh','.sbatch','.txt','.json'):
            files[str(path.relative_to(repo))]=read(path,maximum=4*2**20)
    gate=strict_json(read(gate_path,maximum=4*2**20))
    files['gates/v104-failed-screen-v110.json']=canonical_json(gate)
    for n,b in files.items():
        if n.endswith('.py'):ast.parse(b)
    for label,(modules,count) in SUITES.items():
        actual=sum(sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for n in
            ast.walk(ast.parse(files[m.replace('.','/')+'.py']))) for m in modules)
        require(actual==count,'Test census differs: '+label)
    isolated=extracted_check(files)
    inventory={n:info(b) for n,b in sorted(files.items())};manifest=canonical_json(inventory)
    members={**files,'inventory.json':manifest};expected=tar_extent(members)
    dest=Path(destination).absolute();dest.mkdir(parents=True,exist_ok=False)
    (dest/'inventory.json').write_bytes(manifest)
    archive=dest/'token-stage-diagnostic-v110-source-only.tar'
    with archive.open('xb') as stream,tarfile.open(fileobj=stream,mode='w|') as tar:
        for n,b in sorted(members.items()):
            m=tarfile.TarInfo(n);m.size=len(b);m.mode=0o600;tar.addfile(m,io.BytesIO(b))
    extent=read(archive,maximum=64*2**20,retain=False);require(extent['bytes']==expected,'Archive extent differs')
    plan=build(inventory,extent['bytes'])
    report=dict(schema='diagnostic-package-v110',status='prepared_not_registered',archive=extent,
        inventory=info(manifest),source_count=len(inventory),parent_source_count=1216,
        isolated_check=isolated,expected_linux_tests=sum(v[1] for v in SUITES.values()),
        storage_plan=plan,before_upload_requests=requests(plan,inventory,extent['bytes']),
        registered=False,uploaded=False,numerical_execution=False)
    (dest/'preparation.json').write_bytes(canonical_json(report));print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main(*sys.argv[1:])
