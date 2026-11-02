"""Generated collector guards; no network or empirical terminal execution."""
import base64
import copy
import unittest
from reporting_v113.collect import (EXPECTED, JOBS, RUN, receipt_names,
                                  validate_terminal, decode_payload, identity)


def fixture():
    inputs = {str(RUN/n): identity(b'x') for n in receipt_names()}
    inputs[str(RUN/'program.json')]['sha256'] = EXPECTED
    return dict(schema='matched-complete-terminal-v112', status='verified',
                program_sha256=EXPECTED, jobs=copy.deepcopy(JOBS), inputs=inputs,
                scheduler_raw='\n'.join('|'.join([r['job_id'], r['name'], 'COMPLETED',
                    '0:0', '1', '00:00.001', '1', '16G', 'csis.mn1']) for r in JOBS.values()))


class Collect(unittest.TestCase):
    def test_exact_metadata_census(self):
        result = validate_terminal(fixture())
        self.assertEqual(len(result), 36)
        self.assertFalse(any(n.endswith('.bin') or n.endswith('records.json') for n in result))

    def test_unfinished_failed_or_substituted_jobs_refuse(self):
        for change in ('running', 'failed', 'substituted'):
            t = fixture()
            if change == 'substituted':
                t['jobs']['checks']['job_id'] = '16309'
            else:
                t['scheduler_raw'] = t['scheduler_raw'].replace('COMPLETED', change.upper(), 1)
            with self.assertRaises(ValueError):
                validate_terminal(t)

    def test_changed_program_and_oversized_receipt_refuse(self):
        for change in ('program', 'size'):
            t = fixture()
            if change == 'program':
                t['inputs'][str(RUN/'program.json')]['sha256'] = '0'*64
            else:
                t['inputs'][str(RUN/'primary-audit.json')]['bytes'] = 17*2**20
            with self.assertRaises(ValueError):
                validate_terminal(t)

    def test_transfer_checks_actual_bytes_and_exact_names(self):
        wanted = {'program.json': identity(b'actual')}
        payload = {'program.json': base64.b64encode(b'actual').decode()}
        self.assertEqual(decode_payload(payload, wanted), {'program.json': b'actual'})
        for altered in ({}, dict(payload, extra=''), {'program.json': base64.b64encode(b'change').decode()}):
            with self.assertRaises(ValueError):
                decode_payload(altered, wanted)


if __name__ == '__main__':
    unittest.main()
