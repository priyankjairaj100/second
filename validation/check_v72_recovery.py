"""Reconcile the failed original closure and separately completed recovery."""
from pathlib import Path
import json,hashlib,sys,tarfile,tempfile
from validation.check_v71_campaign_metadata import load,check as check_old
from research_v71 import cost_accounting as costs,campaign
from src.phase_budget import read_budget_snapshot
from research_v72.recover_accounting import failed_closure
R=Path(__file__).resolve().parents[1]
REG72='ec6b5a295667cf9b305f7dc2a0a8a7ee14546c5395f5733c9b9ea8a36c4e9df6'
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def check(old,files):
    original=check_old(old)
    assert original['status']=='failed_or_cancelled_campaign_preserved'
    assert original['job_states']['closure']=='FAILED' and all(original['job_states'][n]=='COMPLETED' for n in campaign.ORDER)
    assert original['actual_completed_worker_seals_checked_locally']==8 and not original['active_worker_reservations']
    collection=json.loads(files['collection.json']);p=json.loads(files['program.json']);receipt=json.loads(files['receipt.json'])
    assert files['program.json']==(R/'handoff/registration_v72_accounting.json').read_bytes() and info(files['program.json'])['sha256']==REG72
    assert collection['files']=={n:info(b) for n,b in files.items() if n!='collection.json'}
    for name,e in p['new_sources'].items():
        relative=str(Path(name).relative_to(p['directory']));assert info(files[relative])==e
        assert files[relative]==(R/relative).read_bytes()
    for role,name in [('old_registration','program.json'),('ledger','budget/ledger.json'),('failed_receipt','closure/receipt.json'),('terminal_completion','terminal/outputs/completion.json')]:
        assert info(old[name])=={k:p['inputs'][role][k] for k in ['bytes','sha256']}
    assert info(files['inputs/original-scheduler.txt'])=={k:p['inputs']['scheduler'][k] for k in ['bytes','sha256']}
    assert files['inputs/original-scheduler.txt'].decode().strip()==json.loads(old['collection.json'])['accounting']
    binding=json.loads(files['job-binding.json']);assert binding==dict(job_id='15421',registration_sha256=REG72,submission_state='held-before-release')
    assert receipt['registration_sha256']==REG72 and receipt['job_id']=='15421' and receipt['status']=='complete' and receipt['error'] is None
    assert receipt['original_campaign_successful'] is False and receipt['original_closure_retried'] is False and receipt['model_or_likelihood_execution'] is False
    row=costs.scheduler_rows(collection['accounting'],{'recovery':'15421'})['recovery']
    assert row['state']=='COMPLETED' and row['exit_code']=='0:0'
    for k in ['process_cpu_ns','waited_child_cpu_ns','elapsed_ns','max_rss_kib']:costs.integer(receipt[k],k)
    total=receipt['process_cpu_ns']+receipt['waited_child_cpu_ns']
    assert total<=602*10**9 and total<=row['total_cpu_ns']+row['reporting_quantum_ns']
    assert row['total_cpu_ns']<=602*10**9 and row['elapsed_seconds']<=1200
    assert receipt['elapsed_ns']<=(row['elapsed_seconds']+1)*10**9 and receipt['max_rss_kib']*1024<=4*2**30
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp).resolve()
        for name,b in old.items():
            if name.startswith('budget/'):
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
        ledger=json.loads(old['budget/ledger.json'])
        snapshot=read_budget_snapshot(root/'budget',identity=ledger['binding']['identity'],phase_cpu_seconds={'quality':39616},max_attempts=8)
        accounting=costs.complete(original['completed_phase_costs'],snapshot)
    result=receipt['result'];assert result['accounting']==accounting and result['ledger']==info(old['budget/ledger.json'])
    assert result['phases']=={n:info(old[n+'/outputs/completion.json']) for n in campaign.ORDER}
    terminal=json.loads(old['terminal/outputs/completion.json'])['result'];loss=terminal['loss_audit']
    assert terminal['status']=='verified_actual_artifacts' and terminal['sequential_actual_saved_codes_reaudited'] is True
    assert terminal['actual_checkpoint_parameter_audit']['actual_checkpoint_reference_compared'] is True
    assert loss['status']=='verified' and loss['actual_loss_files_compared']==1920 and loss['statistics_recomputed'] is True
    assert loss['actual_cpu_reference_audit']['actual_loss_files_compared']==24
    assert type(terminal['quality_guard_pass']) is bool and terminal['quality_guard_pass']==loss['all_endpoint_gates_pass']==result['quality_guard_pass']
    assert result['actual_artifacts_verified'] is True and result['actual_original_outputs_rehashed'] is True
    failure_raw='\n'.join(line for line in json.loads(old['collection.json'])['accounting'].splitlines() if line.split('|')[0].split('.')[0]=='15413')
    failure=failed_closure(json.loads(old['closure/receipt.json']),costs.scheduler_rows(failure_raw,{'failed':'15413'})['failed'])
    assert result['original_failure']==failure
    old_total=accounting['scheduler_cpu_ns']+failure['scheduler']['total_cpu_ns']
    assert result['original_nine_allocation_scheduler_cpu_ns']==old_total and result['original_closure_successful'] is False
    return dict(schema='separate-v72-accounting-recovery-review',status='verified_separate_accounting_recovery',
        observed_at_utc=collection['captured_at_utc'],recovery_job='15421',original_closure_job='15413',
        original_campaign_successful=False,original_failed_closure_preserved=True,
        recovered_quality_evidence_verified=True,quality_guard_pass=terminal['quality_guard_pass'],
        numerical_worker_charged_cpu_seconds=accounting['worker_charged_cpu_seconds'],
        controller_charged_cpu_seconds=accounting['controller_charged_cpu_seconds'],
        original_eight_allocation_scheduler_cpu_ns=accounting['scheduler_cpu_ns'],
        failed_closure_scheduler_cpu_ns=failure['scheduler']['total_cpu_ns'],
        recovery_scheduler_cpu_ns=row['total_cpu_ns'],combined_scheduler_cpu_ns=old_total+row['total_cpu_ns'],
        recovery_process_and_children_cpu_ns=total,recovery_charged_cpu_seconds=max(1,(total+999999999)//10**9),
        original_allowance_cpu_seconds=44726,separate_recovery_allowance_cpu_seconds=602,
        registered_numerical_sources_changed=False,independent_neural_replication=False,
        scope='Original eight actual artifact/audit phases plus separate accounting recovery; original closure failure and cost retained. Local metadata review does not repeat model or loss execution.')
def main():
    old_path=R/'campaigns'/sys.argv[1];new_path=R/'campaigns'/sys.argv[2]
    result=check(load(old_path),load(new_path));result.update(original_archive=info(old_path.read_bytes()),recovery_archive=info(new_path.read_bytes()))
    with (R/'validation'/sys.argv[3]).open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
