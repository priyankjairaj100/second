"""Complete service fixtures for optional exact speculative backends."""
from dataclasses import replace
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

from src.certified_transformer import CertifiedDecoder
from src.compact_service import CompactIdentityService, model_digest
from src.compact_state import CompactState, RecordFactor, prefix_digest, serialize
from src.dyadic_row_target import build_dyadic_row_target
from src.row_target_manifest import build_row_target
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


RECORDS = ({'id':'a','tokens':[0,1]}, {'id':'b','tokens':[2,1]}, {'id':'c','tokens':[0,2]})


class SpeculativeCompactServiceTests(unittest.TestCase):
    def make(self):
        decoder=CertifiedDecoder(decoder_fixture(block_count=1),primitive_backend='mpfr_enclosure')
        recipe=TargetRecipe(original_token_count=6,bits=3,group_count=1,ridge=Q(1,10))
        target=build_dyadic_row_target(decoder,recipe)
        return CompactIdentityService(decoder,target),recipe

    def test_all_methods_and_warm_model_only_match_complete_reference(self):
        reference,_=self.make()
        original=reference.run(RECORDS)
        original_bytes=serialize(original.state)
        seed=CompactState(reference.target.digest,original.stages,())
        expected=reference.run(RECORDS[1:])
        expected_bytes=serialize(expected.state)
        for backend in ('speculative','block_speculative'):
            service=CompactIdentityService(reference.decoder,reference.target,solver_backend=backend,
                max_sweeps=2,row_batch_size=2,**({'block_width':2} if backend=='block_speculative' else {}))
            fresh=service.run(RECORDS[1:])
            nearest=service.run(RECORDS[1:],method='model_only_fresh')
            repaired=service.run(RECORDS[1:],method='repair',prior=original.state,deleted_ids=['a'])
            indexed=service.run(RECORDS[1:],method='indexed_fresh',prior=original.state,deleted_ids=['a'])
            # A warm model-only call cannot inspect any factor payload.
            with patch.object(RecordFactor,'array',side_effect=AssertionError('unexpected factor access')):
                warm=service.run(RECORDS[1:],method='model_only_fresh',initial_model=seed)
            for result in (fresh,repaired,indexed):
                self.assertEqual(serialize(result.state),expected_bytes)
            for result in (fresh,nearest,repaired,indexed,warm):
                self.assertEqual(model_digest(result.stages),model_digest(expected.stages))
                metrics=result.diagnostics
                self.assertEqual(metrics['effective_solver_backends'],[backend])
                self.assertEqual(metrics['changed_ancestor_pairs_avoided'],0)
                self.assertEqual(metrics['prefix_verified_decisions']+metrics['fallback_decisions'],
                                 metrics['interval_decisions']+metrics['exact_decisions'])
                self.assertGreaterEqual(metrics['service_elapsed_ns'],sum(s['elapsed_ns'] for s in metrics['stages']))
                for key in ('features_elapsed_ns','factor_pack_elapsed_ns','weights_prepare_elapsed_ns',
                            'candidate_prepare_elapsed_ns','solver_elapsed_ns','code_pack_elapsed_ns'):
                    self.assertEqual(metrics[key],sum(s[key] for s in metrics['stages']))
                    self.assertGreaterEqual(metrics[key],0)
            self.assertIsNone(warm.state)
            self.assertEqual(warm.diagnostics['cached_factor_reads'],0)
            self.assertEqual(warm.diagnostics['model_seed_factor_reads'],0)
            self.assertEqual(warm.diagnostics['neural_stage_record_pairs'],2*len(reference.target.stages))
            self.assertEqual(warm.diagnostics['model_seed_source'],'external_model_only')
            self.assertEqual(warm.diagnostics['model_seed_sha256'],prefix_digest(reference.target.digest,seed.stages))
            self.assertEqual(warm.diagnostics['model_seed_sha256'],repaired.diagnostics['model_seed_sha256'])
            self.assertEqual(repaired.diagnostics['model_seed_source'],'prior_state')
            self.assertEqual(nearest.diagnostics['model_seed_source'],'nearest')
            for a,b in zip(warm.diagnostics['stages'],repaired.diagnostics['stages']):
                self.assertEqual(a['candidate_stage_sha256'],b['candidate_stage_sha256'])
        self.assertEqual(serialize(original.state),original_bytes)

    def test_sequential_deletion_noop_and_empty_state_remain_canonical(self):
        reference,_=self.make()
        original=reference.run(RECORDS)
        for backend in ('speculative','block_speculative'):
            service=CompactIdentityService(reference.decoder,reference.target,solver_backend=backend,
                max_sweeps=1,row_batch_size=2,**({'block_width':2} if backend=='block_speculative' else {}))
            noop=service.run(RECORDS,method='repair',prior=original.state)
            self.assertEqual(serialize(noop.state),serialize(original.state))
            self.assertEqual(noop.diagnostics['neural_stage_record_pairs'],0)
            first=service.run(RECORDS[1:],method='repair',prior=noop.state,deleted_ids=['a'])
            final=service.run(RECORDS[2:],method='repair',prior=first.state,deleted_ids=['b'])
            combined=service.run(RECORDS[2:],method='repair',prior=original.state,deleted_ids=['a','b'])
            self.assertEqual(serialize(final.state),serialize(combined.state))
            self.assertEqual(serialize(final.state),serialize(reference.run(RECORDS[2:]).state))
            empty=service.run([],method='repair',prior=final.state,deleted_ids=['c'])
            self.assertEqual(serialize(empty.state),serialize(reference.run([]).state))

    def test_seed_validation_rejects_factors_wrong_targets_and_grids(self):
        reference,_=self.make()
        original=reference.run(RECORDS)
        seed=CompactState(reference.target.digest,original.stages,())
        service=CompactIdentityService(reference.decoder,reference.target,solver_backend='speculative')
        with self.assertRaisesRegex(ValueError,'no factors'):
            service.run(RECORDS[1:],method='model_only_fresh',initial_model=original.state)
        with self.assertRaisesRegex(ValueError,'target mismatch'):
            service.run(RECORDS[1:],method='model_only_fresh',initial_model=replace(seed,target_sha256='0'*64))
        first=seed.stages[0]
        changed=replace(first,scale_values=(first.scale_values[0]*2,)+first.scale_values[1:])
        wrong=replace(seed,stages=(changed,)+seed.stages[1:])
        with self.assertRaisesRegex(ValueError,'grid or dimensions'):
            service.run(RECORDS[1:],method='model_only_fresh',initial_model=wrong)
        with self.assertRaisesRegex(ValueError,'model_only_fresh'):
            service.run(RECORDS[1:],initial_model=seed)
        with self.assertRaisesRegex(ValueError,'speculative backend'):
            reference.run(RECORDS[1:],method='model_only_fresh',initial_model=seed)

    def test_backend_options_and_target_are_explicit(self):
        reference,recipe=self.make()
        with self.assertRaisesRegex(ValueError,'dyadic-row'):
            CompactIdentityService(reference.decoder,build_row_target(reference.decoder,recipe),solver_backend='speculative')
        for options in ({'max_sweeps':True},{'max_sweeps':-1},{'row_batch_size':0},{'block_width':0}):
            with self.assertRaises(ValueError):
                CompactIdentityService(reference.decoder,reference.target,solver_backend='block_speculative',**options)
        with self.assertRaisesRegex(ValueError,'speculative options'):
            CompactIdentityService(reference.decoder,reference.target,max_sweeps=1)
        whole=CompactIdentityService(reference.decoder,reference.target,solver_backend='speculative')
        block=CompactIdentityService(reference.decoder,reference.target,solver_backend='block_speculative')
        self.assertEqual(whole.speculative_options,{'max_sweeps':2,'row_batch_size':128})
        self.assertEqual(block.speculative_options,{'max_sweeps':1,'row_batch_size':4096,'block_width':32})
        with self.assertRaises(TypeError):
            block.speculative_options['max_sweeps']=5
        with self.assertRaisesRegex(ValueError,'only to the block_speculative'):
            CompactIdentityService(reference.decoder,reference.target,solver_backend='speculative',block_width=16)


if __name__=='__main__':
    unittest.main()
