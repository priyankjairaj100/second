"""Production checkpoint, target and complete parameter-geometry admission.

No launch entry and no implicit download. Runtime/Slurm admission must precede
cpu_context. Generic tiny-model helpers cannot bypass this production boundary.
"""
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from research_v38.bootstrap_target import CHECKPOINT_HASHES
from research_v43.dispatcher import ResourcePolicy,StageSpec,assess_stage
from research_v61.target import BoundTarget,_service_manifest
from research_v67.config import BASE_TARGET,CALIBRATION_TARGET,SERVICE_TARGET
from research_v67.io import require,read,info
from research_v71.parameter_audit import fields,verify as audit_parameters
from src.run_store import canonical_json,strict_json,digest

CONFIG=dict(vocabulary_size=50257,model_width=768,head_count=12,
    feedforward_width=3072,block_count=6,max_sequence_length=1024,
    layernorm_epsilon=1e-5,activation='gelu_new')
SHAPES={f'block.{i:04d}.{name}':shape for i in range(6) for name,shape in
    [('qkv',[2304,768]),('attn_out',[768,768]),('mlp_up',[3072,768]),('mlp_down',[768,3072])]}
RECIPE=dict(schema='fixed-target-recipe-v1',original_token_count=1664,
    bits=4,ridge=[1,100],group_count=1,max_grid_entries=1000000)


def configuration(value):
    require(type(value) is dict and canonical_json(value)==canonical_json(CONFIG),
        'Exact production decoder configuration required')


def checkpoint(entries):
    require(type(entries) is dict and set(entries)==set(CHECKPOINT_HASHES),
        'Exactly the frozen configuration and safetensors files required')
    parents=set();verified={}
    for name,e in entries.items():
        require(type(e) is dict and set(e)=={'path','bytes','sha256'},'Exact checkpoint binding required')
        p=Path(e['path']);require(p.is_absolute() and p.name==name and '..' not in p.parts,
            'Absolute canonical checkpoint component path required')
        require(e['sha256']==CHECKPOINT_HASHES[name],'Frozen checkpoint commitment differs')
        verified[name]=read(p,{k:e[k] for k in ['bytes','sha256']},maximum=512*2**20,retain=False)
        parents.add(p.parent)
    require(len(parents)==1,'Checkpoint components must share a directory')
    return dict(directory=str(next(iter(parents))),files=verified,
        actual_checkpoint_bytes_verified=True,checkpoint_loaded=False)


def targets(base,calibration):
    require(type(base) is bytes and type(calibration) is bytes and len(base)<=8*2**20
        and len(calibration)<=8*2**20,'Bounded actual target bytes required')
    require(digest(base)==BASE_TARGET and digest(calibration)==CALIBRATION_TARGET,
        'Frozen production target commitments differ')
    b,c=strict_json(base),strict_json(calibration)
    require(canonical_json(b)==base and canonical_json(c)==calibration,'Canonical target bytes required')
    bound=BoundTarget(base,canonical_json(_service_manifest(b,c)))
    require(digest(bound.fixed_payload)==SERVICE_TARGET,'Frozen production service commitment differs')
    require(b['recipe']==RECIPE and [s['stage_id'] for s in b['stages']]==list(SHAPES),
        'Complete production stage order and original normalization required')
    for s in b['stages']:
        require(s['shape']==SHAPES[s['stage_id']] and s['normalization']==[1664,1]
            and s['ridge']==[1,100],'Production stage geometry or objective differs')
    require(sum(s.rows*s.width for s in bound.stages)==42467328,'Complete production code extent differs')
    return bound


def reference_geometry(reference):
    configuration(vars(reference.config))
    require(type(reference.blocks) is list and len(reference.blocks)==6,
        'Complete six-block parameter inventory required')
    expected=dict(embeddings=(50257,768),positions=(1024,768),head=(50257,768),
        head_bias=(50257,),final_scale=(768,),final_bias=(768,))
    expected.update({'weights/'+name:tuple(shape) for name,shape in SHAPES.items()})
    for i in range(6):
        expected.update({f'blocks/{i}/{name}':(n,) for name,n in
            [('norm1_scale',768),('norm1_bias',768),('norm2_scale',768),('norm2_bias',768),
             ('qkv_bias',2304),('attn_out_bias',768),('mlp_up_bias',3072),('mlp_down_bias',768)]})
    actual=fields(reference)
    require(set(actual)==set(expected) and all(actual[k].shape==shape for k,shape in expected.items()),
        'Complete production parameter shapes differ')
    return dict(configuration=CONFIG.copy(),arrays=len(actual),
        parameter_word_bytes=sum(a.nbytes for a in actual.values()),stages=24,
        code_count=42467328,packed_model_bytes=21233664)


def resources(bound):
    require(type(bound) is BoundTarget and digest(bound.anchor_payload)==BASE_TARGET
        and digest(bound.fixed_payload)==SERVICE_TARGET,'Production target admission required')
    base=strict_json(bound.anchor_payload);policy=ResourcePolicy();requests={}
    for n in [12,6]:
        rows=[assess_stage(StageSpec.from_manifest(e,target_sha256=BASE_TARGET),128*n,
            kind='point',block_tokens=128,max_blocks=n,resident_bytes=4*2**30,policy=policy)
            for e in base['stages']]
        total=sum(r['work_units'] for r in rows)
        require(len(rows)==24 and all(r['admitted'] for r in rows)
            and total<=policy.max_request_work_units,'Complete production sequential admission failed')
        requests[str(n)]=dict(stages=rows,reserved_work_units=total)
    return dict(schema='quality-production-resource-review-v71',policy=asdict(policy),
        other_resident_bytes=4*2**30,requests=requests,measured_fit=False,
        interpreter_library_and_compiler_overhead_bounded_by_os=True)


def cpu_context(entries,base_bytes,calibration_bytes):
    """Load once from verified local bytes; rebuild and compare the actual base."""
    bound=targets(base_bytes,calibration_bytes);admission=resources(bound);checked=checkpoint(entries)
    from src.checkpoint_adapter import load_gpt2_checkpoint
    from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
    from src.dyadic_row_target import build_dyadic_row_target
    from src.target_manifest import TargetRecipe
    from scripts.run_quality_v30 import NumpyQualityDecoder
    loaded=load_gpt2_checkpoint(checked['directory'],identity_encoding='binary64_tree_v2')
    require(loaded.provenance['files_sha256']==CHECKPOINT_HASHES,'Actually loaded checkpoint differs')
    configuration(vars(loaded.decoder.config))
    decoder=OrderedFiniteDecoder(loaded.decoder,primitive_backend='mpfr_enclosure')
    base=build_dyadic_row_target(decoder,TargetRecipe(original_token_count=1664,group_count=1))
    require(canonical_json(base.payload())==base_bytes,'Reconstructed actual base target differs')
    reference=NumpyQualityDecoder(loaded.decoder);geometry=reference_geometry(reference)
    require(checkpoint(entries)==checked,'Checkpoint changed during context construction')
    return SimpleNamespace(decoder=decoder,base=base,bound=bound,reference=reference,
        provenance=dict(checkpoint=loaded.provenance,decoder=decoder.kernel_manifest,
            implementation=decoder.implementation_manifest,geometry=geometry,admission=admission,
            base_target=info(base_bytes),calibration_target=info(calibration_bytes),
            service_target=info(bound.fixed_payload)))


def parameter_receipt(context,manifest_path,archive_path,*,expected_manifest,expected_archive,
                      registration_sha256,checkpoint_entries):
    """Compare every saved array against the actual checkpoint-derived context."""
    require(type(registration_sha256) is str and len(registration_sha256)==64
        and all(c in '0123456789abcdef' for c in registration_sha256),'Registration commitment required')
    require(context.provenance['checkpoint']['files_sha256']==CHECKPOINT_HASHES,
        'Checkpoint-derived reference context required')
    geometry=reference_geometry(context.reference)
    require(geometry==context.provenance['geometry'] and
        canonical_json(context.base.payload())==context.bound.anchor_payload,
        'Actual production context changed')
    targets(context.bound.anchor_payload,canonical_json(strict_json(context.bound.fixed_payload)['calibration_target']))
    checkpoint(checkpoint_entries)
    result=audit_parameters(context.reference,manifest_path,archive_path,
        expected_manifest=expected_manifest,expected_archive=expected_archive)
    checkpoint(checkpoint_entries)
    return dict(schema='checkpoint-parameter-audit-v71',status='verified',
        registration_sha256=registration_sha256,checkpoint=checkpoint_entries,
        geometry=geometry,provenance=context.provenance,parameters=result,
        actual_checkpoint_reference_compared=True,gpu_transfer_checked=False)
