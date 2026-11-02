"""New one-use host envelope: storage admission, bounded log and complete clock.

Runs only inside the separately registered Slurm namespace. It does not submit
jobs. A missing/refused storage check cannot dispatch the container. All timings
overlap: never add this envelope's CPU to the contained worker CPU.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import sys
import time

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_v80.io import info, json_read, require, write
from research_v88.storage import capture, evaluate
from research_v89.config import ROOT, RUN, TRIALS, design
from research_v89.storage_plan import requests

LOG_BYTES = 64*2**20


def cpu_ns(usage):
    return round((usage.ru_utime+usage.ru_stime)*10**9)


def admit(program, name):
    requested = requests(program['storage_plan'], program['source_inventory'],
                         program['source_archive_bytes'], name)
    snapshot = capture(requested)
    admission = evaluate(requested, snapshot['observations'], snapshot['quota_text'], snapshot['group_reports'])
    return requested, snapshot, admission


def collect(command, path, wall_seconds, on_abort=None):
    """Keep every byte up to the cap; overflow kills the group and fails the run.

    The prefix is explicitly labelled incomplete on overflow. It can never be
    passed as a complete successful log. No file is reopened or retried.
    """
    require(type(wall_seconds) is int and wall_seconds > 0, 'Positive wall cap required')
    deadline = time.monotonic()+wall_seconds
    saved = 0
    seen = 0
    failure = None
    process = None
    abort_called = False
    sha = hashlib.sha256()
    with Path(path).open('xb') as log, selectors.DefaultSelector() as selector:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True, cwd=ROOT)
        selector.register(process.stdout, selectors.EVENT_READ)
        reaped = None
        try:
            while selector.get_map() or reaped is None:
                if time.monotonic() >= deadline and failure is None:
                    failure = 'wall_timeout'
                if failure is not None:
                    if not abort_called and on_abort is not None:
                        abort_called = True
                        log.flush()
                        os.fsync(log.fileno())
                        on_abort(failure)
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                for key, _ in selector.select(0.05):
                    blob = os.read(key.fileobj.fileno(), 65536)
                    if not blob:
                        selector.unregister(key.fileobj)
                        continue
                    seen += len(blob)
                    prefix = blob[:max(0, LOG_BYTES-saved)]
                    log.write(prefix)
                    sha.update(prefix)
                    saved += len(prefix)
                    if seen > LOG_BYTES:
                        failure = 'log_limit_exceeded'
                if reaped is None:
                    pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                    if pid:
                        reaped = (os.waitstatus_to_exitcode(status), cpu_ns(usage))
                        process.returncode = reaped[0]
                # Descendants may retain a pipe after the direct process exits.
                # They share the new session; deadline/overflow kills that group.
            log.flush()
            os.fsync(log.fileno())
        finally:
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                _, status, _ = os.wait4(process.pid, 0)
                process.returncode = os.waitstatus_to_exitcode(status)
            process.stdout.close()
    return dict(exit_code=reaped[0], subtree_cpu_ns=reaped[1], failure=failure,
                log=dict(bytes=saved, sha256=sha.hexdigest(), observed_bytes=seen,
                         complete=failure != 'log_limit_exceeded'))


def cancel_current(name, expected, reason):
    """One request for the NEW current allocation, never an old or sibling job.

    Workers create their own process groups. Killing only the container group
    cannot promise their cleanup. Slurm owns the whole allocation; its actual
    terminal state must still be inspected after this cancellation request.
    """
    job = os.environ.get('SLURM_JOB_ID', '')
    require(job.isdigit() and reason in ('wall_timeout', 'log_limit_exceeded'),
            'Exact current allocation and failure reason required')
    start = json_read(RUN/(name+'-host-start.json'))
    require(start['job_id'] == job and start['program_sha256'] == expected,
            'Cancellation cannot target another allocation')
    write(RUN/(name+'-abort-intent.json'), dict(job_id=job, program_sha256=expected,
          reason=reason, cancellation_scope='only_this_new_registered_allocation',
          completion_unknown=True), maximum=64*2**20)
    environment = {k:v for k,v in os.environ.items()
                   if not k.startswith('SCANCEL_') and k != 'SLURM_CLUSTERS'}
    # No --signal or --batch: cancel the allocation, including all of its steps.
    # This may terminate the host before a response can be sealed. No retry.
    result = subprocess.run(['scancel', job], capture_output=True, text=True,
                            timeout=15, env=environment)
    write(RUN/(name+'-abort-response.json'), dict(job_id=job, exit=result.returncode,
          stdout=result.stdout[:32768], stderr=result.stderr[:32768],
          response_complete=len(result.stdout) <= 32768 and len(result.stderr) <= 32768,
          terminal_cleanup_verified=False), maximum=64*2**20)


def reconcile_cpu(operation, own_ns, preflight_children_ns, child_ns, entry):
    """Partition a measured subtree; do not add overlapping child counters."""
    require(all(type(x) is int and x >= 0 for x in (own_ns, preflight_children_ns, child_ns)),
            'Nonnegative host CPU observations required')
    numerical = entry['sealed_worker_cpu_ns'] if operation == 'run' else 0
    require(type(numerical) is int and type(entry['waited_child_cpu_ns']) is int
            and 0 <= numerical <= entry['waited_child_cpu_ns'] <= child_ns,
            'Numerical child CPU must be contained in host subtree')
    require(type(entry['process_cpu_ns']) is int and entry['process_cpu_ns'] >= 0
            and entry['process_cpu_ns']+numerical <= child_ns,
            'Entry CPU must be contained in host subtree')
    total = own_ns+preflight_children_ns+child_ns
    controller = total-numerical
    ceiling = 602 if operation in ('run', 'checks') else 7201 if operation == 'primary' else 3601
    require(controller <= ceiling*10**9, 'Complete host/controller CPU allowance exceeded')
    return dict(envelope_cpu_ns=total, contained_numerical_cpu_ns=numerical,
                nonnumerical_cpu_ns=controller, nonnumerical_cap_seconds=ceiling,
                overlapping_clocks_not_summed=True, final_host_write_requires_scheduler_accounting=True)


def main(operation, expected, *arguments):
    tick = time.perf_counter_ns()
    before_children = cpu_ns(resource.getrusage(resource.RUSAGE_CHILDREN))
    require(sys.platform == 'linux' and Path(__file__).resolve() == RUN/'research_v89/host.py'
            and os.environ.get('SLURM_JOB_ID', '').isdigit(), 'Literal registered Slurm host envelope required')
    require(operation in ('checks', 'run', 'primary', 'supplemental'), 'Unknown operation')
    require(len(arguments) == (1 if operation == 'run' else 0), 'Wrong operation arguments')
    name = arguments[0] if operation == 'run' else operation
    require(operation != 'run' or name in TRIALS, 'Unknown trial')
    require(not (RUN/(name+'-host-start.json')).exists()
            and not (RUN/(name+'-host.json')).exists(), 'Consumed host attempt; no retry')
    resource.setrlimit(resource.RLIMIT_AS, (16*2**30,)*2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (2*2**30,)*2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    # Preserve child hard ceilings; complete nonnumerical aggregate is checked
    # after wait4. A timeout/limit remains an unsuccessful consumed allocation.
    resource.setrlimit(resource.RLIMIT_CPU, (600, 16802))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    p = json_read(RUN/'program.json')
    require(info((RUN/'program.json').read_bytes())['sha256'] == expected
            and all(p.get(k) == v for k, v in design().items()), 'Registered recovery program differs')
    require(json_read(RUN/'registration.json') == dict(program_sha256=expected), 'Separate registry required')
    requested, snapshot, admission = admit(p, name)
    # Refusal above has no new project write or child dispatch. Bootstrap stderr
    # remains in its separately budgeted Slurm log if this receipt cannot exist.
    write(RUN/(name+'-host-start.json'), dict(program_sha256=expected, operation=operation,
          arguments=list(arguments), job_id=os.environ['SLURM_JOB_ID'],
          started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
          requests=requested, snapshot=snapshot, admission=admission), maximum=64*2**20)
    preflight_children = cpu_ns(resource.getrusage(resource.RUSAGE_CHILDREN))-before_children
    wall = TRIALS[name]['wall_seconds']+600 if operation == 'run' else 600 if operation == 'checks' else p[operation+'_audit_caps']['wall']
    # Subtract already elapsed admission/setup time from the original wall cap.
    remaining = wall-(time.perf_counter_ns()-tick+10**9-1)//10**9
    require(remaining > 0, 'Storage admission consumed the original wall allowance')
    outcome = collect(['/bin/bash', str(RUN/'research_v89/container.sh'), operation, expected, *arguments],
                      RUN/(name+'-bootstrap.log'), remaining,
                      on_abort=lambda reason: cancel_current(name, expected, reason))
    error = None
    accounting = None
    accounting_own = None
    try:
        entry = json_read(RUN/('software-completion.json' if operation == 'checks' else name+'-entry.json'))
        require(outcome['exit_code'] == 0 and outcome['failure'] is None
                and entry['status'] == 'complete' and entry['error'] is None
                and entry['program_sha256'] == expected and entry['job_id'] == os.environ['SLURM_JOB_ID'],
                'Contained allocation did not complete successfully')
        accounting_own = time.process_time_ns()
        accounting = reconcile_cpu(operation, accounting_own, preflight_children,
                                   outcome['subtree_cpu_ns'], entry)
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:4096])
    receipt = dict(status='complete' if error is None else 'failed', error=error,
                   program_sha256=expected, job_id=os.environ['SLURM_JOB_ID'],
                   operation=operation, arguments=list(arguments), outcome=outcome, accounting=accounting,
                   elapsed_ns=time.perf_counter_ns()-tick, host_process_cpu_ns=accounting_own if accounting_own is not None else time.process_time_ns(),
                   preflight_waited_child_cpu_ns=preflight_children,
                   finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   clock_scope='Host main through admission, container startup, entry, worker sealing and shutdown; host interpreter/import and shell startup plus final host receipt write additionally in scheduler accounting')
    write(RUN/(name+'-host.json'), receipt, maximum=64*2**20)
    require(error is None, 'One-use host envelope failed; inspect, never retry')


if __name__ == '__main__':
    main(*sys.argv[1:])
