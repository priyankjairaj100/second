"""Structural admission for the frozen V59 geometry, not numerical execution.

The new service separately admits its actual target before feature work.
This reports complete solver reservations, including compressed-point fallback;
OS limits remain authoritative for process fit and time.
"""
from dataclasses import asdict

from research_v43.dispatcher import StageSpec, ResourcePolicy, assess_stage
from research_v61.service import gram_budget
from src.run_store import canonical_json, digest, strict_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def review(base_payload):
    require(type(base_payload) is bytes, 'Immutable base target bytes required')
    manifest = strict_json(base_payload)
    require(canonical_json(manifest) == base_payload, 'Canonical base target required')
    require(manifest['schema'] == 'fixed-v-cert-dyadic-row-grid-diagnostic-target-v1'
            and manifest['recipe']['original_token_count'] == 1664
            and manifest['recipe']['bits'] == 4 and manifest['recipe']['ridge'] == [1, 100],
            'V59 base recipe differs')
    stages = manifest['stages']
    require(len(stages) == 24 and [s['shape'] for s in stages] ==
            [[2304,768], [768,768], [3072,768], [768,3072]] * 6,
            'Complete DistilGPT2 geometry required')
    reports = []
    for tokens in (1664, 1536, 768):
        for representation in ('lossless', 'compressed48', 'hybrid_gram'):
            items, work = [], 0
            for entry in stages:
                spec = StageSpec.from_manifest(entry, target_sha256=digest(base_payload))
                require(spec.normalization == 1664, 'Original normalization differs')
                kind = ('gram' if representation == 'hybrid_gram' and spec.width <= 768
                        else 'box' if representation == 'compressed48' else 'point')
                row = assess_stage(spec, tokens, kind=kind, block_tokens=128,
                    max_blocks=tokens//128, resident_bytes=4*2**30)
                require(row['admitted'], 'Stage structural admission refused: '+spec.stage_id)
                work += row['work_units']
                if kind == 'box':
                    fallback = assess_stage(spec, tokens, kind='point', block_tokens=128,
                        max_blocks=tokens//128, resident_bytes=4*2**30)
                    require(fallback['admitted'], 'Exact point fallback refused')
                    work += fallback['work_units']
                    row['reserved_fallback'] = fallback
                items.append(row)
            require(work <= ResourcePolicy().max_request_work_units,
                    'Complete request work refused')
            reports.append(dict(tokens=tokens, representation=representation,
                work_units_including_fallback=work, stages=items))
    exact_features = 1664 * sum(e['shape'][1] for e in stages) * 8
    return dict(schema='full-precision-teacher-shape-admission-v61', status='admitted',
        reference_manifest_sha256=digest(base_payload), requests=reports,
        gram_budget=asdict(gram_budget(1664)), resource_policy=asdict(ResourcePolicy()),
        maximum_complete_exact_feature_bytes=exact_features,
        resident_reservation_bytes=4*2**30, stage_count=24,
        process_address_space_bytes=16*2**30, original_sources=13, tokens_per_source=128,
        target_binding_scope='Frozen V59 base geometry only; actual V61 service target admission precedes all worker feature work',
        feature_rule='original checkpoint teacher; calibrated outputs never installed',
        remaining_process_memory_margin_is_not_a_proof=True,
        arrays_exclude_python_blas_compiler_overhead=True, model_inference=False,
        memory_review='Original features 429391872 bytes. Checkpoint, model, teacher, descriptors, state copies and metadata share the conservative 4 GiB residency reservation. Solver arrays are separate. Source values and Gram integer widths can still cause refusal; structural admission is not measured fit or completion. All six workers retain a 16 GiB OS cap.')
