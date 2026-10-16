"""Check completed preparation/cache artifacts without promoting partial science.

This audit does not invoke calibration, infer losses, touch ledger locks, or
require unrelated workers to finish. The mutable ledger is captured twice;
completed debits must remain identical, while later reservations may advance.
"""
import gc
import os
from pathlib import Path
import resource
import sys
import time
from research_v54.campaign import ROOT,verify,new,require
from research_v54.postrun import (Inputs,registered_records,REPRESENTATIONS,model_matches_state,
    storage_matches_metadata,execution_matches_target,expected_artifacts,verify_kernel)
from research_v53.state import validate_state
from research_v53.service import gram_budget,trust_read
from src.run_store import canonical_json,digest,read_completed,strict_json
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes

COMPLETED=('prepare','cached')
PROGRAM='03a6181b0d32ad023706145fbde28f202ed5d137e95a4b16ecbd19686858465b'


def snapshot(directory,program):
    return read_budget_snapshot(directory/'budget',identity=dict(protocol_sha256=digest(canonical_json(program)),
        source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'feasibility':program['phase_cpu_seconds']})


def verify_completed(directory,program,inputs,ledger,*,version='v54'):
    completions={};receipts={};ph=digest(canonical_json(program))
    require(ledger['status']=='verified' and not any(ledger['over_cap'].values()),'Invalid or over-cap ledger')
    for trial in COMPLETED:
        root=directory/trial;tx=inputs.json(root/'transaction.json');plan=inputs.json(root/'plan.json')
        identity=inputs.json(root/'worker/identity.json');limits=identity['limits']
        require(identity['identity']==dict(campaign_sha256=ph,trial=trial) and identity['cwd']==str(ROOT)
            and identity['command']==[sys.executable,'-B','-m','research_'+version+'.worker',str(root/'plan.json')]
            and identity['phase_budget']==dict(binding_sha256=ledger['binding_sha256'],phase='feasibility',directory=str(directory/'budget')),
            'Worker identity or command differs')
        require(all(limits[k]==v for k,v in program['trials'][trial].items()) and limits['threads']==1
            and len(limits['affinity_cpus'])==1 and limits['address_space_bytes']==program['process_address_space_bytes']
            and limits['file_size_bytes']==program['file_size_bytes'],'Worker resource limits differ')
        sealed=read_completed(root/'worker',identity)
        require(sealed is not None and sealed['outcome']==tx['worker_outcome'] and sealed['outcome']['status']=='complete'
            and sealed['outcome']['returncode']==0,'Selected worker is incomplete')
        require(inputs.json(root/'worker/result.json')==sealed==inputs.json(root/'worker'/sealed['attempt']/'status.json'),
            'Final receipt differs')
        for name,entry in sealed['artifacts'].items():
            require(inputs.read(root/'worker'/sealed['attempt']/name,retain=False)==entry,'Sealed artifact differs')
        debit=sealed['budget_attempt_id']
        require(debit not in receipts and ledger['attempts'].get(debit)==sealed['budget_debit']
            and sealed['budget_debit']['state']=='settled'
            and sealed['budget_debit']['observed_cpu_ns']==sealed['resource_usage']['total_cpu_ns'], 'Completed CPU debit differs')
        require(tx['budget']['attempts'][debit]==sealed['budget_debit'],'Transaction debit differs')
        receipts[debit]=dict(trial=trial,debit=sealed['budget_debit'],transaction_elapsed_ns=tx.get('elapsed_ns'))
        require(plan==dict(trial=trial,program=str(directory/'program.json'),program_sha256=ph,
            output=str(root/'outputs'),slurm_job_id=tx['slurm_job_id']),'Worker plan differs')
        c=inputs.json(root/'outputs/completion.json')
        require(c['schema']=='complete-service-worker-'+version and c['trial']==trial and c['status']=='complete'
            and c['complete_model'] is True and c['program_sha256']==ph and c['source_sha256']==program['sources']
            and c['slurm_job_id']==plan['slurm_job_id'],'Completion identity differs')
        verify_kernel(c['shared_primal_kernel'])
        require(set(c['artifacts'])==expected_artifacts(trial),'Incomplete artifact inventory')
        for name,entry in c['artifacts'].items():
            require(entry==dict(file=name,**inputs.read(root/'outputs'/name,retain=False)),'Actual output artifact differs')
        completions[trial]=c
    return completions,receipts


def check_states(directory,program,completions,inputs,checkpoint_bytes,*,expected_stages=24,expected_codes=42_467_328):
    records=registered_records(program);budget=gram_budget(program['normalization']);prep=directory/'prepare/outputs'
    original_model=inputs.read(prep/'original-model.bin');target=None;originals={};original_source_map=None
    executions={trial:inputs.json(directory/trial/'outputs/execution-provenance.json') for trial in COMPLETED}
    for trial,e in executions.items():
        require(digest(canonical_json(e))==completions[trial]['execution_provenance_sha256'],'Execution commitment differs')
    require(executions['prepare']==executions['cached'],'Execution provenance differs')
    for rep in REPRESENTATIONS:
        blob=inputs.read(prep/(rep+'-original.bin'));trust=inputs.read(prep/(rep+'-trust.json'))
        view=validate_state(blob,expected_target=target,expected_records=records,
            gram_trust=trust_read(strict_json(trust)),gram_budget=budget)
        require(view.representation==rep,'Original representation differs')
        target=view.target if target is None else target
        require(target.original_tokens==program['normalization'],'Original normalization differs')
        extent=model_matches_state(view,original_model)
        require(extent['stages']==expected_stages and extent['code_count']==expected_codes,'Incomplete original model')
        size=storage_matches_metadata(completions['prepare']['preparation']['representations'][rep],blob,trust,checkpoint_bytes)
        originals[rep]=dict(**extent,**size,records=len(records),tokens=program['normalization'])
        if rep=='lossless':original_source_map=view.source_map()
        del blob,trust,view;gc.collect()
    require(completions['prepare']['code_count']==expected_codes,'Preparation code count differs')
    execution_matches_target(executions['prepare'],target)
    rows=completions['cached']['steps'];require(len(rows)==2,'Both cached successors required');steps=[]
    previous=original_source_map
    for index,row in enumerate(rows):
        step=index+1;after=program['retained_counts'][index];before=len(records) if index==0 else program['retained_counts'][index-1]
        expected=records[len(records)-after:];deleted=records[len(records)-before:len(records)-after]
        root=directory/'cached/outputs';blob=inputs.read(root/f'step-{step}-state.bin');trust=inputs.read(root/f'step-{step}-trust.json')
        view=validate_state(blob,expected_target=target,expected_records=expected,gram_trust=trust_read(strict_json(trust)),gram_budget=budget)
        require(view.representation=='lossless','Cached representation differs')
        current=view.source_map();require(all(previous.get(k)==v for k,v in current.items()),'Retained source descriptor changed')
        extent=model_matches_state(view,inputs.read(root/f'step-{step}-model.bin'))
        require(extent['stages']==expected_stages and extent['code_count']==expected_codes,'Incomplete cached model')
        require(row['step']==step and row['representation']=='lossless' and row['retained_ids']==[r.record_id for r in expected]
            and row['deleted_ids']==[r.record_id for r in deleted],'Cached membership metadata differs')
        size=storage_matches_metadata(row,blob,trust,checkpoint_bytes)
        steps.append(dict(step=step,**extent,**size,retained_records=len(expected),retained_tokens=sum(len(r.tokens) for r in expected),
            actual_export_matches_state=True,retained_descriptors_unchanged=True,oracle_comparison_performed=False))
        previous=current;del blob,trust,view;gc.collect()
    return dict(originals=originals,cached_steps=steps,fixed_target_sha256=digest(target.fixed_payload),
        full_campaign_verified=False,oracle_comparison_performed=False,quality_evaluation=False)


def audit(directory,output):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform=='linux','Bounded Linux Slurm audit required')
    # Read-only analysis allowance, separate from the immutable numerical ledger.
    resource.setrlimit(resource.RLIMIT_CPU,(1200,1201));resource.setrlimit(resource.RLIMIT_AS,(16*2**30,16*2**30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(64*2**20,64*2**20))
    directory,output=Path(directory).resolve(),Path(output).resolve();require(not output.exists(),'Fresh audit path required')
    wall,cpu=time.perf_counter_ns(),time.process_time_ns();inputs=Inputs();program=inputs.json(directory/'program.json')
    require(digest(canonical_json(program))==PROGRAM and verify(directory)==program,'Frozen V54 program differs')
    require(inputs.json(directory/'registration.json')['program_sha256']==PROGRAM,'Registration differs')
    first=snapshot(directory,program)
    completions,receipts=verify_completed(directory,program,inputs,first)
    from research_v38.bootstrap_target import CHECKPOINT_HASHES
    checkpoint_bytes=0
    for name,h in CHECKPOINT_HASHES.items():
        e=inputs.read(ROOT/'tmp/models/distilgpt2'/name,retain=False);require(e['sha256']==h,'Checkpoint changed');checkpoint_bytes+=e['bytes']
    require(checkpoint_bytes==program['shared_checkpoint_bytes'],'Checkpoint byte count differs')
    evidence=check_states(directory,program,completions,inputs,checkpoint_bytes)
    inputs.unchanged();last=snapshot(directory,program)
    require(last['status']=='verified' and not any(last['over_cap'].values()) and
        all(last['attempts'].get(k)==v['debit'] for k,v in receipts.items()),'Completed debits changed during audit')
    result=dict(schema='completed-prefix-artifact-audit-v57',status='verified_completed_prefix_only',program_sha256=PROGRAM,
        campaign=str(directory),completed_trials=list(COMPLETED),inputs=inputs.files,evidence=evidence,receipts=receipts,
        completed_cpu_seconds=sum(v['debit']['charged_cpu_seconds'] for v in receipts.values()),
        ledger_at_start=first,ledger_at_end=last,slurm_job_id=os.environ['SLURM_JOB_ID'],
        source_sha256={str(f.relative_to(ROOT)):digest(f.read_bytes()) for f in Path(__file__).parent.glob('*.py')},
        original_preparation_worker_ns=completions['prepare']['worker_elapsed_ns'],
        cached_request_ns=[row['request_elapsed_ns'] for row in completions['cached']['steps']],
        cached_neural_stage_record_pairs=[row['timing']['neural_stage_record_pairs'] for row in completions['cached']['steps']],
        audit_cpu_ns=time.process_time_ns()-cpu,audit_elapsed_ns=time.perf_counter_ns()-wall,
        analysis_outside_empirical_worker_ledger=True,full_campaign_verified=False,confirmation=False,acl_ready=False,
        scope='Actual completed preparation and cached successor artifacts, membership, source retention, common model bytes across prepared representations, and settled debits only. No fresh oracle comparison, reexecuted calibration, compressed service, quality or speedup claim.')
    new(output,result);print(canonical_json(dict(status=result['status'],completed_cpu_seconds=result['completed_cpu_seconds'],
        artifact_inputs=len(inputs.files),audit_cpu_seconds=result['audit_cpu_ns']/1e9)).decode());return result


if __name__=='__main__':audit(*sys.argv[1:])
