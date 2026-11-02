"""Prepare a small review companion from explicit, preserved report fields.

Original bytes remain unchanged. The identifying derivation map stays outside
the review directory. No archive extraction, calibration, inference or network.
"""
from pathlib import Path
import argparse, copy, hashlib, json, re

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'near':'validation/v58_terminal_metadata_check.json',
 'candidate':'validation/v59_terminal_metadata_check.json',
 'service':'validation/v62_recovery_metadata_check.json',
 'codec':'validation/v63_terminal_metadata_check.json',
 'near_cost':'handoff/program_v58.json',
 'service_cost':'handoff/program_v62.json',
 'codec_cost':'handoff/program_v63.json',
 'failure':'validation/v49_v45_failure_audit.json',
}
IDENTITY=re.compile(r'priyankjairaj|poonam|172\.24\.16\.132|csis\.(?:mn|cn)\d+|/Users/|/nfs_home/|second-20261010|github\.com/priyank',re.I)


def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def info(raw):
 return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def get(value,path):
 for key in path:value=value[key]
 return value


def verify_projection(summary,mapping,sources):
 seen=set()
 for row in mapping:
  target=tuple(row['output_path'])
  if target in seen:raise ValueError('Duplicate output projection')
  seen.add(target)
  if canonical(get(summary,target))!=canonical(get(sources[row['source']],row['input_path'])):
   raise ValueError('Copied evidence differs at '+'.'.join(target))
 if IDENTITY.search(canonical(summary).decode('ascii')):
  raise ValueError('Known identifying string entered the review summary')
 return len(seen)


def build(sources):
 summary=dict(schema='review-evidence-summary-v1',status='preparation',
  evidence_kind='derived numerical summary of preserved development audit reports',
  original_receipts_included=False,full_reproduction_package_complete=False,
  calibration_inference_or_binary_audit_repeated=False,
  scopes=dict(quality='Eight previously exposed articles; adaptive development only.',
    timing='One fixed-order observation per request; no population timing confidence interval.',
    state='Agreement is representation-specific and uses the declared fixed-teacher reconstruction target.',
    audit='Cluster actual-byte audit findings are reported; this companion does not reexecute them.',
    cost='Attributed preparation and two-request sums use the recorded reporting convention; they are not a measured deployment lifetime.',
    pending='Complete modern-lossless service, untouched quality and claim-required timing decisions remain pending.'),
  units=dict(request_and_process_times='nanoseconds unless a key states seconds',
    storage='bytes; checkpoint-inclusive deployment is separate from live state',
    quality='mean negative log likelihood in nats; perplexity is exp(mean NLL)',
    charged_cpu='integer CPU seconds, separate from elapsed wall time'),records={})
 mappings=[]
 def put(target,source,path):
  node=summary
  for key in target[:-1]:node=node.setdefault(key,{})
  if target[-1] in node:raise ValueError('Output collision')
  node[target[-1]]=copy.deepcopy(get(sources[source],path))
  mappings.append(dict(output_path=target,source=source,input_path=path))
 def record(eid,title):summary['records'][eid]=dict(title=title)
 def project(eid,name,source,path):put(['records',eid,name],source,path)
 record('E07','Capped larger preparation failure')
 for key in ['charged_cpu_seconds','worker_cpu_ns','completed_stage_count','stage_count','source_records_replayed','complete_model','confirmation','quality_evaluation']:
  project('E07',key,'failure',[key])
 # Preserve the failed outcome without copying scheduler identity or host paths.
 project('E07','worker_outcome','failure',['worker_outcome'])
 record('E12','Nearest-anchor service and failed exposed-quality guard')
 record('E13','Adaptive original-checkpoint feature-teacher quality screen')
 record('E14','Original-checkpoint repair service and separate audit recovery')
 record('E15','Modern lossless artifact control')
 for key in ['original_tokens','retained_tokens','codes','stages','historical_quality_exclusions']:
  project('E12',key,'near_cost',[key])
  project('E14',key,'near_cost',[key])
 for eid,source,base in [('E12','near',['v54']),('E14','service',[])]:
  for arm in ['cached','cold','hybrid','compressed']:
   for field in ['attributed_preparation_ns','attributed_two_deletion_lifetime_ns',
       'complete_deployment_bytes','live_state_bytes','request_elapsed_ns',
       'transaction_elapsed_ns','worker_elapsed_ns','worker_outside_request_ns']:
    put(['records',eid,'service_arms',arm,field],source,base+['timings',arm,field])
 project('E12','complete_model_state_comparison_count','near',['v54','comparisons'])
 for key in ['current_worker_cpu_seconds','prior_failed_cpu_seconds','total_continuation_cpu_seconds']:
  project('E12',key,'near',['v54',key])
 for target,key in [('quality_worker_charged_cpu_seconds','v55_cpu_seconds'),('gpu_worker_charged_cpu_seconds','v56_cpu_seconds')]:
  project('E12',target,'near_cost',[key])
 project('E12','gpu_likelihood_parity','near',['gpu_parity'])
 project('E12','untouched_quality','near_cost',['untouched_quality'])
 project('E13','untouched_quality','near_cost',['untouched_quality'])
 old=sources['near']['cpu_quality']['fixed_feature_comparisons']['sequential']['article_perplexity_ratios']
 new=sources['candidate']['result']['quality']['candidate_comparisons']['sequential']['article_perplexity_ratios']
 if set(old)!=set(new) or len(old)!=8:raise ValueError('Matched exposed article identity census required')
 case_ids={name:f'Q{i:02d}' for i,name in enumerate(sorted(old),1)}
 model_names={'fixed_feature':'nearest_anchor','full_precision_anchor':'original_checkpoint_anchor',
              'full_precision':'full_precision','nearest_rounding':'nearest_rounding','sequential':'sequential'}
 for eid,source,base,comparison_key in [('E12','near',['cpu_quality'],'fixed_feature_comparisons'),
       ('E13','candidate',['result','quality'],'candidate_comparisons')]:
  for key in ['guards','thresholds','development_guards_pass']:
   put(['records',eid,'quality',key],source,base+[key])
  for name in get(sources[source],base+['totals']):
   put(['records',eid,'quality','totals',model_names[name]],source,base+['totals',name])
  for model,values in get(sources[source],base+[comparison_key]).items():
   for key in ['pooled_log_perplexity_ratio','pooled_perplexity_ratio','max_article_log_ratio','max_article_ratio']:
    put(['records',eid,'quality','comparisons',model_names[model],key],source,base+[comparison_key,model,key])
   for key in values:
    if key.startswith('articles_'):
     put(['records',eid,'quality','comparisons',model_names[model],key],source,base+[comparison_key,model,key])
   for original,public in case_ids.items():
    for input_key,label in [('article_log_perplexity_ratios','log_perplexity_ratio'),('article_perplexity_ratios','perplexity_ratio')]:
     put(['records',eid,'quality','paired_articles',public,model_names[model],label],source,base+[comparison_key,model,input_key,original])
 for key in ['charged_cpu_seconds','observed_cpu_ns','constructor_elapsed_ns','controller_transaction_elapsed_ns','worker_elapsed_ns','actual_quality_guard_passed']:
  project('E13',key,'candidate',['result',key])
 for key in ['checked_losses','max_absolute_mean_nll_deviation','passed']:
  put(['records','E13','historical_control_parity',key],'candidate',['result','historical_control_parity',key])
 for target,key in [('complete_model_state_comparison_count','comparison_claims_checked'),
    ('numerical_worker_charged_cpu_seconds','charged_worker_cpu_seconds'),
    ('numerical_worker_observed_cpu_ns','observed_worker_cpu_ns'),
    ('numerical_worker_allowance_cpu_seconds','phase_cap_cpu_seconds'),
    ('original_audit_timeout_preserved','original_audit_timeout_preserved'),
    ('original_terminal_gate_passed','original_terminal_gate_passed'),
    ('same_final_models_as_E13','metadata_claims_link_final_six_models_to_v59')]:
  project('E14',target,'service',[key])
 for key in ['old_failed_audit_cpu_seconds','recovery_scheduler_cpu_seconds','independent_root_replication','prospective_timing_replication','untouched_quality']:
  project('E14',key,'service_cost',[key])
 for label,job in [('primary','15150'),('supplemental','15151')]:
  for key in ['elapsed_seconds','total_cpu','state','exit_code']:
   put(['records','E14','recovery_allocations',label,key],'service_cost',['scheduler_accounting','recovery',job,key])
 project('E15','memberships','codec',['summary'])
 for key in ['added_control_source_bytes','added_dependency_bytes','deletion_latency_measured','quality_evaluation']:
  project('E15',key,'codec',[key])
 for key in ['process_cpu_seconds','scheduler_allocation_cpu_seconds','phase_allowance_cpu_seconds','scope']:
  project('E15',key,'codec_cost',[key])
 count=verify_projection(summary,mappings,sources)
 return summary,mappings,case_ids,count


README='''Review evidence companion: preparation

This directory contains selected development results from preserved audit reports.
results.json provides the capped preparation failure (E07), nearest-anchor service
and failed quality guard (E12), adaptive original-checkpoint quality screen (E13),
original-checkpoint service and audit recovery (E14), and lossless artifact control
(E15). EVIDENCE_INDEX.txt explains all fifteen historical record groups.

Every copied field is checked against its original report. The identifying
derivation map is retained separately. These files are derived summaries, with
their own hashes; they are not copies of the original execution receipts. The
source-and-receipt reproduction package is still being prepared.

Q01--Q08 consistently rename the same eight previously exposed articles in both
quality screens. Ratios compare the named candidate with each listed comparator.
E12 uses the nearest-anchor candidate; E13 uses the original-checkpoint anchor.
Article text, tokens, original record IDs, account details and cluster paths are
excluded. The adverse pooled guard, all article directions, capped preparation
failure and failed original audit remain visible. Passing the adaptive screen
does not establish untouched quality.

Service values retain complete request clocks, live state, checkpoint-inclusive
deployment, attributed preparation and transaction totals. Nested timings are not
additional disjoint costs. CPU charges, process clocks and scheduler costs remain
distinct. E15 measures stored artifacts and copies supplied codes; it supplies no
new complete repair latency, calibration or likelihood measurement.

CHECKS.json records preparation checks. MANIFEST.sha256 binds this directory's
four payload files. This preparation does not rerun inference or binary audits.
Known-identity checks cover these files only. Final anonymity review, additional
claim-required evidence, code/source qualification, licensing and clean-package
reproduction remain pending. No conference submission has been made.
'''


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--mapping',type=Path,required=True);parser.add_argument('--check',type=Path,required=True)
 args=parser.parse_args()
 sources={};bindings={};manifest={line[66:]:line[:64] for line in (ROOT/'MANIFEST.sha256').read_text().splitlines()}
 for key,path in SOURCES.items():
  raw=(ROOT/path).read_bytes();bindings[key]=dict(path=path,**info(raw))
  if bindings[key]['sha256']!=manifest[path]:raise ValueError('Changed original evidence')
  sources[key]=json.loads(raw)
 result,mapping,cases,count=build(sources)
 mutations={}
 for name,path,value in [('changed_request',['records','E14','service_arms','cached','request_elapsed_ns'],[0,0]),
       ('erased_failed_guard',['records','E12','quality','development_guards_pass'],True),
       ('altered_article_ratio',['records','E13','quality','paired_articles','Q01','sequential','perplexity_ratio'],1.0)]:
  bad=copy.deepcopy(result);node=bad
  for key in path[:-1]:node=node[key]
  node[path[-1]]=value
  try:verify_projection(bad,mapping,sources)
  except ValueError:mutations[name]=True
  else:mutations[name]=False
 if not all(mutations.values()):raise ValueError('Mutation probe was not detected')
 public_check=dict(schema='review-summary-preparation-check-v1',status='passed_projection_checks',
    copied_field_groups=count,paired_exposed_article_ids=8,mutation_probes_detected=mutations,
    original_receipts_modified=False,numerical_execution=False,full_reproduction_verified=False,
    full_anonymity_verified=False,known_identity_scan_scope='Four payload files in this directory')
 index=(ROOT/'reports/anonymous-evidence-index.txt').read_bytes()
 payload={'results.json':json.dumps(result,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n',
    'README.txt':README.encode(),'EVIDENCE_INDEX.txt':index,
    'CHECKS.json':json.dumps(public_check,sort_keys=True,indent=2).encode()+b'\n'}
 if any(IDENTITY.search(raw.decode()) for raw in payload.values()):raise ValueError('Known identity in companion payload')
 args.directory.mkdir(exist_ok=False,parents=True)
 for name,raw in payload.items():
  with (args.directory/name).open('xb') as f:f.write(raw)
 checksums=''.join(info(payload[name])['sha256']+'  '+name+'\n' for name in sorted(payload)).encode()
 with (args.directory/'MANIFEST.sha256').open('xb') as f:f.write(checksums)
 if set(p.name for p in args.directory.iterdir())!=set(payload)|{'MANIFEST.sha256'}:raise ValueError('Unexpected file')
 for name,raw in payload.items():
  if (args.directory/name).read_bytes()!=raw:raise ValueError('Saved bytes changed')
 private=dict(schema='review-summary-private-derivation-v69',exclude_from_anonymous_archive=True,
    generator=info(Path(__file__).read_bytes()),sources=bindings,
    output_files={n:info(raw) for n,raw in payload.items()},output_manifest=info(checksums),
    copied_fields=mapping,article_renaming=cases,
    changes='Explicit projection; model labels and article IDs renamed. Copied numbers/booleans remain exact. Static descriptions disclose evidence limits.',
    originals_unchanged=True,derivatives_are_not_original_receipts=True)
 with args.mapping.open('x') as f:json.dump(private,f,sort_keys=True,indent=2);f.write('\n')
 report=dict(public_check,output_directory=str(args.directory.relative_to(ROOT)),
    output_files=private['output_files'],output_manifest=private['output_manifest'],
    private_mapping=info(args.mapping.read_bytes()),input_source_count=len(sources),
    anonymous_summary_only=True,archive_created=False,manuscript_citations_changed=False)
 with args.check.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps({k:report[k] for k in ['status','copied_field_groups','input_source_count','paired_exposed_article_ids','mutation_probes_detected','output_directory']}))


if __name__=='__main__':main()
