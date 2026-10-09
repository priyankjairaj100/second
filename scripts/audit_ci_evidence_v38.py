#!/usr/bin/env python3
"""Recheck published C4 metadata without launching or importing model workers.

The published commit is the trust anchor. Actual binary comparisons ran on CI.
This audit does not recreate missing model bytes or authenticate a hostile host.
It writes nothing and prints a JSON report.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.run_store import canonical_json, digest, strict_json
from src.service_terminal_evidence_v30 import _verify_stdout
from research_v38.c4_analysis import verify_result_fields, verify_native_receipts
from scripts.analyze_compressed_service_v31 import verify_diagnostics

PUBLISHED_COMMIT = '6f3ccfd987f105366c548bf1d0294a81217b4422'
PREFIX = Path('campaigns/ci_v38_setup_fix')
CAMPAIGN = PREFIX / 'independent_c4_v32'
HOST_ROOT = Path('/home/runner/work/second/second')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit():
    started = time.process_time_ns()
    manifest = subprocess.check_output(
        ['git', 'show', PUBLISHED_COMMIT + ':MANIFEST.sha256'], cwd=ROOT, text=True)
    published = {line[66:]: line[:64] for line in manifest.splitlines()}
    verified = {}

    def bind(name, expected=None):
        name = str(name)
        path = ROOT / name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe evidence path')
        require(path.is_file() and not path.is_symlink(), 'Missing evidence: ' + name)
        if name not in verified:
            with path.open('rb') as stream:
                verified[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
        if name in published:
            require(verified[name] == published[name], 'Published bytes changed: ' + name)
        else:
            require(expected is not None, 'Evidence lacks published or registered binding: ' + name)
        if expected is not None:
            require(verified[name] == expected, 'Registered bytes changed: ' + name)
        return verified[name]

    def read(name):
        bind(name)
        return strict_json((ROOT / name).read_bytes())

    summary = read(CAMPAIGN / 'analysis-v38.json')
    final = read(PREFIX / 'workflow-finalization.json')
    require(final['job_status'] == 'success' and final['final_analysis_exists'], 'Workflow not finalized successfully')
    for mapping in (summary['evidence_sha256'], final['current_text_sha256']):
        for name, expected in mapping.items():
            bind(name, expected)
    program = read(CAMPAIGN / 'program.json')
    protocol = read(CAMPAIGN / 'protocol.json')
    registration = read(CAMPAIGN / 'registration.json')
    publication = read(PREFIX / 'registration-publication.json')
    for value in (registration, protocol, publication, summary):
        require(value['program_sha256'] == bind(CAMPAIGN / 'program.json'), 'Program binding differs')
    require(registration['protocol_sha256'] == summary['protocol_sha256'] == bind(CAMPAIGN / 'protocol.json'),
            'Protocol binding differs')
    require(publication['model_workers_started_before_publication'] is False, 'Registration was late')
    original_program = subprocess.check_output(
        ['git', 'show', publication['registration_commit'] + ':' + str(CAMPAIGN / 'program.json')], cwd=ROOT)
    require(digest(original_program) == registration['program_sha256'], 'Published registration changed')
    require(summary['registered_runtime'] == registration['runtime'], 'Runtime metadata differs')
    for name, expected in program['source_sha256'].items():
        bind(CAMPAIGN / 'source' / name, expected)
        bind(name, expected)
    for name, expected in program['controller_sha256'].items():
        bind(name, expected)
    for name, expected in program['historical_frozen_ledgers'].items():
        bind(name, expected)

    ids = program['execution_order']
    require(ids == [trial['id'] for trial in program['trials']] and len(set(ids)) == 7, 'Trial schedule differs')
    require(sorted(p.name for p in (ROOT / CAMPAIGN / 'attempts').iterdir() if p.is_dir()) == sorted(ids),
            'Missing or extra trial')
    ledger = read(CAMPAIGN / 'phase-cpu-budget/ledger.json')
    require(ledger['binding']['identity'] == dict(protocol_sha256=registration['protocol_sha256'],
            source_sha256=program['source_sha256']), 'Ledger identity differs')
    require(ledger['binding']['phase_cpu_seconds'] == protocol['phase_cpu_seconds'] == {'feasibility': 1900},
            'Phase allowance differs')
    results, transactions, audits, debits = {}, {}, {}, {}
    absent = []
    observed_cpu_ns = 0
    peak_rss_kib = 0
    for trial in program['trials']:
        name = trial['id']
        attempt = CAMPAIGN / 'attempts' / name
        plan = read(attempt / 'plan.json')
        tx = read(attempt / 'transaction.json')
        receipt = read(attempt / 'worker/result.json')
        identity = read(attempt / 'worker/identity.json')
        result = read(attempt / 'outputs/completion.json')
        audit_record = read(attempt / 'actual-binary-audit-v38.json')
        require(bind(attempt / 'outputs/completion.json') == bind(attempt / 'outputs/progress.json')
                == bind(attempt / 'sealed-progress.json'), 'Terminal copies differ: ' + name)
        require(tx['receipt_sha256'] == bind(attempt / 'worker/result.json'), 'Receipt digest differs')
        require(receipt['status'] == receipt['outcome']['status'] == result['status'] == 'complete'
                and receipt['outcome']['returncode'] == 0, 'Incomplete worker')
        require(tx['worker_outcome'] == receipt['outcome'], 'Worker outcomes differ')
        require(type(tx['controller_elapsed_ns']) is int and tx['controller_elapsed_ns'] > 0
                and 0 <= receipt['outcome']['elapsed_wall_ns'] <= tx['controller_elapsed_ns'], 'Invalid clocks')
        require(tx['primary_clock'] == program['primary_clock'] == summary['primary_clock'], 'Clock scope differs')
        require(identity['identity'] == receipt['worker_identity'] == dict(campaign='independent-c4-v32',
                plan_sha256=bind(attempt / 'plan.json')), 'Worker identity differs')
        require(receipt['identity_sha256'] == digest(canonical_json(identity)), 'Identity digest differs')
        require(result['plan_sha256'] == bind(attempt / 'plan.json'), 'Terminal plan differs')
        require(plan['program_sha256'] == registration['program_sha256']
                and plan['protocol_sha256'] == registration['protocol_sha256'], 'Trial registration differs')
        require(plan['source_sha256'] == result['source_sha256'] == program['source_sha256'], 'Trial source differs')
        generated = {'source_sha256', 'protocol_sha256', 'program_sha256', 'phase', 'output'}
        require(set(plan) == set(trial['plan']) | generated, 'Unregistered plan fields')
        require(plan['phase'] == 'feasibility' and plan['output'] == str(HOST_ROOT / attempt / 'outputs'),
                'Trial phase or output differs')
        for key, expected in trial['plan'].items():
            if key != 'inputs':
                require(plan[key] == expected, 'Registered plan policy differs: ' + key)
        static, late = trial['plan']['inputs'], trial.get('inputs_from_trial', {})
        require(set(plan['inputs']) == set(static) | set(late) and not set(static) & set(late), 'Input access differs')
        for key, entry in static.items():
            require(plan['inputs'][key] == entry, 'Static input differs')
            bind(Path(entry['path']).relative_to(HOST_ROOT), entry['sha256'])
        for key, entry in late.items():
            parent = entry['trial']
            require(parent in results, 'Dependency did not precede trial')
            base = CAMPAIGN / 'attempts' / parent / 'outputs'
            if entry.get('completion'):
                target, expected = base / 'completion.json', bind(base / 'completion.json')
            else:
                descriptor = results[parent]['artifacts'][entry['artifact']]
                target, expected = base / descriptor['file'], descriptor['sha256']
            require(plan['inputs'][key] == dict(path=str(HOST_ROOT / target), sha256=expected), 'Parent input differs')
        require(identity['command'][1:] == [str(HOST_ROOT / CAMPAIGN / 'source/scripts' / trial['script']),
                str(HOST_ROOT / attempt / 'plan.json')] and len(identity['command']) == 3, 'Worker command differs')
        require(identity['cwd'] == str(HOST_ROOT / CAMPAIGN / 'source'), 'Worker directory differs')
        expected_limits = dict(wall_seconds=trial['wall_seconds'], cpu_seconds=trial['cpu_seconds'],
            address_space_bytes=program['address_space_bytes'], threads=1, affinity_cpus=program['affinity_cpus'],
            file_size_bytes=512 * 2**20, termination_grace_seconds=1)
        require(identity['limits'] == receipt['limits'] == expected_limits, 'Worker limits differ')
        inner = attempt / 'worker' / receipt['attempt']
        require(receipt['attempt'] == 'attempt-0001', 'Unexpected retry')
        for filename, descriptor in receipt['artifacts'].items():
            path = inner / filename
            require(bind(path) == descriptor['sha256'] and (ROOT / path).stat().st_size == descriptor['bytes'],
                    'Bound worker artifact differs')
        request = read(inner / 'request.json')
        require(all(request[key] == identity[key] for key in ('command', 'cwd', 'limits')), 'Worker request differs')
        _verify_stdout(read(inner / 'stdout-summary.json'), bind(attempt / 'outputs/completion.json'))
        debit = receipt['budget_debit']
        observed = debit['observed_cpu_ns']
        require(type(observed) is int and observed >= 0 and debit['state'] == 'settled', 'Unsettled CPU debit')
        require(debit['charged_cpu_seconds'] == max(1, (observed + 999999999) // 1000000000)
                and debit['charged_cpu_seconds'] <= debit['reserved_cpu_seconds'] == trial['cpu_seconds'] + 2,
                'CPU charge differs')
        require(receipt['resource_usage']['total_cpu_ns'] == observed and not receipt['budget_reservation_overrun'],
                'CPU observation differs')
        debit_id = receipt['budget_attempt_id']
        require(debit_id not in debits and tx['budget']['attempts'][debit_id] == debit, 'Duplicate or different debit')
        require(debit_id == digest(canonical_json(dict(worker=identity, attempt=str(HOST_ROOT / inner)))),
                'Debit identity differs')
        debits[debit_id] = debit
        observed_cpu_ns += observed
        peak_rss_kib = max(peak_rss_kib, receipt['resource_usage']['max_rss_kib'])
        require(result['method'] == plan['method'] and result['fixed_target_sha256'] == plan['expected_target'],
                'Target or method differs')
        require(result['retained_record_ids'] == plan['record_ids'] and result['deleted_record_ids'] == plan['deleted_ids'],
                'Source membership differs')
        require(all(result[key] is False for key in ('confirmation', 'scientific_promotion', 'use_candidates')),
                'Scientific policy differs')
        verify_result_fields(result, trial)
        require(audit_record['status'] == 'complete_verified' and audit_record['trial'] == name
                and audit_record['model_code_count'] == 42467328 and audit_record['model_stage_count'] == 24,
                'CI binary audit is incomplete')
        require(audit_record['controller_seconds'] == tx['controller_elapsed_ns'] / 1e9, 'Audit clock differs')
        for kind, descriptor in result['artifacts'].items():
            require(audit_record['actual_artifacts'][kind] == dict(descriptor, full_file_hash_recomputed=True),
                    'CI binary descriptor differs')
            binary = attempt / 'outputs' / descriptor['file']
            require(summary['verified_binary_artifacts'][str(binary)] ==
                    {k: descriptor[k] for k in ('sha256', 'bytes')}, 'Summary binary descriptor differs')
            if not (ROOT / binary).exists():
                absent.append(str(binary))
        gates = read(attempt / 'scientific-gates.json')
        require(gates == audit_record['scientific_gates'], 'Scientific gates differ')
        row = next(row for row in summary['trials'] if row['id'] == name)
        require(row['controller_elapsed_ns'] == tx['controller_elapsed_ns'] and row['artifacts'] == result['artifacts']
                and row['scientific_gates'] == gates, 'Summary trial differs')
        results[name], transactions[name], audits[name] = result, tx, audit_record

    require(debits == ledger['attempts'] == summary['phase_budget']['attempts'], 'Final ledger omits or adds workers')
    charged = sum(d['charged_cpu_seconds'] for d in debits.values())
    require(summary['phase_budget']['charged_cpu_seconds'] == {'feasibility': charged} and charged <= 1900,
            'Total CPU charge differs')
    require(summary['phase_budget']['reserved_unknown_attempts'] == 0, 'Unresolved CPU reservation')
    require(final['ledger_sha256'] == bind(CAMPAIGN / 'phase-cpu-budget/ledger.json'), 'Final ledger digest differs')

    def seconds(name):
        return transactions[name]['controller_elapsed_ns'] / 1e9

    def compare_models(left, right):
        require(results[left]['artifacts']['model'] == results[right]['artifacts']['model'], 'Model descriptors differ')
        comparisons = [(a, b) for a, b in ((left, right), (right, left))
                       if any(row == dict(actual_bytes_equal=True, artifact='model', reference=b)
                              for row in audits[a]['actual_byte_comparisons'])]
        require(bool(comparisons), 'CI recorded no actual byte comparison for this pair')

    pairs = []
    for request, reported in zip(program['requests'], summary['pairs'], strict=True):
        r, c = request['repair_trial'], request['cold_trial']
        compare_models(r, c)
        for name in (r, c):
            require(results[name]['retained_record_ids'] == request['retained_ids']
                    and results[name]['deleted_record_ids'] == request['deleted_ids'], 'Pair membership differs')
        changes = audits[r]['deletion_code_changes']
        require(changes == audits[c]['deletion_code_changes'] == reported['deletion_code_changes'], 'Changed code record differs')
        require(sum(row['changed_code_count'] for row in changes['stages']) == changes['changed_code_count']
                and sum(row['code_count'] for row in changes['stages']) == changes['total_code_count'] == 42467328,
                'Changed code arithmetic differs')
        ratio = seconds(c) / seconds(r)
        require(reported['request'] == request['id'] and reported['cold_seconds'] == seconds(c)
                and reported['repair_seconds'] == seconds(r) and reported['cold_over_repair'] == ratio,
                'Pair timing differs')
        pairs.append(dict(request=request['id'], cold_seconds=seconds(c), repair_seconds=seconds(r),
                          cold_over_repair=ratio, changed_codes=changes['changed_code_count']))
    geometric_mean = math.exp(sum(math.log(p['cold_over_repair']) for p in pairs) / len(pairs))
    require(geometric_mean == summary['descriptive_geometric_mean_cold_over_lossless_repair'], 'Geometric mean differs')
    compressed = summary['compressed']
    request = next(r for r in program['requests'] if r['id'] == program['compressed_request_id'])
    name = compressed['trial']
    compare_models(name, request['cold_trial'])
    compare_models('c4-root-convert', 'c4-root-prepare')
    result = results[name]
    plan = read(CAMPAIGN / 'attempts' / name / 'plan.json')
    native = verify_native_receipts(result, plan, program, ROOT / CAMPAIGN / 'source')
    require(native == summary['native_certificate_evidence'], 'Native certificate metadata differs')
    require(verify_diagnostics(result, plan) == summary['compressed_diagnostics'], 'Certificate diagnostics differ')
    lossless_bytes = results[request['repair_trial']]['state_artifact']['bytes']
    compressed_bytes = result['state_artifact']['bytes']
    base_bytes = sum((ROOT / Path(e['path']).relative_to(HOST_ROOT)).stat().st_size
                     for k, e in program['trials'][0]['plan']['inputs'].items() if k in ('config', 'weights'))
    require(compressed['repair_seconds'] == seconds(name)
            and compressed['cold_over_compressed'] == seconds(request['cold_trial']) / seconds(name)
            and compressed['lossless_over_compressed'] == seconds(request['repair_trial']) / seconds(name),
            'Compressed timing arithmetic differs')
    require(compressed['state_reduction_percent_over_lossless'] == 100 * (1 - compressed_bytes / lossless_bytes)
            and compressed['complete_state_plus_base_bytes'] == compressed_bytes + base_bytes
            and compressed['lossless_state_plus_base_bytes'] == lossless_bytes + base_bytes, 'State accounting differs')
    gates = compressed['scientific_gates']['checks']
    require(gates['latency']['passed'] == (seconds(name) < seconds(request['cold_trial']))
            and gates['storage']['passed'] == (compressed_bytes < lossless_bytes), 'Gate arithmetic differs')
    for field in ('certificate_accepted_stages', 'certificate_rejected_stages', 'point_solver_stages', 'neural_stage_record_pairs'):
        require(compressed[field] == result['diagnostics'][field], 'Compressed route count differs')
    require(summary['preparation_seconds'] == seconds('c4-root-prepare')
            and summary['conversion_seconds'] == seconds('c4-root-convert'), 'Setup timing differs')
    bootstrap = read(PREFIX / 'bootstrap-audit.json')
    boot_ledger = read(PREFIX / 'bootstrap/phase-cpu-budget/ledger.json')
    require(all(row['state'] == 'settled' for row in boot_ledger['attempts'].values()), 'Bootstrap is unsettled')
    require(bootstrap['charged_cpu_seconds'] == sum(row['charged_cpu_seconds'] for row in boot_ledger['attempts'].values()),
            'Bootstrap CPU total differs')
    require(bootstrap['ledger_sha256'] == final['bootstrap_ledger_sha256'] == bind(PREFIX / 'bootstrap/phase-cpu-budget/ledger.json'),
            'Bootstrap ledger changed')
    trial_analysis_ns = sum(row['analysis_cpu_ns'] for row in audits.values())
    return dict(schema='published-c4-metadata-audit-v38', status='metadata_checks_passed', published_commit=PUBLISHED_COMMIT,
        workflow_run_id=37956045572, workflow_job_id=113906696278, corpus='c4',
        scope='Recomputed metadata and arithmetic. Actual binary comparisons occurred on CI; missing binaries were not recreated.',
        model_binary_bytes_reverified_locally=False, neural_inference_performed=False, files_written=False,
        all_seven_trials_accounted=True, terminal_copies_agree=True, absent_binary_artifacts=absent,
        pairs=pairs, descriptive_geometric_mean_cold_over_lossless_repair=geometric_mean,
        compressed=compressed, preparation_seconds=summary['preparation_seconds'], conversion_seconds=summary['conversion_seconds'],
        campaign_charged_cpu_seconds=charged, campaign_observed_cpu_ns=observed_cpu_ns,
        bootstrap_charged_cpu_seconds=bootstrap['charged_cpu_seconds'], max_reported_worker_rss_kib=peak_rss_kib,
        ci_trial_binary_audit_cpu_ns=trial_analysis_ns, ci_final_analysis_cpu_ns=summary['analysis_cpu_ns'],
        analyses_outside_worker_ledgers=True,
        state_plus_base_reduction_percent=100 * (1 - (compressed_bytes + base_bytes) / (lossless_bytes + base_bytes)),
        preparation_plus_conversion_plus_first_compressed_seconds=seconds('c4-root-prepare') + seconds('c4-root-convert') + seconds(name),
        repeated_same_state_break_even_claimed=False, changing_state_lifetime_benefit_established=False,
        confirmation=False, evidence_sha256=verified, verified_files=len(verified),
        auditor_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        local_analysis_cpu_ns=time.process_time_ns() - started)


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, sort_keys=True, allow_nan=False))
