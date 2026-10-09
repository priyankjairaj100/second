"""Read-only independent audit of the second preserved stale progress incident.

No verifier exception, registration change, evidence repair, or experiment runs.
The report is a new append-only artifact; an existing output is never replaced.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.run_store import canonical_json, strict_json
from src.runtime_contract import capture_runtime_contract
from src.service_terminal_evidence_v30 import verify_completed
from src.worker_control import WorkerLimits
from scripts.analyze_full_service_v30 import verify_plan, verify_worker_schedule, verify_service_claims, verify_final_budget

C = ROOT/'campaigns/independent_c4_v32'
INCIDENT = C/'attempts/c4-delete-0-cold'


def check(value, message):
    if not value:
        raise ValueError(message)


def raw(path):
    path = Path(path)
    check(path.is_file() and not path.is_symlink(), 'missing or symbolic file: '+str(path))
    return path.read_bytes()


def hashed(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def entry(path):
    return dict(bytes=Path(path).stat().st_size, sha256=hashed(path))


def read(path):
    value = strict_json(raw(path))
    check(type(value) is dict, 'non-object metadata')
    return value


def audit():
    start = time.process_time_ns()
    program, protocol, registration = (read(C/name) for name in ('program.json','protocol.json','registration.json'))
    ph, qh = hashed(C/'program.json'), hashed(C/'protocol.json')
    check(registration['program_sha256'] == ph == protocol['program_sha256'], 'program registration differs')
    check(registration['protocol_sha256'] == qh, 'protocol registration differs')
    source_checked = 0
    for name, expected in program['source_sha256'].items():
        check(hashed(C/'source'/name) == expected, 'frozen numerical source differs: '+name)
        source_checked += 1
    for name, expected in program['controller_sha256'].items():
        check(hashed(ROOT/name) == expected, 'current registered controller differs: '+name)
    runtime = capture_runtime_contract()
    check(runtime == registration['runtime'], 'current runtime contract differs')
    prior = verify_completed(C/'attempts/c4-root-prepare')
    try:
        verify_completed(INCIDENT)
    except ValueError as exc:
        strict_error = str(exc)
    else:
        raise ValueError('expected original strict guard to remain failed')
    check(strict_error == 'terminal evidence copies differ; preserve and stop', 'unexpected strict failure')
    t = read(INCIDENT/'transaction.json')
    r = read(INCIDENT/'worker/result.json')
    identity = read(INCIDENT/'worker/identity.json')
    check(t['receipt_sha256'] == hashed(INCIDENT/'worker/result.json'), 'receipt hash mismatch')
    check(r['status'] == 'complete' and r['outcome']['status'] == 'complete' and r['outcome']['returncode'] == 0, 'worker not complete')
    check(t['worker_outcome'] == r['outcome'], 'outcome mismatch')
    check(re.fullmatch(r'attempt-[0-9]{4,}', r['attempt']), 'unsafe worker path')
    inner = INCIDENT/'worker'/r['attempt']
    for name, expected in r['artifacts'].items():
        check(Path(name).name == name and entry(inner/name) == expected, 'receipt artifact mismatch: '+name)
    check(hashlib.sha256(canonical_json(identity)).hexdigest() == r['identity_sha256'], 'identity hash mismatch')
    check(identity['identity'] == r['worker_identity'], 'worker identity mismatch')
    request = read(inner/'request.json')
    for key in ('command','cwd','limits'):
        check(request[key] == identity[key], 'worker request differs: '+key)
    plan = read(INCIDENT/'plan.json')
    check(r['worker_identity']['plan_sha256'] == hashed(INCIDENT/'plan.json'), 'worker plan differs')
    debit = r['budget_debit']; cpu = debit['observed_cpu_ns']
    check(debit['state'] == 'settled' and type(cpu) is int and cpu >= 0, 'debit not settled')
    check(debit['charged_cpu_seconds'] == max(1,(cpu+999999999)//1000000000), 'CPU rounding differs')
    check(r['resource_usage']['total_cpu_ns'] == cpu, 'CPU observations differ')
    check(t['budget']['attempts'][r['budget_attempt_id']] == debit, 'transaction debit differs')
    terminal, live = read(INCIDENT/'outputs/completion.json'), read(INCIDENT/'outputs/progress.json')
    check(raw(INCIDENT/'outputs/completion.json') == raw(INCIDENT/'sealed-progress.json'), 'completion/seal mismatch')
    check(terminal['status'] == 'complete' and live['status'] == 'running', 'unexpected status pair')
    check(terminal['plan_sha256'] == hashed(INCIDENT/'plan.json'), 'terminal plan differs')
    check(live['phases'] == terminal['phases'][:len(live['phases'])], 'live phases are not an earlier prefix')
    check(live['phases'][-1]['phase'] == 'model_write_started', 'unexpected stale phase')
    check([p['phase'] for p in terminal['phases'][len(live['phases']):]] == ['model_write_complete','complete'], 'unexpected later phases')
    common_changed = sorted(k for k in live if live[k] != terminal.get(k))
    check(common_changed == ['artifacts','phases','status'], 'unexpected nonterminal disagreement')
    check(live['artifacts'] == {}, 'stale artifact manifest unexpected')
    output_entries = {}
    for kind, expected in terminal['artifacts'].items():
        check(Path(expected['file']).name == expected['file'], 'unsafe output path')
        actual = entry(INCIDENT/'outputs'/expected['file'])
        check(actual == {k:expected[k] for k in ('bytes','sha256')}, 'output bytes differ')
        output_entries[kind] = actual
    stdout = read(inner/'stdout-summary.json')
    tail = stdout['tail_utf8']; markers = []
    for line in tail.splitlines():
        try: value = json.loads(line)
        except json.JSONDecodeError: continue
        if type(value) is dict and value.get('phase') == 'terminal_record_committed':
            check(set(value) == {'phase','sha256'}, 'unexpected terminal marker fields')
            markers.append(value['sha256'])
        elif type(value) is dict and set(value) == {'terminal_sha256'}:
            markers.append(value['terminal_sha256'])
    check(markers == [hashed(INCIDENT/'outputs/completion.json')], 'stdout terminal binding differs')
    if stdout['bytes'] <= stdout['tail_max_bytes']:
        check(len(tail.encode()) == stdout['bytes'] and hashlib.sha256(tail.encode()).hexdigest() == stdout['sha256'], 'stdout full hash differs')
    results = {}; receipts = []; rows = []
    for trial in program['trials'][:2]:
        a = C/'attempts'/trial['id']; result = prior if trial['id'] == 'c4-root-prepare' else terminal
        p = read(a/'plan.json'); tr = read(a/'transaction.json'); receipt = read(a/'worker/result.json')
        verify_plan(C,trial,p,program,ph,qh,results)
        verify_worker_schedule(C,trial,tr,read(a/'worker/identity.json'),registration,program)
        check(result['schema'] == 'ordered-complete-service-transaction-v30', 'ordered service schema differs')
        check(result['method'] == p['method'] and result['source_sha256'] == program['source_sha256'], 'method or source differs')
        for field in ('confirmation','scientific_promotion','use_candidates'):
            check(result[field] is False, 'policy flag differs')
        for field in ('original_token_count','solver_backend','solver_budget','max_point_work_units'):
            check(result[field] == p[field], 'numerical policy differs')
        check(result['retained_record_ids'] == p['record_ids'] and result['deleted_record_ids'] == p['deleted_ids'], 'record membership differs')
        check(result['complete_model'] and result['model_roundtrip_exact'], 'complete model checks absent')
        check(result['stage_count'] == len(set(result['stage_ids'])) == 24 and result['model_code_elements'] == 42467328, 'model shape differs')
        check(result['complete_state'] == (p['method'] != 'model_only_fresh'), 'state output contract differs')
        check(result['diagnostics']['neural_stage_record_pairs'] == 24*len(p['record_ids']), 'unexpected replay count')
        check(receipt['budget_debit']['reserved_cpu_seconds'] == trial['cpu_seconds']+2, 'reservation differs')
        debit_id = hashlib.sha256(canonical_json(dict(worker=read(a/'worker/identity.json'),attempt=str(a/'worker'/receipt['attempt'])))).hexdigest()
        check(receipt['budget_attempt_id'] == debit_id, 'registered debit identity differs')
        check(result['runtime']['affinity_cpus'] == program['affinity_cpus'] and result['runtime']['python'] == sys.version, 'worker runtime declaration differs')
        check(hashed(result['runtime']['executable']) == registration['runtime']['interpreter']['sha256'], 'worker interpreter declaration differs')
        results[trial['id']] = result; receipts.append(receipt)
        rows.append(dict(trial_id=trial['id'],controller_elapsed_ns=tr['controller_elapsed_ns'],budget_debit=receipt['budget_debit'],original_three_copy_guard_passed=trial['id']!='c4-delete-0-cold'))
    budget = verify_final_budget(C,program,qh,receipts)
    remaining = [t['id'] for t in program['trials'][2:]]
    check(sorted(p.name for p in (C/'attempts').iterdir()) == sorted(t['id'] for t in program['trials'][:2]), 'unexpected attempt exists')
    for trial in program['trials'][2:]:
        WorkerLimits(trial['wall_seconds'],trial['cpu_seconds'],program['address_space_bytes'],1,tuple(program['affinity_cpus'])).check_host()
    compiler = subprocess.run(['cc','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    subprocess.run(['/bin/true'],check=True)
    import numpy, gmpy2
    files = {p.relative_to(INCIDENT).as_posix():entry(p) for p in sorted(INCIDENT.rglob('*.json'))}
    return dict(schema='independent-c4-incident-audit-v34',incident=INCIDENT.relative_to(ROOT).as_posix(),cause='unknown',
        original_evidence_modified=False,original_three_copy_guard_passed=False,original_strict_error=strict_error,
        evidence_checks_passed=True,new_verifier_exception_installed=False,registered_continuation=False,
        program_sha256=ph,protocol_sha256=qh,registration_sha256=hashed(C/'registration.json'),
        completion=entry(INCIDENT/'outputs/completion.json'),sealed_progress=entry(INCIDENT/'sealed-progress.json'),
        stale_live_progress=entry(INCIDENT/'outputs/progress.json'),receipt=entry(INCIDENT/'worker/result.json'),
        transaction=entry(INCIDENT/'transaction.json'),model=output_entries['model'],
        live_prefix=dict(status=live['status'],last_phase=live['phases'][-1]['phase'],phase_count=len(live['phases']),terminal_phase_count=len(terminal['phases']),common_changed_fields=common_changed,terminal_only_fields=sorted(set(terminal)-set(live))),
        source_files_checked=source_checked,metadata_inventory=files,completed_observations=rows,
        phase_budget=dict(cap=program['phase_cpu_cap_seconds'],settled_charge=budget['charged_cpu_seconds']['feasibility'],remaining=program['phase_cpu_cap_seconds']-budget['charged_cpu_seconds']['feasibility'],reserved_unknown_attempts=budget['reserved_unknown_attempts'],ledger_sha256=hashed(C/'phase-cpu-budget/ledger.json')),
        remaining_trials=remaining,
        current_runtime=dict(contract_exact_match=True,python_version=runtime['python_version'],numpy_version=numpy.__version__,gmpy2_version=gmpy2.__version__,compiler=compiler,available_affinity_cpus=sorted(os.sched_getaffinity(0)),remaining_worker_host_limit_checks_passed=True,subprocess_launch_passed=True,proc_cpuinfo_available=Path('/proc/cpuinfo').exists(),proc_status_available=Path('/proc/self/status').exists(),proc_required_by_reviewed_controller_or_worker=False,physical_host_identity_verified=False,native_kernel_preflight_performed=False),
        recommendation='Evidence supports a separately reviewed, hash-pinned append-only continuation for this incident only. Keep original program, samples, numerical source, order, ledger, and all five unstarted trials. The original guard remains failed until a separate controller handles the disclosed incident. No reruns, new allowance, or generic exception are justified.',
        scope='Metadata, current source/runtime bindings, actual output bytes, and minimal host checks. No neural inference, model recomputation, speedup comparison, full campaign completion, or incident cause established.',analysis_process_cpu_ns=time.process_time_ns()-start)


if __name__ == '__main__':
    result = audit()
    path = ROOT/'campaigns/recovery_v34/c4-cold0-incident-independent-audit.json'
    with path.open('xb') as stream:
        stream.write(canonical_json(result))
    print(json.dumps(dict(report=str(path.relative_to(ROOT)),sha256=hashed(path),budget=result['phase_budget'],strict_guard_passed=False,runtime_contract_equal=True)))
