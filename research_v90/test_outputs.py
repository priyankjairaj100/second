"""Pure progress/file-census checks; generated records never model results."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest
from research_v90 import outputs as new, records
from research_v87 import outputs as old


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_full_twenty_worker_census_and_unchanged_byte_limits(self):
        total = 0
        for trial in new.ORDER:
            p, _ = new.trial_parts(trial)
            previous = old.allowance(new.expected_artifacts(trial), new.MODEL_BYTES[p])
            current = new.allowance(trial)
            self.assertEqual(current['artifact_bytes'], previous['artifact_bytes'])
            self.assertEqual(current['completion_bytes'], previous['completion_bytes'])
            self.assertEqual(current['output_bytes']-current['progress_bytes'], previous['output_bytes']-previous['progress_bytes'])
            self.assertEqual(current['progress_bytes'], current['progress_files']*old.PROGRESS_BYTES)
            total += current['progress_files']
        self.assertEqual(total, 1714)
        self.assertEqual(max(new.allowance(t)['progress_files'] for t in new.ORDER), 486)

    def test_unknown_trial_and_phase_refuse(self):
        with self.assertRaises(ValueError): new.progress_limits('gpt2/unregistered')
        out = new.Outputs(self.root/'outputs', 'distilgpt2/reference_modern-1')
        with self.assertRaises(ValueError): out.progress({'phase': 'unknown'})
        self.assertTrue(out.poisoned)
        self.assertEqual(list(out.root.iterdir()), [])

    def test_phase_overflow_retains_every_prior_record(self):
        out = new.Outputs(self.root/'outputs', 'gpt2/reference_modern-1')
        item = {'phase': 'context_ready', 'diagnostic': 'untouched'}
        out.progress(item); saved = (out.root/'progress-0000.json').read_bytes()
        with self.assertRaises(ValueError): out.progress(item)
        self.assertEqual(saved, (out.root/'progress-0000.json').read_bytes())
        self.assertEqual(len(list(out.root.iterdir())), 1)
        with self.assertRaises(ValueError): out.finish({'status': 'complete', 'complete_model': True})
        out.finish({'status': 'failed', 'complete_model': False, 'error': 'phase limit'})
        self.assertEqual(json.loads((out.root/'completion.json').read_bytes())['status'], 'failed')

    def test_full_refusal_diagnostic_is_kept_verbatim(self):
        out = new.Outputs(self.root/'outputs', 'gpt2/reference_compressed-1')
        item = dict(phase='stage_certified', certificate_refusal={'message': 'x'*800000, 'diagnostics': {'negative': True}})
        out.progress(item)
        self.assertEqual(json.loads((out.root/'progress-0000.json').read_bytes()), item)

    def test_existing_byte_overflow_still_fails_without_truncation(self):
        out = new.Outputs(self.root/'outputs', 'gpt2/reference_compressed-1')
        with self.assertRaises(ValueError):
            out.progress(dict(phase='stage_certified', certificate_refusal='x'*old.PROGRESS_BYTES))
        self.assertTrue(out.poisoned)
        self.assertEqual(list(out.root.iterdir()), [])

    def test_complete_census_allows_only_zero_or_full_fallback_replay(self):
        for trial in new.ORDER:
            limits = new.progress_limits(trial)
            new.complete_progress(trial, limits)
            if '_compressed-' in trial:
                new.complete_progress(trial, dict(limits, source_replayed=0))
                with self.assertRaises(ValueError): new.complete_progress(trial, dict(limits, source_replayed=1))
            with self.assertRaises(ValueError): new.complete_progress(trial, dict(limits, context_ready=0))
            with self.assertRaises(ValueError): new.complete_progress(trial, dict(limits, stage_certified=0))

    def test_record_layout_caps_and_collision(self):
        writer = records.Records(self.root, {'entry.json': 20})
        self.assertEqual(writer.allowance()['bytes'], 20)
        with self.assertRaises(ValueError): writer.write('other.json', {})
        with self.assertRaises(ValueError): writer.write('entry.json', {'long': 'x'*20})
        self.assertFalse((self.root/'entry.json').exists())
        writer.write('entry.json', {'ok': True})
        with self.assertRaises(ValueError): writer.write('entry.json', {})
        fresh = records.Records(self.root, {'entry.json': 20})
        with self.assertRaises(FileExistsError): fresh.write('entry.json', {})
        self.assertEqual(json.loads((self.root/'entry.json').read_bytes()), {'ok': True})

    def test_record_partial_failure_is_retained_and_consumed(self):
        writer = records.Records(self.root, {'entry.json': 1024})
        original = records.os.write
        calls = 0
        def fail(fd, data):
            nonlocal calls
            calls += 1
            if calls == 1: return original(fd, data[:3])
            raise OSError('fixture disk full')
        with patch.object(records.os, 'write', side_effect=fail):
            with self.assertRaises(OSError): writer.write('entry.json', {'payload': 'complete value'})
        partial = (self.root/'entry.json').read_bytes()
        self.assertEqual(len(partial), 3)
        with self.assertRaises(ValueError): writer.write('entry.json', {})
        self.assertEqual((self.root/'entry.json').read_bytes(), partial)


if __name__ == '__main__': unittest.main()
