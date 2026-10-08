"""Freeze the compressed pilot after complete ordered and quality prerequisites."""
import argparse
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
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.pilot_budget import research_worker_lock
from src.run_store import atomic_write, canonical_json, digest
from src.runtime_contract import capture_runtime_contract
from src.worker_control import WorkerLimits, run_limited

C = ROOT / 'campaigns/compressed_service_v30'
CONTROLLERS = ('scripts/launch_compressed_service_v30.py', 'src/worker_control.py',
    'src/phase_budget.py', 'src/run_store.py', 'src/pilot_budget.py',
    'src/runtime_contract.py', 'src/experiment_inventory.py', 'src/service_terminal_evidence_v30.py')


def hashed(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def historical_ledgers():
    return {str(p.relative_to(ROOT)): hashed(p)
            for base in ('pilots', 'campaigns')
            for p in sorted((ROOT/base).glob('**/phase-cpu-budget/ledger.json'))
            if C not in p.parents}


def checked_external(specification, *, require_bindings=False):
    """Verify external evidence without changing the original experiment."""
    from src.service_terminal_evidence_v30 import verify_completed
    checked = {}
    for key, entry in specification.items():
        attempt = Path(entry['attempt'])
        if not attempt.is_absolute():
            raise ValueError('external attempts require absolute paths')
        result = verify_completed(attempt)
        for field, expected in entry.get('equals', {}).items():
            value = result
            for part in field.split('.'):
                value = value[part]
            if value != expected:
                raise ValueError('external prerequisite differs: '+key+'/'+field)
        evidence = {}
        for name in ('plan.json', 'transaction.json', 'sealed-progress.json',
                     'outputs/completion.json', 'outputs/progress.json', 'worker/result.json'):
            path = attempt/name
            evidence[name] = dict(sha256=hashed(path), bytes=path.stat().st_size)
        if require_bindings and evidence != entry['evidence']:
            raise ValueError('registered external evidence changed: '+key)
        checked[key] = dict(entry, evidence=evidence,
            completion_sha256=evidence['outputs/completion.json']['sha256'],
            verified_artifacts=result['artifacts'])
    return checked


def resolve_external_trials(trials, external):
    """Resolve only prospective references to verified completed attempts."""
    resolved = json.loads(json.dumps(trials))
    for trial in resolved:
        plan = trial['plan']
        plan['inputs'] = dict(plan.get('inputs', {}))
        for key, binding in trial.get('inputs_from_external', {}).items():
            if key in plan['inputs']:
                raise ValueError('external input would replace a registered input')
            parent = external[binding['external']]
            attempt = Path(parent['attempt'])
            if binding.get('completion') is True:
                path = attempt/'outputs/completion.json'
                entry = parent['evidence']['outputs/completion.json']
            else:
                artifact = parent['verified_artifacts'][binding['artifact']]
                if Path(artifact['file']).name != artifact['file']:
                    raise ValueError('unsafe external artifact filename')
                path = attempt/'outputs'/artifact['file']
                entry = {k:artifact[k] for k in ('sha256','bytes')}
            plan['inputs'][key] = dict(path=str(path), sha256=entry['sha256'])
        for key, binding in trial.get('plan_from_external', {}).items():
            if key in plan:
                raise ValueError('external field would replace a registered plan field')
            parent = external[binding['external']]
            value = json.loads((Path(parent['attempt'])/'outputs/completion.json').read_bytes())
            for part in binding['field'].split('.'):
                value = value[part]
            plan[key] = value
    return resolved


def verify_external_equalities(external, comparisons):
    records = []
    for comparison in comparisons:
        left = external[comparison['left']]['verified_artifacts']
        right = external[comparison['right']]['verified_artifacts']
        for artifact in comparison.get('artifacts', ['model']):
            a, b = left[artifact], right[artifact]
            equal = a['sha256'] == b['sha256'] and a['bytes'] == b['bytes']
            records.append(dict(left=comparison['left'],right=comparison['right'],artifact=artifact,equal=equal))
            if not equal:
                raise ValueError('external original/ordered complete models disagree')
    return records


def validate_trial_access(trial):
    from scripts.run_compressed_service_v30 import validate_policy, required_inputs
    if trial['script'] != 'run_compressed_service_v30.py':
        raise ValueError('compressed campaign requires its reviewed worker')
    validate_policy(trial['plan'])
    immediate = set(trial['plan'].get('inputs', {}))
    late = set(trial.get('inputs_from_trial', {}))
    external = set(trial.get('inputs_from_external', {}))
    if (immediate | external) & late:
        raise ValueError('late input would replace a registered input')
    if immediate | late | external != required_inputs(trial['plan']['method']):
        raise ValueError('complete prospective input capability set differs from worker')


def assess_pilot_resources(trials, external):
    """Use verified archived model shapes; no checkpoint load or neural execution."""
    from scripts.run_compressed_service_v30 import select_records, validate_policy, preflight_stages
    from src.compact_state import parse
    from src.ordered_compressed_service_v30 import assess_compressed_routes
    parent = external['original']
    artifact = parent['verified_artifacts']['model']
    model = parse((Path(parent['attempt'])/'outputs'/artifact['file']).read_bytes(),
        expected_sha256=artifact['sha256'])
    if len(model.stages) != 24:
        raise ValueError('resource audit requires the complete archived model')
    stages = [SimpleNamespace(stage_id=s.stage_id,width=s.columns,weights=[None]*s.rows) for s in model.stages]
    reports = []
    for trial in trials:
        plan = trial['plan']
        validate_trial_access(trial)
        point_budget, sparse_budget = validate_policy(plan)
        _, retained = select_records(plan, json.loads(Path(plan['inputs']['records']['path']).read_bytes()))
        if plan['method'] == 'convert_lossless':
            reports.append(dict(trial=trial['id'],method=plan['method'],neural_execution=False,conversion_only=True))
            continue
        if plan['decoder_backend'] != 'ordered':
            raise ValueError('this prospective pilot requires the matched ordered backend')
        tokens = sum(len(row['tokens']) for row in retained)
        point = preflight_stages(stages,tokens,budget=point_budget,route=plan['solver_backend'],
            max_point_work_units=plan['max_point_work_units'])
        remaining = plan['max_certificate_work_units']
        certificates = []
        for stage in model.stages:
            admission = assess_compressed_routes(stage.rows,stage.columns,tokens,bits=stage.bits,
                coefficient_budget=point_budget,sparse_budget=sparse_budget,remaining_work=remaining,
                max_certificate_workspace_bytes=plan['max_certificate_workspace_bytes'])
            route = admission['selected'] if plan['certificate_backend'] == 'auto' else plan['certificate_backend']
            if route is None or not admission['routes'][route]['admitted']:
                raise ValueError('known certificate admission refusal: '+stage.stage_id)
            chosen = admission['routes'][route]
            certificates.append(dict(stage_id=stage.stage_id,route=route,**chosen))
            remaining -= chosen['work_units_reserved']
        reports.append(dict(trial=trial['id'],method=plan['method'],retained_tokens=tokens,neural_execution=False,
            point=point,certificates=certificates,all_certificate_stages_admitted=True,
            certificate_work_units_reserved=plan['max_certificate_work_units']-remaining))
    return dict(model_sha256=artifact['sha256'],stage_count=24,reports=reports,
        scope='structural admission only; no certificate acceptance, whole-process memory, or speed guarantee')


def scientific_gates(trial, result, external, transaction=None):
    """A failed scientific gate remains a completed, preserved numerical result."""
    gates = {}
    policy = trial.get('storage_gate')
    if policy is not None:
        if policy.get('strictly_smaller') is not True:
            raise ValueError('storage gate must explicitly require strictly smaller complete state')
        kind = policy['artifact']
        actual = result['artifacts'][kind]
        reference = external[policy['external']]['verified_artifacts'][kind]
        gates['storage'] = dict(passed=actual['bytes'] < reference['bytes'],actual_bytes=actual['bytes'],
            reference_bytes=reference['bytes'],reference_sha256=reference['sha256'],
            scope='complete state; common base checkpoint and audit archive excluded')
    policy = trial.get('latency_gate')
    if policy is not None:
        if policy.get('strictly_faster') is not True or transaction is None:
            raise ValueError('latency gate requires the complete current transaction')
        references = policy.get('externals')
        if (type(references) is not list or not references or len(set(references)) != len(references)
            or policy.get('aggregation') != 'minimum_recorded_controller_elapsed_ns'):
            raise ValueError('latency gate requires unique references and an explicit minimum policy')
        observed = []
        for key in references:
            parent = external[key]
            path = Path(parent['attempt'])/'transaction.json'
            expected_sha = parent['evidence']['transaction.json']['sha256']
            if hashed(path) != expected_sha:
                raise ValueError('reference latency evidence changed')
            elapsed = json.loads(path.read_bytes())['controller_elapsed_ns']
            if type(elapsed) is not int or elapsed <= 0:
                raise ValueError('latency gate requires observed positive controller clocks')
            observed.append(dict(external=key,controller_elapsed_ns=elapsed,transaction_sha256=expected_sha))
        reference_ns = min(row['controller_elapsed_ns'] for row in observed)
        actual_ns = transaction['controller_elapsed_ns']
        if type(actual_ns) is not int or actual_ns <= 0:
            raise ValueError('latency gate requires observed positive controller clocks')
        gates['latency'] = dict(passed=actual_ns < reference_ns,actual_ns=actual_ns,reference_ns=reference_ns,
            references=observed,aggregation=policy['aggregation'],
            scope='conservative pilot promotion screen against fastest registered cold; not a confidence interval; current evidence verification included')
    return dict(checks=gates,all_passed=all(row['passed'] for row in gates.values()))


def register(spec_path):
    if C.exists():
        raise ValueError('registration exists; cannot overwrite it')
    spec = json.loads(Path(spec_path).read_bytes())
    if spec.get('status') != 'draft_unregistered' or spec.get('confirmation') is not False:
        raise ValueError('extension registration requires an explicit unregistered development specification')
    external = checked_external(spec['external_attempts'])
    spec['external_equality_checks'] = verify_external_equalities(external, spec.get('external_equalities', []))
    spec['external_attempts'] = external
    spec['trials'] = resolve_external_trials(spec['trials'], external)
    quality = spec.get('quality_prerequisite')
    if quality is not None:
        from src.service_terminal_evidence_v30 import verify_completed
        if hashed(quality['path']) != quality['sha256']:
            raise ValueError('quality prerequisite binding differs')
        checked = verify_completed(Path(quality['path']).parent.parent)
        if checked.get('development_quality_gate_pass') is not True or checked.get('historical_parity_pass') is not True:
            raise ValueError('registered quality prerequisite did not pass')
    cap = spec['phase_cpu_cap_seconds']
    if type(cap) is not int or not 1 <= cap <= 3600:
        raise ValueError('local phase requires a positive cap no larger than 3600 seconds')
    trials = spec['trials']
    known = set()
    for trial in trials:
        name = trial['id']
        if not name or not name.replace('-', '').isalnum() or name in known:
            raise ValueError('invalid trial name')
        if not trial['script'].startswith('run_') or Path(trial['script']).name != trial['script']:
            raise ValueError('worker must name a local run script')
        for dependency in trial.get('depends', []):
            if dependency['trial'] not in known:
                raise ValueError('dependency must precede trial')
        if not 1 <= trial['cpu_seconds'] <= 900 or not 1 <= trial['wall_seconds'] <= 1200:
            raise ValueError('invalid per-worker resource limit')
        for entry in trial['plan'].get('inputs', {}).values():
            if set(entry) not in ({'path', 'sha256'}, {'path', 'sha256', 'bytes'}) or hashed(entry['path']) != entry['sha256']:
                raise ValueError('input binding differs')
            if 'bytes' in entry and Path(entry['path']).stat().st_size != entry['bytes']:
                raise ValueError('input size differs')
        for binding in trial.get('inputs_from_trial', {}).values():
            if binding['trial'] not in known:
                raise ValueError('late input must name an earlier registered trial')
        for comparison in trial.get('compare_to', []):
            if comparison['trial'] not in known:
                raise ValueError('comparison must name an earlier registered trial')
        for comparison in trial.get('compare_external', []):
            if comparison['external'] not in external:
                raise ValueError('unknown external comparison')
        validate_trial_access(trial)
        if trial.get('storage_gate') is not None:
            gate = trial['storage_gate']
            if gate['external'] not in external or gate['artifact'] not in external[gate['external']]['verified_artifacts']:
                raise ValueError('storage gate lacks a verified reference artifact')
        if trial.get('latency_gate') is not None:
            gate = trial['latency_gate']
            references = gate.get('externals')
            if (type(references) is not list or not references or len(set(references)) != len(references)
                or any(key not in external for key in references)
                or gate.get('aggregation') != 'minimum_recorded_controller_elapsed_ns'
                or gate.get('strictly_faster') is not True):
                raise ValueError('latency gate lacks unique verified references and explicit minimum policy')
        known.add(name)
    spec['resource_admission'] = assess_pilot_resources(trials, external)
    source = C/'source'
    for folder in ('src', 'scripts'):
        (source/folder).mkdir(parents=True)
        for path in sorted((ROOT/folder).glob('*.py')):
            shutil.copyfile(path, source/folder/path.name)
    program = dict(spec, schema='bounded-research-program-v30',
        status='prospectively_registered', source_sha256=source_hashes(source),
        controller_sha256={p:hashed(ROOT/p) for p in CONTROLLERS},
        historical_frozen_ledgers=historical_ledgers(),
        authorization='user requested complete everything; bounded local development only; no paid compute',
        budget_policy='new separate internal phase; no old ledger reset or pooling',
        primary_clock='controller after input/bootstrap checks through worker receipt and receipt hash',
        secondary_clock='nested worker and body clocks; never added to primary clock',
        confirmation=False, os_cache='uncontrolled', other_activity='uncontrolled',
        affinity_cpus=[min(os.sched_getaffinity(0))], address_space_bytes=6*2**30,
        registered_from_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    program['draft_specification_sha256'] = hashed(spec_path)
    raw = canonical_json(program)
    atomic_write(C/'program.json', raw)
    protocol = canonical_json(dict(schema='bounded-research-policy-v30',
        program_sha256=digest(raw), phase_cpu_seconds={'feasibility':cap}))
    atomic_write(C/'protocol.json', protocol)
    atomic_write(C/'registration.json', canonical_json(dict(
        program_sha256=digest(raw), protocol_sha256=digest(protocol), runtime=capture_runtime_contract())))
    atomic_write(C/'registered-launcher.py', Path(__file__).read_bytes())
    print(json.dumps(dict(registered=True, program_sha256=digest(raw), trials=len(trials), cpu_cap=cap)))


def completed(trial_id):
    from src.service_terminal_evidence_v30 import verify_completed
    attempt = C/'attempts'/trial_id
    result = verify_completed(attempt)
    program = json.loads((C/'program.json').read_bytes())
    positions = {trial['id']:position for position,trial in enumerate(program['trials'])}
    if trial_id not in positions:
        raise ValueError('completed trial is absent from the registered program')
    trial = program['trials'][positions[trial_id]]
    comparisons = []
    for comparison in trial.get('compare_to', []):
        reference_id = comparison['trial']
        if reference_id not in positions or positions[reference_id] >= positions[trial_id]:
            raise ValueError('comparison must reference an earlier registered trial')
        reference = verify_completed(C/'attempts'/reference_id)
        for artifact in comparison.get('artifacts', ['model']):
            left, right = result['artifacts'][artifact], reference['artifacts'][artifact]
            equal = left['sha256'] == right['sha256'] and left['bytes'] == right['bytes']
            comparisons.append(dict(reference_trial=reference_id,artifact=artifact,equal=equal,
                actual_sha256=left['sha256'],reference_sha256=right['sha256']))
    external = checked_external(program['external_attempts'], require_bindings=True)
    verify_external_equalities(external, program.get('external_equalities', []))
    for comparison in trial.get('compare_external', []):
        reference = external[comparison['external']]['verified_artifacts']
        for artifact in comparison.get('artifacts', ['model']):
            left, right = result['artifacts'][artifact], reference[artifact]
            equal = left['sha256'] == right['sha256'] and left['bytes'] == right['bytes']
            comparisons.append(dict(reference_external=comparison['external'],artifact=artifact,equal=equal,
                actual_sha256=left['sha256'],reference_sha256=right['sha256']))
    expected = dict(comparisons=comparisons,all_equal=all(row['equal'] for row in comparisons))
    if not expected['all_equal']:
        raise ValueError('registered complete outputs disagree')
    sidecar = attempt/'cross-method-agreement.json'
    if sidecar.exists() and json.loads(sidecar.read_bytes()) != expected:
        raise ValueError('saved comparison sidecar differs from verified outputs')
    gates = scientific_gates(trial, result, external, json.loads((attempt/'transaction.json').read_bytes()))
    gate_sidecar = attempt/'scientific-gates.json'
    if gate_sidecar.exists() and json.loads(gate_sidecar.read_bytes()) != gates:
        raise ValueError('saved scientific gates differ from verified outputs')
    return dict(result,registered_scientific_gates=gates)


def run(trial_id):
    raw = (C/'program.json').read_bytes()
    program = json.loads(raw)
    protocol = (C/'protocol.json').read_bytes()
    registration = json.loads((C/'registration.json').read_bytes())
    if (registration['program_sha256'] != digest(raw)
        or registration['protocol_sha256'] != digest(protocol)
        or json.loads(protocol)['program_sha256'] != digest(raw)):
        raise ValueError('registration binding differs')
    if historical_ledgers() != program['historical_frozen_ledgers']:
        raise ValueError('historical ledger changed')
    external = checked_external(program['external_attempts'], require_bindings=True)
    verify_external_equalities(external, program.get('external_equalities', []))
    if {p:hashed(ROOT/p) for p in CONTROLLERS} != program['controller_sha256']:
        raise ValueError('controller changed')
    if source_hashes(C/'source') != program['source_sha256']:
        raise ValueError('frozen source changed')
    if capture_runtime_contract() != registration['runtime']:
        raise ValueError('runtime changed')
    trial = next(t for t in program['trials'] if t['id'] == trial_id)
    for dependency in trial.get('depends', []):
        result = completed(dependency['trial'])
        for key, expected in dependency.get('equals', {}).items():
            value = result
            for part in key.split('.'):
                value = value[part]
            if value != expected:
                raise ValueError('prospective gate did not pass: '+key)
    for entry in trial['plan'].get('inputs', {}).values():
        if hashed(entry['path']) != entry['sha256']:
            raise ValueError('input changed')
    budget = PhaseBudget(C/'phase-cpu-budget', identity={'protocol_sha256':digest(protocol),
        'source_sha256':program['source_sha256']}, phase_cpu_seconds={'feasibility':program['phase_cpu_cap_seconds']})
    snap = budget.snapshot()
    if any(row['state'] != 'settled' for row in snap['attempts'].values()):
        raise ValueError('unsettled V30 worker blocks admission')
    if program['phase_cpu_cap_seconds']-snap['charged_cpu_seconds']['feasibility'] < trial['cpu_seconds']+2:
        raise ValueError('insufficient complete reservation')
    attempt = C/'attempts'/trial_id
    attempt.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter_ns()
    plan = dict(trial['plan'], source_sha256=program['source_sha256'],
        protocol_sha256=digest(protocol), program_sha256=digest(raw), phase='feasibility',
        output=str(attempt/'outputs'))
    plan['inputs'] = dict(plan['inputs'])
    for key, binding in trial.get('inputs_from_trial', {}).items():
        parent = completed(binding['trial'])
        if binding.get('completion') is True:
            input_path = C/'attempts'/binding['trial']/'outputs/completion.json'
        else:
            artifact = parent['artifacts'][binding['artifact']]
            input_path = C/'attempts'/binding['trial']/'outputs'/artifact['file']
        plan['inputs'][key] = dict(path=str(input_path),sha256=hashed(input_path))
    path = attempt/'plan.json'
    atomic_write(path, canonical_json(plan))
    source = C/'source'
    receipt = run_limited([sys.executable,str(source/'scripts'/trial['script']),str(path)],
        attempt/'worker', WorkerLimits(trial['wall_seconds'],trial['cpu_seconds'],6*2**30,1,
        tuple(program['affinity_cpus'])), identity={'campaign':'research-v30','plan_sha256':digest(path.read_bytes())},
        cwd=source, phase_budget=budget, phase='feasibility')
    receipt_hash = hashed(attempt/'worker/result.json')
    elapsed = time.perf_counter_ns()-start
    atomic_write(attempt/'transaction.json', canonical_json(dict(schema='research-transaction-v30',
        worker_outcome=receipt['outcome'], receipt_sha256=receipt_hash, controller_elapsed_ns=elapsed,
        primary_clock=program['primary_clock'], budget=budget.snapshot())))
    live = attempt/'outputs/progress.json'
    if live.exists():
        atomic_write(attempt/'sealed-progress.json', live.read_bytes())
    if receipt['outcome']['status'] == 'complete':
        current = completed(trial_id)
        atomic_write(attempt/'scientific-gates.json',canonical_json(current['registered_scientific_gates']))
        comparisons = []
        for comparison in trial.get('compare_to', []):
            reference = completed(comparison['trial'])
            for artifact in comparison.get('artifacts', ['model']):
                left = current['artifacts'][artifact]
                right = reference['artifacts'][artifact]
                equal = left['sha256'] == right['sha256'] and left['bytes'] == right['bytes']
                comparisons.append(dict(reference_trial=comparison['trial'],artifact=artifact,equal=equal,
                    actual_sha256=left['sha256'],reference_sha256=right['sha256']))
        for comparison in trial.get('compare_external', []):
            from src.service_terminal_evidence_v30 import verify_completed
            parent = program['external_attempts'][comparison['external']]
            reference = verify_completed(parent['attempt'])
            for artifact in comparison.get('artifacts', ['model']):
                left, right = current['artifacts'][artifact], reference['artifacts'][artifact]
                equal = left['sha256'] == right['sha256'] and left['bytes'] == right['bytes']
                comparisons.append(dict(reference_external=comparison['external'],artifact=artifact,equal=equal,
                    actual_sha256=left['sha256'],reference_sha256=right['sha256']))
        if comparisons:
            atomic_write(attempt/'cross-method-agreement.json',canonical_json(dict(comparisons=comparisons,
                all_equal=all(r['equal'] for r in comparisons))))
            if not all(r['equal'] for r in comparisons):
                raise ValueError('complete cross-method output mismatch; preserve and stop')
    print(json.dumps(dict(trial=trial_id,status=receipt['outcome']['status'],seconds=elapsed/1e9,
        charged=receipt['budget_debit']['charged_cpu_seconds'],
        phase_charge=budget.snapshot()['charged_cpu_seconds']['feasibility'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--register', type=Path)
    group.add_argument('--run')
    args = parser.parse_args()
    with research_worker_lock(ROOT):
        register(args.register) if args.register else run(args.run)
