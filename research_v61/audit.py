"""Read-only numerical artifact audit; no neural inference or certification."""
import argparse
import os
from pathlib import Path
import sys
import time

from research_v61.campaign import read, sha, new, require, verify, bound
from research_v61.service import gram_budget, trust_read
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes
from research_v61.campaign import ROOT
from research_v61.state import validate_state, verify_successor
from research_v61.postrun import Inputs, bind_ledger_snapshot, verify_worker_receipts, execution_matches_target
from src.run_store import canonical_json, digest, strict_json


def audit(directory, output):
    start,cpu_start=time.perf_counter_ns(),time.process_time_ns()
    require(os.environ.get('SLURM_JOB_ID') and sys.platform == 'linux', 'Bounded Linux Slurm audit required')
    directory=Path(directory).resolve()
    output=Path(output).absolute();require(not output.exists() and not output.is_symlink(), 'Fresh primary audit path required')
    program=verify(directory)
    inputs=Inputs()
    require(inputs.json(directory/'program.json') == program and inputs.json(directory/'registration.json') ==
        dict(program_sha256=digest(canonical_json(program))), 'Primary audit registration binding differs')
    for entry in program['inputs'].values():
        require(inputs.read(bound(entry),retain=False) == {key:entry[key] for key in ('bytes','sha256')}, 'Bound campaign input differs')
    for name,expected in program['sources'].items():
        require(inputs.read(ROOT/name,retain=False)['sha256'] == expected, 'Bound campaign source differs')
    snapshot=read_budget_snapshot(directory/'budget',identity=dict(protocol_sha256=sha(directory/'program.json'),source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'feasibility':program['phase_cpu_seconds']})
    require(snapshot['status'] == 'verified' and not snapshot['reserved_unknown_attempts']
        and not snapshot['reservation_overrun_attempts'] and all(v['state']=='settled' for v in snapshot['attempts'].values()),'Unsettled CPU reservation')
    require(snapshot['charged_cpu_seconds']['feasibility']<=program['phase_cpu_seconds'],'Phase CPU cap exceeded')
    bind_ledger_snapshot(directory,snapshot,inputs)
    results=verify_worker_receipts(directory,program,inputs,snapshot)
    prep=directory/'prepare/outputs'
    oracle=directory/'oracle/outputs'
    comparisons=[]
    timings={}
    g_budget=gram_budget(program['normalization'])
    v59_model=inputs.read(bound(program['inputs']['v59_candidate_model']))
    v59_calibration=inputs.read(bound(program['inputs']['v59_candidate_target']))
    v59_base=inputs.read(bound(program['inputs']['v59_base_target']))
    for trial,representation in dict(cached='lossless',compressed='compressed48',hybrid='hybrid_gram',cold='lossless').items():
        root=directory/trial/'outputs'
        previous=inputs.read(prep/(representation+'-original.bin'))
        previous_trust=trust_read(inputs.json(prep/(representation+'-trust.json')))
        initial=validate_state(previous,gram_trust=previous_trust,gram_budget=g_budget)
        require(initial.target.anchor_payload == v59_base
            and canonical_json(strict_json(initial.target.fixed_payload)['calibration_target']) == v59_calibration,
            'Prepared service target does not wrap exact V59 teacher target')
        execution_matches_target(inputs.json(prep/'execution-provenance.json'),initial.target)
        del initial
        for step in (1,2):
            current=inputs.read(root/f'step-{step}-state.bin')
            current_trust=trust_read(inputs.json(root/f'step-{step}-trust.json'))
            fresh=inputs.read(oracle/f'step-{step}-{representation}.bin')
            fresh_trust=trust_read(inputs.json(oracle/f'step-{step}-{representation}-trust.json'))
            oracle_step=results['oracle']['steps'][step-1]
            require(oracle_step['independent_retained_token_traversal'] and oracle_step['prior_state_read'] is False,
                'Fresh oracle source route not witnessed')
            require(oracle_step['timing']['neural_stage_record_pairs']==24*program['retained_counts'][step-1],'Oracle source extent differs')
            before_count=program['record_count'] if step==1 else program['retained_counts'][step-2]
            after_count=program['retained_counts'][step-1]
            deleted=program['deletion_order'][program['record_count']-before_count:program['record_count']-after_count]
            comparison=verify_successor(previous,current,fresh,deleted,
                previous_gram_trust=previous_trust,candidate_gram_trust=current_trust,
                fresh_gram_trust=fresh_trust,gram_budget=g_budget)
            actual_model=inputs.read(root/f'step-{step}-model.bin')
            fresh_model=inputs.read(oracle/f'step-{step}-model.bin')
            require(actual_model==fresh_model,'Complete model bytes differ: '+trial)
            if step == 2:
                require(actual_model == v59_model, 'Final-six actual model differs from frozen V59 candidate: '+trial)
            require(len(actual_model)==21_233_664 and comparison['code_count']==42_467_328,
                'Complete DistilGPT2 code extent differs')
            comparisons.append(dict(trial=trial,step=step,**comparison,
                actual_model_bytes_equal=True,complete_model_sha256=digest(actual_model),
                v59_quality_anchor_actual_bytes_equal=True if step == 2 else None,
                independent_fresh_source_execution_witnessed=True))
            previous,previous_trust=current,current_trust
        measured=results[trial]
        preparation=results['prepare']['preparation']
        common=(results['prepare']['context_elapsed_ns']+preparation['common_source_ns']+
            preparation['common_original_model_ns']+preparation['common_disposal_ns'])
        own=preparation['representations'][representation]['representation_elapsed_ns']
        requests=sum(row['request_elapsed_ns'] for row in measured['steps'])
        transaction=read(directory/trial/'transaction.json')
        timings[trial]=dict(representation=representation,context_elapsed_ns=measured['context_elapsed_ns'],
            request_elapsed_ns=[row['request_elapsed_ns'] for row in measured['steps']],
            worker_elapsed_ns=measured['worker_elapsed_ns'],transaction_elapsed_ns=transaction['elapsed_ns'],
            worker_outside_request_ns=measured['worker_elapsed_ns']-requests,
            attributed_preparation_ns=common+own,
            attributed_two_deletion_lifetime_ns=common+own+transaction['elapsed_ns'],
            lifetime_scope='Observed two-request path with attributed common+representation preparation and measured complete request-worker transaction. Shared preparation admission/final receipt overhead reported separately.',
            live_state_bytes=[row['state_bytes']+row['trust_bytes'] for row in measured['steps']],
            complete_deployment_bytes=[row['complete_deployment_bytes'] for row in measured['steps']],
            max_rss_kib=measured['max_rss_kib'],
            replay_neural_stage_record_pairs=[row['timing']['neural_stage_record_pairs'] for row in measured['steps']],
            fallback_stages=[[s['stage_id'] for s in row['timing']['stages'] if s['fallback']] for row in measured['steps']])
    ratios={}
    for control in ('cached','hybrid','cold'):
        a,b=timings['compressed'],timings[control]
        ratios[control]=dict(compressed_over_control_request_time=[x/y for x,y in zip(a['request_elapsed_ns'],b['request_elapsed_ns'])],
            compressed_live_state_saving=[1-x/y for x,y in zip(a['live_state_bytes'],b['live_state_bytes'])],
            compressed_deployment_saving=[1-x/y for x,y in zip(a['complete_deployment_bytes'],b['complete_deployment_bytes'])],
            compressed_over_control_observed_lifetime=a['attributed_two_deletion_lifetime_ns']/b['attributed_two_deletion_lifetime_ns'])
    inputs.unchanged()
    result=dict(schema='complete-full-precision-service-artifact-audit-v61',status='verified',
        campaign=str(directory),program_sha256=sha(directory/'program.json'),
        all_declared_artifacts_rehashed=True,comparisons=comparisons,timings=timings,ratios=ratios,
        preparation=results['prepare']['preparation'],
        preparation_worker_ns=results['prepare']['worker_elapsed_ns'],
        preparation_transaction_ns=read(directory/'prepare/transaction.json')['elapsed_ns'],
        oracle_worker_ns=results['oracle']['worker_elapsed_ns'],budget=snapshot,
        fresh_campaign_cpu_seconds=snapshot['charged_cpu_seconds']['feasibility'],allowance_scope=program['allowance_scope'],
        calibration_target_sha256=digest(v59_calibration),v59_final_model_sha256=digest(v59_model),
        all_final_six_models_equal_actual_v59_candidate=True,
        shared_checkpoint_bytes=program['shared_checkpoint_bytes'],
        audit_history_bytes=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()),
        complete_model=True,successive_deletions=2,original_tokens=1664,retained_tokens=[1536,768],
        quality_evaluation=False,confirmation=False,population_claims=False,acl_ready=False,
        limitations=['One adaptively reused bounded-frame development root and one measured observation per request.',
            '128-token contexts; no evidence for long-context or population performance.',
            'Fixed full-precision teacher target, not ordinary sequential GPTQ or pretraining unlearning.',
            'Final-six quality is linked by actual model-byte equality to the exposed V59 screen; no quality rerun or new confirmation.',
            'Hybrid control uses native Grams only for width768; no pure full-model Gram claim.',
            'Common immutable context reused across two requests; startup/admission overhead separately included in worker and transaction clocks.',
            'Runtime/source trust is a controlled execution assumption, not hostile-storage execution authentication.',
            'Audit copies retained; no physical erasure claim. Runtime installation/system storage excluded from model deployment total.',
            'Only observed two-step lifecycle; no extrapolated break-even or lifetime advantage.'],
        source_sha256=program['sources'],runtime=program['runtime'],inputs=inputs.files,slurm_job_id=os.environ['SLURM_JOB_ID'],
        analysis_elapsed_ns=time.perf_counter_ns()-start,analysis_cpu_ns=time.process_time_ns()-cpu_start,
        analysis_outside_empirical_worker_ledger=True)
    new(output,result)
    print(canonical_json(dict(status='verified',actual_comparisons=len(comparisons),output=str(output))).decode())
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('directory')
    parser.add_argument('output')
    args=parser.parse_args()
    audit(args.directory,args.output)
