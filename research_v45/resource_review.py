"""Shape-only admission; no features, checkpoint load, inference, or timing."""
from dataclasses import asdict
from research_v43.campaign import ROOT, read, sha, require
from research_v43.dispatcher import StageSpec,ResourcePolicy,assess_stage
from research_v45.service import gram_budget


def review():
    path=ROOT/'campaigns/ci_scale_v39/attempts/prepare/outputs/base-target.json'
    manifest=read(path)
    stages=manifest['stages']
    require(len(stages)==24,'Historical geometry incomplete')
    reports=[]
    for tokens in (1664,1536,768):
        for representation in ('lossless','compressed40','hybrid_gram'):
            items=[];work=0
            for entry in stages:
                spec=StageSpec.from_manifest(entry,target_sha256=sha(path))
                require(spec.normalization==1664,'Reference normalization differs')
                kind='gram' if representation=='hybrid_gram' and spec.width<=768 else ('box' if representation=='compressed40' else 'point')
                row=assess_stage(spec,tokens,kind=kind,block_tokens=128,max_blocks=tokens//128,resident_bytes=4*2**30)
                require(row['admitted'],'Stage structural admission refused')
                work+=row['work_units']
                if kind=='box':
                    fallback=assess_stage(spec,tokens,kind='point',block_tokens=128,max_blocks=tokens//128,resident_bytes=4*2**30)
                    require(fallback['admitted'],'Point fallback refused');work+=fallback['work_units'];row['reserved_fallback']=fallback
                items.append(row)
            require(work<=ResourcePolicy().max_request_work_units,'Request work refused')
            reports.append(dict(tokens=tokens,representation=representation,work_units_including_fallback=work,stages=items))
    # Complete cached feature residency plus bounded source-local decode/transposes.
    exact_features=1664*sum(e['shape'][1] for e in stages)*8
    return dict(schema='c4-full-model-shape-admission-v45',status='admitted',reference_manifest_sha256=sha(path),
        requests=reports,gram_budget=asdict(gram_budget(1664)),resource_policy=asdict(ResourcePolicy()),
        maximum_complete_exact_feature_bytes=exact_features,resident_reservation_bytes=4*2**30,
        stage_count=24,process_address_space_bytes=16*2**30,original_sources=13,tokens_per_source=128,
        remaining_process_memory_margin_is_not_a_proof=True,
        arrays_exclude_python_blas_compiler_overhead=True,model_inference=False,
        memory_review='Original features429391872 bytes; complete model and checkpoint, target metadata, descriptors/states and copies share4GiB residency allowance. Solver/dispatcher arrays admitted separately;16GiB OS cap remains decisive. Native Grams restricted to widths<=768, source count13; wide stages retain factors. No CPU timing extrapolation is treated as evidence.')
