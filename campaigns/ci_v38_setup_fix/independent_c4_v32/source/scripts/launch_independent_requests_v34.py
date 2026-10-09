#!/usr/bin/env python3
"""Append-only continuation for one exact, independently audited C4 incident.

Both roots retain their original registrations, numerical source, and CPU ledger.
Only the five unstarted C4 trials may continue. The existing WikiText exception
remains scoped by its original V33 verifier. No evidence or trial is replaced.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import copy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import launch_independent_requests_v32 as base
from scripts import verify_terminal_recovery_v34 as recovery
from scripts import launch_independent_requests_v33 as prior
from scripts import launch_compressed_service_v31 as prior_launcher
from scripts import analyze_full_service_v30 as evidence_checks
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget,read_budget_snapshot
from src.pilot_budget import research_worker_lock
from src.run_store import atomic_write,canonical_json,digest
from src.runtime_contract import capture_runtime_contract
from src.worker_control import WorkerLimits,run_limited

require=base.require
hashed=base.hashed
read_json=base.read_json
campaign=base.campaign
registered_program=base.registered_program
historical_ledgers=base.historical_ledgers
validate_design=base.validate_design
build_spec=base.build_spec
archive_evidence=base.archive_evidence
resource_admission=base.resource_admission
verify_completed=recovery.verify_completed
POLICY_FIELDS=base.POLICY_FIELDS
ADAPTER='scripts/execute_compressed_recovery_v34.py'
ADAPTED_TRIAL='c4-delete-0-compressed'
CONTROLLERS=prior.CONTROLLERS+('scripts/launch_independent_requests_v34.py','scripts/verify_terminal_recovery_v34.py',ADAPTER)
PRIOR_IDS=('c4-root-prepare','c4-delete-0-cold')
REMAINING_IDS=('c4-delete-0-repair','c4-delete-1-repair','c4-delete-1-cold','c4-root-convert','c4-delete-0-compressed')
AMENDMENT=ROOT/'campaigns/independent_c4_v32/continuation-v1.json'


def adapter_contract():
    """Prove the only executable change is one evidence-verifier import."""
    original=ROOT/'scripts/run_compressed_service_v31.py'
    frozen=campaign('c4')/'source/scripts/run_compressed_service_v31.py'
    original_bytes=original.read_bytes()
    require(original_bytes==frozen.read_bytes(),'original compressed numerical worker differs from frozen source')
    before=b'from src.service_terminal_evidence_v30 import verify_completed'
    after=b'from scripts.verify_terminal_recovery_v34 import verify_completed'
    require(original_bytes.count(before)==1,'original verifier import is not unique')
    require((ROOT/ADAPTER).read_bytes()==original_bytes.replace(before,after),
        'adapter changes more than the exact completion-verifier import')
    require(source_hashes(ROOT)==source_hashes(campaign('c4')/'source'),
        'adapter numerical dependencies differ from original frozen sources')
    return dict(trial=ADAPTED_TRIAL,path=ADAPTER,sha256=hashed(ROOT/ADAPTER),
        original_path='scripts/run_compressed_service_v31.py',original_sha256=hashed(original),
        sole_source_change='completion-verifier import delegates to the exact V34 incident verifier',
        verification_source_changed=True,worker_entrypoint_changed=True,numerical_source_changed=False,
        original_input_paths_unchanged=True,numerical_dependency_root=str(ROOT),
        numerical_dependencies_match_original_frozen_inventory=True,
        runtime_and_resource_limits_unchanged=True,original_working_directory_unchanged=True)


def verify_worker_schedule(current,trial,transaction,identity,registration,program):
    if trial['id']!=ADAPTED_TRIAL:
        return evidence_checks.verify_worker_schedule(current,trial,transaction,identity,registration,program)
    active=amendment()
    require(active['worker_verification_adapter']==adapter_contract(),'registered evidence adapter changed')
    require(read_json(current/'attempts'/trial['id']/'plan.json').get('controller_continuation_sha256')==hashed(AMENDMENT),
        'adapted worker lacks its explicit continuation binding')
    # The common checker also verifies interpreter, original cwd, exact limits,
    # and nested clocks. Its command argument is explicitly the registered adapter.
    dispatch_trial=dict(trial,script=str(ROOT/ADAPTER))
    return evidence_checks.verify_worker_schedule(current,dispatch_trial,transaction,identity,registration,program)


def prior_bindings():
    """Bind all surviving prior text, including the explicitly discrepant file."""
    files={}
    for trial_id in PRIOR_IDS:
        location=campaign('c4')/'attempts'/trial_id
        for path in sorted(location.rglob('*.json')):
            name=path.relative_to(ROOT).as_posix()
            files[name]=dict(sha256=hashed(path),bytes=path.stat().st_size)
    return files


def validate_amendment(value):
    prior.amendment()
    current=campaign('c4');program,raw,protocol,registration=registered_program(current)
    require(value.get('schema')=='service-controller-continuation-v30'
        and value['original_program_sha256']==digest(raw)==recovery.PROGRAM_SHA256
        and value['original_protocol_sha256']==digest(protocol)==recovery.PROTOCOL_SHA256,
        'continuation does not bind the exact original program')
    require(value.get('cause')=='unknown' and value.get('original_three_copy_guard_passed') is False,
        'incident status or cause was changed')
    require(value['version']==34 and value['remaining_trials']==list(REMAINING_IDS)
        and value['prior_completed_trials']==list(PRIOR_IDS)
        and program['execution_order']==list(PRIOR_IDS)+list(REMAINING_IDS),'continuation trial set differs')
    for flag in ('budget_reset','evidence_changed','numerical_source_changed','preparation_repeated','samples_changed','thresholds_changed'):
        require(value.get(flag) is False,'continuation changes a preserved premise: '+flag)
    require(value['unchanged_phase_cap_seconds']==1900 and value['new_allowance_seconds']==0,
        'continuation must preserve the original CPU allowance')
    require(value['worker_verification_adapter']==adapter_contract(),'worker evidence adapter contract differs')
    require(value['controller_sha256']=={name:hashed(ROOT/name) for name in CONTROLLERS},'continuation controller changed')
    require(value['prior_text_bindings']==prior_bindings(),'prior evidence changed after incident registration')
    require(value['incident_audit_sha256']==hashed(ROOT/recovery.AUDIT_RELATIVE)==recovery.AUDIT_SHA256
        and value['incident_snapshot_sha256']==hashed(ROOT/recovery.SNAPSHOT_RELATIVE/'manifest.json')==recovery.SNAPSHOT_SHA256,
        'independent recovery evidence changed')
    old_ledger=value['prior_ledger'];now=read_json(current/'phase-cpu-budget/ledger.json')
    require(old_ledger['binding']==now['binding'],'original ledger binding changed')
    for key,row in old_ledger['attempts'].items():
        require(row['state']=='settled' and now['attempts'].get(key)==row,'prior settled debit changed')
    require(len(old_ledger['attempts'])==2
        and sum(row['charged_cpu_seconds'] for row in old_ledger['attempts'].values())==422,
        'incident starting ledger differs')
    require(value['prior_wikitext_continuation_sha256']==hashed(prior.AMENDMENT),'prior WikiText continuation changed')
    require(value['primary_clock']==program['primary_clock'],'continuation timing boundary changed')
    require(capture_runtime_contract()==registration['runtime'],'original registered runtime changed')
    require(source_hashes(ROOT)==program['source_sha256'],'original numerical sources changed')
    return value


def amendment():
    require(AMENDMENT.is_file(),'register the reviewed append-only continuation first')
    return validate_amendment(read_json(AMENDMENT))


def verify_registered_attempt(current, trial_id, *, cache=None):
    """Bind a consistent receipt to the exact authorized plan and resources.

Dependencies must precede this trial. The per-call cache shares verified parent
evidence; it is never retained between controller requests.
"""
    current=Path(current);cache={} if cache is None else cache
    key=(str(current),trial_id)
    if key in cache:return cache[key]
    program,raw,protocol,registration=registered_program(current)
    ids=[row['id'] for row in program['trials']]
    require(len(ids)==len(set(ids)) and trial_id in ids,'registered trial is missing or duplicated')
    trial=program['trials'][ids.index(trial_id)]
    parents={}
    bindings=list(trial.get('inputs_from_trial',{}).values())+trial.get('depends',[])
    for binding in bindings:
        name=binding['trial']
        require(name in ids and ids.index(name)<ids.index(trial_id),'registered dependency must point backwards')
        parents[name]=verify_registered_attempt(current,name,cache=cache)
        for field,expected in binding.get('equals',{}).items():
            value=parents[name]
            for part in field.split('.'):value=value[part]
            require(value==expected,'registered dependency condition failed')
    attempt=current/'attempts'/trial_id
    result=verify_completed(attempt)
    plan=json.loads((attempt/'plan.json').read_bytes())
    evidence_checks.verify_plan(current,trial,plan,program,digest(raw),digest(protocol),parents)
    transaction,receipt,identity=(json.loads((attempt/name).read_bytes()) for name in
        ('transaction.json','worker/result.json','worker/identity.json'))
    verify_worker_schedule(current,trial,transaction,identity,registration,program)
    expected_schema={'run_ordered_service_v30.py':'ordered-complete-service-transaction-v30',
        'run_compressed_service_v31.py':'native-box-compressed-service-transaction-v31'}
    require(trial['script'] in expected_schema and result.get('schema')==expected_schema[trial['script']],
        'registered terminal worker family differs')
    require(result.get('method')==plan['method'] and result.get('source_sha256')==program['source_sha256'],
        'registered terminal method or source differs')
    require(result.get('complete_model') is True and result.get('complete_state') is (plan['method']!='model_only_fresh'),
        'registered terminal output contract differs')
    for field in ('confirmation','scientific_promotion','use_candidates'):
        require(result.get(field) is False,'registered terminal scientific policy differs')
    for field in POLICY_FIELDS:
        if field=='expected_target':
            require(result.get('fixed_target_sha256')==plan[field],'registered terminal target differs')
        elif field in plan:
            require(result.get(field)==plan[field],'registered terminal numerical policy differs: '+field)
    require(result.get('retained_record_ids')==plan['record_ids']
        and result.get('deleted_record_ids')==plan['deleted_ids'],'registered terminal membership differs')
    expected_campaign=program.get('worker_campaign','independent-'+program['corpus']+'-v32')
    require(identity['identity']==dict(campaign=expected_campaign,plan_sha256=hashed(attempt/'plan.json')),
        'registered worker identity differs')
    snapshot=read_budget_snapshot(current/'phase-cpu-budget',
        identity=dict(protocol_sha256=digest(protocol),source_sha256=program['source_sha256']),
        phase_cpu_seconds={'feasibility':program['phase_cpu_cap_seconds']})
    require(snapshot['status']=='verified','registered ledger is unavailable')
    expected_budget=dict(binding_sha256=snapshot['binding_sha256'],phase='feasibility',
        directory=str(current/'phase-cpu-budget'))
    require(identity.get('phase_budget')==expected_budget,'registered worker ledger identity differs')
    debit_id=digest(canonical_json(dict(worker=identity,attempt=str(attempt/'worker'/receipt['attempt']))))
    require(receipt['budget_attempt_id']==debit_id,'registered CPU debit identity differs')
    require(snapshot['attempts'].get(debit_id)==receipt['budget_debit'],
        'registered receipt debit differs from current ledger')
    require(receipt['budget_debit']['reserved_cpu_seconds']==trial['cpu_seconds']+2
        and receipt['budget_debit']['phase']=='feasibility','registered CPU reservation differs')
    require(transaction['budget']['binding_sha256']==snapshot['binding_sha256']
        and transaction['budget']['phase_cpu_seconds']==snapshot['phase_cpu_seconds'],
        'registered transaction ledger binding differs')
    require(not snapshot['over_cap']['feasibility'] and not snapshot['reservation_overrun_attempts'],
        'registered CPU allowance was exceeded')
    cache[key]=result
    return result



def completed(current, trial_id):
    program=json.loads((current/'program.json').read_bytes());ids=[row['id'] for row in program['trials']]
    require(trial_id in ids,'trial absent from program');trial=program['trials'][ids.index(trial_id)]
    cache={};attempt=current/'attempts'/trial_id
    result=verify_registered_attempt(current,trial_id,cache=cache);comparisons=[]
    for comparison in trial.get('compare_to',[]):
        other=comparison['trial'];require(other in ids and ids.index(other)<ids.index(trial_id),'comparison must point backwards')
        reference=verify_registered_attempt(current,other,cache=cache)
        for kind in comparison.get('artifacts',['model']):
            left,right=result['artifacts'][kind],reference['artifacts'][kind]
            same=left['sha256']==right['sha256'] and left['bytes']==right['bytes']
            comparisons.append(dict(reference_trial=other,artifact=kind,equal=same,actual_sha256=left['sha256'],reference_sha256=right['sha256']))
    require(all(row['equal'] for row in comparisons),'registered exact model comparison failed')
    agreement=dict(comparisons=comparisons,all_equal=all(row['equal'] for row in comparisons))
    sidecar=attempt/'cross-method-agreement.json'
    require(not sidecar.exists() or json.loads(sidecar.read_bytes())==agreement,'comparison sidecar changed')
    gate_trial=copy.deepcopy(trial);references={}
    for name in ('storage_gate','latency_gate'):
        gate=gate_trial.get(name)
        if gate is None:continue
        others=[gate.pop('trial')] if name=='storage_gate' else gate.pop('trials')
        if name=='storage_gate':gate['external']=others[0]
        else:gate['externals']=others
        for other in others:
            require(other in ids and ids.index(other)<ids.index(trial_id),'scientific reference must point backwards')
            parent=current/'attempts'/other;checked=verify_registered_attempt(current,other,cache=cache)
            references[other]=dict(attempt=str(parent),verified_artifacts=checked['artifacts'],
                evidence={'transaction.json':dict(sha256=hashed(parent/'transaction.json'))})
    gates=prior_launcher.scientific_gates(gate_trial,result,references,json.loads((attempt/'transaction.json').read_bytes()))
    gate_file=attempt/'scientific-gates.json'
    require(not gate_file.exists() or json.loads(gate_file.read_bytes())==gates,'scientific gate sidecar changed')
    return dict(result,registered_scientific_gates=gates,verified_comparisons=agreement)




def prepare_continuation():
    require(not AMENDMENT.exists(),'continuation exists; no overwrite')
    current,program,raw,protocol,registration=prior.check_registered('c4')
    require(digest(raw)==recovery.PROGRAM_SHA256 and digest(protocol)==recovery.PROTOCOL_SHA256,'unexpected original program')
    for name in REMAINING_IDS:require(not (current/'attempts'/name).exists(),'remaining trial was already started')
    wiki=prior.status('wikitext')
    require(wiki['complete'] and not wiki['blocked'],'original WikiText sequence must remain complete')
    receipts=[]
    for name in PRIOR_IDS:
        verify_registered_attempt(current,name)
        receipts.append(read_json(current/'attempts'/name/'worker/result.json'))
    snapshot=evidence_checks.verify_final_budget(current,program,digest(protocol),receipts)
    require(snapshot['charged_cpu_seconds']['feasibility']==422,'initial phase charge differs')
    value=dict(schema='service-controller-continuation-v30',version=34,status='prospectively_registered',
        original_program_sha256=digest(raw),original_protocol_sha256=digest(protocol),
        prior_completed_trials=list(PRIOR_IDS),remaining_trials=list(REMAINING_IDS),
        controller_sha256={name:hashed(ROOT/name) for name in CONTROLLERS},
        prior_text_bindings=prior_bindings(),prior_ledger=read_json(current/'phase-cpu-budget/ledger.json'),
        prior_wikitext_continuation_sha256=hashed(prior.AMENDMENT),worker_verification_adapter=adapter_contract(),
        incident_audit_sha256=recovery.AUDIT_SHA256,incident_snapshot_sha256=recovery.SNAPSHOT_SHA256,
        original_three_copy_guard_passed=False,cause='unknown',
        recovered_terminal_scope='One exact C4 cold0 discrepancy only: completion, controller seal, stdout, receipt, model, plan, schedule, and debit verified. Original running progress preserved. Prior WikiText exception is unchanged.',
        budget_reset=False,evidence_changed=False,numerical_source_changed=False,preparation_repeated=False,
        samples_changed=False,thresholds_changed=False,unchanged_phase_cap_seconds=1900,new_allowance_seconds=0,
        primary_clock=program['primary_clock'],created_unix_ns=time.time_ns(),
        tool_scheduling_precaution='Run remaining workers serially in one process. No concurrent filesystem tools or agents during timing. This precaution does not establish the incident cause.',
        c4_policy='Finish only the five unstarted C4 trials under the original program and ledger. Preserve scientific losses; stop on any new execution or integrity failure.')
    validate_amendment(value)
    return value


def register_continuation():
    value=prepare_continuation()
    with AMENDMENT.open('xb') as stream:
        stream.write(canonical_json(value));stream.flush();os.fsync(stream.fileno())
    directory=os.open(AMENDMENT.parent,os.O_RDONLY)
    try:os.fsync(directory)
    finally:os.close(directory)
    return dict(registered=True,continuation_sha256=hashed(AMENDMENT),remaining_trials=list(REMAINING_IDS),
        unchanged_phase_cap=1900,new_allowance=0,starting_charge=422)


def check_registered(corpus):
    require(corpus in ('wikitext','c4'),'unknown corpus')
    if corpus=='c4':amendment()
    return prior.check_registered(corpus)


def status(corpus):
    current=campaign(corpus)
    if not current.exists():return dict(corpus=corpus,registered=False,next_action='register',campaign=str(current))
    current,program,raw,protocol,registration=check_registered(corpus)
    done=[];blocked=None;next_id=None
    for trial in program['trials']:
        attempt=current/'attempts'/trial['id']
        if not attempt.exists():next_id=trial['id'];break
        try:done.append(dict(id=trial['id'],scientific_gates=completed(current,trial['id'])['registered_scientific_gates']))
        except (ValueError,KeyError,OSError) as exc:
            blocked=dict(id=trial['id'],reason=str(exc),automatic_retry=False);break
    snapshot=read_budget_snapshot(current/'phase-cpu-budget',identity=dict(protocol_sha256=digest(protocol),source_sha256=program['source_sha256']),
        phase_cpu_seconds={'feasibility':1900})
    if snapshot.get('status')=='verified' and any(v['state']!='settled' for v in snapshot['attempts'].values()):
        blocked=dict(reason='unsettled worker or lost receipt; no automatic retry');next_id=None
    return dict(corpus=corpus,registered=True,completed=done,blocked=blocked,next_trial=None if blocked else next_id,
        complete=len(done)==7,budget=snapshot)


def run(corpus, trial_id):
    current,program,raw,protocol,registration=check_registered(corpus)
    ids=program['execution_order'];require(trial_id in ids,'unregistered trial')
    require(corpus=='c4' and trial_id in REMAINING_IDS,'completed prior trial cannot be repeated')
    for previous in ids[:ids.index(trial_id)]:completed(current,previous)
    trial=program['trials'][ids.index(trial_id)]
    for dependency in trial.get('depends',[]):
        checked=completed(current,dependency['trial'])
        for field,expected in dependency.get('equals',{}).items():
            value=checked
            for part in field.split('.'):value=value[part]
            require(value==expected,'registered dependency condition failed')
    budget=PhaseBudget(current/'phase-cpu-budget',identity={'protocol_sha256':digest(protocol),
        'source_sha256':program['source_sha256']},phase_cpu_seconds={'feasibility':1900})
    snap=budget.snapshot();require(all(row['state']=='settled' for row in snap['attempts'].values()),'unsettled worker blocks admission')
    require(1900-snap['charged_cpu_seconds']['feasibility']>=trial['cpu_seconds']+2,'insufficient complete reservation')
    attempt=current/'attempts'/trial_id;attempt.mkdir(parents=True,exist_ok=False);start=time.perf_counter_ns()
    plan=dict(trial['plan'],source_sha256=program['source_sha256'],protocol_sha256=digest(protocol),program_sha256=digest(raw),
        phase='feasibility',output=str(attempt/'outputs'));plan['inputs']=dict(plan['inputs'])
    for key,binding in trial.get('inputs_from_trial',{}).items():
        parent=completed(current,binding['trial']);location=current/'attempts'/binding['trial']/'outputs'
        path=location/('completion.json' if binding.get('completion') is True else parent['artifacts'][binding['artifact']]['file'])
        plan['inputs'][key]=dict(path=str(path),sha256=hashed(path))
    plan['controller_continuation_sha256']=hashed(AMENDMENT)
    path=attempt/'plan.json';atomic_write(path,canonical_json(plan));source=current/'source'
    dispatch=ROOT/ADAPTER if trial_id==ADAPTED_TRIAL else source/'scripts'/trial['script']
    receipt=run_limited([sys.executable,str(dispatch),str(path)],attempt/'worker',
        WorkerLimits(trial['wall_seconds'],trial['cpu_seconds'],6*2**30,1,tuple(program['affinity_cpus'])),
        identity={'campaign':program.get('worker_campaign','independent-'+corpus+'-v32'),'plan_sha256':digest(path.read_bytes())},
        cwd=source,phase_budget=budget,phase='feasibility')
    receipt_sha=hashed(attempt/'worker/result.json');elapsed=time.perf_counter_ns()-start
    atomic_write(attempt/'transaction.json',canonical_json(dict(schema='research-transaction-v30',worker_outcome=receipt['outcome'],
        receipt_sha256=receipt_sha,controller_elapsed_ns=elapsed,primary_clock=program['primary_clock'],budget=budget.snapshot())))
    live=attempt/'outputs/progress.json'
    if live.exists():atomic_write(attempt/'sealed-progress.json',live.read_bytes())
    gates=None
    if receipt['outcome']['status']=='complete':
        result=completed(current,trial_id);gates=result['registered_scientific_gates']
        atomic_write(attempt/'cross-method-agreement.json',canonical_json(result['verified_comparisons']))
        atomic_write(attempt/'scientific-gates.json',canonical_json(gates))
    return dict(corpus=corpus,trial=trial_id,status=receipt['outcome']['status'],controller_seconds=elapsed/1e9,
        scientific_gates=gates,phase_charge=budget.snapshot()['charged_cpu_seconds']['feasibility'])



def execute_remaining():
    """One serial process; no automatic retry, method change, or new allowance."""
    amendment()
    require(prior.status('wikitext')['complete'],'WikiText prerequisite must remain complete')
    for _ in range(6):
        observed=status('c4')
        require(not observed.get('blocked'),'existing incomplete attempt blocks continuation')
        if observed['complete']:
            print(json.dumps(dict(corpus='c4',complete=True,budget=observed['budget']),sort_keys=True),flush=True)
            return dict(program_complete=True,scope='two preselected development roots; broader paper program remains open')
        outcome=run('c4',observed['next_trial']);print(json.dumps(outcome,sort_keys=True),flush=True)
        require(outcome['status']=='complete','worker failed; no automatic retry')
    raise ValueError('unexpected trial count; continuation stopped')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',choices=('wikitext','c4'),default='c4')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--register-continuation',action='store_true')
    group.add_argument('--preflight-continuation',action='store_true')
    group.add_argument('--run')
    group.add_argument('--run-next',action='store_true');group.add_argument('--status',action='store_true')
    group.add_argument('--execute-remaining',action='store_true')
    args=parser.parse_args()
    with research_worker_lock(ROOT):
        if args.preflight_continuation:
            value=prepare_continuation()
            result=dict(preflight=True,registered=False,remaining_trials=value['remaining_trials'],new_allowance=0,starting_charge=422)
        elif args.register_continuation:result=register_continuation()
        elif args.status:result=status(args.corpus)
        elif args.execute_remaining:result=execute_remaining()
        elif args.run_next:
            observed=status(args.corpus)
            require(observed.get('registered') and not observed.get('blocked'),'root is not ready for continuation')
            result=observed if observed['complete'] else run(args.corpus,observed['next_trial'])
        else:result=run(args.corpus,args.run)
    print(json.dumps(result,sort_keys=True),flush=True)
    if result.get('status') not in (None,'complete') or result.get('blocked'):raise SystemExit(1)


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError) as exc:
        print(str(exc),file=sys.stderr,flush=True);raise SystemExit(1)
