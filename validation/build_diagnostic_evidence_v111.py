"""Typed E19 derivative from actual failure and diagnostic receipts; no new science."""
import json
from pathlib import Path
from validation.build_review_source_v69 import info,enc
from validation.package_review_bundle_v105 import zip_payload
R=Path(__file__).resolve().parents[1]
S=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/work/second-speed-campaign')

def build():
    target=R/'reports/development-diagnostic-evidence-v111.zip';folder=R/'reports/review-diagnostic-v111'
    assert not target.exists() and not folder.exists()
    names=['v104-failure-accounting-v108.json','v110-diagnostic-review-20261026T110110Z.json',
        'v104-distilgpt2-preparation-review-20261026T085504Z.json','v104-gpt2-preparation-review-20261026T095457Z.json']
    raw={n:(S/n).read_bytes() for n in names};failed,diagnostic,distil,gpt=(json.loads(raw[n]) for n in names)
    assert failed['status']=='verified_failed_request_and_cancelled_dependents' and failed['cumulative_numerical_charged_seconds']==6196
    assert failed['complete_model_comparisons']==0 and len(failed['cancelled_unstarted_jobs'])==19
    assert diagnostic['status']=='verified_selected_stage_certificate_and_complete_accounting'
    q=diagnostic['completion'];w=diagnostic['worker'];costs=diagnostic['costs']
    assert q['status']=='certified_stage' and q['certified_codes']==2359296 and q['route']=='token'
    assert q['original_streamed_route_executed'] is q['complete_model'] is q['speed_comparison'] is q['transfer_evidence'] is False
    assert diagnostic['independent_stage_oracle_executed'] is diagnostic['full_model_oracle_executed'] is False
    assert w['budget_debit']['charged_cpu_seconds']==108 and 6196+108==diagnostic['numerical_debit_with_prior']==6304
    assert failed['failed_scheduler_cpu_upper_ns']-failed['contained_worker_cpu_ns']==failed['complete_controller_upper_cpu_ns']
    for op,c in costs.items():
        assert c['scheduler_cpu_ns']+c['scheduler_quantum_ns']-c['contained_work_cpu_ns']==c['complete_controller_upper_cpu_ns']
    results=dict(schema='e19-scoped-diagnostic-v111',full_model_comparisons=0,full_model_transfer=False,speed_comparison=False,new_quality_evidence=False,
        matched_screen=dict(original_sources=4,tokens_per_record=128,retained_counts=[3,2],normalization=512,
            profiles=['distilgpt2','gpt2'],stage_counts=[24,48],both_preparations_complete=True,
            failed_job='16339',failed_operation='gpt2/reference_compressed-1',failure='certification_refusal',
            native_status=3,coordinate=359,subset_row=0,original_row_identity_saved=False,
            stage_inferred_from_completed_prefix_and_bound_target='block.0011.mlp_up',completed_stage_prefix=46,
            retained_sources_replayed=3,route_for_box_and_point='streamed',completed_requests=0,
            cancelled_unstarted_jobs=failed['cancelled_unstarted_jobs'],numerical_cpu_charged_seconds=6196,
            failed_request_cpu_charged_seconds=1879,failed_request_actual_worker_cpu_ns=failed['contained_worker_cpu_ns'],
            failed_request_scheduler_cpu_lower_ns=failed['failed_scheduler_cpu_lower_ns'],
            failed_request_scheduler_cpu_upper_ns=failed['failed_scheduler_cpu_upper_ns'],
            failed_request_complete_controller_upper_cpu_ns=failed['complete_controller_upper_cpu_ns'],
            old_receipts_modified=False,refusal_proves_wrong_model=False,refusal_proves_budget_impossibility=False),
        diagnostic=dict(job='16367',software_job='16366',software_checks=246,route='token',selected_stage='block.0011.mlp_up',
            rows=3072,columns=768,certified_codes=q['certified_codes'],packed_code_bytes=q['artifacts']['codes.bin']['bytes'],
            packed_code_sha256=q['artifacts']['codes.bin']['sha256'],retained_sources=3,normalization=512,
            source='original complete preparation lossless factors',original_target_and_grids=True,
            original_streamed_route_repeated=False,independent_stage_oracle_executed=False,full_model_oracle_executed=False,
            numerical_cpu_charged_seconds=108,actual_worker_cpu_ns=w['resource_usage']['total_cpu_ns'],
            complete_costs=costs,code_extent_checked=True),
        costs=dict(cumulative_numerical_charged_seconds=6304,original_numerical_ceiling=82840,
            conservative_next_software_carry_seconds=207,conservative_next_checks_controller_carry_seconds=48,
            conservative_next_numerical_controller_carry_seconds=79,overlapping_clocks_not_summed=True,
            old_unrelated_unknown_reservation_seconds=12602,preserved_separately=True))
    assert results['diagnostic']['packed_code_bytes']==1179648 and results['diagnostic']['rows']*results['diagnostic']['columns']==2359296
    result=dict(results=results,provenance=dict(schema='e19-input-commitments-v111',receipts={n:info(b) for n,b in raw.items()},
        original_receipts_retained_in_research_repository=True,typed_derivative_not_reexecution=True,
        original_failed_entry_sealed_cpu_field_zero=failed['failed_saved_entry_sealed_cpu_is_zero'],
        original_failed_host_accounting_null=failed['failed_saved_host_accounting_is_null'],
        actual_failed_seal_used_for_readonly_accounting=failed['reporting_partition_uses_actual_worker_seal'],
        diagnostic_program_sha256=diagnostic['program_sha256']))
    readme=b'''E19: failed matched screen and separate selected-stage diagnostic

The first GPT2 request refused certification in the streamed route, including
its exact-source fallback. Both preparations completed; no matched request did.
The46-stage prefix and fixed target identify the implicated stage by inference;
the traceback does not name it. Native status3 can denote an unresolved, invalid
or nonfinite arithmetic enclosure. It does not prove an exact tie, an incorrect
model or universal impossibility. Row0 indexes the selected subset; the original
output-row identity was not saved. Nineteen dependents were cancelled unstarted.

A distinct registered token-only stage diagnostic certified all2359296codes of
that stage from the original retained lossless factors. Actual source, target,
original grids, packed extent and worker/host/scheduler accounting were checked.
No independent fresh stage oracle or complete model was run. This is bounded
certification evidence under the trusted implementation, not a speed comparison,
full-model transfer or new quality result. Frozen limits and failed source remain.

results.json preserves scope and CPU partitions; provenance.json commits to the
actual source receipts. The diagnostic worker charges108seconds, bringing matched
numerical debit to6304of82840. Software and controllers are separate; nested clocks
must not be added. The older unrelated unknown12602-second debit is not erased.
Original V109 host preparation failed before registration and remains preserved.

This component supplies descriptive derivatives, not model/code binaries or a
numerical rerun. It contains no raw token bodies, corpus, credentials or runtime.
Hashes and job IDs remain potential linkage channels; anonymity is not guaranteed.
'''
    files={'results.json':enc(results),'provenance.json':enc(result['provenance']),'README.txt':readme}
    files['MANIFEST.json']=enc({n:info(b) for n,b in sorted(files.items())})
    folder.mkdir()
    for n,b in files.items():(folder/n).write_bytes(b)
    zip_payload(target,'diagnostic-evidence',files)
    report=dict(schema='diagnostic-evidence-build-v111',archive=info(target.read_bytes()),inputs=result['provenance']['receipts'],
        checked_actual_saved_values=True,empirical_execution=False,independent_stage_oracle=False,full_model_transfer=False)
    (R/'validation/v111_diagnostic_evidence.json').write_bytes(enc(report));print(json.dumps(report,sort_keys=True))

if __name__=='__main__':build()
