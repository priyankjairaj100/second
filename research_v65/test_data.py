"""Synthetic selection/admission fixtures; no corpus or network access."""
import gzip
import json
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research_v45.data import Exclusions
from research_v65 import data
from src.run_store import canonical_json,digest


def row(i):
    return dict(id=f'c4:en:shard2:line{i}',tokens=[100+i]*128,
        normalized_text_sha256=digest(('text'+str(i)).encode()),body_sha256=digest(('body'+str(i)).encode()),
        url_sha256=digest(('url'+str(i)).encode()))


class DataTests(unittest.TestCase):
    def test_selection_is_input_order_independent_and_exactly_thirteen(self):
        rows=[row(i) for i in range(30)]
        a=data.choose(rows,Exclusions());b=data.choose(list(reversed(rows)),Exclusions())
        self.assertEqual(a,b);self.assertEqual(len(a),13)
        self.assertEqual(a,sorted(rows,key=lambda x:digest((data.POLICY['order_key']+x['id']).encode()))[:13])

    def test_ids_text_urls_and_token_prefixes_are_all_excluded(self):
        rows=[row(i) for i in range(35)];e=Exclusions()
        e.ids.add(rows[0]['id']);e.content.add(rows[1]['normalized_text_sha256'])
        e.content.add(rows[2]['body_sha256']);e.content.add(rows[3]['url_sha256']);e.tokens(rows[4]['tokens'][:16])
        got=data.choose(rows,e);self.assertFalse({r['id'] for r in got}&{r['id'] for r in rows[:5]})

    def test_candidate_duplicates_cannot_fill_multiple_slots(self):
        rows=[row(i) for i in range(14)];rows[1]['tokens']=rows[0]['tokens']
        got=data.choose(rows,Exclusions());self.assertEqual(len(got),13)
        self.assertEqual(len({digest(canonical_json(x['tokens'])) for x in got}),13)
        with self.assertRaises(ValueError):data.choose(rows+[rows[0]],Exclusions())

    def test_short_records_and_insufficient_frame_fail_without_expansion(self):
        rows=[row(i) for i in range(13)];rows[0]['tokens']=rows[0]['tokens'][:127]
        with self.assertRaises(ValueError):data.choose(rows,Exclusions())

    def test_protected_exclusions_union_every_metadata_record(self):
        a,b=row(0),row(1);e=Exclusions();e.add(a)
        protected={k:sorted(getattr(e,k)) for k in ['ids','content','chunks']}
        result=data.exclusions_from(protected,[dict(records=[b])])
        self.assertFalse(result.disjoint(a));self.assertFalse(result.disjoint(b));self.assertTrue(result.disjoint(row(9)))
        with self.assertRaises(ValueError):data.exclusions_from(dict(protected,extra=[]),[])
        with self.assertRaises(ValueError):data.exclusions_from(dict(protected,chunks=['bad']),[])

    def test_gzip_complete_lines_only_and_text_extent(self):
        raw=b'{"text":"ok","url":"u"}\n{"text":"partial'
        self.assertEqual(data.decode_prefix(gzip.compress(raw)),[dict(text='ok',url='u')])
        for bad in [b'{"text":3,"url":"u"}\n',b'\n']:
            with self.assertRaises(ValueError):data.decode_prefix(gzip.compress(bad))
        with patch.dict(data.POLICY,{'max_decompressed_bytes':4}):
            with self.assertRaises(ValueError):data.decode_prefix(gzip.compress(raw))

    def test_history_census_covers_local_runs_and_excludes_only_current_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            for n in ['campaigns/a/program.json','pilots/a/records.json','local_runs/old/outputs/selection.json',
                      'local_runs/old/worker/plan.json','local_runs/disjoint-data-v65-20261016-a/registration.json',
                      'local_runs/disjoint-data-v65-20261016-a/outputs/records.json']:
                p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
            got=data.history_inventory(root)
            self.assertEqual(set(got),{'campaigns/a/program.json','pilots/a/records.json','local_runs/old/outputs/selection.json'})
            p=root/'campaigns/a/selection.json';p.symlink_to(root/'pilots/a/records.json')
            with self.assertRaises(ValueError):data.history_inventory(root)

    def test_network_range_wrong_status_or_extent_refuses(self):
        class Response:
            status=200;headers={}
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,n):return b'x'*n
        with patch.object(data,'urlopen',return_value=Response()):
            with self.assertRaises(ValueError):data.acquire()
        Response.status=206;Response.headers={'Content-Range':'bytes 1-2097152/9000000'}
        with patch.object(data,'urlopen',return_value=Response()):
            with self.assertRaises(ValueError):data.acquire()
        Response.headers={'Content-Range':'bytes 0-2097151/9000000'}
        with patch.object(data,'urlopen',return_value=Response()):
            with self.assertRaises(ValueError):data.acquire()


    def test_saved_data_audit_reconstructs_tokens_and_refuses_mutation(self):
        class Tokenizer:
            @classmethod
            def from_file(cls,path):return cls()
            def get_vocab_size(self):return 50257
            def encode(self,text,add_special_tokens=False):return SimpleNamespace(ids=[int(text)]*128)
        module=SimpleNamespace(Tokenizer=Tokenizer,__version__='fixture')
        with tempfile.TemporaryDirectory() as folder,patch.dict(sys.modules,{'tokenizers':module}):
            root=Path(folder).resolve();prior=root/'local_runs/c4-data-v45-20261010-a/outputs';prior.mkdir(parents=True)
            def packed(rows):
                raw=gzip.compress(b''.join(canonical_json(x)+b'\n' for x in rows))
                return raw+b'\0'*(data.POLICY['prefix_bytes']-len(raw))
            old=packed([dict(text='1',url='old')]);(prior/'shard-1-prefix.gz.part').write_bytes(old)
            (prior/'exclusions.json').write_bytes(canonical_json(dict(ids=[],content=[],chunks=[])))
            (prior/'selection.json').write_bytes(canonical_json(dict(source_files=dict(new_c4=dict(complete_records=1)))))
            run=root/'local_runs/disjoint-data-v65-20261016-a';run.mkdir()
            plan=dict(tokenizers_version='fixture',history=data.history_inventory(root))
            raw=packed([dict(text=str(i),url=str(i)) for i in range(100,130)])
            source=dict(url=f"https://huggingface.co/datasets/allenai/c4/resolve/{data.POLICY['revision']}/en/c4-train.00002-of-01024.json.gz",content_range='bytes 0-2097151/9000000',**data.info(raw))
            with patch.object(data,'acquire',return_value=(raw,source)):
                result=data.prepare(root,run,plan)
            (run/'data.json').write_bytes(canonical_json(dict(status='complete',result=result)))
            answer=data.audit(root,run,plan)
            self.assertTrue(answer['actual_selected_records_equal'])
            output=run/'outputs/records.json';saved=output.read_bytes();value=json.loads(saved);value['records'][0]['tokens'][0]+=1;output.write_bytes(canonical_json(value))
            with self.assertRaisesRegex(ValueError,'Actual selected token'):data.audit(root,run,plan)
            output.write_bytes(saved)
            protected=run/'outputs/exclusions-before.json';value=json.loads(protected.read_bytes());value['ids']=[];protected.write_bytes(canonical_json(value))
            with self.assertRaisesRegex(ValueError,'protected exclusions'):data.audit(root,run,plan)


if __name__=='__main__':unittest.main()
