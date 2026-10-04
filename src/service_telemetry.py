"""Optional exclusive diagnostic timings outside canonical model state.

These timings add instrumentation overhead. They are not clean latency results.
Each interval subtracts its child intervals, including repeated category names.
A collector belongs to one synchronous operation at a time.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from itertools import islice
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from time import perf_counter_ns

_CURRENT: ContextVar[ServiceTelemetry | None] = ContextVar('service_telemetry', default=None)
_MAX_COUNT = (1 << 64) - 1


@dataclass(frozen=True)
class DiagnosticLimits:
    """Explicit storage limits for external numerical diagnostics."""
    max_stage_records: int = 256
    max_event_kinds_per_stage: int = 32
    max_cell_samples: int = 4
    max_integer_bits: int = 256
    max_text_length: int = 192
    max_fields: int = 24
    max_depth: int = 5
    max_counter_keys: int = 256

    def __post_init__(self):
        if any(type(x) is not int or x <= 0 for x in self.__dict__.values()):
            raise ValueError('diagnostic limits must be positive built-in integers')
        if self.max_cell_samples > 64 or self.max_integer_bits > 4096 or self.max_depth > 8:
            raise ValueError('cell, integer, and nesting limits exceed supported diagnostic bounds')


def _text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    digest = sha256(value.encode('utf-8')).hexdigest()
    suffix = '...[sha256:' + digest + ']'
    if limit <= len(suffix):
        return ('sha256:' + digest)[:limit]
    return value[:limit - len(suffix)] + suffix



class ServiceTelemetry:
    """Collect disjoint nanoseconds, invocation counts, and diagnostic events."""
    def __init__(self, *, clock=perf_counter_ns, diagnostic_limits: DiagnosticLimits | None = None, enabled=None):
        from .instrumentation import detailed_diagnostics_enabled
        allowed = detailed_diagnostics_enabled()
        if enabled is not None and type(enabled) is not bool:
            raise TypeError('telemetry enabled flag requires a Boolean')
        self.enabled = allowed if enabled is None else enabled
        if self.enabled and not allowed:
            raise RuntimeError('detailed telemetry is forbidden inside clean execution')
        self._active = False
        self._timing_clock = ('time.perf_counter_ns_system_monotonic' if clock is perf_counter_ns else 'custom_unverified')
        self._timing_windows = []
        self._timing_windows_omitted = 0
        if not self.enabled:
            return
        if not callable(clock):
            raise TypeError('clock must be callable')
        self._clock = clock
        self.diagnostic_limits = DiagnosticLimits() if diagnostic_limits is None else diagnostic_limits
        if not isinstance(self.diagnostic_limits, DiagnosticLimits):
            raise TypeError('diagnostic_limits must be DiagnosticLimits')
        self._stage_records = {}
        self._diagnostic_counters = Counter()
        self._operation_records = []
        self._operation_index = 0
        self._operation_name = 'external'
        self._stack = []
        self._nanoseconds = Counter()
        self._calls = Counter()
        self._events = Counter()
        self._reasons = Counter()
        self._active = False

    @contextmanager
    def span(self, category: str):
        if not self.enabled:
            yield
            return
        from .instrumentation import detailed_diagnostics_enabled
        if not detailed_diagnostics_enabled():
            raise RuntimeError('a diagnostic collector cannot enter clean execution')
        if type(category) is not str or not category:
            raise ValueError('timing category must be nonempty text')
        category = _text(category, self.diagnostic_limits.max_text_length)
        if category not in self._calls and len(self._calls) >= self.diagnostic_limits.max_counter_keys:
            category = '__other__'
        # Reserve the category on entry, including before nested spans enter.
        self._calls.setdefault(category, 0)
        frame = [self._clock(), 0]
        self._stack.append(frame)
        try:
            yield
        finally:
            ended = self._clock()
            elapsed = ended - frame[0]
            if elapsed < frame[1]:
                raise RuntimeError('telemetry clock must be monotone')
            popped = self._stack.pop()
            if popped is not frame:
                raise RuntimeError('telemetry spans must close in stack order')
            self._nanoseconds[category] += elapsed - frame[1]
            self._calls[category] += 1
            if self._stack:
                self._stack[-1][1] += elapsed
            elif len(self._timing_windows) < self.diagnostic_limits.max_counter_keys:
                self._timing_windows.append({'start_ns':frame[0], 'end_ns':ended, 'wall_ns':elapsed})
            else:
                self._timing_windows_omitted += 1

    def event(self, name: str, *, reason: str | None = None, count: int = 1):
        if not self.enabled:
            return
        from .instrumentation import detailed_diagnostics_enabled
        if not detailed_diagnostics_enabled():
            raise RuntimeError('a diagnostic collector cannot enter clean execution')
        if type(name) is not str or not name or type(count) is not int or count < 0:
            raise ValueError('events require a name and a nonnegative integer count')
        if reason is not None and type(reason) is not str:
            raise TypeError('event reason must be text')
        name = _text(name, self.diagnostic_limits.max_text_length)
        if name not in self._events and len(self._events) >= self.diagnostic_limits.max_counter_keys:
            name = '__other__'
        self._count(self._events, name, count)
        if reason is not None:
            reason = _text(reason, self.diagnostic_limits.max_text_length)
            key = (name, reason)
            if key not in self._reasons and len(self._reasons) >= self.diagnostic_limits.max_counter_keys:
                key = ('__other__', 'reason_keys_truncated')
            self._count(self._reasons, key, count)

    def _count(self, counter, key, amount=1):
        current = counter.get(key, 0)
        if amount > _MAX_COUNT - current:
            counter[key] = _MAX_COUNT
            self._diagnostic_counters['counter_values_saturated'] = min(
                _MAX_COUNT, self._diagnostic_counters['counter_values_saturated'] + 1)
        else:
            counter[key] = current + amount

    def _summarize_values(self, record, event_name, value):
        if type(value) is not dict:
            return
        for selector in ('status', 'proposal', 'role', 'accepted', 'contract_available'):
            item = value.get(selector)
            if type(item) not in (str, bool):
                continue
            key = event_name + ':' + selector + '=' + _text(str(item), self.diagnostic_limits.max_text_length)
            if key not in record['dispositions'] and len(record['dispositions']) >= self.diagnostic_limits.max_counter_keys:
                key = '__other__'
            self._count(record['dispositions'], key)
        for field in ('unavailable_records', 'retained_records', 'checked_cells', 'failed_cells', 'feature_evaluations'):
            item = value.get(field)
            if type(item) is int and item >= 0:
                key = event_name + ':' + field
                if key not in record['totals'] and len(record['totals']) >= self.diagnostic_limits.max_counter_keys:
                    key = '__other__'
                self._count(record['totals'], key, item)

    def _begin_operation(self, name):
        self._operation_index += 1
        self._operation_name = _text(name, self.diagnostic_limits.max_text_length)

    def _end_operation(self, *, success, failure=None, produced_model=False):
        failure = None if failure is None else _text(failure, self.diagnostic_limits.max_text_length)
        if len(self._operation_records) < self.diagnostic_limits.max_stage_records:
            self._operation_records.append({'operation_index': self._operation_index,
                'operation': self._operation_name, 'status': 'complete' if success else 'failed',
                'failure_type': failure, 'produced_complete_model': bool(success and produced_model)})
        else:
            self._diagnostic_counters['operation_records_omitted'] += 1
        if not success:
            for record in self._stage_records.values():
                if record['operation_index'] == self._operation_index and record['status'] == 'running':
                    record['status'] = 'failed'
                    record['failure_type'] = failure

    def _encode(self, value, depth=0):
        limits = self.diagnostic_limits
        if value is None or type(value) is bool:
            return value
        if type(value) is int:
            if abs(value).bit_length() <= limits.max_integer_bits:
                return value
            self._diagnostic_counters['large_values_summarized'] += 1
            return {'encoding': 'integer_magnitude', 'sign': (value > 0) - (value < 0),
                    'bits': abs(value).bit_length()}
        if isinstance(value, Fraction):
            nbits, dbits = abs(value.numerator).bit_length(), value.denominator.bit_length()
            if max(nbits, dbits) <= limits.max_integer_bits:
                return {'encoding': 'rational', 'numerator': value.numerator, 'denominator': value.denominator}
            self._diagnostic_counters['large_values_summarized'] += 1
            return {'encoding': 'rational_magnitude', 'sign': (value > 0) - (value < 0),
                    'numerator_bits': nbits, 'denominator_bits': dbits}
        if type(value) is str:
            if len(value) > limits.max_text_length:
                self._diagnostic_counters['texts_truncated'] += 1
            return _text(value, limits.max_text_length)
        if depth >= limits.max_depth:
            self._diagnostic_counters['nested_values_omitted'] += 1
            return {'encoding': 'depth_limit'}
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                raise TypeError('diagnostic field names must be strings')
            if len(value) > limits.max_fields:
                self._diagnostic_counters['fields_omitted'] += len(value) - limits.max_fields
            return {_text(key, limits.max_text_length): self._encode(child, depth + 1)
                    for key, child in islice(value.items(), limits.max_fields)}
        if isinstance(value, (tuple, list)):
            if len(value) > limits.max_cell_samples:
                self._diagnostic_counters['sequence_values_omitted'] += len(value) - limits.max_cell_samples
            return [self._encode(x, depth + 1) for x in value[:limits.max_cell_samples]]
        raise TypeError('diagnostic values must be exact scalars or bounded containers')

    def diagnostic(self, stage_id, event_name, *, values=None, build=None):
        """Keep bounded first/last observations and counts, never full traces."""
        if not self.enabled:
            return False
        from .instrumentation import detailed_diagnostics_enabled
        if not detailed_diagnostics_enabled():
            raise RuntimeError('a diagnostic collector cannot enter clean execution')
        if type(stage_id) is not str or type(event_name) is not str or not stage_id or not event_name:
            raise ValueError('diagnostic stage and event identifiers must be nonempty strings')
        if values is not None and build is not None:
            raise ValueError('supply values or a lazy diagnostic builder')
        self._diagnostic_counters['observations'] += 1
        stage_key = sha256(stage_id.encode('utf-8')).hexdigest()
        key = (self._operation_index, stage_key)
        if key not in self._stage_records:
            if len(self._stage_records) >= self.diagnostic_limits.max_stage_records:
                self._diagnostic_counters['stage_observations_omitted'] += 1
                return False
            self._stage_records[key] = {'operation_index': self._operation_index, 'operation': self._operation_name,
                'stage_id': _text(stage_id, self.diagnostic_limits.max_text_length), 'stage_id_sha256': stage_key,
                'status': 'observed', 'failure_type': None, 'events': {}, 'dispositions': {}, 'totals': {}}
        record = self._stage_records[key]
        if event_name == 'stage_started':
            record['status'] = 'running'
        elif event_name == 'stage_completed':
            record['status'] = 'complete'
        elif event_name == 'stage_failed':
            record['status'] = 'failed'
        events = record['events']
        event_name = _text(event_name, self.diagnostic_limits.max_text_length)
        if event_name not in events:
            if len(events) >= self.diagnostic_limits.max_event_kinds_per_stage:
                self._diagnostic_counters['event_kind_observations_omitted'] += 1
                return False
            events[event_name] = {'count': 0, 'first': None, 'last': None}
        entry = events[event_name]
        self._count(entry, 'count')
        try:
            value = build(self.diagnostic_limits.max_cell_samples) if build is not None else values
            encoded = self._encode({} if value is None else value)
            self._summarize_values(record, event_name, value)
        except Exception as exc:
            # Diagnostic encoding never turns an otherwise valid model into an abort.
            self._diagnostic_counters['encoding_failures'] += 1
            encoded = {'diagnostic_failure': _text(type(exc).__name__, self.diagnostic_limits.max_text_length)}
        if entry['first'] is None:
            entry['first'] = encoded
        entry['last'] = encoded
        self._diagnostic_counters['observations_recorded'] += 1
        return True

    def payload(self) -> dict:
        if not self.enabled:
            return {'schema': 'service-telemetry-v1', 'instrumented': False,
                    'details': None, 'reason': 'optional_detailed_telemetry_disabled'}
        if self._stack or self._active:
            raise RuntimeError('read telemetry only after the operation finishes')
        return {'schema': 'service-telemetry-v1', 'instrumented': True,
                'timing_semantics': 'exclusive nested spans; instrumentation overhead included',
                'timings': {name: {'exclusive_ns': self._nanoseconds[name], 'calls': self._calls[name]}
                            for name in sorted(self._calls)},
                'total_exclusive_ns': sum(self._nanoseconds.values()),
                'timing_clock': self._timing_clock,
                'timing_windows': deepcopy(self._timing_windows),
                'timing_windows_omitted': self._timing_windows_omitted,
                'events': dict(sorted(self._events.items())),
                'reasons': [{'event': name, 'reason': reason, 'count': count}
                            for (name, reason), count in sorted(self._reasons.items())],
                'certificate_funnel': {'schema': 'certificate-funnel-v1',
                    'scope': 'external bounded diagnostics; no payloads, features, or canonical state additions',
                    'limits': dict(self.diagnostic_limits.__dict__),
                    'counters': dict(sorted(self._diagnostic_counters.items())),
                    'operations': deepcopy(self._operation_records),
                    'stages': deepcopy(list(self._stage_records.values()))}}



def event(name: str, *, reason: str | None = None, count: int = 1):
    collector = _CURRENT.get()
    if collector is not None:
        collector.event(name, reason=reason, count=count)


def diagnostics_enabled():
    return _CURRENT.get() is not None


def diagnostic(stage_id, event_name, *, values=None, build=None):
    collector = _CURRENT.get()
    if collector is None:
        return False
    with collector.span('certificate_diagnostics'):
        return collector.diagnostic(stage_id, event_name, values=values, build=build)


def timed(category: str):
    """Measure a nested helper only when an operation enabled telemetry."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            collector = _CURRENT.get()
            if collector is None:
                return function(*args, **kwargs)
            with collector.span(category):
                return function(*args, **kwargs)
        return wrapped
    return decorate


def provider_diagnostic(stage_id, event_name, *, build):
    """Expose available provider evidence only inside a diagnostic operation.

    The builder receives the sample cap and stays unevaluated in clean mode.
    No values enter canonical state, and bounded encoding errors stay diagnostic.
    """
    collector = _CURRENT.get()
    if collector is None:
        return False
    with collector.span('provider_diagnostics'):
        return collector.diagnostic(stage_id, event_name, build=build)


def operation(function):
    """Add the optional telemetry keyword without changing scientific inputs."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        collector = kwargs.pop('telemetry', None)
        if collector is None:
            return function(*args, **kwargs)
        if not isinstance(collector, ServiceTelemetry):
            raise TypeError('telemetry must be ServiceTelemetry')
        if not collector.enabled:
            return function(*args, **kwargs)
        if collector._active or _CURRENT.get() is not None:
            raise RuntimeError('one telemetry collector is allowed per synchronous operation')
        collector._active = True
        token = _CURRENT.set(collector)
        try:
            with collector.span('service_overhead'):
                collector._begin_operation(function.__name__)
                collector.event('operation.' + function.__name__)
                try:
                    result = function(*args, **kwargs)
                except BaseException as exc:
                    collector.event('operation.failed', reason=type(exc).__name__)
                    collector._end_operation(success=False, failure=type(exc).__name__)
                    raise
                collector.event('operation.completed')
                collector._end_operation(success=True, produced_model=any(
                    hasattr(getattr(result, name, None), 'model') for name in ('state', 'output')))
                return result
        finally:
            _CURRENT.reset(token)
            collector._active = False
    return wrapped


__all__ = ['ServiceTelemetry', 'DiagnosticLimits', 'provider_diagnostic']
