"""Metadata export fixtures, with failed records and dummy nontext artifacts."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import export_local_evidence_v32 as exporter


class ExportTests(unittest.TestCase):
    def fixtures(self,root):
        workspace=root/'local_runs/replay-001';campaign=workspace/'independent_wikitext_v32'
        (campaign/'attempts/failed/outputs').mkdir(parents=True)
        (campaign/'source/src').mkdir(parents=True)
        (campaign/'phase-cpu-budget').mkdir()
        files={'program.json':b'{"path":"/original/bound/path"}',
            'attempts/failed/outputs/progress.json':b'{"status":"failed"}',
            'source/src/numerics.py':b'x = 1\n',
            'phase-cpu-budget/ledger.json':b'{"reserved_unknown_attempts":1}'}
        for name,raw in files.items():(campaign/name).write_bytes(raw)
        (campaign/'attempts/failed/outputs/model.bin').write_bytes(b'\0binary')
        return workspace,campaign,files

    def test_inventory_is_read_only_and_keeps_failed_and_held_records(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(exporter,'ROOT',Path(tmp)):
            workspace,campaign,files=self.fixtures(Path(tmp))
            result=exporter.snapshot('local_runs/replay-001')
            self.assertFalse(result['exported']);self.assertFalse((Path(tmp)/'archives').exists())
            manifest=result['inventory'];self.assertEqual(manifest['files_count'],4)
            self.assertFalse(manifest['outcome_filter_applied']);self.assertFalse(manifest['runnable'])
            self.assertEqual(len(manifest['omitted_files']),1)
            names=[r['original_workspace_relative'] for r in manifest['files']]
            self.assertTrue(any('failed' in name for name in names))
            self.assertTrue(any('ledger' in name for name in names))

    def test_export_copies_bytes_and_paths_without_moving_live_campaign(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(exporter,'ROOT',Path(tmp)):
            workspace,campaign,files=self.fixtures(Path(tmp))
            result=exporter.snapshot('local_runs/replay-001','archives/local-checkpoint-001')
            self.assertTrue(result['exported']);destination=Path(result['destination'])
            manifest=json.loads((destination/'EXPORT_MANIFEST.json').read_bytes())
            for entry in manifest['files']:
                original=Path(tmp)/entry['original_repository_relative'];copied=destination/entry['archive_relative']
                self.assertEqual(copied.read_bytes(),original.read_bytes())
                self.assertEqual(hashlib.sha256(copied.read_bytes()).hexdigest(),entry['sha256'])
            self.assertIn(b'/original/bound/path',(destination/'files/independent_wikitext_v32/program.json').read_bytes())
            self.assertTrue((campaign/'attempts/failed/outputs/model.bin').exists())
            self.assertFalse(list(destination.rglob('*.bin')))
            with self.assertRaisesRegex(ValueError,'never overwritten'):
                exporter.snapshot('local_runs/replay-001','archives/local-checkpoint-001')

    def test_workspace_and_destination_are_narrowly_scoped(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(exporter,'ROOT',Path(tmp)):
            for source in ('campaigns/x','/tmp/x','local_runs','local_runs/../x'):
                with self.assertRaises(ValueError):exporter.relative_path(source,'workspace')
            for output in ('campaigns/x','archives/not-local','archives/local-x/nested','../archives/local-x'):
                with self.assertRaises(ValueError):exporter.relative_path(output,'output')

    def test_symlink_evidence_is_rejected_even_for_excluded_binary(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(exporter,'ROOT',Path(tmp)):
            workspace,campaign,files=self.fixtures(Path(tmp))
            (campaign/'outside.bin').symlink_to('/etc/hosts')
            with self.assertRaisesRegex(ValueError,'symbolic evidence'):
                exporter.snapshot('local_runs/replay-001','archives/local-checkpoint-001')
            self.assertFalse((Path(tmp)/'archives/local-checkpoint-001').exists())

    def test_invalid_utf8_metadata_is_not_silently_omitted(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(exporter,'ROOT',Path(tmp)):
            workspace,campaign,files=self.fixtures(Path(tmp));(campaign/'bad.json').write_bytes(b'\xff')
            with self.assertRaises(UnicodeDecodeError):exporter.snapshot('local_runs/replay-001')

    def test_both_root_outcomes_and_optional_analyses_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(exporter,'ROOT',Path(tmp)):
            workspace,campaign,files=self.fixtures(Path(tmp))
            other=workspace/'independent_c4_v32';other.mkdir();(other/'program.json').write_text('{}')
            (workspace/'wikitext-analysis.json').write_text('{"speedup":0.8}')
            result=exporter.snapshot('local_runs/replay-001')['inventory']
            self.assertEqual(result['included_roots'],list(exporter.CAMPAIGNS))
            self.assertEqual(result['files_count'],6)


if __name__=='__main__':unittest.main()
