import unittest,struct
from research_v135 import source_state as s
from research_v61.test_target import bind,fixture
from research_v61.test_state import record,codes
from src.run_store import canonical_json,strict_json

class SourceOnly(unittest.TestCase):
    def setUp(self):
        self.t=bind(*fixture(((2,4),(1,2)),original=512));self.r=(record('a',[1,2]),record('b',[3,4]));self.c=codes(self.t)
    def test_both_modes_exact_roundtrip(self):
        for mode in ('tokens','references'):
            b=s.pack(self.t,self.r,self.c,mode);v=s.unpack(b,lambda rid,meta:dict(a=[1,2],b=[3,4])[rid]);self.assertEqual(v.codes,self.c);self.assertEqual(v.records,self.r)
    def test_tokens_need_no_external_source_and_no_callback(self):
        def forbidden(*_):raise AssertionError('External corpus called')
        s.unpack(s.pack(self.t,self.r,self.c),forbidden)
    def test_references_refuse_missing_and_wrong_words(self):
        b=s.pack(self.t,self.r,self.c,'references')
        with self.assertRaises(PermissionError):s.unpack(b)
        with self.assertRaises(ValueError):s.unpack(b,lambda *_:[9,9])
    def test_successor_excludes_deleted_tokens_and_matches_fresh_pack(self):
        b=s.pack(self.t,self.r,self.c);v=s.unpack(b);got=s.successor(v,('b',),self.c)
        self.assertEqual(got,s.pack(self.t,self.r[1:],self.c));self.assertEqual([r.record_id for r in s.unpack(got).records],['b'])
    def test_corrupt_model_and_trailing_bytes_rejected(self):
        b=s.pack(self.t,self.r,self.c)
        for bad in (b[:-1],b+b'x',b[:-1]+bytes([b[-1]^1])):
            with self.assertRaises(ValueError):s.unpack(bad)
    def test_hidden_cache_field_rejected(self):
        b=s.pack(self.t,self.r,self.c);n=struct.unpack_from('<Q',b,8)[0];h=strict_json(b[16:16+n]);h['feature_cache']='hidden';raw=canonical_json(h)
        with self.assertRaises(ValueError):s.unpack(b[:8]+struct.pack('<Q',len(raw))+raw+b[16+n:])
    def test_duplicate_membership_and_incomplete_codes_rejected(self):
        with self.assertRaises(ValueError):s.pack(self.t,(self.r[0],self.r[0]),self.c)
        with self.assertRaises(ValueError):s.pack(self.t,self.r,self.c[:1])
    def test_reference_successor_never_requests_deleted_record(self):
        b=s.successor(s.unpack(s.pack(self.t,self.r,self.c)),('b',),self.c)
        v=s.unpack(b);ref=s.pack(v.target,v.records,v.codes,'references');seen=[]
        def provider(rid,meta):seen.append(rid);return [3,4]
        s.unpack(ref,provider);self.assertEqual(seen,['b'])
    def test_predecessor_reference_selection_never_reads_deleted(self):
        b=s.pack(self.t,self.r,self.c,'references');seen=[]
        def provider(rid,meta):
            self.assertEqual(rid,'b');seen.append(rid);return [3,4]
        v=s.select_retained(b,('b',),provider);self.assertEqual(seen,['b']);self.assertEqual(v.records,self.r[1:])
        self.assertEqual(s.successor(v,('b',),self.c),s.pack(self.t,self.r[1:],self.c,'references'))
    def test_corrupt_predecessor_rejected_before_external_lookup(self):
        b=s.pack(self.t,self.r,self.c,'references');seen=[]
        with self.assertRaises(ValueError):s.select_retained(b[:-1],('b',),lambda *x:seen.append(x))
        self.assertEqual(seen,[])
if __name__=='__main__':unittest.main()
