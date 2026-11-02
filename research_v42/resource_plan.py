"""Conservative, read-only stage resource planning for the fixed-anchor target.

This is not an executable dispatcher, canonical state oracle, empirical
registration, or permission to launch work. It calls existing shape-only
admission helpers without compiling kernels, allocating numerical arrays,
reading features, or changing their limits. In particular, the point-token
assessment includes the existing row/fallback reservation, not just native
coefficient admission. Every stage is reported even after a refusal.

Solver admission is distinct from complete route admission. Source preparation,
archive parsing, replay ancestors, simultaneous residency, output, and process
limits remain unreviewed here. Consequently every complete route and request
is refused, including tiny cases whose solver components fit. Work proxies
from different routes are not ranked or pooled.

Run from the repository root (write to a fresh path):
  python -B -m research_v42.resource_plan --output work/v42-resource-plan.json
Tests need the existing Python dependencies but no compiler, GPU, or datasets:
  python -B -m unittest research_v42.test_resource_plan
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_DIR = ROOT / 'campaigns/ci_scale_v39/attempts/prepare/outputs'
COMMON_BLOCKERS = (
    'whole_process_residency_and_os_limits_unreviewed',
    'source_access_preparation_and_replay_ancestors_unreviewed',
    'complete_output_serialization_and_atomic_commit_unreviewed',
    'canonical_successor_state_contract_and_independent_oracle_missing',
    'fresh_empirical_registration_and_runtime_binding_missing',
)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _integer(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(name + ' must be a built-in integer >= ' + str(minimum))
    return value


def _digest(value, name):
    if (type(value) is not str or len(value) != 64
            or any(c not in '0123456789abcdef' for c in value)):
        raise ValueError(name + ' must be a lowercase SHA-256 digest')
    return value


def _rational_pair(value, name):
    if (type(value) is not list or len(value) != 2
            or any(type(v) is not int for v in value)
            or min(value) <= 0):
        raise ValueError(name + ' must be a positive exact rational pair')
    result = Fraction(*value)
    if [result.numerator, result.denominator] != value:
        raise ValueError(name + ' must be in canonical lowest terms')
    return tuple(value)


def _object(payload, name):
    if type(payload) is not bytes:
        raise TypeError(name + ' must be immutable bytes')
    try:
        value = json.loads(payload)
        canonical = _json(value)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError(name + ' is not canonical JSON') from exc
    if type(value) is not dict or canonical != payload:
        raise ValueError(name + ' is not a canonical JSON object')
    return value


@dataclass(frozen=True)
class StageBinding:
    """Immutable dimensions and numerical identifiers derived from bound bytes."""
    index: int
    stage_id: str
    rows: int
    width: int
    bits: int
    normalization: tuple[int, int]
    ridge: tuple[int, int]
    stage_sha256: str
    target_sha256: str
    anchor_target_sha256: str


@dataclass(frozen=True)
class BoundTarget:
    """Bind both target manifests; digests provide identity, not provenance trust.

    Only immutable canonical bytes are retained. Stage bindings are regenerated
    from those bytes, so a caller cannot replace dimensions in an old binding
    while keeping its target identity. No model weights/features are loaded.
    """
    anchor_payload: bytes
    fixed_payload: bytes

    def __post_init__(self):
        self._read()

    def _read(self):
        anchor = _object(self.anchor_payload, 'anchor target')
        fixed = _object(self.fixed_payload, 'fixed target')
        if anchor.get('schema') != 'fixed-v-cert-dyadic-row-grid-diagnostic-target-v1':
            raise ValueError('unsupported anchor target schema')
        if fixed.get('schema') != 'fixed-nearest-anchor-calibration-target-v1':
            raise ValueError('unsupported fixed target schema')
        if fixed.get('anchor_target_sha256') != _sha(self.anchor_payload):
            raise ValueError('fixed target does not bind the supplied anchor target')
        supported = dict(
            feature_rule='every stage uses its fixed source-local nearest-grid anchor features',
            output_rule='calibrate each stage independently in the fixed anchor feature metric',
            prefix_rule='calibrated output codes never affect any feature',
            anchor_rule='base-only canonical dyadic grids; nearest rounding; lower midpoint ties',
            normalization_rule='unchanged original normalization from anchor target',
            state_family='fixed_anchor_calibration_v1')
        if any(fixed.get(key) != expected for key, expected in supported.items()):
            raise ValueError('unsupported fixed target numerical contract')
        for name in ('decoder_sha256', 'provider_sha256', 'constructor_source_sha256'):
            _digest(fixed.get(name), name)
        # The wrapper hash binds bytes, but cannot make a contradictory base
        # manifest implement the solver contract. Check the arithmetic facts
        # used by the existing four-bit schedules independently of provenance.
        anchor_contract = dict(
            numerical_contract='correctly-rounded finite sequential features; exact rational metric; fixed base-only output-row dyadic24 grids; lower ties',
            grid_recipe='output-row-extrema-smallest-dyadic24-cover-with-exact-midpoints-v1',
            coordinate_order='input coordinate ascending; output row ascending; declared stage order',
            normalization_rule='original calibration token total; fixed for every retained subset',
            scale_fitting='base weights only; no calibration fitting or retained-data refit',
            significant_bits=24, code_count=16, code_min=-8, code_max=7,
            minimum_row_scale_hex='0x0.0000000000002p-1022',
            zero_row_scale_rule='minimum admissible positive scale; exact half-step midpoint required')
        if any(type(anchor.get(key)) is not type(expected) or anchor[key] != expected
               for key, expected in anchor_contract.items()):
            raise ValueError('unsupported anchor target numerical contract')
        if anchor.get('evaluator_id') != 'certified-decoder-v1:' + fixed['decoder_sha256']:
            raise ValueError('anchor evaluator and fixed decoder identities differ')
        recipe = anchor.get('recipe')
        if type(recipe) is not dict or recipe.get('schema') != 'fixed-target-recipe-v1':
            raise ValueError('unsupported target recipe')
        if type(recipe.get('bits')) is not int or recipe['bits'] != 4:
            raise ValueError('only the existing four-bit route policies are reviewed')
        original = _integer(recipe.get('original_token_count'), 'original token count')
        ridge = _rational_pair(recipe.get('ridge'), 'recipe ridge')
        stages = anchor.get('stages')
        if type(stages) is not list or not stages:
            raise ValueError('target must declare a nonempty ordered stage list')
        seen, bindings = [], []
        for index, stage in enumerate(stages):
            if type(stage) is not dict:
                raise ValueError('invalid stage object')
            sid = stage.get('stage_id')
            if type(sid) is not str or not sid or sid in seen:
                raise ValueError('stage IDs must be unique nonempty strings')
            shape = stage.get('shape')
            if type(shape) is not list or len(shape) != 2:
                raise ValueError('stage shape must contain rows and width')
            rows, width = (_integer(v, 'stage dimension') for v in shape)
            dependencies = stage.get('dependencies')
            if (type(dependencies) is not list or any(type(v) is not str for v in dependencies)
                    or len(dependencies) != len(seen) or set(dependencies) != set(seen)):
                raise ValueError('anchor dependencies must equal the complete stage prefix')
            norm = _rational_pair(stage.get('normalization'), 'stage normalization')
            stage_ridge = _rational_pair(stage.get('ridge'), 'stage ridge')
            if norm != (original, 1) or stage_ridge != ridge:
                raise ValueError('stage normalization or ridge differs from the original recipe')
            if stage.get('grid_axis') != 'output_row' or stage.get('significant_bits') != 24:
                raise ValueError('unsupported stage grid contract')
            scales = stage.get('row_scale_hex')
            if type(scales) is not list or len(scales) != rows:
                raise ValueError('one bound row scale is required per output row')
            for scale in scales:
                try:
                    value = float.fromhex(scale) if type(scale) is str else float('nan')
                except (ValueError, OverflowError) as exc:
                    raise ValueError('invalid finite positive row scale') from exc
                if not math.isfinite(value) or value <= 0 or value.hex() != scale:
                    raise ValueError('invalid canonical finite positive row scale')
                numerator = Fraction.from_float(value).numerator
                significant = numerator >> ((numerator & -numerator).bit_length() - 1)
                if (significant.bit_length() > 24
                        or value < float.fromhex(anchor_contract['minimum_row_scale_hex'])
                        or not math.isfinite(8 * value)):
                    raise ValueError('row scale cannot form the declared exact dyadic24 grid')
            _digest(stage.get('weights_sha256'), 'stage weights')
            bindings.append(StageBinding(index, sid, rows, width, 4, norm, stage_ridge,
                _sha(_json(stage)), _sha(self.fixed_payload), _sha(self.anchor_payload)))
            seen.append(sid)
        return original, tuple(bindings)

    @property
    def stages(self):
        return self._read()[1]

    @property
    def original_tokens(self):
        return self._read()[0]


def _sources():
    paths = (
        'research_v42/resource_plan.py', 'src/adaptive_calibration_v30.py',
        'src/ordered_fixed_service_v30.py',
        'src/native_token_coefficients_v30.py', 'src/native_box_coefficients_v31.py',
        'src/primal_certificate_v30.py', 'research_v35/direct_gram.py',
        'research_v37/direct_gram_ball.py', 'research_v40/streamed_primal_ball.py',
        'research_v40/policy.py',
        'src/dyadic_row_target.py', 'src/dyadic_row_quantizer.py',
        'src/fixed_anchor_target.py', 'src/anchor_transformer.py',
        'src/certified_transformer.py', 'src/target_manifest.py',
    )
    return {name: _sha((ROOT / name).read_bytes()) for name in paths}


def plan_request(target, retained_tokens, *, block_tokens=128):
    """Report every prospective stage; never select a route or authorize work.

    ``block_tokens`` is an upper bound, not a claim that all records have that
    size. The streamed assessment conservatively allows one nonempty block per
    retained token. Actual block layout and source residency remain unreviewed.
    """
    if type(target) is not BoundTarget:
        raise TypeError('target must be BoundTarget')
    _integer(retained_tokens, 'retained tokens', 0)
    _integer(block_tokens, 'block tokens')
    original, stages = target._read()
    if retained_tokens > original:
        raise ValueError('retained tokens exceed the bound original token count')
    # Imports call no native compilation or numerical solver. Authoritative
    # admission functions retain their existing policies without alteration.
    from src.adaptive_calibration_v30 import AdaptiveBudget, assess_routes
    from src.native_token_coefficients_v30 import assess_native_coefficients
    from src.native_box_coefficients_v31 import assess_native_box_coefficients
    from research_v37.direct_gram_ball import assess_direct_gram_ball_budget
    from research_v40.streamed_primal_ball import assess_streamed
    from research_v40.policy import point_budget

    token_budget, primal_budget = AdaptiveBudget(), point_budget()
    rows = []
    for stage in stages:
        full_token = assess_routes(stage.rows, stage.width, retained_tokens, budget=token_budget)['routes']['token']
        coefficients = assess_native_coefficients(stage.width, retained_tokens)
        token = dict(full_token, coefficient_assessment=coefficients,
            solver_admitted=full_token['admitted'] and coefficients['admitted'],
            complete_solver_assessed=True, row_and_bounded_fallback_reserved=True,
            max_exact_rank=0, max_exact_coordinates=0,
            max_refinement_coordinates=token_budget.max_refinement_coordinates,
            budget=asdict(token_budget))
        token.pop('admitted')
        token.pop('selection_work_units')
        token['solver_blockers'] = []
        if full_token['work_units'] > token_budget.max_work_units:
            token['solver_blockers'].append('complete_token_work_exceeds_existing_limit')
        if full_token['explicit_array_bytes'] > token_budget.max_workspace_bytes:
            token['solver_blockers'].append('complete_token_arrays_exceed_existing_limit')
        if not coefficients['admitted']:
            token['solver_blockers'].append('native_token_coefficients_refused')
        direct = assess_direct_gram_ball_budget(rows=stage.rows, width=stage.width,
                                               bits=stage.bits, budget=primal_budget)
        streamed = assess_streamed(rows=stage.rows, width=stage.width, tokens=retained_tokens,
            block_tokens=block_tokens, max_blocks=retained_tokens, bits=stage.bits, budget=primal_budget)
        routes = {'token_point': token}
        for name, assessment in (('direct_gram_ball', direct), ('streamed_primal_ball', streamed)):
            admitted = assessment.pop('admitted')
            routes[name] = dict(assessment, solver_admitted=admitted,
                complete_solver_assessed=True, row_and_bounded_fallback_reserved=True,
                budget=asdict(primal_budget),
                solver_blockers=[] if admitted else [assessment['refusal_reason']])
        box = assess_native_box_coefficients(stage.width, retained_tokens)
        routes['token_box'] = dict(coefficient_assessment=box, solver_admitted=False,
            complete_solver_assessed=False, row_and_bounded_fallback_reserved=False,
            solver_blockers=['complete_token_box_solver_and_fallback_not_reviewed'])
        for name, route in routes.items():
            route['route_admitted'] = False
            pending = list(COMMON_BLOCKERS)
            if name == 'direct_gram_ball':
                pending.append('exact_gram_accumulation_parsing_and_trusted_lineage_unreviewed')
            elif name in ('streamed_primal_ball', 'token_box'):
                pending.append('descriptor_loading_containment_and_fresh_fallback_unreviewed')
            route['route_blockers'] = route['solver_blockers'] + pending
        rows.append(dict(binding=asdict(stage), routes=routes,
            any_solver_admitted=any(r['solver_admitted'] for r in routes.values()),
            stage_admitted=False, selected_route=None))
    # This is the existing ordered point-service ceiling. No cumulative V40
    # full-model Gram/streamed allowance exists, so none is invented here.
    token_total = sum(row['routes']['token_point']['work_units'] for row in rows)
    token_cap = 48_000_000_000
    return dict(schema='prospective-stage-resource-plan-v42',
        target_sha256=_sha(target.fixed_payload), anchor_target_sha256=_sha(target.anchor_payload),
        original_tokens=original, retained_tokens=retained_tokens, stages=rows,
        streamed_block_tokens=block_tokens, streamed_max_blocks=retained_tokens,
        streamed_partition_policy='any nonempty partition within block_tokens; worst-case block count',
        solver_blocked_stage_ids=[r['binding']['stage_id'] for r in rows if not r['any_solver_admitted']],
        route_blocked_stage_ids=[r['binding']['stage_id'] for r in rows],
        token_cumulative=dict(work_units=token_total, existing_request_limit=token_cap,
            within_existing_limit=token_total <= token_cap,
            all_stage_solvers_admitted=all(r['routes']['token_point']['solver_admitted'] for r in rows),
            admitted=False, scope='full token solver reservations only; not complete request costs'),
        request_admitted=False, request_blockers=list(COMMON_BLOCKERS),
        solver_dispatch_implemented=False, canonical_state_oracle_implemented=False,
        numerical_arrays_allocated=False, empirical_worker_launched=False,
        whole_process_fit_guaranteed=False, wall_time_guaranteed=False,
        target_provenance_authenticated=False, source_sha256=_sources(),
        source_identity_scope='planner, structural admission helpers, and metadata contract references; not complete numerical execution provenance',
        scope='Existing solver structural admission only; no route selection, execution, or new resource allowance')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--anchor-target', type=Path, default=DEFAULT_TARGET_DIR / 'base-target.json')
    parser.add_argument('--fixed-target', type=Path, default=DEFAULT_TARGET_DIR / 'fixed-target.json')
    parser.add_argument('--retained-tokens', nargs='+', type=int, default=[768, 1536])
    parser.add_argument('--block-tokens', type=int, default=128)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    target = BoundTarget(args.anchor_target.read_bytes(), args.fixed_target.read_bytes())
    plans = [plan_request(target, n, block_tokens=args.block_tokens) for n in args.retained_tokens]
    report = dict(schema='prospective-resource-plan-cases-v42', cases=plans)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(_json(report) + b'\n')
    print(json.dumps([dict(retained_tokens=p['retained_tokens'],
        solver_blocked_stage_ids=p['solver_blocked_stage_ids'], request_admitted=False) for p in plans]))


if __name__ == '__main__':
    main()
