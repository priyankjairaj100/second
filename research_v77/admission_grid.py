"""Shape-only prospective screening; no model weights or numerical execution."""
from dataclasses import asdict
from fractions import Fraction
import hashlib,json,sys
from pathlib import Path
R=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(R))
from research_v43.dispatcher import StageSpec,ResourcePolicy,assess_stage

policy=ResourcePolicy();rows=[]
for blocks in (6,12):
    for tokens in (128,256,384,512,768,1024,1536,1664):
        for reserve in (8*2**30,9*2**30):
            for kind in ('point','box'):
                stages=[];units=0;ok=True
                for i,(outputs,width) in enumerate(((2304,768),(768,768),(3072,768),(768,3072))):
                    spec=StageSpec('shape-only-'+str(i),'a'*64,outputs,width,(1.,)*outputs,Fraction(1,100),Fraction(1664),'b'*64)
                    report=assess_stage(spec,tokens,kind=kind,block_tokens=128,max_blocks=tokens//128,resident_bytes=reserve)
                    ok &= report['admitted'];units+=report['work_units']*blocks
                    item=dict(rows=outputs,width=width,selected=report['selected_route'],admitted=report['admitted'],
                        work_units=report['work_units'],array_bytes=report['explicit_array_bytes'],candidates=report['candidates'])
                    if kind=='box':
                        fallback=assess_stage(spec,tokens,kind='point',block_tokens=128,max_blocks=tokens//128,resident_bytes=reserve)
                        ok &= fallback['admitted'];units+=fallback['work_units']*blocks
                        item['point_fallback']=dict(selected=fallback['selected_route'],admitted=fallback['admitted'],work_units=fallback['work_units'])
                    stages.append(item)
                rows.append(dict(blocks=blocks,stages=4*blocks,tokens=tokens,resident_bytes=reserve,kind=kind,
                    stage_admitted=bool(ok),work_units=units,whole_request_admitted=bool(ok and units<=policy.max_request_work_units),
                    four_stage_geometry=stages,raw_feature_bytes=tokens*sum(s['width'] for s in stages)*blocks*8,
                    code_count=blocks*sum(s['rows']*s['width'] for s in stages)))
result=dict(scope='Shape-only route and structural work screen; not target admission, measured memory, latency or transfer evidence',
    placeholder_weights_and_scales=True,policy=asdict(policy),rows=rows,
    source_sha256=hashlib.sha256((R/'research_v43/dispatcher.py').read_bytes()).hexdigest())
Path(__file__).with_name('admission-grid.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps([dict(blocks=r['blocks'],tokens=r['tokens'],kind=r['kind'],admitted=r['whole_request_admitted'],work=r['work_units'],routes=[s['selected'] for s in r['four_stage_geometry']]) for r in rows if r['resident_bytes']==9*2**30 and r['tokens'] in (768,1536,1664)],indent=2))
