"""Actual packed-code/grid checks before a future quality evaluator.

These helpers have no file/network/Slurm entry. Callers must first bind actual
V67 audited artifacts, checkpoint, targets, memberships and runtime. Packed-code
validation alone does not repeat the full successor-state audit.
"""
import numpy as np
from src.compact_state import StageCodes
from src.dyadic_row_target import DyadicRowTarget
from src.ordered_finite import FiniteWeights
from src.run_store import canonical_json,digest
from research_v55 import sequential
from research_v43.dispatcher import ResourcePolicy
from research_v67.io import require,info


def target_stages(base,expected_target_sha256):
    require(type(base) is DyadicRowTarget and base.digest==expected_target_sha256,'Bound sequential base target required')
    stages=base.stages;names=tuple(s.stage_id for s in stages)
    require(bool(stages) and len(set(names))==len(names),'Complete unique stage order required')
    for index,s in enumerate(stages):
        require(s.bits==4 and len(s.dependencies)==index and set(s.dependencies)==set(names[:index])
            and len(s.scale_values)==len(s.weights),'Four-bit complete sequential target/grid required')
    return stages


def restore(blob,base,*,expected_blob,expected_target_sha256):
    """Read every packed code using actual frozen base grids, without float rounding."""
    require(type(blob) is bytes and info(blob)==expected_blob,'Actual complete model binding differs')
    stages=target_stages(base,expected_target_sha256);offset=0;codes=[]
    for s in stages:
        rows,cols=len(s.weights),s.width;nbytes=(rows*cols*s.bits+7)//8
        code=StageCodes(s.stage_id,rows,cols,'dyadic_row',s.bits,(),blob[offset:offset+nbytes],s.scale_values)
        codes.append(code);offset+=nbytes
    require(offset==len(blob),'Missing or trailing complete-model bytes')
    return tuple(codes)


def matched_codes(codes,base,expected_target_sha256):
    stages=target_stages(base,expected_target_sha256)
    require(type(codes) is tuple and len(codes)==len(stages),'Complete ordered code tuple required')
    for code,s in zip(codes,stages):
        require(type(code) is StageCodes and code.stage_id==s.stage_id
            and code.shape==(len(s.weights),s.width) and code.grid_axis=='dyadic_row'
            and code.bits==s.bits and code.scale_values==s.scale_values,'Actual model shape/grid/order differs')


def construct_sequential(decoder,base,records,candidate,*,expected_target_sha256,
                         expected_records_sha256,policy=ResourcePolicy(),progress=None):
    """Reuse the frozen sequential constructor; no candidate weights enter features."""
    require(digest(canonical_json(dict(records=records)))==expected_records_sha256,'Retained membership/token commitment differs')
    require(records and [r['id'] for r in records]==sorted({r['id'] for r in records}),'Distinct canonical retained record order required')
    matched_codes(candidate,base,expected_target_sha256)
    codes,diagnostics=sequential.calibrate(decoder,base,records,policy=policy,progress=progress)
    matched_codes(codes,base,expected_target_sha256)
    require(candidate[0].packed_indices==codes[0].packed_indices,'First-stage invariant differs for matched retained tokens')
    require(diagnostics['target_sha256']==base.digest and diagnostics['records']==len(records)
        and diagnostics['retained_tokens']==sum(len(r['tokens']) for r in records)
        and diagnostics['neural_stage_record_pairs']==len(records)*len(codes)
        and diagnostics['prior_model_access'] is False and diagnostics['prior_factor_access'] is False,
        'Complete matched sequential traversal required')
    return codes,dict(diagnostics=diagnostics,retained_records_sha256=expected_records_sha256,
        sequential_target_sha256=base.digest,complete_model=info(b''.join(c.packed_indices for c in codes)),
        first_stage_equal=True,code_count=sum(c.rows*c.columns for c in codes),stages=len(codes),
        quality_evaluation=False,full_successor_state_audit_repeated=False)


def parameter_prefix(codes,base,reference,*,expected_target_sha256):
    """Validate actual checkpoint stage-weight words before expanding model codes."""
    matched_codes(codes,base,expected_target_sha256)
    require(set(reference.weights)=={s.stage_id for s in base.stages},'Complete evaluator stage-weight extent required')
    for s in base.stages:
        actual=reference.weights[s.stage_id];expected=FiniteWeights(s.weights).array()
        require(type(actual) is np.ndarray and actual.dtype==np.float64 and actual.shape==expected.shape
            and actual.astype('<f8',copy=False).tobytes()==expected.astype('<f8',copy=False).tobytes(),
            'Evaluator checkpoint stage-weight words differ')
    # StageCodes.array constructs the frozen exact row-grid words, not a lossy cast.
    arrays={c.stage_id:c.array() for c in codes}
    manifest={name:dict(shape=list(a.shape),dtype='<f8',word_sha256=digest(a.astype('<f8',copy=False).tobytes()))
        for name,a in arrays.items()}
    return arrays,dict(stage_weight_words_checked=True,replacement_arrays=manifest,
        embeddings_norm_bias_head_words_checked=False,gpu_transfer_checked=False,
        full_parameter_snapshot_audit_still_required=True)
