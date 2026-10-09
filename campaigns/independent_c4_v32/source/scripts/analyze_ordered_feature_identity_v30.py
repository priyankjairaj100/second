"""Compare saved scalar/ordered feature words without neural inference."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.run_store import canonical_json,digest
from src.service_terminal_evidence_v30 import verify_completed
from src.fixed_lossless_state_v29 import parse


def compare(left,right):
    started=time.process_time_ns()
    states=[]
    evidence=[]
    for attempt in (left,right):
        result=verify_completed(attempt)
        artifact=result['artifacts']['state']
        raw=(attempt/'outputs'/artifact['file']).read_bytes()
        states.append(parse(raw,expected_sha256=artifact['sha256']))
        evidence.append(dict(attempt=str(attempt),
            completion_sha256=digest((attempt/'outputs/completion.json').read_bytes()),
            state_sha256=artifact['sha256'],model_sha256=result['artifacts']['model']['sha256']))
    a,b=states
    if evidence[0]['model_sha256']!=evidence[1]['model_sha256']:
        raise ValueError('complete models differ')
    for name in ('target_sha256','anchor_target_sha256','decoder_sha256','provider_sha256',
                 'anchor_sha256','codec_sha256','record_ids','stages'):
        if getattr(a,name)!=getattr(b,name):
            raise ValueError('shared mathematical state differs: '+name)
    if a.preparer_sha256==b.preparer_sha256:
        raise ValueError('execution provenance was not distinguished')
    rows=[]
    for old,new in zip(a.anchors,b.anchors):
        if old.tokens!=new.tokens or len(old.descriptors)!=len(new.descriptors):
            raise ValueError('source membership or shape differs')
        for x,y in zip(old.descriptors,new.descriptors):
            left_bytes,right_bytes=x.binary64(),y.binary64()
            if x!=y or left_bytes!=right_bytes:
                raise ValueError('feature words or canonical descriptors differ')
            rows.append(dict(record_id=old.record_id,stage_id=x.stage_id,
                shape=list(x.shape),binary64_bytes=len(left_bytes),
                binary64_sha256=hashlib.sha256(left_bytes).hexdigest(),equal=True))
    return dict(schema='ordered-real-feature-identity-v30',status='complete',
        neural_evaluation_performed=False,archive_analysis=True,
        input_evidence=evidence,descriptor_count=len(rows),
        total_binary64_bytes=sum(row['binary64_bytes'] for row in rows),
        complete_models_equal=True,all_feature_words_equal=True,
        all_canonical_descriptors_equal=True,
        preparation_identities=[a.preparer_sha256,b.preparer_sha256],
        descriptors=rows,analysis_cpu_ns=time.process_time_ns()-started,
        limitation='one already measured corpus; supports equality here, not arbitrary-input proof or population performance')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scalar',type=Path,default=ROOT/'campaigns/full_service_v30/attempts/prepare-128')
    p.add_argument('--ordered',type=Path,default=ROOT/'campaigns/ordered_service_v30/attempts/prepare-256')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    report=compare(args.scalar,args.ordered)
    with args.output.open('xb') as f:f.write(canonical_json(report))
    print(json.dumps({key:report[key] for key in ('status','descriptor_count',
        'total_binary64_bytes','all_feature_words_equal','analysis_cpu_ns')}))
