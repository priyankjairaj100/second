"""Real ledger/command contracts without replacing the verifier with a mock."""
import ast
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from research_v90 import admission as a
from research_v90.phase_budget import PhaseBudget
from research_v90.worker_control import WorkerLimits
from src.run_store import canonical_json, digest


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.program = 'a'*64; self.sources = {'fixture.py': {'bytes': 3, 'sha256': 'b'*64}}
        self.limits = WorkerLimits(900, 600, 16*2**30, 1, (0,), file_size_bytes=2*2**30)
        self.caps = {'admission': 1204}; self.worker_identity = dict(program_sha256=self.program, profile='distilgpt2')
        self.command = ['/usr/bin/python3', '-B', str(self.root/'worker.py'), str(self.root/'plan.json')]
        self.budget = PhaseBudget(self.root/'budget', identity=a.ledger_identity(self.program, self.sources), phase_cpu_seconds=self.caps)
        binding = dict(schema='limited-worker-identity-v1', identity=self.worker_identity,
            command=self.command, cwd=str(self.root), limits=self.limits.payload(),
            phase_budget=dict(binding_sha256=self.budget.identity_digest, phase='admission', directory=str(self.budget.root)))
        self.attempt = digest(canonical_json(dict(worker=binding, attempt=str(self.root/'worker/attempt-0001'))))
        self.budget.reserve('admission', self.attempt, 602)
        self.env = dict(phase_budget_root=str(self.budget.root), phase_budget_binding_sha256=self.budget.identity_digest,
            attempt_id=self.attempt, phase='admission', command=self.command, cwd=str(self.root))

    def verify(self, **changes):
        arguments = dict(sources=self.sources, phase_cpu_seconds=self.caps, budget_root=self.budget.root,
                         worker_root=self.root/'worker', worker_identity=self.worker_identity,
                         limits=self.limits, cwd=self.root)
        arguments.update(changes)
        with patch.dict(os.environ, CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(self.env).decode()):
            return a.verify_command_admission(self.program, 'admission', self.command, **arguments)

    def test_exact_live_allowance_passes_without_any_ledger_write(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.budget.root.iterdir()}
        self.assertEqual(self.verify(), self.env)
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.budget.root.iterdir()}
        self.assertEqual(before, after)

    def test_wrong_command_cwd_phase_root_digest_and_attempt_refuse(self):
        for key, value in [('command', ['/bin/true']), ('cwd', '/wrong'), ('phase', 'other'),
                           ('phase_budget_root', '/other'), ('phase_budget_binding_sha256', 'c'*64), ('attempt_id', 'd'*64)]:
            with self.subTest(key=key), patch.dict(self.env, {key: value}):
                with self.assertRaises(ValueError): self.verify()

    def test_changed_sources_cap_identity_and_limits_refuse(self):
        for change in [dict(sources={'other.py': {'bytes': 3, 'sha256': 'b'*64}}),
                       dict(phase_cpu_seconds={'admission': 1205}),
                       dict(worker_identity=dict(self.worker_identity, profile='gpt2')),
                       dict(limits=WorkerLimits(900, 601, 16*2**30, 1, (0,), file_size_bytes=2*2**30))]:
            with self.subTest(change=change):
                with self.assertRaises(ValueError): self.verify(**change)

    def test_settled_allowance_is_not_reusable(self):
        self.budget.settle(self.attempt, 100)
        with self.assertRaisesRegex(ValueError, 'live reservation'): self.verify()

    def test_missing_environment_and_extra_fields_refuse(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                a.verify_command_admission(self.program, 'admission', self.command,
                    sources=self.sources, phase_cpu_seconds=self.caps, budget_root=self.budget.root,
                    worker_root=self.root/'worker', worker_identity=self.worker_identity, limits=self.limits, cwd=self.root)
        with patch.dict(self.env, extra=True):
            with self.assertRaises(ValueError): self.verify()

    def test_missing_ledger_is_not_created(self):
        missing = self.root/'missing'
        self.env['phase_budget_root'] = str(missing)
        with self.assertRaises(ValueError): self.verify(budget_root=missing)
        self.assertFalse(missing.exists())

    def test_frozen_legacy_import_bug_is_recorded_without_mutation(self):
        root = Path(__file__).resolve().parents[1]
        old = ast.parse((root/'research_v82/target_worker.py').read_text())
        imports = [n for n in ast.walk(old) if isinstance(n, ast.ImportFrom) and n.module == 'src.worker_control']
        self.assertTrue(any(a.name == 'verify_command_admission' for n in imports for a in n.names))
        from src import worker_control, transaction_timing
        self.assertFalse(hasattr(worker_control, 'verify_command_admission'))
        self.assertTrue(callable(transaction_timing.verify_command_admission))

    def test_legacy_verifier_rejects_actual_transfer_identity_schema(self):
        # Reproduces the second independent wiring defect with actual ledger
        # bytes. Only the historical source inventory scan is stubbed; the
        # verifier, ledger parsing and identity check execute unchanged.
        from src.transaction_timing import verify_command_admission
        with patch.dict(os.environ, CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(self.env).decode()), \
                patch('src.experiment_inventory.source_hashes', return_value={}):
            with self.assertRaisesRegex(ValueError, 'identity or schema'):
                verify_command_admission(self.program, 'admission', self.command)


if __name__ == '__main__': unittest.main()
