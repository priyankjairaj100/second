"""Synthetic boundary fixtures. No empirical inputs or neural execution."""
import copy
import struct
import unittest
from dataclasses import replace
from unittest.mock import patch
import numpy as np
import zstandard as zstd
from research_v61.test_target import bind,fixture
from src.compact_state import StageCodes
from research_v61 import state as old
from src import fixed_lossless_codec_v29 as prior
from src.run_store import canonical_json
from . import codec,archive

KW=dict(target_sha256='1'*64,anchor_target_sha256='2'*64,record_id='a',token_sha256='3'*64,stage_id='s')


def record(name,tokens):
    return old.Record(name,tuple(tokens),canonical_json(dict(dataset_id='fixture',dataset_revision='fixture',
        source_file_sha256='1'*64,body_sha256=old.sha(name.encode()),tokenizer_sha256='2'*64)))


def codes(target):
    return tuple(StageCodes.from_array(s.stage_id,np.zeros((s.rows,s.width)),grid_axis='dyadic_row',bits=4,
                                      scale_values=(1.,)*s.rows) for s in target.stages)


def features(stage,source):
    return np.array([[(t+j+stage.index)%7/8 for j in range(stage.width)] for t in source.tokens],dtype=np.float64)


def edited(blob,fn):
    n=struct.unpack_from('<Q',blob,8)[0];h=old._object(blob[16:16+n]);fn(h);raw=canonical_json(h)
    return blob[:8]+struct.pack('<Q',len(raw))+raw+blob[16+n:]


class CodecTests(unittest.TestCase):
    def test_exact_signed_zero_subnormal_and_extreme_words(self):
        raw=struct.pack('<QQQQQQ',0,1<<63,1,(1<<63)|1,0x7fefffffffffffff,0xffefffffffffffff)
        a=np.frombuffer(raw,dtype='<f8').reshape(2,3);d=codec.encode_factor(a,**KW)
        self.assertEqual(codec.parse(codec.serialize(d)).binary64(),raw)
    def test_all_five_modes_decode_exactly(self):
        raw=np.arange(128,dtype=np.float64).tobytes()
        values=(raw,codec._compress(raw),codec._compress(codec._shuffle(raw)),codec._zstd(raw),codec._zstd(codec._shuffle(raw)))
        for mode,payload in enumerate(values):self.assertEqual(codec._decode(payload,mode,len(raw)),raw)
    def test_canonical_choice_records_every_mode_and_is_deterministic(self):
        a=np.zeros((8,8));m=[];d=codec.encode_factor(a,**KW,measurements=m)
        self.assertEqual([x['mode'] for x in m],list(codec.MODES))
        self.assertEqual(codec.serialize(d),codec.serialize(codec.encode_factor(a.copy(),**KW)))
        self.assertEqual(d.mode,min(m,key=lambda x:(x['payload_bytes']+len(str(x['payload_bytes'])),x['mode']))['mode'])
    def test_trailing_extra_frame_truncation_and_checksum_refuse(self):
        raw=np.arange(64,dtype=np.float64).tobytes();frame=codec._zstd(raw)
        for bad in (frame+b'x',frame+frame,frame[:-1],frame[:-1]+bytes([frame[-1]^1])):
            with self.subTest(length=len(bad)),self.assertRaises(ValueError):codec._decode(bad,3,len(raw))
    def test_content_size_checksum_and_skippable_requirements(self):
        raw=np.arange(64,dtype=np.float64).tobytes()
        for bad in (zstd.ZstdCompressor(write_content_size=False,write_checksum=True).compress(raw),
                    zstd.ZstdCompressor(write_checksum=False).compress(raw),b'\x50\x2a\x4d\x18'+b'\0'*8):
            with self.assertRaises(ValueError):codec._decode(bad,3,len(raw))
        with self.assertRaises(ValueError):codec._decode(codec._zstd(raw),3,len(raw)-8)
    def test_window_and_dictionary_rejected_before_decompression(self):
        raw=np.zeros((2,2)).tobytes();frame=codec._zstd(raw)
        class Parameters:content_size=len(raw);dict_id=0;has_checksum=True;window_size=codec.MAX_DECODED_BYTES+1
        with patch.object(codec.zstd,'get_frame_parameters',return_value=Parameters()),patch.object(codec.zstd,'ZstdDecompressor',side_effect=AssertionError('allocated')):
            with self.assertRaises(ValueError):codec._decode(frame,3,len(raw))
        Parameters.window_size=len(raw);Parameters.dict_id=1
        with patch.object(codec.zstd,'get_frame_parameters',return_value=Parameters()),patch.object(codec.zstd,'ZstdDecompressor',side_effect=AssertionError('allocated')):
            with self.assertRaises(ValueError):codec._decode(frame,3,len(raw))
    def test_extent_nonfinite_unknown_mode_and_limits_refuse(self):
        with self.assertRaises(ValueError):codec._decode(b'',0,codec.MAX_DECODED_BYTES+1)
        with self.assertRaises(ValueError):codec._decode(struct.pack('<d',float('inf')),0,8)
        with self.assertRaises(ValueError):codec._decode(b'\0'*8,99,8)
        b=codec.serialize(codec.encode_factor(np.zeros((2,3)),**KW))
        with self.assertRaises(ValueError):codec.parse(b,limits=codec.LoadLimits(max_values=5))
    def test_changed_hash_runtime_shape_and_noncanonical_mode_refuse(self):
        d=codec.encode_factor(np.zeros((4,4)),**KW);b=codec.serialize(d)
        for key,val in [('source_sha256','0'*64),('codec_sha256','0'*64),('shape',[True,16]),('mode',True)]:
            with self.assertRaises(ValueError):codec.parse(edited(b,lambda h:h.update({key:val})))
        with self.assertRaises(ValueError):replace(d,mode=0,payload=np.zeros((4,4)).tobytes())
    def test_actual_largest_registered_shape_zstd_roundtrip(self):
        raw=np.arange(128*3072,dtype=np.float64).tobytes()
        frame=codec._zstd(raw)
        self.assertEqual(codec._decode(frame,3,len(raw)),raw)
    def test_old_and_new_magic_are_distinct(self):
        a=np.zeros((2,2));new=codec.serialize(codec.encode_factor(a,**KW));oldb=prior.serialize(prior.encode_factor(a,**KW))
        with self.assertRaises(ValueError):prior.parse(new)
        with self.assertRaises(ValueError):codec.parse(oldb)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.target=bind(*fixture(((2,3),(1,2)),original=8));self.records=(record('a',(1,2)),record('b',(3,4)))
        self.codes=codes(self.target);self.sources={};self.old_sources={}
        for s in self.target.stages:
            for r in self.records:
                kw=dict(target_sha256=old.sha(self.target.fixed_payload),anchor_target_sha256=old.sha(self.target.anchor_payload),record_id=r.record_id,token_sha256=r.token_sha256,stage_id=s.stage_id)
                self.sources[s.stage_id,r.record_id]=codec.serialize(codec.encode_factor(features(s,r),**kw))
                self.old_sources[s.stage_id,r.record_id]=prior.serialize(prior.encode_factor(features(s,r),**kw))
        self.blob=archive.pack(self.target,self.records,self.codes,self.sources)
    def test_roundtrip_restores_actual_old_state(self):
        before=old.build_state(self.target,self.records,self.codes,'lossless',source_payloads=self.old_sources)
        self.assertEqual(archive.restore(archive.unpack(self.blob)),before)
        with self.assertRaises(ValueError):old.validate_state(self.blob)
    def test_transition_equals_fresh_and_retains_descriptor_bytes(self):
        v=archive.unpack(self.blob);r=self.records[:1];kept={(s,x):b for (s,x),b in self.sources.items() if x=='a'}
        repaired=archive.transition(v,r,self.codes);fresh=archive.pack(self.target,r,self.codes,kept)
        self.assertEqual(repaired,fresh);self.assertEqual(archive.unpack(repaired).source_map(),kept)
    def test_non_subset_and_missing_extra_sources_refuse(self):
        with self.assertRaises(ValueError):archive.transition(archive.unpack(self.blob),(record('c',(1,2)),),self.codes)
        missing=dict(self.sources);missing.pop(next(iter(missing)))
        with self.assertRaises(ValueError):archive.pack(self.target,self.records,self.codes,missing)
        with self.assertRaises(ValueError):archive.pack(self.target,self.records,self.codes,dict(self.sources,extra=b'x'))
    def test_source_binding_and_stage_grids_refuse(self):
        changed=dict(self.sources);key=next(iter(changed));changed[key]=edited(changed[key],lambda h:h.update(record_id='wrong'))
        with self.assertRaises(ValueError):archive.pack(self.target,self.records,self.codes,changed)
        bad=list(self.codes);bad[0]=replace(bad[0],scale_values=(2.,)*bad[0].rows)
        with self.assertRaises(ValueError):archive.pack(self.target,self.records,bad,self.sources)
    def test_trailing_changed_payload_and_header_bound_refuse(self):
        for b in (self.blob+b'x',self.blob[:-1],self.blob[:8]+struct.pack('<Q',archive.MAX_HEADER+1)+self.blob[16:]):
            with self.assertRaises(ValueError):archive.unpack(b)
    def test_duplicate_or_reordered_records_refuse(self):
        with self.assertRaises(ValueError):archive.unpack(edited(self.blob,lambda h:h['records'].reverse()))
        with self.assertRaises(ValueError):archive.unpack(edited(self.blob,lambda h:h['records'].__setitem__(1,copy.deepcopy(h['records'][0]))))
    def test_codec_binding_and_reference_target_cannot_be_relabelled(self):
        with self.assertRaises(ValueError):archive.unpack(edited(self.blob,lambda h:h.update(codec_sha256='0'*64)))
        with self.assertRaises(ValueError):archive.unpack(edited(self.blob,lambda h:h.update(schema='complete-full-precision-anchor-successor-v61')))


if __name__=='__main__':unittest.main()
