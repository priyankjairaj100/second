"""Build a reversible source review component without mutating frozen originals."""
from pathlib import Path
import ast,copy,datetime,hashlib,json,subprocess,zipfile
R=Path(__file__).resolve().parents[1]
ZIP=R/'reports/development-source-review-v69c.zip'
PRIVATE=R/'docs/REVIEW_SOURCE_DERIVATION_V69C.json'
CHECK=R/'validation/v69_review_source_build_c.json'
MAPPING={
 '/nfs_home/users/poonam/second-20261010':'/review/project',
 '/nfs_home/software/envs/pytorch-12.8':'/review/runtime',
 'priyankjairaj100/second':'REVIEW_OWNER/REVIEW_REPOSITORY',
 'poonam':'review_user',
 'csis.':'reviewcluster.',
 'csis_':'reviewcluster_',
 'CSIS':'REVIEW_CLUSTER'}

def sha(b):return hashlib.sha256(b).hexdigest()
def info(b):return dict(bytes=len(b),sha256=sha(b))
def enc(d):return (json.dumps(d,sort_keys=True,indent=2)+'\n').encode()
def replace(s,m):
 for k,v in sorted(m.items(),key=lambda x:-len(x[0])):s=s.replace(k,v)
 return s
class Rename(ast.NodeTransformer):
 def visit_Constant(self,n):
  if isinstance(n.value,str):n.value=replace(n.value,MAPPING)
  return n

def build():
 for p in [ZIP,PRIVATE,CHECK]:
  if p.exists():raise FileExistsError('Preserve existing output '+str(p))
 inventory=json.loads((R/'validation/v69_submission_inventory.json').read_text())['source_files']
 inventory.update(json.loads((R/'validation/v69_source_package_supplement.json').read_text())['sources']);assert len(inventory)==534
 manifest={l[66:]:l[:64] for l in (R/'MANIFEST.sha256').read_text().splitlines()}
 originals={};adapted={};changed={};parsed=0;reverse={v:k for k,v in MAPPING.items()}
 for name,e in sorted(inventory.items()):
  p=R/name;assert not p.is_symlink();b=p.read_bytes();assert info(b)==e and manifest[name]==e['sha256'];s=b.decode()
  assert not any(v in s for v in MAPPING.values()),name
  a=replace(s,MAPPING);assert replace(a,reverse)==s,name
  if p.suffix=='.py':
   before=ast.parse(s,feature_version=(3,10));after=ast.parse(a,feature_version=(3,10))
   assert ast.dump(Rename().visit(before))==ast.dump(after),name
   parsed+=1
  originals[name]=e;adapted[name]=a.encode()
  if a!=s:changed[name]=dict(original=e,derivative=info(a.encode()),replacement_counts={k:s.count(k) for k in MAPPING if k in s})
 assert len(changed)==34 and parsed==503
 readme='''Source review component: adapted copies, not executed research bytes\n\nThis component contains534 source/protocol/wrapper files from the prepared chain.\nIt includes the two legacy helper/package files required by the static import review.\nThirty-four files have only declared account/repository/node/path identifiers replaced.\nEvery copy reverses to its committed original bytes using a separate provenance map.\nAll503 Python files parse with Python3.10 grammar; their ASTs differ only by those\nstring replacements. This does not establish numerical or operational equivalence.\n\nPlaceholders\n/review/project is an illustrative checkout root, /review/runtime an interpreter\ninstallation prefix, review_user an account, reviewcluster.* illustrative node names and\nREVIEW_OWNER/REVIEW_REPOSITORY a repository placeholder. Historical institution\nmarkers become reviewcluster_ or REVIEW_CLUSTER. They are not available\nservices. No source is licensed anew by this component; project release terms and\nthird-party notices are still being reviewed. No dependency/model/data/environment\nbinaries, real registrations, live ledgers or article token arrays are bundled.\nThe original source may contain tiny generated software-test fixtures.\n\nDo not run historical empirical launchers or attempt to satisfy their original\nhashes with these adapted bytes. Frozen source/runtime/input hashes and one-use\nguards still describe the preserved original experiments. Empirical reproduction\nrequires a NEW prospectively admitted environment, paths, inputs, registration,\nresource budget and one-use attempt. The active V67 experiment is unchanged.\n\nLocal fixture check\nThe included qualify_review_source.py checks22 V68 and92 V69 generated fixtures\nfrom an extracted copy using CPython3.12.7 with NumPy2.3.5 in an existing environment. This is a local\nfixture environment, not a production runtime lock. Invoke with\npython -I -B qualify_review_source.py PATH_TO_THIS_DIRECTORY --report REPORT.json\n--log TESTS.txt --temporary EMPTY_TEMP_DIRECTORY\nUse new report/log paths. The checker enforces a120/121-second CPU bound and64MiB\nfile bound, rejects network and process launches except bash syntax checks, and\nconfines writes to the temporary directory and report/log. Production numerical\nconstructors, checkpoint/runtime and Slurm boundaries remain mocked; tiny generated\nCPU likelihood fixtures are real. Actual Linux98-test and CUDA qualification are\nseparate pending gates. This is not full empirical reproduction or anonymity\nclearance. Do not infer any scientific result from fixture success.\n\nThe historical summary and receipt companions preserve adverse findings and costs.\nThey remain separate components until the complete reviewed submission bundle is\nassembled and qualified.\n'''
 adapted['README.txt']=readme.encode();adapted['qualify_review_source.py']=(R/'validation/qualify_review_source_v69.py').read_bytes()
 assert all(not any(k in b.decode() for k in MAPPING) for b in adapted.values())
 files={n:info(b) for n,b in sorted(adapted.items())};m=''.join(e['sha256']+'  '+n+'\n' for n,e in files.items()).encode();adapted['MANIFEST.sha256']=m;files['MANIFEST.sha256']=info(m)
 with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in sorted(files):
   i=zipfile.ZipInfo('source-review/'+name,date_time=(2026,10,16,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,adapted[name])
 for name,e in originals.items():assert info((R/name).read_bytes())==e
 archive=dict(path=str(ZIP.relative_to(R)),**info(ZIP.read_bytes()))
 PRIVATE.write_bytes(enc(dict(schema='review-source-private-derivation-v69',exclude_from_anonymous_archive=True,mapping=MAPPING,changed_files=changed,original_files=originals,derivative_files=files,archive=archive)))
 report=dict(schema='review-source-component-build-v69',revision='C_after_broader_institution_marker_review',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='built_pending_clean_fixture_qualification',archive=archive,original_source_count=534,unchanged_original_sources=534,exact_byte_original_copies=500,adapted_copies=34,python_asts_checked=503,python_changes_only_declared_strings=True,all_copies_reverse_to_original_bytes=True,package_files=len(files),packaging_private_mapping=str(PRIVATE.relative_to(R)),known_identity_replacements_only=True,full_anonymity_verified=False,full_reproduction_verified=False,original_execution_changed=False,empirical_work_executed=False)
 CHECK.write_bytes(enc(report));print(json.dumps(report))
if __name__=='__main__':build()
