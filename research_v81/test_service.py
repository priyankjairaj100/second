"""Constructor and archive dispatch guards; no empirical checkpoint loaded."""
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from research_v81 import service

class Guards(unittest.TestCase):
    def test_default_gpt2_grid_refuses_before_checkpoint_access(self):
        with patch.object(service,'load_gpt2_checkpoint') as load:
            with self.assertRaisesRegex(ValueError,'grid guard'):
                service.MatchedService('/unused','gpt2',{str(i):{} for i in range(4)})
            load.assert_not_called()
    def test_approved_grid_does_not_bypass_checkpoint_identity(self):
        loaded=SimpleNamespace(provenance={'files_sha256':{'wrong':'0'*64}})
        with patch.object(service,'load_gpt2_checkpoint',return_value=loaded),patch.object(service,'OrderedFiniteDecoder') as decode:
            with self.assertRaisesRegex(ValueError,'checkpoint bytes'):
                service.MatchedService('/unused','gpt2',{str(i):{} for i in range(4)},allow_proposed_grid_cap=True)
            decode.assert_not_called()
    def test_modern_serialization_uses_distinct_archive_and_records_time(self):
        s=object.__new__(service.MatchedService);s.bound=object();s.records=lambda r:tuple(r)
        timing={'serialization_ns':0}
        with patch.object(service.archive,'pack',return_value=b'new-archive') as pack:
            self.assertEqual(s.serialize(['r'],['c'],'modern_lossless',{'s':b'p'},{},{},timing),b'new-archive')
            pack.assert_called_once_with(s.bound,('r',),['c'],{'s':b'p'})
        self.assertGreater(timing['serialization_ns'],0)
    def test_legacy_repair_entry_refuses(self):
        s=object.__new__(service.MatchedService)
        with self.assertRaisesRegex(RuntimeError,'V81 operations.request'):s.repair()

if __name__=='__main__':unittest.main()
