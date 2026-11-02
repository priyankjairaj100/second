"""Actual-manifest structural admission, still not numerical/fit evidence."""
from research_v43.dispatcher import StageSpec,ResourcePolicy,assess_stage
from research_v81.profile import validate_geometry
from src.run_store import strict_json,digest

def review(base):
    manifest=strict_json(base);profile=validate_geometry(manifest);requests=[]
    for n in (512,384,256):
        for kind in ('point','box'):
            reports=[];work=0
            for entry in manifest['stages']:
                spec=StageSpec.from_manifest(entry,target_sha256=digest(base))
                row=assess_stage(spec,n,kind=kind,block_tokens=128,max_blocks=n//128,resident_bytes=9*2**30)
                if not row['admitted']:raise ValueError('Matched stage refused')
                work+=row['work_units']
                if kind=='box':
                    fallback=assess_stage(spec,n,kind='point',block_tokens=128,max_blocks=n//128,resident_bytes=9*2**30)
                    if not fallback['admitted']:raise ValueError('Complete fallback refused')
                    work+=fallback['work_units'];row['reserved_fallback']=fallback
                reports.append(row)
            if work>ResourcePolicy().max_request_work_units:raise ValueError('Whole matched request refused')
            requests.append(dict(tokens=n,kind=kind,work_units_including_fallback=work,stages=reports))
    return dict(profile=profile,base_sha256=digest(base),requests=requests,measured_fit=False,
        resident_bytes=9*2**30,process_limit_bytes=16*2**30,shape_only=True)
