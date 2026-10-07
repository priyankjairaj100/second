"""Compare exact packed codes and current-prefix factors without model execution."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.compact_state import parse
from src.run_store import digest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--initial',type=Path,default=Path('pilots/v13/attempt-002/outputs/state.bin'))
    p.add_argument('--retained',type=Path,default=Path('pilots/v13/attempt-003/outputs/state.bin'))
    p.add_argument('--output',type=Path,default=Path('pilots/v13/deletion-propagation.json'))
    args=p.parse_args();initial=args.initial.read_bytes();retained=args.retained.read_bytes()
    a=parse(initial);b=parse(retained)
    if a.target_sha256!=b.target_sha256:raise ValueError('targets differ')
    af={(f.stage_id,f.record_id):f for f in a.factors};bf={(f.stage_id,f.record_id):f for f in b.factors};rows=[]
    if not set(b.record_ids)<=set(a.record_ids):raise ValueError('retained records are not a subset')
    for old,new in zip(a.stages,b.stages):
        if (old.stage_id,old.grid_axis,old.bits,old.scale_exponents)!=(new.stage_id,new.grid_axis,new.bits,new.scale_exponents):raise ValueError('grid bindings differ')
        factors=[]
        for rid in b.record_ids:
            x=af[(old.stage_id,rid)];y=bf[(old.stage_id,rid)];xa=x.array();ya=y.array()
            if x.token_sha256!=y.token_sha256 or xa.shape!=ya.shape:raise ValueError('retained record changed')
            factors.append(dict(record_id=rid,values=xa.size,changed_values=int(np.count_nonzero(xa.view(np.uint64)!=ya.view(np.uint64))),prefix_changed=x.prefix_sha256!=y.prefix_sha256))
        rows.append(dict(stage_id=old.stage_id,values=old.rows*old.columns,changed_codes=int(np.count_nonzero(old.indices_array()!=new.indices_array())),retained_factors=factors))
    out=dict(schema='v13-exact-deletion-propagation',original_state_sha256=digest(initial),retained_state_sha256=digest(retained),retained_ids=list(b.record_ids),
        changed_codes=sum(r['changed_codes'] for r in rows),code_values=sum(r['values'] for r in rows),
        retained_factor_values=sum(f['values'] for r in rows for f in r['retained_factors']),changed_retained_factor_values=sum(f['changed_values'] for r in rows for f in r['retained_factors']),
        stages=rows,scope='one tiny real deletion; canonical factors normalize signed zero; no population inference')
    args.output.write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':main()
