"""Explicit fixed-feature calibration target, separate from sequential repair.

Every feature uses the fixed nearest-grid anchor model. Calibrated output
codes never change later feature inputs. This changes the numerical target.
"""
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path

from .anchor_transformer import decoder_binding, provider_binding


@dataclass(frozen=True)
class FixedAnchorTarget:
    anchor_target: object
    payload_bytes: bytes

    @property
    def stages(self):
        # Calibrated stages are independent in this target. Advertising the
        # original dependency prefixes would let sequential services accept
        # this digest while executing the wrong feature rule.
        return tuple(replace(stage, dependencies=()) for stage in self.anchor_target.stages)

    @property
    def recipe(self):
        return self.anchor_target.recipe

    @property
    def digest(self):
        return hashlib.sha256(self.payload_bytes).hexdigest()

    def payload(self):
        return json.loads(self.payload_bytes)


def build_fixed_anchor_target(decoder, base_target):
    """Bind the changed feature rule without preparing or executing an anchor."""
    if tuple(s.stage_id for s in base_target.stages) != tuple(decoder.stage_ids):
        raise ValueError('fixed anchor target requires every decoder stage')
    for i, stage in enumerate(base_target.stages):
        if (not hasattr(stage, 'scale_values') or len(stage.dependencies) != i
                or set(stage.dependencies) != set(decoder.stage_ids[:i])):
            raise ValueError('base target must be a complete dyadic sequential specification')
    payload = dict(
        schema='fixed-nearest-anchor-calibration-target-v1',
        anchor_target_sha256=base_target.digest,
        decoder_sha256=decoder_binding(decoder), provider_sha256=provider_binding(),
        feature_rule='every stage uses its fixed source-local nearest-grid anchor features',
        output_rule='calibrate each stage independently in the fixed anchor feature metric',
        prefix_rule='calibrated output codes never affect any feature',
        anchor_rule='base-only canonical dyadic grids; nearest rounding; lower midpoint ties',
        normalization_rule='unchanged original normalization from anchor target',
        state_family='fixed_anchor_calibration_v1',
        constructor_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return FixedAnchorTarget(base_target, json.dumps(payload, sort_keys=True,
        separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii'))
