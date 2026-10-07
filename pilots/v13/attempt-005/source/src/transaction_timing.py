"""External transaction observer with an explicit, nonrecursive receipt boundary.

The measured child must finish its transaction before exiting. Its full local
output tree is then verified and hashed. Observer receipt writes occur after
the stop timestamp. Reused receipts never become new latency observations.
"""
from __future__ import annotations

import os
import ctypes
import math
from pathlib import Path
import signal
import sys
import time

from .run_store import RunStore, canonical_json, digest, strict_json, read_completed
from .worker_control import WorkerLimits, run_limited
from .phase_budget import PhaseBudget

BOUNDARY = 'observer_source_validation_through_child_exit_controller_commits_cleanup_and_output_validation'
CACHE_MODES = ('fresh_transaction_os_cache_uncontrolled', 'resumed_transaction_os_cache_uncontrolled')
OUTPUT_CONTRACTS = ('model_only', 'canonical_state', 'comparison', 'sequence', 'quality_evaluation')


def _budget_details(config, limits):
    from .experiment_campaign import _phase_caps
    from .experiment_inventory import source_hashes
    if (type(config) is not dict or set(config) != {'protocol_path','protocol_sha256','phase'}
            or type(config['protocol_path']) is not str or not Path(config['protocol_path']).is_absolute()):
        raise ValueError('invalid measured phase-budget configuration')
    path = _safe_path(config['protocol_path'])
    raw = path.read_bytes()
    if digest(raw) != config['protocol_sha256']:
        raise ValueError('measured budget protocol hash differs')
    protocol = strict_json(raw)
    phase = config['phase']
    if phase not in ('software_test','feasibility','development','confirmation'):
        raise ValueError('invalid measured budget phase')
    if phase != 'software_test' and 'experiments_paused' in str(protocol.get('status','')):
        raise ValueError('protocol keeps research experiments paused')
    caps = _phase_caps({'entries':[{'phase':phase}]},protocol,limits)
    return {'directory':path.parent/('phase-cpu-budget-'+digest(raw)),
        'identity':{'protocol_sha256':digest(raw),'source_sha256':source_hashes(Path(__file__).resolve().parents[1])},
        'phase_cpu_seconds':caps}


def _budget_from_config(config, limits):
    details=_budget_details(config,limits)
    return PhaseBudget(details['directory'],identity=details['identity'],phase_cpu_seconds=details['phase_cpu_seconds'])


def verify_command_admission(protocol_sha256, phase, expected_command):
    """Validate a live exact-command allowance in the trusted local ledger."""
    from .experiment_inventory import source_hashes
    encoded = os.environ.get('CALIBRATION_PHASE_CPU_ADMISSION')
    if encoded is None:
        raise ValueError('research execution requires active phase CPU admission')
    admission = strict_json(encoded)
    fields = {'phase_budget_root','phase_budget_binding_sha256','attempt_id','phase','command','cwd'}
    if type(admission) is not dict or set(admission) != fields or admission['phase'] != phase:
        raise ValueError('invalid phase CPU admission')
    if admission['command'] != list(expected_command):
        raise ValueError('CPU admission does not bind this exact command')
    root = _safe_path(admission['phase_budget_root'])
    ledger = strict_json((root/'ledger.json').read_bytes())
    identity = {'protocol_sha256':protocol_sha256,
                'source_sha256':source_hashes(Path(__file__).resolve().parents[1])}
    budget = PhaseBudget(root,identity=identity,phase_cpu_seconds=ledger['binding']['phase_cpu_seconds'])
    if budget.identity_digest != admission['phase_budget_binding_sha256']:
        raise ValueError('CPU admission ledger binding differs')
    row = budget.snapshot()['attempts'].get(admission['attempt_id'])
    if row is None or row['state'] != 'reserved' or row['phase'] != phase:
        raise ValueError('CPU admission is missing, settled, or belongs to another phase')
    return dict(admission)


def verify_phase_admission(protocol_sha256, phase, manifest_path, output_path):
    """Require the literal model-only CLI command for research execution."""
    expected = [sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/run_model_fresh.py'),
                str(Path(manifest_path).absolute()),'--output',str(Path(output_path).absolute())]
    return verify_command_admission(protocol_sha256,phase,expected)


def _status_fields(path):
    return {line.split(':',1)[0]:line.split(':',1)[1].strip()
            for line in path.read_text().splitlines() if ':' in line}


def _owned_children():
    """Map direct children through procfs host/namespace PID coordinates."""
    own = _status_fields(Path('/proc/self/status'))
    host_pid = int(own['Pid'])
    namespace_index = len(own.get('NSpid',own['Pid']).split()) - 1
    children = []
    for path in Path('/proc').glob('[0-9]*/status'):
        try:
            fields = _status_fields(path)
            if int(fields['PPid']) == host_pid:
                pids = fields.get('NSpid',fields['Pid']).split()
                children.append(int(pids[namespace_index]))
        except (FileNotFoundError,ProcessLookupError):
            continue
    return tuple(sorted(children))


def _enable_subreaper():
    """Require an otherwise idle single-threaded measurement observer."""
    if len(tuple(Path('/proc/self/task').iterdir())) != 1 or _owned_children():
        raise ValueError('measurement observer requires one thread and no existing child processes')
    libc = ctypes.CDLL(None,use_errno=True)
    previous = ctypes.c_int()
    if libc.prctl(37,ctypes.byref(previous),0,0,0) != 0 or libc.prctl(36,1,0,0,0) != 0:
        raise OSError(ctypes.get_errno(),'cannot enable Linux child subreaper')
    return libc,previous.value


def _cleanup_adopted():
    """Kill and reap trusted orphan descendants, including new sessions."""
    usage = []
    deadline = time.monotonic() + 3
    while True:
        children = _owned_children()
        if not children:
            return usage
        for pid in children:
            try:
                os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                reaped, _, resources = os.wait4(pid,os.WNOHANG)
            except ChildProcessError:
                continue
            if reaped:
                usage.append({'pid':pid,'user_cpu_ns':math.ceil(resources.ru_utime*1_000_000_000),
                              'system_cpu_ns':math.ceil(resources.ru_stime*1_000_000_000),
                              'max_rss_kib':resources.ru_maxrss})
        if time.monotonic() >= deadline:
            raise RuntimeError('adopted descendant cleanup did not complete')
        time.sleep(0.01)


def transaction_source_hashes(repository=None):
    root = Path(repository or Path(__file__).resolve().parents[1])
    paths = sorted(root.glob('src/*.py')) + sorted(root.glob('scripts/*.py'))
    if not paths:
        raise ValueError('transaction sources are missing')
    result = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError('transaction sources must be regular files')
        result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def _safe_path(value):
    path = Path(value).absolute()
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError('transaction paths cannot contain symlinks')
    return path


def _nested(left, right):
    return left == right or left in right.parents or right in left.parents


def _verify_inputs(bindings):
    for name, expected in bindings.items():
        if type(name) is not str or not Path(name).is_absolute():
            raise ValueError('bound input paths must be absolute')
        path = _safe_path(name)
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError('transaction input hash mismatch')


def _snapshot(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError('transaction output directory is missing')
    answer = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('transaction output contains a symlink')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError('transaction output is not a regular file')
        raw = path.read_bytes()
        answer[path.relative_to(root).as_posix()] = {'bytes':len(raw), 'sha256':digest(raw)}
    return answer


def _validate_output(root, output_contract):
    """Verify the committed root receipt and every declared root artifact."""
    identity_path = root / 'identity.json'
    if identity_path.is_symlink() or not identity_path.is_file():
        raise ValueError('transaction identity is missing')
    identity = strict_json(identity_path.read_bytes())
    verified = read_completed(root, identity)
    if verified is None:
        raise ValueError('transaction completion receipt is missing or incomplete')
    outcome = verified.get('outcome', verified.get('status'))
    if isinstance(outcome, dict):
        outcome = outcome.get('status')
    if outcome != 'complete':
        raise ValueError('transaction receipt reports unsuccessful work')
    known = {'calibration-experiment-v1':'comparison', 'calibration-sequence-v1':'sequence',
             'calibration-model-fresh-v1':'model_only', 'isolated-child-result-v1':'canonical_state'}
    if verified.get('schema') == 'isolated-child-result-v1':
        if verified.get('role') == 'quality':
            known['isolated-child-result-v1'] = 'quality_evaluation'
        elif verified.get('role') not in ('setup','repair','indexed_fresh','direct_fresh'):
            raise ValueError('isolated child timing requires a supported role')
    schema_contract = known.get(verified.get('schema'))
    declared = verified.get('output_contract', schema_contract)
    if schema_contract is not None and declared != schema_contract:
        raise ValueError('child output contract contradicts its known schema')
    if declared is not None and declared != output_contract:
        raise ValueError('child output contract differs from timing manifest')
    return verified, declared == output_contract


def accounting_partition(start, call_start, call_end, end, worker):
    """Disjoint intervals exactly cover the declared observer clock boundary."""
    boundary = worker.get('timing_boundary') if isinstance(worker, dict) else None
    if boundary is None:
        points = [start, call_start, call_end, end]
        names = ['observer_preflight', 'worker_call_unpartitioned', 'observer_postflight']
    else:
        if boundary.get('clock') != 'time.perf_counter_ns_same_controller_process':
            raise ValueError('worker clock does not match enclosing controller')
        points = [start, call_start, boundary['start_ns'], boundary['cleanup_end_ns'], call_end, end]
        names = ['observer_preflight', 'worker_preparation', 'worker_execution_and_cleanup',
                 'worker_finalization_and_commit', 'observer_postflight']
        if boundary['cleanup_end_ns'] - boundary['start_ns'] != worker['outcome']['elapsed_wall_ns']:
            raise ValueError('worker elapsed time differs from its boundaries')
    if any(type(x) is not int for x in points) or any(a > b for a,b in zip(points,points[1:])):
        raise ValueError('timing boundaries are not ordered monotonic integers')
    spans = [{'name':name, 'start_offset_ns':a-start, 'end_offset_ns':b-start, 'wall_ns':b-a}
             for name,a,b in zip(names,points,points[1:])]
    if sum(span['wall_ns'] for span in spans) != end-start:
        raise ValueError('disjoint accounting does not equal enclosing wall time')
    return spans


def detailed_accounting_partition(spans, worker):
    """Refine cleanup when available; preserve the historical outer partition."""
    boundary = worker.get('timing_boundary') if isinstance(worker,dict) else None
    if boundary is None or 'cleanup_start_ns' not in boundary:
        return [dict(span) for span in spans]
    start, split, end = (boundary[key] for key in ('start_ns','cleanup_start_ns','cleanup_end_ns'))
    if any(type(value) is not int for value in (start,split,end)) or not start <= split <= end:
        raise ValueError('worker cleanup coordinates are not ordered')
    result=[]
    for span in spans:
        if span['name']!='worker_execution_and_cleanup':
            result.append(dict(span)); continue
        if span['wall_ns']!=end-start:
            raise ValueError('worker cleanup split differs from original elapsed time')
        offset=span['start_offset_ns']; midpoint=offset+split-start
        result.extend(({'name':'worker_execution_until_cleanup','start_offset_ns':offset,
                        'end_offset_ns':midpoint,'wall_ns':split-start},
                       {'name':'ordinary_process_cleanup','start_offset_ns':midpoint,
                        'end_offset_ns':span['end_offset_ns'],'wall_ns':end-split}))
    return result


def measure_command(command, transaction_root, observer_root, limits:WorkerLimits, *, identity,
                    source_sha256, input_sha256=None, cache_mode=CACHE_MODES[0],
                    output_contract='canonical_state', budget_config=None, cwd=None):
    """Run one trusted local CLI inside a fresh worker, then seal external timing.

    Fresh mode refuses any preexisting transaction directory. Resume mode must
    name an existing directory and never yields a fresh-latency observation.
    A repeated completed observer returns a verified archival receipt only.
    """
    if not isinstance(command,(list,tuple)) or not command or any(type(x) is not str or not x or '\0' in x for x in command):
        raise ValueError('command requires nonempty literal arguments')
    if not Path(command[0]).is_absolute():
        raise ValueError('command executable must be absolute')
    if cache_mode not in CACHE_MODES:
        raise ValueError('unknown measured cache mode')
    if output_contract not in OUTPUT_CONTRACTS:
        raise ValueError('unknown measured output contract')
    if not isinstance(limits,WorkerLimits):
        raise TypeError('WorkerLimits required')
    if type(source_sha256) is not dict or not source_sha256:
        raise ValueError('frozen transaction source hashes are required')
    input_sha256 = {} if input_sha256 is None else input_sha256
    if type(input_sha256) is not dict:
        raise ValueError('input hash bindings must be a mapping')
    transaction, observer = _safe_path(transaction_root), _safe_path(observer_root)
    work = _safe_path(cwd or Path.cwd())
    if _nested(transaction,observer):
        raise ValueError('transaction and observer trees must be disjoint')
    if not work.is_dir():
        raise ValueError('working directory is missing')
    binding = {'schema':'measured-transaction-identity-v1','command':list(command),'cwd':str(work),
               'transaction_root':str(transaction),'cache_mode':cache_mode,'limits':limits.payload(),
               'source_sha256':source_sha256,'identity':identity,'measurement_boundary':BOUNDARY}
    binding['output_contract'] = output_contract
    binding['input_sha256'] = input_sha256
    binding['budget'] = budget_config
    store = RunStore(observer,binding)
    previous = store.completed()
    if previous is not None:
        if transaction_source_hashes() != source_sha256:
            raise ValueError('sources differ from the saved timing receipt')
        _verify_inputs(input_sha256)
        if budget_config is not None:
            budget = _budget_from_config(budget_config,limits)
            attempt_id = previous.get('budget_attempt_id')
            if attempt_id is not None and budget.snapshot()['attempts'].get(attempt_id) != previous.get('budget_debit'):
                raise ValueError('saved measured budget debit differs from the phase ledger')
        saved = strict_json((store.root / previous['attempt'] / 'transaction-tree.json').read_bytes())
        current = _snapshot(transaction) if transaction.is_dir() else {}
        if saved != current:
            raise ValueError('transaction output differs from the saved timing receipt')
        saved_worker = strict_json((store.root / previous['attempt'] / 'worker-tree.json').read_bytes())
        worker_root = store.root / previous['attempt'] / 'worker'
        current_worker = _snapshot(worker_root) if worker_root.is_dir() else {}
        if saved_worker != current_worker:
            raise ValueError('worker diagnostics differ from the saved timing receipt')
        return {'reused_receipt':True,'new_latency_observation':False,'receipt':previous}
    store.claim()
    worker = None
    failure = None
    child_receipt = None
    before = {}
    after = {}
    worker_tree = {}
    completed = False
    contract_verified = False
    caught_interrupt = None
    subreaper = None
    adopted_usage = []
    adopted_cleanup_windows = []
    budget = None
    start = time.perf_counter_ns()
    call_start = start
    call_end = start
    record = {'schema':'measured-transaction-receipt-v1','status':'running','cache_mode':cache_mode,
              'output_contract':output_contract,
              'measurement_boundary':BOUNDARY,'source_sha256':source_sha256,
              'observer_receipt_excluded':True,'outer_wrapper_cpu_not_debited_to_child_phase_budget':True,
              'execution_scope':'fresh trusted controller process; OS caches uncontrolled',
              'outcome':{'status':'incomplete'}}
    from .instrumentation import instrumentation_state
    record['instrumentation_state'] = instrumentation_state()
    try:
        store.write_artifact('request.json',canonical_json(binding))
        store.write_status(record)
        if transaction_source_hashes() != source_sha256:
            raise ValueError('transaction sources differ from frozen hashes')
        _verify_inputs(input_sha256)
        if budget_config is not None:
            budget = _budget_from_config(budget_config,limits)
        if cache_mode == CACHE_MODES[0]:
            if transaction.exists():
                raise ValueError('fresh measurement refuses preexisting transaction outputs')
        else:
            if not transaction.is_dir():
                raise ValueError('resumed measurement requires existing transaction outputs')
            before = _snapshot(transaction)
        subreaper = _enable_subreaper()
        call_start = time.perf_counter_ns()
        try:
            worker = run_limited(command,store.attempt/'worker',limits,
                identity={'transaction_identity_sha256':store.identity_digest},cwd=work,
                phase_budget=budget,phase=None if budget is None else budget_config['phase'])
        finally:
            cleanup_begin=time.perf_counter_ns()
            try:
                adopted_usage.extend(_cleanup_adopted())
            finally:
                cleanup_finish=time.perf_counter_ns()
                adopted_cleanup_windows.append({'start_ns':cleanup_begin,'end_ns':cleanup_finish,
                    'wall_ns':cleanup_finish-cleanup_begin})
        call_end = time.perf_counter_ns()
        if worker['outcome']['status'] != 'complete':
            raise ValueError('measured worker did not finish successfully: '+worker['outcome']['kind'])
        if transaction_source_hashes() != source_sha256:
            raise ValueError('transaction sources changed during execution')
        _verify_inputs(input_sha256)
        child_receipt, contract_verified = _validate_output(transaction,output_contract)
        after = _snapshot(transaction)
        completed = True
    except BaseException as exc:
        failure = {'type':type(exc).__name__,'message':str(exc)}
        if call_start == start:
            call_start = call_end = time.perf_counter_ns()
        elif call_end < call_start:
            call_end = time.perf_counter_ns()
        if transaction.is_dir():
            try:
                after = _snapshot(transaction)
            except (ValueError,OSError) as snapshot_error:
                failure['snapshot_failure'] = str(snapshot_error)
        if isinstance(exc,(KeyboardInterrupt,SystemExit)):
            caught_interrupt = exc
    finally:
        if subreaper is not None:
            cleanup_begin=time.perf_counter_ns()
            try:
                adopted_usage.extend(_cleanup_adopted())
            except (ValueError,OSError,RuntimeError) as exc:
                completed = False
                failure = {'type':type(exc).__name__,'message':str(exc)}
            finally:
                if subreaper[0].prctl(36,subreaper[1],0,0,0) != 0:
                    completed = False
                    failure = {'type':'OSError','message':'cannot restore child subreaper setting'}
                cleanup_finish=time.perf_counter_ns()
                adopted_cleanup_windows.append({'start_ns':cleanup_begin,'end_ns':cleanup_finish,
                    'wall_ns':cleanup_finish-cleanup_begin})
        try:
            worker_root = store.attempt / 'worker'
            worker_tree = _snapshot(worker_root) if worker_root.is_dir() else {}
        except (ValueError,OSError) as exc:
            completed = False
            failure = {'type':type(exc).__name__,'message':str(exc)}
        record['instrumentation_state_end'] = instrumentation_state()
        if record['instrumentation_state']['mode'] == 'clean':
            from .instrumentation import require_clean_instrumentation
            try:
                require_clean_instrumentation()
            except (ValueError,RuntimeError) as exc:
                completed = False
                failure = {'type':type(exc).__name__,'message':str(exc)}
        end = time.perf_counter_ns()
        try:
            spans = accounting_partition(start,call_start,call_end,end,worker)
            detail_spans = detailed_accounting_partition(spans,worker)
        except (ValueError,KeyError,TypeError) as exc:
            completed = False
            failure = {'type':type(exc).__name__,'message':str(exc)}
            spans = accounting_partition(start,start,end,end,None)
            detail_spans = [dict(span) for span in spans]
        fresh = cache_mode == CACHE_MODES[0]
        record.update(status='complete',outcome={'status':'complete' if completed else 'incomplete',
                      'failure':failure}, observed_wall_ns=end-start,
                      complete_transaction_wall_ns=end-start if completed else None,
                      child_output_contract_verified=contract_verified,
                      eligible_fresh_transaction_latency=completed and fresh and contract_verified,
                      timing_spans=spans, accounting_sum_ns=sum(x['wall_ns'] for x in spans),
                      timing_detail_spans=detail_spans,
                      observer_clock={'clock':'time.perf_counter_ns_system_monotonic',
                                      'start_ns':start,'end_ns':end,'wall_ns':end-start},
                      adopted_cleanup_windows=adopted_cleanup_windows,
                      worker_outcome=None if worker is None else worker['outcome'],
                      worker_resource_usage=None if worker is None else worker.get('resource_usage'),
                      adopted_descendant_resource_usage=adopted_usage,
                      budget_attempt_id=None if worker is None else worker.get('budget_attempt_id'),
                      budget_debit=None if worker is None else worker.get('budget_debit'),
                      budget_scope='enclosing child allowance; nested child debits may duplicate usage' if budget else
                                   'no new allowance; child executor must enforce its declared research budgets',
                      transaction_result_sha256=after.get('result.json',{}).get('sha256'),
                      resumed_preexisting_file_count=len(before), final_file_count=len(after),
                      terminal_observer_writes='excluded: tree snapshots, final receipt and observer lock release')
        # These immutable diagnostics occur AFTER the stop clock. They do not
        # pretend to include the act of reporting their own timing.
        try:
            store.write_artifact('transaction-before.json',canonical_json(before))
            store.write_artifact('transaction-tree.json',canonical_json(after))
            store.write_artifact('worker-tree.json',canonical_json(worker_tree))
            record = store.finish(record)
        finally:
            store.close()
    if caught_interrupt is not None:
        raise caught_interrupt
    return {'reused_receipt':False,'new_latency_observation':completed and fresh and contract_verified,'receipt':record}


def verify_observer_receipt(observer_root):
    """Read-only verification; missing or unfinished observers never execute."""
    root = _safe_path(observer_root)
    if not root.is_dir():
        raise ValueError('observer archive is missing')
    identity = strict_json((root/'identity.json').read_bytes())
    saved = read_completed(root,identity)
    if saved is None:
        raise ValueError('observer archive is not sealed')
    request = strict_json((root/saved['attempt']/'request.json').read_bytes())
    if request != identity or identity.get('measurement_boundary') != BOUNDARY:
        raise ValueError('observer request differs from its identity')
    # This path must not instantiate a budget writer or invoke an executor,
    # even when the original receipt is already sealed.
    verified=saved
    if transaction_source_hashes()!=identity['source_sha256']:
        raise ValueError('sources differ from the saved timing receipt')
    _verify_inputs(identity['input_sha256'])
    if identity['budget'] is not None:
        from .phase_budget import read_budget_snapshot
        details=_budget_details(identity['budget'],WorkerLimits.from_payload(identity['limits']))
        budget=read_budget_snapshot(**details)
        if budget.get('status')!='verified' or type(budget.get('attempts')) is not dict:
            raise ValueError('saved measured phase ledger is unavailable')
        attempt=verified.get('budget_attempt_id')
        if attempt is not None and budget['attempts'].get(attempt)!=verified.get('budget_debit'):
            raise ValueError('saved measured budget debit differs from the phase ledger')
    for artifact,directory in (('transaction-tree.json',_safe_path(identity['transaction_root'])),
                               ('worker-tree.json',root/verified['attempt']/'worker')):
        recorded=strict_json((root/verified['attempt']/artifact).read_bytes())
        current=_snapshot(directory) if directory.is_dir() else {}
        if recorded!=current:
            raise ValueError('saved measured output or worker artifact tree changed')
    for key in ('source_sha256','cache_mode','output_contract','measurement_boundary'):
        if verified[key] != identity[key]:
            raise ValueError('observer convenience field differs from request: '+key)
    spans = verified['timing_spans']; cursor = 0
    for span in spans:
        if (span['start_offset_ns'] != cursor or type(span['wall_ns']) is not int or span['wall_ns'] < 0
                or span['end_offset_ns'] != cursor + span['wall_ns']):
            raise ValueError('observer time partition differs')
        cursor = span['end_offset_ns']
    if cursor != verified['observed_wall_ns'] or cursor != verified['accounting_sum_ns']:
        raise ValueError('observer accounting total differs')
    worker=None
    if 'timing_detail_spans' in verified:
        worker_root=root/verified['attempt']/'worker'
        worker=None
        if (worker_root/'identity.json').is_file():
            worker_identity=strict_json((worker_root/'identity.json').read_bytes())
            worker=read_completed(worker_root,worker_identity)
        if verified['timing_detail_spans']!=detailed_accounting_partition(spans,worker):
            raise ValueError('observer cleanup detail differs from worker evidence')
    if 'observer_clock' in verified:
        coordinates=verified['observer_clock']
        if (coordinates.get('clock')!='time.perf_counter_ns_system_monotonic' or
                any(type(coordinates.get(key)) is not int for key in ('start_ns','end_ns','wall_ns')) or
                coordinates['end_ns']-coordinates['start_ns']!=cursor or coordinates['wall_ns']!=cursor):
            raise ValueError('observer absolute clock differs from enclosing interval')
        boundary=worker.get('timing_boundary') if worker is not None else None
        if boundary is not None:
            matching=[span for span in spans if span['name']=='worker_execution_and_cleanup']
            if (len(matching)!=1 or coordinates['start_ns']+matching[0]['start_offset_ns']!=boundary['start_ns']
                    or coordinates['start_ns']+matching[0]['end_offset_ns']!=boundary['cleanup_end_ns']):
                raise ValueError('observer and worker absolute clock origins differ')
        previous_end=coordinates['start_ns']
        for window in verified.get('adopted_cleanup_windows',[]):
            if (any(type(window.get(key)) is not int for key in ('start_ns','end_ns','wall_ns')) or
                    not previous_end <= window['start_ns'] <= window['end_ns'] <= coordinates['end_ns'] or
                    window['wall_ns']!=window['end_ns']-window['start_ns']):
                raise ValueError('observer adopted cleanup windows overlap or exceed its clock')
            previous_end=window['end_ns']
    complete = verified['outcome']['status'] == 'complete'
    if verified['complete_transaction_wall_ns'] != (cursor if complete else None):
        raise ValueError('observer complete time differs')
    if complete:
        _, contract = _validate_output(Path(identity['transaction_root']),identity['output_contract'])
        if not contract or verified['child_output_contract_verified'] is not True:
            raise ValueError('observer output contract is unverified')
    eligible = complete and identity['cache_mode'] == CACHE_MODES[0] and verified['child_output_contract_verified']
    if verified['eligible_fresh_transaction_latency'] != eligible:
        raise ValueError('observer eligibility differs')
    return verified


def run_measured_manifest(path, observer_root):
    path = _safe_path(path)
    raw = path.read_bytes()
    request = strict_json(raw)
    fields = {'schema','command','transaction_root','cwd','cache_mode','output_contract','limits',
              'source_sha256','input_sha256','budget','identity'}
    if type(request) is not dict or set(request) != fields or request['schema'] != 'measured-transaction-v1':
        raise ValueError('invalid measured transaction manifest')
    if raw != canonical_json(request):
        raise ValueError('measured transaction manifest must be canonical JSON')
    # Paths are absolute, so a moved manifest cannot change the transaction.
    for name in ('transaction_root','cwd'):
        if type(request[name]) is not str or not Path(request[name]).is_absolute():
            raise ValueError('measured manifest paths must be absolute')
    return measure_command(request['command'],request['transaction_root'],observer_root,
        WorkerLimits.from_payload(request['limits']),identity={'manifest_sha256':digest(raw),'user':request['identity']},
        source_sha256=request['source_sha256'],cache_mode=request['cache_mode'],
        input_sha256=request['input_sha256'],output_contract=request['output_contract'],
        budget_config=request['budget'],cwd=request['cwd'])


def build_role_measurement(request_path, limits:WorkerLimits, *, cache_mode=CACHE_MODES[0]):
    """Wrap ONE existing isolated-child request without including other arms.

    Its output directory must be absent for fresh measurement. The child still
    verifies its own pinned sources and request. This helper does not validate
    model equality against another method or charge that research comparison
    to the production-style canonical-state transaction.
    """
    path = _safe_path(request_path)
    raw = path.read_bytes()
    request = strict_json(raw)
    if (type(request) is not dict or request.get('schema') != 'isolated-child-request-v1'
            or request.get('role') not in ('setup','repair','indexed_fresh','direct_fresh')
            or raw != canonical_json(request)):
        raise ValueError('requires a canonical supported isolated-child request')
    output = request.get('output')
    if type(output) is not str or not Path(output).is_absolute():
        raise ValueError('isolated child output must be absolute')
    if not isinstance(limits,WorkerLimits) or cache_mode not in CACHE_MODES:
        raise ValueError('invalid measured role execution controls')
    from .experiment_runner import _read_json, _referenced_json, _local
    manifest_path = _safe_path(request['manifest_path'])
    manifest, manifest_raw = _read_json(manifest_path)
    if digest(manifest_raw) != request['manifest_sha256']:
        raise ValueError('isolated role run manifest hash differs')
    protocol, protocol_raw = _referenced_json(manifest_path.parent,manifest['protocol'])
    protocol_path = _local(manifest_path.parent,manifest['protocol']['path'])
    phase = manifest['phase']
    budget = None if phase == 'software_test' else {'protocol_path':str(protocol_path),
             'protocol_sha256':digest(protocol_raw),'phase':phase}
    return {'schema':'measured-transaction-v1',
            'command':[sys.executable,'-m','src.isolated_comparison','--child',str(path)],
            'transaction_root':output,'cwd':str(Path(__file__).resolve().parents[1]),
            'cache_mode':cache_mode,'output_contract':'canonical_state','limits':limits.payload(),
            'source_sha256':transaction_source_hashes(),'input_sha256':{str(path):digest(raw),
                str(manifest_path):digest(manifest_raw),str(protocol_path):digest(protocol_raw)},
            'budget':budget,
            'identity':{'isolated_role':request['role'],'isolated_request_sha256':digest(raw)}}
