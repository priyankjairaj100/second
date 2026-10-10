"""Read-only local audit of published V39 metadata and recorded comparisons.

Missing derived binaries remain explicitly unverified locally. This command
does not invoke an empirical worker, reconstruct a model, or change a ledger.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time

from src.run_store import canonical_json, digest
from src.service_terminal_evidence_v30 import _verify_stdout
from src.phase_budget import read_budget_snapshot

ROOT = Path(__file__).resolve().parents[1]
PREFIX = Path('campaigns/ci_scale_v39')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    require(path.is_file() and not path.is_symlink(), 'Missing or symbolic file: ' + str(path))
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def audit():
    start = time.process_time_ns()
    root = ROOT / PREFIX
    final = read(root / 'workflow-finalization.json')
    require(final['job_status'] == 'success' and final['analysis_exists'], 'Workflow did not finish successfully')
    for name, expected in final['text_sha256'].items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts and path.is_relative_to(PREFIX), 'Unsafe evidence path')
        require(sha(ROOT / path) == expected, 'Published text changed: ' + name)
    program, registration = read(root / 'program.json'), read(root / 'registration.json')
    require(sha(root / 'program.json') == registration['program_sha256'], 'Program binding differs')
    source_commit = program['registered_source_commit']
    source_files = dict(program['source_sha256'], **program['extra_source_sha256'], **program['control_source_sha256'])
    for name, expected in source_files.items():
        raw = subprocess.check_output(['git', 'show', source_commit + ':' + name], cwd=ROOT)
        require(digest(raw) == expected, 'Registered source differs from published commit: ' + name)
    for name, expected in program['historical_ledgers_sha256'].items():
        require(sha(ROOT / name) == expected, 'Historical ledger changed: ' + name)
    budgets = {}
    for group, cap in program['phase_cpu_seconds'].items():
        protocol = root / f'protocol-{group}.json'
        require(sha(protocol) == registration['protocols'][group], 'Protocol binding differs')
        require(read(protocol)['program_sha256'] == registration['program_sha256'], 'Protocol program differs')
        snapshot = read_budget_snapshot(root / f'{group}-phase-cpu-budget',
            identity=dict(protocol_sha256=sha(protocol), source_sha256=program['source_sha256']),
            phase_cpu_seconds={'feasibility': cap})
        require(snapshot['status'] == 'verified', 'Ledger is unavailable')
        require(all(row['state'] == 'settled' for row in snapshot['attempts'].values()), 'Unsettled attempt exists')
        require(not snapshot['over_cap']['feasibility'], 'Phase exceeded its allowance')
        budgets[group] = snapshot
    missing, present, results, trials = [], [], {}, []
    for trial in program['trials']:
        attempt = root / 'attempts' / trial['id']
        plan_path, worker, output = attempt / 'plan.json', attempt / 'worker', attempt / 'outputs'
        plan, transaction, receipt = read(plan_path), read(attempt / 'transaction.json'), read(worker / 'result.json')
        require(all(plan[k] == v for k, v in trial.items()), 'Plan differs from registered trial')
        require(plan['program_sha256'] == registration['program_sha256'], 'Plan program differs')
        require(plan['protocol_sha256'] == registration['protocols'][trial['phase_group']], 'Plan protocol differs')
        require(transaction['receipt_sha256'] == sha(worker / 'result.json'), 'Receipt binding differs')
        require(transaction['worker_outcome'] == receipt['outcome'], 'Transaction outcome differs')
        require(receipt['outcome']['status'] == 'complete' and receipt['outcome']['returncode'] == 0, 'Worker failed')
        identity = read(worker / 'identity.json')
        require(digest(canonical_json(identity)) == receipt['identity_sha256'], 'Worker identity differs')
        require(identity['identity'] == receipt['worker_identity'], 'Identity record differs')
        require(receipt['worker_identity']['plan_sha256'] == sha(plan_path), 'Worker plan differs')
        inner = worker / receipt['attempt']
        require(receipt['attempt'].startswith('attempt-') and Path(receipt['attempt']).name == receipt['attempt'],
                'Unsafe worker attempt')
        for name, entry in receipt['artifacts'].items():
            require(Path(name).name == name, 'Unsafe receipt artifact')
            require(sha(inner / name) == entry['sha256'] and (inner / name).stat().st_size == entry['bytes'],
                    'Receipt artifact differs')
        request = read(inner / 'request.json')
        require(all(request[k] == identity[k] for k in ('command', 'cwd', 'limits')), 'Worker request differs')
        debit = receipt['budget_debit']
        require(debit == budgets[trial['phase_group']]['attempts'][receipt['budget_attempt_id']], 'Ledger debit differs')
        require(debit == transaction['budget']['attempts'][receipt['budget_attempt_id']], 'Transaction debit differs')
        observed = receipt['resource_usage']['total_cpu_ns']
        require(observed == debit['observed_cpu_ns'] and debit['charged_cpu_seconds'] == max(1, (observed + 999999999) // 1000000000),
                'Observed CPU settlement differs')
        terminal = (output / 'completion.json').read_bytes()
        require(terminal == (output / 'progress.json').read_bytes() == (attempt / 'sealed-progress.json').read_bytes(),
                'Terminal copies differ')
        _verify_stdout(read(inner / 'stdout-summary.json'), digest(terminal))
        result = json.loads(terminal)
        require(result['status'] == 'complete' and result['plan_sha256'] == sha(plan_path), 'Terminal binding differs')
        require(result['source_sha256'] == program['source_sha256']
                and result['extra_source_sha256'] == program['extra_source_sha256'], 'Terminal sources differ')
        for name, entry in result['artifacts'].items():
            require(Path(entry['file']).name == entry['file'], 'Unsafe output artifact')
            path = output / entry['file']
            if not path.exists():
                require(path.suffix == '.bin', 'Required text output is missing')
                missing.append(dict(path=str(path.relative_to(ROOT)), **entry))
            else:
                require(sha(path) == entry['sha256'] and path.stat().st_size == entry['bytes'], 'Output artifact differs')
                present.append(str(path.relative_to(ROOT)))
        recorded = read(attempt / 'actual-artifact-audit.json')
        require(recorded['status'] == 'verified' and recorded['completion_sha256'] == digest(terminal), 'CI audit binding differs')
        require(recorded['actual_output_files_rehashed'], 'CI did not audit output files')
        if trial['kind'] == 'case':
            require(result['exact_gram_bytes_equal'] and result['actual_binary_comparison_performed'] and recorded['binary_bytes_compared'],
                    'Recorded complete-stage comparison failed')
            require(set(result['arms']) == set(trial['arm_order']), 'Registered arm is missing')
            hashes = set()
            for arm, row in result['arms'].items():
                require(row['component_elapsed_ns'] > 0, 'Invalid component clock')
                if row['status'] == 'certified':
                    require(row['code_count'] == 1769472 and row['codes_committed'], 'Incomplete codes')
                    entry = result['artifacts'][arm + '-codes.bin']
                    require(entry['sha256'] == row['code_sha256'] and entry['bytes'] == 884736, 'Packed code binding differs')
                    hashes.add(row['code_sha256'])
                else:
                    require(row['status'] == 'scientific_refusal' and not row['codes_committed'], 'Undeclared arm outcome')
            require(len(hashes) <= 1, 'Recorded code hashes differ')
            require(result['all_committed_code_bytes_equal'] == bool(hashes), 'Recorded agreement flag differs')
            results[str(trial['retained_count'] * 128)] = result['arms']
        trials.append(dict(id=trial['id'], cpu_charge=debit['charged_cpu_seconds'],
            controller_seconds=transaction['controller_elapsed_ns'] / 1e9))
    analysis = read(root / 'analysis.json')
    require(analysis['status'] == 'complete_verified' and analysis['actual_binary_artifacts_reverified'], 'Final CI analysis incomplete')
    for count, arms in results.items():
        require(analysis['cases'][count]['arms'] == arms, 'Final analysis changed arm results')
        for name, ratio in analysis['cases'][count]['ratios'].items():
            base, method = name.split('_over_')
            expected = (arms[base]['component_elapsed_ns'] / arms[method]['component_elapsed_ns']
                        if arms[base]['status'] == arms[method]['status'] == 'certified' else None)
            require(ratio == expected, 'Derived ratio differs')
    return dict(schema='scale-metadata-audit-v40', status='metadata_checks_passed',
        registered_source_commit=source_commit, published_text_files_checked=len(final['text_sha256']),
        source_files_checked=len(source_files), trials=trials,
        cpu_charges={group: row['charged_cpu_seconds']['feasibility'] for group, row in budgets.items()},
        all_new_ledgers_settled=True, present_output_files_checked=len(present),
        missing_derived_binary_count=len(missing), missing_derived_binaries=missing,
        local_binary_reverification_complete=not missing, numerical_reexecution=False,
        ci_reported_actual_binary_audit_verified_as_metadata=True,
        cases=analysis['cases'], cpu_seconds=time.process_time_ns() / 1e9 - start / 1e9,
        scope='Read-only text, receipt, ledger, source, and ratio audit. Missing binary files were not locally reverified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'published_text_files_checked',
        'cpu_charges', 'missing_derived_binary_count', 'local_binary_reverification_complete')}))
