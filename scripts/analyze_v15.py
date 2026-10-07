"""Verify complete dyadic transactions and their explicit v14 code bridge."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pilot_budget import inherited_allowance
from src.run_store import atomic_write, canonical_json, digest


def main():
    root = Path(__file__).resolve().parents[1]
    archive = root / 'pilots/v15'
    attempts = []; results = {}
    for directory in sorted(archive.glob('attempt-*')):
        receipt_path = directory / 'worker/result.json'
        if not receipt_path.exists():
            continue
        receipt = json.loads(receipt_path.read_bytes())
        ledger = json.loads((directory / 'phase-cpu-budget/ledger.json').read_bytes())
        if (receipt.get('budget_debit', {}).get('state') != 'settled'
                or any(row['state'] != 'settled' for row in ledger['attempts'].values())):
            raise ValueError('settle every worker before final analysis')
        progress_path = directory / 'outputs/progress.json'
        progress = json.loads(progress_path.read_bytes()) if progress_path.exists() else {}
        status = receipt['outcome']['status']
        if status == 'complete':
            if progress.get('status') != 'complete':
                raise ValueError('receipt/progress mismatch')
            results[directory.name] = progress
        attempts.append(dict(id=directory.name, method=progress.get('method'), status=status,
            receipt_sha256=digest(receipt_path.read_bytes()),
            progress_sha256=digest(progress_path.read_bytes()) if progress_path.exists() else None,
            worker_wall_seconds=receipt['outcome']['elapsed_wall_ns']/1e9,
            charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],
            peak_rss_bytes=progress.get('peak_rss_bytes'),
            model_sha256=progress.get('model_sha256'), state_artifact=progress.get('state_artifact'),
            diagnostics=progress.get('diagnostics')))
    selected = ['attempt-002','attempt-003','attempt-004','attempt-005']
    complete = all(name in results for name in selected)
    comparison = dict(all_four_complete=complete, all_models_equal=None, all_states_equal=None)
    if complete:
        comparison.update(all_models_equal=len({results[name]['model_sha256'] for name in selected})==1,
            all_states_equal=len({results[name]['state_artifact']['sha256'] for name in selected
                                  if results[name]['complete_state']})==1,
            compared_models=4, compared_states=3, shared_numerical_kernels=True,
            changed_ancestor_factor_pairs=results['attempt-002']['diagnostics']['changed_ancestor_factor_pairs'],
            changed_ancestor_pairs_avoided=results['attempt-002']['diagnostics']['changed_ancestor_pairs_avoided'])
    bridge = None
    if 'attempt-002' in results:
        import numpy as np
        from src.compact_state import parse
        result = results['attempt-002']
        model_path = archive/'attempt-002/outputs/model.bin'
        model = parse(model_path.read_bytes(),expected_sha256=result['model_artifact']['sha256'])
        oldroot = root/'pilots/v14/attempt-001/outputs'
        oldindex = json.loads((oldroot/'model-index.json').read_bytes())
        oldprogress = json.loads((oldroot/'progress.json').read_bytes())
        if oldindex['stages'] != oldprogress['stages']:
            raise ValueError('old model index differs from completed generation')
        if len(model.stages) != len(oldindex['stages']):
            raise ValueError('incomplete bridge model')
        rows=[]
        for codes, entry in zip(model.stages,oldindex['stages']):
            if codes.stage_id != entry['stage_id'] or list(codes.shape) != entry['shape']:
                raise ValueError('bridge stage mismatch')
            raw=(oldroot/entry['codes_file']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=entry['codes_sha256']:
                raise ValueError('old code artifact changed')
            old=np.frombuffer(raw,dtype='<f8').reshape(entry['shape'])
            new=codes.array()
            rows.append(dict(stage_id=codes.stage_id,values=new.size,
                             unequal_values=int(np.count_nonzero(old.view(np.uint64)!=new.view(np.uint64)))))
        bridge=dict(schema='v15-v14-decoded-code-bridge',old_target_sha256=oldindex['target_sha256'],
            new_target_sha256=model.target_sha256,target_hashes_equal=oldindex['target_sha256']==model.target_sha256,
            old_index_sha256=digest((oldroot/'model-index.json').read_bytes()),new_model_sha256=digest(model_path.read_bytes()),
            total_values=sum(row['values'] for row in rows),unequal_values=sum(row['unequal_values'] for row in rows),
            stages=rows,scope='same retained membership; explicit code equality across constructor-validation versions; not target-hash equivalence')
        atomic_write(archive/'v14-code-bridge.json',canonical_json(bridge))
    charged,remaining=inherited_allowance(root)
    summary=dict(schema='v15-dyadic-complete-state-evidence',attempts=attempts,comparison=comparison,
        v14_code_bridge=bridge,inherited_charged_cpu_seconds=charged,remaining_cpu_seconds=remaining,
        scientific_promotion=False,reliable_repair_speedup_established=False,
        preparation_inclusive_lifetime_evaluated=False,
        limitations=['one tiny original root','shared numerical kernels','zero changed-ancestor avoidance',
                     'uncontrolled OS cache and machine activity','registered feasibility and confirmation remain unmet'])
    atomic_write(archive/'summary.json',canonical_json(summary))
    print(json.dumps({key:value for key,value in summary.items() if key not in ('attempts','v14_code_bridge')},indent=2))
    if bridge:
        print(json.dumps({key:value for key,value in bridge.items() if key!='stages'},indent=2))


if __name__=='__main__':main()
