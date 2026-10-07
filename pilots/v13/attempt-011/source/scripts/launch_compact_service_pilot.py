"""Freeze sources and run one complete compact transaction within inherited limits."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json,atomic_write,digest
from src.experiment_inventory import source_hashes
from src.worker_control import WorkerLimits,run_limited
from src.phase_budget import PhaseBudget


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id',required=True)
    p.add_argument('--method',choices=['model_only_fresh','repair','indexed_fresh','direct_fresh','quality'],default='direct_fresh')
    p.add_argument('--delete-index',type=int,action='append',choices=[0,1],default=[])
    p.add_argument('--prior-attempt')
    p.add_argument('--solver-backend',choices=['reference','batched'],default='reference')
    p.add_argument('--dataset',choices=['wikitext2','c4'],default='wikitext2')
    args=p.parse_args()
    if not args.id.replace('-','').isalnum():raise ValueError('invalid attempt ID')
    root=Path(__file__).resolve().parents[1];archive=root/'pilots/v13';attempt=archive/args.id
    if attempt.exists():raise ValueError('attempt exists; failures cannot be overwritten')
    from src.pilot_budget import inherited_allowance
    used,cap=inherited_allowance(root)
    if cap<902:raise ValueError('insufficient inherited feasibility allowance')
    records=root/f'pilots/v10/{args.dataset}/preflight-records.json'
    original=json.loads(records.read_bytes())['records'];ids=sorted(r['id'] for r in original)
    if len(set(args.delete_index))!=len(args.delete_index):raise ValueError('duplicate deletion index')
    prior=None
    if args.prior_attempt:
        if not args.prior_attempt.replace('-','').isalnum():raise ValueError('invalid prior ID')
        previous=archive/args.prior_attempt
        status=json.loads((previous/'outputs/progress.json').read_bytes())
        if status['status']!='complete' or not status.get('complete_state'):raise ValueError('prior state is incomplete')
        state=previous/'outputs/state.bin'
        prior=dict(path=str(state),sha256=status['state_artifact']['sha256'])
        if digest(state.read_bytes())!=prior['sha256']:raise ValueError('prior artifact changed')
    if (args.method in ('repair','indexed_fresh','quality'))!=(prior is not None):raise ValueError('indexed methods require a prior state')
    snapshot=attempt/'source';snapshot.mkdir(parents=True)
    for folder in ['src','scripts']:
        (snapshot/folder).mkdir()
        for path in (root/folder).glob('*.py'):shutil.copyfile(path,snapshot/folder/path.name)
    policy=dict(schema='compact-service-diagnostic-policy-v13',attempt_id=args.id,
        inherited_cap_cpu_seconds=10800,prior_charged_cpu_seconds=used,remaining_allowance_cpu_seconds=cap,
        scope='complete factor_identity_v1 transaction; no transport avoidance or primary promotion',
        state_contract='packed exact model plus exact retained factors at current ancestor prefixes',
        mode=args.method,solver_backend=args.solver_backend,dataset=args.dataset,
        numerical_target='fixed output-row four-bit grids, V_cert finite features, original normalization 32',
        os_cache='uncontrolled',other_machine_activity='uncontrolled',scientific_promotion=False)
    atomic_write(attempt/'protocol.json',canonical_json(policy));ph=digest(canonical_json(policy))
    cp=root/'tmp/models/distilgpt2';hashes={}
    for name in ['config.json','model.safetensors']:
        with (cp/name).open('rb') as f:hashes[name]=hashlib.file_digest(f,'sha256').hexdigest()
    plan=dict(method=args.method,solver_backend=args.solver_backend,dataset=args.dataset,checkpoint=str(cp),checkpoint_sha256=hashes,records=str(records),
        records_sha256=digest(records.read_bytes()),deleted_record_ids=[ids[i] for i in args.delete_index],
        prior_state=prior,output=str(attempt/'outputs'),source_sha256=source_hashes(snapshot),protocol_sha256=ph)
    worker='run_compact_service_pilot.py'
    if args.method=='quality':
        worker='run_v13_quality_pilot.py'
        evaluation=archive/'quality-records.json'
        plan.update(evaluation_records=str(evaluation),evaluation_records_sha256=digest(evaluation.read_bytes()),
            model_order=json.loads(evaluation.read_bytes())['model_order'],
            quantized_model=dict(path=str(previous/'outputs/model.bin'),sha256=status['model_artifact']['sha256']))
    planpath=attempt/'plan.json';atomic_write(planpath,canonical_json(plan))
    from src.runtime_contract import capture_runtime_contract
    atomic_write(attempt/'runtime.json',canonical_json(capture_runtime_contract()))
    limits=WorkerLimits(900,900,6*2**30,1,(min(os.sched_getaffinity(0)),))
    budget=PhaseBudget(attempt/'phase-cpu-budget',identity={'protocol_sha256':ph,'source_sha256':source_hashes(snapshot)},phase_cpu_seconds={'feasibility':cap})
    result=run_limited([sys.executable,str(snapshot/'scripts'/worker),str(planpath)],attempt/'worker',limits,
        identity={'pilot':'compact-complete-service-v13','plan_sha256':digest(planpath.read_bytes())},cwd=snapshot,
        phase_budget=budget,phase='feasibility')
    print(json.dumps({'outcome':result['outcome'],'budget_debit':result.get('budget_debit'),'resource_usage':result.get('resource_usage')}))


if __name__=='__main__':
    from src.pilot_budget import research_worker_lock
    with research_worker_lock(Path(__file__).resolve().parents[1]):main()
