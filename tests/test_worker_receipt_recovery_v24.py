"""Small process fixtures for preserving observations across ledger failure."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from src.phase_budget import PhaseBudget
from src.worker_control import WorkerLimits,run_limited

class ReceiptRecoveryTests(unittest.TestCase):
    def run_fixture(self, root, budget):
        return run_limited([sys.executable,'-c',"print('fixture')"],root/'worker',
            WorkerLimits(5,3,128*2**20,1,(min(os.sched_getaffinity(0)),)),
            identity={'fixture':'receipt-recovery'},phase_budget=budget,phase='software_test')

    def test_exit_evidence_survives_settlement_failure(self):
        class BrokenSettlement(PhaseBudget):
            def settle(self,*args):raise ValueError('injected missing reservation')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);budget=BrokenSettlement(root/'budget',identity={},phase_cpu_seconds={'software_test':5})
            with self.assertRaisesRegex(ValueError,'injected missing reservation'):self.run_fixture(root,budget)
            attempt=root/'worker/attempt-0001'
            observation=json.loads((attempt/'pre-settlement-observation.json').read_bytes())
            reservation=json.loads((attempt/'budget-reservation.json').read_bytes())
            self.assertEqual(observation['outcome']['returncode'],0)
            self.assertEqual(observation['outcome']['status'],'complete')
            self.assertGreater(observation['resource_usage']['total_cpu_ns'],0)
            self.assertEqual(reservation['budget_debit']['observed_cpu_ns'],None)
            self.assertEqual(reservation['budget_attempt_id'],observation['budget_attempt_id'])
            self.assertTrue((attempt/'stdout-summary.json').is_file())
            self.assertTrue((attempt/'stderr-summary.json').is_file())
            self.assertEqual(json.loads((root/'worker/result.json').read_bytes())['status'],'running')

    def test_completed_receipt_binds_preserved_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);budget=PhaseBudget(root/'budget',identity={},phase_cpu_seconds={'software_test':5})
            receipt=self.run_fixture(root,budget)
            self.assertEqual(receipt['outcome']['status'],'complete')
            self.assertEqual(receipt['budget_debit']['state'],'settled')
            self.assertIn('pre-settlement-observation.json',receipt['artifacts'])
            self.assertIn('budget-reservation.json',receipt['artifacts'])
