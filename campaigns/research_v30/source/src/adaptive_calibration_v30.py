"""Bounded route selection for the unchanged exact dyadic calibration target.

Work units are structural operation proxies, not CPU time. Resource refusal
never implies that a requested model has been repaired. Compatible callers
must supply the same policy to repair and reconstruction.
"""
from dataclasses import dataclass, fields

import numpy as np

from .token_box_certificate import TokenBoxUnresolved


@dataclass(frozen=True)
class AdaptiveBudget:
    max_workspace_bytes: int = 512 * 2**20
    max_work_units: int = 2_000_000_000
    max_refinement_coordinates: int = 16

    def __post_init__(self):
        for name in ('max_workspace_bytes', 'max_work_units', 'max_refinement_coordinates'):
            value = getattr(self, name)
            if type(value) is not int or value < (0 if name == 'max_refinement_coordinates' else 1):
                raise ValueError(name + ' has an invalid integer limit')


class CalibrationWorkRefused(TokenBoxUnresolved):
    """The declared resource policy does not admit this stage."""

    def __init__(self, message, report):
        super().__init__(message)
        self.admission = report


def assess_routes(rows, width, tokens, *, budget=AdaptiveBudget()):
    for name, value in (('rows', rows), ('width', width), ('tokens', tokens)):
        if type(value) is not int or value < (0 if name == 'tokens' else 1):
            raise ValueError(name + ' has invalid dimensions')
    if type(budget) is not AdaptiveBudget:
        raise TypeError('budget must be AdaptiveBudget')
    # Include the common ridge pass and one repeated fallback table. The
    # coordinate cap bounds direct suffix Gram construction and solves.
    k = min(width, budget.max_refinement_coordinates)
    dual_work = 2 * width * tokens**2 + 2 * rows * width * tokens
    dual_work += k * (width * tokens**2 + tokens**3)
    # This is an explicit numerical-array envelope, not whole-process RSS.
    dual_bytes = 8 * (32*tokens**2 + 16*width*tokens + 8*rows*width + 1024)
    from .primal_certificate_v30 import PrimalBudget, assess_primal_budget
    primal = assess_primal_budget(rows=rows, width=width, tokens=tokens, bits=4,
        budget=PrimalBudget(max_workspace_bytes=budget.max_workspace_bytes,
                           max_work_units=budget.max_work_units))
    # The primal assessment is authoritative for its own explicit arrays.
    if hasattr(primal, '__dict__'):
        primal = vars(primal)
    pwork = int(primal['work_units'])
    pbytes = int(primal['explicit_array_bytes'])
    routes = {
        'token': dict(work_units=dual_work, explicit_array_bytes=dual_bytes),
        'primal': dict(work_units=pwork, explicit_array_bytes=pbytes),
    }
    for route in routes.values():
        route['admitted'] = (route['work_units'] <= budget.max_work_units
                             and route['explicit_array_bytes'] <= budget.max_workspace_bytes)
    allowed = [name for name in routes if routes[name]['admitted']]
    selected = min(allowed, key=lambda name: (routes[name]['work_units'], name)) if allowed else None
    return dict(rows=rows, width=width, tokens=tokens, routes=routes, selected=selected,
        policy='minimum admitted structural work; no measured timing crossover',
        max_workspace_bytes=budget.max_workspace_bytes, max_work_units=budget.max_work_units,
        max_refinement_coordinates=budget.max_refinement_coordinates,
        whole_process_memory_guaranteed=False, wall_time_guaranteed=False)


@dataclass(frozen=True)
class AdaptiveResult:
    codes: object
    backend: str
    admission: dict
    solver_diagnostics: dict


def quantize_adaptive_dyadic_rows(weights, features, scale_values=None, *, bits=4,
        significant_bits=24, ridge, normalization=1, route='auto',
        budget=AdaptiveBudget(), candidate=None, **unused_limits):
    """Use one admitted route, with no automatic cross-route retry.

The point token path permits bounded numerical refinement only. Exact
rational fallback is disabled because bit complexity has no useful scalar
dimension bound here. A failed certificate returns no model.
"""
    if route not in ('auto', 'token', 'primal'):
        raise ValueError('route must be auto, token, or primal')
    if type(weights) is not np.ndarray or type(features) is not np.ndarray:
        raise TypeError('weights and features must be arrays')
    if weights.dtype != np.float64 or features.dtype != np.float64:
        raise TypeError('weights and features must preserve binary64 input values')
    if weights.ndim != 2 or features.ndim != 2 or weights.shape[1] != features.shape[0]:
        raise ValueError('incompatible dimensions')
    if candidate is not None:
        raise ValueError('adaptive route has no prior-model candidate input')
    if bits != 4:
        raise ValueError('the current route budget is registered for four bits')
    report = assess_routes(weights.shape[0], weights.shape[1], features.shape[1], budget=budget)
    selected = report['selected'] if route == 'auto' else route
    if selected is None or not report['routes'][selected]['admitted']:
        raise CalibrationWorkRefused('stage exceeds declared coefficient work or array limit', report)
    weights = np.require(weights, dtype=np.float64, requirements=['C', 'A'])
    features = np.require(features, dtype=np.float64, requirements=['C', 'A'])
    options = dict(bits=bits, significant_bits=significant_bits, ridge=ridge, normalization=normalization)
    if selected == 'token':
        from .native_ball_quantizer import native_quantize_dyadic_rows
        result = native_quantize_dyadic_rows(weights, features, scale_values,
            max_exact_rank=0, max_exact_coordinates=0,
            max_refinement_coordinates=budget.max_refinement_coordinates, **options)
    else:
        from .primal_certificate_v30 import PrimalBudget, certify_primal_dyadic_box
        result = certify_primal_dyadic_box(weights, features, features, scale_values,
            budget=PrimalBudget(max_workspace_bytes=budget.max_workspace_bytes,
                max_work_units=budget.max_work_units), **options)
    return AdaptiveResult(result.codes, selected, report,
        {f.name: getattr(result, f.name) for f in fields(result) if f.name != 'codes'})
