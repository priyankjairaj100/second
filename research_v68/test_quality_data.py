"""Generated synthetic articles and fake networking only; no corpus access."""
import gzip,json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from research_v68 import quality_data as d
from research_v45.data import Exclusions
from src.run_store import canonical_json,digest

class Tokenizer:
    def encode(self,text,add_special_tokens=False):
        assert not add_special_tokens
        return SimpleNamespace(ids=[int(text)+100]*128)


def frame(n=8):
    plaintext=b''.join(canonical_json(dict(text=str(i),url='url'+str(i)))+b'\n' for i in range(n))
    policy=dict(d.POLICY,articles=3,transfer_bytes=4096,decompressed_prefix_bytes=len(plaintext)-8,source_total_bytes=9999999)
    compressed=gzip.compress(plaintext);return compressed+b'\0'*(4096-len(compressed)),policy


def candidates(n=8):return [d.row(i,dict(text=str(i),url='u'+str(i)),Tokenizer()) for i in range(n)]


def save_acquisition(root,raw,p):
    (root/'validation-prefix.gz.part').write_bytes(raw)
    receipt=dict(status='complete',error=None,url=d.url(p),method='GET',automatic_retry=False,
        headers={'Content-Range':f"bytes 0-{len(raw)-1}/{p['source_total_bytes']}",'Content-Length':str(len(raw))},
        received=d.info(raw),whole_source_sha256_is_metadata_only=True,whole_source_sha256_metadata=p['whole_source_sha256_metadata'])
    (root/'acquisition.json').write_bytes(canonical_json(receipt))

class QualityDataTests(unittest.TestCase):
    def test_fixed_decompressed_frame_keeps_only_complete_lines(self):
        raw,p=frame();rows,meta=d.decode_frame(raw,p)
        self.assertEqual(len(rows),7);self.assertEqual(meta['decompressed_prefix']['bytes'],p['decompressed_prefix_bytes'])
        self.assertFalse(meta['whole_gzip_trailer_verified']);self.assertGreater(meta['incomplete_trailing_bytes'],0)
        with self.assertRaises(ValueError):d.decode_frame(raw[:-1],p)
        with self.assertRaises(ValueError):d.decode_frame(raw,dict(p,decompressed_prefix_bytes=99999))

    def test_duplicate_json_keys_empty_lines_and_oversized_text_refuse(self):
        raw,p=frame();length=p['transfer_bytes']
        for text in [b'{"text":"1","text":"2","url":"u"}\n',b'\n',b'{"text":3,"url":"u"}\n']:
            b=gzip.compress(text);data=b+b'\0'*(length-len(b))
            with self.assertRaises(ValueError):d.decode_frame(data,dict(p,decompressed_prefix_bytes=len(text)))
        with self.assertRaises(ValueError):d.decode_frame(raw,dict(p,max_text_characters=0))

    def test_validation_ids_do_not_collide_with_training_shards(self):
        r=candidates()[0];self.assertEqual(r['id'],'c4:en:validation:shard1:line0')
        self.assertNotEqual(r['id'],'c4:en:shard1:line0')

    def test_full_deduplicated_frame_then_fixed_rank(self):
        rows=candidates();p=dict(d.POLICY,articles=3);a=d.select(rows,Exclusions(),p);b=d.select(rows,Exclusions(),p)
        self.assertEqual(a,b);self.assertEqual(a['status'],'complete')
        expected=sorted(rows,key=lambda r:(digest((p['order_seed']+r['id']).encode()),r['id']))
        self.assertEqual(a['chosen'],expected[:3]);self.assertEqual(len(a['candidates']),8)
        self.assertEqual(set(a['exclusions_after']['ids']),{r['id'] for r in rows})
        with self.assertRaises(ValueError):d.select(list(reversed(rows)),Exclusions(),p)

    def test_each_protected_overlap_kind_is_rejected(self):
        rows=candidates(10);e=Exclusions();e.ids.add(rows[0]['id']);e.content.add(rows[1]['body_sha256'])
        e.content.add(rows[2]['normalized_text_sha256']);e.content.add(rows[3]['url_sha256']);e.tokens(rows[4]['tokens'][:16])
        result=d.select(rows,e,dict(d.POLICY,articles=3))
        self.assertFalse({r['id'] for r in result['chosen']}&{r['id'] for r in rows[:5]})
        self.assertTrue(all(not x['eligible'] for x in result['candidates'][:5]))

    def test_excluded_source_content_propagates_to_later_frame_duplicates(self):
        rows=candidates();rows[1]['body_sha256']=rows[0]['body_sha256'];rows[2]['tokens']=rows[3]['tokens']
        e=Exclusions();e.ids.add(rows[0]['id']);result=d.select(rows,e,dict(d.POLICY,articles=3))
        self.assertFalse(result['candidates'][1]['eligible']);self.assertFalse(result['candidates'][3]['eligible'])
        self.assertIn('within_frame_content_or_url_overlap',result['candidates'][1]['exclusion_reasons'])

    def test_underfilled_frame_and_all_exclusions_are_saved_before_refusal(self):
        raw,p=frame(4);p['articles']=9
        with TemporaryDirectory() as f:
            root=Path(f).resolve();save_acquisition(root,raw,p)
            with self.assertRaisesRegex(ValueError,'preserved underfilled'):d.materialize(root,raw,Tokenizer(),Exclusions(),p)
            selection=json.loads((root/'selection.json').read_text());self.assertEqual(selection['status'],'underfilled')
            self.assertEqual(len(json.loads((root/'exclusions-after.json').read_text())['ids']),3)
            with self.assertRaises(ValueError):d.audit_saved(root,Tokenizer(),Exclusions(),p)

    def test_saved_actual_token_and_candidate_inventory_tampering_refuse(self):
        raw,p=frame()
        with TemporaryDirectory() as f:
            root=Path(f).resolve();save_acquisition(root,raw,p);d.materialize(root,raw,Tokenizer(),Exclusions(),p)
            self.assertTrue(d.audit_saved(root,Tokenizer(),Exclusions(),p)['actual_records_equal'])
            target=root/'records.json';original=target.read_bytes();changed=json.loads(original);changed['records'][0]['tokens'][0]+=1;target.write_bytes(canonical_json(changed))
            with self.assertRaisesRegex(ValueError,'Actual selected token'):d.audit_saved(root,Tokenizer(),Exclusions(),p)
            target.write_bytes(original);q=root/'candidate-inventory.json';changed=json.loads(q.read_bytes());changed['candidates'].pop();q.write_bytes(canonical_json(changed))
            with self.assertRaisesRegex(ValueError,'candidate inventory'):d.audit_saved(root,Tokenizer(),Exclusions(),p)

    def test_entire_prior_shard_two_frame_is_excluded_not_only_selected_ids(self):
        old=[dict(text=str(i),url='old'+str(i)) for i in range(2349)]
        compressed=gzip.compress(b''.join(canonical_json(x)+b'\n' for x in old));raw=compressed+b'\0'*(2*2**20-len(compressed))
        after=canonical_json(dict(ids=['c4:en:shard2:line0'],content=[],chunks=[]))
        with patch.object(d,'AFTER_SHA',digest(after)),patch.object(d,'PREFIX_SHA',digest(raw)):
            result=d.protected_from_v65(after,raw,[],Tokenizer())
        self.assertEqual(len(result.ids),2349)
        for i in [1,100,2348]:self.assertFalse(result.disjoint(d.c4_row(i,old[i],2,Tokenizer())))
        with self.assertRaises(ValueError):d.protected_from_v65(after,raw,[],Tokenizer())

    def test_network_overlong_or_short_transfer_is_preserved_and_refused(self):
        raw,p=frame()
        class Response:
            status=206
            headers={'Content-Range':f"bytes 0-4095/{p['source_total_bytes']}",'Content-Length':'4096'}
            def __init__(self,payload):self.payload=payload
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):b=self.payload[:n];self.payload=self.payload[n:];return b
        for payload in [raw+b'x',raw[:-1]]:
            with self.subTest(length=len(payload)),TemporaryDirectory() as f:
                root=Path(f).resolve()
                with patch.object(d,'urlopen',return_value=Response(payload)) as network:
                    with self.assertRaises(ValueError):d.acquire(root,p)
                    self.assertEqual(network.call_count,1)
                self.assertEqual((root/'validation-prefix.gz.part').read_bytes(),payload)
                self.assertEqual(json.loads((root/'acquisition.json').read_text())['status'],'failed')

    def test_wrong_status_reads_no_body_and_one_use_retry_cannot_overwrite(self):
        raw,p=frame()
        class Response:
            status=200;headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):raise AssertionError('Unbounded response body must not be read')
        with TemporaryDirectory() as f:
            root=Path(f).resolve()
            with patch.object(d,'urlopen',return_value=Response()):
                with self.assertRaises(ValueError):d.acquire(root,p)
            original=(root/'acquisition.json').read_bytes()
            with patch.object(d,'urlopen') as network:
                with self.assertRaises(FileExistsError):d.acquire(root,p)
                network.assert_not_called()
            self.assertEqual((root/'acquisition.json').read_bytes(),original)

if __name__=='__main__':unittest.main()
