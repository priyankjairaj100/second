"""Read-only audit of saved v17 factors. No new quantization or model execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.compact_state import parse
from src.run_store import atomic_write,canonical_json,digest


def analyze(root):
    root=Path(root); states=[];bindings=[]
    for attempt in ('attempt-002','attempt-003'):
        base=root/'pilots/v17'/attempt
        plan=(base/'plan.json').read_bytes()
        receipt=json.loads((base/'worker/result.json').read_bytes())
        progress=json.loads((base/'outputs/progress.json').read_bytes())
        if (receipt['outcome']['status']!='complete'
            or receipt['budget_debit']['state']!='settled'
            or receipt['worker_identity']['plan_sha256']!=digest(plan)
            or progress['plan_sha256']!=digest(plan) or progress['status']!='complete'):
            raise ValueError('unverified source transaction')
        artifact=progress['state_artifact'];raw=(base/'outputs'/artifact['file']).read_bytes()
        if len(raw)!=artifact['bytes'] or digest(raw)!=artifact['sha256']:
            raise ValueError('state bytes differ from receipt')
        states.append(parse(raw,expected_sha256=artifact['sha256']))
        bindings.append(dict(attempt=attempt,plan_sha256=digest(plan),state_sha256=digest(raw)))
    original,retained=states
    if original.target_sha256!=retained.target_sha256:raise ValueError('target differs')
    old={(f.record_id,f.stage_id):f for f in original.factors}
    results=[]
    for factor in retained.factors:
        prior=old[(factor.record_id,factor.stage_id)]
        if prior.token_sha256!=factor.token_sha256:raise ValueError('record contents differ')
        a,b=prior.array(),factor.array()
        if a.shape!=b.shape:raise ValueError('factor shape differs')
        equal=a==b
        bit_equal=a.view(np.uint64)==b.view(np.uint64)
        results.append(dict(stage_id=factor.stage_id,record_id=factor.record_id,shape=list(a.shape),
            values=int(a.size),equal_values=int(equal.sum()),equal_binary64=int(bit_equal.sum()),
            all_values_equal=bool(equal.all()),max_absolute_change=float(np.max(np.abs(a-b))),
            max_original_magnitude=float(np.max(np.abs(a))),
            old_prefix_sha256=prior.prefix_sha256,new_prefix_sha256=factor.prefix_sha256))
    changed=[r for r in results if r['old_prefix_sha256']!=r['new_prefix_sha256']]
    return dict(schema='saved-factor-audit-v18',scope='analysis of archived arrays; no model execution',
        bindings=bindings,target_sha256=retained.target_sha256,rows=results,
        total_values=sum(r['values'] for r in results),
        equal_values=sum(r['equal_values'] for r in results),
        changed_prefix_pairs=len(changed),
        changed_prefix_values=sum(r['values'] for r in changed),
        changed_prefix_equal_values=sum(r['equal_values'] for r in changed),
        reusable_changed_prefix_factors=sum(r['all_values_equal'] for r in changed),
        universal_transport_impossibility=False,scientific_promotion=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('output exists')
    atomic_write(args.output,canonical_json(analyze(args.root)))
