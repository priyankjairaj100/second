"""Actual temporary file integrity tests for the terminal reporting reader."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from research_v83 import terminal
class InputIntegrity(unittest.TestCase):
    def test_actual_bytes_inventory_and_later_mutation_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p=root/'receipt.json';p.write_bytes(b'{"value":1}')
            with patch.object(terminal,'BASE',root):
                x=terminal.Inputs();self.assertEqual(x.json(p),{'value':1});x.unchanged()
                p.write_bytes(b'{"value":2}')
                with self.assertRaises(ValueError):x.unchanged()
    def test_symlink_outside_root_and_duplicate_json_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p=root/'receipt.json';p.write_bytes(b'{"value":1,"value":2}');(root/'link').symlink_to(p)
            with patch.object(terminal,'BASE',root):
                x=terminal.Inputs()
                for path in (p,root/'link',root.parent/'missing'):
                    with self.assertRaises(ValueError):x.json(path)
if __name__=='__main__':unittest.main()
