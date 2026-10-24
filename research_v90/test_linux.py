"""Actual new-child-module checks for a separately registered pinned Linux gate."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys
import unittest
from research_v90 import worker_control as c, phase_budget as b
from src.run_store import read_completed


@unittest.skipUnless(sys.platform == 'linux', 'Pinned Linux qualification required')
class LinuxControlTests(unittest.TestCase):
    def exercise(self, code):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            phase = b.PhaseBudget(root/'ledger', identity={'fixture': code}, phase_cpu_seconds={'test': 8})
            limits = c.WorkerLimits(10, 3, 512*2**20, 1, (min(os.sched_getaffinity(0)),), file_size_bytes=2**20)
            result = c.run_limited([sys.executable, '-c', code], root/'worker', limits,
                                  identity={'fixture': code}, cwd=root, phase_budget=phase, phase='test')
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(result['limits_applied']['affinity_cpus'], list(limits.affinity_cpus))
            self.assertEqual(result['budget_debit']['state'], 'settled')
            self.assertEqual(result['budget_debit']['observed_cpu_ns'], result['resource_usage']['total_cpu_ns'])
            import json
            identity = json.loads((root/'worker/identity.json').read_bytes())
            self.assertEqual(result, read_completed(root/'worker', identity))
            before = (root/'ledger/ledger.json').read_bytes()
            with self.assertRaises(FileExistsError):
                c.run_limited([sys.executable, '-c', code], root/'worker', limits,
                              identity={'fixture': code}, cwd=root, phase_budget=phase, phase='test')
            self.assertEqual(before, (root/'ledger/ledger.json').read_bytes())
            return result

    def test_new_child_module_seals_success_and_exact_debit(self):
        self.assertEqual(self.exercise('print("bounded controller fixture")')['outcome']['status'], 'complete')

    def test_nonzero_worker_is_sealed_as_failure(self):
        outcome = self.exercise('raise SystemExit(3)')['outcome']
        self.assertEqual((outcome['status'], outcome['kind'], outcome['returncode']), ('failed', 'nonzero_exit', 3))

    def test_real_child_checks_its_live_exact_command_and_source_ledger(self):
        import json
        from research_v90.admission import ledger_identity
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve(); sha = 'a'*64
            sources = {'fixture.py': {'bytes': 3, 'sha256': 'b'*64}}
            identity = dict(program_sha256=sha, profile='fixture')
            caps = {'admission': 8}
            phase = b.PhaseBudget(root/'budget', identity=ledger_identity(sha, sources), phase_cpu_seconds=caps)
            limits = c.WorkerLimits(10, 3, 512*2**20, 1, (min(os.sched_getaffinity(0)),), file_size_bytes=2**20)
            parameters = dict(program=sha, sources=sources, caps=caps, budget=str(phase.root),
                worker=str(root/'worker'), identity=identity, limits=limits.payload(), cwd=str(root))
            code = '''import json,sys
from research_v90.admission import verify_command_admission
from research_v90.worker_control import WorkerLimits
p=json.loads(sys.argv[1])
verify_command_admission(p['program'],'admission',sys.orig_argv,sources=p['sources'],
 phase_cpu_seconds=p['caps'],budget_root=p['budget'],worker_root=p['worker'],
 worker_identity=p['identity'],limits=WorkerLimits.from_payload(p['limits']),cwd=p['cwd'])
print('actual child admission verified')
'''
            result = c.run_limited([sys.executable, '-c', code, json.dumps(parameters)], root/'worker', limits,
                                  identity=identity, cwd=root, phase_budget=phase, phase='admission')
            self.assertEqual(result['outcome']['status'], 'complete')
            self.assertEqual(result['budget_debit']['state'], 'settled')
            self.assertEqual(result['budget_debit']['reserved_cpu_seconds'], 5)


if __name__ == '__main__': unittest.main()
