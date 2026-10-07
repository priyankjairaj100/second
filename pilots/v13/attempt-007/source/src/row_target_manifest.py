"""Explicit diagnostic target with fixed base-weight output-row grids.

This wrapper declares a new quantizer. It supplies no canonical repair-state
contract and cannot be silently substituted into the existing service family.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from .target_manifest import build_target
from .row_scaled_quantizer import row_scale_exponents


def _raw(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')


@dataclass(frozen=True)
class RowStage:
    stage_id: str
    dependencies: tuple
    weights: object
    ridge: object
    normalization: object
    scale_exponents: tuple
    bits: int

    @property
    def width(self):return len(self.weights[0])


@dataclass(frozen=True)
class RowTarget:
    recipe: object
    stages: tuple
    payload_bytes: bytes

    def payload(self):return json.loads(self.payload_bytes)

    @property
    def digest(self):return hashlib.sha256(self.payload_bytes).hexdigest()


def build_row_target(decoder,recipe,*,weight_digest_encoding='binary64_matrix_v1'):
    base=build_target(decoder,recipe,weight_digest_encoding=weight_digest_encoding)
    payload=base.payload()
    payload.update(schema='fixed-v-cert-row-grid-diagnostic-target-v1',
        numerical_contract='correctly-rounded finite sequential features; exact rational metric; fixed base-only output-row power2 grids; lower ties',
        grid_recipe='output-row-extrema-smallest-power2-cover-v1',
        output_rule='complete stage codes only; no canonical repair-state contract declared',
        zero_row_scale_exponent=0,
        row_constructor_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        row_solver_source_sha256=hashlib.sha256(Path(__file__).with_name('row_scaled_quantizer.py').read_bytes()).hexdigest(),
        token_solver_source_sha256=hashlib.sha256(Path(__file__).with_name('low_rank_certified.py').read_bytes()).hexdigest())
    payload.pop('zero_column_scale_exponent',None)
    stages=[]
    for stage,entry in zip(base.stages,payload['stages']):
        from .ordered_finite import FiniteWeights
        exponents=tuple(row_scale_exponents(FiniteWeights(stage.weights).array(),bits=recipe.bits))
        stages.append(RowStage(stage.stage_id,stage.dependencies,stage.weights,stage.ridge,stage.normalization,exponents,recipe.bits))
        entry.pop('grids_sha256',None);entry.pop('scale_exponents',None)
        entry.update(grid_axis='output_row',row_scale_exponents=list(exponents))
    return RowTarget(recipe,tuple(stages),_raw(payload))
