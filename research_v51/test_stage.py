import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import numpy as np
from research_v51.stage import prefix_factor, checked_feature
from research_v51 import campaign
from src.anchor_transformer import prepare_context
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.ordered_fixed_service_v30 import prepare_ordered_leaf
from src.dyadic_row_target import build_dyadic_row_target
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


@unittest.skipUnless(sys.platform=='linux','Pinned Linux runtime required')
class PrefixTests(unittest.TestCase):
    def fixture(self):
        decoder=OrderedFiniteDecoder(decoder_fixture(block_count=2),primitive_backend='mpfr_enclosure')
        target=build_dyadic_row_target(decoder,TargetRecipe(original_token_count=4,group_count=1))
        return decoder,target,prepare_context(decoder,target)

    def test_every_prefix_matches_complete_leaf_words(self):
        decoder,target,context=self.fixture()
        for tokens in ([0,1],[2,0,1]):
            row=dict(id='fixture',tokens=tokens)
            leaf=prepare_ordered_leaf(decoder,target,row,context=context)
            for expected in leaf.blocks:
                actual=prefix_factor(decoder,target,row,context,expected.stage_id)
                self.assertEqual(actual.binary64,expected.binary64)

    def test_foreign_context_and_unknown_stage_refused_before_source(self):
        decoder,target,context=self.fixture();row=dict(id='fixture',tokens=[0,1])
        with patch('research_v51.stage.ordered_sequential_features',side_effect=AssertionError('no source read')):
            with self.assertRaisesRegex(ValueError,'context'):
                prefix_factor(decoder,target,row,replace(context,target_sha256='0'*64))
            with self.assertRaisesRegex(ValueError,'outside'):
                prefix_factor(decoder,target,row,context,'unknown')

    def test_prefix_stops_at_requested_yield_and_closes_generator(self):
        decoder,target,context=self.fixture();seen=[]
        def stream(*args):
            try:
                for i,stage in enumerate(target.stages):
                    seen.append(stage.stage_id)
                    received=yield stage.stage_id,np.zeros((2,stage.width))
                    self.assertIs(received,context.anchor_matrices[i])
                raise AssertionError('Read past target')
            finally:seen.append('closed')
        with patch('research_v51.stage.ordered_sequential_features',stream):
            prefix_factor(decoder,target,dict(id='fixture',tokens=[0,1]),context)
        self.assertEqual(seen,[s.stage_id for s in target.stages[:4]]+['closed'])


class AdmissionTests(unittest.TestCase):
    def test_wide_gram_not_silently_admitted_and_all_workers_fit_new_caps(self):
        report=campaign.review()
        self.assertEqual(report['native_gram_max_width'],768)
        self.assertEqual(set(report['reports']),{'candidate','reference','compressed'})
        self.assertTrue(all(r['selected_route']=='streamed' and r['admitted'] for r in report['reports'].values()))
        self.assertEqual(sum(campaign.CAPS.values()),5108)

    def test_bad_feature_shape_type_and_nonfinite_values_refused(self):
        for a in (np.zeros((2,3),dtype=np.float32),np.zeros((3,2)),np.full((2,3),np.nan)):
            with self.assertRaises(ValueError):checked_feature(a,3,2)

    def test_durable_command_admission_rejects_other_trial(self):
        from src.transaction_timing import verify_command_admission
        from src.run_store import canonical_json
        import os
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();(root/'program.json').write_bytes(canonical_json({'fixture':True}))
            budget=campaign.budget(root);budget.reserve('candidate','fixture',10)
            command=[sys.executable,'-B','-m','research_v51.worker',str(root),'candidate']
            binding=dict(phase_budget_root=str(budget.root),phase_budget_binding_sha256=budget.identity_digest,
                attempt_id='fixture',phase='candidate',command=command,cwd=str(campaign.ROOT))
            with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(binding).decode()):
                verify_command_admission(campaign.sha(root/'program.json'),'candidate',command)
                with self.assertRaises(ValueError):
                    verify_command_admission(campaign.sha(root/'program.json'),'reference',command[:-1]+['reference'])


if __name__=='__main__':unittest.main()
