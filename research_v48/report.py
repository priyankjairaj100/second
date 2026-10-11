"""Read copied evidence and refuse promotion of missing or inconsistent results.

This checks existing audited evidence and reported arithmetic. It does not
repeat model inference or replace the two frozen actual-payload auditors.
"""
import argparse
import hashlib
from pathlib import Path
from src.run_store import canonical_json,strict_json,read_completed
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes

PROFILES={
    'v45':dict(program='02c7f6cfc0240bc34f2a5faec05dfb5392b81d12e5ac4cd95279167ef99c6d50',
        original=1664,retained=[1536,768],records=[12,6]),
    'v43':dict(program='e350109ae0771afcd9bb94abf6bf40a8082110a76c33bcaaf7e23922a107ce4d',
        original=96,retained=[64,32],records=[2,1]),
}
ARMS=('cached','compressed','hybrid','cold')
TRIALS=('prepare',*ARMS,'oracle')
V45_JOBS={str(n):name for n,name in zip(range(13228,13236),
    ('prepare','hybrid','cached','cold','compressed','oracle','primary_audit','supplemental_audit'))}


def require(value,message):
    if not value:raise ValueError(message)


def read(path):
    path=Path(path)
    require(path.is_file() and not path.is_symlink(),'Missing or symbolic input: '+str(path))
    return strict_json(path.read_bytes())


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(2**20),b''):h.update(part)
    return h.hexdigest()


def verify_file(path,entry):
    path=Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size==entry['bytes']
        and sha(path)==entry['sha256'],'Artifact commitment differs: '+str(path))


def scheduler_status(text,expected=V45_JOBS):
    """Parse sacct -n -P --format=JobIDRaw,State,ExitCode; preserve all failures."""
    jobs={}
    for line in text.splitlines():
        fields=line.strip().split('|')
        if len(fields)<3 or fields[0] not in expected:continue
        key,state,code=fields[:3]
        require(key not in jobs,'Duplicate scheduler job: '+key)
        jobs[key]=dict(name=expected[key],state=state,exit_code=code)
    if set(jobs)!=set(expected):status='unknown_missing_scheduler_records'
    elif all(r['state']=='COMPLETED' and r['exit_code']=='0:0' for r in jobs.values()):status='all_completed'
    elif any(r['state'].split()[0] in ('FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE')
             or (r['state']=='COMPLETED' and r['exit_code']!='0:0') for r in jobs.values()):status='terminal_failure_observed'
    else:status='not_all_terminal'
    return dict(status=status,jobs=jobs,missing_jobs=sorted(set(expected)-set(jobs)))


def compare_audits(first,second,profile,program_sha,first_sha):
    spec=PROFILES[profile]
    for audit,schema in [(first,'complete-service-artifact-audit-'),(second,'complete-service-additive-artifact-audit-')]:
        require(audit['schema']==schema+profile and audit['status']=='verified'
            and audit['program_sha256']==program_sha,'Audit identity/status differs')
    require(second['frozen_audit_sha256']==first_sha and second['campaign']==first['campaign'],
        'Supplemental audit does not bind primary receipt')
    require(second['frozen_sources_changed'] is False,'Supplemental audit changed frozen sources')
    require(first['all_declared_artifacts_rehashed'] is True and first['complete_model'] is True
        and first['original_tokens']==spec['original'] and first['retained_tokens']==spec['retained'],
        'Audited workload extent differs')
    expected={(arm,step) for arm in ARMS for step in (1,2)}
    tables=[]
    for rows in (first['comparisons'],second['evidence']['comparisons']):
        table={(r['trial'],r['step']):r for r in rows}
        require(len(rows)==len(table)==8 and set(table)==expected,'All eight distinct comparisons required')
        for (_,step),row in table.items():
            require(all(row.get(k) is True for k in ('actual_bytes_equal','actual_model_bytes_equal','exact_retained_membership_verified'))
                and row['code_count']==42_467_328 and row['stages']==24
                and row['retained_tokens']==spec['retained'][step-1]
                and row['retained_records']==spec['records'][step-1],'Incomplete exactness evidence')
        tables.append(table)
    for key,row in tables[1].items():
        require(all(row.get(k) is True for k in ('model_export_matches_state_codes',
            'cross_representation_target_and_model_verified','registered_record_binding_verified')),
            'Missing supplemental code/source binding')
        require(all(row[k]==tables[0][key][k] for k in ('state_sha256','complete_model_sha256','state_bytes')),
            'Audits disagree on actual output commitments')


def verified_costs(primary,completions,transactions,checkpoint):
    """Recompute reported ratios, preserving slower/larger outcomes unchanged."""
    costs={};preparation=completions['prepare']['preparation']
    common=completions['prepare']['context_elapsed_ns']+sum(preparation[k] for k in
        ('common_source_ns','common_original_model_ns','common_disposal_ns'))
    for arm in ARMS:
        timing=primary['timings'][arm];worker=completions[arm];steps=worker['steps']
        require(len(steps)==2,'Two successive requests required')
        elapsed=[r['request_elapsed_ns'] for r in steps]
        live=[r['state_bytes']+r['trust_bytes'] for r in steps]
        deployed=[r['complete_deployment_bytes'] for r in steps]
        require(all(type(n) is int and n>0 for n in elapsed+live+deployed),'Invalid measured time/storage')
        require(deployed==[n+checkpoint for n in live],'Deployment omitted required checkpoint')
        own=preparation['representations'][timing['representation']]['representation_elapsed_ns']
        expected=dict(request_elapsed_ns=elapsed,live_state_bytes=live,complete_deployment_bytes=deployed,
            attributed_preparation_ns=common+own,attributed_two_deletion_lifetime_ns=common+own+transactions[arm]['elapsed_ns'])
        require(all(timing[k]==v for k,v in expected.items()),'Audited costs disagree with worker/transaction')
        costs[arm]=expected
    ratios={}
    for arm in ('cached','hybrid','cold'):
        a,b=costs['compressed'],costs[arm]
        row=dict(compressed_over_control_request_time=[x/y for x,y in zip(a['request_elapsed_ns'],b['request_elapsed_ns'])],
            compressed_live_state_saving=[1-x/y for x,y in zip(a['live_state_bytes'],b['live_state_bytes'])],
            compressed_deployment_saving=[1-x/y for x,y in zip(a['complete_deployment_bytes'],b['complete_deployment_bytes'])],
            compressed_over_control_observed_lifetime=a['attributed_two_deletion_lifetime_ns']/b['attributed_two_deletion_lifetime_ns'])
        require(row==primary['ratios'][arm],'Reported comparison ratios differ')
        ratios[arm]=row
    return dict(costs=costs,ratios=ratios)


def inspect(directory,repository,profile='v45',accounting=None,require_binaries=False):
    directory,repository=Path(directory).resolve(),Path(repository).resolve()
    spec=PROFILES[profile];program=read(directory/'program.json');ph=sha(directory/'program.json')
    require(ph==spec['program']==read(directory/'registration.json')['program_sha256'],
        'This is not the registered campaign')
    scheduler=None;accounting_sha=None
    if profile=='v45':
        require(accounting is not None,'Fresh scheduler accounting is required for V45')
        accounting_raw=Path(accounting).read_bytes()
        accounting_sha=hashlib.sha256(accounting_raw).hexdigest()
        scheduler=scheduler_status(accounting_raw.decode())
        if scheduler['status']!='all_completed':
            return dict(schema='copied-campaign-report-v48',status='unverified_execution',profile=profile,
                program_sha256=ph,scheduler=scheduler,accounting_sha256=accounting_sha,complete_model_verified=False,
                numerical_reproduction=False,confirmation=False,acl_ready=False)
    for name,expected in program['sources'].items():
        require(sha(repository/name)==expected,'Frozen source differs: '+name)
    ledger=read(directory/'budget/ledger.json')
    snapshot=read_budget_snapshot(directory/'budget',identity=ledger['binding']['identity'],
        phase_cpu_seconds={'feasibility':program['phase_cpu_seconds']})
    require(ledger['binding']['identity']==dict(protocol_sha256=ph,source_sha256=source_hashes(repository))
        and not snapshot['reserved_unknown_attempts']
        and not any(snapshot['over_cap'].values()),'Budget is unsettled, unbound, or over cap')
    remote_campaign=Path(program['directory']);remote_repository=remote_campaign.parents[1]
    completions={};transactions={};debits=set();required=[]
    for trial in TRIALS:
        root=directory/trial;identity=read(root/'worker/identity.json');receipt=read_completed(root/'worker',identity)
        require(identity['identity']==dict(campaign_sha256=ph,trial=trial) and receipt is not None,
            'Sealed worker identity missing or changed')
        require(identity['command'][1:]==['-B','-m',f'research_{profile}.worker',str(remote_campaign/trial/'plan.json')]
            and identity['cwd']==str(remote_repository)
            and receipt['worker_identity']==dict(campaign_sha256=ph,trial=trial),
            'Worker command or receipt identity differs')
        require(identity['phase_budget']==dict(binding_sha256=snapshot['binding_sha256'],
            phase='feasibility',directory=str(remote_campaign/'budget')),'Worker budget binding differs')
        require(receipt['outcome']['status']=='complete' and receipt['outcome']['returncode']==0,
            'Worker did not successfully finish')
        transactions[trial]=read(root/'transaction.json')
        require(transactions[trial]['worker_outcome']==receipt['outcome'],'Transaction and receipt disagree')
        debit=receipt['budget_attempt_id'];require(debit not in debits,'Duplicate worker debit');debits.add(debit)
        require(snapshot['attempts'][debit]==receipt['budget_debit'] and receipt['budget_debit']['state']=='settled',
            'Worker debit differs from actual ledger')
        require(receipt['budget_debit']['observed_cpu_ns']==receipt['resource_usage']['total_cpu_ns'],
            'Measured CPU differs from debit')
        plan=read(root/'plan.json')
        require(plan==dict(trial=trial,program=str(remote_campaign/'program.json'),program_sha256=ph,
            output=str(remote_campaign/trial/'outputs'),slurm_job_id=transactions[trial]['slurm_job_id']),
            'Plan differs from transaction/program')
        if profile=='v45':
            require(V45_JOBS.get(plan['slurm_job_id'])==trial,'Receipt belongs to another scheduled job')
        c=read(root/'outputs/completion.json');completions[trial]=c
        require(c['schema']==f'complete-service-worker-{profile}' and c['trial']==trial
            and c['slurm_job_id']==plan['slurm_job_id']
            and c['status']=='complete' and c['complete_model'] is True and c['program_sha256']==ph
            and c['source_sha256']==program['sources'],'Numerical completion binding differs')
        require(read(root/'worker'/receipt['attempt']/'status.json')==receipt,'Terminal status differs from receipt')
        required += [remote_campaign/trial/s for s in ('outputs/completion.json','transaction.json',
            'plan.json','worker/identity.json','worker/result.json',f"worker/{receipt['attempt']}/status.json")]
        required += [remote_campaign/trial/'worker'/receipt['attempt']/s for s in receipt['artifacts']]
    require(debits==set(snapshot['attempts']),'Missing or extra numerical attempts')
    first=read(directory/'artifact-audit.json');second=read(directory/'postrun-audit.json')
    compare_audits(first,second,profile,ph,sha(directory/'artifact-audit.json'))
    require(first['campaign']==str(remote_campaign),'Audit campaign differs from registered directory')
    if profile=='v45':
        require(second['slurm_job_id']=='13235','Supplemental audit belongs to another scheduled job')
    require(all(snapshot[k]==v for k,v in first['budget'].items()),'Primary audit budget differs')
    saved=second['ledger_snapshot']
    require(saved['path']==str(remote_campaign/'budget/ledger.json')
        and set(saved)==set(snapshot) and all(saved[k]==snapshot[k] for k in saved if k!='path'),
        'Supplemental audit does not bind the relocated ledger bytes')
    require(first['shared_checkpoint_bytes']==program['shared_checkpoint_bytes'],'Checkpoint accounting differs')
    verified=[];missing=[]
    for name,entry in second['inputs'].items():
        remote=Path(name)
        require(remote.is_absolute() and '..' not in remote.parts,'Unsafe recorded input path')
        if remote.is_relative_to(remote_campaign):local=directory/remote.relative_to(remote_campaign)
        else:
            require(remote.is_relative_to(remote_repository),'Recorded input escapes repository')
            local=repository/remote.relative_to(remote_repository)
        if local.exists():verify_file(local,entry);verified.append(name)
        else:
            require(not require_binaries and remote.suffix in ('.bin','.safetensors'),
                'Required copied input is missing: '+name)
            missing.append(dict(path=name,**entry))
    # Require the completion/ledger bytes used for arithmetic to be sealed by
    # the supplemental input inventory, not merely present beside it.
    required += [remote_campaign/s for s in ('program.json','registration.json','budget/ledger.json','artifact-audit.json')]
    require(all(str(path) in second['inputs'] for path in required),'Supplemental audit lacks consumed receipt bindings')
    measurements=verified_costs(first,completions,transactions,program['shared_checkpoint_bytes'])
    charged=snapshot['charged_cpu_seconds']['feasibility'];prior=program['prior_failed_charge']
    require(first['prior_failed_cpu_seconds']==prior and first['total_continuation_cpu_seconds']==prior+charged,
        'Prior failed charges omitted or changed')
    return dict(schema='copied-campaign-report-v48',status='verified_copied_audit_evidence',profile=profile,
        program_sha256=ph,scheduler=scheduler,accounting_sha256=accounting_sha,complete_model_verified_by_remote_audits=True,
        primary_audit_sha256=sha(directory/'artifact-audit.json'),supplemental_audit_sha256=sha(directory/'postrun-audit.json'),
        copied_inputs_rehashed=len(verified),remote_only_binary_inputs=missing,all_audited_inputs_present_locally=not missing,
        charged_cpu_seconds=charged,prior_failed_cpu_seconds=prior,total_continuation_cpu_seconds=charged+prior,comparisons=8,
        **measurements,numerical_reproduction=False,confirmation=False,acl_ready=False,
        scope='Copied receipt commitments and arithmetic checked; exact output equality relies on the two bound frozen audits. No new inference, certificate proof or performance measurement.',
        lifetime_scope='Attributed shared preparation plus observed two-request transaction; not an independently measured standalone pipeline.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory');parser.add_argument('--repository',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--profile',choices=PROFILES,default='v45');parser.add_argument('--accounting')
    parser.add_argument('--require-binaries',action='store_true');parser.add_argument('--output',required=True)
    args=parser.parse_args();output=Path(args.output)
    require(not output.exists(),'Use a fresh report path')
    result=inspect(args.directory,args.repository,args.profile,args.accounting,args.require_binaries)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream:stream.write(canonical_json(result))
    print(canonical_json(dict(status=result['status'],output=str(output))).decode())
