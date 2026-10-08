"""Lossless storage with the same bounded point solver as reconstruction."""
from .adaptive_calibration_v30 import AdaptiveBudget
from .adaptive_fixed_service_v30 import AdaptiveFixedAnchorService
from .fixed_lossless_service_v29 import FixedLosslessService


class AdaptiveLosslessService(FixedLosslessService):
    def __init__(self, decoder, base_target, *, solver_backend='auto',
                 coefficient_budget=AdaptiveBudget(), progress=None):
        if progress is not None and not callable(progress):
            raise TypeError('progress must be callable or None')
        self.exact = AdaptiveFixedAnchorService(decoder, base_target,
            solver_backend=solver_backend, coefficient_budget=coefficient_budget,
            state_backend='factors', use_candidates=False, progress=progress)
        self.decoder, self.base_target, self.target = decoder, base_target, self.exact.target
        self.solver_backend = solver_backend
