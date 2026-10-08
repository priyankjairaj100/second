"""Full finite-anchor software fixtures. These are not empirical datasets."""
from dataclasses import replace
from fractions import Fraction as Q
import json
import unittest
from unittest.mock import patch
import numpy as np
from src.anchor_transformer import (prepare_context,prepare_anchor,bound_stage,
    encode_anchor,decode_anchor,AnchorBoundUnresolved,_up_q,_node_error,SummaryNode,_affine_bound)
from src.certified_transformer import CertifiedDecoder
from src.compact_state import StageCodes
from src.dyadic_row_target import build_dyadic_row_target
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


def fixture(blocks=2,heads=1,activation=None):
    base=decoder_fixture(block_count=blocks,head_count=heads)
    if activation is not None:
        # Fixture constructors freeze configuration; use a fresh constructor.
        from src.transformer_backend import DeterministicDecoder
        base=DeterministicDecoder(replace(base.config,activation=activation),
            token_embeddings=base._token_embeddings,position_embeddings=base._position_embeddings,
            blocks=base._blocks,lm_head=base._lm_head,lm_head_bias=base._lm_head_bias,
            final_norm_scale=base._final_norm_scale,final_norm_bias=base._final_norm_bias)
    decoder=CertifiedDecoder(base,primitive_backend='mpfr_enclosure')
    target=build_dyadic_row_target(decoder,TargetRecipe(original_token_count=4,bits=4,group_count=1,ridge=Q(1,10)))
    return decoder,target


class AnchorTransformerTests(unittest.TestCase):
    def test_full_anchor_matches_scalar_target_both_heads(self):
        for heads in (1,2):
            decoder,target=fixture(heads=heads);context=prepare_context(decoder,target)
            anchor=prepare_anchor(decoder,target,{'id':'a','tokens':[0,1,2]},context=context)
            for i,stage in enumerate(target.stages):
                prefix=context.anchor_codes[:i]
                mapping={c.stage_id:tuple(tuple(Q.from_float(float(x)) for x in row) for row in c.array()) for c in prefix}
                exact=np.asarray(decoder.stage_features(stage.stage_id,anchor.tokens,mapping),dtype=np.float64).T
                box=bound_stage(decoder,target,anchor,prefix,stage.stage_id,context=context)
                self.assertTrue(box.singleton)
                np.testing.assert_array_equal(box.lower,exact)
                with self.assertRaises(ValueError):box.lower.flags.writeable=True

    def test_changed_prefix_contains_complete_scalar_execution(self):
        decoder,target=fixture();context=prepare_context(decoder,target)
        anchor=prepare_anchor(decoder,target,{'id':'a','tokens':[0,1]},context=context)
        accepted=0;rejected=0
        for changed in range(len(target.stages)-1):
            prefix=list(context.anchor_codes)
            code=prefix[changed];array=code.array().copy()
            scale=code.scale_values[0]
            grid=scale*np.arange(-(1<<(code.bits-1)),1<<(code.bits-1))
            old=np.flatnonzero(grid==array[0,0])[0]
            array[0,0]=grid[old-1 if old else 1]
            prefix[changed]=StageCodes.from_array(code.stage_id,array,grid_axis=code.grid_axis,bits=code.bits,scale_values=code.scale_values)
            for i in range(changed+1,len(target.stages)):
                metrics={}
                try:box=bound_stage(decoder,target,anchor,prefix[:i],target.stages[i].stage_id,context=context,diagnostics=metrics)
                except AnchorBoundUnresolved:rejected+=1;continue
                mapping={c.stage_id:tuple(tuple(Q.from_float(float(x)) for x in row) for row in c.array()) for c in prefix[:i]}
                exact=np.asarray(decoder.stage_features(target.stages[i].stage_id,anchor.tokens,mapping),dtype=np.float64).T
                self.assertTrue(box.contains(exact),(changed,i));accepted+=1
                self.assertEqual(metrics['retained_dot_products'],0)
                self.assertEqual(metrics['retained_token_reads'],0)
        self.assertGreater(accepted,0)
        self.assertGreater(rejected,0)  # Fail-closed behavior is exercised too.

    def test_bound_does_not_execute_decoder_or_read_tokens(self):
        decoder,target=fixture(blocks=1);context=prepare_context(decoder,target)
        anchor=prepare_anchor(decoder,target,{'id':'a','tokens':[0,1]},context=context)
        class BadTokens:
            def __iter__(self):raise AssertionError('tokens accessed')
        anchor=replace(anchor,tokens=BadTokens())
        with patch.object(type(decoder),'stage_features',side_effect=AssertionError('feature execution')):
            box=bound_stage(decoder,target,anchor,context.anchor_codes[:3],target.stages[3].stage_id,context=context)
        self.assertTrue(box.singleton)

    def test_canonical_serialization_and_deterministic_preparation(self):
        decoder,target=fixture();context=prepare_context(decoder,target)
        record={'id':'z','tokens':[2,0]}
        first=prepare_anchor(decoder,target,record,context=context)
        raw=encode_anchor(first)
        self.assertEqual(raw,encode_anchor(prepare_anchor(decoder,target,record,context=context)))
        loaded=decode_anchor(raw)
        self.assertEqual(raw,encode_anchor(loaded))
        box=bound_stage(decoder,target,loaded,context.anchor_codes[:7],target.stages[7].stage_id,context=context)
        self.assertTrue(box.singleton)
        for _,_,array in loaded.factors:
            with self.assertRaises(ValueError):array.flags.writeable=True
        for kwargs in ({'max_bytes':len(raw)-1},{'max_nodes':1},{'max_values':1},{'max_tokens':1}):
            with self.assertRaises(ValueError):decode_anchor(raw,**kwargs)
        bad=json.loads(raw);bad['nodes'][1][1]=[1]
        with self.assertRaises(ValueError):decode_anchor(json.dumps(bad).encode())

    def test_bindings_and_complete_prefix(self):
        decoder,target=fixture(blocks=1);context=prepare_context(decoder,target)
        anchor=prepare_anchor(decoder,target,{'id':'a','tokens':[0]},context=context)
        with self.assertRaises(ValueError):bound_stage(decoder,target,replace(anchor,target_sha256='0'*64),(),target.stages[0].stage_id,context=context)
        with self.assertRaises(ValueError):bound_stage(decoder,target,anchor,(),target.stages[1].stage_id,context=context)
        with self.assertRaises(ValueError):bound_stage(decoder,target,anchor,context.anchor_codes[1:2],target.stages[1].stage_id,context=context)
        with self.assertRaises(ArithmeticError):prepare_anchor(decoder,target,{'id':'a','tokens':[0]},context=context,max_nodes=2)

    def test_gelu_new_complete_schedule_matches_scalar_target(self):
        decoder,target=fixture(blocks=2,activation='gelu_new')
        context=prepare_context(decoder,target)
        anchor=prepare_anchor(decoder,target,{'id':'new','tokens':[0,1,2]},context=context)
        for i,stage in enumerate(target.stages):
            prefix=context.anchor_codes[:i]
            mapping={c.stage_id:tuple(tuple(Q.from_float(float(x)) for x in row) for row in c.array()) for c in prefix}
            exact=np.asarray(decoder.stage_features(stage.stage_id,anchor.tokens,mapping),dtype=np.float64).T
            box=bound_stage(decoder,target,anchor,prefix,stage.stage_id,context=context)
            np.testing.assert_array_equal(box.lower,exact)
            self.assertTrue(box.singleton)

    def test_matrix_changes_are_shared_between_records(self):
        decoder,target=fixture(blocks=1);context=prepare_context(decoder,target)
        a=prepare_anchor(decoder,target,{'id':'a','tokens':[0,1]},context=context)
        b=prepare_anchor(decoder,target,{'id':'b','tokens':[1,0]},context=context)
        first={};second={}
        bound_stage(decoder,target,a,context.anchor_codes[:1],target.stages[1].stage_id,context=context,diagnostics=first)
        bound_stage(decoder,target,b,context.anchor_codes[:1],target.stages[1].stage_id,context=context,diagnostics=second)
        self.assertGreater(first['matrix_scan_values'],0)
        self.assertEqual(second['matrix_scan_values'],0)

    def test_affine_bias_binding_rejects_mixed_summary(self):
        from src.anchor_affine import prepare_affine_change
        decoder,target=fixture(blocks=1);context=prepare_context(decoder,target)
        anchor=prepare_anchor(decoder,target,{'id':'a','tokens':[0,1]},context=context)
        stage,summary=anchor.affines[0]
        weights=context.anchor_matrices[stage]
        change=prepare_affine_change(weights,weights)
        bias=context.biases[stage].copy()
        bias[0]=np.nextafter(bias[0],np.inf)
        with self.assertRaisesRegex(ValueError,'bias binding'):
            _affine_bound(summary,change,bias,Q(0))

    def test_bounds_round_up_and_reject_overflow(self):
        for x in (Q(1,2**1200),Q(1,3),Q(10)**300):
            self.assertGreaterEqual(_up_q(x),x)
            self.assertLessEqual(_up_q(x).denominator.bit_length(),1075)
        with self.assertRaises(AnchorBoundUnresolved):_up_q(Q(10)**400)
        a=SummaryNode('constant',(),1.,1.,1.)
        d=SummaryNode('div',(0,0),1.,1.,1.)
        with self.assertRaises(AnchorBoundUnresolved):_node_error(d,[a],[Q(1)])

if __name__=='__main__':unittest.main()
