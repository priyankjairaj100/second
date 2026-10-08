"""Admitted real-factor screen; no neural replay and no full-model speed claim."""
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
    result=dict(schema='compressed-factor-stage-screen-v25',status='running',plan_sha256=digest(raw),
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
        from src.fixed_factor_codec import encode_factor,serialize as serialize_descriptor,parse as parse_descriptor
        from src.compact_state import token_digest
        from src.native_ball_quantizer import native_quantize_dyadic_rows
        from src.dyadic_box_certificate import certify_dyadic_box
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
        stage=state.stages[0];leaf=state.anchors[0];block=leaf.blocks[0];entry=base['stages'][0]
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
        tick=time.perf_counter_ns();oracle=native_quantize_dyadic_rows(weights,features,stage.scale_values,**options)
        require(np.array_equal(oracle.codes,stage.array()),'exact reference differs from archived stage')
        result['oracle_elapsed_ns']=time.perf_counter_ns()-tick
        save('exact_oracle_verified')
        previous=None
        for bits in plan['precisions']:
            row=dict(bits=bits,block_size=plan['block_size']);tick=time.perf_counter_ns()
            descriptor=encode_factor(values,target_sha256=state.target_sha256,anchor_target_sha256=state.anchor_target_sha256,
                record_id=leaf.record_id,token_sha256=token_digest(leaf.tokens),stage_id=stage.stage_id,
                bits=bits,block_size=plan['block_size'])
            encoded=serialize_descriptor(descriptor);decoded=parse_descriptor(encoded)
            require(serialize_descriptor(decoded)==encoded,'descriptor roundtrip differs')
            box=descriptor.box();require(np.all(box.lower<=values) and np.all(values<=box.upper),'codec containment failure')
            if previous is not None:require(np.all(previous.lower<=box.lower) and np.all(box.upper<=previous.upper),'precision not nested')
            previous=box
            row.update(descriptor_bytes=len(encoded),descriptor_sha256=digest(encoded),
                encode_decode_elapsed_ns=time.perf_counter_ns()-tick,uncertain_values=int(np.count_nonzero(box.lower!=box.upper)))
            endpoints=[]
            for label,array in [('lower',box.lower),('upper',box.upper)]:
                tick=time.perf_counter_ns();point=native_quantize_dyadic_rows(weights,np.ascontiguousarray(array.T),stage.scale_values,**options)
                row[label+'_solve_elapsed_ns']=time.perf_counter_ns()-tick
                row[label+'_codes_sha256']=digest(point.codes.tobytes())
                row[label+'_changes_from_true']=int(np.count_nonzero(point.codes!=oracle.codes))
                endpoints.append(point.codes)
            changed=np.argwhere(endpoints[0]!=endpoints[1])
            row['endpoint_disagreement_count']=len(changed)
            row['universal_box_impossible']=bool(len(changed))
            row['witness']=None
            if len(changed):
                i,j=map(int,changed[0]);row['witness']=dict(row=i,coordinate=j,
                    lower_code_hex=float(endpoints[0][i,j]).hex(),upper_code_hex=float(endpoints[1][i,j]).hex())
            result['rows'].append(row);save('endpoints_complete',result=row)
            tick=time.perf_counter_ns()
            try:
                certificate=certify_dyadic_box(weights,np.ascontiguousarray(box.lower.T),np.ascontiguousarray(box.upper.T),
                    stage.scale_values,**options)
                require(not len(changed),'certificate contradicted endpoint witness')
                require(np.array_equal(certificate.codes,oracle.codes),'certificate differs from true oracle')
                row.update(certificate_status='accepted',certificate_reason=None)
            except TokenBoxUnresolved as exc:
                row.update(certificate_status='unresolved',certificate_reason=str(exc))
            row['certificate_elapsed_ns']=time.perf_counter_ns()-tick
            save('precision_complete',result=row)
        result.update(status='complete',stage_exactness_verified=True,
            permits_full_compressed_pilot=any(r['certificate_status']=='accepted' for r in result['rows']),
            outcome_interpretation='endpoint disagreement rejects this universal box only; endpoint agreement does not prove constancy')
        save('complete')
    except BaseException as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise


if __name__=='__main__':main()
