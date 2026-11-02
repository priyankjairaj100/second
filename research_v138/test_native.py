"""Pinned Linux real decoder and acceptance API; generated cases only."""
import tempfile
import unittest
from pathlib import Path
from research_v59.test_anchor import RECORDS
from research_v79.test_integration import service
from research_v112.policy import execution
from research_v135 import source_state
from research_v138.transaction import reconstruct, repair, publish

class Native(unittest.TestCase):
    def test_real_service_repair_fresh_equality_and_all_abort_points(self):
        with tempfile.TemporaryDirectory() as td, execution('optimized_modern'):
            d=Path(td);s=service();records=s.records(sorted(RECORDS,key=lambda r:r['id']))
            c,_=reconstruct(s,records);blob=source_state.pack(s.bound,records,c)
            old={'state.bin':blob,'model.bin':b''.join(x.packed_indices for x in c),'trust.json':b'{}'}
            publish(d/'old',old);snapshot={f.name:f.read_bytes() for f in (d/'old').iterdir()}
            ids=(records[-1].record_id,)
            for point in ('after_proposal','during_replay','before_seal','before_publish'):
                def hook(phase):
                    if phase==point:raise RuntimeError('actual '+point)
                with self.assertRaisesRegex(RuntimeError,'actual'):
                    repair(s,blob,ids,d/point,hook=hook)
                self.assertFalse((d/point).exists())
                self.assertEqual(snapshot,{f.name:f.read_bytes() for f in (d/'old').iterdir()})
            r=repair(s,blob,ids,d/'new')
            fresh,t=reconstruct(s,records[-1:])
            self.assertEqual((d/'new/state.bin').read_bytes(),source_state.pack(s.bound,records[-1:],fresh))
            self.assertEqual((d/'new/model.bin').read_bytes(),b''.join(x.packed_indices for x in fresh))
            self.assertEqual(r['timing']['neural_stage_record_pairs'],len(s.bound.stages))
            self.assertTrue(all(x['route']=='token' for x in r['timing']['stages']))

if __name__=='__main__':unittest.main()
