"""Extract complete transaction evidence without promoting diagnostic clocks."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json,atomic_write,digest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,default=Path('pilots/v13'));args=p.parse_args();archive=args.archive
    results={};attempts=[];charged=4283;reserved=0
    for directory in sorted(archive.glob('attempt-*')):
        resultpath=directory/'worker/result.json';ledgerpath=directory/'phase-cpu-budget/ledger.json';progresspath=directory/'outputs/progress.json'
        if not resultpath.exists():continue
        receipt=json.loads(resultpath.read_bytes());progress=json.loads(progresspath.read_bytes()) if progresspath.exists() else {}
        ledger=json.loads(ledgerpath.read_bytes())
        settled=all(x['state']=='settled' for x in ledger['attempts'].values()) and receipt.get('budget_debit',{}).get('state')=='settled'
        debits=sum(x['charged_cpu_seconds'] for x in ledger['attempts'].values())
        if settled:charged+=debits
        else:reserved+=debits
        state='running' if not settled else receipt['outcome']['status']
        row=dict(id=directory.name,status=state,settled=settled,charged_or_reserved_cpu_seconds=debits,
            receipt_sha256=digest(resultpath.read_bytes()),progress_sha256=digest(progresspath.read_bytes()) if progresspath.exists() else None,
            worker_wall_seconds=receipt.get('outcome',{}).get('elapsed_wall_ns',0)/1e9,
            worker_cpu_seconds=receipt.get('resource_usage',{}).get('total_cpu_ns',0)/1e9,
            peak_rss_bytes=progress.get('peak_rss_bytes'))
        if state=='complete':
            if progress.get('status')!='complete':raise ValueError('receipt/progress mismatch')
            results[directory.name]=progress
            row.update(method=progress.get('method','quality'),model_sha256=progress.get('model_sha256'),
                state_sha256=progress.get('state_artifact',{}).get('sha256'),
                state_bytes=progress.get('state_artifact',{}).get('bytes'),diagnostics=progress.get('diagnostics'))
        attempts.append(row)
    methods=['attempt-003','attempt-004','attempt-005','attempt-006']
    complete=all(x in results for x in methods)
    comparison=dict(all_four_complete=complete,all_models_equal=None,all_states_equal=None)
    if complete:
        comparison.update(all_models_equal=len({results[x]['model_sha256'] for x in methods})==1,
            all_states_equal=len({results[x]['state_artifact']['sha256'] for x in methods if results[x]['complete_state']})==1,
            compared_models=4,compared_states=3,independent_neural_implementations=False,
            changed_ancestor_pairs=results['attempt-003']['diagnostics']['changed_ancestor_factor_pairs'],
            changed_ancestor_pairs_avoided=results['attempt-003']['diagnostics']['changed_ancestor_pairs_avoided'])
    sequential=None
    if all(x in results for x in ['attempt-007','attempt-008']):sequential=results['attempt-007']['state_artifact']['sha256']==results['attempt-008']['state_artifact']['sha256']
    batching=None
    if all(x in results for x in ['attempt-010','attempt-011','attempt-006']):
        batching=dict(all_models_match_reference=len({results[x]['model_sha256'] for x in ['attempt-010','attempt-011','attempt-006']})==1,
            repaired_state_matches_reference=results['attempt-010']['state_artifact']['sha256']==results['attempt-006']['state_artifact']['sha256'])
    summary=dict(schema='v13-complete-service-evidence',attempts=attempts,
        completed=sum(x['status']=='complete' for x in attempts),failed=sum(x['status']=='failed' for x in attempts),
        running=sum(x['status']=='running' for x in attempts),inherited_charged_cpu_seconds=charged,reserved_cpu_seconds=reserved,
        unreserved_remaining_cpu_seconds=10800-charged-reserved,comparison=comparison,
        sequence_equals_combined=sequential,batching=batching,quality=results.get('attempt-009',{}).get('quality'),
        quality_ratios=results.get('attempt-009',{}).get('ratios_to_base'),
        reliable_repair_speedup_established=False,preparation_inclusive_lifetime_evaluated=False,scientific_promotion=False,
        limitations=['one tiny original root','shared numerical kernels','uncontrolled OS cache and machine activity',
            'identity cache has zero changed-ancestor avoidance','complete registered feasibility workload unevaluated'])
    atomic_write(archive/'summary.json',canonical_json(summary));print(json.dumps({k:v for k,v in summary.items() if k not in ('attempts','quality')},indent=2))


if __name__=='__main__':main()
