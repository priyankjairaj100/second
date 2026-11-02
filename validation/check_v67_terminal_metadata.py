"""Portable V67 terminal receipt reconciliation. Never reads numerical binaries.

This is reporting code, outside the frozen experiment. It cannot launch a job.
A successful report reconciles cluster audit claims, not an independent solver.
"""
import argparse
import ast
import json
from pathlib import Path
import sys
import tarfile
from decimal import Decimal
from validation.check_v67_snapshot import check as snapshot_check, info, canonical, SHA

ARMS=('cached','cold','hybrid','compressed','modern')
REP=dict(cached='lossless',cold='lossless',hybrid='hybrid_gram',compressed='compressed48',modern='modern_lossless')
REPS=set(REP.values())
THREADS=('BLIS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OMP_NUM_THREADS',
         'OPENBLAS_NUM_THREADS','RAYON_NUM_THREADS','VECLIB_MAXIMUM_THREADS')


def require(value,message):
    if not value:raise ValueError(message)


def elapsed_seconds(value):
    """Slurm elapsed/CPU text, retaining fractional seconds without float rounding."""
    require(isinstance(value,str) and value and value not in ('Unknown','N/A'),'Missing scheduler duration')
    days=0
    if '-' in value:
        d,value=value.split('-',1);require(d.isdigit(),'Invalid day field');days=int(d)
    parts=value.split(':');require(1<=len(parts)<=3,'Invalid duration fields')
    require(all(p.isdigit() for p in parts[:-1]),'Invalid duration prefix')
    seconds=Decimal(parts[-1]);require(seconds.is_finite() and 0<=seconds<60,'Invalid seconds')
    minutes=int(parts[-2]) if len(parts)>=2 else 0;hours=int(parts[-3]) if len(parts)==3 else 0
    require(0<=minutes<60 and (not days or hours<24),'Invalid hour/minute fields')
    return Decimal(days*86400+hours*3600+minutes*60)+seconds


def terminal_gate(summary,files):
    """Pending/failed scheduler state cannot be overridden by terminal-looking JSON."""
    required={str(i) for i in range(15261,15276)}
    require(set(summary['jobs'])==required,'Registered scheduler census differs')
    active={j:r['state'] for j,r in summary['jobs'].items() if r['state'] in ('PENDING','RUNNING','CONFIGURING','COMPLETING')}
    failed={j:r['state'] for j,r in summary['jobs'].items() if r['state'] not in ('PENDING','RUNNING','CONFIGURING','COMPLETING','COMPLETED')
            or (r['state']=='COMPLETED' and r['exit_code']!='0:0')}
    absent=[n for n in ('primary-audit.json','supplemental-audit.json','primary-entry.json','supplemental-entry.json') if n not in files]
    if failed:return dict(status='terminal_failure_preserved',failed_jobs=failed,active_jobs=active,missing_receipts=absent)
    if active:return dict(status='pending_terminal',active_jobs=active,missing_receipts=absent)
    if absent:return dict(status='terminal_capture_incomplete',active_jobs={},missing_receipts=absent)
    require(summary['terminal_receipts_present'] is True and not summary['queue'].strip(),'Terminal snapshot/queue disagree')
    return dict(status='ready_for_receipt_reconciliation')


def recompute_costs(program,completions,transactions):
    prep=completions['prepare']['preparation']
    require(set(prep['states'])==REPS,'Four unique state representations required')
    common=completions['prepare']['context_elapsed_ns']+sum(prep[k] for k in
        ['common_source_ns','common_original_model_and_write_ns','common_disposal_ns'])
    timings={}
    for arm in ARMS:
        requests=[]
        for step in (1,2):
            name=arm+'-'+str(step);c=completions[name];r=c['request'];t=transactions[name]
            require(all(type(v)is int and v>=0 for v in [r['request_elapsed_ns'],c['worker_elapsed_ns'],t['elapsed_ns'],c['context_elapsed_ns']]),'Invalid clocks')
            require(0<r['request_elapsed_ns']<=c['worker_elapsed_ns']<=t['elapsed_ns'],'Request clock containment')
            requests.append(dict(request_elapsed_ns=r['request_elapsed_ns'],worker_elapsed_ns=c['worker_elapsed_ns'],
                transaction_elapsed_ns=t['elapsed_ns'],context_elapsed_ns=c['context_elapsed_ns'],
                controller_process_cpu_ns=t['controller_process_cpu_ns'],max_rss_kib=c['max_rss_kib'],
                source_stage_record_pairs=r['timing']['neural_stage_record_pairs'],
                fallback_stages=[x['stage_id'] for x in r['timing']['stages'] if x['fallback']]))
        attributed=common+prep['states'][REP[arm]]['representation_elapsed_ns']
        timings[arm]=dict(requests=requests,attributed_preparation_ns=attributed,
            attributed_two_request_total_ns=attributed+sum(x['transaction_elapsed_ns'] for x in requests),
            lifetime_scope='Attributed shared preparation plus two observed fresh-process request transactions; not an independently measured end-to-end lifecycle')
    return dict(timings=timings,preparation=prep,preparation_worker_elapsed_ns=completions['prepare']['worker_elapsed_ns'],
        preparation_transaction_elapsed_ns=transactions['prepare']['elapsed_ns'],
        oracle_transaction_elapsed_ns=transactions['oracle']['elapsed_ns'])


def reconcile(files,summary):
    gate=terminal_gate(summary,files)
    scope=dict(actual_model_state_bytes_checked_locally=False,inference_executed=False,
        independent_solver_validation=False,quality_evaluation=False,confirmation=False,
        automatic_launch_or_retry=False,submission_ready=False)
    base=dict(schema='v67-portable-terminal-metadata-review',snapshot=summary['archive'],
        captured_at_utc=summary['captured_at_utc'],program_sha256=SHA,**scope)
    if gate['status']!='ready_for_receipt_reconciliation':return dict(base,**gate,cluster_terminal_audit_claims_reconciled=False)
    def obj(n):
        raw=files[n];value=json.loads(raw);require(canonical(value)==raw,'Noncanonical copied JSON: '+n);return value
    p=obj('program.json');directory=p['directory'];root=str(Path(directory).parents[1])
    constants={node.targets[0].id:ast.literal_eval(node.value)
        for node in ast.parse(files['research_v67/config.py']).body
        if isinstance(node,ast.Assign) and len(node.targets)==1
        and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='SERVICE_TARGET'}
    primary=obj('primary-audit.json');supplemental=obj('supplemental-audit.json')
    ledger=obj('budget/ledger.json');budget=primary['budget']
    require(budget==supplemental['budget'] and budget['status']=='verified' and budget['read_only'] is True,'Consistent terminal budget snapshot required')
    require(budget['attempts']==ledger['attempts'] and budget['binding']==ledger['binding'],'Actual copied ledger differs')
    require(budget['ledger_sha256']==info(files['budget/ledger.json'])['sha256']
        and budget['ledger_bytes']==len(files['budget/ledger.json'])
        and budget['binding_sha256']==info(canonical(ledger['binding']))['sha256'],'Ledger byte binding differs')
    require(budget['phase_cpu_seconds']=={'feasibility':p['phase_cpu_seconds']}
        and budget['reserved_unknown_attempts']==0 and budget['reservation_overrun_attempts']==[]
        and budget['over_cap']=={'feasibility':False},'Unsettled or exceeded numerical allowance')
    require(ledger['binding']['identity']['protocol_sha256']==SHA,'Budget protocol binding differs')
    old_sources={str(Path(name).relative_to(root)):e['sha256'] for name,e in p['prior_sources'].items()
        if str(Path(name).parent) in (root+'/src',root+'/scripts')
        and Path(name).suffix=='.py' and (str(Path(name).parent)==root+'/src' or Path(name).name.startswith('run_'))}
    require(bool(old_sources) and ledger['schema']=='phase-cpu-ledger-v1'
        and ledger['binding']==dict(identity=dict(protocol_sha256=SHA,source_sha256=old_sources),
            phase_cpu_seconds={'feasibility':p['phase_cpu_seconds']},
            scope='trusted_worker_cpu_admission_not_process_tree_containment'),'Complete ledger source/schema/scope differs')
    jobs={r['name']:r['job_id'] for r in obj('chain-submission.json')['jobs']}
    completions={};transactions={};entries={};used={};workers={};artifact_bindings={};prefix={}
    for trial in p['trial_order']:
        d=directory+'/'+trial;limits=p['trials'][trial];identity=obj(trial+'/worker/identity.json')
        seal=obj(trial+'/worker/result.json');c=obj(trial+'/outputs/completion.json');t=obj(trial+'/transaction.json')
        command=[root+'/.venv-container/bin/python','-B',directory+'/research_v67/worker.py',d+'/plan.json']
        require(identity['command']==command and identity['cwd']==root
            and identity['identity']==dict(campaign_sha256=SHA,trial=trial),'Worker identity or command differs')
        require(identity['phase_budget']==dict(binding_sha256=budget['binding_sha256'],phase='feasibility',directory=directory+'/budget'),'Worker budget identity differs')
        require(seal['identity_sha256']==info(canonical(identity))['sha256'] and seal['worker_identity']==identity['identity']
            and seal==obj(trial+'/worker/'+seal['attempt']+'/status.json'),'Worker seal differs')
        require(seal['status']=='complete' and seal['outcome']['status']=='complete' and seal['outcome']['returncode']==0
            and seal['outcome']==t['worker_outcome'],'Worker outcome is not successful')
        require(seal['limits']==identity['limits'] and all(identity['limits'][k]==v for k,v in limits.items())
            and identity['limits']['address_space_bytes']==p['process_address_space_bytes']
            and identity['limits']['file_size_bytes']==p['file_size_bytes']
            and identity['limits']['threads']==1 and len(identity['limits']['affinity_cpus'])==1,'Worker resource binding differs')
        for name,e in seal['artifacts'].items():require(info(files[trial+'/worker/'+seal['attempt']+'/'+name])==e,'Sealed artifact differs')
        req=obj(trial+'/worker/'+seal['attempt']+'/request.json');ack=obj(trial+'/worker/'+seal['attempt']+'/limits-applied.json')
        require(req['command']==command and req['cwd']==root and req['limits']==identity['limits'],'Executed request differs')
        require(ack==seal['limits_applied'] and ack['request_sha256']==info(canonical(req))['sha256']
            and ack['cpu_seconds']==[limits['cpu_seconds'],limits['cpu_seconds']+1]
            and ack['address_space']==[p['process_address_space_bytes']]*2
            and ack['file_size']==[p['file_size_bytes']]*2
            and ack['affinity_cpus']==identity['limits']['affinity_cpus']
            and ack['thread_environment']=={n:'1' for n in THREADS},'Applied limit acknowledgement differs')
        debit=seal['budget_debit'];usage=seal['resource_usage'];did=seal['budget_attempt_id']
        require(did not in used and debit==budget['attempts'][did] and debit['state']=='settled'
            and debit['phase']=='feasibility' and debit['reserved_cpu_seconds']==limits['cpu_seconds']+2,'CPU debit binding differs')
        require(all(type(usage[k]) is int and usage[k]>=0 for k in ['user_cpu_ns','system_cpu_ns','total_cpu_ns'])
            and usage['total_cpu_ns']==usage['user_cpu_ns']+usage['system_cpu_ns']==debit['observed_cpu_ns'],'Observed CPU differs')
        require(debit['charged_cpu_seconds']==max(1,(usage['total_cpu_ns']+999999999)//10**9)
            and debit['charged_cpu_seconds']<=debit['reserved_cpu_seconds'] and seal['budget_reservation_overrun'] is False,'CPU charge/cap differs')
        used[did]=debit;prefix[did]=debit
        expected=dict(binding_sha256=budget['binding_sha256'],phase_cpu_seconds=budget['phase_cpu_seconds'],
            charged_cpu_seconds={'feasibility':sum(x['charged_cpu_seconds'] for x in prefix.values())},attempts=dict(prefix),over_cap={'feasibility':False})
        require(t['budget']==expected,'Chronological transaction ledger differs')
        require(obj(trial+'/plan.json')==dict(trial=trial,program=directory+'/program.json',program_sha256=SHA,output=d+'/outputs',slurm_job_id=jobs[trial]),'Plan identity differs')
        require(c['schema']=='disjoint-complete-service-worker-v67' and c['trial']==trial and c['status']=='complete'
            and c['complete_model'] is True and c['quality_evaluation'] is False and c['confirmation'] is False
            and c['program_sha256']==SHA and c['slurm_job_id']==t['slurm_job_id']==jobs[trial]
            and c['source_files_sha256']==info(canonical(p['new_sources']))['sha256'],'Completed worker binding differs')
        require(c['base_target_sha256']==p['inputs']['base_target']['sha256']
            and c['calibration_target_sha256']==p['inputs']['calibration_target']['sha256']
            and c['service_target_sha256']==constants['SERVICE_TARGET'],'Teacher target differs')
        rebuilt={'model.bin'}|{rep+'-'+suffix for rep in REPS for suffix in ['state.bin','trust.json']}
        required={'execution-provenance.json','admission.json'}
        required|=rebuilt if trial=='prepare' else {f'step-{s}/'+n for s in (1,2) for n in rebuilt} if trial=='oracle' else {'model.bin','state.bin','trust.json'}
        require(set(c['artifacts'])==required,'Complete worker artifact census differs')
        for name,e in c['artifacts'].items():
            require(e['file']==name and type(e['bytes']) is int and 0<=e['bytes']<=p['artifact_limit_bytes'],'Artifact extent differs')
            binding={k:e[k] for k in ['bytes','sha256']};artifact_bindings[d+'/outputs/'+name]=binding
            copied=trial+'/outputs/'+name
            if copied in files:require(info(files[copied])==binding,'Copied output differs')
        require(c['execution_provenance_sha256']==c['artifacts']['execution-provenance.json']['sha256'],'Execution provenance differs')
        completions[trial]=c;transactions[trial]=t;workers[trial]=dict(resource_usage=usage,budget_debit=debit)
        e=obj(trial+'-entry.json');start=obj(trial+'-entry-start.json')
        require(e['status']=='complete' and e['error'] is None and e['program_sha256']==start['program_sha256']==SHA
            and e['job_id']==start['job_id']==jobs[trial] and e['operation']==start['operation']=='run'
            and e['arguments']==start['arguments']==[trial] and e['hostname']==start['hostname']==p['slurm_host']
            and e['affinity_cpus']==start['affinity_cpus']==identity['limits']['affinity_cpus']
            and e['cpu_limits']==[p['controller_cpu_soft_seconds'],p['controller_cpu_hard_seconds']]
            and e['child_cpu_is_numerical_ledger_work'] is True,'Controller entry differs')
        require(type(e['process_cpu_ns']) is int and 0<=e['process_cpu_ns']<=601*10**9
            and e['waited_child_cpu_ns']+2>=usage['total_cpu_ns']
            and 0<c['worker_elapsed_ns']<=t['elapsed_ns']<=e['elapsed_ns'],'Controller clock/CPU differs')
        entries[trial]=e
    require(set(used)==set(budget['attempts']) and len(used)==12,'Missing or extra numerical debit')
    require(len({c['execution_provenance_sha256'] for c in completions.values()})==1,'Fresh-process execution provenance differs')
    require(len(completions['oracle']['steps'])==2 and [r['step'] for r in completions['oracle']['steps']]==[1,2],'Fresh oracle endpoint census differs')
    charged=sum(e['charged_cpu_seconds'] for e in used.values())
    require(budget['charged_cpu_seconds']=={'feasibility':charged} and charged<=p['phase_cpu_seconds'],'Total numerical charge differs')
    costs=recompute_costs(p,completions,transactions)
    require(primary['costs']==supplemental['costs']==costs,'Audit clocks differ from underlying worker/transaction receipts')
    own=sum(e['process_cpu_ns'] for e in entries.values())
    controllers=dict(process_cpu_ns=own,entries=entries,waited_child_cpu_is_already_in_worker_debits=True,
        entry_final_write_and_container_startup_excluded_scheduler_accounting_required=True)
    require(own<=p['controller_allowance_cpu_seconds']*10**9 and primary['controllers']==supplemental['controllers']==controllers,'Controller accounting differs')
    codec=sum(e['bytes'] for e in p['dependency_files'].values())
    expected_inputs={directory+'/program.json':info(files['program.json']),directory+'/budget/ledger.json':info(files['budget/ledger.json'])}
    for group in ['prior_sources','new_sources','dependency_files','historical_ledgers']:expected_inputs.update(p[group])
    expected_inputs.update({e['path']:{k:e[k] for k in ['bytes','sha256']} for e in p['inputs'].values()})
    expected_inputs.update(artifact_bindings)
    for trial in p['trial_order']:
        seal=obj(trial+'/worker/result.json')
        names=[trial+'/transaction.json',trial+'/plan.json',trial+'/worker/identity.json',trial+'/worker/result.json',
            trial+'/worker/'+seal['attempt']+'/status.json',trial+'/outputs/completion.json',trial+'-entry.json',trial+'-entry-start.json']
        names += [trial+'/worker/'+seal['attempt']+'/'+n for n in seal['artifacts']]
        for name in names:expected_inputs[directory+'/'+name]=info(files[name])
    for kind,audit in [('primary',primary),('supplemental',supplemental)]:
        require(audit['schema']=='disjoint-service-'+kind+'-audit-v67' and audit['status']=='verified'
            and audit['program_sha256']==SHA and audit['confirmation'] is False and audit['quality_evaluation'] is False
            and audit['shared_checkpoint_bytes']==p['shared_checkpoint_bytes'] and audit['added_codec_installation_bytes']==codec,'Audit identity/scope differs')
        expected=dict(expected_inputs)
        if kind=='supplemental':expected[directory+'/primary-audit.json']=info(files['primary-audit.json'])
        require(audit['inputs']==expected,'Complete audit input inventory differs')
        for group in ['prior_sources','new_sources','dependency_files','historical_ledgers']:
            for name,e in p[group].items():require(audit['inputs'].get(name)==e,'Audit source/input inventory differs')
        for e in p['inputs'].values():require(audit['inputs'].get(e['path'])=={k:e[k] for k in ['bytes','sha256']},'External input commitment differs')
        for name,e in artifact_bindings.items():require(audit['inputs'].get(name)==e,'Audit output inventory differs')
        for name,e in audit['inputs'].items():
            if name.startswith(directory+'/'):
                rel=name[len(directory)+1:]
                if rel in files:require(info(files[rel])==e,'Audit consumed copied metadata differs')
        e=obj(kind+'-entry.json');start=obj(kind+'-entry-start.json');cap=p[kind+'_audit_caps']['cpu']
        require(e['status']=='complete' and e['error'] is None and e['program_sha256']==start['program_sha256']==SHA
            and e['job_id']==start['job_id']==jobs[kind] and e['operation']==start['operation']==kind
            and e['arguments']==start['arguments']==[] and e['hostname']==start['hostname']==p['slurm_host']
            and e['cpu_limits']==[cap,cap+1] and e['child_cpu_is_numerical_ledger_work'] is False,'Audit entry binding differs')
        require(0<=audit['process_cpu_ns']<=e['process_cpu_ns']<=(cap+1)*10**9 and 0<audit['elapsed_ns']<=e['elapsed_ns'],'Audit clock containment differs')
    ev=primary['evidence'];comparisons=ev['comparisons']
    require(len(comparisons)==10 and {(r['arm'],r['step']) for r in comparisons}=={(a,s) for a in ARMS for s in (1,2)},'Ten unique actual-state audit claims required')
    require(ev['shared_numerical_implementation'] is True and set(ev['storage'])==set(ARMS) and set(ev['original_storage'])==REPS,'Audit scope differs')
    require(ev['target_sha256']==constants['SERVICE_TARGET'],'Audited target differs')
    for rep in REPS:
        c=completions['prepare'];sb=c['artifacts'][rep+'-state.bin']['bytes'];tb=c['artifacts'][rep+'-trust.json']['bytes']
        require(ev['original_storage'][rep]==dict(state_bytes=sb,trust_bytes=tb,live_state_bytes=sb+tb)
            and c['preparation']['states'][rep]['live_state_bytes']==sb+tb,'Preparation live storage arithmetic differs')
    for r in comparisons:
        arm,step=r['arm'],r['step'];c=completions[arm+'-'+str(step)];request=c['request'];fresh=completions['oracle']['steps'][step-1]
        require(all(r[k] is True for k in ['actual_bytes_equal','actual_model_bytes_equal','source_membership_and_provenance_checked','independent_retained_traversal_witnessed']), 'Missing actual-byte audit assertion')
        require(r['code_count']==p['code_count'] and r['stages']==p['stage_count'] and r['model_bytes']==p['model_bytes']
            and r['model_sha256']==c['artifacts']['model.bin']['sha256']==completions['oracle']['artifacts'][f'step-{step}/model.bin']['sha256'],'Audited complete-model identity differs')
        require(request['retained_ids']==fresh['retained_ids'] and len(request['retained_ids'])==p['retained_counts'][step-1]
            and len(set(request['retained_ids']))==len(request['retained_ids'])
            and fresh['prior_state_read'] is False and fresh['independent_retained_token_traversal'] is True
            and fresh['common_timing']['neural_stage_record_pairs']==24*p['retained_counts'][step-1],'Retained/fresh traversal metadata differs')
        if arm=='modern':require(r['modern_restoration_equal'] is True,'Modern restoration audit assertion absent')
        for filename in ['state.bin','trust.json']:
            original=c['artifacts'][filename];reference=completions['oracle']['artifacts'][f'step-{step}/'+REP[arm]+'-'+filename]
            require({k:original[k] for k in ['bytes','sha256']}=={k:reference[k] for k in ['bytes','sha256']},'Candidate/fresh artifact commitments differ')
        size=ev['storage'][arm][step-1];sb=c['artifacts']['state.bin']['bytes'];tb=c['artifacts']['trust.json']['bytes']
        require(size==dict(state_bytes=sb,trust_bytes=tb,live_state_bytes=sb+tb,checkpoint_inclusive_bytes=sb+tb+p['shared_checkpoint_bytes'])
            and request['live_state_bytes']==sb+tb,'Full live/deployment storage arithmetic differs')
    se=supplemental['evidence']
    require(se==dict(primary_receipt_sha256=info(files['primary-audit.json'])['sha256'],ten_actual_model_pairs_equal=True,
        full_state_semantics_reparsed=False,primary_full_state_audit_required=True),'Supplemental audit scope/link differs')
    scheduler={}
    for line in obj('collection.json')['accounting'].splitlines():
        row=line.split('|');require(row[0] not in scheduler,'Duplicate scheduler row');scheduler[row[0]]=row
    allocated_cpu=Decimal(0)
    submission={r['job_id']:r for r in obj('chain-submission.json')['jobs']}
    for job in summary['jobs']:
        require(job in scheduler and job+'.batch' in scheduler,'Missing terminal allocation/batch row')
        for key in [job,job+'.batch']:require(scheduler[key][2:4]==['COMPLETED','0:0'],'Terminal scheduler row failed')
        if job=='15261':wall=p['software_wall_seconds']
        else:
            time_arguments=[s.split('=',1)[1] for s in submission[job]['arguments'] if s.startswith('--time=')]
            require(len(time_arguments)==1,'Unique registered scheduler wall ceiling required');wall=elapsed_seconds(time_arguments[0])
        require(0<elapsed_seconds(scheduler[job][4])<=wall,'Scheduler elapsed wall exceeds registered limit')
        allocated_cpu+=elapsed_seconds(scheduler[job][5])
    software=obj('software-completion.json')
    require(software['cpu_limits']==[300,301] and 0<=software['process_cpu_ns']<=301*10**9
        and software['process_cpu_ns']+software['waited_child_cpu_ns']<=p['software_allowance_cpu_seconds']*10**9,'Software gate CPU accounting differs')
    rows=[]
    for arm in ARMS:
        for step in (1,2):
            c=completions[arm+'-'+str(step)];stages=c['request']['timing']['stages']
            require(len(stages)==24 and len({r['stage_id'] for r in stages})==24,'Complete unique stage census required')
            solver=[r['solver'].get('diagnostics',{}).get('rows',r['solver']) for r in stages]
            rows.append(dict(arm=arm,step=step,retained_records=p['retained_counts'][step-1],
                **ev['storage'][arm][step-1],**costs['timings'][arm]['requests'][step-1],
                numerical_solver_fallback_rows=sum(r.get('fallback_rows',0) for r in solver),
                stage_refusals=sum(r['certificate_refusal'] is not None for r in stages)))
    return dict(base,status='verified_terminal_receipt_metadata',cluster_terminal_audit_claims_reconciled=True,
        complete_state_comparison_claims=10,comparison_rows=rows,costs=costs,workers=workers,
        numerical_worker_charged_cpu_seconds=charged,controller_own_cpu_ns=own,
        audit_entries={k:obj(k+'-entry.json') for k in ['primary','supplemental']},
        scheduler_allocation_cpu_seconds=str(allocated_cpu),scheduler_batch_cpu_not_added=True,
        nested_clocks_not_summed=True,added_codec_installation_bytes=codec,
        audit_receipt_commitments={k:info(files[k+'-audit.json']) for k in ['primary','supplemental']},
        decision_scope='One disjoint-root development sequence; strongest-control and quality decisions still required',
        omitted_input_binary_contents_not_revalidated=True,root_review_not_independent=True)


def check(path):
    require(not sys.flags.optimize,'Unoptimized reporting interpreter required')
    summary=snapshot_check(path)
    with tarfile.open(path,'r:gz') as t:files={m.name:t.extractfile(m).read() for m in t}
    return reconcile(files,summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive');parser.add_argument('--output',required=True)
    args=parser.parse_args();result=check(args.archive)
    with Path(args.output).open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:result[k] for k in ['status','cluster_terminal_audit_claims_reconciled','actual_model_state_bytes_checked_locally']}))
