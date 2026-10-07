from fractions import Fraction as Q
import struct
import unittest
from src.certified_transformer import CertifiedDecoder
from src.prepared_finite import PreparedFinitePrefix
from tests.test_transformer_backend import decoder_fixture


def bits(rows):return b''.join(struct.pack('<d',x) for row in rows for x in row)


class PreparedFiniteTests(unittest.TestCase):
    def test_repeated_records_match_complete_original_path(self):
        for backend in ['rational','mpfr_enclosure']:
            decoder=CertifiedDecoder(decoder_fixture(block_count=2),primitive_backend=backend)
            prefix={stage:[[w+Q(1,16) for w in row] for row in decoder.stage_weights(stage)] for stage in decoder.stage_ids}
            for installed in [None,prefix]:
                prepared=PreparedFinitePrefix(decoder,installed)
                for tokens in [(0,1,2),(2,1),(0,)]:
                    self.assertEqual(bits(prepared.logits(tokens)),bits(decoder.logits(tokens,installed)))

    def test_compact_immutable_prefix_matches_reference(self):
        from src.compact_exact import CompactDyadicVector
        decoder=CertifiedDecoder(decoder_fixture(block_count=2))
        prefix={}
        for stage in decoder.stage_ids:
            weights=decoder.stage_weights(stage)
            raw=b''.join(struct.pack('<d',float(x)) for row in weights for x in row)
            prefix[stage]=CompactDyadicVector.from_bytes(raw,'F64').matrix(len(weights),len(weights[0]))
        prepared=PreparedFinitePrefix(decoder,prefix)
        self.assertEqual(bits(prepared.logits((0,1,2))),bits(decoder.logits((0,1,2),prefix)))
        prefix.clear()
        self.assertEqual(bits(prepared.logits((0,1,2))),bits(decoder.logits((0,1,2))))

    def test_external_mutation_cannot_change_captured_codes(self):
        decoder=CertifiedDecoder(decoder_fixture())
        stage=decoder.stage_ids[0]
        prefix={stage:[list(row) for row in decoder.stage_weights(stage)]}
        prepared=PreparedFinitePrefix(decoder,prefix)
        before=bits(prepared.logits((0,1)))
        prefix[stage][0][0]+=Q(1)
        self.assertEqual(bits(prepared.logits((0,1))),before)
        with self.assertRaises(TypeError):prepared.installed[stage]=()
        with self.assertRaises(AttributeError):prepared.decoder=decoder
        with self.assertRaises((ValueError,TypeError)):prepared.logits((-1,))


if __name__=='__main__':unittest.main()
