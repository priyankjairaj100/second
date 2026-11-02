"""Packed-byte/parameter/boundary fixtures; numerical constructor is mocked.

Actual MPFR sequential fixtures still require the separately admitted Linux gate.
"""
import copy
from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from research_v69 import model_gate as g
from src.compact_state import StageCodes
from src.dyadic_row_target import DyadicRowStage,DyadicRowTarget
from src.run_store import canonical_json,digest


def fixture():
    stages=(DyadicRowStage('first',(),((1.,0.,-1.),(0.,1.,0.)),Fraction(1,100),4,(.25,.125),4),
        DyadicRowStage('second',('first',),((1.,0.,-1.),),Fraction(1,100),4,(.5,),4))
    base=DyadicRowTarget(None,stages,canonical_json(dict(fixture_only=True)))
    codes=tuple(StageCodes.from_array(s.stage_id,np.zeros((len(s.weights),s.width)),grid_axis='dyadic_row',bits=4,scale_values=s.scale_values) for s in stages)
    return base,codes


class ModelGateTests(unittest.TestCase):
    def test_actual_packed_bytes_and_each_grid_roundtrip_without_lossy_cast(self):
        base,codes=fixture();blob=b''.join(c.packed_indices for c in codes)
        result=g.restore(blob,base,expected_blob=g.info(blob),expected_target_sha256=base.digest)
        self.assertEqual(result,codes)
        reference=SimpleNamespace(weights={s.stage_id:np.asarray(s.weights) for s in base.stages})
        arrays,receipt=g.parameter_prefix(result,base,reference,expected_target_sha256=base.digest)
        for code in codes:self.assertEqual(arrays[code.stage_id].tobytes(),code.array().tobytes())
        self.assertTrue(receipt['stage_weight_words_checked']);self.assertFalse(receipt['gpu_transfer_checked'])
        self.assertFalse(receipt['embeddings_norm_bias_head_words_checked'])

    def test_corrupted_binding_padding_extent_and_target_are_refused(self):
        base,codes=fixture();blob=b''.join(c.packed_indices for c in codes)
        with self.assertRaises(ValueError):g.restore(blob[:-1]+bytes([blob[-1]^1]),base,expected_blob=g.info(blob),expected_target_sha256=base.digest)
        for changed in [blob[:-1],blob+b'x',blob[:-1]+bytes([blob[-1]|0x80])]:
            with self.assertRaises(ValueError):g.restore(changed,base,expected_blob=g.info(changed),expected_target_sha256=base.digest)
        with self.assertRaises(ValueError):g.restore(blob,base,expected_blob=g.info(blob),expected_target_sha256='0'*64)
        with self.assertRaises(ValueError):g.matched_codes(tuple(reversed(codes)),base,base.digest)
        with self.assertRaises(ValueError):g.matched_codes((replace(codes[0],scale_values=(.5,.125)),codes[1]),base,base.digest)

    def test_actual_checkpoint_weight_changes_or_partial_extent_refuse_prefix(self):
        base,codes=fixture();weights={s.stage_id:np.asarray(s.weights) for s in base.stages}
        variants=[dict(weights),dict(weights),dict(weights),{}]
        variants[0]['first']=weights['first'].copy();variants[0]['first'][0,1]=-0.
        variants[1]['first']=weights['first'].astype(np.float32)
        variants[2]['first']=weights['first'][:1]
        for values in variants:
            with self.assertRaises(ValueError):g.parameter_prefix(codes,base,SimpleNamespace(weights=values),expected_target_sha256=base.digest)

    def test_both_retained_sets_are_forwarded_without_candidate_feature_injection(self):
        base,codes=fixture();decoder=object()
        for records in [[dict(id='a',tokens=[0,1]),dict(id='b',tokens=[1,0])],[dict(id='b',tokens=[1,0])]]:
            diagnostics=dict(target_sha256=base.digest,records=len(records),retained_tokens=2*len(records),
                neural_stage_record_pairs=2*len(records),prior_model_access=False,prior_factor_access=False)
            with patch.object(g.sequential,'calibrate',return_value=(codes,diagnostics)) as called:
                out,receipt=g.construct_sequential(decoder,base,records,codes,expected_target_sha256=base.digest,
                    expected_records_sha256=digest(canonical_json(dict(records=records))))
                self.assertEqual(called.call_args.args,(decoder,base,records));self.assertEqual(out,codes)
                self.assertTrue(receipt['first_stage_equal']);self.assertFalse(receipt['quality_evaluation'])

    def test_wrong_membership_prevents_work_and_constructor_refusal_is_preserved(self):
        base,codes=fixture();records=[dict(id='a',tokens=[0,1])];rh=digest(canonical_json(dict(records=records)))
        with patch.object(g.sequential,'calibrate') as called:
            with self.assertRaises(ValueError):g.construct_sequential(object(),base,records,codes,expected_target_sha256=base.digest,expected_records_sha256='0'*64)
            called.assert_not_called()
        error=ArithmeticError('generated refusal');error.service_diagnostics={'completed_stages':1}
        with patch.object(g.sequential,'calibrate',side_effect=error):
            with self.assertRaises(ArithmeticError) as caught:g.construct_sequential(object(),base,records,codes,expected_target_sha256=base.digest,expected_records_sha256=rh)
        self.assertIs(caught.exception,error);self.assertEqual(error.service_diagnostics,{'completed_stages':1})

    def test_incorrect_first_stage_or_partial_traversal_is_not_accepted(self):
        base,codes=fixture();records=[dict(id='a',tokens=[0,1])];rh=digest(canonical_json(dict(records=records)))
        d=dict(target_sha256=base.digest,records=1,retained_tokens=2,neural_stage_record_pairs=2,prior_model_access=False,prior_factor_access=False)
        changed=(replace(codes[0],packed_indices=bytes([codes[0].packed_indices[0]^1])+codes[0].packed_indices[1:]),codes[1])
        for out,metrics in [(changed,d),(codes,dict(d,neural_stage_record_pairs=1)),(codes,dict(d,prior_model_access=True))]:
            with patch.object(g.sequential,'calibrate',return_value=(out,metrics)):
                with self.assertRaises(ValueError):g.construct_sequential(object(),base,records,codes,expected_target_sha256=base.digest,expected_records_sha256=rh)


if __name__=='__main__':unittest.main()
