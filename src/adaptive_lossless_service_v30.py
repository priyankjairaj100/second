"""Lossless storage with the same bounded point solver as reconstruction."""
from dataclasses import replace
import time
from .adaptive_calibration_v30 import AdaptiveBudget
from .adaptive_fixed_service_v30 import AdaptiveFixedAnchorService
from .fixed_lossless_service_v29 import FixedLosslessService
from .compact_service import _records
from .low_rank_certified import LowRankUnresolved


class AdaptiveLosslessService(FixedLosslessService):
    def __init__(self, decoder, base_target, *, solver_backend='auto',
                 coefficient_budget=AdaptiveBudget(), progress=None,
                 max_point_work_units=48_000_000_000):
        if progress is not None and not callable(progress):
            raise TypeError('progress must be callable or None')
        self.exact = AdaptiveFixedAnchorService(decoder, base_target,
            solver_backend=solver_backend, coefficient_budget=coefficient_budget,
            state_backend='factors', use_candidates=False, progress=progress,
            max_point_work_units=max_point_work_units)
        self.decoder, self.base_target, self.target = decoder, base_target, self.exact.target
        self.solver_backend = solver_backend

    def run(self, records, **kwargs):
        started = time.perf_counter_ns()
        rows = _records(self.decoder, records)
        admission = self.exact.admit_records(rows)
        preflight_ns = time.perf_counter_ns()-started
        try:
            result = super().run(tuple(dict(id=rid,tokens=tokens) for rid,tokens in rows), **kwargs)
        except LowRankUnresolved as exc:
            exc.diagnostics = dict(schema='adaptive-lossless-refusal-v30', aborted=True,
                exact_service_diagnostics=getattr(exc, 'service_diagnostics', None),
                early_point_admission=admission, early_admission_elapsed_ns=preflight_ns,
                service_elapsed_ns=time.perf_counter_ns()-started)
            raise
        diag = dict(result.diagnostics, early_point_admission=admission,
            early_admission_elapsed_ns=preflight_ns,
            inner_service_elapsed_ns=result.diagnostics['service_elapsed_ns'],
            service_elapsed_ns=time.perf_counter_ns()-started)
        return replace(result, diagnostics=diag)
