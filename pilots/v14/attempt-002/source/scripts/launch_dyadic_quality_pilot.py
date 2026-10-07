"""Admit the registered finer-grid quality control without resetting CPU costs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json,atomic_write,digest
from src.experiment_inventory import source_hashes
from src.pilot_budget import inherited_allowance,research_worker_lock
from src.worker_control import WorkerLimits,run_limited
from src.phase_budget import PhaseBudget
from src.dyadic_quality_validation import bound_file,read_bound,capture_generation,load_generation,validate_quality_inputs


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--id',required=True);p.add_argument('--dyadic-attempt',required=True);args=p.parse_args()
    if any(not s.replace('-','').isalnum() for s in (args.id,args.dyadic_attempt)):raise ValueError('invalid attempt ID')
    root=Path(__file__).resolve().parents[1];archive=root/'pilots/v14';attempt=archive/args.id
    if attempt.exists():raise ValueError('attempt exists')
    used,cap=inherited_allowance(root)
    if cap<902:raise ValueError('insufficient inherited allowance')
    fine=archive/args.dyadic_attempt;reference=root/'pilots/v13/attempt-003'
    fine_evidence=capture_generation(fine,'dyadic');reference_evidence=capture_generation(reference,'power2')
    cp=root/'tmp/models/distilgpt2';hashes={}
    for name in ['config.json','model.safetensors']:
        with (cp/name).open('rb') as f:hashes[name]=hashlib.file_digest(f,'sha256').hexdigest()
    evaluation=bound_file(archive/'quality-records.json')
    calibration=bound_file(root/'pilots/v10/wikitext2/preflight-records.json')
    previous=[bound_file(root/path) for path in ['pilots/v12/wikitext-heldout.json','pilots/v13/quality-records.json']]
    fine_plan,fine_progress,_=load_generation(fine_evidence)
    reference_plan,reference_progress,_=load_generation(reference_evidence)
    validate_quality_inputs(json.loads(read_bound(evaluation)),json.loads(read_bound(calibration)),
        [json.loads(read_bound(item)) for item in previous],fine_plan,fine_progress,reference_plan,reference_progress,
        hashes,calibration['sha256'])
    snapshot=attempt/'source';snapshot.mkdir(parents=True)
    for folder in ['src','scripts']:
        (snapshot/folder).mkdir()
        for path in (root/folder).glob('*.py'):shutil.copyfile(path,snapshot/folder/path.name)
    policy=dict(schema='dyadic-quality-policy-v14',prior_charged_cpu_seconds=used,remaining_allowance_cpu_seconds=cap,
        inherited_cap_cpu_seconds=10800,scientific_promotion=False,scope='one prospective four-bit grid control on new fixed development articles')
    atomic_write(attempt/'protocol.json',canonical_json(policy));ph=digest(canonical_json(policy))
    plan=dict(checkpoint=str(cp),checkpoint_sha256=hashes,output=str(attempt/'outputs'),protocol_sha256=ph,source_sha256=source_hashes(snapshot),
        evaluation=evaluation,calibration_records=calibration,previous_evaluations=previous,
        dyadic_generation=fine_evidence,power2_generation=reference_evidence)
    planpath=attempt/'plan.json';atomic_write(planpath,canonical_json(plan))
    from src.runtime_contract import capture_runtime_contract
    atomic_write(attempt/'runtime.json',canonical_json(capture_runtime_contract()))
    budget=PhaseBudget(attempt/'phase-cpu-budget',identity={'protocol_sha256':ph,'source_sha256':source_hashes(snapshot)},phase_cpu_seconds={'feasibility':cap})
    result=run_limited([sys.executable,str(snapshot/'scripts/run_dyadic_quality_pilot.py'),str(planpath)],attempt/'worker',WorkerLimits(900,900,6*2**30,1,(min(os.sched_getaffinity(0)),)),
        identity={'pilot':'dyadic-quality-v14','plan_sha256':digest(planpath.read_bytes())},cwd=snapshot,phase_budget=budget,phase='feasibility')
    print(json.dumps({'outcome':result['outcome'],'budget_debit':result.get('budget_debit')}))


if __name__=='__main__':
    with research_worker_lock(Path(__file__).resolve().parents[1]):main()
