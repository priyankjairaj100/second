"""Read-only reconciliation of saved host envelopes against contained workers."""
from research_v80.io import require
from research_v89.host import reconcile_cpu
from research_v89.storage_plan import requests
from research_v88.storage import evaluate
from src.run_store import canonical_json, digest


def review(directory, program, inputs):
    sha = digest(canonical_json(program))
    rows = {}
    for trial in program['trial_order']:
        host = inputs.json(directory/(trial+'-host.json'))
        start = inputs.json(directory/(trial+'-host-start.json'))
        entry = inputs.json(directory/(trial+'-entry.json'))
        worker = inputs.json(directory/trial/'worker/result.json')
        for row in (host, start, entry):
            require(row['program_sha256'] == sha and row['operation'] == 'run'
                    and row['arguments'] == [trial] and row['job_id'] == entry['job_id'],
                    'Host/entry identity differs')
        require(host['status'] == entry['status'] == 'complete'
                and host['error'] is entry['error'] is None,
                'Actual successful host and entry receipts required')
        require(entry['sealed_worker_cpu_ns'] == worker['resource_usage']['total_cpu_ns']
                == worker['budget_debit']['observed_cpu_ns'], 'Contained numerical CPU differs')
        require(entry['container_storage_mapping']['status'] == 'matched_host_devices_and_new_file_groups'
                and entry['container_storage_mapping']['paths_redirected'] is False,
                'Container path qualification absent')
        wanted = requests(program['storage_plan'], program['source_inventory'],
                          program['source_archive_bytes'], trial)
        snapshot = start['snapshot']
        for scope, path in (('project', str(directory)), ('temporary', '/tmp')):
            observed = snapshot['observations'][scope]
            require(entry['container_storage_mapping']['observations'][scope]
                    == dict(path=path, device=observed['device'], write_group=observed['write_group']),
                    'Saved container device/group mapping differs from host observation')
        require(start['requests'] == snapshot['requested'] == wanted,
                'Saved allowance differs from registered write plan')
        require(start['admission'] == evaluate(wanted, snapshot['observations'],
                snapshot['quota_text'], snapshot['group_reports']), 'Saved capacity observation does not admit this plan')
        outcome = host['outcome']
        require(outcome['exit_code'] == 0 and outcome['failure'] is None
                and outcome['log']['complete'] is True
                and 0 <= outcome['log']['bytes'] <= 64*2**20
                and outcome['log']['observed_bytes'] == outcome['log']['bytes'],
                'Failed or overflowed host log is not successful evidence')
        require(inputs.read(directory/(trial+'-bootstrap.log'), retain=False)
                == {k:outcome['log'][k] for k in ('bytes', 'sha256')}, 'Actual saved bootstrap log changed')
        expected = reconcile_cpu('run', host['host_process_cpu_ns'],
                                 host['preflight_waited_child_cpu_ns'], outcome['subtree_cpu_ns'], entry)
        # Host accounting is sampled before final receipt construction. Store
        # and reconcile that exact sample; later host work is in scheduler CPU.
        require(host['accounting'] == expected, 'Complete envelope CPU differs')
        require(0 < entry['elapsed_ns'] <= host['elapsed_ns'], 'Host clock excludes entry work')
        rows[trial] = dict(elapsed_ns=host['elapsed_ns'], **expected)
    total = sum(r['nonnumerical_cpu_ns'] for r in rows.values())
    require(total <= program['controller_allowance_cpu_seconds']*10**9,
            'Aggregate complete controller allowance exceeded')
    return dict(entries=rows, nonnumerical_cpu_ns=total, overlapping_clocks_not_summed=True,
                final_writes_and_bootstrap_require_terminal_scheduler_accounting=True)
