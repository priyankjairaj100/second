"""One existing token solve. No streamed attempt, target change or retry."""
import numpy as np
from research_v43 import dispatcher
from research_v80.io import require
from research_v110.config import STAGE
from src import fixed_lossless_codec_v29 as codec
from src.compact_state import StageCodes
from src.run_store import digest, canonical_json


def select_stage(stages):
    matches=[s for s in stages if s.stage_id==STAGE]
    require(len(matches)==1,'Exactly one registered diagnostic stage required')
    stage=matches[0]
    require((len(stage.weights),stage.width)==(3072,768),'Registered stage shape differs')
    return stage


def decode_points(stage,rows,payloads,target_sha,anchor_sha):
    require(len(rows)==3 and all(len(r['tokens'])==128 for r in rows)
        and rows==sorted(rows,key=lambda r:r['id']) and len({r['id'] for r in rows})==3,
        'Exact three ordered distinct retained records required')
    points=[];identities=[]
    for row in rows:
        blob=payloads[stage.stage_id,row['id']]
        d=codec.parse(blob,expected_sha256=digest(blob))
        require(d.target_sha256==target_sha and d.anchor_target_sha256==anchor_sha
            and d.stage_id==stage.stage_id and d.record_id==row['id']
            and d.token_sha256==digest(canonical_json(row['tokens']))
            and d.shape==(128,768),'Retained point source binding differs')
        point=np.ascontiguousarray(d.array().T)
        require(point.shape==(768,128) and np.isfinite(point).all(),'Finite registered point extent required')
        points.append(point)
        identities.append(dict(record_id=row['id'],payload_sha256=digest(blob),
            source_sha256=d.source_sha256,point_sha256=digest(point.T.astype('<f8').tobytes())))
        require(identities[-1]['source_sha256']==identities[-1]['point_sha256'],'Decoded point bytes differ')
    return points,identities


def solve_token(spec,weights,points,*,policy=None):
    policy=dispatcher.ResourcePolicy() if policy is None else policy
    require(len(points)==3 and all(p.shape==(spec.width,128) for p in points),
        'Exactly three point blocks required')
    admission=dispatcher.assess_stage(spec,384,kind='point',block_tokens=128,max_blocks=3,
        policy=policy,resident_bytes=9*2**30,route='token')
    require(admission['admitted'] and admission['selected_route']=='token','Token route not admitted')
    answer=dispatcher.solve_blocks(spec,weights,((p,p) for p in points),total_tokens=384,
        kind='point',block_tokens=128,max_blocks=3,policy=policy,resident_bytes=9*2**30,route='token')
    require(answer.route=='token' and answer.admission==admission,'Actual forced route differs')
    code=StageCodes.from_array(spec.stage_id,answer.codes,grid_axis='dyadic_row',
        bits=spec.bits,scale_values=spec.scale_values)
    return answer,code
