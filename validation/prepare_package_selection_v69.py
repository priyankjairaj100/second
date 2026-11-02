"""Build private receipt candidates and exclusions without changing or executing source.

Output is exclusive; preserve an existing selection record rather than overwrite it.
"""
from pathlib import Path
import ast,datetime,hashlib,json,tarfile
R=Path(__file__).resolve().parents[1]
def binding(p):
 b=(R/p).read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(p,d):
 with (R/p).open('x') as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
x=json.loads((R/'validation/v69_archive_content_review.json').read_text())
selected={
 'campaigns/csis_terminal_v54_v56_metadata_20261013.tar.gz':[
 ('full-model48-v54-20261011-a/artifact-audit.json','E10','primary saved model/state and cost audit'),
 ('full-model48-v54-20261011-a/postrun-audit.json','E10','additive independent audit implementation and accounting'),
 ('exposed-quality-v55-20261011-a/artifact-audit.json','E12','adverse exposed-quality screen and original development guards'),
 ('gpu-parity-v56-20261011-a/artifact-audit.json','E11','CPU/CUDA parity scope, tolerances and costs')],
 'campaigns/csis_terminal_v59_metadata_20261014.tar.gz':[
 ('full-precision-anchor-v59-20261014-a/artifact-audit.json','E13','adaptive full-precision construction and same exposed-quality screen')],
 'campaigns/csis_terminal_v62_recovery_metadata_20261016.tar.gz':[
 ('primary.json','E14','actual saved V61 models, fresh oracle, complete storage and cost audit recovered under V62'),
 ('postrun.json','E14','separate additive saved V61 model/state and accounting audit recovered under V62')],
 'campaigns/csis_terminal_v63_lossless_metadata_20261016.tar.gz':[
 ('measure.json','E15','artifact-only stronger-lossless measurements and complete worker costs'),
 ('audit.json','E15','portable saved-byte artifact audit and costs')]}
rows=[]
for archive,items in selected.items():
 assert binding(archive)==x['archives'][archive]['commitment']
 with tarfile.open(R/archive,'r:gz') as t:
  for name,evidence,reason in items:
   m=x['archives'][archive]['members'][name];assert not m['payload_candidates']
   raw=t.extractfile(name).read();assert len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256']
   d=json.loads(raw);assert isinstance(d,dict)
   rows.append(dict(archive=archive,member=name,evidence_record=evidence,purpose=reason,original_commitment={k:m[k] for k in ('bytes','sha256')},schema=m['json_schema'],top_level_fields=list(d),known_identity_categories=sorted(m['known_identity_match_counts']),raw_payload_heuristic_flags=m['payload_candidates'],reviewed_derivative_required=True,derivative_created=False,final_inclusion_approved=False))
exclusions=[];diagnostics=[]
for a,d in x['archives'].items():
 for n,m in d['members'].items():
  if any(f['kind']=='token_array' for f in m['payload_candidates']):
   exclusions.append(dict(archive=a,member=n,original_commitment={k:m[k] for k in ('bytes','sha256')},reason='Contains raw historical calibration or exposed-quality token arrays; preserve original but exclude from review archive.',token_array_fields=[f for f in m['payload_candidates'] if f['kind']=='token_array']))
  elif m['payload_candidates']:
   diagnostics.append(dict(archive=a,member=n,original_commitment={k:m[k] for k in ('bytes','sha256')},fields=m['payload_candidates'],review='Two18-element lists identify numerical fallback rows/failed coordinates, not token arrays. Preserve these adverse diagnostics. This does not approve inclusion of the surrounding file.'))
assert len(rows)==9 and len(exclusions)==10 and len(diagnostics)==1
review=[]
for name,line,target,expected in [
 ('research_v44/campaign.py',56,None,('numpy','scipy','gmpy2')),
 ('src/runtime_contract.py',45,'_MODULES',('fractions','decimal','_decimal','math','json','struct','_struct','fcntl','resource','hashlib','_hashlib'))]:
 source=(R/name).read_text();tree=ast.parse(source);found=[]
 if target:
  for n in ast.walk(tree):
   if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==target for t in n.targets):found.append(tuple(ast.literal_eval(n.value)))
 else:
  for n in ast.walk(tree):
   if isinstance(n,ast.For) and isinstance(n.iter,ast.Tuple) and all(isinstance(e,ast.Constant) for e in n.iter.elts):
    value=ast.literal_eval(n.iter)
    if value==expected:found.append(value)
 assert found==[expected]
 assert 'importlib.import_module(name)' in source.splitlines()[line-1]
 review.append(dict(source=name,commitment=binding(name),call_line=line,static_argument_values=list(expected),actual_runtime_executed=False,note='Bounded source-declared tuple. scipy absence is recorded as optional for the pinned gelu_new route.' if target is None else 'Bounded stdlib tuple; actual Linux interpreter, native dependencies and module origins remain runtime-gated.'))
plan=dict(schema='source-receipt-package-selection-v69',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reporting_base='a439b589cdab7b7029d1f34d26c7b2965ac7dc05',private_provenance_not_for_anonymous_archive=True,local_preparation_note='The initial AST tuple scan encountered an unrelated nonliteral tuple and stopped before writing output. It now selects literal tuples only; no experiment or source change occurred.',status='explicit_candidates_and_exclusions_prepared_not_packaged',input_reports={p:binding(p) for p in ['validation/v69_archive_content_review.json','validation/v69_static_source_closure_extended.json','validation/v69_source_package_supplement.json','validation/v69_submission_inventory.json']},prepared_execution_source_count=532,broader_package_source_count=534,execution_inventory_or_registration_changed=False,source_files_edited=False,nonliteral_dynamic_import_review=review,original_receipt_candidates=rows,raw_token_member_exclusions=exclusions,numeric_array_false_positive_review=diagnostics,original_archives_excluded_from_review_bundle=list(x['archives']),required_derivative_checks=['Use explicit per-field mappings, preserve every numeric and Boolean measurement/guard/failure/cap/cost, and retain consistent shared article labels.','Label derivatives separately from executed receipts, bind original and derivative hashes in private provenance, and do not imply original path/hash bindings validate redacted paths.','Reject mapping collisions and leftover identifying keys/values; scan all text and perform manual review before final inclusion.','Preserve failed V61 audit history and earlier adverse screens using the checked companion and original archival provenance; do not silently replace it with successful V62 recovery.','Verify final package extraction, internal pointers, notices, runtime prerequisites and a separately qualified portable workflow; static import closure is insufficient.'],untouched_data_acquired=False,empirical_work_executed=False,full_anonymity_verified=False,clean_reproduction_verified=False,submission_ready=False)
save('docs/SOURCE_RECEIPT_SELECTION_V69.json',plan)
print(json.dumps(dict(receipt_candidates=len(rows),token_exclusions=len(exclusions),dynamic_tuples_reviewed=len(review),candidate_source_count=534)))
