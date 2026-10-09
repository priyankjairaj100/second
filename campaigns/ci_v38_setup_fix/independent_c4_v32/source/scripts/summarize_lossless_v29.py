"""Check and summarize the frozen lossless pilot without running a model."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-artifacts', action='store_true')
    args = parser.parse_args()
    bindings = {}

    def read(path):
        path = ROOT/path
        bindings[str(path.relative_to(ROOT))] = sha(path)
        return json.loads(path.read_bytes())

    folder = Path('campaigns/lossless_timing_v29')
    program = read(folder/'program.json')
    protocol = read(folder/'protocol.json')
    assert protocol['program_sha256'] == bindings[str(folder/'program.json')]
    read(folder/'registration.json')
    records = {}
    for trial in program['trials']:
        attempt = folder/'attempts'/trial['id']
        plan = read(attempt/'plan.json')
        tx = read(attempt/'transaction.json')
        receipt = read(attempt/'worker/result.json')
        p = read(attempt/'sealed-progress.json')
        live = read(attempt/'outputs/progress.json')
        terminal = read(attempt/'outputs/completion.json')
        assert p == live == terminal
        terminal_hash = bindings[str(attempt/'outputs/completion.json')]
        assert terminal_hash == bindings[str(attempt/'outputs/progress.json')]
        assert terminal_hash == bindings[str(attempt/'sealed-progress.json')]
        assert p['status'] == receipt['outcome']['status'] == 'complete'
        assert receipt['budget_debit']['state'] == 'settled'
        assert receipt['outcome']['returncode'] == 0
        assert tx['receipt_sha256'] == bindings[str(attempt/'worker/result.json')]
        assert p['plan_sha256'] == bindings[str(attempt/'plan.json')]
        assert p['stage_count'] == 24 and p['model_code_elements'] == 42467328
        assert plan['program_sha256'] == bindings[str(folder/'program.json')]
        for name, artifact in receipt['artifacts'].items():
            path = attempt/'worker/attempt-0001'/name
            value = read(path)
            assert (ROOT/path).stat().st_size == artifact['bytes']
            assert bindings[str(path)] == artifact['sha256']
            if name == 'stdout-summary.json':
                rows = [json.loads(line) for line in value['tail_utf8'].splitlines() if line.startswith('{')]
                assert any(row.get('phase') == 'terminal_record_committed'
                           and row.get('sha256') == terminal_hash for row in rows)
        artifacts = {'model':p['model_artifact']}
        if p.get('state_artifact'):
            artifacts['state'] = p['state_artifact']
        if args.verify_artifacts:
            for artifact in artifacts.values():
                path = ROOT/attempt/'outputs'/artifact['file']
                assert path.stat().st_size == artifact['bytes']
                assert sha(path) == artifact['sha256']
        d = p['diagnostics']
        neural = d.get('neural_stage_record_pairs', 0)
        if trial['method'] == 'model_only_fresh':
            neural += d.get('anchor_preparation_stage_record_pairs', 0)
        records[trial['id']] = dict(method=trial['method'],
            controller_elapsed_ns=tx['controller_elapsed_ns'],
            controller_seconds=tx['controller_elapsed_ns']/1e9,
            stage_count=p['stage_count'], model_code_elements=p['model_code_elements'],
            neural_stage_record_pairs=neural, avoided_neural_stage_record_pairs=24-neural,
            artifacts=artifacts, three_terminal_records_equal=True,
            terminal_sha256=terminal_hash, terminal_hash_bound_in_receipt_logs=True,
            charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],
            observed_cpu_ns=receipt['budget_debit']['observed_cpu_ns'],
            service_metrics={key:d.get(key) for key in ('service_elapsed_ns',
                'exact_service_elapsed_ns','lossless_decode_elapsed_ns','decoded_descriptors',
                'decoded_deleted_descriptors','reused_descriptors','encoded_descriptors')})

    archive = read(Path('campaigns/lossless_state_audit_v29b/summary.json'))
    read(Path('campaigns/lossless_state_audit_v29b/plan.json'))
    old_archive = read(Path('campaigns/lossless_state_audit_v29/summary.json'))
    probe = read(Path('campaigns/lossless_probe_v29/summary.json'))
    tests = read(Path('campaigns/lossless_software_check_v29.json'))
    read(Path('campaigns/calibration_admission_plans_v29.json'))
    assert tests['exit_code'] == 0 and tests['count'] == 35
    assert archive['status'] == old_archive['status'] == probe['status'] == 'complete'
    repair, indexed, cold = (records[name] for name in ('repair-001','indexed-001','cold-001'))
    assert repair['artifacts']['model'] == indexed['artifacts']['model'] == cold['artifacts']['model']
    assert repair['artifacts']['state'] == indexed['artifacts']['state']
    assert repair['artifacts']['state']['sha256'] == archive['generations']['repair-001']['complete_state_sha256']
    assert repair['neural_stage_record_pairs'] == indexed['neural_stage_record_pairs'] == 0
    assert cold['neural_stage_record_pairs'] == 24
    ledger = read(folder/'phase-cpu-budget/ledger.json')
    charged = sum(row['charged_cpu_seconds'] for row in ledger['attempts'].values())
    assert charged == sum(row['charged_cpu_seconds'] for row in records.values()) == 148
    assert all(row['state'] == 'settled' for row in ledger['attempts'].values())
    for name, expected in program['historical_frozen_ledgers'].items():
        path = Path('campaigns')/name/'phase-cpu-budget/ledger.json'
        old = read(path)
        assert bindings[str(path)] == expected['sha256']
        assert sum(row['charged_cpu_seconds'] for row in old['attempts'].values()) == expected['charged_or_reserved_cpu_seconds']
    raw_bytes = archive['generations']['repair-001']['exact_state_bytes']
    lossless_bytes = repair['artifacts']['state']['bytes']
    compressed = read(Path('campaigns/compressed_summary_v25_v28.json'))
    enclosure_bytes = compressed['full_model_results']['v28_repair']['artifacts']['state']['bytes']
    report = dict(schema='lossless-summary-v29', status='complete',
        scope='One adaptive DistilGPT2/WikiText deletion; one timing per method; no confirmation or quality evaluation.',
        target='Fixed nearest-grid ancestor features; not sequential GPTQ calibration.',
        trials=records, prospective_order=[trial['id'] for trial in program['trials']], order_seed=program['order_seed'],
        ratios=dict(cold_over_repair=cold['controller_elapsed_ns']/repair['controller_elapsed_ns'],
                    cold_over_indexed=cold['controller_elapsed_ns']/indexed['controller_elapsed_ns']),
        interpretation='Lossless repair beat matched cold reconstruction in this pilot. Reliable or broad speedup remains unproved.',
        indexed_interpretation='Repair and indexed reconstruction share the algorithm. Their single timings differ; no statistical equality is claimed.',
        primary_comparison='repair-001 versus cold-001; do not substitute the faster indexed control as repair.',
        comparison_limits=['One request and one observation per method.',
            'Repair and indexed reconstruction write complete model plus state; cold writes model only.',
            'OS caches and other machine activity are uncontrolled.',
            'Historical V28 latency is not a newly matched comparison.',
            'Archive conversion is measured separately; lifetime preparation remains open.'],
        storage=dict(raw_exact_complete_state_bytes=raw_bytes, lossless_complete_state_bytes=lossless_bytes,
            v28_enclosure_complete_state_bytes=enclosure_bytes,
            lossless_reduction_from_raw_percent=(1-lossless_bytes/raw_bytes)*100,
            enclosure_reduction_from_lossless_percent=(1-enclosure_bytes/lossless_bytes)*100,
            shared_base_checkpoint_excluded=True, shared_base_checkpoint_required=True),
        budget=dict(separate_phase_cap_cpu_seconds=240, phase_charged_cpu_seconds=charged,
            phase_remaining_cpu_seconds=240-charged, registered_trials_complete=True, additional_trials_registered=False,
            historical_phase_held_cpu_seconds=898, historical_phase_cap_cpu_seconds=900,
            historical_unknown_reserved_cpu_seconds=122, legacy_charged_cpu_seconds=10775,
            legacy_cap_cpu_seconds=10800, combined_charged_or_reserved_cpu_seconds=11673+charged,
            historical_ledgers_unchanged=True, budgets_reset_or_pooled=False,
            archive_analysis_and_software_costs_reported_separately=True),
        software=dict(count=tests['count'], suite_seconds=tests['suite_seconds'], child_cpu_seconds=tests['child_cpu_seconds']),
        artifact_binaries_reverified=args.verify_artifacts,
        new_theory='Canonical four-bit model-response separation, positive margins, uniformly conditioned metrics, and explicit archive/probe bounds.',
        scaling='Current token-space path retains quadratic memory; primal certificate path is not implemented.',
        open_gates=['Scalable certified solver','Stronger lossless controls','Broader untouched quality',
                    'Independent requests, models, and corpora','Lifetime cost','Prospective confirmation'],
        acl_ready=False, empirical_program_complete=False, evidence_sha256=dict(sorted(bindings.items())))
    output = ROOT/'campaigns/lossless_summary_v29.json'
    output.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(report=str(output.relative_to(ROOT)), ratios=report['ratios'],
        bound_files=len(bindings), phase_charge=charged)))


if __name__ == '__main__':
    main()
