"""Synthetic complete-clock reconciliation, never scientific evidence."""
from copy import deepcopy
import unittest
from research_v89.terminal import cost
from research_v89.host import reconcile_cpu
from src.run_store import canonical_json, digest


def fixture():
    p = {'fixture': True}
    entry = dict(status='complete', error=None, program_sha256=digest(canonical_json(p)),
                 job_id='99999', operation='run', process_cpu_ns=10**9,
                 waited_child_cpu_ns=5*10**9, sealed_worker_cpu_ns=4*10**9, elapsed_ns=9*10**9)
    host = {k:entry[k] for k in ('status', 'error', 'program_sha256', 'job_id', 'operation')}
    host.update(host_process_cpu_ns=10**9, preflight_waited_child_cpu_ns=10**9,
                outcome=dict(exit_code=0, failure=None, subtree_cpu_ns=6*10**9, log=dict(complete=True)),
                elapsed_ns=10*10**9)
    host['accounting'] = reconcile_cpu('run', 10**9, 10**9, 6*10**9, entry)
    scheduler = dict(job_id='99999', elapsed_seconds=10, cpu_ns=10*10**9, quantum_ns=10**6)
    worker = dict(outcome=dict(status='complete'), budget_debit=dict(state='settled', observed_cpu_ns=4*10**9),
                  resource_usage=dict(total_cpu_ns=4*10**9))
    return host, entry, scheduler, p, 'run', worker


class TerminalTests(unittest.TestCase):
    def test_full_scheduler_cost_and_precision_retained_without_double_counting(self):
        r = cost(*fixture())
        self.assertEqual(r['scheduler_cpu_ns'], 10*10**9)
        self.assertEqual(r['nonnumerical_upper_cpu_ns'], 6*10**9+10**6)
        self.assertTrue(r['overlapping_clocks_not_summed'])

    def test_missing_worker_or_mutated_sealed_cpu_refuses(self):
        args = list(fixture());args[-1] = None
        with self.assertRaises(ValueError): cost(*args)
        args = list(fixture());args[-1]['budget_debit']['observed_cpu_ns'] += 1
        with self.assertRaises(ValueError): cost(*args)

    def test_short_scheduler_cpu_or_elapsed_cannot_hide_host_overhead(self):
        for key, value in (('cpu_ns', 7*10**9), ('elapsed_seconds', 8)):
            args = list(fixture());args[2][key] = value
            with self.assertRaises(ValueError): cost(*args)

    def test_final_scheduler_overage_refuses_even_with_passing_inner_clocks(self):
        args = list(fixture());args[2]['cpu_ns'] = 606*10**9
        with self.assertRaisesRegex(ValueError, 'cap'): cost(*args)

    def test_failed_or_differently_bound_host_refuses(self):
        for key, value in (('status', 'failed'), ('job_id', '15905'), ('program_sha256', '0'*64)):
            args = list(fixture());args[0][key] = value
            with self.assertRaises(ValueError): cost(*args)


if __name__ == '__main__':
    unittest.main()
