import unittest
from unittest.mock import patch
import numpy as np
from research_v52.worker import encode_checked,compare_codes
from src import fixed_lossless_codec_v29 as lossless,fixed_factor_codec_v26 as codec
from src.run_store import digest
from research_v51.stage import STAGE_ID


class PrecisionTests(unittest.TestCase):
    def fixture(self):
        values=np.array([[0.,-0.,.1,-.2,3.141592653589793],[-5.,1e-8,1e8,-1e-8,.123456789123456]],dtype=np.float64)
        kwargs=dict(target_sha256='1'*64,anchor_target_sha256='2'*64,record_id='fixture',
            token_sha256='3'*64,stage_id=STAGE_ID)
        desc=lossless.encode_factor(values,**kwargs)
        item=dict(record_id='fixture',features_sha256=desc.source_sha256,token_sha256='3'*64)
        manifest={k:kwargs[k] for k in ('target_sha256','anchor_target_sha256')}
        return values,lossless.serialize(desc),item,manifest

    def test_next_precision_preserves_source_commitment_and_encloses_every_value(self):
        values,raw,item,manifest=self.fixture();out=encode_checked(raw,item,manifest)
        desc=codec.parse(out,expected_sha256=digest(out));box=desc.box()
        self.assertEqual(desc.bits,48);self.assertEqual(desc.block_size,256)
        self.assertEqual(desc.source_sha256,digest(values.astype('<f8').tobytes()))
        self.assertTrue(np.all(box.lower<=values) and np.all(values<=box.upper))

    def test_wrong_source_binding_rejected_before_encoding(self):
        values,raw,item,manifest=self.fixture();item['features_sha256']='0'*64
        with patch('research_v52.worker.codec.encode_factor',side_effect=AssertionError('No unbound encoding')):
            with self.assertRaisesRegex(ValueError,'binding'):encode_checked(raw,item,manifest)

    def test_missing_containment_rejected_even_with_matching_source_hash(self):
        values,raw,item,manifest=self.fixture()
        def incorrect(desc):
            from types import SimpleNamespace
            return SimpleNamespace(lower=np.ones_like(values)*1e20,upper=np.ones_like(values)*1e21)
        with patch.object(codec.FactorDescriptor,'box',incorrect):
            with self.assertRaisesRegex(ValueError,'containment'):encode_checked(raw,item,manifest)

    def test_partial_or_different_output_never_counts_as_exact_match(self):
        original=b'\x12\x34\x56\x78'
        compare_codes(original,original,8,digest(original))
        for changed in (original[:-1],b'\x12\x34\x56\x79'):
            with self.assertRaisesRegex(ValueError,'bytes differ'):compare_codes(changed,original,8,digest(original))


if __name__=='__main__':unittest.main()
