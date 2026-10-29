"""Read-only numerical artifact audit; no neural inference or certification."""
import argparse
from pathlib import Path
import time

from research_v45.campaign import read, sha, new, require, verify, budget
from research_v45.service import gram_budget, trust_read
from research_v43.state import compare_fresh, verify_successor
from src.run_store import canonical_json, digest


def audit(directory, output):
    start=time.perf_counter_ns()
    directory=Path(directory).resolve()
    program=verify(directory)
    results={}
    for trial in program['trials']:
        root=directory/trial
        transaction=read(root/'transaction.json')
        require(transaction['worker_outcome']['status']=='complete','Worker did not finish: '+trial)
        completion=read(root/'outputs/completion.json')
        require(completion['status']=='complete' and completion['complete_model'],'Incomplete model: '+trial)
        require(completion['program_sha256']==sha(directory/'program.json'),'Worker program changed')
        for name,entry in completion['artifacts'].items():
            path=root/'outputs'/name
            require(path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256'],'Artifact bytes changed: '+str(path))
        results[trial]=completion
    snapshot=budget(program).snapshot()
    require(all(v['state']=='settled' for v in snapshot['attempts'].values()),'Unsettled CPU reservation')
    require(snapshot['charged_cpu_seconds']['feasibility']<=program['phase_cpu_seconds'],'Phase CPU cap exceeded')
    prep=directory/'prepare/outputs'
    oracle=directory/'oracle/outputs'
    comparisons=[]
    timings={}
    g_budget=gram_budget(program['normalization'])
    for trial,representation in dict(cached='lossless',compressed='compressed40',hybrid='hybrid_gram',cold='lossless').items():
        root=directory/trial/'outputs'
        previous=(prep/(representation+'-original.bin')).read_bytes()
        previous_trust=trust_read(read(prep/(representation+'-trust.json')))
        for step in (1,2):
            current=(root/f'step-{step}-state.bin').read_bytes()
            current_trust=trust_read(read(root/f'step-{step}-trust.json'))
            fresh=(oracle/f'step-{step}-{representation}.bin').read_bytes()
            fresh_trust=trust_read(read(oracle/f'step-{step}-{representation}-trust.json'))
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
            actual_model=(root/f'step-{step}-model.bin').read_bytes()
            fresh_model=(oracle/f'step-{step}-model.bin').read_bytes()
            require(actual_model==fresh_model,'Complete model bytes differ: '+trial)
            require(len(actual_model)==21_233_664 and comparison['code_count']==42_467_328,
                'Complete DistilGPT2 code extent differs')
            comparisons.append(dict(trial=trial,step=step,**comparison,
                actual_model_bytes_equal=True,complete_model_sha256=digest(actual_model),
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
    result=dict(schema='complete-service-artifact-audit-v45',status='verified',
        campaign=str(directory),program_sha256=sha(directory/'program.json'),
        all_declared_artifacts_rehashed=True,comparisons=comparisons,timings=timings,ratios=ratios,
        preparation=results['prepare']['preparation'],
        preparation_worker_ns=results['prepare']['worker_elapsed_ns'],
        preparation_transaction_ns=read(directory/'prepare/transaction.json')['elapsed_ns'],
        oracle_worker_ns=results['oracle']['worker_elapsed_ns'],budget=snapshot,
        prior_failed_cpu_seconds=program['prior_failed_charge'],
        total_continuation_cpu_seconds=program['prior_failed_charge']+snapshot['charged_cpu_seconds']['feasibility'],
        shared_checkpoint_bytes=program['shared_checkpoint_bytes'],
        audit_history_bytes=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()),
        complete_model=True,successive_deletions=2,original_tokens=1664,retained_tokens=[1536,768],
        quality_evaluation=False,confirmation=False,population_claims=False,acl_ready=False,
        limitations=['One independent bounded-frame development root and one measured observation per request.',
            '128-token contexts; no evidence for long-context or population performance.',
            'Fixed nearest-anchor calibration target, not ordinary sequential GPTQ or pretraining unlearning.',
            'Hybrid control uses native Grams only for width768; no pure full-model Gram claim.',
            'Common immutable context reused across two requests; startup/admission overhead separately included in worker and transaction clocks.',
            'Runtime/source trust is a controlled execution assumption, not hostile-storage execution authentication.',
            'Audit copies retained; no physical erasure claim. Runtime installation/system storage excluded from model deployment total.',
            'Only observed two-step lifecycle; no extrapolated break-even or lifetime advantage.'],
        analysis_elapsed_ns=time.perf_counter_ns()-start,analysis_outside_empirical_worker_ledger=True)
    new(output,result)
    print(canonical_json(dict(status='verified',actual_comparisons=len(comparisons),output=str(output))).decode())
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('directory')
    parser.add_argument('output')
    args=parser.parse_args()
    audit(args.directory,args.output)
