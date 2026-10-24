"""Pure source-selection and transport-bound tests; no model/network access."""
import hashlib,io,tempfile,unittest
from pathlib import Path
from research_v82.selection import select
from research_v82.fetch import receive,valid_url,EXPECTED
class Inputs(unittest.TestCase):
    def test_selection_is_fixed_matched_and_endpoint_nested(self):
        rows=[dict(id=f'row{i:02}',tokens=[i]*128) for i in range(13)];prov={r['id']:{'index':i} for i,r in enumerate(rows)}
        a,p,s=select(rows,prov);b,q,t=select(rows,prov)
        self.assertEqual((a,p,s),(b,q,t));self.assertEqual(len(a),4)
        self.assertEqual(s['retained_ids'],[[r['id'] for r in a[-n:]] for n in (3,2)])
        self.assertFalse(s['confirmation']);self.assertEqual(len(s['excluded_from_this_workload']),9)
    def test_bad_root_order_membership_and_tokens_refuse(self):
        rows=[dict(id=f'row{i:02}',tokens=[i]*128) for i in range(13)];prov={r['id']:{} for r in rows}
        for bad in (rows[:-1],list(reversed(rows)),rows[:-1]+[rows[0]],rows[:-1]+[dict(id='row12',tokens=[True]*128)]):
            with self.assertRaises(ValueError):select(bad,prov)
        with self.assertRaises(ValueError):select(rows,{})
    def test_public_https_host_boundary(self):
        for url in ('https://huggingface.co/a','https://cas-bridge.xethub.hf.co/a','https://cdn-lfs.huggingface.co/a'):self.assertTrue(valid_url(url))
        for url in ('http://huggingface.co/a','https://huggingface.co.evil.test/a','https://u:p@huggingface.co/a','https://huggingface.co:4433/a','file:///tmp/x'):self.assertFalse(valid_url(url))
    def test_exact_stream_and_consumed_destination(self):
        b=b'bounded artifact';e=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve()/'file';self.assertEqual(receive(io.BytesIO(b),p,e,deadline=10,clock=lambda:0),e)
            with self.assertRaises(FileExistsError):receive(io.BytesIO(b),p,e,deadline=10,clock=lambda:0)
            self.assertEqual(p.read_bytes(),b)
    def test_wrong_hash_truncation_and_overflow_preserve_failure_files(self):
        b=b'abcd';e=dict(bytes=4,sha256=hashlib.sha256(b).hexdigest())
        with tempfile.TemporaryDirectory() as d:
            for i,bad in enumerate((b'abc',b'abce',b'abcde')):
                p=Path(d).resolve()/str(i)
                with self.assertRaises(ValueError):receive(io.BytesIO(bad),p,e,deadline=10,clock=lambda:0)
                self.assertTrue(p.exists());self.assertLessEqual(p.stat().st_size,4)
    def test_deadline_and_symbolic_destination_refuse(self):
        e=dict(bytes=4,sha256=hashlib.sha256(b'abcd').hexdigest())
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve()/'late'
            with self.assertRaises(TimeoutError):receive(io.BytesIO(b'abcd'),p,e,deadline=10,clock=lambda:11)
            self.assertTrue(p.exists())
            q=Path(d).resolve()/'link';q.symlink_to(p)
            with self.assertRaises(ValueError):receive(io.BytesIO(b'abcd'),q,e,deadline=10,clock=lambda:0)
    def test_config_bytes_match_exact_fetch_commitment(self):
        b=Path(__file__).resolve().parents[1].joinpath('research_v81/gpt2-config.json').read_bytes()
        self.assertEqual(EXPECTED['config.json'],dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
if __name__=='__main__':unittest.main()
