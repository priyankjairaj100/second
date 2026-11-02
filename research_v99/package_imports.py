"""Reject missing reachable project imports before writing the source archive."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def require_closed(files):
    pending = [n for n in files if n.startswith(('research_v90/', 'research_v99/')) and n.endswith('.py')]
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        for node in ast.walk(ast.parse(files[name])):
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                module = node.module
                if module.replace('.', '/') + '.py' in files:
                    modules = [module]
                else:
                    modules = [module + '.' + a.name for a in node.names]
            else:
                continue
            for module in modules:
                if not (module.startswith('research_v') or module.startswith('src.')):
                    continue
                path = module.replace('.', '/') + '.py'
                if path not in files:
                    raise ValueError('Missing reachable project import: ' + module + ' from ' + name)
                pending.append(path)
    return sorted(seen)


def check_host_imports(files):
    """Import real staged host entrypoints with no research checkout on sys.path."""
    modules = ['config', 'records', 'storage_plan', 'protocol', 'mapping', 'host',
               'entry', 'submit', 'prepare', 'closure', 'terminal', 'package',
               'prior_setup', 'software']
    with tempfile.TemporaryDirectory(prefix='second99-package-imports-') as temporary:
        root = Path(temporary).resolve()
        for name, blob in files.items():
            path = Path(name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe candidate member')
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        command = '''import importlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
names=json.loads(sys.argv[2])
for name in names:importlib.import_module('research_v99.'+name)
for name,module in list(sys.modules.items()):
 if name.startswith(('research_v','src.')) and getattr(module,'__file__',None):
  assert pathlib.Path(module.__file__).resolve().is_relative_to(root),name
print(json.dumps(dict(imported=names,isolated=True)))
'''
        environment = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
        result = subprocess.run([sys.executable, '-I', '-B', '-c', command, str(root), json.dumps(modules)],
                                cwd=root, env=environment, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ValueError('Extracted-only host import failed: ' + result.stderr[-6000:])
        return json.loads(result.stdout)
