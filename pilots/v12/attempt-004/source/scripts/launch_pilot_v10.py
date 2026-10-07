"""Execute or recover one frozen diagnostic under its original CPU ledger."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.worker_control import WorkerLimits, run_limited
from src.phase_budget import PhaseBudget
from src.experiment_inventory import source_hashes
from src.run_store import digest


def main():
    entries={
        'wikitext2-scalar':('feature-plan.json','scripts/run_feature_pilot.py','feature-worker','real-first-block-v1'),
        'wikitext2-accelerated':('wikitext2-accelerated-plan.json','pilots/v10/feature_accelerated.py','wikitext2-accelerated-worker','real-first-block-ordered-numpy-v1'),
        'c4-scalar':('c4-scalar-plan.json','scripts/run_feature_pilot.py','c4-scalar-worker','c4-real-first-block-scalar-v1'),
        'c4-accelerated':('c4-accelerated-plan.json','pilots/v10/feature_accelerated.py','c4-accelerated-worker','real-first-block-ordered-numpy-v1')}
    p=argparse.ArgumentParser();p.add_argument('pilot',choices=entries);args=p.parse_args()
    root=Path(__file__).resolve().parents[1];directory=root/'pilots/v10'
    protocol_path=root/'configs/protocol_v6.json';protocol=json.loads(protocol_path.read_bytes())
    if protocol['status']!='authorized_pilots_only_confirmation_blocked':
        raise ValueError('unexpected pilot authorization policy')
    ph=digest(protocol_path.read_bytes())
    budget=PhaseBudget(directory/'phase-cpu-budget',identity={'protocol_sha256':ph,'source_sha256':source_hashes(root)},
        phase_cpu_seconds={'feasibility':10800})
    limits=WorkerLimits.from_payload(protocol['resources']['worker_profiles']['preflight'])
    planname,script,output,label=entries[args.pilot];plan=directory/planname
    before=(directory/output/'result.json').exists()
    result=run_limited([sys.executable,str(root/script),str(plan)],directory/output,limits,
        identity={'pilot':label,'plan_sha256':digest(plan.read_bytes())},cwd=root,phase_budget=budget,phase='feasibility')
    print(json.dumps({'outcome':result['outcome'],'archived_receipt_already_present':before,
        'archived_receipt_is_not_new_timing':True,'resource_usage':result.get('resource_usage')}))


if __name__=='__main__':main()
