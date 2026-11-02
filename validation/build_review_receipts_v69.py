"""Create labelled receipt derivatives, preserving every original typed field.

No scientific code is imported or executed. Original archives remain immutable.
The private reverse map must not enter a review archive.
"""
from pathlib import Path
import copy,datetime,hashlib,json,re,tarfile,tempfile,zipfile
R=Path(__file__).resolve().parents[1]
OUT=R/'reports/review-audit-receipts-v69'
ZIP=R/'reports/development-audit-receipts-v69.zip'
PRIVATE=R/'docs/REVIEW_RECEIPT_DERIVATION_V69.json'
CHECK=R/'validation/v69_review_receipts.json'
IDENTITY=re.compile(r'priyank|poonam|172\.24\.16\.132|csis\.(?:mn|cn)\d+|/Users/|/nfs_home/|github\.com/priyankjairaj100/second|wikitext2:(?:validation|train|test):article-row-\d+|c4:[^\s"\\]{1,120}',re.I)

def digest(b):return hashlib.sha256(b).hexdigest()
def encoded(v):return (json.dumps(v,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()
def commit(b):return dict(bytes=len(b),sha256=digest(b))
def strings(v):
 if isinstance(v,str):yield v
 elif isinstance(v,list):
  for x in v:yield from strings(x)
 elif isinstance(v,dict):
  for k,x in v.items():yield k;yield from strings(x)
def transform(v,mapping):
 if isinstance(v,str):return mapping.get(v,v)
 if isinstance(v,list):return [transform(x,mapping) for x in v]
 if isinstance(v,dict):
  result={}
  for k,x in v.items():
   key=mapping.get(k,k)
   if key in result:raise ValueError('Redaction would collide with another object key')
   result[key]=transform(x,mapping)
  return result
 return v

def verify(original,derivative,reverse):
 # Canonical serialization distinguishes numbers/Booleans and preserves structure.
 if encoded(original)!=encoded(transform(derivative,reverse)):
  raise ValueError('Derivative does not preserve the original typed JSON object')
 if IDENTITY.search(encoded(derivative).decode()):raise ValueError('Known identifying text remains')

def census(v,out=None):
 if out is None:out=dict(objects=0,arrays=0,strings=0,numbers=0,booleans=0,nulls=0,object_keys=0)
 if isinstance(v,dict):
  out['objects']+=1;out['object_keys']+=len(v)
  for x in v.values():census(x,out)
 elif isinstance(v,list):
  out['arrays']+=1
  for x in v:census(x,out)
 elif isinstance(v,str):out['strings']+=1
 elif type(v)is bool:out['booleans']+=1
 elif type(v)in(int,float):out['numbers']+=1
 elif v is None:out['nulls']+=1
 else:raise ValueError('Unexpected JSON value')
 return out

def build():
 for p in [OUT,ZIP,PRIVATE,CHECK]:
  if p.exists():raise FileExistsError('Preserve previous artifact; output already exists: '+str(p))
 plan=json.loads((R/'docs/SOURCE_RECEIPT_SELECTION_V69.json').read_text())
 inspection=json.loads((R/'validation/v69_archive_content_review.json').read_text())
 manifest={l[66:]:l[:64] for l in (R/'MANIFEST.sha256').read_text().splitlines()}
 assert digest((R/'docs/SOURCE_RECEIPT_SELECTION_V69.json').read_bytes())==manifest['docs/SOURCE_RECEIPT_SELECTION_V69.json']
 originals=[];all_strings=set();names=['E10_primary','E10_additive','E12_exposed_quality','E11_cpu_cuda_parity','E13_adaptive_quality','E14_primary_recovery','E14_additive_recovery','E15_lossless_measurement','E15_lossless_audit']
 assert len(plan['original_receipt_candidates'])==len(names)==9
 for name,row in zip(names,plan['original_receipt_candidates']):
  a=row['archive'];raw=(R/a).read_bytes();assert digest(raw)==manifest[a]
  assert commit(raw)==inspection['archives'][a]['commitment']
  assert not inspection['archives'][a]['members'][row['member']]['payload_candidates']
  with tarfile.open(R/a,'r:gz') as t:
   m=t.getmember(row['member']);assert m.isfile() and m.size<=16*2**20
   b=t.extractfile(m).read(m.size+1)
  assert commit(b)==row['original_commitment']
  data=json.loads(b);all_strings.update(strings(data));originals.append((name,row,data))
 prior=json.loads((R/'docs/REVIEW_HISTORY_DERIVATION_V69.json').read_text())
 known=prior['article_renaming']['earlier_exposed'];assert known==prior['article_renaming']['later_exposed']
 flagged=sorted(s for s in all_strings if IDENTITY.search(s));mapping={};counts=dict(paths=0,known_exposed_articles=0,other_article_identifiers=0)
 for s in flagged:
  if s in known:
   replacement=known[s];counts['known_exposed_articles']+=1
  elif s.startswith(('/nfs_home/','/Users/')):
   counts['paths']+=1;replacement='REVIEW_PATH_'+str(counts['paths']).zfill(4)
  elif s.startswith(('wikitext2:','c4:')):
   counts['other_article_identifiers']+=1;replacement='REVIEW_ARTICLE_'+str(counts['other_article_identifiers']).zfill(4)
  else:raise ValueError('Unreviewed identifying string category; stop before writing')
  assert replacement not in all_strings and replacement not in mapping.values()
  mapping[s]=replacement
 reverse={v:k for k,v in mapping.items()};derived=[];total=census({})
 for k in total:total[k]=0
 for name,row,original in originals:
  d=transform(original,mapping);verify(original,d,reverse)
  c=census(d);assert c==census(original)
  for k,v in c.items():total[k]+=v
  derived.append((name,row,original,d,c))
 # Meaningful integrity probes: changing an adverse Boolean or cost, dropping a
 # field, and a mapping collision must all be rejected before outputs are written.
 probes=[]
 for name,label,mutate in [
  ('E12_exposed_quality','adverse_guard_flip',lambda d:d.__setitem__('development_guards_pass',True)),
  ('E10_primary','failed_cost_change',lambda d:d.__setitem__('prior_failed_cpu_seconds',d['prior_failed_cpu_seconds']+1)),
  ('E14_primary_recovery','drop_budget',lambda d:d.pop('budget'))]:
  _,_,o,d,_=next(x for x in derived if x[0]==name);bad=copy.deepcopy(d)
  if label=='adverse_guard_flip':assert bad['development_guards_pass'] is False
  mutate(bad)
  try:verify(o,bad,reverse)
  except ValueError:probes.append(label)
  else:raise AssertionError('Tamper not detected')
 try:transform({'a':1,'b':2},{'a':'x','b':'x'})
 except ValueError:probes.append('mapping_collision')
 else:raise AssertionError('Collision not detected')
 assert len(probes)==4
 OUT.mkdir()
 file_bindings={};private_rows=[]
 for name,row,original,d,c in derived:
  filename=name+'.json';b=encoded(d);(OUT/filename).write_bytes(b);file_bindings[filename]=commit(b)
  private_rows.append(dict(output=filename,derivative=commit(b),original=row,census=c,typed_roundtrip_verified=True))
 readme='''Selected historical audit receipts: review derivatives\n\nThese nine JSON files are labelled derivatives of preserved execution receipts.\nIdentifying absolute paths are replaced consistently by REVIEW_PATH_####. The\nsame eight exposed evaluation articles retain Q01--Q08 across these receipts and\nthe development-evidence summary. Other historical article identifiers, if any,\nuse REVIEW_ARTICLE_####. No raw article/token/model/state binary is included.\n\nEvery original JSON number, Boolean, null, array order and field is preserved.\nOnly selected string values/object keys change. A private reverse map verifies\nexact typed-object roundtrips and collision rejection. Original byte commitments\nand this private mapping are not included here. Embedded source/input/artifact\nhashes still refer to ORIGINAL execution objects: a redacted path does not satisfy\nthe corresponding original binding. Do not execute these copies as registrations.\n\nRecord guide\nE10_primary/additive: nearest-anchor complete service and two saved-artifact audits.\nE12_exposed_quality: the historical quality screen FAILED its unchanged pooled guard.\nE11_cpu_cuda_parity: implementation parity only; it does not repair that quality loss.\nE13_adaptive_quality: the full-precision follow-up reuses the SAME exposed articles.\nE14_primary/additive_recovery: separately registered recovery of the original service\n  audits. The original audit timeout/cancellation and costs remain in the development\n  history; recovery does not erase them or create independent experimental repeats.\nE15_lossless_measurement/audit: artifact-only lossless compression and portable audit,\n  with no new deletion/repair latency or model-quality result.\n\nThis component supplements the15-record development-evidence summary. It is not\na complete source/protocol/runtime package, a rerun of numerical inference, final\nanonymity clearance, or confirmation of general speed or untouched quality.\nSuccessful JSON integrity checks do not verify model/state binary equality anew.\nHistorical results and failed/adaptive scope remain unchanged.\n'''
 assert not IDENTITY.search(readme);b=readme.encode();(OUT/'README.txt').write_bytes(b);file_bindings['README.txt']=commit(b)
 manifest_text=''.join(v['sha256']+'  '+k+'\n' for k,v in sorted(file_bindings.items()));b=manifest_text.encode();(OUT/'MANIFEST.sha256').write_bytes(b);file_bindings['MANIFEST.sha256']=commit(b)
 with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in sorted(file_bindings):
   info=zipfile.ZipInfo('audit-receipts/'+name,date_time=(2026,10,16,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
   z.writestr(info,(OUT/name).read_bytes())
 # Clean bounded extraction and second roundtrip against actual extracted bytes.
 with tempfile.TemporaryDirectory(prefix='second-receipt-review-') as directory:
  dest=Path(directory)
  with zipfile.ZipFile(ZIP) as z:
   assert len(z.infolist())==11 and set(z.namelist())=={'audit-receipts/'+n for n in file_bindings}
   for i in z.infolist():
    p=Path(i.filename);assert not p.is_absolute() and '..' not in p.parts and i.file_size<16*2**20
    b=z.read(i);assert commit(b)==file_bindings[p.name];q=dest/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
  for name,row,o,d,c in derived:
   saved=json.loads((dest/'audit-receipts'/(name+'.json')).read_text());verify(o,saved,reverse)
  assert len(list(dest.rglob('*.*')))==11
 for _,row,_ in originals:
  assert digest((R/row['archive']).read_bytes())==manifest[row['archive']]
 archive=commit(ZIP.read_bytes());archive['path']=str(ZIP.relative_to(R))
 private=dict(schema='review-receipt-private-derivation-v69',exclude_from_anonymous_archive=True,mapping=mapping,article_renaming=known,rows=private_rows,archive=archive,original_archives_unchanged=True,originals_are_execution_evidence=True,derivatives_are_original_receipts=False)
 PRIVATE.write_bytes(encoded(private))
 report=dict(schema='review-receipt-derivative-check-v69',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='typed_derivatives_and_clean_extraction_verified',receipt_count=9,archive=archive,output_files=file_bindings,redacted_string_counts=counts,typed_census=total,exact_typed_json_roundtrips=9,unchanged_numeric_and_boolean_values=True,shared_exposed_article_count=counts['known_exposed_articles'],tamper_probes_rejected=probes,clean_extraction_files=11,known_identity_scan_passed=True,full_anonymity_verified=False,numerical_audits_repeated=False,empirical_work_executed=False,execution_sources_or_registrations_changed=False,original_archives_unchanged=True,private_mapping='docs/REVIEW_RECEIPT_DERIVATION_V69.json',submission_ready=False,complete_reproduction_package=False)
 CHECK.write_bytes(encoded(report));print(json.dumps({k:report[k] for k in ['status','receipt_count','archive','redacted_string_counts','typed_census','clean_extraction_files']}))

if __name__=='__main__':build()
