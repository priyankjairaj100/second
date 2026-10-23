"""Full saved-byte successor audit and separate accounting/metadata audit."""
import gc,time
from pathlib import Path
from research_v80 import campaign as c
from research_v80.config import ROOT,RUN,ORDER,ARMS,ARTIFACT_LIMIT,SERVICE_TARGET,CELLS,RESIDENT
from research_v80.io import require,regular,write
from research_v80.worker import predecessor,expected_artifacts,ARM_REPRESENTATION
from research_v80.receipts import verify_worker_receipts
from research_v66.operations import REPRESENTATIONS,MODERN
from research_v61.postrun import Inputs,model_matches_state,execution_matches_target,bind_ledger_snapshot
from research_v61.service import gram_budget,trust_read
from research_v61.state import Record,validate_state,verify_successor
from research_v63 import archive
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes
from src.run_store import canonical_json,digest,strict_json

class AuditInputs(Inputs):
    def read(self,path,*,retain=True,maximum=ARTIFACT_LIMIT):
        regular(path)
        return super().read(path,retain=retain,maximum=maximum)

def snapshot(p,inputs):
    s=read_budget_snapshot(RUN/'budget',identity=dict(protocol_sha256=c.sha(RUN/'program.json'),source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'feasibility':p['phase_cpu_seconds']})
    require(s['status']=='verified' and not s['reserved_unknown_attempts'] and not s['reservation_overrun_attempts']
        and not any(s['over_cap'].values()) and all(x['state']=='settled' for x in s['attempts'].values()),'Unsettled or over-cap budget')
    bind_ledger_snapshot(RUN,s,inputs);return s

def state_view(blob,trust,rep,records,target,g):
    require(canonical_json(strict_json(trust))==trust,'Noncanonical trust sidecar')
    trust=trust_read(strict_json(trust))
    if rep==MODERN:
        require(not trust,'Modern state cannot contain Gram trust');view=archive.unpack(blob)
        require(view.records==records and (target is None or view.target==target),'Modern target/membership differs')
    else:
        view=validate_state(blob,expected_target=target,expected_records=records,gram_trust=trust,gram_budget=g)
        require(view.representation==rep,'State representation differs')
    return view,trust

def verify_states(directory,p,completions,inputs,*,expected_stages=24,expected_codes=42_467_328):
    directory=Path(directory);rows,provenance=c.load_records(p)
    records=tuple(Record(r['id'],tuple(r['tokens']),canonical_json(provenance[r['id']])) for r in rows)
    g=gram_budget(p['normalization']);target=None;original_sizes={};executions=[]
    for trial in p['trial_order']:
        e=inputs.json(directory/trial/'outputs/execution-provenance.json')
        require(digest(canonical_json(e))==completions[trial]['execution_provenance_sha256'],'Execution provenance commitment differs')
        executions.append(e)
    require(all(e==executions[0] for e in executions),'Execution provenance differs across fresh processes')
    prep=directory/'prepare/outputs';prep_model=inputs.read(prep/'model.bin')
    for rep in REPRESENTATIONS:
        blob=inputs.read(prep/(rep+'-state.bin'));tb=inputs.read(prep/(rep+'-trust.json'))
        view,_=state_view(blob,tb,rep,records,target,g);target=view.target if target is None else target
        extent=model_matches_state(view,prep_model)
        require(extent['code_count']==expected_codes and extent['stages']==expected_stages,'Original complete model extent')
        original_sizes[rep]=dict(state_bytes=len(blob),trust_bytes=len(tb),live_state_bytes=len(blob)+len(tb))
        meta=completions['prepare']['preparation']['states'][rep]
        require(meta['live_state_bytes']==len(blob)+len(tb),'Preparation storage metadata differs')
        if rep==MODERN:require(archive.restore(view)==inputs.read(prep/'lossless-state.bin'),'Modern original restoration differs')
        del blob,tb,view;gc.collect()
    require(digest(target.fixed_payload)==SERVICE_TARGET and target.anchor_payload==c.bound(p['inputs']['base_target'])
        and canonical_json(strict_json(target.fixed_payload)['calibration_target'])==c.bound(p['inputs']['calibration_target']),'Actual saved teacher target differs')
    execution_matches_target(executions[0],target)
    for completion in completions.values():
        require(completion['service_target_sha256']==digest(target.fixed_payload)
            and completion['base_target_sha256']==digest(target.anchor_payload)
            and completion['calibration_target_sha256']==target.calibration_target_sha256,'Worker target commitments differ')
    comparisons=[];sizes={a:[] for a in ARMS}
    for arm in ARMS:
        rep=ARM_REPRESENTATION[arm]
        for step,n in enumerate(p['retained_counts'],1):
            trial=arm+'-'+str(step);root=directory/trial/'outputs';oracle=directory/'oracle/outputs'/f'step-{step}'
            prior,pn,tn=predecessor(trial);pr=directory/prior/'outputs'
            before=records[-(13 if step==1 else p['retained_counts'][step-2]):];after=records[-n:]
            previous=inputs.read(pr/pn);previous_trust=inputs.read(pr/tn)
            candidate=inputs.read(root/'state.bin');candidate_trust=inputs.read(root/'trust.json')
            fresh=inputs.read(oracle/(rep+'-state.bin'));fresh_trust=inputs.read(oracle/(rep+'-trust.json'))
            pv,pt=state_view(previous,previous_trust,rep,before,target,g)
            cv,ct=state_view(candidate,candidate_trust,rep,after,target,g)
            fv,ft=state_view(fresh,fresh_trust,rep,after,target,g)
            require(candidate==fresh and candidate_trust==fresh_trust,'Actual complete successor/trust differs from fresh reconstruction')
            kept={r.record_id for r in after};deleted=[r.record_id for r in before if r.record_id not in kept]
            require(cv.source_map()=={k:v for k,v in pv.source_map().items() if k[1] in kept},'Retained descriptor bytes changed')
            if rep==MODERN:
                require(archive.restore(cv)==inputs.read(oracle/'lossless-state.bin'),'Modern successor restoration differs')
                comparison=dict(actual_bytes_equal=True,code_count=sum(c.rows*c.columns for c in cv.stage_codes),modern_restoration_equal=True)
            else:
                comparison=verify_successor(previous,candidate,fresh,deleted,previous_gram_trust=pt,
                    candidate_gram_trust=ct,fresh_gram_trust=ft,gram_budget=g)
            model=inputs.read(root/'model.bin');expected=inputs.read(oracle/'model.bin')
            require(model==expected,'Actual complete model bytes differ from fresh model')
            extent=model_matches_state(cv,model);model_matches_state(fv,expected);model_matches_state(pv,inputs.read(pr/'model.bin'))
            require(extent['code_count']==expected_codes and extent['stages']==expected_stages,'Complete model extent differs')
            r=completions[trial]['request']
            require(r['arm']==CELLS[arm] and r['representation']==rep,'Cell operation/representation differs')
            fresh_result=completions['oracle']['steps'][step-1]
            require(r['retained_ids']==[x.record_id for x in after] and r['deleted_ids']==deleted
                and fresh_result['retained_ids']==r['retained_ids'] and fresh_result['prior_state_read'] is False
                and fresh_result['independent_retained_token_traversal'] is True
                and fresh_result['common_timing']['neural_stage_record_pairs']==expected_stages*n,'Membership/fresh traversal metadata differs')
            actual=dict(state_bytes=len(candidate),trust_bytes=len(candidate_trust),live_state_bytes=len(candidate)+len(candidate_trust),
                checkpoint_inclusive_bytes=len(candidate)+len(candidate_trust)+p['shared_checkpoint_bytes'])
            require(r['live_state_bytes']==actual['live_state_bytes'] and r['state']['bytes']==len(candidate)
                and r['trust']['bytes']==len(candidate_trust),'Request storage metadata differs')
            sizes[arm].append(actual)
            comparisons.append({**comparison,**extent,'arm':arm,'step':step,'actual_model_bytes_equal':True,
                'source_membership_and_provenance_checked':True,'independent_retained_traversal_witnessed':True})
            del previous,candidate,fresh,pv,cv,fv,model,expected;gc.collect()
    return dict(comparisons=comparisons,storage=sizes,original_storage=original_sizes,
        target_sha256=digest(target.fixed_payload),shared_numerical_target=True,implementation_versions_differ=True)

def costs(p,completions,inputs):
    prep=completions['prepare']['preparation'];timings={}
    common=completions['prepare']['context_elapsed_ns']+prep['common_source_ns']+prep['common_original_model_and_write_ns']+prep['common_disposal_ns']
    for arm in ARMS:
        rep=ARM_REPRESENTATION[arm];requests=[]
        for step in [1,2]:
            trial=arm+'-'+str(step);cpl=completions[trial];r=cpl['request'];tx=inputs.json(RUN/trial/'transaction.json')
            require(0<r['request_elapsed_ns']<=cpl['worker_elapsed_ns']<=tx['elapsed_ns'],'Clock containment differs')
            requests.append(dict(request_elapsed_ns=r['request_elapsed_ns'],worker_elapsed_ns=cpl['worker_elapsed_ns'],
                transaction_elapsed_ns=tx['elapsed_ns'],context_elapsed_ns=cpl['context_elapsed_ns'],
                controller_process_cpu_ns=tx['controller_process_cpu_ns'],max_rss_kib=cpl['max_rss_kib'],
                source_stage_record_pairs=r['timing']['neural_stage_record_pairs'],
                implementation=cpl['implementation'],fallback_stages=[x['stage_id'] for x in r['timing']['stages'] if x['fallback']]))
        attributed=common+prep['states'][rep]['representation_elapsed_ns']
        timings[arm]=dict(requests=requests,attributed_preparation_ns=attributed,
            attributed_two_request_total_ns=attributed+sum(x['transaction_elapsed_ns'] for x in requests),
            lifetime_scope='Attributed shared preparation plus two observed fresh-process request transactions; not an independently measured end-to-end lifecycle')
    return dict(timings=timings,preparation=prep,preparation_worker_elapsed_ns=completions['prepare']['worker_elapsed_ns'],
        preparation_transaction_elapsed_ns=inputs.json(RUN/'prepare/transaction.json')['elapsed_ns'],
        oracle_transaction_elapsed_ns=inputs.json(RUN/'oracle/transaction.json')['elapsed_ns'])

def entry_costs(p,completions,inputs):
    """Account controller CPU once; waited child CPU is already in worker debit."""
    receipts={};program_sha=c.sha(RUN/'program.json')
    for trial in p['trial_order']:
        r=inputs.json(RUN/(trial+'-entry.json'));start=inputs.json(RUN/(trial+'-entry-start.json'))
        require(r['status']=='complete' and r['error'] is None and r['program_sha256']==program_sha
            and r['operation']=='run' and r['arguments']==[trial]
            and r['job_id']==completions[trial]['slurm_job_id']==start['job_id']
            and start['program_sha256']==program_sha and start['operation']=='run' and start['arguments']==[trial]
            and r['hostname']==start['hostname']==p['slurm_host']
            and r['affinity_cpus']==start['affinity_cpus'] and len(r['affinity_cpus'])==1
            and r['cpu_limits']==[p['controller_cpu_soft_seconds'],p['controller_cpu_hard_seconds']]
            and r['child_cpu_is_numerical_ledger_work'] is True,'Controller entry binding differs')
        require(all(type(r[k]) is int and r[k]>=0 for k in ['process_cpu_ns','waited_child_cpu_ns','elapsed_ns'])
            and r['process_cpu_ns']<=(p['controller_cpu_soft_seconds']+1)*10**9,'Controller observed CPU outside allowance')
        require(inputs.json(RUN/trial/'transaction.json')['elapsed_ns']<=r['elapsed_ns'],'Entry clock excludes transaction')
        receipts[trial]=r
    total=sum(r['process_cpu_ns'] for r in receipts.values())
    require(total<=p['controller_allowance_cpu_seconds']*10**9,'Separate controller allowance exceeded')
    return dict(process_cpu_ns=total,entries=receipts,waited_child_cpu_is_already_in_worker_debits=True,
        entry_final_write_and_container_startup_excluded_scheduler_accounting_required=True)

def main(kind):
    require(kind in ['primary','supplemental'],'Unknown audit');tick=time.perf_counter_ns();cpu=time.process_time_ns()
    p=c.verify();inputs=AuditInputs();require(inputs.json(RUN/'program.json')==p,'Program changed')
    s=snapshot(p,inputs);completions=verify_worker_receipts(RUN,p,inputs,s)
    for e in p['inputs'].values():require(inputs.read(e['path'],retain=False)=={k:e[k] for k in ['bytes','sha256']},'Audit bound input differs')
    for group in ['prior_sources','new_sources','dependency_files','historical_ledgers']:
        for path,e in p[group].items():require(inputs.read(path,retain=False)==e,'Audit source/ledger binding differs')
    timing=costs(p,completions,inputs);controllers=entry_costs(p,completions,inputs)
    if kind=='primary':evidence=verify_states(RUN,p,completions,inputs)
    else:
        primary=inputs.json(RUN/'primary-audit.json')
        require(primary['status']=='verified' and primary['program_sha256']==c.sha(RUN/'program.json') and primary['budget']==s
            and primary['costs']==timing and primary['controllers']==controllers and len(primary['evidence']['comparisons'])==8,'Primary actual-byte audit is absent or inconsistent')
        # Independently re-read the eight actual model outputs, not just their hashes.
        for arm in ARMS:
            for step in [1,2]:require(inputs.read(RUN/(arm+'-'+str(step))/'outputs/model.bin')==inputs.read(RUN/'oracle/outputs'/f'step-{step}/model.bin'),'Supplemental actual-model check failed')
        evidence=dict(primary_receipt_sha256=digest(canonical_json(primary)),eight_actual_model_pairs_equal=True,
            full_state_semantics_reparsed=False,primary_full_state_audit_required=True)
    inputs.unchanged()
    result=dict(schema='disjoint-service-'+kind+'-audit-v80',status='verified',program_sha256=c.sha(RUN/'program.json'),
        budget=s,evidence=evidence,costs=timing,controllers=controllers,inputs=inputs.files,confirmation=False,quality_evaluation=False,
        elapsed_ns=time.perf_counter_ns()-tick,process_cpu_ns=time.process_time_ns()-cpu,
        controller_and_audit_cpu_outside_numerical_ledger=True,shared_checkpoint_bytes=p['shared_checkpoint_bytes'],
        added_codec_installation_bytes=sum(e['bytes'] for e in p['dependency_files'].values()))
    write(RUN/(kind+'-audit.json'),result)
