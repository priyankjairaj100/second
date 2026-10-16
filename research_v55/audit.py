"""Read-only V55 artifact, loss-summary and sealed CPU audit; no inference."""
import os
from pathlib import Path
import sys
import time
from research_v55.campaign import ROOT,verify,require,new,bound
from research_v55.diagnostic import reconstruct_fixed,reconstruct_sequential,check_result
from research_v54.postrun import Inputs,bind_ledger_snapshot,verify_kernel
from research_v42.resource_plan import BoundTarget
from src.experiment_inventory import source_hashes
from src.phase_budget import read_budget_snapshot
from src.run_store import canonical_json,digest,read_completed

ARTIFACTS={'sequential-target.json','fixed-target.json','execution-provenance.json','historical-parity.json',
    'sequential-model.bin','sequential-model-metadata.json','sequential-diagnostics.json'}


def check_prefix(diagnostics,stages,target_sha256):
    require(diagnostics['schema']=='dispatched-sequential-calibration-v55' and
        diagnostics['target_sha256']==target_sha256 and diagnostics['records']==6 and
        diagnostics['retained_tokens']==768 and diagnostics['neural_stage_record_pairs']==144 and
        diagnostics['prior_model_access'] is False and diagnostics['prior_factor_access'] is False,
        'Sequential execution extent differs')
    require(len(diagnostics['stages'])==len(diagnostics['point_admission'])==len(stages)==24,
        'Sequential diagnostics incomplete')
    from research_v43.dispatcher import ResourcePolicy
    policy=ResourcePolicy()
    require(all(a['admitted'] is True and a['policy']==policy.__dict__ for a in diagnostics['point_admission'])
        and sum(a['work_units'] for a in diagnostics['point_admission'])<=policy.max_request_work_units,
        'Sequential resource admissions incomplete')
    for index,(row,stage,admission) in enumerate(zip(diagnostics['stages'],stages,diagnostics['point_admission'])):
        require(row['stage_id']==admission['stage_id']==stage.stage_id and row['feature_tokens']==768 and
            row['input_width']==stage.columns and row['output_rows']==stage.rows and
            row['route']==admission['selected_route'] and
            row['installed_parent_stage_id']==(stages[index-1].stage_id if index else None) and
            row['installed_parent_packed_sha256']==(digest(stages[index-1].packed_indices) if index else None),
            'Sequential calibrated prefix binding differs')


def audit(directory,output):
    require(os.environ.get('SLURM_JOB_ID'),'Audit requires a bounded Linux Slurm allocation')
    directory,output=Path(directory).resolve(),Path(output).resolve()
    require(not output.exists(),'Fresh audit path required')
    tick,cpu=time.perf_counter_ns(),time.process_time_ns();inputs=Inputs()
    p=inputs.json(directory/'program.json');ph=digest(canonical_json(p))
    require(verify(directory)==p and inputs.json(directory/'registration.json')['program_sha256']==ph,
        'Frozen registration differs')
    for entry in p['inputs'].values():
        actual=inputs.read(bound(entry),retain=False)
        require(actual==dict(bytes=entry['bytes'],sha256=entry['sha256']),'Bound audit input differs')
    snapshot=read_budget_snapshot(directory/'budget',identity=dict(protocol_sha256=ph,source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'development':p['phase_cpu_seconds']})
    require(snapshot['status']=='verified' and not snapshot['reserved_unknown_attempts'] and
        not any(snapshot['over_cap'].values()),'CPU ledger unsettled or over cap')
    bind_ledger_snapshot(directory,snapshot,inputs)
    root=directory/'quality';out=root/'outputs'
    identity=inputs.json(root/'worker/identity.json');tx=inputs.json(root/'transaction.json');plan=inputs.json(root/'plan.json')
    require(identity['identity']==dict(program_sha256=ph) and identity['cwd']==str(ROOT) and
        identity['command']==[sys.executable,'-B','-m','research_v55.worker',str(root/'plan.json')] and
        identity['phase_budget']==dict(directory=str(directory/'budget'),phase='development',binding_sha256=snapshot['binding_sha256']),
        'Sealed command or phase binding differs')
    limits=identity['limits']
    require(limits['cpu_seconds']==p['worker_cpu_seconds'] and limits['wall_seconds']==p['worker_wall_seconds'] and
        limits['address_space_bytes']==p['process_address_space_bytes'] and limits['file_size_bytes']==p['file_size_bytes'] and
        limits['threads']==1 and len(limits['affinity_cpus'])==1,'Worker limits differ')
    sealed=read_completed(root/'worker',identity)
    require(sealed is not None and sealed['outcome']==tx['worker_outcome'] and
        sealed['outcome']['status']=='complete' and sealed['outcome']['returncode']==0,'Worker did not complete')
    require(inputs.json(root/'worker/result.json')==sealed==inputs.json(root/'worker'/sealed['attempt']/'status.json'),
        'Terminal seal differs')
    for name,entry in sealed['artifacts'].items():
        require(inputs.read(root/'worker'/sealed['attempt']/name,retain=False)==entry,'Sealed controller artifact differs')
    require(snapshot['attempts']=={sealed['budget_attempt_id']:sealed['budget_debit']} and
        sealed['budget_debit']['observed_cpu_ns']==sealed['resource_usage']['total_cpu_ns'], 'CPU debit differs')
    require(all(tx['budget'][k]==snapshot[k] for k in tx['budget']), 'Transaction ledger differs')
    require(plan==dict(program=str(directory/'program.json'),program_sha256=ph,output=str(out),slurm_job_id=tx['slurm_job_id']),
        'Worker plan differs')
    c=inputs.json(out/'completion.json')
    require(c['schema']=='exposed-quality-worker-v55' and c['program_sha256']==ph and c['slurm_job_id']==plan['slurm_job_id']
        and c['original_normalization']==1664 and c['retained_calibration_tokens']==768 and c['code_count']==42_467_328
        and c['fixed_model_sha256']==p['inputs']['fixed_model']['sha256'] and c['confirmation'] is False
        and c['acl_ready'] is False and c['certified_inference'] is False,'Worker extent or scope differs')
    verify_kernel(c['shared_primal_kernel'])
    require(set(c['artifacts'])==ARTIFACTS,'Incomplete quality artifact inventory')
    for name,entry in c['artifacts'].items():
        require(entry==dict(file=name,**inputs.read(out/name,retain=False)),'Quality artifact bytes differ')
    history=inputs.json(bound(p['inputs']['historical_losses']))
    summary=check_result(c,history,inputs.json(out/'historical-parity.json'))
    target=BoundTarget(inputs.read(out/'sequential-target.json'),inputs.read(out/'fixed-target.json'))
    require(c['fixed_target_sha256']==digest(target.fixed_payload) and c['sequential_target_sha256']==digest(target.anchor_payload),
        'Target identity differs')
    old=inputs.json(bound(p['inputs']['v54_program']))
    fixed=reconstruct_fixed(inputs.read(bound(p['inputs']['fixed_state'])),inputs.read(bound(p['inputs']['fixed_model'])),
        bound_target=target,records=p['retained_records'],provenance=old['record_provenance'])
    sequential=reconstruct_sequential(inputs.read(out/'sequential-model.bin'),inputs.json(out/'sequential-model-metadata.json'),
        target_sha256=c['sequential_target_sha256'],fixed=fixed)
    check_prefix(inputs.json(out/'sequential-diagnostics.json'),sequential,c['sequential_target_sha256'])
    require(c['excluded_from_future_confirmation_ids']==inputs.json(bound(p['inputs']['all_exclusions']))['excluded_from_future_confirmation_ids'],
        'Quality exclusion registry differs')
    inputs.unchanged()
    result=dict(schema='exposed-quality-artifact-audit-v55',status='verified',campaign=str(directory),program_sha256=ph,
        inputs=inputs.files,summary=summary,development_guards_pass=summary['development_guards_pass'],
        actual_model_codes_reconstructed=42_467_328,complete_stages=24,sealed_cpu_receipt_verified=True,budget=snapshot,
        historical_control_parity=c['historical_parity'],source_sha256=p['sources'],
        slurm_job_id=os.environ['SLURM_JOB_ID'],analysis_cpu_ns=time.process_time_ns()-cpu,
        analysis_elapsed_ns=time.perf_counter_ns()-tick,analysis_outside_empirical_worker_ledger=True,
        confirmation=False,acl_ready=False,
        scope='Actual fixed/sequential packed arrays and row grids, all 32 losses, descriptive summaries, historical parity and sealed CPU debit verified. Trusted execution assumed; no independent inference or quantization rerun.')
    new(output,result)
    print(canonical_json(dict(status='verified',development_guards_pass=result['development_guards_pass'],output=str(output))).decode())
    return result


if __name__=='__main__':audit(*sys.argv[1:])
