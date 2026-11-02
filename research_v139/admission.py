"""Pure geometry screening; no model, data or successful calibration claim."""
from dataclasses import asdict
from fractions import Fraction
import json
from research_v43.dispatcher import StageSpec,ResourcePolicy,assess_stage
from research_v81.profile import SHAPES

def screen():
 p=ResourcePolicy();out=[]
 for records in (4,13,32,128):
  for kind in ('point','box'):
   for route in ('token','streamed'):
    stages=[]
    for i,(rows,width) in enumerate(SHAPES):
     # These identities/scales are synthetic: admission depends only on geometry.
     s=StageSpec('shape-'+str(i),'0'*64,rows,width,(1.0,)*rows,Fraction(1,100),Fraction(records*128),'1'*64)
     r=assess_stage(s,records*128,kind=kind,block_tokens=128,max_blocks=records,policy=p,resident_bytes=9*2**30,route=route)
     stages.append(r)
    total=sum(r['candidates'][route]['work_units'] for r in stages)*6
    limitations=[dict(stage=r['stage_id'],reason=r['candidates'][route]['refusal_reason'],work_units=r['candidates'][route]['work_units'],arrays=r['candidates'][route]['explicit_array_bytes']) for r in stages if not r['admitted']]
    out.append(dict(records=records,tokens=records*128,kind=kind,route=route,distilgpt2_shape_stages=24,stage_geometry_admitted=all(r['admitted'] for r in stages),required_request_work_units=total,request_work_admitted=total<=p.max_request_work_units,shape_admitted=all(r['admitted'] for r in stages) and total<=p.max_request_work_units,limitations=limitations,stages=stages))
 # Service-level compression must also reserve a full point-token fallback.
 complete=[]
 for records in (4,13,32,128):
  point=next(r for r in out if r['records']==records and r['kind']=='point' and r['route']=='token')
  boxes=next(r for r in out if r['records']==records and r['kind']=='box' and r['route']=='token')
  combined=[a['candidates']['token']['work_units']+b['candidates']['token']['work_units'] for a,b in zip(point['stages'],boxes['stages'])]
  complete.append(dict(records=records,point_token_shape_admitted=point['shape_admitted'],compressed_token_with_point_fallback_admitted=point['shape_admitted'] and boxes['shape_admitted'] and max(combined)<=p.max_stage_work_units and sum(combined)*6<=p.max_request_work_units,box_plus_fallback_stage_work=combined,total_work=sum(combined)*6,current_service_record_cap_admitted=records<=4))
 return dict(schema='prospective-shape-screen-v139',policy=asdict(p),scope='hypothetical DistilGPT2 roots; no loaded checkpoint, new target, dataset selection or model execution',empirical_evidence=False,matched_service_max_records=4,new_service_registration_required=True,codec_supported_bits=[16,24,32,40,48],rows=out,complete_point_policy=complete)
if __name__=='__main__':print(json.dumps(screen(),indent=2,sort_keys=True))
