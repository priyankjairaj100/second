"""Optional exclusive diagnostic timings outside canonical model state.

These timings add instrumentation overhead. They are not clean latency results.
Each interval subtracts its child intervals, including repeated category names.
A collector belongs to one synchronous operation at a time.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from time import perf_counter_ns

_CURRENT: ContextVar[ServiceTelemetry | None] = ContextVar('service_telemetry', default=None)


class ServiceTelemetry:
    """Collect disjoint nanoseconds, invocation counts, and diagnostic events."""
    def __init__(self, *, clock=perf_counter_ns):
        if not callable(clock):
            raise TypeError('clock must be callable')
        self._clock = clock
        self._stack = []
        self._nanoseconds = Counter()
        self._calls = Counter()
        self._events = Counter()
        self._reasons = Counter()
        self._active = False

    @contextmanager
    def span(self, category: str):
        if type(category) is not str or not category:
            raise ValueError('timing category must be nonempty text')
        frame = [self._clock(), 0]
        self._stack.append(frame)
        try:
            yield
        finally:
            elapsed = self._clock() - frame[0]
            if elapsed < frame[1]:
                raise RuntimeError('telemetry clock must be monotone')
            popped = self._stack.pop()
            if popped is not frame:
                raise RuntimeError('telemetry spans must close in stack order')
            self._nanoseconds[category] += elapsed - frame[1]
            self._calls[category] += 1
            if self._stack:
                self._stack[-1][1] += elapsed

    def event(self, name: str, *, reason: str | None = None, count: int = 1):
        if type(name) is not str or not name or type(count) is not int or count < 0:
            raise ValueError('events require a name and a nonnegative integer count')
        if reason is not None and type(reason) is not str:
            raise TypeError('event reason must be text')
        self._events[name] += count
        if reason is not None:
            self._reasons[(name, reason)] += count

    def payload(self) -> dict:
        if self._stack or self._active:
            raise RuntimeError('read telemetry only after the operation finishes')
        return {'schema': 'service-telemetry-v1', 'instrumented': True,
                'timing_semantics': 'exclusive nested spans; instrumentation overhead included',
                'timings': {name: {'exclusive_ns': self._nanoseconds[name], 'calls': self._calls[name]}
                            for name in sorted(self._calls)},
                'total_exclusive_ns': sum(self._nanoseconds.values()),
                'events': dict(sorted(self._events.items())),
                'reasons': [{'event': name, 'reason': reason, 'count': count}
                            for (name, reason), count in sorted(self._reasons.items())]}


def event(name: str, *, reason: str | None = None, count: int = 1):
    collector = _CURRENT.get()
    if collector is not None:
        collector.event(name, reason=reason, count=count)


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


def operation(function):
    """Add the optional telemetry keyword without changing scientific inputs."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        collector = kwargs.pop('telemetry', None)
        if collector is None:
            return function(*args, **kwargs)
        if not isinstance(collector, ServiceTelemetry):
            raise TypeError('telemetry must be ServiceTelemetry')
        if collector._active or _CURRENT.get() is not None:
            raise RuntimeError('one telemetry collector is allowed per synchronous operation')
        collector._active = True
        token = _CURRENT.set(collector)
        try:
            with collector.span('service_overhead'):
                collector.event('operation.' + function.__name__)
                try:
                    result = function(*args, **kwargs)
                except BaseException as exc:
                    collector.event('operation.failed', reason=type(exc).__name__)
                    raise
                collector.event('operation.completed')
                return result
        finally:
            _CURRENT.reset(token)
            collector._active = False
    return wrapped


__all__ = ['ServiceTelemetry']
