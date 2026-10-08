"""Hash-check saved diagnostic codes and summarize zeros, without model execution."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('attempt',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    index_path=a.attempt/'outputs/model-index.json'
    index=json.loads(index_path.read_bytes())
    rows=[]
    for s in index['stages']:
        raw=(index_path.parent/s['codes_file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=s['codes_sha256']:raise ValueError('code digest mismatch')
        outputs,width=s['shape'];count=outputs*width
        if len(raw)!=8*count:raise ValueError('code shape mismatch')
        zeros=sum(x==0 for x, in struct.iter_unpack('<d',raw))
        row={'stage_id':s['stage_id'],'values':count,'zeros':zeros,'zero_fraction':zeros/count,'codes_sha256':s['codes_sha256']}
        if s['stage_id'].endswith('.qkv'):
            if outputs!=3*width:raise ValueError('unexpected packed QKV shape')
            stride=width*width*8
            row['qkv_zero_fractions']={name:sum(x==0 for x, in struct.iter_unpack('<d',raw[i*stride:(i+1)*stride]))/(width*width) for i,name in enumerate(['query','key','value'])}
        rows.append(row)
    result={'schema':'v12-code-distribution-diagnostic','attempt':a.attempt.name,'model_index_sha256':hashlib.sha256(index_path.read_bytes()).hexdigest(),'rows':rows,'values':sum(r['values'] for r in rows),'zeros':sum(r['zeros'] for r in rows),'scope':'Descriptive output-code sparsity only. No attribution, quality, or speed conclusion follows.'}
    if a.output.exists():raise ValueError('do not overwrite an analysis artifact')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'values':result['values'],'zero_fraction':result['zeros']/result['values']}))


if __name__=='__main__':main()
