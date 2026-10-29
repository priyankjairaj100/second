"""Likelihood-only libm identity adapter. Never used for native calibration.

The historical backend only recognizes libm.so* basenames. Older glibc maps the
resolved libm-2.17.so file. Hash actual mapped files and retain all runtime checks.
"""
import re,sys,math,platform
from pathlib import Path
from contextlib import contextmanager

def is_libm(path):
 return path.startswith('/') and re.fullmatch(r'libm(?:\.so(?:\.[0-9]+)*|-[0-9]+(?:\.[0-9]+)*\.so)',Path(path).name) is not None

def libraries(text):
 paths=set();py=set()
 for line in text.splitlines():
  fields=line.split()
  if len(fields)>=6 and fields[-1].startswith('/'):
   path=fields[-1]
   if is_libm(path):paths.add(path)
   if Path(path).name.startswith('libpython'):py.add(path)
 if not paths:raise RuntimeError('Actual mapped math library required')
 return paths,py

def manifest():
 from src.transformer_backend import _check_runtime,_file_hash
 _check_runtime();paths,py=libraries(Path('/proc/self/maps').read_text())
 fields={};selected={'vendor_id','cpu family','model','model name','stepping','flags','CPU implementer','CPU architecture','CPU variant','CPU part','CPU revision','Features'}
 for line in Path('/proc/cpuinfo').read_text().split('\n\n',1)[0].splitlines():
  if ':' in line:
   k,v=(s.strip() for s in line.split(':',1))
   if k in selected:fields[k]=v
 return {'python':sys.version,'implementation':sys.implementation.name,'python_executable_sha256':_file_hash(sys.executable),
 'math_extension_sha256':_file_hash(math.__file__) if getattr(math,'__file__',None) else 'built-in; bound by Python binaries',
 'loaded_python_libraries_sha256':sorted(_file_hash(p) for p in py),'loaded_libm_sha256':sorted(_file_hash(p) for p in paths),
 'actual_libm_paths':sorted(paths),'libc':list(platform.libc_ver()),'system':platform.system(),'machine':platform.machine(),
 'cpu_dispatch_fields':fields,'byteorder':sys.byteorder,'binary64':[sys.float_info.radix,sys.float_info.mant_dig,sys.float_info.max_exp],
 'rounding':'nearest; caller must not mutate fenv during evaluation','subnormals':'gradual underflow; checked at each public evaluation',
 'scope':'v125 approximate likelihood only; not certified native calibration'}

@contextmanager
def likelihood_manifest_scope():
 from src import transformer_backend as backend
 old=backend._runtime_manifest;backend._runtime_manifest=manifest
 try:yield
 finally:backend._runtime_manifest=old
