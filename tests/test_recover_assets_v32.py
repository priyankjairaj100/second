"""Restart helper safety fixtures. No network or empirical inference is used."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import recover_assets_v32 as recovery


class AssetRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root_patch = patch.object(recovery, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.data = {'config.json': b'config fixture', 'model.safetensors': b'weights fixture'}
        fixture = {name: (hashlib.sha256(raw).hexdigest(), len(raw)) for name, raw in self.data.items()}
        self.asset_patch = patch.object(recovery, 'CHECKPOINT', fixture)
        self.asset_patch.start()
        self.addCleanup(self.asset_patch.stop)

    def prepare(self):
        directory = self.root / 'tmp/models/distilgpt2'
        directory.mkdir(parents=True)
        for name, raw in self.data.items():
            (directory / name).write_bytes(raw)
        return directory

    def test_mismatched_existing_asset_is_preserved_without_network(self):
        directory = self.prepare()
        path = directory / 'config.json'
        path.write_bytes(b'keep this mismatch')
        with patch.object(recovery, 'urlopen') as network:
            with self.assertRaisesRegex(ValueError, 'existing checkpoint differs'):
                recovery.restore_checkpoint()
            network.assert_not_called()
        self.assertEqual(path.read_bytes(), b'keep this mismatch')

    def test_matching_existing_assets_are_not_downloaded_or_rewritten(self):
        directory = self.prepare()
        before = {p.name: p.stat().st_mtime_ns for p in directory.iterdir()}
        with patch.object(recovery, 'urlopen') as network:
            result = recovery.restore_checkpoint()
            network.assert_not_called()
        self.assertEqual([row['status'] for row in result], ['already_verified', 'already_verified'])
        self.assertEqual(before, {p.name: p.stat().st_mtime_ns for p in directory.iterdir()})

    def test_checkpoint_only_success_does_not_audit_missing_history(self):
        self.prepare()
        output = io.StringIO()
        with patch.object(recovery, 'asset_inventory', side_effect=AssertionError('historical audit invoked')):
            with patch('sys.argv', ['recover_assets_v32.py', '--checkpoint-only']), redirect_stdout(output):
                self.assertEqual(recovery.main(), 0)
        report = json.loads(output.getvalue())
        self.assertTrue(report['checkpoint_verified'])
        self.assertFalse(report['historical_assets_audited'])
        self.assertFalse(report['controller_ready'])
        self.assertNotIn('all_listed_assets_verified', report)

    def test_checkpoint_only_missing_input_fails(self):
        report = recovery.checkpoint_inventory()
        self.assertFalse(report['checkpoint_verified'])
        self.assertEqual([row['status'] for row in report['checkpoint_assets']], ['missing', 'missing'])

    def test_relocation_maps_archived_paths_without_modifying_them(self):
        archived = recovery.ARCHIVED_ROOT / 'tmp/models/distilgpt2/config.json'
        expected = self.root / 'tmp/models/distilgpt2/config.json'
        self.assertEqual(recovery.local_path(archived), expected)
        self.assertEqual(recovery.local_path(expected), expected)
        self.assertEqual(recovery.local_path('tmp/models/distilgpt2/config.json'), expected)
        with self.assertRaisesRegex(ValueError, 'outside the archived repository'):
            recovery.local_path('/unrelated/config.json')
        with self.assertRaisesRegex(ValueError, 'parent traversal'):
            recovery.local_path('../config.json')


if __name__ == '__main__':
    unittest.main()
