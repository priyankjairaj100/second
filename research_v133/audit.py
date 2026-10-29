"""Validate saved numerical output; never construct or recalibrate a model."""
import json, hashlib, math

def enc(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def ident(b):
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

def validate(blob, anchor, codes, report, stages, retained, fixed, policy):
    specs=anchor['stages']; n=len(specs)
    assert n and len(codes['stages'])==len(stages)==n
    assert len({s['stage_id'] for s in specs})==n
    assert report['complete_model']==ident(blob)
    assert report['sequential_target_sha256']==ident(enc(anchor))['sha256']
    assert report['retained_records_sha256']==ident(enc({'records':retained}))['sha256']
    assert report['first_stage_equal'] is True and report['stages']==n
    assert report['quality_evaluation'] is False and report['full_successor_state_audit_repeated'] is False
    d=report['diagnostics']; assert d['stages']==stages and not d.get('aborted',False)
    assert d['target_sha256']==report['sequential_target_sha256']
    assert d['records']==len(retained) and d['retained_tokens']==sum(len(r['tokens']) for r in retained)
    assert d['neural_stage_record_pairs']==n*len(retained)
    assert d['prior_model_access'] is False and d['prior_factor_access'] is False
    assert d['feature_rule']=='each stage uses all preceding certified calibrated outputs'
    assert d['implementation']=='ordered-finite-decoder-v30'
    assert len(d['point_admission'])==n
    offset=0; previous=None; previous_id=None; count=0; hashes={}
    for i,(s,c,m,a) in enumerate(zip(specs,codes['stages'],stages,d['point_admission'])):
        rows,cols=s['shape']; size=rows*cols
        assert size%2==0 and rows>0 and cols>0
        chunk=blob[offset:offset+size//2]; assert len(chunk)==size//2
        expected=dict(stage_id=s['stage_id'],rows=rows,columns=cols,grid_axis='dyadic_row',bits=4,nbytes=size//2,sha256=ident(chunk)['sha256'],scale_values_hex=s['row_scale_hex'])
        assert c==expected, 'Packed stage metadata differs'
        assert len(s['row_scale_hex'])==rows and all(math.isfinite(float.fromhex(v)) and float.fromhex(v)>0 for v in s['row_scale_hex'])
        assert s['normalization']==[512,1] and s['ridge']==[1,100]
        assert set(s['dependencies'])=={v['stage_id'] for v in specs[:i]}
        assert m['stage_id']==s['stage_id'] and m['route']=='token'
        assert m['input_width']==cols and m['output_rows']==rows and m['feature_tokens']==d['retained_tokens']
        assert m['installed_parent_stage_id']==previous_id and m['installed_parent_packed_sha256']==previous
        assert a['admitted'] is True and a['kind']=='point' and a['selected_route']=='token' and a['selection_policy']==policy
        assert a['work_units']<=64000000000
        sd=m['solver_diagnostics']; assert sd['backend']=='token'
        num=sd['solver_diagnostics']; assert num['interval_decisions']+num['exact_decisions']==size
        assert num['exact_decisions']==0 and not num['exact_coordinates']
        assert num['runtime_premise']=='IEEE binary64 RN elementary operations; gradual underflow'
        assert sd['admission']['max_refinement_coordinates']==16 and sd['admission']['max_workspace_bytes']==8589934592 and sd['admission']['max_work_units']==64000000000
        if i==0: assert chunk==fixed[:size//2], 'First-stage invariant differs'
        offset+=size//2;count+=size; previous=c['sha256']; previous_id=s['stage_id'];hashes[s['stage_id']]=previous
    assert offset==len(blob) and count==report['code_count']
    assert sum(a['work_units'] for a in d['point_admission'])<=1000000000000
    return dict(stages=n,code_count=count,model=ident(blob),first_stage_equal=True,stage_sha256=hashes)
