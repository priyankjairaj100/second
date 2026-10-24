"""Actual tiny receipt files; complete clocks and storage remain synthetic."""
from pathlib import Path
import tempfile
import unittest
from research_v80.io import write, json_read, read, info
from research_v89 import config, envelope, storage_plan
from research_v89.host import reconcile_cpu
from research_v88.storage import evaluate
from src.run_store import canonical_json, digest


class Inputs:
    def json(self, path): return json_read(path)
    def read(self, path, retain=True): return read(path, retain=retain)


def fixture(root):
    sources = {'example.py': dict(bytes=1, sha256='a'*64)}
    p = dict(config.design(), source_inventory=sources, source_archive_bytes=10240,
             storage_plan=storage_plan.build(sources, 10240))
    sha = digest(canonical_json(p))
    raw = 'Filesystem blocks quota limit grace files quota limit grace\n/dev/project 100 999999999 1000000000 12 0 0\n'
    for trial in p['trial_order']:
        wanted = storage_plan.requests(p['storage_plan'], sources, 10240, trial)
        observations = {scope:dict(path=row['path'], source='/dev/project' if scope == 'project' else '/dev/temp',
                                  device=1 if scope == 'project' else 2, mount='/',
                                  filesystem='ext4' if scope == 'project' else 'xfs',
                                  options='rw,usrquota' if scope == 'project' else 'rw,noquota',
                                  available_bytes=2**40, available_files=100000, fragment_bytes=4096, write_group=1008)
                        for scope, row in wanted.items()}
        snapshot = dict(requested=wanted, observations=observations, quota_text=raw, group_reports={})
        entry = dict(status='complete', error=None, program_sha256=sha, job_id='99999', operation='run', arguments=[trial],
                     process_cpu_ns=10, waited_child_cpu_ns=50, sealed_worker_cpu_ns=40, elapsed_ns=90,
                     container_storage_mapping=dict(status='matched_host_devices_and_new_file_groups', paths_redirected=False,
                         observations={scope:dict(path=str(root) if scope == 'project' else '/tmp', device=obs['device'], write_group=1008)
                                       for scope, obs in observations.items()}))
        start = dict(program_sha256=sha, job_id='99999', operation='run', arguments=[trial], requests=wanted,
                     snapshot=snapshot, admission=evaluate(wanted, observations, raw, {}))
        host = {k:entry[k] for k in ('status', 'error', 'program_sha256', 'job_id', 'operation', 'arguments')}
        host.update(host_process_cpu_ns=3, preflight_waited_child_cpu_ns=7, elapsed_ns=100,
                    outcome=dict(exit_code=0, failure=None, subtree_cpu_ns=100,
                                 log=dict(**info(b'log'), complete=True, observed_bytes=3)),
                    accounting=reconcile_cpu('run', 3, 7, 100, entry))
        write(root/(trial+'-entry.json'), entry)
        write(root/(trial+'-host-start.json'), start)
        write(root/(trial+'-host.json'), host)
        write(root/(trial+'-bootstrap.log'), b'log', raw=True)
        write(root/trial/'worker/result.json', dict(resource_usage=dict(total_cpu_ns=40), budget_debit=dict(observed_cpu_ns=40)))
    return p


class EnvelopeTests(unittest.TestCase):
    def test_actual_saved_receipts_and_log_bytes_reconcile(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve();p = fixture(root)
            result = envelope.review(root, p, Inputs())
            self.assertEqual(len(result['entries']), 10)
            self.assertEqual(result['nonnumerical_cpu_ns'], 700)
            (root/'prepare-bootstrap.log').write_bytes(b'changed')
            with self.assertRaises(ValueError): envelope.review(root, p, Inputs())

    def test_changed_clock_sample_or_path_mapping_refuses(self):
        for which in ('clock', 'mapping'):
            with self.subTest(which=which), tempfile.TemporaryDirectory() as d:
                root = Path(d).resolve();p = fixture(root)
                path = root/('prepare-host.json' if which == 'clock' else 'prepare-entry.json')
                row = json_read(path)
                if which == 'clock': row['host_process_cpu_ns'] += 1
                else: row['container_storage_mapping']['observations']['temporary']['device'] += 1
                path.write_bytes(canonical_json(row))
                with self.assertRaises(ValueError): envelope.review(root, p, Inputs())


if __name__ == '__main__':
    unittest.main()
