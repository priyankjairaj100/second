"""Explicit leaf instrumentation profiles for trusted local execution.

Clean disables optional Python diagnostics. Required exact arithmetic work
counters, correctness checks, output checks, and external clocks remain charged.
This is not a claim that external native profilers or OS tracing are absent.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import sys
import tracemalloc

_MODE = ContextVar('calibration_instrumentation_mode', default='diagnostic')
MODES = ('clean', 'diagnostic')


def instrumentation_state():
    monitoring = getattr(sys, 'monitoring', None)
    events = [] if monitoring is None else [monitoring.get_events(i) for i in range(6)]
    tools_allocated = False if monitoring is None else any(monitoring.get_tool(i) is not None for i in range(6))
    return {
        'schema': 'calibration-instrumentation-v1',
        'mode': _MODE.get(),
        'python_profiler_active': sys.getprofile() is not None,
        'python_trace_active': sys.gettrace() is not None,
        'allocation_tracing_active': tracemalloc.is_tracing(),
        'global_monitoring_active': any(events),
        'monitoring_tools_allocated': tools_allocated,
        'detailed_service_telemetry': _MODE.get() == 'diagnostic',
        'required_arithmetic_counters_retained': True,
        'external_native_profiler_status': 'unobserved',
    }


def require_clean_instrumentation():
    state = instrumentation_state()
    if state['mode'] != 'clean':
        raise ValueError('a clean instrumentation scope is required')
    if any(state[k] for k in ('python_profiler_active', 'python_trace_active',
                              'allocation_tracing_active', 'global_monitoring_active', 'monitoring_tools_allocated')):
        raise RuntimeError('clean execution has active optional Python instrumentation')
    return state


def detailed_diagnostics_enabled():
    return _MODE.get() == 'diagnostic'


@contextmanager
def instrumentation_scope(mode):
    """Set the bound profile and validate both ends, including failed work."""
    if type(mode) is not str or mode not in MODES:
        raise ValueError('instrumentation mode must be clean or diagnostic')
    # A nested callback cannot silently re-enable diagnostics in a clean leaf.
    if _MODE.get() == 'clean' and mode != 'clean':
        raise RuntimeError('cannot enable diagnostic mode inside clean execution')
    token = _MODE.set(mode)
    original_error = None
    try:
        if mode == 'clean':
            require_clean_instrumentation()
        try:
            yield instrumentation_state()
        except BaseException as exc:
            original_error = exc
            raise
        finally:
            if mode == 'clean':
                try:
                    require_clean_instrumentation()
                except BaseException as exc:
                    if original_error is None:
                        raise
                    if hasattr(original_error, 'add_note'):
                        original_error.add_note('clean instrumentation postcheck failed: ' + str(exc))
    finally:
        _MODE.reset(token)
