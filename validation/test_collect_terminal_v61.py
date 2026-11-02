"""Stdlib fixtures only; no cluster connection, research imports, or model work."""
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('collect_terminal_v61.py'))
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


def accounting(states=None):
    states = states or {}
    rows = []
    for name, job in c.JOBS.items():
        state, exit_code = states.get(name, ('COMPLETED', '0:0'))
        rows.append('|'.join((job, 'second61-' + name, state, exit_code, '9',
            '00:00:08', '2026-10-14T01:00:00', '2026-10-14T01:00:09')) + '|')
    return '\n'.join(rows) + '\n'


class CollectorFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        self.root = self.parent / 'repository'
        self.root.mkdir()

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def fixture(self, *, blocked=False):
        source = self.write('src/example.py', b'# source fixture\n')
        protocol = self.write('research_v61/PROTOCOL.txt', b'Protocol fixture\n')
        prior = self.write('local_runs/prior/outputs/completion.json', b'{"status":"complete"}')
        binary = self.write('local_runs/prior/outputs/candidate-model.bin', b'not an actual model')
        ledger = self.write('local_runs/prior/budget/ledger.json', b'{"ledger":"historical"}')
        inputs = {name: dict(path=str(path), **c.info(path.read_bytes()))
            for name, path in [('prior_completion', prior), ('candidate', binary)]}
        sources = {str(path.relative_to(self.root)): c.info(path.read_bytes())['sha256']
            for path in (source, protocol)}
        program = dict(directory=str(self.root / 'local_runs' / c.CAMPAIGN),
            registered_source_commit=c.EXPECTED_COMMIT, sources=sources, runtime={'fixture': True},
            inputs=inputs, historical_ledgers={str(ledger.relative_to(self.root)): c.info(ledger.read_bytes())['sha256']})
        program_data = c.canonical(program)
        program_sha = c.info(program_data)['sha256']
        self.write('local_runs/' + c.CAMPAIGN + '/program.json', program_data)
        self.write('local_runs/' + c.CAMPAIGN + '/registration.json', c.canonical(dict(program_sha256=program_sha)))
        self.write('local_runs/' + c.LAUNCH + '/source-commit.txt', c.EXPECTED_COMMIT.encode() + b'\n')
        self.write('local_runs/' + c.LAUNCH + '/jobs.tsv', ''.join(
            key + '\t' + value + '\n' for key, value in c.JOBS.items() if key != 'checks').encode())
        self.write('local_runs/' + c.SOFTWARE_LAUNCH + '/checks-' + c.JOBS['checks'] + '.log', b'205 tests passed, 0 skips\n')
        self.write('local_runs/' + c.SOFTWARE, c.canonical(dict(status='passed', tests=205, skipped=0,
            sources=sources, runtime=program['runtime'], source_and_runtime_unchanged=True,
            real_model_inference=False, slurm_job_id=c.JOBS['checks'])))
        self.write('local_runs/' + c.CAMPAIGN + '/prepare/outputs/completion.json', b'{partial')
        self.write('local_runs/' + c.CAMPAIGN + '/prepare/transaction.json', b'{"worker_outcome":null}')
        self.write('local_runs/' + c.CAMPAIGN + '/prepare/worker/result.json',
            c.canonical(dict(status='failed', outcome=None, attempt='attempt-0001', artifacts={})))
        states = dict(prepare=('FAILED', '1:0'))
        for name in ('cached', 'cold', 'hybrid', 'compressed', 'oracle', 'audit', 'postrun'):
            states[name] = ('PENDING', '0:0') if blocked else ('CANCELLED by 1000', '0:0')
        queue = ''.join(c.JOBS[name] + '|PENDING|DependencyNeverSatisfied\n'
            for name, value in states.items() if value[0] == 'PENDING')
        def command(args):
            if args == ['git', 'rev-parse', 'HEAD']: return c.EXPECTED_COMMIT + '\n'
            if args == ['git', 'status', '--porcelain']: return ''
            if args[0] == 'squeue': return queue
            if args[0] == 'sacct': return accounting(states) if '-X' in args else 'fixture step accounting\n'
            raise AssertionError('Unexpected command: ' + repr(args))
        return program_sha, binary, ledger, c.Collector(self.root, command, failure_capture=blocked)

    def test_scheduler_terminal_rows_and_exact_census(self):
        rows = c.parse_accounting(accounting(dict(prepare=('FAILED', '1:0'), cold=('CANCELLED by 1000', '0:0'))))
        self.assertEqual(rows[c.JOBS['cold']]['state'], 'CANCELLED')
        for altered in (accounting().splitlines()[0] + '\n', accounting() + accounting().splitlines()[0] + '\n'):
            with self.assertRaises(ValueError): c.parse_accounting(altered)

    def test_scheduler_refuses_active_unknown_and_ordinary_pending(self):
        for state in ('RUNNING', 'COMPLETING', 'CONFIGURING', 'STAGE_OUT', 'SUSPENDED', 'PENDING', 'NEW_UNKNOWN'):
            with self.subTest(state=state), self.assertRaises(ValueError):
                c.parse_accounting(accounting(dict(prepare=(state, '0:0'))))
        rows = c.parse_accounting(accounting(dict(prepare=('FAILED', '1:0'), cold=('PENDING', '0:0'))), allow_blocked=True)
        for state, reason in (('PENDING', 'Dependency'), ('RUNNING', 'None'), ('PENDING', 'Resources')):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                c.blocked_jobs(c.JOBS['cold'] + '|' + state + '|' + reason, rows, failure_capture=True)

    def test_blocked_failure_requires_explicit_mode_failed_ancestor_and_exact_queue(self):
        queued = c.JOBS['cold'] + '|PENDING|DependencyNeverSatisfied\n'
        rows = c.parse_accounting(accounting(dict(prepare=('FAILED', '1:0'), cold=('PENDING', '0:0'))), allow_blocked=True)
        with self.assertRaises(ValueError): c.blocked_jobs(queued, rows)
        with self.assertRaises(ValueError): c.blocked_jobs('', rows, failure_capture=True)
        good = c.blocked_jobs(queued, rows, failure_capture=True)
        self.assertEqual(good[c.JOBS['cold']]['failed_ancestors'], [c.JOBS['prepare']])
        rows[c.JOBS['prepare']].update(state='COMPLETED', exit_code='0:0')
        with self.assertRaises(ValueError): c.blocked_jobs(queued, rows, failure_capture=True)
        rows = c.parse_accounting(accounting(dict(cold=('PENDING', '0:0'), oracle=('FAILED', '1:0'))), allow_blocked=True)
        with self.assertRaises(ValueError): c.blocked_jobs(queued, rows, failure_capture=True)

    def test_failure_capture_preserves_invalid_receipt_and_never_reads_binary(self):
        program_sha, binary, ledger, collector = self.fixture()
        original_open = Path.open
        def no_binary_open(path, *args, **kwargs):
            if path == binary: raise AssertionError('Numerical binary contents were opened')
            return original_open(path, *args, **kwargs)
        with patch.object(c, 'PROGRAM_SHA', program_sha), patch.object(c, 'SOURCE_COUNT', 2), patch.object(Path, 'open', no_binary_open):
            manifest = collector.collect()
        self.assertTrue(manifest['terminal'])
        self.assertFalse(manifest['reported_success'])
        self.assertEqual(manifest['capture_scope'], 'terminal_failure_or_incomplete_receipts_metadata_only')
        self.assertEqual(manifest['inputs_not_copied'][str(binary)]['status'], 'NOT revalidated')
        self.assertFalse(manifest['inputs_not_copied'][str(binary)]['binary_contents_read'])
        self.assertTrue(manifest['historical_ledger_bindings'][str(ledger)]['verified'])
        self.assertIn('repository/src/example.py', manifest['files'])
        self.assertIn(c.SOFTWARE_LAUNCH + '/checks-' + c.JOBS['checks'] + '.log', manifest['files'])
        self.assertIn('invalid_terminal_json', {item['kind'] for item in manifest['capture_issues']})
        bad = c.CAMPAIGN + '/prepare/outputs/completion.json'
        self.assertEqual(collector.contents[bad], b'{partial')
        self.assertEqual(manifest['files'][bad], c.info(b'{partial'))

    def test_blocked_failure_capture_is_explicitly_nonterminal_and_never_success(self):
        program_sha, _, _, collector = self.fixture(blocked=True)
        with patch.object(c, 'PROGRAM_SHA', program_sha), patch.object(c, 'SOURCE_COUNT', 2):
            manifest = collector.collect()
        self.assertFalse(manifest['terminal'])
        self.assertTrue(manifest['quiescent'])
        self.assertFalse(manifest['reported_success'])
        self.assertEqual(manifest['capture_scope'], 'quiescent_dependency_failure_metadata_only')
        self.assertEqual(len(manifest['blocked_dependency_jobs']), 7)

    def test_frozen_source_change_refused_even_in_failure_capture(self):
        program_sha, _, _, collector = self.fixture()
        (self.root / 'src/example.py').write_bytes(b'# changed source\n')
        with patch.object(c, 'PROGRAM_SHA', program_sha), patch.object(c, 'SOURCE_COUNT', 2), self.assertRaisesRegex(ValueError, 'Frozen source changed'):
            collector.collect()

    def test_final_rehash_catches_changed_bytes_even_if_metadata_is_stale(self):
        path = self.write('local_runs/prior/data.json', b'{"x":1}')
        observed_signature = c.signature(path)
        collector = c.Collector(self.root)
        with patch.object(c, 'signature', return_value=observed_signature):
            collector.capture(path)
            path.write_bytes(b'{"x":2}')
            with self.assertRaisesRegex(ValueError, 'Input bytes changed'): collector.rehash()

    def test_tree_census_includes_empty_directories_and_refuses_symlinks(self):
        self.write('local_runs/' + c.CAMPAIGN + '/metadata.json', b'{}')
        (self.root / 'local_runs' / c.LAUNCH).mkdir()
        (self.root / 'local_runs' / c.SOFTWARE_LAUNCH).mkdir()
        collector = c.Collector(self.root)
        before = collector.trees()
        (self.root / 'local_runs' / c.CAMPAIGN / 'new-empty').mkdir()
        self.assertNotEqual(before, collector.trees())
        (self.root / 'local_runs' / c.CAMPAIGN / 'symbolic').symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symbolic directory'): collector.trees()

    def test_archive_is_exclusive_and_contains_exact_payloads(self):
        destination = self.parent / 'capture.tar.gz'
        payloads = {'collection-manifest.json': b'{}\n', 'repository/src/fixture.py': b'# fixture\n'}
        result = c.write_archive(destination, payloads, self.root)
        self.assertEqual(result['sha256'], c.info(destination.read_bytes())['sha256'])
        with tarfile.open(destination, 'r:gz') as archive:
            self.assertEqual({member.name: archive.extractfile(member).read() for member in archive}, payloads)
        original = destination.read_bytes()
        with self.assertRaises(FileExistsError): c.write_archive(destination, {}, self.root)
        self.assertEqual(destination.read_bytes(), original)
        for unsafe in (self.root / 'capture.tar.gz', Path('relative.tar.gz'), self.parent / 'capture.zip'):
            with self.assertRaises(ValueError): c.write_archive(unsafe, {}, self.root)

    def test_unsafe_paths_and_input_bounds_are_refused(self):
        collector = c.Collector(self.root)
        for name in ('../escape.json', '/absolute.json', 'normal/../escape.json'):
            with self.assertRaises(ValueError): c.safe_relative(name)
        path = self.write('prior/data.json', b'{}')
        (self.root / 'prior/symbolic.json').symlink_to(path)
        with self.assertRaises(ValueError): collector.capture(self.root / 'prior/symbolic.json')
        with patch.object(c, 'MAX_FILE_BYTES', 1), self.assertRaisesRegex(ValueError, 'exceeds bound'):
            collector.capture(path)


if __name__ == '__main__':
    unittest.main()
