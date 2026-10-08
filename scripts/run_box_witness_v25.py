"""Two prospectively specified gradient-corner probes of a real compressed box."""
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
    result=dict(schema='gradient-corner-witness-v25',status='running',plan_sha256=digest(raw),
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
        from src.box_corner_witness import gradient_corners
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
        descriptor=encode_factor(values,target_sha256=state.target_sha256,anchor_target_sha256=state.anchor_target_sha256,
            record_id=leaf.record_id,token_sha256=token_digest(leaf.tokens),stage_id=stage.stage_id,
            bits=24,block_size=plan['block_size'])
        encoded=serialize_descriptor(descriptor)
        require(digest(encoded)==plan['descriptor_sha256'],'witness descriptor differs from failed screen')
        box=descriptor.box();require(box.contains(values),'source is outside compressed box')
        row_id,coordinate=plan['row_id'],plan['coordinate']
        selected_weights=np.ascontiguousarray(weights[row_id:row_id+1])
        selected_reference=np.ascontiguousarray(oracle.codes[row_id:row_id+1])
        lower,upper=np.ascontiguousarray(box.lower.T),np.ascontiguousarray(box.upper.T)
        tick=time.perf_counter_ns()
        proposals=gradient_corners(selected_weights[0],selected_reference[0],lower,upper,
            coordinate,beta=options['ridge']*options['normalization'])
        result.update(row_id=row_id,coordinate=coordinate,descriptor_sha256=digest(encoded),
            proposal_elapsed_ns=time.perf_counter_ns()-tick,
            proposal_midpoint_decision=float(proposals.midpoint_decision).hex(),
            gradient_nonzero_entries=int(np.count_nonzero(proposals.gradient)))
        save('corners_proposed')
        witnesses=[]
        for direction,array in [('minus',proposals.minus),('plus',proposals.plus)]:
            require(np.all(np.isfinite(array)),'nonfinite witness proposal')
            require(np.all((array==lower)|(array==upper)),'proposal is not an endpoint corner')
            require(np.all(lower<=array) and np.all(array<=upper),'proposal outside registered box')
            tick=time.perf_counter_ns()
            point=native_quantize_dyadic_rows(selected_weights,np.ascontiguousarray(array),
                (stage.scale_values[row_id],),**options)
            mismatch=np.argwhere(point.codes!=selected_reference)
            value=dict(direction=direction,member_of_registered_box=True,full_width=weights.shape[1],
                factor_sha256=digest(np.ascontiguousarray(array.T,dtype='<f8').tobytes()),
                codes_sha256=digest(point.codes.tobytes()),changed_codes=len(mismatch),
                exact_solve_elapsed_ns=time.perf_counter_ns()-tick,first_difference=None)
            if len(mismatch):
                _,j=map(int,mismatch[0]);value['first_difference']=dict(row=row_id,coordinate=j,
                    reference_code_hex=float(selected_reference[0,j]).hex(),
                    witness_code_hex=float(point.codes[0,j]).hex())
            witnesses.append(value);result['witnesses']=witnesses
            save('corner_complete',result=value)
        result.update(status='complete',stage_exactness_verified=True,
            universal_box_impossible=any(w['changed_codes']>0 for w in witnesses),
            permits_full_compressed_pilot=False,
            outcome_interpretation='exact in-box disagreement disproves universal box constancy only; absence remains inconclusive')
        save('complete')
    except BaseException as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc));save('failed');raise


if __name__=='__main__':main()
