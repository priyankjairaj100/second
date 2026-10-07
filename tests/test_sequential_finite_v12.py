"""Compare each incremental stage with the complete restart reference."""
from fractions import Fraction as Q
import struct
import unittest
from src.certified_transformer import CertifiedDecoder
from src.sequential_finite import sequential_features
from tests.test_transformer_backend import decoder_fixture
from tests.test_certified_transformer import small_decoder


class SequentialFiniteTests(unittest.TestCase):
    def check(self,decoder,tokens):
        stream=sequential_features(decoder,tokens)
        stage,features=next(stream)
        prefix={}
        for index,expected in enumerate(decoder.stage_ids):
            self.assertEqual(stage,expected)
            reference=decoder.stage_features(stage,tokens,prefix)
            self.assertEqual([[struct.pack('<d',x) for x in row] for row in features],
                             [[struct.pack('<d',float(reference[k][t])) for k in range(len(reference))] for t in range(len(tokens))])
            # Change each installed stage, so stale-base caching cannot pass.
            installed=tuple(tuple(Q(0) if (i+j)%3==0 else x+Q(1,64)
                                  for j,x in enumerate(row)) for i,row in enumerate(decoder.stage_weights(stage)))
            prefix[stage]=installed
            if index+1<len(decoder.stage_ids):stage,features=stream.send(installed)
            else:
                with self.assertRaises(StopIteration):stream.send(installed)

    def test_multi_block_changed_prefix(self):
        self.check(CertifiedDecoder(decoder_fixture(block_count=2)),(0,1,2))

    def test_both_activations(self):
        for name in ['gelu','gelu_new']:
            self.check(small_decoder(name)[0],(0,1))


if __name__=='__main__':unittest.main()
