"""Prospective full-geometry generated archives; no model inference/calibration.

Packed zero codes and zero factors are artificial. These checks establish only
format extent, exact restoration, source selection and corruption refusal.
"""
import gc,struct,unittest
import numpy as np
from research_v61.test_target import fixture,service_for,bind
from research_v61.test_state import record
from research_v61 import state as old
from research_v63 import codec,archive as old_archive
from research_v81 import archive
from research_v81.profile import SHAPES,KINDS
from src.compact_state import StageCodes
from src.run_store import canonical_json,digest,strict_json

def target(blocks):
    base,_=fixture(SHAPES*blocks,original=512)
    ids=[f'block.{i:04d}.{k}' for i in range(blocks) for k in KINDS]
    base['recipe']['max_grid_entries']=1_327_104
    for i,s in enumerate(base['stages']):s.update(stage_id=ids[i],dependencies=sorted(ids[:i]))
    return bind(base,service_for(base))

def fixture_archive(blocks,records):
    bound=target(blocks);stages=bound.stages;codes=[];payloads={}
    values={w:np.zeros((128,w)) for _,w in SHAPES}
    for s in stages:
        codes.append(StageCodes(s.stage_id,s.rows,s.width,'dyadic_row',4,(),b'\x88'*((s.rows*s.width+1)//2),(1.,)*s.rows))
        for r in records:
            payloads[s.stage_id,r.record_id]=codec.serialize(codec.encode_factor(values[s.width],
                target_sha256=digest(bound.fixed_payload),anchor_target_sha256=digest(bound.anchor_payload),
                record_id=r.record_id,token_sha256=r.token_sha256,stage_id=s.stage_id))
    return bound,tuple(codes),payloads

def edit(blob,change):
    n=struct.unpack_from('<Q',blob,8)[0];h=strict_json(blob[16:16+n]);change(h);b=canonical_json(h)
    return blob[:8]+struct.pack('<Q',len(b))+b+blob[16+n:]

class FullGeometryArchives(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=(record('a',[1]*128),record('b',[2]*128))
        cls.bound,cls.codes,cls.sources=fixture_archive(12,cls.records)
        cls.blob=archive.pack(cls.bound,cls.records,cls.codes,cls.sources)
    @classmethod
    def tearDownClass(cls):
        for name in ('bound','codes','sources','blob'):delattr(cls,name)
        gc.collect()
    def test_48_stage_extent_actual_restoration_and_24_stage_profile(self):
        view=archive.unpack(self.blob)
        self.assertEqual(len(view.stage_codes),48)
        self.assertEqual(sum(s.rows*s.columns for s in view.stage_codes),84934656)
        legacy=old.validate_state(archive.restore(view))
        self.assertEqual(legacy.stage_codes,view.stage_codes);self.assertEqual(legacy.records,self.records)
        b,c,p=fixture_archive(6,self.records[:1]);v=archive.unpack(archive.pack(b,self.records[:1],c,p))
        self.assertEqual(len(v.stage_codes),24)
    def test_retained_transition_equals_independent_pack(self):
        retained=self.records[:1];sources={k:v for k,v in self.sources.items() if k[1]=='a'}
        got=archive.transition(archive.unpack(self.blob),retained,self.codes)
        self.assertEqual(got,archive.pack(self.bound,retained,self.codes,sources))
        self.assertEqual(archive.unpack(got).source_map(),sources)
    def test_wrong_profile_missing_stages_and_malformed_frame_refuse(self):
        bad=[self.blob+b'x',self.blob[:-1],edit(self.blob,lambda h:h.update(profile='distilgpt2')),
             edit(self.blob,lambda h:h['stages'].pop()),edit(self.blob,lambda h:h.update(codec_sha256='0'*64))]
        for b in bad:
            with self.assertRaises(ValueError):archive.unpack(b)
    def test_missing_code_source_or_oversized_source_set_refuses(self):
        with self.assertRaises(ValueError):archive.pack(self.bound,self.records,self.codes[:-1],self.sources)
        missing=dict(self.sources);missing.pop(next(iter(missing)))
        with self.assertRaises(ValueError):archive.pack(self.bound,self.records,self.codes,missing)
        with self.assertRaises(ValueError):archive.pack(self.bound,self.records*3,self.codes,self.sources)
    def test_old_and_new_archive_framing_are_not_interchangeable(self):
        with self.assertRaises(ValueError):old_archive.unpack(self.blob)
        with self.assertRaises(ValueError):archive.unpack(old_archive.MAGIC+self.blob[8:])
        with self.assertRaises(ValueError):old_archive.pack(self.bound,self.records,self.codes,self.sources)

if __name__=='__main__':unittest.main()
