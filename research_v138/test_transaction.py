import tempfile
import unittest
from pathlib import Path
from research_v61.test_service import FixtureService
from research_v59.test_anchor import RECORDS
from research_v135 import source_state as state
from research_v138.transaction import reconstruct, publish, repair


class Transaction(unittest.TestCase):
    def setUp(self):
        self.s = FixtureService(None, 512, {})
        self.rows = sorted(RECORDS, key=lambda r: r['id'])
        self.records = self.s.records(self.rows)
        self.c, _ = reconstruct(self.s, self.records)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_success_with_all_three_artifacts_and_exact_fresh_state(self):
        for mode in ('tokens', 'references'):
            blob = state.pack(self.s.bound, self.records, self.c, mode)
            provider = lambda rid, meta: next(r['tokens'] for r in self.rows if r['id']==rid)
            ids = (self.records[-1].record_id,)
            result = repair(self.s, blob, ids, self.root/mode, provider)
            fresh, _ = reconstruct(self.s, self.records[-1:])
            self.assertEqual((self.root/mode/'state.bin').read_bytes(), state.pack(self.s.bound,self.records[-1:],fresh,mode))
            self.assertEqual(set(result['artifacts']), {'state.bin','model.bin','trust.json'})

    def test_all_four_fault_points_leave_predecessor_and_published_inventory_unchanged(self):
        # Fixture extraction does not emit per-record events; this generated
        # test emits that actual hook explicitly. Linux test uses the real provider.
        original_extract = self.s.extract
        def extract(rows, timing):
            out = original_extract(rows,timing)
            self.s.mark('source_replayed',record_id=rows[0]['id'])
            return out
        self.s.extract = extract
        blob = state.pack(self.s.bound,self.records,self.c)
        before = {'state.bin':blob,'model.bin':b''.join(c.packed_indices for c in self.c),'trust.json':b'{}'}
        publish(self.root/'predecessor',before)
        snapshot = {f.name:f.read_bytes() for f in (self.root/'predecessor').iterdir()}
        for point in ('after_proposal','during_replay','before_seal','before_publish'):
            def hook(phase):
                if phase==point:raise RuntimeError('injected '+point)
            with self.assertRaisesRegex(RuntimeError,'injected'):
                repair(self.s,blob,(self.records[-1].record_id,),self.root/point,hook=hook)
            self.assertFalse((self.root/point).exists())
            self.assertEqual(snapshot,{f.name:f.read_bytes() for f in (self.root/'predecessor').iterdir()})

    def test_missing_retained_reference_refuses_before_reconstruction(self):
        blob=state.pack(self.s.bound,self.records,self.c,'references')
        self.s.extract=lambda *a:self.fail('extraction before source admission')
        with self.assertRaises(PermissionError):repair(self.s,blob,(self.records[-1].record_id,),self.root/'absent')
        self.assertFalse((self.root/'absent').exists())

    def test_corrupt_predecessor_refuses_before_any_source_call(self):
        blob=state.pack(self.s.bound,self.records,self.c,'references')
        with self.assertRaises(ValueError):repair(self.s,blob[:-1],(self.records[-1].record_id,),self.root/'bad',lambda *a:self.fail('source read'))
        self.assertEqual(list(self.root.iterdir()),[])

    def test_publish_refuses_model_mismatch_and_retry(self):
        blob=state.pack(self.s.bound,self.records,self.c)
        good={'state.bin':blob,'model.bin':b''.join(c.packed_indices for c in self.c),'trust.json':b'{}'}
        with self.assertRaises(ValueError):publish(self.root/'bad',dict(good,**{'model.bin':b'x'}))
        self.assertFalse((self.root/'.bad.partial').exists())
        publish(self.root/'good',good)
        with self.assertRaises(ValueError):publish(self.root/'good',good)

    def test_no_deleted_reference_lookup_and_tokens_survive_absence(self):
        rid=self.records[-1].record_id;seen=[]
        def provider(k,meta):
            self.assertEqual(k,rid);seen.append(k);return self.rows[-1]['tokens']
        for mode in ('tokens','references'):
            blob=state.pack(self.s.bound,self.records,self.c,mode)
            repair(self.s,blob,(rid,),self.root/mode,provider)
        self.assertEqual(seen,[rid])

if __name__=='__main__':unittest.main()
