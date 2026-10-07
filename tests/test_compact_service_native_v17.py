"""Complete native service software fixtures; no empirical speed evidence."""
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


class NativeCompactServiceTests(unittest.TestCase):
    def make(self):
        decoder=CertifiedDecoder(decoder_fixture(block_count=1),primitive_backend='mpfr_enclosure')
        recipe=TargetRecipe(original_token_count=6,bits=3,group_count=1,ridge=Q(1,10))
        target=build_dyadic_row_target(decoder,recipe)
        return CompactIdentityService(decoder,target),recipe

    def test_all_methods_and_factor_free_warm_control_match_reference(self):
        reference,_=self.make()
        original=reference.run(RECORDS)
        original_bytes=serialize(original.state)
        expected=reference.run(RECORDS[1:])
        expected_bytes=serialize(expected.state)
        seed=CompactState(reference.target.digest,original.stages,())
        service=CompactIdentityService(reference.decoder,reference.target,solver_backend='native_ball')
        fresh=service.run(RECORDS[1:])
        cold=service.run(RECORDS[1:],method='model_only_fresh')
        repaired=service.run(RECORDS[1:],method='repair',prior=original.state,deleted_ids=['a'])
        indexed=service.run(RECORDS[1:],method='indexed_fresh',prior=original.state,deleted_ids=['a'])
        with patch.object(RecordFactor,'array',side_effect=AssertionError('unexpected factor access')):
            warm=service.run(RECORDS[1:],method='model_only_fresh',initial_model=seed)
        for result in (fresh,repaired,indexed):
            self.assertEqual(serialize(result.state),expected_bytes)
        for result in (fresh,cold,repaired,indexed,warm):
            self.assertEqual(model_digest(result.stages),model_digest(expected.stages))
            metrics=result.diagnostics
            self.assertEqual(metrics['effective_solver_backends'],['native_ball'])
            self.assertEqual(metrics['changed_ancestor_pairs_avoided'],0)
            self.assertEqual(metrics['solver_options'],{})
            self.assertGreaterEqual(metrics['service_elapsed_ns'],sum(s['elapsed_ns'] for s in metrics['stages']))
            self.assertGreaterEqual(metrics['native_attempted_decisions'],metrics['native_prefix_certified_decisions'])
            for field,diagnostic in (('native_compile_elapsed_ns','compile_elapsed_ns'),
                                     ('native_kernel_elapsed_ns','native_elapsed_ns'),
                                     ('native_candidate_checks','candidate_checks'),
                                     ('native_candidate_hits','candidate_hits')):
                self.assertEqual(metrics[field],sum(s['solver_diagnostics'][diagnostic] for s in metrics['stages']))
            manifest=metrics['native_build_manifest']
            self.assertEqual(len(manifest['source_sha256']),64)
            self.assertEqual(len(manifest['binary_sha256']),64)
            self.assertIn('-ffp-contract=off',manifest['flags'])
            for stage in metrics['stages']:
                self.assertEqual(stage['solver_diagnostics']['native_source_sha256'],manifest['source_sha256'])
                self.assertEqual(stage['solver_diagnostics']['native_binary_sha256'],manifest['binary_sha256'])
        self.assertIsNone(warm.state)
        self.assertEqual(warm.diagnostics['cached_factor_reads'],0)
        self.assertEqual(warm.diagnostics['model_seed_factor_reads'],0)
        self.assertEqual(warm.diagnostics['model_seed_source'],'external_model_only')
        self.assertEqual(warm.diagnostics['model_seed_sha256'],prefix_digest(reference.target.digest,seed.stages))
        self.assertEqual(warm.diagnostics['model_seed_sha256'],repaired.diagnostics['model_seed_sha256'])
        self.assertEqual(repaired.diagnostics['model_seed_source'],'prior_state')
        self.assertEqual(cold.diagnostics['model_seed_source'],'none')
        self.assertEqual(cold.diagnostics['native_candidate_checks'],0)
        for left,right in zip(warm.diagnostics['stages'],repaired.diagnostics['stages']):
            self.assertEqual(left['candidate_stage_sha256'],right['candidate_stage_sha256'])
        self.assertEqual(serialize(original.state),original_bytes)

    def test_sequential_deletion_noop_and_empty_remain_canonical(self):
        reference,_=self.make()
        original=reference.run(RECORDS)
        service=CompactIdentityService(reference.decoder,reference.target,solver_backend='native_ball')
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

    def test_seed_and_backend_options_fail_closed(self):
        reference,recipe=self.make()
        original=reference.run(RECORDS)
        seed=CompactState(reference.target.digest,original.stages,())
        service=CompactIdentityService(reference.decoder,reference.target,solver_backend='native_ball')
        with self.assertRaisesRegex(ValueError,'no factors'):
            service.run(RECORDS[1:],method='model_only_fresh',initial_model=original.state)
        with self.assertRaisesRegex(ValueError,'target mismatch'):
            service.run(RECORDS[1:],method='model_only_fresh',initial_model=replace(seed,target_sha256='0'*64))
        with self.assertRaisesRegex(ValueError,'model_only_fresh'):
            service.run(RECORDS[1:],initial_model=seed)
        with self.assertRaisesRegex(ValueError,'dyadic-row'):
            CompactIdentityService(reference.decoder,build_row_target(reference.decoder,recipe),solver_backend='native_ball')
        for options in ({'max_sweeps':1},{'row_batch_size':2},{'block_width':16}):
            with self.assertRaisesRegex(ValueError,'speculative options'):
                CompactIdentityService(reference.decoder,reference.target,solver_backend='native_ball',**options)
        self.assertEqual(reference.solver_backend,'reference')


if __name__=='__main__':
    unittest.main()
