"""Read-only static dependency review of the prepared source inventory.

No project imports are executed. Static imports do not qualify runtime, dynamic
file access, native compilation, or an anonymous/reproducible distribution.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,datetime,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]


def check(supplement=None):
 inventory=json.loads((ROOT/'validation/v69_submission_inventory.json').read_text())
 sources=dict(inventory['source_files']);assert len(sources)==532
 supplement_count=0
 if supplement:
  extra=json.loads(Path(supplement).read_text())['sources'];assert not set(extra)&set(sources)
  sources.update(extra);supplement_count=len(extra)
 manifest={l[66:]:l[:64] for l in (ROOT/'MANIFEST.sha256').read_text().splitlines()}
 for name,e in sources.items():
  p=ROOT/name;assert not p.is_symlink();raw=p.read_bytes()
  assert {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==e,name
  assert e['sha256']==manifest[name],name
 mods={};namespace=set()
 for name in sources:
  p=Path(name)
  if p.suffix!='.py':continue
  parts=list(p.with_suffix('').parts)
  if parts[-1]=='__init__':parts.pop()
  module='.'.join(parts);assert module not in mods;mods[module]=name
  namespace.update('.'.join(parts[:i]) for i in range(1,len(parts)))
 roots={m.split('.')[0] for m in mods}
 graph={name:set() for name in mods.values()};missing=[];external={};dynamics=[];file_boundaries=[];parse=[];aliases=[]
 explicit_aliases={'exact_core':'src.exact_core','repair_service':'src.repair_service','launch_fixed_timing_v23':'scripts.launch_fixed_timing_v23'}
 def resolve(module):
  if module in mods:return mods[module]
  return None
 def inspect(name,line,module,kind,required=True):
  if not module:return
  top=module.split('.')[0]
  if top in explicit_aliases:
   expanded=explicit_aliases[top]+module[len(top):]
   aliases.append(dict(source=name,line=line,original=module,resolved=expanded,scope='Reviewed direct-import/same-directory alternative; actual execution mode remains required.'))
   module=expanded;top=module.split('.')[0]
  if top in roots or (ROOT/top).is_dir() or (ROOT/(top+'.py')).is_file():
   target=resolve(module)
   if target:
    graph[name].add(target)
    pieces=module.split('.')
    for i in range(1,len(pieces)):
     parent=mods.get('.'.join(pieces[:i]))
     if parent and Path(parent).name=='__init__.py':graph[name].add(parent)
   elif module not in namespace and required:missing.append(dict(source=name,line=line,module=module,kind=kind,exists_outside_inventory=(ROOT/(module.replace('.','/')+'.py')).is_file()))
  else:external.setdefault(top,[]).append(dict(source=name,line=line,module=module,kind=kind))
 for module,name in sorted(mods.items()):
  source=(ROOT/name).read_text();node=ast.parse(source,filename=name,feature_version=(3,10));parse.append(name)
  package=module if Path(name).name=='__init__.py' else module.rpartition('.')[0]
  for n in ast.walk(node):
   if isinstance(n,ast.Import):
    for alias in n.names:inspect(name,n.lineno,alias.name,'import')
   elif isinstance(n,ast.ImportFrom):
    if n.level:
     parts=package.split('.') if package else []
     if n.level>len(parts):raise ValueError('Relative import escapes package: '+name)
     root='.'.join(parts[:len(parts)-n.level+1]);base='.'.join(p for p in [root,n.module or ''] if p)
    else:base=n.module or ''
    inspect(name,n.lineno,base,'from')
    for alias in n.names:
     if alias.name!='*':inspect(name,n.lineno,base+'.'+alias.name,'from_attribute_or_submodule',required=False)
   elif isinstance(n,ast.Call):
    call=ast.unparse(n.func)
    if call in {'__import__','importlib.import_module','import_module'}:
     literal=n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str)
     value=n.args[0].value if literal else None
     dynamics.append(dict(source=name,line=n.lineno,call=call,literal_module=value,requires_runtime_review=not bool(literal)))
     if literal:inspect(name,n.lineno,value,'literal_dynamic_import')
    if call.startswith(('subprocess.','ctypes.')) or call in {'open','exec','eval','compile'}:
     file_boundaries.append(dict(source=name,line=n.lineno,call=call))
 stdlib=set(sys.stdlib_module_names)|{'__future__'}
 third={k:v for k,v in sorted(external.items()) if k not in stdlib}
 def reachable(names):
  seen=set();todo=[p for p in names if p in graph]
  while todo:
   p=todo.pop()
   if p in seen:continue
   seen.add(p);todo.extend(graph[p]-seen)
  return sorted(seen)
 entries=['research_v67/entry.py','research_v67/worker.py','research_v69/entry.py','research_v69/worker.py','research_v69/closure.py','research_v69/submission.py','research_v68/data_runner.py']
 reach={p:reachable([p]) for p in entries}
 return dict(schema='prepared-source-static-closure-v69',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='static_import_inventory_checked' if not missing else 'static_missing_sources_require_review',inventory_sha256=hashlib.sha256((ROOT/'validation/v69_submission_inventory.json').read_bytes()).hexdigest(),source_count=len(sources),prepared_execution_sources=532,packaging_supplement_sources=supplement_count,reviewed_bare_import_aliases=aliases,python_modules_parsed=len(parse),python_grammar='3.10',source_suffix_counts=dict(Counter(Path(p).suffix for p in sources)),local_import_edges=sum(len(v) for v in graph.values()),local_import_graph={k:sorted(v) for k,v in sorted(graph.items())},missing_static_project_modules=missing,third_party_imports=third,stdlib_classification_host_python=sys.version.split()[0],static_entry_reachability=reach,dynamic_import_calls=dynamics,process_native_or_dynamic_code_calls=file_boundaries,all_original_source_bytes_unchanged=True,project_imports_executed=False,runtime_dependency_closure_verified=False,source_reproduction_verified=False,anonymity_verified=False,scope='Prepared source union plus an optional explicit packaging supplement. Static edges include package initializers and conditional/test imports. Reachability is not a sufficient package allowlist: registration inventories, native code, data, dynamic loading and external runtimes still require review.')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--supplement',type=Path);a=p.parse_args();r=check(a.supplement)
 with a.output.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({k:r[k] for k in ['status','source_count','python_modules_parsed','local_import_edges','missing_static_project_modules']}))
 print(json.dumps({'third_party_roots':list(r['third_party_imports']),'dynamic_calls':len(r['dynamic_import_calls']),'nonliteral_dynamic_calls':sum(x['requires_runtime_review'] for x in r['dynamic_import_calls']),'entry_reachable_counts':{k:len(v) for k,v in r['static_entry_reachability'].items()}}))
