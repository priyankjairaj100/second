"""Generated actual V63 parser fixtures; no model, corpus or service execution."""
from contextlib import nullcontext
import hashlib,json,statistics,struct,sys,time,unittest
from unittest.mock import patch
import numpy as np
from research_v63 import codec,archive
from research_v63.test_control import KW,record,codes,features
from research_v61.test_target import bind,fixture
from src.run_store import canonical_json
from research_v77.canonical_reuse import enabled


def frame(blob,updates=None,payload=None):
    n=struct.unpack_from('<Q',blob,8)[0]
    h=json.loads(blob[16:16+n]);h.update(updates or {})
    body=blob[16+n:] if payload is None else payload
    if payload is not None:
        h.update(payload_bytes=len(body),payload_sha256=hashlib.sha256(body).hexdigest())
    header=canonical_json(h)
    return blob[:8]+struct.pack('<Q',len(header))+header+body


def outcome(blob,**kwargs):
    try:
        d=codec.parse(blob,**kwargs)
        return ('accept',codec.serialize(d),d.binary64())
    except (ValueError,TypeError):return ('reject',)


class Checks(unittest.TestCase):
    def setUp(self):
        self.values=np.arange(64,dtype=np.float64).reshape(8,8)/8
        self.blob=codec.serialize(codec.encode_factor(self.values,**KW))

    def test_warm_cache_does_not_bypass_per_call_limits_or_expected_hash(self):
        with enabled(codec,max_bytes=2**20) as cache:
            good=outcome(self.blob);self.assertEqual(outcome(self.blob),good)
            self.assertEqual(cache.hits,1)
            for limits in (codec.LoadLimits(max_bytes=len(self.blob)-1),codec.LoadLimits(max_header_bytes=1),
                           codec.LoadLimits(max_values=63),codec.LoadLimits(max_tokens=7),codec.LoadLimits(max_width=7)):
                self.assertEqual(outcome(self.blob,limits=limits),('reject',))
            self.assertEqual(outcome(self.blob,expected_sha256='f'*64),('reject',))
            self.assertEqual(outcome(bytes(bytearray(self.blob)),expected_sha256=hashlib.sha256(self.blob).hexdigest()),good)

    def test_warm_cache_retains_canonical_mode_and_payload_checks(self):
        raw=self.values.astype('<f8').tobytes()
        candidates=(raw,codec._compress(raw),codec._compress(codec._shuffle(raw)),codec._zstd(raw),codec._zstd(codec._shuffle(raw)))
        variants=[frame(self.blob,{'mode':m},payload) for m,payload in enumerate(candidates)]
        expected=[outcome(b) for b in variants]
        self.assertEqual(sum(x[0]=='accept' for x in expected),1)
        with enabled(codec,max_bytes=2**20) as cache:
            codec.parse(self.blob)
            self.assertEqual([outcome(b) for b in variants],expected)
            self.assertGreaterEqual(cache.hits,5)

    def test_warm_cache_cannot_relabel_metadata_or_runtime(self):
        with enabled(codec,max_bytes=2**20):
            codec.parse(self.blob)
            for key,val in (('source_sha256','0'*64),('codec_sha256','0'*64),('shape',[True,64]),('mode',True),('raw_bytes',8)):
                self.assertEqual(outcome(frame(self.blob,{key:val})),('reject',))
            with patch.object(codec.zstd,'__version__','unregistered'):
                self.assertEqual(outcome(self.blob),('reject',))

    def test_signed_zero_exact_words_and_new_request_isolation(self):
        words=np.array([0,1<<63,1,(1<<63)|1,0x7fefffffffffffff,0xffefffffffffffff],dtype='<u8')
        values=words.view('<f8').reshape(2,3)
        b=codec.serialize(codec.encode_factor(values,**KW))
        for _ in range(2):
            with enabled(codec,max_bytes=2**20) as cache:
                self.assertEqual(codec.parse(b).binary64(),words.tobytes())
                self.assertEqual((cache.hits,cache.misses),(0,1))
                self.assertEqual(codec.parse(b).binary64(),words.tobytes())
                self.assertEqual(cache.hits,1)
            self.assertEqual((cache.retained_bytes,len(cache.entries),cache.closed),(0,0,True))

    def test_measurement_calls_run_all_five_encoders(self):
        with enabled(codec,max_bytes=2**20) as cache:
            codec.parse(self.blob)
            for _ in range(2):
                measurements=[]
                self.assertEqual(codec.serialize(codec.encode_factor(self.values,**KW,measurements=measurements)),self.blob)
                self.assertEqual([m['mode'] for m in measurements],[0,1,2,3,4])
                self.assertTrue(all(m['encode_ns']>0 for m in measurements))
            self.assertEqual(cache.bypasses,2)

    def test_eviction_and_oversize_keep_actual_parser_bytes(self):
        blobs=[codec.serialize(codec.encode_factor(self.values+i,**KW)) for i in range(6)]
        expected=[outcome(b) for b in blobs]
        for cap in (0,500,1500,2**20):
            with enabled(codec,max_bytes=cap,max_entries=2) as cache:
                for order in (list(range(6)),list(reversed(range(6))),list(range(6))):
                    for i in order:self.assertEqual(outcome(blobs[i]),expected[i])
                self.assertLessEqual(cache.peak_retained_bytes,cap)
                self.assertLessEqual(len(cache.entries),2)

    def test_mutation_and_truncation_parity_after_warm_parse(self):
        rng=np.random.default_rng(20261023)
        variants=[self.blob[:i] for i in range(len(self.blob))]+[self.blob+b'x']
        for _ in range(300):
            b=bytearray(self.blob);i=int(rng.integers(len(b)));b[i]^=int(rng.integers(1,256));variants.append(bytes(b))
        expected=[outcome(b) for b in variants]
        with enabled(codec,max_bytes=2**20):
            codec.parse(self.blob)
            self.assertEqual([outcome(b) for b in variants],expected)

    def test_archive_record_binding_after_cached_choice(self):
        target=bind(*fixture(((2,3),(1,2)),original=8));records=(record('a',(1,2)),record('b',(3,4)))
        packed_codes=codes(target);sources={}
        for s in target.stages:
            for r in records:
                kw=dict(target_sha256=hashlib.sha256(target.fixed_payload).hexdigest(),anchor_target_sha256=hashlib.sha256(target.anchor_payload).hexdigest(),
                    record_id=r.record_id,token_sha256=r.token_sha256,stage_id=s.stage_id)
                sources[s.stage_id,r.record_id]=codec.serialize(codec.encode_factor(features(s,r),**kw))
        expected=archive.pack(target,records,packed_codes,sources)
        expected_restored=archive.restore(archive.unpack(expected))
        with enabled(codec,max_bytes=2**20):
            self.assertEqual(archive.pack(target,records,packed_codes,sources),expected)
            self.assertEqual(archive.restore(archive.unpack(expected)),expected_restored)
            for key in ('record_id','stage_id','target_sha256','token_sha256'):
                bad=dict(sources);k=next(iter(bad));bad[k]=frame(bad[k],{key:'0'*64 if key.endswith('_sha256') else 'wrong'})
                with self.assertRaises(ValueError):archive.pack(target,records,packed_codes,bad)


def profile():
    rng=np.random.default_rng(20261024);rows=[]
    for width in (768,3072):
        values=rng.normal(size=(128,width));values[:,::31]=0
        blob=codec.serialize(codec.encode_factor(values,**KW));expected=values.astype('<f8').tobytes()
        samples={m:[] for m in ('reference','optimized')};stats=[]
        for repeat in range(6):
            for mode in (('reference','optimized') if repeat%2==0 else ('optimized','reference')):
                start=time.perf_counter_ns()
                with (enabled(codec,max_bytes=32*2**20) if mode=='optimized' else nullcontext()) as cache:
                    outputs=[]
                    for _ in range(3):
                        d=codec.parse(blob,expected_sha256=hashlib.sha256(blob).hexdigest());outputs.append(d.binary64())
                    if cache is not None:before=cache.stats()
                elapsed=time.perf_counter_ns()-start
                assert all(raw==expected for raw in outputs)
                if cache is not None:
                    assert cache.closed and not cache.entries and before['misses']==1 and before['hits']==2
                    stats.append(before)
                samples[mode].append(elapsed)
        medians={k:statistics.median(v)/1e9 for k,v in samples.items()}
        rows.append(dict(shape=[128,width],operation='three full parse/decode calls with cache create/clear',samples_ns=samples,median_seconds=medians,speedup=medians['reference']/medians['optimized'],cache_statistics=stats,source_words_sha256=hashlib.sha256(expected).hexdigest()))
    return rows


def main(output):
    start=time.perf_counter_ns();result={'scope':'Generated V63 parser and control software qualification; no neural or full-request measurement','suites':{}}
    for mode in ('reference','optimized'):
        suite=unittest.defaultTestLoader.loadTestsFromName('research_v63.test_control')
        with (enabled(codec,max_bytes=32*2**20) if mode=='optimized' else nullcontext()):
            r=unittest.TextTestRunner(verbosity=2).run(suite)
        result['suites'][mode]=dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped))
        assert r.wasSuccessful() and r.testsRun==17 and not r.skipped
    for name,tests,expected in [('cache_mechanics','research_v77.check_mechanics.Checks',9),('cache_parser',__name__+'.Checks',8)]:
        r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(tests))
        result['suites'][name]=dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped))
        assert r.wasSuccessful() and r.testsRun==expected and not r.skipped
    result.update(profiles=profile(),codec_manifest=codec.codec_manifest(),elapsed_ns=time.perf_counter_ns()-start)
    from pathlib import Path
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(suites=result['suites'],profiles=[dict(shape=r['shape'],speedup=r['speedup']) for r in result['profiles']])))

if __name__=='__main__':main(sys.argv[1])
