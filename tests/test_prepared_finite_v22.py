"""Equivalent evaluator setup for validated immutable compact prefixes."""
import struct
import unittest
from unittest.mock import patch

from src.certified_transformer import CertifiedDecoder
from src.compact_exact import CompactDyadicMatrix, CompactDyadicVector
from src.prepared_finite import PreparedFinitePrefix
from tests.test_prepared_finite_v12 import bits
from tests.test_transformer_backend import decoder_fixture


class PreparedCompactTests(unittest.TestCase):
    def setUp(self):
        self.decoder=CertifiedDecoder(decoder_fixture(),primitive_backend='mpfr_enclosure')
        self.stage=self.decoder.stage_ids[0]
        weights=self.decoder.stage_weights(self.stage)
        self.shape=(len(weights),len(weights[0]))

    def matrix(self, dtype='F64', reverse=False):
        count=self.shape[0]*self.shape[1]
        values=([-0.0,0.0,0.25,-0.5,1.0,-1.0]*count)[:count]
        if dtype=='BF16':
            raw=b''.join(struct.pack('<H',struct.unpack('<I',struct.pack('<f',v))[0]>>16) for v in values)
        else:
            fmt={'F16':'e','F32':'f','F64':'d'}[dtype]
            raw=b''.join(struct.pack('<'+fmt,v) for v in values)
        vector=CompactDyadicVector.from_bytes(raw,dtype)
        return (vector[::-1] if reverse else vector).matrix(*self.shape)

    def test_compact_setup_does_not_iterate_exact_values(self):
        matrix=self.matrix()
        with patch.object(CompactDyadicMatrix,'__iter__',side_effect=AssertionError('redundant exact scan')):
            prepared=PreparedFinitePrefix(self.decoder,{self.stage:matrix})
        self.assertEqual(bits(prepared.logits((0,1))),bits(self.decoder.logits((0,1),{self.stage:matrix})))

    def test_all_storage_types_and_strides_match_original_bits(self):
        for dtype in ('F16','BF16','F32','F64'):
            for reverse in (False,True):
                with self.subTest(dtype=dtype,reverse=reverse):
                    prefix={self.stage:self.matrix(dtype,reverse)}
                    prepared=PreparedFinitePrefix(self.decoder,prefix)
                    original=self.decoder.base._prefix(prefix)
                    self.assertEqual(bits(prepared.installed[self.stage]),bits(original[self.stage]))
                    self.assertEqual(bits(prepared.logits((2,1))),bits(self.decoder.logits((2,1),prefix)))

    def test_mixed_representations_retain_original_validation(self):
        matrix=self.matrix()
        second=self.decoder.stage_ids[1]
        prefix={self.stage:matrix,second:self.decoder.stage_weights(second)}
        self.assertEqual(bits(PreparedFinitePrefix(self.decoder,prefix).logits((0,2))),
                         bits(self.decoder.logits((0,2),prefix)))
        bad=[list(row) for row in self.decoder.stage_weights(second)]
        bad[0][0]=float(bad[0][0])
        with self.assertRaises(TypeError):
            PreparedFinitePrefix(self.decoder,{self.stage:matrix,second:bad})

    def test_stage_shape_and_immutable_capture(self):
        matrix=self.matrix()
        with self.assertRaises(ValueError):PreparedFinitePrefix(self.decoder,{'missing':matrix})
        wrong=CompactDyadicVector.from_bytes(struct.pack('<d',0.0),'F64').matrix(1,1)
        with self.assertRaises(ValueError):PreparedFinitePrefix(self.decoder,{self.stage:wrong})
        prefix={self.stage:matrix}
        prepared=PreparedFinitePrefix(self.decoder,prefix)
        before=bits(prepared.logits((0,1)))
        prefix.clear()
        self.assertEqual(before,bits(prepared.logits((0,1))))
        with self.assertRaises(TypeError):prepared.installed[self.stage]=None
        with self.assertRaises(ValueError):CompactDyadicVector.from_bytes(struct.pack('<d',float('nan')),'F64')

    def test_compact_subclass_cannot_bypass_value_validation(self):
        class FloatSubclass(CompactDyadicMatrix):
            def __iter__(self):
                return iter([[0.0]*self._columns for _ in range(self._rows)])
        m=self.matrix()
        fake=FloatSubclass(m._storage,m._offset,m._rows,m._columns,m._row_stride,m._column_stride)
        with self.assertRaises(TypeError):
            PreparedFinitePrefix(self.decoder,{self.stage:fake})


if __name__=='__main__':unittest.main()
