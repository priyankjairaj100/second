"""Fresh, portable recovery of two preselected independent development roots.

This is a new registration, never a continuation of the lost V31 registration.
Historical metadata supplies prior evidence only. Every new clock comparison
uses the same newly prepared root and current registered runtime.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = None
sys.path.insert(0, str(ROOT))
from scripts import launch_compressed_service_v31 as prior_launcher
from scripts import analyze_full_service_v30 as evidence_checks
from scripts import prepare_independent_campaigns_v31 as policy
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget, read_budget_snapshot
from src.pilot_budget import research_worker_lock
from src.run_store import atomic_write, canonical_json, digest
from src.runtime_contract import capture_runtime_contract
from src.service_terminal_evidence_v30 import verify_completed, _verify_stdout
from src.worker_control import WorkerLimits, run_limited

BINDINGS = 'campaigns/recovery_v32/historical-bindings.json'
BINDINGS_SHA256 = 'bf000726d2b6cc4fa4707745e1dda4d3948e96d05ce5829c8344a59842671b20'
POLICY_FIELDS = policy.POLICY_FIELDS
CONTROLLERS = ('scripts/launch_independent_requests_v32.py',
    'scripts/analyze_full_service_v30.py', 'scripts/prepare_independent_campaigns_v31.py',
    'scripts/launch_compressed_service_v31.py', 'src/worker_control.py',
    'src/phase_budget.py', 'src/run_store.py', 'src/pilot_budget.py',
    'src/runtime_contract.py', 'src/experiment_inventory.py', 'src/service_terminal_evidence_v30.py')
RECOVERY = dict(
    schema='fresh-registration-amendment-v32', historical_checkpoint='604de5b830bd1386055b394df13275ef7e55475a',
    old_registrations_resumed=False, old_ledgers_modified=False, numerical_policy_changed=False,
    source_selection_changed=False, historical_binary_artifacts_available=False,
    historical_gate_scope='Immutable published metadata checked; historical model/state binaries are unavailable. Prior successful evidence only.',
    comparison_scope='Within the new root and registered runtime only; no historical latency enters a new gate.',
    lost_unpublished_context=dict(status='unverified conversation context, no receipt or ledger survives',
        wikitext_preparation_reported_cpu_seconds=314, wikitext_repair_reported_reservation_seconds=182,
        repair_observed_cpu_seconds=None, reuse_as_measured_evidence=False,
        entire_lost_phase_cpu_allowance_held_seconds=1900, held_allowance_is_not_observed_usage=True),
    statistical_scope='Development replication; prior selection remains fixed; no confirmation or population interval.',
    stop_rule='No retry or source replacement. Finish both selected roots after scientific losses. Execution or exactness failures block dependent work.')


def require(condition, message):
    if not condition: raise ValueError(message)


def hashed(path):
    path=Path(path)
    require(path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
        'missing or unsafe file: '+str(path))
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read_json(path):return json.loads(Path(path).read_bytes())


def campaign(corpus):
    require(corpus in ('wikitext','c4'),'unknown corpus')
    return ROOT/(WORKSPACE or 'campaigns')/('independent_'+corpus+'_v32')


def historical_ledgers(current):
    return {str(p.relative_to(ROOT)):hashed(p) for base in ('pilots','campaigns','local_runs')
        for p in sorted((ROOT/base).glob('**/phase-cpu-budget/ledger.json'))
        if current not in p.parents and not (current==campaign('wikitext') and campaign('c4') in p.parents)}


def check_file(entry):
    require(type(entry) is dict and set(entry) in ({'path','sha256'},{'path','sha256','bytes'}),'invalid file binding')
    path=Path(entry['path'])
    require(path.is_absolute() and hashed(path)==entry['sha256'],'bound input changed')
    if 'bytes' in entry:require(path.stat().st_size==entry['bytes'],'bound input size changed')
    return path


def relocate(value, old_root, new_root):
    """Relocate path strings only; never change hashes, tokens, or policies."""
    if isinstance(value,dict):return {k:relocate(v,old_root,new_root) for k,v in value.items()}
    if isinstance(value,list):return [relocate(v,old_root,new_root) for v in value]
    if isinstance(value,str) and (value==old_root or value.startswith(old_root+'/')):
        return str(new_root)+value[len(old_root):]
    return value


def archive_attempt(directory, trial_id):
    """Check pinned receipt consistency without claiming missing binary checks."""
    path=directory/'attempts'/trial_id
    program=read_json(directory/'program.json');protocol=read_json(directory/'protocol.json')
    registration=read_json(directory/'registration.json');plan=read_json(path/'plan.json')
    ph=hashed(directory/'program.json');qh=hashed(directory/'protocol.json')
    require(registration['program_sha256']==protocol['program_sha256']==ph
        and registration['protocol_sha256']==qh,'historical registration differs')
    require(plan['program_sha256']==ph and plan['protocol_sha256']==qh
        and plan['source_sha256']==program['source_sha256'],'historical plan registration differs')
    receipt=read_json(path/'worker/result.json');tx=read_json(path/'transaction.json')
    identity=read_json(path/'worker/identity.json');inner=path/'worker'/receipt['attempt']
    require(receipt['status']=='complete' and receipt['outcome']['status']=='complete'
        and receipt['outcome']['returncode']==0,'historical worker did not complete')
    require(tx['receipt_sha256']==hashed(path/'worker/result.json')
        and tx['worker_outcome']==receipt['outcome'],'historical receipt transaction differs')
    require(digest(canonical_json(identity))==receipt['identity_sha256']
        and identity['identity']==receipt['worker_identity']
        and receipt['worker_identity']['plan_sha256']==hashed(path/'plan.json'),'historical identity differs')
    request=read_json(inner/'request.json')
    for key in ('command','cwd','limits'):require(request[key]==identity[key],'historical request differs')
    for name,entry in receipt['artifacts'].items():
        require(Path(name).name==name,'unsafe historical artifact name')
        require(hashed(inner/name)==entry['sha256'] and (inner/name).stat().st_size==entry['bytes'],
            'historical receipt metadata differs')
    raw=(path/'outputs/completion.json').read_bytes()
    require(raw==(path/'outputs/progress.json').read_bytes()==(path/'sealed-progress.json').read_bytes(),
        'historical terminal copies differ')
    result=json.loads(raw);require(result['status']=='complete' and result['plan_sha256']==hashed(path/'plan.json'),
        'historical terminal plan differs')
    _verify_stdout(read_json(inner/'stdout-summary.json'),digest(raw))
    debit=receipt['budget_debit'];cpu=debit['observed_cpu_ns']
    require(debit['state']=='settled' and type(cpu) is int and cpu>=0
        and debit['charged_cpu_seconds']==max(1,(cpu+999999999)//1000000000),'historical CPU debit differs')
    require(tx['budget']['attempts'][receipt['budget_attempt_id']]==debit
        and receipt['resource_usage']['total_cpu_ns']==cpu,'historical settlement differs')
    return result,tx


def archive_evidence():
    """Pinned metadata is prior evidence, not a fresh historical-output audit."""
    require(hashed(ROOT/BINDINGS)==BINDINGS_SHA256,'recovery archive manifest changed')
    bindings=read_json(ROOT/BINDINGS)
    for name,entry in bindings['files'].items():
        path=ROOT/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe archive member')
        require(hashed(path)==entry['sha256'] and path.stat().st_size==entry['bytes'],'historical metadata changed: '+name)
    pilot=ROOT/'campaigns/compressed_service_v31'
    program=read_json(pilot/'program.json')
    require(source_hashes(ROOT)==program['source_sha256'],'numerical sources differ from published V31')
    require(program['draft_specification_sha256']==policy.COMPRESSED_POLICY_SHA256,'historical pilot draft differs')
    current,clock=archive_attempt(pilot,'repair-128-48')
    converted,_=archive_attempt(pilot,'convert-256-48')
    require(current['fixed_target_sha256']==policy.FIXED_TARGET
        and current['model_artifact']['sha256']==policy.RETAINED_MODEL
        and converted['model_artifact']['sha256']==policy.ORIGINAL_MODEL,'historical model target differs')
    cols=[]
    for name in ('cold-001','cold-002','cold-003'):
        result,tx=archive_attempt(ROOT/'campaigns/ordered_service_v30',name)
        require(result['model_artifact']['sha256']==policy.RETAINED_MODEL,'historical cold model differs')
        cols.append(tx['controller_elapsed_ns'])
    lossless,_=archive_attempt(ROOT/'campaigns/ordered_service_v30','repair-001')
    gate=read_json(pilot/'attempts/repair-128-48/scientific-gates.json')
    require(gate['all_passed'] is True and current['state_artifact']['bytes']<lossless['state_artifact']['bytes']
        and clock['controller_elapsed_ns']<min(cols),'archived V31 promotion screen failed')
    require(gate['checks']['latency']['actual_ns']==clock['controller_elapsed_ns']
        and gate['checks']['latency']['reference_ns']==min(cols)
        and gate['checks']['storage']['actual_bytes']==current['state_artifact']['bytes']
        and gate['checks']['storage']['reference_bytes']==lossless['state_artifact']['bytes'],'archived gate sidecar differs')
    quality=read_json(ROOT/'campaigns/quality_extensions_v30/attempts/matched-quality-128/outputs/completion.json')
    for key in ('matched_quality_gate_pass','development_safety_gate_pass','historical_control_parity_pass'):
        require(quality[key] is True,'historical quality screen failed')
    return dict(binding_sha256=BINDINGS_SHA256,metadata_files_checked=len(bindings['files']),
        historical_binary_outputs_reverified=False,source_sha256=program['source_sha256'],
        prior_gate=gate,scope=RECOVERY['historical_gate_scope'])


def build_spec(corpus):
    require(corpus in ('wikitext','c4'),'unknown corpus')
    original=read_json(ROOT/('campaigns/independent_requests_v31_ready/'+corpus+'.spec.json'))
    old_root=str(Path(original['campaign']).parents[1]);moved=relocate(original,old_root,ROOT)
    return dict(schema='fresh-independent-recovery-specification-v32',status='draft_unregistered',
        corpus=corpus,campaign=str(campaign(corpus)),workspace=WORKSPACE,confirmation=False,recovery=RECOVERY,
        phase_cpu_cap_seconds=1900,maximum_complete_reservations_seconds=1844,
        execution_order=moved['execution_order'],trials=moved['trials'],requests=moved['requests'],
        source_ids=moved['source_ids'],compressed_request_id=moved['compressed_request_id'],
        historical_bindings_sha256=BINDINGS_SHA256,
        registration_sequence=['independent_wikitext_v32','independent_c4_v32'],
        lifetime_limit=moved['lifetime_limit'],statistical_unit=moved['statistical_unit'])


def validate_design(spec, *, inputs=True):
    expected=build_spec(spec['corpus'])
    for name,value in expected.items():
        if name not in ('schema','status'):require(spec.get(name)==value,'recovery design differs: '+name)
    require(len(spec['trials'])==7 and sum(t['cpu_seconds']+2 for t in spec['trials'])==1844,'trial reservations differ')
    from scripts import run_ordered_service_v30 as ordered
    from scripts import run_compressed_service_v31 as compressed
    for i,trial in enumerate(spec['trials']):
        worker=ordered if i<5 else compressed
        worker.validate_policy(trial['plan'])
        static=trial['plan']['inputs'];late=trial.get('inputs_from_trial',{})
        require(not set(static)&set(late) and set(static)|set(late)==worker.required_inputs(trial['plan']['method']),
            'input capabilities differ')
        if inputs:
            for entry in static.values():check_file(entry)
        records=read_json(Path(static['records']['path']))
        worker.select_records(trial['plan'],records)
    return spec


def resource_admission(spec):
    recorded=read_json(ROOT/'campaigns/independent_requests_v31_ready/resource-admission.json')
    report=recorded['reports'][spec['corpus']]
    require(report['model_sha256']==policy.ORIGINAL_MODEL and report['neural_execution'] is False,'shape record differs')
    rows=report['reports'];by_id={row['trial']:row for row in rows}
    require(set(by_id)=={t['id'] for t in spec['trials'] if t['plan']['method']!='convert_lossless'},'shape trial set differs')
    for row in rows:
        point=row['point'];require(point['all_stages_admitted'] and point['request_admitted'],'point admission failed')
        require(len(point['stages'])==24 and point['request_cap']==96000000000,'shape coverage differs')
        if 'certificates' in row:
            require(len(row['certificates'])==24 and all(r['admitted'] for r in row['certificates']),'certificate admission failed')
    return dict(historical_shape_record_sha256=hashed(ROOT/'campaigns/independent_requests_v31_ready/resource-admission.json'),
        reports=rows,neural_execution=False,scope='Pinned unchanged 24-stage shape admission only; no acceptance, runtime, or whole-process memory guarantee.')


def registered_program(directory):
    directory=Path(directory);raw=(directory/'program.json').read_bytes();protocol=(directory/'protocol.json').read_bytes()
    program=json.loads(raw);registration=read_json(directory/'registration.json')
    require(registration['program_sha256']==digest(raw) and registration['protocol_sha256']==digest(protocol)
        and json.loads(protocol)['program_sha256']==digest(raw),'registration binding differs')
    require(source_hashes(directory/'source')==program['source_sha256'],'registered frozen source differs')
    return program,raw,protocol,registration


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
    evidence_checks.verify_worker_schedule(current,trial,transaction,identity,registration,program)
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
    expected_campaign='independent-'+program['corpus']+'-v32'
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



def register(corpus):
    current=campaign(corpus)
    require(not current.exists(),'registration exists; no overwrite or allowance reset')
    if corpus=='wikitext':require(not campaign('c4').exists(),'successor root exists before fresh WikiText registration')
    spec=build_spec(corpus);historical=archive_evidence();validate_design(spec)
    if corpus=='c4':
        earlier=campaign('wikitext');old,_,proto,_=registered_program(earlier)
        receipts=[]
        for trial in old['trials']:
            completed(earlier,trial['id']);receipts.append(read_json(earlier/'attempts'/trial['id']/'worker/result.json'))
        evidence_checks.verify_final_budget(earlier,old,digest(proto),receipts)
    admission=resource_admission(spec)
    source=current/'source'
    for folder in ('src','scripts'):
        (source/folder).mkdir(parents=True)
        for path in sorted((ROOT/folder).glob('*.py')):shutil.copyfile(path,source/folder/path.name)
    program=dict(spec,schema='bounded-independent-recovery-program-v32',status='prospectively_registered',
        source_sha256=source_hashes(source),controller_sha256={p:hashed(ROOT/p) for p in CONTROLLERS},
        historical_evidence=historical,resource_admission=admission,historical_frozen_ledgers=historical_ledgers(current),
        affinity_cpus=[min(os.sched_getaffinity(0))],address_space_bytes=6*2**30,
        primary_clock='controller after prerequisite/bootstrap checks through worker receipt and receipt hash',
        secondary_clock='nested worker and service clocks; never add to primary clock',
        authorization='user requested recovery and continued experiments; bounded local CPU only; no paid compute',
        registered_from_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    raw=canonical_json(program);protocol=canonical_json(dict(schema='bounded-independent-recovery-policy-v32',
        program_sha256=digest(raw),phase_cpu_seconds={'feasibility':1900}))
    atomic_write(current/'program.json',raw);atomic_write(current/'protocol.json',protocol)
    atomic_write(current/'registration.json',canonical_json(dict(program_sha256=digest(raw),protocol_sha256=digest(protocol),runtime=capture_runtime_contract())))
    atomic_write(current/'registered-launcher.py',Path(__file__).read_bytes())
    return dict(registered=True,corpus=corpus,trials=7,max_complete_reservations=1844,phase_cpu_cap=1900)


def check_registered(corpus):
    current=campaign(corpus);program,raw,protocol,registration=registered_program(current)
    require({p:hashed(ROOT/p) for p in CONTROLLERS}==program['controller_sha256'],'controller changed')
    require(historical_ledgers(current)==program['historical_frozen_ledgers'],'historical ledger changed')
    require(capture_runtime_contract()==registration['runtime'],'runtime changed')
    require(archive_evidence()==program['historical_evidence'],'historical evidence changed')
    validate_design(program)
    return current,program,raw,protocol,registration


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
    path=attempt/'plan.json';atomic_write(path,canonical_json(plan));source=current/'source'
    receipt=run_limited([sys.executable,str(source/'scripts'/trial['script']),str(path)],attempt/'worker',
        WorkerLimits(trial['wall_seconds'],trial['cpu_seconds'],6*2**30,1,tuple(program['affinity_cpus'])),
        identity={'campaign':'independent-'+corpus+'-v32','plan_sha256':digest(path.read_bytes())},
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


def validate_workspace(value):
    if value is None:return None
    path=Path(value)
    require(not path.is_absolute() and len(path.parts)>=2 and path.parts[0]=='local_runs'
        and '..' not in path.parts and '.' not in path.parts and str(path)==value,
        'workspace must be a normalized relative path below local_runs')
    target=ROOT/path
    require(not any(p.is_symlink() for p in (target,*target.parents)), 'workspace must not contain symlinks')
    require(not target.exists() or target.is_dir(),'workspace is not a directory')
    return value


def main():
    global WORKSPACE
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--corpus',choices=('wikitext','c4'),required=True)
    parser.add_argument('--workspace',help='fresh separate replay namespace, such as local_runs/replay-001')
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--register',action='store_true');action.add_argument('--run')
    action.add_argument('--run-next',action='store_true');action.add_argument('--status',action='store_true')
    action.add_argument('--preflight',action='store_true')
    args=parser.parse_args();WORKSPACE=validate_workspace(args.workspace)
    with research_worker_lock(ROOT):
        if args.preflight:
            evidence=archive_evidence();spec=validate_design(build_spec(args.corpus));admission=resource_admission(spec)
            output=dict(corpus=args.corpus,preflight=True,archive_metadata_files=evidence['metadata_files_checked'],
                trials=len(spec['trials']),numerical_sources_match=True,admission=admission)
        elif args.register:output=register(args.corpus)
        elif args.status:output=status(args.corpus)
        elif args.run_next:
            checked=status(args.corpus)
            require(checked.get('registered') is True,'register the fresh root first')
            require(not checked.get('blocked'),'existing incomplete attempt blocks admission')
            output=checked if checked['complete'] else run(args.corpus,checked['next_trial'])
        else:output=run(args.corpus,args.run)
    print(json.dumps(output,sort_keys=True))
    if args.run or args.run_next:
        if output.get('status') not in (None,'complete') or output.get('blocked'):
            raise SystemExit(1)


if __name__=='__main__':main()
