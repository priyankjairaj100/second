"""Read-only final host closure, after every NEW allocation is terminal.

No submission, ledger mutation or successful inference from software tests.
The old failed reservation remains charged even after this recovery succeeds.
"""
import datetime
import json
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_v83.terminal import Inputs, actual_seal
from research_v83.accounting import scheduler_rows
from research_v89.config import ROOT, RUN, design
from research_v89.recovery import verify_failure_bindings
from research_v89.host import reconcile_cpu
from research_v86.admission import EXPECTED, terminal_disposition
from research_v80.io import require
from src.run_store import canonical_json, digest


def cost(host, entry, scheduler, program, operation, worker=None):
    sha = digest(canonical_json(program))
    require(host['status'] == entry['status'] == 'complete' and host['error'] is entry['error'] is None
            and host['program_sha256'] == entry['program_sha256'] == sha
            and host['job_id'] == entry['job_id'] == scheduler['job_id']
            and host['operation'] == entry['operation'] == operation,
            'Successful bound host/entry/scheduler receipts required')
    require(host['outcome']['exit_code'] == 0 and host['outcome']['failure'] is None
            and host['outcome']['log']['complete'] is True, 'Incomplete host outcome')
    expected = reconcile_cpu(operation, host['host_process_cpu_ns'],
                             host['preflight_waited_child_cpu_ns'], host['outcome']['subtree_cpu_ns'], entry)
    require(host['accounting'] == expected, 'Host CPU partition differs')
    numerical = 0
    if operation == 'run':
        require(worker is not None and worker['outcome']['status'] == 'complete'
                and worker['budget_debit']['state'] == 'settled', 'Actual settled numerical worker required')
        numerical = worker['resource_usage']['total_cpu_ns']
        require(numerical == entry['sealed_worker_cpu_ns'] == worker['budget_debit']['observed_cpu_ns'],
                'Actual sealed worker differs from envelope')
    require(type(entry['elapsed_ns']) is int and type(host['elapsed_ns']) is int
            and 0 < entry['elapsed_ns'] <= host['elapsed_ns'] <= (scheduler['elapsed_seconds']+1)*10**9,
            'Scheduler wall time cannot contain complete transaction')
    lower = scheduler['cpu_ns']
    upper = lower+scheduler['quantum_ns']
    require(upper >= expected['envelope_cpu_ns'], 'Scheduler CPU cannot contain complete host envelope')
    # Use the conservative displayed upper endpoint, not an invented precise
    # scheduler value. Final writes and shell startup remain charged here.
    nonnumerical_upper = upper-numerical
    require(0 <= nonnumerical_upper <= expected['nonnumerical_cap_seconds']*10**9,
            'Scheduler-observed complete nonnumerical CPU exceeds preserved cap')
    return dict(job_id=entry['job_id'], scheduler_cpu_ns=lower,
                scheduler_reporting_quantum_ns=scheduler['quantum_ns'],
                contained_numerical_cpu_ns=numerical, nonnumerical_upper_cpu_ns=nonnumerical_upper,
                host_envelope_cpu_ns=expected['envelope_cpu_ns'], overlapping_clocks_not_summed=True)


def command(args):
    return subprocess.check_output(args, text=True, timeout=20)


def main(expected):
    require(sys.platform == 'linux' and platform.node() == 'csis.mn1'
            and Path(__file__).resolve() == RUN/'research_v89/terminal.py', 'Literal pinned host reporter required')
    resource.setrlimit(resource.RLIMIT_CPU, (300, 301))
    resource.setrlimit(resource.RLIMIT_AS, (2*2**30,)*2)
    started = time.perf_counter_ns()
    cpu = time.process_time_ns()
    require(command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).strip() == design()['numerical_checkout']
            and not command(['git', '-C', str(ROOT), 'status', '--short']).strip(), 'Frozen clean checkout required')
    inputs = Inputs()
    p = inputs.json(RUN/'program.json')
    require(digest(canonical_json(p)) == expected and all(p.get(k) == v for k, v in design().items()),
            'Exact recovery program required')
    require(inputs.json(RUN/'registration.json') == dict(program_sha256=expected), 'Separate registry differs')
    carry = verify_failure_bindings(p)
    old_raw = command(['sacct', '-nP', '-j', ','.join(EXPECTED),
                       '--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'])
    old = terminal_disposition(old_raw)
    jobs = {}
    for mode in ('checks', 'chain'):
        chain = inputs.json(RUN/(mode+'-released-chain.json'))
        require(chain['program_sha256'] == expected, 'Released chain program differs')
        for row in chain['jobs']:
            require(row['name'] not in jobs and row['job_id'] not in EXPECTED, 'Duplicate or old allocation reused')
            require(row == inputs.json(RUN/(row['name']+'-submission.json')), 'Actual held submission changed')
            release = inputs.json(RUN/(row['name']+'-release.json'))
            require(release == dict(program_sha256=expected, job_id=row['job_id'], released=True), 'One-use release differs')
            jobs[row['name']] = dict(job_id=row['job_id'], name='second89-'+row['name'])
    require(set(jobs) == {'checks', 'primary', 'supplemental', *p['trial_order']}, 'Complete finite allocation set required')
    raw = command(['sacct', '-nP', '-j', ','.join(r['job_id'] for r in jobs.values()),
                   '--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'])
    scheduled = scheduler_rows(raw, jobs)
    costs = {}
    debits = set()
    for name in jobs:
        trial = name in p['trials']
        operation = 'run' if trial else name
        entry = inputs.json(RUN/('software-completion.json' if name == 'checks' else name+'-entry.json'))
        host = inputs.json(RUN/(name+'-host.json'))
        worker = actual_seal(inputs, RUN/name/'worker') if trial else None
        require(host['arguments'] == entry['arguments'] == ([name] if trial else []), 'Allocation argument identity differs')
        if worker:
            require(worker['budget_attempt_id'] not in debits, 'Worker debit duplicated')
            debits.add(worker['budget_attempt_id'])
        if name == 'checks':
            require(entry['tests'] == p['expected_tests'] and entry['skipped'] == entry['failures'] == entry['errors'] == 0,
                    'Actual exact-count Linux gate required')
        costs[name] = cost(host, entry, scheduled[name], p, operation, worker)
        inputs.read(RUN/(name+'-bootstrap.log'), {k:host['outcome']['log'][k] for k in ('bytes', 'sha256')}, retain=False)
        slurm_log = inputs.read(RUN/(name+'-'+jobs[name]['job_id']+'.log'), retain=False)
        require(slurm_log['bytes'] <= 4*2**20, 'Observed external Slurm log exceeds conservative allowance')
    audits = {}
    for name in ('primary', 'supplemental'):
        audit = inputs.json(RUN/(name+'-audit.json'))
        require(audit['status'] == 'verified' and audit['program_sha256'] == expected, 'Actual saved audit required')
        for path, e in audit['inputs'].items():
            inputs.read(path, e, retain=False)
        audits[name] = audit
    primary, secondary = audits['primary'], audits['supplemental']
    require(secondary['evidence']['primary_receipt_sha256'] == inputs.files[str(RUN/'primary-audit.json')]['sha256']
            and secondary['evidence']['eight_actual_model_pairs_equal'] is True
            and primary['budget'] == secondary['budget'] and primary['host_envelopes'] == secondary['host_envelopes'],
            'Both completed audit results must agree')
    require(len(primary['evidence']['comparisons']) == 8
            and all(r['actual_bytes_equal'] is True and r['actual_model_bytes_equal'] is True
                    for r in primary['evidence']['comparisons']), 'Eight complete empirical comparisons required')
    budget = primary['budget']
    require(debits == set(budget['attempts']) and not budget['reserved_unknown_attempts']
            and not budget['reservation_overrun_attempts'] and not any(budget['over_cap'].values()), 'Complete settled new ledger required')
    for group in ('prior_sources', 'new_sources', 'dependency_files', 'historical_ledgers'):
        for path, e in p[group].items():
            inputs.read(path, e, retain=False)
    controller_upper = sum(costs[t]['nonnumerical_upper_cpu_ns'] for t in p['trial_order'])
    require(controller_upper <= 6020*10**9 and controller_upper+602*10**9 <= 7224*10**9,
            'Complete new controller plus old reserved cost exceeds ceiling')
    inputs.unchanged()
    report = dict(schema='recovery-terminal-v89', status='verified', program_sha256=expected,
                  evidence=dict(actual_audits_and_inputs_reverified=True, comparison_count=8,
                                quality_evaluation=False, transfer=False, confirmation=False),
                  costs=costs, preserved_failure=old, carried_reservations=carry,
                  scheduler_raw=raw, old_scheduler_raw=old_raw, inputs=inputs.files,
                  overlapping_clocks_not_summed=True,
                  readonly_review_cost_outside_experiment=True,
                  readonly_host_review_cpu_ns=time.process_time_ns()-cpu,
                  readonly_host_review_elapsed_ns=time.perf_counter_ns()-started,
                  captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    print(json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False))


if __name__ == '__main__':
    main(*sys.argv[1:])
