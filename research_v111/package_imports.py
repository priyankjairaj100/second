"""Close imported AND hash-bound sources; execute checks from isolated bytes."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
PREFIXES=('research_v90/','research_v101/','research_v111/')
PURE_MODULES=[f'research_v101.test_{n}' for n in ('contracts','storage','accounting','fetch','protocol','submit','host','package','closure')]+[f'research_v90.test_{n}' for n in ('metadata','outputs','admission','storage_plan','recovery_gate')]+['research_v82.test_inputs','research_v82.test_admission_reports']
PURE_MODULES += [f'research_v111.test_{n}' for n in ('contracts','design','host','closure','submit','gate','accounting','chain','timing','boundary','dispatch')]
PURE_MODULES += ['research_v111.test_prepare','research_v111.test_policy.Policy']
HOST_MODULES=['config','records','storage_plan','protocol','mapping','host','entry','submit','prepare','closure','terminal','package','gate','software']


def close_dependencies(files,repo):
    """Only add existing source bytes; conflicting frozen commitments refuse."""
    repo=Path(repo).resolve()
    def add(name,binding=None):
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or p.suffix not in ('.py','.json','.txt','.sh','.sbatch','.c'):
            raise ValueError('Unsafe source dependency: '+name)
        data=files[name] if name in files else (repo/name).read_bytes()
        if len(data)>64*2**20:raise ValueError('Dependency too large')
        if binding is not None and dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())!=binding:
            raise ValueError('Hash-bound dependency differs: '+name)
        if name not in files:files[name]=data
    # All packaged runtime/source manifests, including transitively added ones.
    manifests=set();bound_sources=set()
    while True:
        todo=[n for n in files if n.endswith('_BINDINGS.json') and n not in manifests]
        if not todo:break
        for name in todo:
            bindings=json.loads(files[name]);manifests.add(name)
            for source,binding in bindings.items():
                add(source,binding);bound_sources.add(source)
    pending=[n for n in files if n.endswith('.py') and (n.startswith(PREFIXES) or n in bound_sources)]
    seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name)
        for node in ast.walk(ast.parse(files[name])):
            if isinstance(node,ast.Import):modules=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module and not node.level:
                module=node.module;path=module.replace('.','/')+'.py'
                modules=[module] if path in files or (repo/path).is_file() else [module+'.'+a.name for a in node.names]
            else:continue
            for module in modules:
                if not (module.startswith('research_v') or module.startswith('src.')):continue
                path=module.replace('.','/')+'.py';add(path);pending.append(path)
    return dict(reachable_modules=sorted(seen),hash_manifests=sorted(manifests),hash_bound_sources=sorted(bound_sources))


def check_extracted(files):
    """No checkout imports, no empirical execution; fail before an archive exists."""
    with tempfile.TemporaryDirectory(prefix='second111-extracted-') as temporary:
        root=Path(temporary).resolve()
        for name,blob in files.items():
            path=Path(name)
            if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe candidate member')
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
        command='''import contextlib,importlib,json,pathlib,sys,unittest
root=pathlib.Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
host,pure=json.loads(sys.argv[2])
for name in host:importlib.import_module('research_v111.'+name)
suite=unittest.defaultTestLoader.loadTestsFromNames(pure)
with contextlib.redirect_stdout(sys.stderr):r=unittest.TextTestRunner(verbosity=1).run(suite)
assert r.wasSuccessful() and r.testsRun==160 and not r.skipped
for name,module in list(sys.modules.items()):
 if name.startswith(('research_v','src.')) and getattr(module,'__file__',None):
  assert pathlib.Path(module.__file__).resolve().is_relative_to(root),name
print(json.dumps(dict(imported=host,isolated=True,tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped))))
'''
        env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')}
        result=subprocess.run([sys.executable,'-I','-B','-c',command,str(root),json.dumps([HOST_MODULES,PURE_MODULES])],cwd=root,env=env,capture_output=True,text=True,timeout=60)
        if result.returncode:raise ValueError('Extracted-only checks failed: '+result.stderr[-12000:])
        return json.loads(result.stdout)
