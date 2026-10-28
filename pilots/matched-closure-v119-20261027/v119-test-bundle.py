"""Reject byte corruption and rehashed scientific-scope/arithmetic mutations."""
from pathlib import Path
import datetime
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import zipfile

R = Path('/Users/priyankjairaj/Downloads/ACL/Second')
W = Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')
bundle = W/'outputs/second-development-review-v119.zip'
info = lambda b: dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
enc = lambda o: (json.dumps(o, indent=2, sort_keys=True)+'\n').encode()
original = bundle.read_bytes()
with zipfile.ZipFile(io.BytesIO(original)) as z:
    payload = {Path(n).name:z.read(n) for n in z.namelist()}
e20 = 'development-matched-evidence-v119.zip'

def alter_e20(files, name):
    with zipfile.ZipFile(io.BytesIO(files[e20])) as z:
        original_files = {n:z.read(n) for n in z.namelist()}
    prefix = next(iter(original_files)).split('/')[0]+'/'
    inside = {n[len(prefix):]:b for n,b in original_files.items()}
    if name == 'rehashed_false_stable_speedup':
        for file, key in [('audit-summary.json','evidence'),('results.json','scope')]:
            obj=json.loads(inside[file]);obj[key]['stable_speedup']=True;inside[file]=enc(obj)
    elif name == 'rehashed_changed_host_time':
        obj=json.loads(inside['results.json']);obj['rows'][0]['host_elapsed_ns']+=1;inside['results.json']=enc(obj)
    elif name == 'rehashed_omitted_losing_row':
        obj=json.loads(inside['results.json']);obj['rows'].pop();inside['results.json']=enc(obj)
    inside['MANIFEST.json']=enc({n:info(b) for n,b in inside.items() if n!='MANIFEST.json'})
    target=io.BytesIO()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in inside.items(): z.writestr(prefix+n,b)
    files[e20]=target.getvalue()
    files['MANIFEST.json']=enc({n:info(b) for n,b in files.items() if n!='MANIFEST.json'})

checks=[]
for name in ['unchanged_positive','corrupted_component','missing_component','unexpected_file',
             'rehashed_false_stable_speedup','rehashed_changed_host_time','rehashed_omitted_losing_row']:
    files=payload.copy()
    if name=='corrupted_component': files[e20]=files[e20]+b'corrupt'
    elif name=='missing_component': del files[e20]
    elif name=='unexpected_file': files['unexpected.txt']=b'unexpected'
    elif name.startswith('rehashed_'): alter_e20(files,name)
    with tempfile.TemporaryDirectory(prefix='second-v119-check-') as temp:
        root=Path(temp)
        for n,b in files.items(): (root/n).write_bytes(b)
        result=subprocess.run([sys.executable,'-I','-B',str(root/'verify_review_bundle.py'),str(root)],
            capture_output=True,text=True,timeout=30,cwd=root)
    expected_success=name=='unchanged_positive'
    assert (result.returncode==0)==expected_success,(name,result.stdout,result.stderr)
    checks.append(dict(case=name,expected_acceptance=expected_success,returncode=result.returncode,
                       stdout=result.stdout,stderr=result.stderr))
assert bundle.read_bytes()==original
report=dict(schema='bundle-corruption-scope-checks-v119',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            archive=info(original),positive_acceptance=True,rejection_cases=6,checks=checks,
            original_bundle_unchanged=True,numerical_execution=False,actual_binary_reaudit=False)
(R/'validation/v119_bundle_rejections.json').write_bytes(enc(report))
print(json.dumps({k:v for k,v in report.items() if k!='checks'},sort_keys=True))
