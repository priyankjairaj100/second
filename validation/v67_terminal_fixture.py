"""Entirely generated receipt fixture. Never a model, job, or result archive.

Only the already-public protocol commitments are read. All synthetic durations,
model/state commitments, receipts and job success flags exist only in memory.
"""
import copy
import json
from pathlib import Path
from validation import check_v67_terminal_metadata as m


def make():
    repo=Path(__file__).resolve().parents[1]
    p=json.loads((repo/'handoff/registration_v67.json').read_text());directory=p['directory'];root=str(Path(directory).parents[1])
    files={}
    def put(name,value):files[name]=m.canonical(value)
    def get(name):return json.loads(files[name])
    def binding(label,size=5):return dict(bytes=size,sha256=m.info(('GENERATED FIXTURE ONLY:'+label).encode())['sha256'])
    put('program.json',p);files['research_v67/config.py']=(repo/'research_v67/config.py').read_bytes()
    target='ded01d9b27816eb32a8ddc241f0c014a05b43a5ffe7ce6f2f0a8853aefb3d0ad'
    old={str(Path(n).relative_to(root)):e['sha256'] for n,e in p['prior_sources'].items()
        if str(Path(n).parent) in (root+'/src',root+'/scripts') and Path(n).suffix=='.py'
        and (str(Path(n).parent)==root+'/src' or Path(n).name.startswith('run_'))}
    budget_binding=dict(identity=dict(protocol_sha256=m.SHA,source_sha256=old),
        phase_cpu_seconds={'feasibility':p['phase_cpu_seconds']},scope='trusted_worker_cpu_admission_not_process_tree_containment')
    bh=m.info(m.canonical(budget_binding))['sha256'];attempts={};prefix={};completions={};transactions={};entries={}
    jobs={n:str(i) for i,n in enumerate(p['trial_order']+['primary','supplemental'],15262)}
    put('chain-submission.json',dict(jobs=[dict(name=n,job_id=j,arguments=['--time=01:00:00']) for n,j in jobs.items()]))
    provenance=m.canonical({'generated_fixture_only':True})
    def artifacts(trial):
        result={}
        def add(name,e):result[name]=dict(file=name,**e)
        add('execution-provenance.json',m.info(provenance));add('admission.json',m.info(b'{}'))
        if trial in ['prepare','oracle']:
            steps=[0] if trial=='prepare' else [1,2]
            for step in steps:
                pre='' if step==0 else f'step-{step}/'
                add(pre+'model.bin',binding('model'+str(step),p['model_bytes']))
                for rep in m.REPS:
                    add(pre+rep+'-state.bin',binding(f'{rep}/{step}',1000+step))
                    add(pre+rep+'-trust.json',binding('trust',2))
        else:
            arm,step=trial.rsplit('-',1)
            add('model.bin',binding('model'+step,p['model_bytes']))
            add('state.bin',binding(m.REP[arm]+'/'+step,1000+int(step)));add('trust.json',binding('trust',2))
        return result
    for trial in p['trial_order']:
        limits=dict(p['trials'][trial],address_space_bytes=p['process_address_space_bytes'],file_size_bytes=p['file_size_bytes'],threads=1,affinity_cpus=[0])
        command=[root+'/.venv-container/bin/python','-B',directory+'/research_v67/worker.py',directory+'/'+trial+'/plan.json']
        identity=dict(command=command,cwd=root,identity=dict(campaign_sha256=m.SHA,trial=trial),limits=limits,
            phase_budget=dict(binding_sha256=bh,phase='feasibility',directory=directory+'/budget'))
        req=dict(command=command,cwd=root,limits=limits)
        ack=dict(request_sha256=m.info(m.canonical(req))['sha256'],cpu_seconds=[limits['cpu_seconds'],limits['cpu_seconds']+1],
            address_space=[limits['address_space_bytes']]*2,file_size=[limits['file_size_bytes']]*2,affinity_cpus=[0],thread_environment={n:'1' for n in m.THREADS})
        did='generated-'+trial;debit=dict(phase='feasibility',reserved_cpu_seconds=limits['cpu_seconds']+2,state='settled',charged_cpu_seconds=2,observed_cpu_ns=2*10**9)
        attempts[did]=debit;prefix[did]=debit
        outcome=dict(status='complete',returncode=0)
        for name,value in [('request.json',req),('limits-applied.json',ack)]:put(trial+'/worker/attempt-fixture/'+name,value)
        seal=dict(identity_sha256=m.info(m.canonical(identity))['sha256'],worker_identity=identity['identity'],attempt='attempt-fixture',
            status='complete',outcome=outcome,limits=limits,limits_applied=ack,budget_attempt_id=did,budget_debit=debit,
            budget_reservation_overrun=False,resource_usage=dict(user_cpu_ns=10**9,system_cpu_ns=10**9,total_cpu_ns=2*10**9),
            artifacts={n:m.info(files[trial+'/worker/attempt-fixture/'+n]) for n in ['request.json','limits-applied.json']})
        put(trial+'/worker/identity.json',identity);put(trial+'/worker/result.json',seal);put(trial+'/worker/attempt-fixture/status.json',seal)
        t=dict(worker_outcome=outcome,elapsed_ns=12*10**9,controller_process_cpu_ns=10**8,slurm_job_id=jobs[trial],
            budget=dict(binding_sha256=bh,phase_cpu_seconds={'feasibility':p['phase_cpu_seconds']},
                charged_cpu_seconds={'feasibility':2*len(prefix)},attempts=copy.deepcopy(prefix),over_cap={'feasibility':False}))
        put(trial+'/transaction.json',t);transactions[trial]=t
        put(trial+'/plan.json',dict(trial=trial,program=directory+'/program.json',program_sha256=m.SHA,output=directory+'/'+trial+'/outputs',slurm_job_id=jobs[trial]))
        c=dict(schema='disjoint-complete-service-worker-v67',trial=trial,status='complete',complete_model=True,quality_evaluation=False,confirmation=False,
            program_sha256=m.SHA,slurm_job_id=jobs[trial],source_files_sha256=m.info(m.canonical(p['new_sources']))['sha256'],
            base_target_sha256=p['inputs']['base_target']['sha256'],calibration_target_sha256=p['inputs']['calibration_target']['sha256'],
            service_target_sha256=target,artifacts=artifacts(trial),execution_provenance_sha256=m.info(provenance)['sha256'],
            worker_elapsed_ns=10*10**9,context_elapsed_ns=10**8,max_rss_kib=100)
        if trial=='prepare':c['preparation']=dict(common_source_ns=10**8,common_original_model_and_write_ns=10**8,common_disposal_ns=10**8,
            states={rep:dict(representation_elapsed_ns=10**8,live_state_bytes=1002) for rep in m.REPS})
        elif trial=='oracle':c['steps']=[dict(step=s,retained_ids=['fixture-record-'+str(i) for i in range(n)],prior_state_read=False,
            independent_retained_token_traversal=True,common_timing=dict(neural_stage_record_pairs=24*n)) for s,n in [(1,12),(2,6)]]
        else:
            arm,s=trial.rsplit('-',1);step=int(s);n=p['retained_counts'][step-1]
            c['request']=dict(arm=arm,retained_ids=['fixture-record-'+str(i) for i in range(n)],live_state_bytes=1002+step,request_elapsed_ns=8*10**9,
                timing=dict(neural_stage_record_pairs=24*n if arm=='cold' else 0,stages=[dict(stage_id='fixture-stage-'+str(i),fallback=(arm=='compressed' and i==0),certificate_refusal=None,
                    solver=dict(fallback_rows=1 if arm=='compressed' and i==0 else 0)) for i in range(24)]))
        put(trial+'/outputs/completion.json',c);files[trial+'/outputs/execution-provenance.json']=provenance;files[trial+'/outputs/admission.json']=b'{}';completions[trial]=c
        e=dict(status='complete',error=None,program_sha256=m.SHA,job_id=jobs[trial],operation='run',arguments=[trial],hostname=p['slurm_host'],affinity_cpus=[0],
            cpu_limits=[600,16802],child_cpu_is_numerical_ledger_work=True,process_cpu_ns=10**9,waited_child_cpu_ns=2*10**9,elapsed_ns=15*10**9)
        put(trial+'-entry.json',e);put(trial+'-entry-start.json',{k:e[k] for k in ['program_sha256','job_id','operation','arguments','hostname','affinity_cpus']});entries[trial]=e
    ledger=dict(schema='phase-cpu-ledger-v1',binding=budget_binding,attempts=attempts);put('budget/ledger.json',ledger)
    budget=dict(status='verified',read_only=True,binding=budget_binding,binding_sha256=bh,ledger_sha256=m.info(files['budget/ledger.json'])['sha256'],
        ledger_bytes=len(files['budget/ledger.json']),attempts=attempts,phase_cpu_seconds={'feasibility':p['phase_cpu_seconds']},reserved_unknown_attempts=0,
        reservation_overrun_attempts=[],over_cap={'feasibility':False},charged_cpu_seconds={'feasibility':24})
    expected={directory+'/program.json':m.info(files['program.json']),directory+'/budget/ledger.json':m.info(files['budget/ledger.json'])}
    for group in ['prior_sources','new_sources','dependency_files','historical_ledgers']:expected.update(p[group])
    expected.update({e['path']:{k:e[k] for k in ['bytes','sha256']} for e in p['inputs'].values()})
    for trial,c in completions.items():
        for name,e in c['artifacts'].items():expected[directory+'/'+trial+'/outputs/'+name]={k:e[k] for k in ['bytes','sha256']}
        for name in files:
            if name.startswith(trial+'/') or name in [trial+'-entry.json',trial+'-entry-start.json']:expected[directory+'/'+name]=m.info(files[name])
    comparisons=[];storage={a:[] for a in m.ARMS}
    for a in m.ARMS:
        for s in (1,2):
            comparisons.append(dict(arm=a,step=s,actual_bytes_equal=True,actual_model_bytes_equal=True,source_membership_and_provenance_checked=True,
                independent_retained_traversal_witnessed=True,code_count=p['code_count'],stages=24,model_bytes=p['model_bytes'],
                model_sha256=binding('model'+str(s))['sha256'],**({'modern_restoration_equal':True} if a=='modern' else {})))
            storage[a].append(dict(state_bytes=1000+s,trust_bytes=2,live_state_bytes=1002+s,checkpoint_inclusive_bytes=1002+s+p['shared_checkpoint_bytes']))
    common=dict(status='verified',program_sha256=m.SHA,budget=budget,costs=m.recompute_costs(p,completions,transactions),
        controllers=dict(process_cpu_ns=12*10**9,entries=entries,waited_child_cpu_is_already_in_worker_debits=True,
            entry_final_write_and_container_startup_excluded_scheduler_accounting_required=True),
        confirmation=False,quality_evaluation=False,shared_checkpoint_bytes=p['shared_checkpoint_bytes'],
        added_codec_installation_bytes=sum(e['bytes'] for e in p['dependency_files'].values()),process_cpu_ns=10**9,elapsed_ns=2*10**9)
    primary=dict(common,schema='disjoint-service-primary-audit-v67',inputs=dict(expected),
        evidence=dict(comparisons=comparisons,storage=storage,original_storage={rep:dict(state_bytes=1000,trust_bytes=2,live_state_bytes=1002) for rep in m.REPS},
            target_sha256=target,shared_numerical_implementation=True));put('primary-audit.json',primary)
    expected[directory+'/primary-audit.json']=m.info(files['primary-audit.json'])
    put('supplemental-audit.json',dict(common,schema='disjoint-service-supplemental-audit-v67',inputs=expected,
        evidence=dict(primary_receipt_sha256=m.info(files['primary-audit.json'])['sha256'],ten_actual_model_pairs_equal=True,
            full_state_semantics_reparsed=False,primary_full_state_audit_required=True)))
    for kind in ['primary','supplemental']:
        cap=p[kind+'_audit_caps']['cpu'];e=dict(status='complete',error=None,program_sha256=m.SHA,job_id=jobs[kind],operation=kind,arguments=[],hostname=p['slurm_host'],
            cpu_limits=[cap,cap+1],child_cpu_is_numerical_ledger_work=False,process_cpu_ns=2*10**9,waited_child_cpu_ns=0,elapsed_ns=3*10**9)
        put(kind+'-entry.json',e);put(kind+'-entry-start.json',{k:e[k] for k in ['program_sha256','job_id','operation','arguments','hostname']})
    put('software-completion.json',dict(cpu_limits=[300,301],process_cpu_ns=10**9,waited_child_cpu_ns=0))
    rows=[]
    for i in range(15261,15276):
        for suffix in ['', '.batch']:rows.append(f'{i}{suffix}|fixture|COMPLETED|0:0|00:00:30|00:01.000||fixture-host|fixture-start|fixture-end')
    put('collection.json',dict(accounting='\n'.join(rows)))
    summary=dict(jobs={str(i):dict(state='COMPLETED',exit_code='0:0') for i in range(15261,15276)},terminal_receipts_present=True,queue='',
        archive={'synthetic_fixture_only':True},captured_at_utc='generated fixture, not an observation')
    return files,summary
