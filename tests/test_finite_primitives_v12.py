import math
import struct
import unittest
from src import certified_intervals as ci
from src.finite_primitives import round_mpfr,primitive_scope,rounded,primitive_manifest
from src.certified_transformer import CertifiedDecoder
from tests.test_transformer_backend import decoder_fixture


class FinitePrimitiveTests(unittest.TestCase):
    def test_reference_bits(self):
        tiny=float.fromhex('0x0.0000000000001p-1022')
        for name in ['exp','sqrt','erf','tanh']:
            for value in [-20.,-1.,-.1,-tiny,-0.,0.,tiny,.1,.5,1.,2.,20.]:
                if name=='sqrt' and value<0:continue
                a=getattr(ci,'round_'+name)(value)
                b=round_mpfr(name,value)
                self.assertEqual(struct.pack('<d',a),struct.pack('<d',b),(name,value))

    def test_scope_and_context_restore(self):
        import gmpy2 as g
        before=g.get_context().copy()
        with primitive_scope('mpfr_enclosure'):self.assertEqual(rounded('tanh',.1),ci.round_tanh(.1))
        self.assertEqual(g.get_context().precision,before.precision)
        self.assertEqual(g.get_context().round,before.round)
        with self.assertRaises(ValueError):round_mpfr('sqrt',-1.)

    def test_hostile_ambient_context_cannot_change_enclosures(self):
        import gmpy2 as g
        expected={name:struct.pack('<d',round_mpfr(name,.1)) for name in ('exp','sqrt','erf','tanh')}
        with g.context(precision=7,round=g.RoundToZero,emin=-2,emax=2,subnormalize=True,
                       trap_underflow=True,trap_overflow=True,trap_inexact=True,
                       trap_invalid=True,trap_erange=True,trap_divzero=True,
                       allow_complex=True):
            before=str(g.get_context())
            for name in expected:
                self.assertEqual(struct.pack('<d',round_mpfr(name,.1)),expected[name])
                self.assertEqual(str(g.get_context()),before)
            with self.assertRaises(ValueError):round_mpfr('sqrt',-1.)
            self.assertEqual(str(g.get_context()),before)

    def test_manifest_copies_cannot_change_bound_decoder(self):
        decoder=CertifiedDecoder(decoder_fixture(),primitive_backend='mpfr_enclosure')
        before=decoder.kernel_manifest
        external=primitive_manifest('mpfr_enclosure')
        external['backend']='forged'
        external['binary_sha256'].clear()
        external['mpfr_context']['emin']=0
        self.assertEqual(decoder.kernel_manifest,before)
        self.assertEqual(primitive_manifest('mpfr_enclosure')['backend'],'mpfr_enclosure')
        self.assertTrue(primitive_manifest('mpfr_enclosure')['binary_sha256'])
        self.assertEqual(primitive_manifest('mpfr_enclosure')['mpfr_context']['emin'],-16384)

    def test_mpfr_generator_scope_never_leaks_at_suspension(self):
        import src.finite_primitives as primitives
        from src.sequential_finite import sequential_features
        base=decoder_fixture(block_count=2)
        decoder=CertifiedDecoder(base,primitive_backend='mpfr_enclosure')
        reference=CertifiedDecoder(base)
        tokens=(0,1)
        stream=sequential_features(decoder,tokens)
        stage,features=next(stream)
        self.assertEqual(primitives._BACKEND.get(),'rational')
        prefix={}
        for index,expected_stage in enumerate(decoder.stage_ids):
            self.assertEqual(stage,expected_stage)
            exact=reference.stage_features(stage,tokens,prefix)
            self.assertEqual([[struct.pack('<d',x) for x in row] for row in features],
                             [[struct.pack('<d',float(exact[k][t])) for k in range(len(exact))] for t in range(len(tokens))])
            installed=decoder.stage_weights(stage)
            prefix[stage]=installed
            if index+1<len(decoder.stage_ids):stage,features=stream.send(installed)
            else:
                with self.assertRaises(StopIteration):stream.send(installed)
            self.assertEqual(primitives._BACKEND.get(),'rational')

    def test_precision_rejection_and_nested_scope_restore(self):
        import src.finite_primitives as primitives
        with primitive_scope('mpfr_enclosure'):
            with self.assertRaises(ci.UnresolvedRounding):round_mpfr('exp',1.,initial_bits=1,max_bits=1)
            self.assertEqual(primitives._BACKEND.get(),'mpfr_enclosure')
            with self.assertRaises(RuntimeError):
                with primitive_scope('rational'):
                    raise RuntimeError('test restoration')
            self.assertEqual(primitives._BACKEND.get(),'mpfr_enclosure')
        self.assertEqual(primitives._BACKEND.get(),'rational')

    def test_complete_decoder_bits_and_binding(self):
        base=decoder_fixture(block_count=2)
        a=CertifiedDecoder(base)
        b=CertifiedDecoder(base,primitive_backend='mpfr_enclosure')
        self.assertNotEqual(a.evaluator_id,b.evaluator_id)
        self.assertEqual(a.logits((0,1,2)),b.logits((0,1,2)))
        self.assertTrue(primitive_manifest('mpfr_enclosure')['binary_sha256'])


if __name__=='__main__':unittest.main()
