"""Freeze and execute one contingent V31 independent development root at a time.

Registration requires completed matched quality and a successful compressed
pilot. Importing this module or validating a draft launches no worker.
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
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import launch_compressed_service_v31 as prior_launcher
from scripts import prepare_independent_campaigns_v31 as preparation
from scripts import analyze_full_service_v30 as evidence_checks
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget, read_budget_snapshot
from src.pilot_budget import research_worker_lock
from src.run_store import atomic_write, canonical_json, digest
from src.runtime_contract import capture_runtime_contract
from src.service_terminal_evidence_v30 import verify_completed
from src.worker_control import WorkerLimits, run_limited

CONTROLLERS = ('scripts/launch_independent_requests_v31.py', 'scripts/prepare_independent_campaigns_v31.py',
    'scripts/analyze_full_service_v30.py',
    'scripts/launch_compressed_service_v31.py', 'src/worker_control.py',
    'src/phase_budget.py', 'src/run_store.py', 'src/pilot_budget.py',
    'src/runtime_contract.py', 'src/experiment_inventory.py', 'src/service_terminal_evidence_v30.py')
POLICY_FIELDS = ('decoder_backend', 'codec_bits', 'block_size', 'solver_backend', 'solver_budget',
    'sparse_budget', 'certificate_backend', 'max_certificate_work_units',
    'max_certificate_workspace_bytes', 'max_point_work_units', 'max_neural_stage_record_pairs',
    'use_candidates', 'original_token_count', 'expected_target')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def campaign(corpus):
    require(corpus in ('wikitext', 'c4'), 'unknown independent corpus')
    return ROOT/('campaigns/independent_'+corpus+'_v31')


def hashed(path):
    path = Path(path)
    require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), 'symbolic path refused')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def historical_ledgers(current):
    return {str(p.relative_to(ROOT)):hashed(p) for base in ('pilots', 'campaigns')
        for p in sorted((ROOT/base).glob('**/phase-cpu-budget/ledger.json')) if current not in p.parents}


def check_file(entry):
    require(type(entry) is dict and set(entry) in ({'path','sha256'}, {'path','sha256','bytes'}), 'invalid file binding')
    path = Path(entry['path'])
    require(path.is_absolute() and hashed(path) == entry['sha256'], 'bound file changed')
    if 'bytes' in entry:
        require(type(entry['bytes']) is int and path.stat().st_size == entry['bytes'], 'bound file size changed')
    return path


def registered_program(directory):
    directory = Path(directory)
    raw, protocol = (directory/'program.json').read_bytes(), (directory/'protocol.json').read_bytes()
    program, registration = json.loads(raw), json.loads((directory/'registration.json').read_bytes())
    require(registration['program_sha256'] == digest(raw)
        and registration['protocol_sha256'] == digest(protocol)
        and json.loads(protocol)['program_sha256'] == digest(raw), 'registration binding differs')
    require(source_hashes(directory/'source') == program['source_sha256'], 'registered frozen source differs')
    return program, raw, protocol, registration


def verify_pilot_contract(program):
    """Reject a numerically identical pilot with weaker comparison gates."""
    reviewed,_ = preparation.checked_json(ROOT/'campaigns/compressed_service_v31.spec.json',
        preparation.COMPRESSED_POLICY_SHA256)
    require(program.get('draft_specification_sha256') == preparation.COMPRESSED_POLICY_SHA256,
        'pilot is not bound to the reviewed draft')
    require(len(program['trials']) == len(reviewed['trials']), 'pilot trial count differs')
    for actual,expected in zip(program['trials'],reviewed['trials']):
        for field in ('id','script','storage_gate','latency_gate','compare_external','compare_to'):
            require(actual.get(field) == expected.get(field), 'reviewed pilot gate differs: '+field)
    external=prior_launcher.checked_external(program['external_attempts'],require_bindings=True)
    require(program['trials'] == prior_launcher.resolve_external_trials(reviewed['trials'],external),
        'registered pilot trials differ from resolved reviewed draft')


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
    expected_campaign='research-v30' if current==prior_launcher.C else 'independent-'+program['corpus']+'-v31'
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


def prerequisites(spec, *, frozen=False):
    for entry in spec['prerequisite_files'].values():
        check_file(entry)
    external = prior_launcher.checked_external(spec['external_attempts'], require_bindings=frozen)
    equalities = prior_launcher.verify_external_equalities(external, spec['external_equalities'])
    gate = spec['prerequisite_scientific_gate']
    directory = Path(gate['campaign'])
    require(directory == prior_launcher.C and gate.get('all_passed') is True,
        'scientific prerequisite must identify the reviewed compressed pilot')
    program, raw, protocol, registration = registered_program(directory)
    verify_pilot_contract(program)
    require({p:hashed(ROOT/p) for p in prior_launcher.CONTROLLERS} == program['controller_sha256'],
        'prerequisite scientific gate controller changed')
    require(source_hashes(ROOT) == program['source_sha256'],
        'current numerical sources differ from the successful V31 pilot')
    require(capture_runtime_contract() == registration['runtime'],
        'current runtime differs from the successful V31 pilot')
    verify_registered_attempt(directory,gate['trial'])
    result = prior_launcher.completed(gate['trial'])
    require(result['registered_scientific_gates']['all_passed'] is True,
        'compressed scientific prerequisite failed; preserve and do not expand')
    policy = spec['prerequisite_policy']
    require(Path(policy['campaign']) == directory and policy['trial'] == gate['trial']
        and set(policy['fields']) == set(POLICY_FIELDS), 'incomplete successful-pilot policy binding')
    old_trial = next(row for row in program['trials'] if row['id'] == policy['trial'])
    repair = next(row for row in spec['trials'] if row['script'] == 'run_compressed_service_v31.py'
        and row['plan']['method'] == 'repair')
    require(all(repair['plan'][field] == old_trial['plan'][field] for field in POLICY_FIELDS),
        'independent compressed numerical policy differs from successful prerequisite')
    observed = dict(program_sha256=digest(raw), protocol_sha256=digest(protocol),
        completion_sha256=hashed(directory/'attempts'/gate['trial']/'outputs/completion.json'),
        transaction_sha256=hashed(directory/'attempts'/gate['trial']/'transaction.json'),
        scientific_gates=result['registered_scientific_gates'],
        source_sha256=program['source_sha256'], runtime=registration['runtime'],
        policy={field:old_trial['plan'][field] for field in POLICY_FIELDS})
    if frozen:
        require(spec['prerequisite_scientific_evidence'] == observed, 'frozen scientific prerequisite changed')
    return external, equalities, observed


def validate_design(spec):
    require(spec.get('schema') in ('independent-request-campaign-specification-v31', 'bounded-independent-program-v31')
        and spec.get('confirmation') is False, 'independent draft schema or phase differs')
    corpus = spec['corpus']
    require(Path(spec['campaign']) == campaign(corpus), 'independent campaign destination differs')
    require(spec['phase_cpu_cap_seconds'] == 1900, 'independent root must preserve its 1900-second cap')
    draft = json.loads(check_file(spec['prerequisite_files']['draft']).read_bytes())
    old_root = next(row for row in draft['roots'] if row['corpus'] == corpus)
    trials = spec['trials']
    require(len(trials) == 7 and trials[:5] == old_root['point_trials'], 'selected point plans or balanced order changed')
    require(spec['execution_order'] == [row['id'] for row in trials], 'complete execution order differs')
    require(sum(row['cpu_seconds']+2 for row in trials) == 1844, 'complete reservations must remain 1844 seconds')
    require([row['plan']['method'] for row in trials[5:]] == ['convert_lossless','repair'], 'compressed trial order differs')
    records_path = check_file(spec['prerequisite_files']['records'])
    require(records_path == Path(old_root['records']['path']) and hashed(records_path) == old_root['records']['sha256'],
        'selected source tokens changed')
    records = json.loads(records_path.read_bytes())
    from scripts import run_ordered_service_v30 as ordered
    from scripts import run_compressed_service_v31 as compressed
    known = set(); checked_inputs = set()
    for index, trial in enumerate(trials):
        name = trial['id']
        require(type(name) is str and name and name.replace('-','').isalnum() and name not in known, 'invalid trial identifier')
        worker = ordered if index < 5 else compressed
        require(trial['script'] == ('run_ordered_service_v30.py' if index < 5 else 'run_compressed_service_v31.py'),
            'unexpected worker family')
        worker.validate_policy(trial['plan']); worker.select_records(trial['plan'], records)
        immediate = set(trial['plan']['inputs']); late = set(trial.get('inputs_from_trial', {}))
        require(not immediate & late and immediate | late == worker.required_inputs(trial['plan']['method']),
            'prospective input access differs or delayed input overwrites a bound file')
        require(trial['plan']['inputs']['records']['sha256'] == old_root['records']['sha256'], 'record input differs')
        for entry in trial['plan']['inputs'].values():
            signature=(entry['path'],entry['sha256'],entry.get('bytes'))
            if signature not in checked_inputs:
                check_file(entry);checked_inputs.add(signature)
        for entry in list(trial.get('depends', []))+list(trial.get('inputs_from_trial', {}).values())+trial.get('compare_to', []):
            require(entry['trial'] in known, 'dependency or comparison must name a previous trial')
        require(type(trial['cpu_seconds']) is int and 1 <= trial['cpu_seconds'] <= 900
            and type(trial['wall_seconds']) is int and 1 <= trial['wall_seconds'] <= 1200, 'invalid transaction limits')
        known.add(name)
    original_ids = old_root['source_ids']
    require(trials[5]['plan']['record_ids'] == original_ids and trials[5]['plan']['deleted_ids'] == [],
        'conversion must use original selected sources')
    selected = old_root['requests'][0]
    require(trials[6]['plan']['record_ids'] == selected['retained_ids']
        and trials[6]['plan']['deleted_ids'] == selected['deleted_ids'], 'compressed request selection changed')
    require(trials[5]['cpu_seconds'] == 120 and trials[5]['wall_seconds'] == 180
        and trials[6]['cpu_seconds'] == 300 and trials[6]['wall_seconds'] == 420, 'compressed abort ceilings changed')
    # Bind the complete derivative design, including fresh preparation edges and
    # scientific comparators. Parser-valid substitutions are not a new protocol.
    expected = preparation.build(ROOT)[corpus]
    for key, value in expected.items():
        if key in ('schema', 'status', 'external_attempts'):
            continue
        require(spec.get(key) == value, 'prospective V31 design changed: '+key)
    require(set(spec['external_attempts']) == set(expected['external_attempts']),
        'prospective V31 external evidence set changed')
    for name, entry in expected['external_attempts'].items():
        require(all(spec['external_attempts'][name].get(key) == value for key, value in entry.items()),
            'prospective V31 prerequisite changed: '+name)
    return old_root


def resource_admission(spec, external):
    from src.compact_state import parse
    from scripts.run_ordered_service_v30 import preflight_stages
    from src.adaptive_calibration_v30 import AdaptiveBudget
    from src.sparse_box_certificate_v31 import SparseCertificateBudget
    from src.native_box_compressed_service_v31 import assess_compressed_routes
    parent = external[spec['resource_shape_reference']]
    artifact = parent['verified_artifacts']['model']
    model = parse((Path(parent['attempt'])/'outputs'/artifact['file']).read_bytes(),expected_sha256=artifact['sha256'])
    require(len(model.stages) == 24, 'shape reference must be complete')
    stages = [SimpleNamespace(stage_id=s.stage_id,width=s.columns,weights=[None]*s.rows) for s in model.stages]
    records = json.loads(check_file(spec['prerequisite_files']['records']).read_bytes())['records']
    reports = []
    for trial in spec['trials']:
        plan=trial['plan']; method=plan['method']
        if method == 'convert_lossless':continue
        tokens=sum(len(row['tokens']) for row in records if row['id'] in plan['record_ids'])
        budget=AdaptiveBudget(**plan['solver_budget'])
        report=dict(trial=trial['id'],tokens=tokens,point=preflight_stages(stages,tokens,budget=budget,
            route=plan['solver_backend'],max_point_work_units=plan['max_point_work_units']))
        if trial['script'] == 'run_compressed_service_v31.py':
            remaining=plan['max_certificate_work_units'];certificates=[]
            for stage in model.stages:
                routes=assess_compressed_routes(stage.rows,stage.columns,tokens,bits=stage.bits,coefficient_budget=budget,
                    sparse_budget=SparseCertificateBudget(**plan['sparse_budget']),remaining_work=remaining,
                    max_certificate_workspace_bytes=plan['max_certificate_workspace_bytes'])
                chosen=routes['routes'][plan['certificate_backend']]
                require(chosen['admitted'],'known certificate resource refusal before registration')
                certificates.append(dict(stage_id=stage.stage_id,**chosen));remaining-=chosen['work_units_reserved']
            report['certificates']=certificates
        reports.append(report)
    return dict(model_sha256=artifact['sha256'],reports=reports,neural_execution=False,
        scope='shape admission only; no certificate acceptance, whole-process memory, or elapsed-speed guarantee')


def register(spec_path, corpus):
    current=campaign(corpus)
    require(not current.exists(),'registration exists; no overwrite or allowance reset')
    spec=json.loads(Path(spec_path).read_bytes())
    require(spec.get('status') == 'draft_unregistered','registration needs an unregistered draft')
    require(spec['corpus'] == corpus,'CLI corpus differs from specification')
    validate_design(spec)
    external,equalities,scientific=prerequisites(spec)
    # Freeze one root at a time; the second root snapshots the settled first ledger.
    if corpus == 'c4':
        earlier=campaign('wikitext')
        old,_,_,_=registered_program(earlier)
        for trial in old['trials']:completed(earlier,trial['id'])
        ledger=json.loads((earlier/'phase-cpu-budget/ledger.json').read_bytes())
        require(all(row['state']=='settled' for row in ledger['attempts'].values()),'previous independent root is unsettled')
    admission=resource_admission(spec,external)
    source=current/'source'
    for folder in ('src','scripts'):
        (source/folder).mkdir(parents=True)
        for path in sorted((ROOT/folder).glob('*.py')):shutil.copyfile(path,source/folder/path.name)
    program=dict(spec,schema='bounded-independent-program-v31',status='prospectively_registered',
        source_sha256=source_hashes(source),controller_sha256={p:hashed(ROOT/p) for p in CONTROLLERS},
        external_attempts=external,external_equality_checks=equalities,prerequisite_scientific_evidence=scientific,
        resource_admission=admission,historical_frozen_ledgers=historical_ledgers(current),
        draft_specification_sha256=hashed(spec_path),affinity_cpus=[min(os.sched_getaffinity(0))],address_space_bytes=6*2**30,
        primary_clock='controller after prerequisite/bootstrap checks through worker receipt and receipt hash',
        secondary_clock='nested worker and service clocks; never add to primary clock',
        budget_policy='1900 seconds for this root only; no pooling, reset, automatic retries, or source replacements',
        authorization='user requested continued complete program; bounded local development only; no paid compute',
        registered_from_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    raw=canonical_json(program);protocol=canonical_json(dict(schema='bounded-independent-policy-v31',
        program_sha256=digest(raw),phase_cpu_seconds={'feasibility':1900}))
    atomic_write(current/'program.json',raw);atomic_write(current/'protocol.json',protocol)
    atomic_write(current/'registration.json',canonical_json(dict(program_sha256=digest(raw),protocol_sha256=digest(protocol),runtime=capture_runtime_contract())))
    atomic_write(current/'registered-launcher.py',Path(__file__).read_bytes())
    print(json.dumps(dict(registered=True,corpus=corpus,trials=7,max_complete_reservations=1844,phase_cpu_cap=1900)))


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


def run(corpus, trial_id):
    current=campaign(corpus);program,raw,protocol,registration=registered_program(current)
    require({p:hashed(ROOT/p) for p in CONTROLLERS}==program['controller_sha256'],'controller changed')
    require(historical_ledgers(current)==program['historical_frozen_ledgers'],'historical ledger changed')
    require(capture_runtime_contract()==registration['runtime'],'runtime changed')
    prerequisites(program,frozen=True);validate_design(program)
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
        identity={'campaign':'independent-'+corpus+'-v31','plan_sha256':digest(path.read_bytes())},
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
    print(json.dumps(dict(corpus=corpus,trial=trial_id,status=receipt['outcome']['status'],controller_seconds=elapsed/1e9,
        scientific_gates=gates,phase_charge=budget.snapshot()['charged_cpu_seconds']['feasibility'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--corpus',choices=('wikitext','c4'),required=True)
    action=parser.add_mutually_exclusive_group(required=True);action.add_argument('--register',type=Path);action.add_argument('--run')
    args=parser.parse_args()
    with research_worker_lock(ROOT):
        register(args.register,args.corpus) if args.register else run(args.corpus,args.run)
