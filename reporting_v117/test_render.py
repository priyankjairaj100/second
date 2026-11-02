"""Generated malformed-report tests; no actual empirical result is consumed."""
import contextlib
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import reporting_v113.collect as collector
import reporting_v117.render as renderer
from reporting_v113.test_reuse import generate
from reporting_v113.reduce import main as reduce_saved
from reporting_v93.cost_scope import comparisons
from reporting_v117.render import render, main, decimal, JOBS, PROFILES, CELLS


def generated():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        terminal = generate(root)
        output = root/'result.json'
        with contextlib.redirect_stdout(io.StringIO()):
            reduce_saved(terminal, root, output)
        result = json.loads(output.read_bytes())
    for row in result['rows']:
        row['job_id'] = JOBS[f"{row['profile']}/{row['cell']}-{row['step']}"]['job_id']
        # Deliberately mixed: compressed wins at the first endpoint and loses at
        # the second. This must survive reporting without averaging or sign swaps.
        if row['cell'] == 'optimized_compressed':
            row['host_elapsed_ns'] = 1500 if row['step'] == 1 else 2500
            row['disjoint_host_partition_ns']['outside_request'] = row['host_elapsed_ns']-row['request_elapsed_ns']
            row['live_state_bytes'] = 90
            row['checkpoint_inclusive_bytes'] = 190
    for profile in PROFILES:
        rows = {(r['cell'], r['step']): r for r in result['rows'] if r['profile'] == profile}
        result['comparisons'][profile] = comparisons(rows)
    return result


class ClosedReporting(unittest.TestCase):
    def test_generated_closed_path_recomputes_and_detects_tampered_scalar(self):
        # Explicit synthetic program/job identities exercise file plumbing. The
        # production command never overrides either identity (tested below).
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            receipts = base/'receipts'
            receipts.mkdir()
            terminal_path = generate(receipts)
            terminal = json.loads(terminal_path.read_bytes())
            (base/'terminal-stdout.json').write_bytes(terminal_path.read_bytes())
            with contextlib.redirect_stdout(io.StringIO()):
                reduce_saved(base/'terminal-stdout.json', receipts, base/'reduction.json')
            with mock.patch.object(collector, 'EXPECTED', terminal['program_sha256']), \
                 mock.patch.object(collector, 'JOBS', terminal['jobs']), \
                 mock.patch.object(renderer, 'EXPECTED', terminal['program_sha256']), \
                 mock.patch.object(renderer, 'JOBS', terminal['jobs']):
                target = base/'report'
                with contextlib.redirect_stdout(io.StringIO()):
                    main(base, target)
                manifest = json.loads((target/'MANIFEST.json').read_bytes())
                self.assertEqual(manifest['program_sha256'], terminal['program_sha256'])
                for name, entry in manifest['files'].items():
                    self.assertEqual(renderer.identity((target/name).read_bytes()), entry)
                with self.assertRaisesRegex(ValueError, 'exclusive'):
                    main(base, target)
                changed = json.loads((base/'reduction.json').read_bytes())
                changed['rows'][0]['host_elapsed_ns'] += 100
                (base/'reduction.json').write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, 'differs from recomputed'):
                    main(base, base/'tampered-report')
                self.assertFalse((base/'tampered-report').exists())

    def test_all_rows_and_adverse_direction_survive(self):
        result = generated()
        payload = render(result)
        rows = list(csv.DictReader(io.StringIO(payload['all-requests.tsv'].decode()), delimiter='\t'))
        self.assertEqual(len(rows), 16)
        self.assertEqual({r['job_id'] for r in rows}, {str(i) for i in range(16408, 16424)})
        contrasts = json.loads(payload['signed-contrasts.json'])
        self.assertEqual([r['complete_host_change_percent'] for r in contrasts],
                         ['-25.000', '25.000', '-25.000', '25.000'])
        self.assertEqual({r['live_storage_change_percent'] for r in contrasts}, {'-10.000'})
        self.assertIn(b'0.7500', payload['matched-table.tex'])
        self.assertIn(b'1.2500', payload['matched-table.tex'])

    def test_missing_losing_endpoint_and_duplicate_refuse(self):
        for duplicate in (False, True):
            r = generated()
            r['rows'].pop()
            if duplicate:
                r['rows'].append(copy.deepcopy(r['rows'][0]))
            with self.assertRaises(ValueError):
                render(r)

    def test_swapped_job_endpoint_or_ratio_refuse(self):
        for change in ('job', 'endpoint', 'ratio'):
            r = generated()
            if change == 'job':
                r['rows'][0]['job_id'] = '16423'
            elif change == 'endpoint':
                r['rows'][0]['retained_records'] = 2
            else:
                r['comparisons']['gpt2'][1]['optimized_compressed_to_modern']['host_elapsed_ns']['numerator'] = 1
            with self.assertRaises(ValueError):
                render(r)

    def test_scope_upgrade_or_erased_historical_cost_refuse(self):
        for change in ('quality', 'stable', 'transfer', 'old_debit', 'zero_prepare', 'missing_prepare'):
            r = generated()
            if change == 'quality':
                r['new_quality_evaluation'] = True
            elif change == 'stable':
                r['stable_latency_established'] = True
            elif change == 'transfer':
                r['cross_architecture_generality'] = True
            elif change == 'old_debit':
                r['old_unknown_v80_cpu_seconds'] = 0
            elif change == 'zero_prepare':
                r['reused_preparation_host_ns']['gpt2'] = 0
            else:
                r['reused_preparation_host_ns'].pop('gpt2')
            with self.assertRaises(ValueError):
                render(r)

    def test_nested_clock_is_not_added_or_renamed(self):
        r = generated()
        r['rows'][0]['disjoint_host_partition_ns']['stage_work_including_any_fallback'] += 1
        with self.assertRaises(ValueError):
            render(r)
        r = generated()
        r['rows'][0]['decoder_only_duration_available'] = True
        with self.assertRaises(ValueError):
            render(r)

    def test_costs_preserve_prior_charges_without_sum(self):
        r = generated()
        costs = json.loads(render(r)['costs-and-scope.json'])
        self.assertEqual(costs['prior_screen_costs'], r['prior_screen_costs'])
        self.assertEqual(costs['reused_preparation_host_ns'], r['reused_preparation_host_ns'])
        self.assertEqual(costs['cumulative_screen_numerical_seconds'], 6322)
        self.assertFalse(costs['combine_scheduler_worker_controller_clocks'])
        self.assertFalse(costs['all_experiments_total_established'])

    def test_generated_terminal_cannot_publish_as_actual(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            receipts = base/'receipts'
            receipts.mkdir()
            terminal = generate(receipts)
            (base/'terminal-stdout.json').write_bytes(terminal.read_bytes())
            target = base/'report'
            with self.assertRaisesRegex(ValueError, 'Exact successful V112 terminal'):
                main(base, target)
            self.assertFalse(target.exists())

    def test_decimal_rounding_keeps_ns_units_and_large_integers(self):
        self.assertEqual(decimal(2027290442863, 10**9), '2027.290')
        self.assertEqual(decimal(100*(1500-2000), 2000), '-25.000')
        self.assertEqual(decimal(10**20+1, 10**20, 20), '1.00000000000000000001')


if __name__ == '__main__':
    unittest.main()
