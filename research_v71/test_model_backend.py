"""Generated tiny parameter/target/code fixtures; no actual checkpoint or CUDA."""
import os,unittest
from unittest.mock import patch
import numpy as np
from research_v47.test_snapshot import full_fixture
from research_v61.test_target import fixture,service_for,bind
from research_v71 import model_backend as b
from src.run_store import digest,strict_json


def make():
    reference=full_fixture();base,_=fixture(shapes=tuple(a.shape for a in reference.weights.values()))
    for entry,(name,a) in zip(base['stages'],reference.weights.items()):
        entry['stage_id']=name;entry['weights_sha256']=b._weight_digest(a)
    for i,entry in enumerate(base['stages']):entry['dependencies']=[e['stage_id'] for e in base['stages'][:i]]
    target=bind(base,service_for(base));codes=[]
    for e in base['stages']:
        codes.append(b.StageCodes.from_array(e['stage_id'],np.zeros(e['shape']),grid_axis='dyadic_row',bits=4,
            scale_values=tuple(float.fromhex(v) for v in e['row_scale_hex'])))
    blob=b''.join(c.packed_indices for c in codes)
    models={m:dict(blob=blob,expected=b.info(blob),retained_records_sha256=digest(m.rsplit('_',1)[1].encode())) for m in b.MODELS[2:]}
    return reference,target,models


def construct(reference,target,models):
    return b.ModelSet(reference,target,models,expected_base=b.info(target.anchor_payload),expected_service=b.info(target.fixed_payload))


class ModelBackendTests(unittest.TestCase):
    def test_all_six_actual_tiny_cpu_models_have_distinct_bound_roles_and_expected_loss(self):
        ref,target,models=make();result=construct(ref,target,models);tokens=[1,2,3,4]
        self.assertEqual(set(result.bindings),set(b.MODELS))
        for label in b.MODELS:
            with result.cpu(label) as evaluator:
                expected=b.nll_from_logits(ref.logits(tokens,result.arrays(label)),tokens)
                self.assertEqual(evaluator.nll(tokens),expected)
                self.assertEqual(evaluator.binding,result.bindings[label])
        self.assertIsNone(result.bindings['original']['installed_prefix_words'])

    def test_actual_weight_parameter_and_label_mutations_refuse(self):
        ref,target,models=make();ref.weights[next(iter(ref.weights))][0,0]=0.
        with self.assertRaisesRegex(ValueError,'checkpoint matrix'):construct(ref,target,models)
        ref,target,models=make();result=construct(ref,target,models)
        ref.head[0,0]+=1
        with self.assertRaisesRegex(ValueError,'parameter words'):
            with result.cpu('original'):self.fail('must refuse before inference')
        with self.assertRaises(ValueError):result.arrays('foreign')
        ref,target,models=make();result=construct(ref,target,models)
        result.bindings['candidate_6']['retained_records_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'provenance bindings'):
            with result.cpu('candidate_6'):self.fail('must refuse')

    def test_nearest_preserves_lower_midpoint_ties_in_positive_and_negative_cells(self):
        ref,target,models=make();name=next(iter(ref.weights))
        ref.weights[name][0]=[.5,-.5,1.5,-1.5]
        base=strict_json(target.anchor_payload);base['stages'][0]['weights_sha256']=b._weight_digest(ref.weights[name])
        target=bind(base,service_for(base));result=construct(ref,target,models)
        np.testing.assert_array_equal(result.arrays('nearest')[name][0],[0.,-1.,1.,-2.])

    def test_incomplete_corrupt_or_wrong_membership_codes_refuse(self):
        for variant in ['missing','trailing','hash','membership','first_stage']:
            ref,target,models=make()
            if variant=='missing':del models['candidate_6']
            elif variant=='membership':models['candidate_6']['retained_records_sha256']='a'*64
            else:
                entry=models['candidate_6']
                entry['blob']=entry['blob']+b'x' if variant=='trailing' else bytes([entry['blob'][0]^1])+entry['blob'][1:]
                if variant!='hash':entry['expected']=b.info(entry['blob'])
            with self.assertRaises(ValueError):construct(ref,target,models)

    def test_changed_target_or_partial_decoder_extent_refuse(self):
        ref,target,models=make()
        with self.assertRaises(ValueError):b.ModelSet(ref,target,models,expected_base=dict(bytes=1,sha256='a'*64),expected_service=b.info(target.fixed_payload))
        del ref.weights[next(iter(ref.weights))]
        with self.assertRaises(ValueError):construct(ref,target,models)

    def test_cuda_requires_explicit_fresh_admission_before_import_or_likelihood(self):
        result=construct(*make())
        with patch.dict(os.environ,{'CUBLAS_WORKSPACE_CONFIG':''}):
            with self.assertRaisesRegex(ValueError,'cuBLAS'):
                with b.cuda(result,allocator_bytes=2**30):self.fail('must refuse')
        with self.assertRaises(ValueError):
            with b.cuda(result,allocator_bytes=True):self.fail('must refuse')


if __name__=='__main__':unittest.main()
