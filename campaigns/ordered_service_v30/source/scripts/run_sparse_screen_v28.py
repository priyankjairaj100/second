"""Registered full-width sparse-row fallback diagnostic on the slowest saved stage."""
import hashlib
import json
from pathlib import Path
import sys
import time
from fractions import Fraction as Q
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.run_store import canonical_json,digest,atomic_write
from src.experiment_inventory import source_hashes
from src.transaction_timing import verify_command_admission


def require(condition,message):
    if not condition:raise ValueError(message)


def main():
    raw=Path(sys.argv[1]).read_bytes();plan=json.loads(raw)
    require(source_hashes(ROOT)==plan['source_sha256'],'frozen source changed')
    verify_command_admission(plan['protocol_sha256'],'feasibility',
        [sys.executable,str(Path(__file__).resolve()),str(Path(sys.argv[1]).absolute())])
    out=Path(plan['output']);require(not out.exists(),'cannot overwrite screen')
    out.mkdir(parents=True);start=time.perf_counter_ns()
    result=dict(schema='sparse-row-factor-screen-v28',status='running',plan_sha256=digest(raw),
        phases=[],rows=[],full_model=False,quality_evaluation=False,neural_evaluation=False,
        scope='first calibrated stage, one real retained factor, full weight rows; no complete repair timing')
    def save(phase,**details):
        result['phases'].append(dict(phase=phase,elapsed_ns=time.perf_counter_ns()-start,**details))
        atomic_write(out/'progress.json',canonical_json(result));print(json.dumps(result['phases'][-1]),flush=True)
    def read(name):
        entry=plan['inputs'][name];p=Path(entry['path']);value=p.read_bytes()
        require(digest(value)==entry['sha256'],'input changed: '+name);return value
    try:
        save('inputs_started')
        for key,entry in plan['inputs'].items():
            with Path(entry['path']).open('rb') as stream:
                require(hashlib.file_digest(stream,'sha256').hexdigest()==entry['sha256'],'input hash differs: '+key)
        import numpy as np
        from src.checkpoint_adapter import _SafeFile
        from src.fixed_factor_state import parse as parse_state
        from src.fixed_factor_codec_v26 import encode_factor,serialize as serialize_descriptor,parse as parse_descriptor
        from src.compact_state import token_digest
        from src.native_ball_quantizer import native_quantize_dyadic_rows
        from src.ball_box_certificate_v28 import certify_ball_dyadic_box
        from src.token_box_certificate import TokenBoxUnresolved
        state=parse_state(read('state'),expected_sha256=plan['inputs']['state']['sha256'])
        progress=json.loads(read('generation_progress'));generation_plan=read('generation_plan')
        receipt=json.loads(read('generation_receipt'));base_raw=read('base_target');base=json.loads(base_raw)
        require(digest(base_raw)==state.anchor_target_sha256,'base target artifact differs')
        require(progress['status']==receipt['outcome']['status']=='complete','incomplete source generation')
        require(receipt['budget_debit']['state']=='settled','unsettled source generation')
        require(progress['plan_sha256']==receipt['worker_identity']['plan_sha256']==digest(generation_plan),'generation binding differs')
        require(progress['state_artifact']['sha256']==plan['inputs']['state']['sha256'],'state differs from generation')
        require(state.target_sha256==progress['fixed_target_sha256'] and state.anchor_target_sha256==progress['base_target_sha256'],'target differs')
        require(state.record_ids==(plan['retained_record_id'],),'unexpected retained membership')
        index=plan['stage_index'];stage=state.stages[index];leaf=state.anchors[0];block=leaf.blocks[index];entry=base['stages'][index]
        require(stage.stage_id==block.stage_id==entry['stage_id']==plan['stage_id'],'stage identity differs')
        with Path(plan['inputs']['weights']['path']).open('rb') as handle:
            weight_file=_SafeFile(handle,max_header_bytes=16*2**20)
            require(weight_file.sha256==plan['inputs']['weights']['sha256'],'checkpoint reader identity differs')
            shape=weight_file.tensors[plan['weight_key']].shape
            weights=np.ascontiguousarray(weight_file.compact_values(plan['weight_key']).float_array().reshape(shape).T,dtype=np.float64)
        h=hashlib.sha256(b'binary64-matrix-little-endian-row-major-v1\0')
        h.update(json.dumps(list(weights.shape),separators=(',',':')).encode('ascii'));h.update(b'\0')
        h.update(weights.astype('<f8',copy=False).tobytes(order='C'))
        require(h.hexdigest()==entry['weights_sha256'],'stage weight identity differs')
        require(tuple(weights.shape)==stage.shape==tuple(entry['shape']),'weight shape differs')
        require(tuple(float.fromhex(v) for v in entry['row_scale_hex'])==stage.scale_values,'grid differs')
        values=block.array();features=np.ascontiguousarray(values.T)
        options=dict(bits=stage.bits,ridge=Q(*entry['ridge']),normalization=Q(*entry['normalization']),
                     max_exact_rank=64,max_exact_coordinates=16,max_refinement_coordinates=64)
        require(options['normalization']==32 and options['ridge']==Q(1,100),'recipe differs')
        result.update(target_sha256=state.target_sha256,anchor_target_sha256=state.anchor_target_sha256,
            stage_id=stage.stage_id,weights_shape=list(weights.shape),factor_shape=list(values.shape),
            record_id=leaf.record_id,normalization=32,ridge=[1,100],raw_factor_bytes=len(block.binary64))
        save('inputs_verified')
        reference=stage.array()
        descriptor=encode_factor(values,target_sha256=state.target_sha256,anchor_target_sha256=state.anchor_target_sha256,
            record_id=leaf.record_id,token_sha256=token_digest(leaf.tokens),stage_id=stage.stage_id,bits=40,block_size=256)
        encoded=serialize_descriptor(descriptor);box=descriptor.box()
        require(box.contains(values),'descriptor containment differs')
        require(serialize_descriptor(parse_descriptor(encoded))==encoded,'descriptor roundtrip differs')
        result.update(descriptor_bytes=len(encoded),descriptor_sha256=digest(encoded),
            oracle_source='bound saved exact retained generation; no new point solve',
            model_code_elements=reference.size)
        save('certificate_started')
        tick=time.perf_counter_ns()
        try:
            certificate=certify_ball_dyadic_box(weights,np.ascontiguousarray(box.lower.T),
                np.ascontiguousarray(box.upper.T),stage.scale_values,**options)
            elapsed=time.perf_counter_ns()-tick
            require(np.array_equal(certificate.codes,reference),'certificate differs from archived exact model')
            result.update(certificate_status='accepted',certificate_elapsed_ns=elapsed,
                certificate_diagnostics={k:v for k,v in certificate.__dict__.items() if k!='codes'},
                codes_sha256=digest(certificate.codes.tobytes()),
                permits_full_compressed_pilot=elapsed<=4_000_000_000)
        except TokenBoxUnresolved as exc:
            result.update(certificate_status='unresolved',certificate_reason=str(exc),
                certificate_elapsed_ns=time.perf_counter_ns()-tick,
                certificate_diagnostics=getattr(exc,'native_diagnostics',None),
                permits_full_compressed_pilot=False)
        result.update(status='complete',stage_exactness_verified=result['certificate_status']=='accepted',
            outcome_interpretation='full-width archived exact reference; component cost gate only; no complete repair speed claim')
        save('complete')
    except BaseException as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise


if __name__=='__main__':main()
