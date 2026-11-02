import unittest,copy
from research_v133.audit import enc,ident,validate

def fixture():
    specs=[dict(stage_id='s'+str(i),shape=[1,2],row_scale_hex=['0x1.0000000000000p+0'],normalization=[512,1],ridge=[1,100],dependencies=['s0'] if i else []) for i in range(2)]
    anchor={'stages':specs};blob=b'\x88\x79';codes={'stages':[]};marks=[];admissions=[];rows=[dict(id='a',tokens=[1]*128),dict(id='b',tokens=[2]*128)]
    for i,s in enumerate(specs):
        codes['stages'].append(dict(stage_id=s['stage_id'],rows=1,columns=2,grid_axis='dyadic_row',bits=4,nbytes=1,sha256=ident(blob[i:i+1])['sha256'],scale_values_hex=s['row_scale_hex']))
        admissions.append(dict(admitted=True,kind='point',selected_route='token',selection_policy='test-policy',work_units=1))
        marks.append(dict(stage_id=s['stage_id'],route='token',input_width=2,output_rows=1,feature_tokens=256,installed_parent_stage_id='s0' if i else None,installed_parent_packed_sha256=ident(blob[:1])['sha256'] if i else None,solver_diagnostics=dict(backend='token',admission=dict(max_refinement_coordinates=16,max_workspace_bytes=8589934592,max_work_units=64000000000),solver_diagnostics=dict(interval_decisions=2,exact_decisions=0,exact_coordinates=[],runtime_premise='IEEE binary64 RN elementary operations; gradual underflow'))))
    d=dict(stages=marks,target_sha256=ident(enc(anchor))['sha256'],records=2,retained_tokens=256,neural_stage_record_pairs=4,prior_model_access=False,prior_factor_access=False,feature_rule='each stage uses all preceding certified calibrated outputs',implementation='ordered-finite-decoder-v30',point_admission=admissions)
    report=dict(complete_model=ident(blob),sequential_target_sha256=ident(enc(anchor))['sha256'],retained_records_sha256=ident(enc({'records':rows}))['sha256'],first_stage_equal=True,stages=2,code_count=4,quality_evaluation=False,full_successor_state_audit_repeated=False,diagnostics=d)
    return [blob,anchor,codes,report,marks,rows,blob,'test-policy']

class Audit(unittest.TestCase):
    def test_valid_complete_chain(self):self.assertEqual(validate(*fixture())['code_count'],4)
    def test_corrupt_model_rejected(self):
        x=fixture();x[0]=b'\x88\x78'
        with self.assertRaises(AssertionError):validate(*x)
    def test_missing_stage_rejected(self):
        x=fixture();x[4].pop()
        with self.assertRaises(AssertionError):validate(*x)
    def test_changed_parent_rejected(self):
        x=fixture();x[4][1]['installed_parent_packed_sha256']='0'*64
        with self.assertRaises(AssertionError):validate(*x)
    def test_incomplete_certification_rejected(self):
        x=fixture();x[4][1]['solver_diagnostics']['solver_diagnostics']['interval_decisions']=1
        with self.assertRaises(AssertionError):validate(*x)
    def test_changed_grid_rejected(self):
        x=fixture();x[2]['stages'][1]['scale_values_hex']=['0x1.0000000000000p+1']
        with self.assertRaises(AssertionError):validate(*x)
    def test_membership_or_first_stage_change_rejected(self):
        for j in (5,6):
            x=fixture();x[j]=x[j][:1] if j==5 else b'\x77\x79'
            with self.assertRaises(AssertionError):validate(*x)
    def test_original_serialization_error_reproduced(self):
        with self.assertRaises(TypeError):enc(dict(native_calibration_runtime=enc({'runtime':'fixture'})))
        self.assertEqual(__import__('json').loads(enc(dict(native_calibration_runtime={'runtime':'fixture'})))['native_calibration_runtime'],{'runtime':'fixture'})
if __name__=='__main__':unittest.main()
