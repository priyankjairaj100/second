"""Freeze source copies, carry prior CPU debits, and launch one bounded pilot."""
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
    p.add_argument('--revision',choices=['v12','v14'],default='v12')
    p.add_argument('--dataset',choices=['wikitext2','c4'],default='wikitext2')
    p.add_argument('--mode',choices=['load_forward','first_stage_quantization','full_quantization','model_quality'],default='load_forward')
    p.add_argument('--grid-axis',choices=['column','row','dyadic_row'],default='column')
    p.add_argument('--delete-index',type=int,choices=[0,1])
    p.add_argument('--compare-attempt')
    args=p.parse_args()
    if not args.id.replace('-','').isalnum():raise ValueError('invalid attempt ID')
    root=Path(__file__).resolve().parents[1];archive=root/'pilots'/args.revision
    attempt=archive/args.id
    if attempt.exists():raise ValueError('use a new attempt ID; never overwrite observations')
    from src.pilot_budget import inherited_allowance
    used,cap=inherited_allowance(root)
    if cap<902:raise ValueError('remaining inherited feasibility allowance cannot admit this worker')
    snapshot=attempt/'source';snapshot.mkdir(parents=True)
    for folder in ['src','scripts']:
        (snapshot/folder).mkdir()
        for path in (root/folder).glob('*.py'):
            shutil.copyfile(path,snapshot/folder/path.name)
    policy={'schema':'compact-admission-policy-v12','date':'2026-10-07','status':'authorized_bounded_diagnostics_confirmation_blocked',
      'inherited_cap_cpu_seconds':10800,'prior_charged_cpu_seconds':used,'remaining_allowance_cpu_seconds':cap,
      'original_resource_gate_unchanged':True,'scope':'bounded compact checkpoint, finite features, and token-space quantizer diagnostics; no repair claim',
      'attempt_id':args.id,'dataset':args.dataset,'revision':args.revision,'quantizer_variant':args.grid_axis}
    atomic_write(attempt/'protocol.json',canonical_json(policy));ph=digest(canonical_json(policy))
    cp=root/'tmp/models/distilgpt2'
    hashes={}
    for name in ['config.json','model.safetensors']:
        with (cp/name).open('rb') as f:hashes[name]=hashlib.file_digest(f,'sha256').hexdigest()
    records=root/f'pilots/v10/{args.dataset}/preflight-records.json'
    plan={'mode':args.mode,'grid_axis':args.grid_axis,'parameter_identity_encoding':'binary64_tree_v2',
      'weight_digest_encoding':'binary64_matrix_v1','primitive_backend':'mpfr_enclosure','checkpoint':str(cp),'checkpoint_sha256':hashes,'records':str(records),
      'records_sha256':digest(records.read_bytes()),'output':str(attempt/'outputs'),
      'source_sha256':source_hashes(snapshot),'protocol_sha256':ph}
    original_records=json.loads(records.read_bytes())['records']
    plan['deleted_record_ids']=[] if args.delete_index is None else [sorted(r['id'] for r in original_records)[args.delete_index]]
    if args.compare_attempt:
        if not args.compare_attempt.replace('-','').isalnum():raise ValueError('invalid comparison attempt')
        other=archive/args.compare_attempt
        prior=json.loads((other/'outputs/progress.json').read_bytes())
        prior_plan=json.loads((other/'plan.json').read_bytes())
        if prior['status']!='complete' or not prior.get('full_model_quantization'):raise ValueError('comparison needs completed full-model codes')
        if prior_plan['records_sha256']!=plan['records_sha256'] or (prior_plan.get('deleted_record_ids',[]) and args.mode!='model_quality'):raise ValueError('comparison needs the same original records')
        plan['comparison_model']={'index':str(other/'outputs/model-index.json'),
            'index_sha256':digest((other/'outputs/model-index.json').read_bytes()),'target_sha256':prior['target_sha256'],
            'plan':str(other/'plan.json'),'plan_sha256':digest((other/'plan.json').read_bytes())}
    if args.mode=='model_quality':
        if args.dataset!='wikitext2' or not args.compare_attempt:raise ValueError('quality pilot requires WikiText and a completed model')
        evaluation=archive/'wikitext-heldout.json'
        plan['evaluation_records']=str(evaluation)
        plan['evaluation_records_sha256']=digest(evaluation.read_bytes())
    planpath=attempt/'plan.json';atomic_write(planpath,canonical_json(plan))
    from src.runtime_contract import capture_runtime_contract
    atomic_write(attempt/'runtime.json',canonical_json(capture_runtime_contract()))
    limits=WorkerLimits(900,900,6*2**30,1,(min(os.sched_getaffinity(0)),))
    budget=PhaseBudget(attempt/'phase-cpu-budget',identity={'protocol_sha256':ph,'source_sha256':source_hashes(snapshot)},phase_cpu_seconds={'feasibility':cap})
    result=run_limited([sys.executable,str(snapshot/'scripts/run_compact_pilot.py'),str(planpath)],attempt/'worker',limits,
        identity={'pilot':'compact-checkpoint-real-forward-v12','plan_sha256':digest(planpath.read_bytes())},cwd=snapshot,
        phase_budget=budget,phase='feasibility')
    print(json.dumps({'outcome':result['outcome'],'budget_debit':result.get('budget_debit'),'resource_usage':result.get('resource_usage')}))


if __name__=='__main__':
    from src.pilot_budget import research_worker_lock
    with research_worker_lock(Path(__file__).resolve().parents[1]):main()
