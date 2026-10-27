"""Reproduce inherited reader failures with generated files; exercise real fix."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from research_v112 import audit_inputs
from research_v83.terminal import Inputs as MetadataInputs
from research_v80.io import info

class BinaryAuditInputs(unittest.TestCase):
    def test_non_utf8_model_fails_old_reader_and_passes_actual_binary_reader(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();path=root/'model.bin';blob=b'\xff\x80\x00\xfe';path.write_bytes(blob)
            with patch('research_v83.terminal.BASE',root),self.assertRaises(UnicodeDecodeError):MetadataInputs().read(path)
            with patch.object(audit_inputs,'ROOT',root):
                reader=audit_inputs.Inputs();self.assertEqual(reader.read(path),blob);self.assertEqual(reader.files[str(path)],info(blob));reader.unchanged()
    def test_actual_state_larger_than_metadata_limit_passes_under_original_artifact_cap(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();path=root/'state.bin';size=64*2**20+1
            with path.open('wb') as f:f.truncate(size)
            with patch('research_v83.terminal.BASE',root),self.assertRaisesRegex(ValueError,'extent'):MetadataInputs().read(path)
            with patch.object(audit_inputs,'ROOT',root):
                reader=audit_inputs.Inputs();blob=reader.read(path);self.assertEqual(len(blob),size);self.assertEqual(reader.files[str(path)],info(blob));del blob;reader.unchanged()
                with self.assertRaises(ValueError):reader.json(path)
    def test_original_artifact_bound_and_changed_input_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();path=root/'state.bin';path.write_bytes(b'binary')
            with patch.object(audit_inputs,'ROOT',root):
                reader=audit_inputs.Inputs();reader.read(path)
                with self.assertRaises(ValueError):reader.read(path,expected=info(b'wrong'))
                with self.assertRaises(ValueError):reader.read(path,maximum=2**30+1)
                path.write_bytes(b'changed')
                with self.assertRaises(ValueError):reader.unchanged()
    def test_symbolic_and_outside_project_inputs_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();inside=root/'inside';inside.mkdir();path=root/'outside.bin';path.write_bytes(b'x');link=inside/'link';link.symlink_to(path)
            with patch.object(audit_inputs,'ROOT',inside):
                for p in (path,link):
                    with self.assertRaises(ValueError):audit_inputs.Inputs().read(p)
