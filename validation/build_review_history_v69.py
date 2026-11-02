"""Extend the checked development companion with explicit historical projections.

Only preserved reports are read. No inference, archive extraction or empirical launch.
Original identifiers are retained only in the separate private derivation map.
"""
from pathlib import Path
import argparse,copy,hashlib,json,re,zipfile
import build_review_summary_v69 as base

ROOT=base.ROOT
SOURCES=dict(base.SOURCES,stage='campaigns/ci_scale_v39/analysis.json',native='campaigns/ci_native_scale_v40/analysis.json',
 pilot='validation/v48_v43_full_archive.json',pilot_bytes='validation/v43_local_archive.json',
 old_quality='campaigns/csis_exposed_quality_v44/quality/outputs/completion.json',old_quality_cost='validation/v44_local_archive.json',
 parity='campaigns/csis_cuda_parity_v47/parity/outputs/completion.json',parity_cost='validation/v47_local_archive.json',
 refusal='validation/v52_v51_point_pair_audit.json',higher='validation/v52_terminal_audit.json',
 admission_failure='validation/v53_admission_failure_audit.json',quality_launch='validation/v56_launch_audit.json',
 index='docs/EVIDENCE_INDEX_MAP_V69.json')


def build(sources):
 out,mapping,cases,count=base.build(sources)
 def put(target,src,path):
  node=out
  for key in target[:-1]:node=node.setdefault(key,{})
  if target[-1] in node:raise ValueError('Output collision')
  node[target[-1]]=copy.deepcopy(base.get(sources[src],path))
  mapping.append(dict(output_path=target,source=src,input_path=path))
 def p(eid,key,src,path):put(['records',eid,key],src,path)
 for i,record in enumerate(sources['index']['records']):
  eid=record['record_id']
  if eid not in out['records']:out['records'][eid]={};p(eid,'title','index',['records',i,'title'])
  p(eid,'historical_scope','index',['records',i,'scope'])
 for eid,src in [('E01','stage'),('E02','native')]:
  for k in ['full_model','confirmation','lifetime_benefit_established','paired_repetitions','population_inference','stage','analysis_cpu_ns','analysis_cost_outside_worker_ledger']:
   p(eid,k,src,[k])
  for group in ['data','model']:
   for k in ['charged_cpu_seconds','phase_cpu_seconds','over_cap']:
    put(['records',eid,'costs',group,k],src,['budgets',group,k])
  for tokens,case in sources[src]['cases'].items():
   for k in ['all_arms_certified','exact_code_agreement']:
    put(['records',eid,'cases',tokens,k],src,['cases',tokens,k])
   for arm,fields in case['arms'].items():
    for k in ['certificate_accepted','code_count','codes_committed','component_elapsed_ns','component_state_bytes','fallback','fallback_elapsed_ns','neural_stage_record_pairs','state_scope','status']:
     put(['records',eid,'cases',tokens,'arms',arm,k],src,['cases',tokens,'arms',arm,k])
    if 'fallback_refusal' in fields:put(['records',eid,'cases',tokens,'arms',arm,'fallback_refusal'],src,['cases',tokens,'arms',arm,'fallback_refusal'])
    solver=fields['solver']
    for path in [['fallback_rows'],['diagnostics','rows','fallback_rows']]:
     try:base.get(solver,path)
     except (KeyError,TypeError):continue
     put(['records',eid,'cases',tokens,'arms',arm,'numerical_solver_fallback_rows'],src,['cases',tokens,'arms',arm,'solver']+path);break
 for k in ['charged_cpu_seconds','prior_failed_cpu_seconds','total_continuation_cpu_seconds','comparisons','costs','ratios','lifetime_scope','complete_model_verified_by_remote_audits','confirmation','numerical_reproduction']:
  p('E04',k,'pilot',[k])
 p('E04','actual_payload_comparisons','pilot_bytes',['comparisons'])
 # All historical screens reuse the same eight exposed article identities.
 old_ids=sorted({r['id'] for rows in sources['old_quality']['quality'].values() for r in rows})
 if len(old_ids)!=8 or set(old_ids)!=set(cases):raise ValueError('Historical article overlap differs from the preserved eight-case frame')
 old_cases=dict(cases)
 for k in ['approximate_numpy_binary64_likelihood','certified_inference','code_count','confirmation','development_guards_pass','original_normalization','retained_calibration_tokens','sequential_construction_elapsed_ns','worker_elapsed_ns','cpu_self_seconds','max_rss_kib','no_new_quality_inputs']:
  p('E05',k,'old_quality',[k])
 for k in ['charged_cpu_seconds','all_reservations_settled','inference_repeated']:
  p('E05',k,'old_quality_cost',[k])
 for k in ['guards','thresholds','totals','inferential_interval']:
  put(['records','E05','quality',k],'old_quality',['summary',k])
 for model,rows in sources['old_quality']['quality'].items():
  for i,row in enumerate(rows):
   for k in ['elapsed_ns','mean_nll','nll_sum','predictions']:
    put(['records','E05','quality','articles',old_cases[row['id']],model,k],'old_quality',['quality',model,i,k])
 for model,vals in sources['old_quality']['summary']['fixed_feature_comparisons'].items():
  for k in vals:
   if k.startswith('article_'):continue
   put(['records','E05','quality','comparisons',model,k],'old_quality',['summary','fixed_feature_comparisons',model,k])
 for k in ['amp','certified_inference','confirmation','copied_arrays_with_bitwise_roundtrip','cpu_self_seconds','deterministic_algorithms','device','dtype','exact_calibration_equivalence','first_actual_batch_parity_passed','max_rss_kib','new_quality_inputs','parity_passed','peak_cuda_allocated_bytes','peak_cuda_reserved_bytes','scope','tf32','torch','worker_elapsed_ns']:
  p('E06',k,'parity',[k])
 for k in ['failed_v46_charge','cpu_export_charge','gpu_parity_charge','all_three_worker_reservations_settled','parameter_npz_copied_locally','numerical_inference_repeated']:
  p('E06',k,'parity_cost',[k])
 for k in ['maximum_absolute_mean_nll_deviation','passed']:
  put(['records','E06','parity',k],'parity',['parity',k])
 for i,row in enumerate(sources['parity']['parity']['checks']):
  for k in ['absolute_mean_nll_deviation','passed','threshold']:
   put(['records','E06','parity','checks',old_cases[row['id']],row['model'],k],'parity',['parity','checks',i,k])
 for k in ['all_point_code_bytes_equal','code_count','point_measurements','candidate_over_reference_solve_time','feature_descriptor_bytes','compressed40_feature_saving','failure','charged_cpu_seconds','total_charged_cpu_seconds','gate_passed','complete_model','quality_evaluation','confirmation','scope']:
  p('E08',k,'refusal',[k])
 for k in ['actual_complete_code_bytes_equal','adaptive_development','charged_cpu_seconds','complete_model','complete_stage_codes','confirmation','encoding_and_containment_seconds','feature_descriptor_bytes','feature_saving_vs_v51_lossless','interval_fallback_rows','max_coefficient_radius','native_certified_rows','peak_rss_kib','prior_preparation_charge','prior_preparation_reused','prior_v51_total_charge','quality_evaluation','scope','solve_and_write_seconds','worker_elapsed_seconds']:
  p('E09',k,'higher',[k])
 for k in ['program_created','numerical_worker_started','numerical_budget_created','software_tests_passed','registration_scheduler_cpu_seconds','cause']:
  p('E10',k,'admission_failure',[k])
 out['records']['E10']['completed_outcomes']='See E12; software/admission records are not model results.'
 for group in ['v55','v56']:
  for k in ['tests_passed','skipped','source_files']:
   put(['records','E11','qualification',group,k],'quality_launch',['checks',group,k])
 for k in ['numerical_results_verified','confirmation']:
  p('E11',k,'quality_launch',[k])
 out['records']['E11']['completed_outcomes']='See E12 for actual failed CPU quality and passing GPU parity.'
 out['scopes']['historical_quality']='Q01--Q08 identify the same eight exposed articles across E05,E06,E12,E13. Reusing them is adaptive development, not independent quality confirmation.'
 out['scopes']['record_completeness']='All fifteen historical groups have selected summaries or scope notes. This is not their complete protocol/source/receipt dependency closure.'
 assert set(out['records'])=={f'E{i:02d}' for i in range(1,16)}
 count=base.verify_projection(out,mapping,sources)
 return out,mapping,dict(later_exposed=cases,earlier_exposed=old_cases),count


README='''Development evidence companion, draft revision B

results.json covers all fifteen historical groups in EVIDENCE_INDEX.txt. It keeps
29 stage-scale arm observations, the early complete service and exposed-quality
screen, CPU/CUDA evaluator parity, the wide-stage refusal and adaptive precision
diagnostic, admission failure, and later service/quality/storage results.
E03 supplies a historical scope note; E10/E11 separate qualification/admission
from actual outcomes in E12. This is a selected summary, not complete source,
protocol or original execution receipts. The reproduction package remains open.

Every copied field group matches its bound original report. The separate private
derivation map records source paths, original hashes and identity renaming; it
must not enter an anonymous review package. These files have their own hashes and
are explicitly derived summaries. No original source or receipt was changed.
Q01--Q08 consistently rename the same eight exposed WikiText articles across
E05,E06,E12,E13. These screens reuse evaluation units; they are not independent.
No article text, tokens or original article identifiers are included. Timing,
quality and storage scopes differ between campaigns; do not pool their clocks,
count repeated article identities as new evidence or treat development as confirmation.

Failed quality, numerical refusal/replay, capped preparation, admission failure
and failed/recovered audit costs remain visible. Stage-scale payloads exclude
checkpoint/raw tokens/audits; they are not full service storage. Service request,
attributed preparation, worker and scheduler measures remain separate. E15 is an
artifact-only control with no repair latency or new quality measurement.

MANIFEST.sha256 binds the four payload files. CHECKS.json records only preparation
checks. The ZIP is a deterministic copy of this directory and has been reopened
and checked byte-for-byte. No binaries, corpus, environment or original logs are
included. Numerical reproduction, source/runtime qualification, final anonymity,
licensing and claim-required new evidence remain unfinished. No conference
submission has been made. Main manuscript references are not changed by this tool.
'''


def main():
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--mapping',type=Path,required=True);p.add_argument('--check',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
 for field in ['directory','mapping','check','archive']:setattr(a,field,getattr(a,field).resolve())
 manifest={l[66:]:l[:64] for l in (ROOT/'MANIFEST.sha256').read_text().splitlines()};sources={};bindings={}
 for k,path in SOURCES.items():
  raw=(ROOT/path).read_bytes();assert base.info(raw)['sha256']==manifest[path],path
  sources[k]=json.loads(raw);bindings[k]=dict(path=path,**base.info(raw))
 result,mapping,cases,count=build(sources)
 probes={}
 for name,path,value in [('hide_stage_refusal',['records','E01','cases','768','arms','compressed_32','fallback'],False),('erase_feasibility_failure',['records','E08','gate_passed'],True),('erase_adaptive_scope',['records','E09','adaptive_development'],False),('alter_service_clock',['records','E14','service_arms','cached','request_elapsed_ns'],[0,0])]:
  bad=copy.deepcopy(result);node=bad
  for k in path[:-1]:node=node[k]
  assert node[path[-1]]!=value
  node[path[-1]]=value
  try:base.verify_projection(bad,mapping,sources)
  except ValueError:probes[name]=True
  else:probes[name]=False
 assert all(probes.values())
 # Check exact record/arm/article censuses independently of the projections.
 assert sum(len(c['arms']) for c in result['records']['E01']['cases'].values())==17
 assert sum(len(c['arms']) for c in result['records']['E02']['cases'].values())==12
 assert len(result['records']['E05']['quality']['articles'])==8
 assert sum(len(v) for v in result['records']['E06']['parity']['checks'].values())==32
 check=dict(schema='historical-review-companion-check-v69b',status='passed_projection_and_census_checks',record_count=15,copied_field_groups=count,input_source_count=len(sources),stage_arm_observations=29,earlier_exposed_articles=8,later_exposed_articles=8,unique_exposed_articles=8,shared_article_identity_verified=True,mutation_probes_detected=probes,numerical_execution=False,original_receipts_modified=False,full_reproduction_verified=False,full_anonymity_verified=False)
 payload={'results.json':json.dumps(result,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n','README.txt':README.encode(),'EVIDENCE_INDEX.txt':(ROOT/'reports/anonymous-evidence-index.txt').read_bytes(),'CHECKS.json':json.dumps(check,sort_keys=True,indent=2).encode()+b'\n'}
 for raw in payload.values():assert not base.IDENTITY.search(raw.decode()),'Known identity in payload'
 payload['MANIFEST.sha256']=''.join(base.info(payload[n])['sha256']+'  '+n+'\n' for n in sorted(payload)).encode()
 assert not a.archive.exists() and not a.mapping.exists() and not a.check.exists()
 a.directory.mkdir(parents=True,exist_ok=False)
 for n,raw in payload.items():
  with (a.directory/n).open('xb') as f:f.write(raw)
 with zipfile.ZipFile(a.archive,'x',compression=zipfile.ZIP_STORED) as z:
  for n,raw in sorted(payload.items()):
   entry=zipfile.ZipInfo('development-evidence/'+n,date_time=(1980,1,1,0,0,0));entry.create_system=3;entry.external_attr=0o100644<<16;z.writestr(entry,raw)
 with zipfile.ZipFile(a.archive) as z:
  assert len(z.infolist())==5 and set(z.namelist())=={'development-evidence/'+n for n in payload}
  for n,raw in payload.items():assert z.read('development-evidence/'+n)==raw==(a.directory/n).read_bytes()
 private=dict(schema='historical-review-private-derivation-v69b',exclude_from_anonymous_archive=True,generators={Path(__file__).name:base.info(Path(__file__).read_bytes()),Path(base.__file__).name:base.info(Path(base.__file__).read_bytes())},sources=bindings,copied_fields=mapping,article_renaming=cases,output_files={n:base.info(v) for n,v in payload.items()},archive=base.info(a.archive.read_bytes()),originals_unchanged=True,derivatives_are_not_original_receipts=True)
 with a.mapping.open('x') as f:json.dump(private,f,sort_keys=True,indent=2);f.write('\n')
 report=dict(check,output_directory=str(a.directory.relative_to(ROOT)),archive=dict(path=str(a.archive.relative_to(ROOT)),**private['archive']),output_files=private['output_files'],private_mapping=dict(path=str(a.mapping.relative_to(ROOT)),**base.info(a.mapping.read_bytes())),archive_members_verified=5,archive_byte_readback=True,filesystem_extraction_verified=False,source_reproduction=False,manuscript_changed=False)
 with a.check.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({k:report[k] for k in ['status','record_count','copied_field_groups','input_source_count','archive','mutation_probes_detected']}))

if __name__=='__main__':main()
