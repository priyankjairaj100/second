"""Opt-in endpoint diagnostics for the actual local reference runners.

The audit observes standard Fraction allocation returns without replacing any
arithmetic function. It reports constructed rational endpoints, not every
integer intermediate, physical live-rational memory, or clean latency.
Only the calling thread and process are profiled. Child execution is uncovered.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from fractions import Fraction
import gc
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import sys
import _thread
import threading
import time
import tracemalloc


def _positive(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(f'{name} must be a positive built-in integer')
    return value


def _empty():
    return {'fraction_objects': 0, 'numerator_bits_sum': 0, 'denominator_bits_sum': 0,
            'maximum_numerator_bits': 0, 'maximum_denominator_bits': 0, 'zero_numerators': 0}


def _add(summary, value):
    # Read the immutable slots directly; no new Fraction is constructed here.
    numerator, denominator = value._numerator, value._denominator
    nb, db = abs(numerator).bit_length(), denominator.bit_length()
    summary['fraction_objects'] += 1
    summary['numerator_bits_sum'] += nb
    summary['denominator_bits_sum'] += db
    summary['maximum_numerator_bits'] = max(summary['maximum_numerator_bits'], nb)
    summary['maximum_denominator_bits'] = max(summary['maximum_denominator_bits'], db)
    summary['zero_numerators'] += int(numerator == 0)


def _rss():
    high = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    high = int(high if sys.platform == 'darwin' else high * 1024)
    current, reason = None, None
    try:
        fields = Path('/proc/self/statm').read_text().split()
        current = int(fields[1]) * os.sysconf('SC_PAGE_SIZE')
    except (OSError, ValueError, IndexError) as exc:
        reason = type(exc).__name__
    return {'current_rss_bytes': current, 'process_lifetime_peak_rss_bytes': high,
            'current_rss_unavailable_reason': reason}


class ArithmeticAudit:
    """Single-use current-thread profiler with bounded attribution and no value cache.

    Existing profilers and nested audits are rejected before mutation. Existing
    tracemalloc state is preserved. Runners own their allocation tracing scopes.
    """
    def __init__(self, *, max_attributions=64, sample_every=1024, max_memory_events=128,
                 initial_scan_limit=1_000_000):
        self.max_attributions = _positive(max_attributions, 'max_attributions')
        self.sample_every = _positive(sample_every, 'sample_every')
        self.max_memory_events = _positive(max_memory_events, 'max_memory_events')
        self.initial_scan_limit = _positive(initial_scan_limit, 'initial_scan_limit')
        self._root = str(Path(__file__).resolve().parents[1]) + os.sep
        constructor = Fraction.__new__
        allocators = {constructor.__code__: '__new__'}
        coprime = getattr(Fraction, '_from_coprime_ints', None)
        if coprime is not None and hasattr(coprime, '__func__'):
            allocators[coprime.__func__.__code__] = '_from_coprime_ints'
        self._allocators = allocators
        self._spawn_functions = tuple(getattr(os, name) for name in ('fork', 'posix_spawn', 'posix_spawnp')
                                      if hasattr(os, name))
        self._hook = self._profile
        self._used = self._active = False
        self._previous = None
        self._phase = None
        self._total, self._phases, self._callers = _empty(), {}, {}
        self._allocator_counts = Counter()
        self._events = Counter()
        self._memory_events = []
        self._memory_event_count = 0
        self._traced_peak = None
        self._last_traced_current = None
        self._peak_rss_observed = None
        self._maximum_sampled_current_rss = None
        self._errors = []
        self._profile_replaced = False

    def _initial(self):
        summary = _empty()
        objects = gc.get_objects()
        observed = min(len(objects), self.initial_scan_limit)
        for value in objects[:observed]:
            if isinstance(value, Fraction):
                _add(summary, value)
        summary.update(scanned_gc_objects=observed, scan_truncated=len(objects) > observed,
                       scope='GC-visible live Fraction objects before profiling; not all live Python or native values')
        # No inspected value or object list survives this call.
        return summary

    def __enter__(self):
        if self._used or self._active:
            raise RuntimeError('arithmetic audit contexts are single-use and cannot nest')
        previous = sys.getprofile()
        if previous is not None:
            raise RuntimeError('an existing profiler must be removed before arithmetic audit')
        self._previous = previous
        self._initial_summary = self._initial()
        self._threads_at_entry = threading.active_count()
        self._tracing_at_entry = tracemalloc.is_tracing()
        self._start_wall, self._start_cpu = time.perf_counter_ns(), time.process_time_ns()
        self._sample_memory('entry')
        self._used = self._active = True
        sys.setprofile(self._hook)
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            self._profile_replaced = sys.getprofile() is not self._hook
        finally:
            sys.setprofile(self._previous)
            self._active = False
        self._end_wall, self._end_cpu = time.perf_counter_ns(), time.process_time_ns()
        try:
            self._sample_memory('exit')
        except Exception as observation_error:
            if len(self._errors) < 8:
                self._errors.append(type(observation_error).__name__)
        self._tracing_at_exit = tracemalloc.is_tracing()
        self._threads_at_exit = threading.active_count()
        self._exit_exception = None if exc_type is None else exc_type.__name__
        return False

    @contextmanager
    def phase(self, name):
        """Optional explicit bounded attribution; it does not alter arithmetic."""
        if not self._active or type(name) is not str or not name or len(name) > 160:
            raise ValueError('phase requires an active audit and short nonempty text')
        previous = self._phase
        self._phase = name
        try:
            yield
        finally:
            self._phase = previous

    def _bucket(self, table, key):
        if key not in table and len(table) >= self.max_attributions:
            key = '<other>'
        return table.setdefault(key, _empty())

    def _attribution(self, frame):
        caller, phase = '<outside-project>', self._phase
        current = frame.f_back
        for _ in range(32):
            if current is None:
                break
            code = current.f_code
            filename, name = code.co_filename, code.co_name
            if filename.startswith(self._root):
                local = filename[len(self._root):]
                if caller == '<outside-project>':
                    caller = f'{local}:{code.co_firstlineno}:{name}'[:240]
                if phase is None:
                    base = local.rsplit('/', 1)[-1]
                    if base == 'exact_core.py' or name == '_quantize':
                        phase = 'factor_and_rounding'
                    elif base == 'domain_refinement.py':
                        phase = 'interval_verification'
                    elif base == 'checkpoint_adapter.py':
                        phase = 'checkpoint_loading'
                    elif base in ('target_manifest.py', 'chart_construction.py'):
                        phase = 'target_and_domain_construction'
                    elif base in ('certified_transformer.py', 'certified_intervals.py', 'box_response_provider.py'):
                        phase = 'finite_or_proof_features'
                    elif base == 'transformer_backend.py':
                        phase = 'finite_features'
                    elif base in ('response_moments.py', 'linear_response.py', 'response_certificate.py'):
                        phase = 'response_moments_and_bounds'
                    elif name in ('_gram', '_combine', '_metric'):
                        phase = 'gram_arithmetic'
                    elif name.startswith('_valid') or name in ('load_state', '_scalar'):
                        phase = 'validation_and_loading'
            current = current.f_back
        return phase or 'unclassified', caller

    def _sample_memory(self, reason):
        tracing = tracemalloc.is_tracing()
        current, peak = tracemalloc.get_traced_memory() if tracing else (None, None)
        rss = _rss()
        if peak is not None:
            self._traced_peak = peak if self._traced_peak is None else max(self._traced_peak, peak)
            self._last_traced_current = current
        high = rss['process_lifetime_peak_rss_bytes']
        self._peak_rss_observed = high if self._peak_rss_observed is None else max(self._peak_rss_observed, high)
        if rss['current_rss_bytes'] is not None:
            current_rss = rss['current_rss_bytes']
            self._maximum_sampled_current_rss = (current_rss if self._maximum_sampled_current_rss is None
                                                else max(self._maximum_sampled_current_rss, current_rss))
        self._memory_event_count += 1
        if len(self._memory_events) < self.max_memory_events:
            self._memory_events.append({'reason': reason, 'phase': self._phase,
                                        'fraction_objects_observed': self._total['fraction_objects'],
                                        'tracemalloc_active': tracing, 'traced_current_bytes': current,
                                        'traced_peak_bytes': peak, **rss})

    def _profile(self, frame, event, arg):
        try:
            if event == 'return' and frame.f_code in self._allocators:
                if isinstance(arg, Fraction):
                    _add(self._total, arg)
                    name = self._allocators[frame.f_code]
                    self._allocator_counts[name] += 1
                    phase, caller = self._attribution(frame)
                    _add(self._bucket(self._phases, phase), arg)
                    _add(self._bucket(self._callers, caller), arg)
                    if self._total['fraction_objects'] % self.sample_every == 0:
                        self._sample_memory('allocation_sample')
                else:
                    self._events['allocator_returns_without_fraction'] += 1
            elif event == 'c_call' and arg is tracemalloc.stop:
                self._sample_memory('before_tracemalloc_stop')
            elif event == 'c_return' and arg is tracemalloc.start:
                self._events['tracemalloc_starts'] += 1
                self._sample_memory('after_tracemalloc_start')
            elif event == 'c_call' and arg in self._spawn_functions:
                self._events['child_process_launch_attempts'] += 1
            elif event == 'c_call' and arg is _thread.start_new_thread:
                self._events['thread_launch_attempts'] += 1
            elif event == 'c_call' and arg is sys.setprofile:
                if frame.f_code is not ArithmeticAudit.__exit__.__code__:
                    self._events['profile_mutation_attempts'] += 1
            elif event == 'call':
                code = frame.f_code
                if code.co_qualname == 'Popen.__init__' and code.co_filename.endswith('subprocess.py'):
                    self._events['child_process_launch_attempts'] += 1
                elif code.co_qualname == 'Thread.start' and code.co_filename.endswith('threading.py'):
                    self._events['thread_launch_attempts'] += 1
        except Exception as exc:
            # A diagnostic failure makes coverage incomplete, never certifies zero work.
            if len(self._errors) < 8:
                self._errors.append(type(exc).__name__)

    def payload(self):
        if not self._used or self._active:
            raise RuntimeError('read the arithmetic audit after its context exits')
        child_count = self._events['child_process_launch_attempts']
        thread_count = self._events['thread_launch_attempts']
        mutation_count = self._events['profile_mutation_attempts']
        intact = not (self._profile_replaced or mutation_count or self._errors or child_count or thread_count or
                      self._threads_at_entry != 1 or self._threads_at_exit != 1)
        return {
            'schema': 'rational-endpoint-audit-v1',
            'audit_status': 'complete_declared_scope' if intact else 'incomplete',
            'scope': 'current thread in current process; successful standard Fraction allocator returns',
            'numerical_functions_replaced': False,
            'clean_latency_eligible': False,
            'timing_warning': 'all runner and audit timings from this profiled process are diagnostic only',
            'runtime': {'python': sys.version, 'implementation': sys.implementation.name,
                        'fraction_source': str(Path(sys.modules['fractions'].__file__).resolve()),
                        'fraction_source_sha256': sha256(Path(sys.modules['fractions'].__file__).read_bytes()).hexdigest(),
                        'observed_allocators': sorted(self._allocators.values())},
            'initial_live_fraction_snapshot': self._initial_summary,
            'constructed_fraction_endpoints': self._total.copy(),
            'allocator_returns': dict(sorted(self._allocator_counts.items())),
            'by_phase': dict(sorted(self._phases.items())),
            'by_project_caller': dict(sorted(self._callers.items())),
            'attribution_limit': self.max_attributions,
            'attribution_overflow_bucket': '<other>; at most one extra aggregate bucket',
            'memory': {'tracemalloc_at_entry': self._tracing_at_entry,
                       'tracemalloc_at_exit': self._tracing_at_exit,
                       'maximum_observed_traced_peak_bytes': self._traced_peak,
                       'last_observed_traced_current_bytes': self._last_traced_current,
                       'maximum_sampled_current_rss_bytes': self._maximum_sampled_current_rss,
                       'maximum_process_lifetime_peak_rss_bytes': self._peak_rss_observed,
                       'sample_count': self._memory_event_count, 'saved_sample_limit': self.max_memory_events,
                       'samples': list(self._memory_events),
                       'scope': 'whole process including diagnostics; traced peaks only when caller enables tracemalloc',
                       'unavailable_tracemalloc_is_null': True},
            'coverage': {'profile_replaced': self._profile_replaced, 'observer_errors': list(self._errors),
                         'profile_mutation_attempts': mutation_count,
                         'threads_at_entry': self._threads_at_entry, 'threads_at_exit': self._threads_at_exit,
                         'child_process_launch_attempts': child_count, 'thread_launch_attempts': thread_count,
                         'current_thread_trace_intact': not (self._profile_replaced or mutation_count or self._errors),
                         'whole_runner_coverage_eligible': intact,
                         'unobserved': ['hidden integer expression intermediates', 'C-extension allocator bypasses',
                                        'other threads', 'child processes', 'object lifetimes and frees',
                                        'preexisting values absent from the bounded GC-visible snapshot']},
            'diagnostic_timing': {'wall_ns': self._end_wall - self._start_wall,
                                  'process_cpu_ns': self._end_cpu - self._start_cpu,
                                  'includes_profiler_overhead': True},
            'exception_type': self._exit_exception, 'events': dict(sorted(self._events.items())),
        }


def _identity(manifest, result):
    keys = ('protocol_sha256', 'target_manifest_sha256', 'service_job_sha256', 'service_manifest_sha256',
            'chart_sha256', 'service_family', 'response_tier', 'service_mode', 'verifier_policy',
            'cache_mode', 'service_boundary', 'phase', 'sequence_id', 'root_id', 'request_id', 'configuration_id')
    metadata = result.get('metadata', {})
    if not isinstance(metadata, dict):
        metadata = {}
    return {'runner_output': {key: result[key] for key in keys if key in result},
            'runner_output_metadata': {key: metadata[key] for key in keys if key in metadata},
            'declared_protocol': manifest.get('protocol'), 'declared_target': manifest.get('target'),
            'declared_chart': manifest.get('chart'),
            'declared_service_configuration': {key: manifest[key] for key in keys if key in manifest}}


def _artifacts(output, limit=10000):
    base, entries, truncated, links = Path(output), [], False, 0
    if base.exists():
        for directory, folders, files in os.walk(base, followlinks=False):
            accepted = []
            for folder in sorted(folders):
                if (Path(directory) / folder).is_symlink():
                    links += 1
                else:
                    accepted.append(folder)
            folders[:] = accepted
            for filename in sorted(files):
                path = Path(directory) / filename
                if path.is_symlink():
                    links += 1
                    continue
                if len(entries) >= limit:
                    truncated = True
                    break
                if path.is_file():
                    entries.append({'path': str(path.relative_to(base)), 'bytes': path.stat().st_size})
            if truncated:
                break
    return {'files': entries, 'total_listed_bytes': sum(x['bytes'] for x in entries),
            'truncated': truncated, 'limit': limit, 'symlinks_skipped': links,
            'scope': 'serialized files under the requested runner output; no resident-memory claim'}


def _write_report(path, report):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    with destination.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def audit_local_run(kind, manifest_path, output, audit_output, *, validate_only=False,
                    sample_every=1024, max_attributions=64):
    """Profile a standard local experiment or sequence; preserve its guards and output.

    This entry point never dispatches an isolated or campaign controller because
    their child computations would escape this profiler.
    """
    if kind not in ('experiment', 'sequence'):
        raise ValueError('arithmetic audit supports only current-process experiment or sequence runners')
    destination = Path(audit_output).resolve()
    if destination.exists():
        raise FileExistsError('arithmetic audit output already exists')
    output = Path(output).resolve()
    if destination.is_relative_to(output):
        raise ValueError('audit sidecar must be outside the immutable runner output directory')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError('arithmetic audit requires a fresh runner output directory')
    manifest_path = Path(manifest_path).absolute()
    raw = manifest_path.read_bytes()
    audit_source_before = sha256(Path(__file__).read_bytes()).hexdigest()
    manifest = json.loads(raw)
    if not isinstance(manifest, dict):
        raise ValueError('runner manifest must be an object')
    audit = ArithmeticAudit(sample_every=sample_every, max_attributions=max_attributions)
    result, failure, original_exception = {}, None, None
    try:
        with audit:
            # Include module constants, checkpoint loading, and all target factories.
            if kind == 'experiment':
                from .experiment_runner import run_manifest
            else:
                from .sequence_runner import run_sequence_manifest as run_manifest
            result = run_manifest(manifest_path, output, validate_only=validate_only)
    except BaseException as exc:
        original_exception = exc
        failure = {'type': type(exc).__name__, 'message': str(exc)[:1000]}
        raise
    finally:
        if audit._used and not audit._active:
            try:
                report = audit.payload()
                try:
                    manifest_unchanged = manifest_path.read_bytes() == raw
                except OSError:
                    manifest_unchanged = False
                try:
                    audit_source_after = sha256(Path(__file__).read_bytes()).hexdigest()
                except OSError:
                    audit_source_after = None
                sources_unchanged = manifest_unchanged and audit_source_before == audit_source_after
                if not sources_unchanged:
                    report['audit_status'] = 'incomplete'
                    report['coverage']['whole_runner_coverage_eligible'] = False
                report.update(runner_kind=kind, manifest_sha256=sha256(raw).hexdigest(),
                              runner_status=result.get('status'), runner_failure=failure,
                              identity=_identity(manifest, result), artifacts=_artifacts(output),
                              audit_source_sha256=audit_source_before,
                              source_stability={'manifest_unchanged': manifest_unchanged,
                                                'audit_source_unchanged': audit_source_before == audit_source_after})
                _write_report(destination, report)
            except Exception as report_error:
                if original_exception is None:
                    raise
                original_exception.add_note('Arithmetic audit receipt failed: ' + type(report_error).__name__)
    return report
