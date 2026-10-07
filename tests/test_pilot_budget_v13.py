import json
from pathlib import Path
import tempfile
import unittest
from src.pilot_budget import inherited_allowance,research_worker_lock


class InheritedBudgetTests(unittest.TestCase):
    def test_later_revisions_and_reservations_cannot_reset_allowance(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for path,amount,state in [('v10/phase-cpu-budget/ledger.json',614,'settled'),('v12/a/phase-cpu-budget/ledger.json',100,'settled'),('v13/a/phase-cpu-budget/ledger.json',200,'settled'),('v14/a/phase-cpu-budget/ledger.json',300,'settled')]:
                p=root/'pilots'/path;p.parent.mkdir(parents=True);p.write_text(json.dumps({'attempts':{'a':dict(charged_cpu_seconds=amount,state=state)}}))
            self.assertEqual(inherited_allowance(root),(1214,9586))
            p=root/'pilots/v14/a/phase-cpu-budget/ledger.json';p.write_text(json.dumps({'attempts':{'a':dict(charged_cpu_seconds=902,state='reserved')}}))
            with self.assertRaises(ValueError):inherited_allowance(root)

    def test_shared_lock_rejects_second_admission_and_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            with research_worker_lock(directory):
                with self.assertRaises(ValueError):
                    with research_worker_lock(directory):pass
            with research_worker_lock(directory):pass
