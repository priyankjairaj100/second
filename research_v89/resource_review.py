"""Conservative complete-process reservation plus unchanged solver admission."""
from dataclasses import asdict
from research_v43.dispatcher import StageSpec,ResourcePolicy,assess_stage
from research_v61.resource_review import review as previous_review
from research_v89.config import RESIDENT,MEMORY,ARTIFACT_LIMIT
from research_v80.io import require
from src.run_store import strict_json,digest

def review(base):
    inherited=previous_review(base);manifest=strict_json(base);rows=[]
    for n in [1664,1536,768]:
        for representation in ['lossless','compressed48','hybrid_gram','modern_lossless']:
            reports=[];units=0
            for e in manifest['stages']:
                spec=StageSpec.from_manifest(e,target_sha256=digest(base))
                kind='box' if representation=='compressed48' else 'gram' if representation=='hybrid_gram' and spec.width<=768 else 'point'
                report=assess_stage(spec,n,kind=kind,block_tokens=128,max_blocks=n//128,resident_bytes=RESIDENT)
                require(report['admitted'],'Complete resident-plus-solver admission failed');units+=report['work_units']
                if kind=='box':
                    fallback=assess_stage(spec,n,kind='point',block_tokens=128,max_blocks=n//128,resident_bytes=RESIDENT)
                    require(fallback['admitted'],'Complete fallback admission failed');units+=fallback['work_units'];report['reserved_fallback']=fallback
                reports.append(report)
            require(units<=ResourcePolicy().max_request_work_units,'Complete work cap')
            rows.append(dict(tokens=n,representation=representation,stages=reports,reserved_work_units=units))
    return dict(schema='v80-complete-resource-admission',requests=rows,inherited_shape_admission=inherited,
        resident_reservation_bytes=RESIDENT,process_cap_bytes=MEMORY,artifact_cap_bytes=ARTIFACT_LIMIT,
        maximum_original_feature_bytes=429391872,checkpoint_teacher_reservation_bytes=2*2**30,
        incoming_outgoing_and_parsed_state_reservation_bytes=4*2**30,
        remaining_reservation_scope='Feature arrays, full model code buffers, codec candidates, Gram temporaries and interpreter/metadata margin share remaining2GiB plus1GiB reserved canonical cache; OS cap remains authoritative.',
        measured_fit=False,formal_python_heap_bound=False,
        failure_rule='Any source value, Gram width, codec/state size, process or certificate refusal ends the fixed attempt; no cap increase or root replacement.')
