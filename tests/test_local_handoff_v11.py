"""Software checks for metadata-only handoff tooling. No empirical model runs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_handoff', ROOT / 'scripts/local_handoff.py')
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


class LocalHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'work'
        with patch.object(handoff, 'capture_runtime_contract', return_value={'fixture': True}):
            handoff.initialize(self.workspace)

    def test_preserves_budget_and_does_not_authorize(self):
        program = json.loads((self.workspace / 'checklist.json').read_text())
        self.assertEqual(program['inherited_budget']['remaining_cpu_seconds'], 10186)
        self.assertFalse(program['runnable_protocol'])
        self.assertEqual(len(program['cells']), 40)
        self.assertFalse((self.workspace / 'protocol.json').exists())

    def test_refuses_existing_workspace(self):
        with self.assertRaises(ValueError):
            handoff.initialize(self.workspace)

    def test_default_bundle_hashes(self):
        output = self.root / 'result.zip'
        handoff.pack(self.workspace, output)
        with zipfile.ZipFile(output) as z:
            manifest = json.loads(z.read('bundle-manifest.json'))
            self.assertFalse(manifest['scientific_validation_performed'])
            for name, row in manifest['files'].items():
                self.assertEqual(handoff.sha(z.read(name)), row['sha256'])
        with self.assertRaises(ValueError):
            handoff.pack(self.workspace, output)

    def test_rejects_external_and_symlink_files(self):
        external = self.root / 'outside.json'
        external.write_text('{}')
        for candidate in [external, self.workspace / 'link.json']:
            if candidate.name == 'link.json':
                candidate.symlink_to(external)
            with self.assertRaises(ValueError):
                handoff.pack(self.workspace, self.root / 'bad.zip', [candidate])
        self.assertFalse((self.root / 'bad.zip').exists())

    def test_rejects_input_filenames(self):
        candidate = self.workspace / 'token-records.json'
        candidate.write_text('{}')
        with self.assertRaises(ValueError):
            handoff.pack(self.workspace, self.root / 'bad.zip', [candidate])

    def test_missing_planned_cell_rejected(self):
        path = self.workspace / 'checklist.json'
        program = json.loads(path.read_text())
        program['cells'].pop()
        path.write_text(json.dumps(program))
        with self.assertRaises(ValueError):
            handoff.pack(self.workspace, self.root / 'bad.zip')

    def test_extra_evidence_and_size_cap(self):
        candidate = self.workspace / 'receipt.json'
        candidate.write_text('{"complete":false}')
        output = self.root / 'good.zip'
        handoff.pack(self.workspace, output, [candidate])
        with zipfile.ZipFile(output) as archive:
            self.assertIn('receipt.json', archive.namelist())
        with patch.object(handoff, 'MAX_FILE_BYTES', 1):
            with self.assertRaises(ValueError):
                handoff.pack(self.workspace, self.root / 'too-large.zip')


if __name__ == '__main__':
    unittest.main()
