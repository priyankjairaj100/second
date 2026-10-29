"""Cache mechanics with actual stdlib lossless encoders, not V63 qualification."""
import hashlib,json,random,struct,sys,types,unittest,zlib
from research_v77.canonical_reuse import ChoiceCache,enabled

class Checks(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        def select(raw,measurements=None):
            self.calls.append(raw)
            choices=(raw,zlib.compress(raw,6))
            if measurements is not None:measurements.extend(len(x) for x in choices)
            mode=min(range(2),key=lambda i:(len(choices[i]),i))
            return mode,choices[mode]
        self.select=select

    def test_byte_identity_signed_zero_and_equal_distinct_objects(self):
        cache=ChoiceCache(self.select,max_bytes=10000)
        a=struct.pack('<dd',0.,1.);b=struct.pack('<dd',-0.,1.)
        self.assertEqual(cache(a),self.select(a));self.assertEqual(cache(b),self.select(b))
        self.assertEqual(cache(bytes(bytearray(a))),self.select(a))
        self.assertEqual((cache.hits,cache.misses),(1,2))

    def test_lru_eviction_and_entry_bound(self):
        cache=ChoiceCache(self.select,max_bytes=10000,max_entries=2)
        for raw in (b'a',b'b',b'a',b'c'):cache(raw)
        self.assertEqual(list(cache.entries),[b'a',b'c'])
        cache(b'b');self.assertEqual(cache.evictions,2)
        self.assertEqual(len(cache.entries),2)

    def test_actual_byte_bound_and_oversize_bypass(self):
        cache=ChoiceCache(self.select,max_bytes=500)
        rng=random.Random(20261022)
        for i in range(100):
            raw=rng.randbytes(i*7+1)
            self.assertEqual(cache(raw),self.select(raw))
            self.assertLessEqual(cache.retained_bytes,500)
        self.assertLessEqual(cache.peak_retained_bytes,500)

    def test_measurements_always_execute(self):
        cache=ChoiceCache(self.select,max_bytes=10000)
        raw=b'a'*100
        cache(raw);before=len(self.calls);measurements=[]
        self.assertEqual(cache(raw,measurements),self.select(raw))
        self.assertEqual(len(self.calls),before+2)
        self.assertEqual(len(measurements),2);self.assertEqual(cache.bypasses,1)

    def test_mapping_capacity_and_repeated_hits_respect_budget(self):
        for cap in (0,236,237,240,256,300,450,500,700,1000):
            cache=ChoiceCache(self.select,max_bytes=cap,max_entries=4)
            for i in range(100):
                raw=bytes([i%7])*(1+i%11)
                self.assertEqual(cache(raw),self.select(raw))
                cache(bytes(bytearray(raw)))
                charge=cache.retained_bytes+max(0,sys.getsizeof(cache.entries)-cache.base_mapping_bytes)
                self.assertLessEqual(charge,cap)
                self.assertLessEqual(cache.peak_retained_bytes,cap)

    def test_zero_cap_has_no_reuse(self):
        cache=ChoiceCache(self.select,max_bytes=0)
        self.assertEqual(cache(b'hi'),cache(b'hi'))
        self.assertEqual(len(cache.entries),0);self.assertEqual(cache.hits,0)

    def test_failure_never_populates(self):
        def bad(raw,measurements=None):raise ValueError('fixture')
        cache=ChoiceCache(bad,max_bytes=10000)
        with self.assertRaises(ValueError):cache(b'hi')
        self.assertEqual(len(cache.entries),0)

    def test_scope_restores_and_clears_on_exception(self):
        codec=types.SimpleNamespace(_select=self.select)
        with self.assertRaises(LookupError):
            with enabled(codec,max_bytes=10000) as cache:
                codec._select(b'hi')
                with self.assertRaises(RuntimeError):
                    with enabled(codec,max_bytes=10000):pass
                raise LookupError('fixture')
        self.assertIs(codec._select,self.select)
        self.assertEqual(cache.retained_bytes,0);self.assertEqual(len(cache.entries),0)
        with self.assertRaises(RuntimeError):cache(b'hi')

    def test_nonbytes_preserve_original_behavior(self):
        cache=ChoiceCache(self.select,max_bytes=10000)
        value=bytearray(b'hi')
        self.assertEqual(cache(value),self.select(value))
        self.assertEqual(len(cache.entries),0)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(scope='stdlib cache mechanics only; V63 parser and zstandard not exercised',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors))))
    if not result.wasSuccessful():sys.exit(1)
