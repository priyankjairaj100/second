"""Preparation receipt/cost metadata check; no model/state binary audit."""
import json,tarfile
from pathlib import Path
from validation.check_v67_snapshot import check,info,canonical,SHA


def verify(path):
    summary=check(path)
    with tarfile.open(path,'r:gz') as archive:
        files={m.name:archive.extractfile(m).read() for m in archive}
    def obj(name):
        value=json.loads(files[name]);assert canonical(value)==files[name];return value
    p=obj('program.json');completion=obj('prepare/outputs/completion.json')
    entry=obj('prepare-entry.json');transaction=obj('prepare/transaction.json')
    seal=obj('prepare/worker/result.json');identity=obj('prepare/worker/identity.json')
    assert seal['identity_sha256']==info(canonical(identity))['sha256']
    assert seal==obj('prepare/worker/'+seal['attempt']+'/status.json')
    assert seal['status']=='complete' and seal['outcome']['status']=='complete' and seal['outcome']['returncode']==0
    for name,e in seal['artifacts'].items():assert info(files['prepare/worker/'+seal['attempt']+'/'+name])==e
    assert seal['outcome']==transaction['worker_outcome']
    assert completion['status']=='complete' and completion['complete_model'] is True and completion['trial']=='prepare'
    assert completion['program_sha256']==entry['program_sha256']==SHA
    assert completion['slurm_job_id']==entry['job_id']==transaction['slurm_job_id']=='15262'
    assert entry['status']=='complete' and entry['error'] is None and entry['hostname']=='csis.mn1'
    assert entry['cpu_limits']==[600,16802] and entry['process_cpu_ns']<=601*10**9
    assert completion['source_files_sha256']==info(canonical(p['new_sources']))['sha256']
    assert completion['base_target_sha256']==p['inputs']['base_target']['sha256']
    assert completion['calibration_target_sha256']==p['inputs']['calibration_target']['sha256']
    usage=seal['resource_usage'];debit=seal['budget_debit'];ledger=obj('budget/ledger.json')
    assert usage['total_cpu_ns']==usage['user_cpu_ns']+usage['system_cpu_ns']==debit['observed_cpu_ns']
    assert debit['state']=='settled' and debit['reserved_cpu_seconds']==p['trials']['prepare']['cpu_seconds']+2
    assert debit['charged_cpu_seconds']==max(1,(usage['total_cpu_ns']+999999999)//10**9)
    assert not seal['budget_reservation_overrun']
    assert debit==ledger['attempts'][seal['budget_attempt_id']]==transaction['budget']['attempts'][seal['budget_attempt_id']]
    assert completion['worker_elapsed_ns']<=transaction['elapsed_ns']<=entry['elapsed_ns']
    assert entry['waited_child_cpu_ns']+2>=usage['total_cpu_ns']
    progress=[obj(n) for n in sorted(files) if n.startswith('prepare/outputs/progress-')]
    assert len([r for r in progress if r['phase']=='source_replayed'])==13
    stages=[r for r in progress if r['phase']=='stage_certified']
    assert len(stages)==24 and len({r['stage_id'] for r in stages})==24
    assert all(r.get('certificate_refusal') is None and r.get('fallback') is False for r in stages)
    assert summary['jobs']['15262']['state']=='COMPLETED' and summary['jobs']['15262']['exit_code']=='0:0'
    return dict(status='verified_preparation_receipt_metadata',captured_at_utc=summary['captured_at_utc'],
        archive=summary['archive'],job=summary['jobs']['15262'],program_sha256=SHA,
        replayed_sources=13,stage_certificates=24,worker_process_and_waited_descendant_cpu_ns=usage['total_cpu_ns'],
        worker_charged_cpu_seconds=debit['charged_cpu_seconds'],controller_own_cpu_ns=entry['process_cpu_ns'],
        controller_all_waited_children_cpu_ns=entry['waited_child_cpu_ns'],
        worker_maximum_rss_kib=usage['max_rss_kib'],transaction_elapsed_ns=transaction['elapsed_ns'],
        declared_artifacts=completion['artifacts'],actual_model_state_bytes_checked=False,
        fresh_oracle_comparison_verified=False,complete_campaign_costs_verified=False,
        later_reserved_attempts_preserved=sum(r['state']=='reserved' for r in ledger['attempts'].values()),
        numerical_result_verified=False)


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[1])),sort_keys=True,indent=2))
