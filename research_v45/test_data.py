import copy
import gzip
import unittest
from research_v45.data import Exclusions, choose, decode_prefix, POLICY
from src.run_store import canonical_json, digest

def row(i):
    return dict(id=f'c4:en:shard1:line{i}',tokens=[i+100]*128,
        body_sha256=digest(f'body{i}'.encode()),normalized_text_sha256=digest(f'normal{i}'.encode()),
        url_sha256=digest(f'url{i}'.encode()))

class SelectionTests(unittest.TestCase):
    def test_order_is_input_order_invariant_and_excludes_every_identity_type(self):
        rows=[row(i) for i in range(24)];ex=Exclusions();ex.add(rows[0])
        rows[1]['id']=rows[0]['id'];rows[2]['normalized_text_sha256']=rows[0]['normalized_text_sha256']
        rows[3]['body_sha256']=rows[0]['body_sha256'];rows[4]['url_sha256']=rows[0]['url_sha256']
        rows[5]['tokens'][:16]=rows[0]['tokens'][:16]
        a=choose(rows,copy.deepcopy(ex));b=choose(list(reversed(rows)),copy.deepcopy(ex))
        self.assertEqual(a,b);self.assertEqual(len(a),13)
        self.assertTrue(all(r not in a for r in rows[:6]))
    def test_does_not_fill_with_duplicate_documents(self):
        rows=[row(i) for i in range(13)];rows[-1]['url_sha256']=rows[0]['url_sha256']
        with self.assertRaisesRegex(ValueError,'Insufficient'):choose(rows,Exclusions())
    def test_archived_nested_tokens_and_identifiers_are_protected(self):
        ex=Exclusions();r=row(1);ex.visit({'records':[r]})
        self.assertFalse(ex.disjoint(r));other=row(2);other['tokens'][:32]=r['tokens'][:32]
        self.assertFalse(ex.disjoint(other))
    def test_prefix_ignores_partial_last_record(self):
        raw=b'{"text":"first","url":"x"}\n{"text":"partial'
        self.assertEqual(decode_prefix(gzip.compress(raw)),[dict(text='first',url='x')])
    def test_rejects_invalid_complete_record(self):
        with self.assertRaises(ValueError):decode_prefix(gzip.compress(b'{"text":1,"url":"x"}\n'))

class AdmissionTests(unittest.TestCase):
    def test_data_budget_matches_shared_exact_command_verifier(self):
        import os, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from research_v45 import data_phase
        from src.transaction_timing import verify_command_admission
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'program.json').write_bytes(canonical_json({'fixture':True}))
            p=dict(directory=str(root));command=['python','-B','-m','research_v45.data_phase','worker',str(root)]
            with patch.object(data_phase,'source_hashes',return_value={'fixture.py':'1'*64}), patch('src.experiment_inventory.source_hashes',return_value={'fixture.py':'1'*64}):
                b=data_phase.budget(p);b.reserve('data','attempt',10)
                admission=dict(phase_budget_root=str(b.root),phase_budget_binding_sha256=b.identity_digest,
                    attempt_id='attempt',phase='data',command=command,cwd=str(data_phase.ROOT))
                with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(admission).decode()):
                    result=verify_command_admission(data_phase.sha(root/'program.json'),'data',command)
                    self.assertEqual(result['attempt_id'],'attempt')
                    with self.assertRaises(ValueError):verify_command_admission(data_phase.sha(root/'program.json'),'data',command+['extra'])
