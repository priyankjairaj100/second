"""Arithmetic/coverage checks for the NOT-YET-INTEGRATED write census."""
import unittest
from research_v90 import storage_plan as plan
from research_v90.outputs import allowance
from research_v87.outputs import allowance as old_allowance
from research_v84.config import ORDER, expected_artifacts
from research_v90.outputs import MODEL_BYTES
from research_v90.records import Records


class StorageTests(unittest.TestCase):
    def test_twentytwo_workers_and_twenty_eight_allocations(self):
        p = plan.build(); rows = p['roles']
        self.assertEqual(len([r for r in rows if r['role'] == 'worker_outputs']), 20)
        self.assertEqual(len([r for r in rows if r['role'] == 'target_admission_outputs']), 2)
        self.assertEqual(len([r for r in rows if r['role'] == 'captured_bootstrap_log']), 28)
        self.assertEqual(len([r for r in rows if r['role'] == 'controller_ledger_and_replacement']), 22)

    def test_all_role_extents_and_allocation_margin_accounted_once(self):
        p = plan.build()
        for key, rows in [('project', p['roles']), ('temporary', p['temporary_roles'])]:
            logical = sum(r['bytes'] for r in rows); files = sum(r['files'] for r in rows)
            rounded = logical+4096*files
            self.assertEqual(p[key], dict(logical_bytes=logical, files=files,
                required_bytes=rounded+(rounded+3)//4+plan.GIB, required_files=files+4096))
        self.assertFalse(p['eligible_for_storage_admission'])
        self.assertFalse(p['historical_outputs_credited_as_free'])

    def test_metadata_census_is_accepted_by_exact_writer(self):
        for kind in ('admission', 'complete'):
            layout = plan.metadata_layout(kind)
            writer = Records('/uncreated-plan-only-path', layout)
            row = next(r for r in plan.build()['roles'] if r['role'] == 'exclusive_metadata' and r['chain'] == kind)
            self.assertEqual((row['bytes'], row['files']), (writer.allowance()['bytes'], writer.allowance()['files']))
            self.assertIn('registration.json', layout)
            self.assertIn('gates/v89-terminal.json', layout)
            self.assertIn('chain-released-chain.json', layout)

    def test_progress_reduction_does_not_cut_artifact_or_diagnostic_extent(self):
        previous = sum(old_allowance(expected_artifacts(t), MODEL_BYTES[t.split('/')[0]])['output_bytes'] for t in ORDER)
        current = sum(allowance(t)['output_bytes'] for t in ORDER)
        self.assertEqual(previous-current, (20*512-1714)*2**20)


if __name__ == '__main__': unittest.main()
