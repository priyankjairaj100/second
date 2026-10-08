"""Summarize the fixed finer-grid pilot without promoting exploratory evidence."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pilot_budget import inherited_allowance
from src.run_store import atomic_write, canonical_json, digest


def main():
    root = Path(__file__).resolve().parents[1]
    archive = root / 'pilots/v14'
    attempts = []
    results = {}
    for directory in sorted(archive.glob('attempt-*')):
        receipt_path = directory / 'worker/result.json'
        if not receipt_path.exists():
            continue
        receipt = json.loads(receipt_path.read_bytes())
        progress_path = directory / 'outputs/progress.json'
        progress = json.loads(progress_path.read_bytes()) if progress_path.exists() else {}
        ledger = json.loads((directory / 'phase-cpu-budget/ledger.json').read_bytes())
        settled = (receipt.get('budget_debit', {}).get('state') == 'settled'
                   and all(row['state'] == 'settled' for row in ledger['attempts'].values()))
        if not settled:
            raise ValueError('settle all research workers before final analysis')
        status = receipt['outcome']['status']
        if status == 'complete' and progress.get('status') != 'complete':
            raise ValueError('receipt/progress mismatch')
        attempts.append(dict(
            id=directory.name, status=status,
            receipt_sha256=digest(receipt_path.read_bytes()),
            progress_sha256=digest(progress_path.read_bytes()) if progress_path.exists() else None,
            worker_wall_seconds=receipt['outcome']['elapsed_wall_ns'] / 1e9,
            charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],
            peak_rss_bytes=progress.get('peak_rss_bytes'),
        ))
        if status == 'complete':
            results[directory.name] = progress
    charged, remaining = inherited_allowance(root)
    quantization = results.get('attempt-001', {})
    quality = results.get('attempt-002', {})
    ratios = quality.get('ratios_to_base', {})
    summary = dict(
        schema='v14-finer-dyadic-grid-evidence', attempts=attempts,
        quantization_complete=quantization.get('full_model_quantization', False),
        stage_count=len(quantization.get('stages', [])),
        interval_decisions=sum(row['interval_decisions'] for row in quantization.get('stages', [])),
        exact_decisions=sum(row['exact_decisions'] for row in quantization.get('stages', [])),
        target_sha256=quantization.get('target_sha256'),
        quality_complete=quality.get('status') == 'complete',
        quality=quality.get('quality'), ratios_to_base=ratios,
        fine_to_power2_ratio=(ratios['dyadic_calibrated'] / ratios['power2_calibrated']
                              if 'dyadic_calibrated' in ratios and 'power2_calibrated' in ratios else None),
        inherited_charged_cpu_seconds=charged, remaining_cpu_seconds=remaining,
        scientific_promotion=False, reliable_repair_speedup_established=False,
        canonical_dyadic_repair_state_implemented=False,
        limitations=['four new articles and sixty next-token predictions',
                     'one retained sixteen-token calibration article',
                     'separate target from power-of-two row grids',
                     'single prospective variant; no corpus-level inference',
                     'no changed-prefix avoidance or repair-speed claim'],
    )
    atomic_write(archive / 'summary.json', canonical_json(summary))
    atomic_write(archive / 'program-outcomes.json', canonical_json(dict(
        schema='v14-prospective-program-outcomes',
        prospective_program_sha256=digest((archive / 'prospective-program.json').read_bytes()),
        slots=[dict(id=row['id'], status=row['status']) for row in attempts],
        status='settled', scientific_promotion=False,
    )))
    print(json.dumps({key: value for key, value in summary.items() if key != 'quality'}, indent=2))


if __name__ == '__main__':
    main()
