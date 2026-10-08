"""Restore a documented missing reservation; never manufacture measured usage."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.phase_budget import PhaseBudget
from src.pilot_budget import research_worker_lock
from src.run_store import canonical_json,digest,atomic_write


def main():
    root=ROOT/'campaigns/fixed_feature_v23'; incident=root/'incidents/warm-cold-001'
    report_path=incident/'accounting-reconciliation.json'
    if report_path.exists():raise ValueError('reconciliation already recorded')
    manifest=json.loads((incident/'preserved.json').read_bytes())
    for name,entry in manifest.items():
        raw=(incident/name).read_bytes()
        if digest(raw)!=entry['sha256'] or len(raw)!=entry['bytes']:raise ValueError('preserved evidence changed')
    status=json.loads((incident/'attempts/warm-cold-001/worker/result.json').read_bytes())
    identity=json.loads((incident/'attempts/warm-cold-001/worker/identity.json').read_bytes())
    before=(root/'phase-cpu-budget/ledger.json').read_bytes(); ledger=json.loads(before)
    if before!=(incident/'phase-cpu-budget/ledger.json').read_bytes():raise ValueError('ledger changed since incident')
    attempt=status['budget_attempt_id']; row=status['budget_debit']
    expected=digest(canonical_json({'worker':identity,'attempt':str(root/'attempts/warm-cold-001/worker/attempt-0001')}))
    if attempt!=expected or row!={'phase':'feasibility','reserved_cpu_seconds':122,'state':'reserved','charged_cpu_seconds':122,'observed_cpu_ns':None}:
        raise ValueError('reservation identity or amount differs')
    if digest(canonical_json(ledger['binding']))!=identity['phase_budget']['binding_sha256']:
        raise ValueError('budget identity differs')
    if attempt in ledger['attempts']:raise ValueError('reservation already present')
    budget=PhaseBudget(root/'phase-cpu-budget',identity=ledger['binding']['identity'],phase_cpu_seconds={'feasibility':900})
    with budget._locked():
        current=budget._read()
        if canonical_json(current)!=before:raise ValueError('concurrent ledger mutation')
        current['attempts'][attempt]=row
        budget._save(current)
    after=(root/'phase-cpu-budget/ledger.json').read_bytes()
    report=dict(schema='explicit-missing-reservation-reconciliation-v23',cause='unknown',
        evidence_manifest_sha256=digest((incident/'preserved.json').read_bytes()),
        script_sha256=digest(Path(__file__).read_bytes()),ledger_before_sha256=digest(before),
        ledger_after_sha256=digest(after),restored_attempt_id=attempt,restored_row=row,
        observed_cpu_ns=None,outer_transaction_elapsed_ns=None,
        reservation_disposition='permanently held as unavailable usage; not a settled measurement',
        recorded_cpu_seconds=251,unknown_reserved_cpu_seconds=122,total_charged_or_reserved_cpu_seconds=373,
        remaining_cpu_seconds=527,legacy_reset=False,original_campaign_status='stopped',
        numerical_output='complete progress and exact model; no sealed transaction',
        forbidden_inferences=['no fabricated CPU usage','no complete timing from worker-body duration'])
    atomic_write(report_path,canonical_json(report));print(json.dumps(report))


if __name__=='__main__':
    with research_worker_lock(ROOT):main()
