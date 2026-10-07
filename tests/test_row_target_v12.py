from fractions import Fraction as Q
import unittest
from src.certified_transformer import CertifiedDecoder
from src.target_manifest import TargetRecipe,build_target
from src.row_target_manifest import build_row_target
from tests.test_transformer_backend import decoder_fixture


class RowTargetTests(unittest.TestCase):
    def test_distinct_target_complete_bindings_and_safe_scales(self):
        decoder=CertifiedDecoder(decoder_fixture(block_count=2))
        recipe=TargetRecipe(original_token_count=6,group_count=1)
        legacy=build_target(decoder,recipe,weight_digest_encoding='binary64_matrix_v1')
        target=build_row_target(decoder,recipe)
        self.assertNotEqual(target.digest,legacy.digest)
        self.assertIn('no canonical repair-state',target.payload()['output_rule'])
        for stage,entry in zip(target.stages,target.payload()['stages']):
            self.assertFalse(hasattr(stage,'grids'))
            self.assertEqual(entry['grid_axis'],'output_row')
            self.assertEqual(len(stage.scale_exponents),len(stage.weights))
            self.assertEqual(entry['shape'],[len(stage.weights),stage.width])
            for row,e in zip(stage.weights,stage.scale_exponents):
                a=Q(2)**e
                self.assertTrue(all(-8*a<=w<=7*a for w in row))
        before=target.digest
        payload=target.payload();payload['stages'][0]['row_scale_exponents'][0]+=1
        self.assertEqual(target.digest,before)


if __name__=='__main__':unittest.main()
