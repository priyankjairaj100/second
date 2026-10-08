"""Summarize all registered stage cells, including missing and failed cells.

These single in-process timings cannot establish a full-service speedup.
This reader requires a settled worker and verifies its source and plan bindings.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.experiment_inventory import source_hashes
from src.run_store import atomic_write, canonical_json, digest


def summarize(attempt):
    plan_raw = (attempt / 'plan.json').read_bytes()
    plan = json.loads(plan_raw)
    receipt = json.loads((attempt / 'worker/result.json').read_bytes())
    if receipt['budget_debit']['state'] != 'settled':
        raise ValueError('the empirical worker is not settled')
    if receipt['worker_identity']['plan_sha256'] != digest(plan_raw):
        raise ValueError('worker and plan bindings differ')
    if source_hashes(attempt / 'source') != plan['source_sha256']:
        raise ValueError('the archived source snapshot changed')
    raw = attempt / 'outputs/progress.json'
    progress = json.loads(raw.read_bytes()) if raw.exists() else {}
    if progress and progress['plan_sha256'] != digest(plan_raw):
        raise ValueError('progress and plan bindings differ')
    observed = {row['dataset']: row for row in progress.get('datasets', [])}
    if len(observed) != len(progress.get('datasets', [])):
        raise ValueError('duplicate observed dataset')
    rows = []
    for entry in plan['datasets']:
        data = observed.get(entry['dataset'], {})
        variants = data.get('variants', [])
        if len(variants) > len(entry['comparison_order']):
            raise ValueError('unregistered extra variants')
        reference_ns = data.get('retained_reference_solver_elapsed_ns')
        reference = data.get('retained_codes', {})
        for index, cell in enumerate(entry['comparison_order']):
            value = variants[index] if index < len(variants) else {}
            for field, expected in cell.items():
                if value and value.get(field) != expected:
                    raise ValueError('observed cell differs from its registered position')
            status = value.get('status', 'unstarted')
            if status == 'running':
                status = 'interrupted'
            exact = None
            if status == 'complete':
                exact = (value['unequal_values'] == 0 and
                         value['codes']['sha256'] == reference['sha256'] and
                         value['codes']['values'] == reference['values'])
                if not exact:
                    raise ValueError('a complete cell does not match the reference')
            timing = value.get('solver_elapsed_ns')
            diagnostics = value.get('diagnostics', {})
            row = dict(dataset=entry['dataset'], **cell, status=status,
                       exact=exact, solver_elapsed_ns=timing,
                       reference_elapsed_ns=reference_ns,
                       reference_over_variant=(reference_ns / timing
                           if exact and reference_ns and timing else None),
                       diagnostics=diagnostics)
            total = reference.get('values')
            if total and 'prefix_verified_decisions' in diagnostics:
                prefix = diagnostics['prefix_verified_decisions']
                if prefix + diagnostics['fallback_decisions'] != total:
                    raise ValueError('unique decision counters do not partition the output')
                row['verified_fraction'] = prefix / total
            for key in ('error_type', 'error'):
                if key in value:
                    row[key] = value[key]
            rows.append(row)
    return dict(schema='speculative-stage-summary-v16',
        attempt_id=attempt.name, plan_sha256=digest(plan_raw),
        progress_sha256=digest(raw.read_bytes()) if raw.exists() else None,
        worker_status=receipt['outcome']['status'],
        progress_status=progress.get('status', 'absent'),
        budget_debit=receipt['budget_debit'], cells=rows,
        complete_cells=sum(row['status'] == 'complete' for row in rows),
        planned_cells=len(rows), scientific_promotion=False,
        full_model_speed_claim=False,
        limitations=['Single in-process solver timings; no replication or uncertainty interval.',
                     'Common input loading and features are outside per-solver clocks.',
                     'No complete state, transaction, or lifetime result.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt', type=Path)
    args = parser.parse_args()
    output = summarize(args.attempt)
    atomic_write(args.attempt / 'analysis.json', canonical_json(output))
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
