import struct
import unittest
from fractions import Fraction as Q
from src.binary64_identity import binary64_matrix_sha256
from src.compact_exact import CompactDyadicVector
from src.target_manifest import build_target,TargetRecipe
from tests.test_certified_transformer import small_decoder


class Binary64IdentityTests(unittest.TestCase):
    def test_compact_tuple_and_signed_zero(self):
        values=CompactDyadicVector.from_bytes(struct.pack('<4f',1.,-0.,.25,-.5),'F32').matrix(2,2)
        exact=((Q(1),Q(0)),(Q(1,4),Q(-1,2)))
        self.assertEqual(binary64_matrix_sha256(values),binary64_matrix_sha256(exact))
        self.assertNotEqual(binary64_matrix_sha256(values),binary64_matrix_sha256(((Q(1),Q(0),Q(1,4),Q(-1,2)),)))

    def test_unrepresentable_rejected(self):
        with self.assertRaises(ValueError):binary64_matrix_sha256(((Q(1,3),),))

    def test_explicit_encoding_preserves_target_values(self):
        decoder=small_decoder()[0];recipe=TargetRecipe(original_token_count=4,group_count=1)
        old=build_target(decoder,recipe)
        new=build_target(decoder,recipe,weight_digest_encoding='binary64_matrix_v1')
        self.assertEqual(old.stages,new.stages)
        self.assertEqual(old.scale_exponents,new.scale_exponents)
        self.assertNotEqual(old.digest,new.digest)
        self.assertEqual(new.payload()['schema'],'fixed-v-cert-target-v2')
        self.assertNotIn('weight_digest_encoding',old.payload())


if __name__=='__main__':unittest.main()
