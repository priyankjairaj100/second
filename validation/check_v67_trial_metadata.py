"""Completed comparison receipt/debit metadata only; never reads model/state bytes."""
import ast,json,tarfile,sys
from pathlib import Path
from validation.check_v67_snapshot import check,info,canonical,SHA


def verify(path,trial):
    summary=check(path)
    with tarfile.open(path,'r:gz') as archive:files={m.name:archive.extractfile(m).read() for m in archive}
    def obj(name):
        value=json.loads(files[name]);assert canonical(value)==files[name];return value
    p=obj('program.json');arm,step=trial.rsplit('-',1)
    assert arm in {'hybrid','compressed','cold','cached','modern'} and step in {'1','2'} and trial in p['trials']
    job=next(r['job_id'] for r in obj('chain-submission.json')['jobs'] if r['name']==trial)
    c=obj(trial+'/outputs/completion.json');e=obj(trial+'-entry.json');t=obj(trial+'/transaction.json')
    seal=obj(trial+'/worker/result.json');identity=obj(trial+'/worker/identity.json')
    assert seal['identity_sha256']==info(canonical(identity))['sha256']
    assert seal==obj(trial+'/worker/'+seal['attempt']+'/status.json')
    assert seal['status']=='complete' and seal['outcome']['status']=='complete' and seal['outcome']['returncode']==0
    for name,h in seal['artifacts'].items():assert info(files[trial+'/worker/'+seal['attempt']+'/'+name])==h
    assert seal['outcome']==t['worker_outcome']
    assert identity['identity']==dict(campaign_sha256=SHA,trial=trial)
    assert c['schema']=='disjoint-complete-service-worker-v67' and c['trial']==trial
    assert c['status']=='complete' and c['complete_model'] is True and c['quality_evaluation'] is False
    assert c['program_sha256']==e['program_sha256']==SHA and c['slurm_job_id']==e['job_id']==t['slurm_job_id']==job
    assert e['status']=='complete' and e['error'] is None and e['hostname']=='csis.mn1'
    assert e['cpu_limits']==[600,16802] and e['process_cpu_ns']<=601*10**9
    assert c['source_files_sha256']==info(canonical(p['new_sources']))['sha256']
    for name in ['base_target','calibration_target']:
        assert c[name+'_sha256']==p['inputs'][name]['sha256']
    # Service target is committed in the frozen config, not a separate input leaf.
    constants={node.targets[0].id:ast.literal_eval(node.value)
        for node in ast.parse(files['research_v67/config.py']).body
        if isinstance(node,ast.Assign) and len(node.targets)==1
        and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='SERVICE_TARGET'}
    assert c['service_target_sha256']==constants['SERVICE_TARGET']
    for name in ['cpu_seconds','wall_seconds']:assert identity['limits'][name]==p['trials'][trial][name]
    assert seal['limits']==identity['limits']
    usage=seal['resource_usage'];debit=seal['budget_debit'];ledger=obj('budget/ledger.json')
    assert usage['total_cpu_ns']==usage['user_cpu_ns']+usage['system_cpu_ns']==debit['observed_cpu_ns']
    assert debit['state']=='settled' and debit['reserved_cpu_seconds']==p['trials'][trial]['cpu_seconds']+2
    assert debit['charged_cpu_seconds']==max(1,(usage['total_cpu_ns']+999999999)//10**9)
    assert not seal['budget_reservation_overrun'] and debit['charged_cpu_seconds']<=debit['reserved_cpu_seconds']
    assert debit==ledger['attempts'][seal['budget_attempt_id']]==t['budget']['attempts'][seal['budget_attempt_id']]
    assert c['worker_elapsed_ns']<=t['elapsed_ns']<=e['elapsed_ns']
    assert e['waited_child_cpu_ns']+2>=usage['total_cpu_ns'] and usage['max_rss_kib']*1024<=16*2**30
    progress=[obj(n) for n in sorted(files) if n.startswith(trial+'/outputs/progress-')]
    stages=[r for r in progress if r['phase']=='stage_certified'];request=c['request']
    assert len(stages)==24 and len({r['stage_id'] for r in stages})==24 and request['code_count']==42467328
    assert len(request['retained_ids'])==p['retained_counts'][int(step)-1]
    assert request['arm']==arm and len(set(request['retained_ids']))==len(request['retained_ids'])
    assert not set(request['deleted_ids'])&set(request['retained_ids'])
    timing=request['timing']['stages'];assert len(timing)==24
    assert [r['stage_id'] for r in timing]==[r['stage_id'] for r in stages]
    for a,b in zip(stages,timing):
        assert all(a[k]==b[k] for k in ['stage_id','code_sha256','route','fallback','certificate_refusal'])
    for name in ['model','state','trust']:assert request[name]==c['artifacts'][request[name]['file']]
    assert c['artifacts']['model.bin']['bytes']==p['model_bytes']==21233664
    solver_rows=[r['solver'].get('diagnostics',{}).get('rows',r['solver']) for r in timing]
    assert summary['jobs'][job]['state']=='COMPLETED' and summary['jobs'][job]['exit_code']=='0:0'
    return dict(status='verified_completed_comparison_receipt_metadata',trial=trial,job_id=job,
        captured_at_utc=summary['captured_at_utc'],archive=summary['archive'],job=summary['jobs'][job],
        program_sha256=SHA,stage_certificates=len(stages),refused_stages=sum(r['certificate_refusal'] is not None for r in stages),
        stage_level_fallback_flags=sum(r['fallback'] is True for r in stages),
        numerical_solver_fallback_rows=sum(r.get('fallback_rows',0) for r in solver_rows),
        numerical_solver_fallback_attempted_decisions=sum(r.get('fallback_attempted_decisions',0) for r in solver_rows),
        numerical_solver_fallback_certified_decisions=sum(r.get('fallback_certified_decisions',0) for r in solver_rows),
        worker_process_and_waited_descendant_cpu_ns=usage['total_cpu_ns'],worker_charged_cpu_seconds=debit['charged_cpu_seconds'],
        controller_own_cpu_ns=e['process_cpu_ns'],controller_all_waited_children_cpu_ns=e['waited_child_cpu_ns'],
        worker_maximum_rss_kib=usage['max_rss_kib'],transaction_elapsed_ns=t['elapsed_ns'],
        declared_artifacts=c['artifacts'],actual_model_state_bytes_checked=False,fresh_oracle_comparison_verified=False,
        complete_campaign_costs_verified=False,retained_membership_independently_rebuilt=False,
        later_reserved_attempts_preserved=sum(r['state']=='reserved' for r in ledger['attempts'].values()),
        numerical_result_verified=False)


if __name__=='__main__':
    assert not sys.flags.optimize
    print(json.dumps(verify(Path(sys.argv[1]),sys.argv[2]),sort_keys=True,indent=2))
