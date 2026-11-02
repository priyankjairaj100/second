"""A service identity around the unchanged V59 numerical calibration target.

The embedded V59 payload still promises model codes only. This distinct wrapper
declares the V61 state/access contract and binds its feature provider; it never
masquerades as the historical nearest-anchor target. Metadata validation checks
arithmetic consistency and identity, not trusted execution or feature provenance.
"""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

from src.run_store import canonical_json, digest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'fixed-full-precision-anchor-service-target-v61'
FAMILY = 'full_precision_anchor_service_v61'
STATE_SCHEMA = 'complete-full-precision-anchor-successor-v61'
FEATURE_RULE = 'each stage uses source-local features from original full-precision checkpoint weights'
ANCHOR_RULE = 'original pinned binary64 checkpoint stage matrices; no quantized matrix is installed'
MAX_TARGET_BYTES = 32*2**20

BASE_CONTRACT = dict(
    schema='fixed-v-cert-dyadic-row-grid-diagnostic-target-v1',
    numerical_contract='correctly-rounded finite sequential features; exact rational metric; fixed base-only output-row dyadic24 grids; lower ties',
    grid_recipe='output-row-extrema-smallest-dyadic24-cover-with-exact-midpoints-v1',
    coordinate_order='input coordinate ascending; output row ascending; declared stage order',
    normalization_rule='original calibration token total; fixed for every retained subset',
    scale_fitting='base weights only; no calibration fitting or retained-data refit',
    significant_bits=24, code_count=16, code_min=-8, code_max=7,
    minimum_row_scale_hex='0x0.0000000000002p-1022',
    zero_row_scale_rule='minimum admissible positive scale; exact half-step midpoint required',
    weight_digest_encoding='binary64_matrix_v1',
    base_parameter_rule='quantized base entries must equal their binary64 conversions',
    token_program='nonempty token IDs; positions reset per record; inclusive causal mask; no padding',
    attention_scope='record local; no cross-record state',
    fixed_components='embeddings, positions, norms, biases, and final language-model head',
    output_rule='complete stage codes only; no canonical repair-state contract declared',
    deleted_source_rule='retained-record code target; no deletion-service access contract declared',
    failure_rule='bounded exact fallback for unresolved cells; exhausted budget or finite evaluator failure aborts')
BASE_SOURCE_KEYS = ('constructor_source_sha256', 'exact_core_source_sha256', 'dyadic_constructor_source_sha256',
    'dyadic_solver_source_sha256', 'batched_solver_source_sha256', 'token_solver_source_sha256')
SERVICE_CONTRACT = dict(schema=SCHEMA, state_family=FAMILY, state_schema=STATE_SCHEMA,
    feature_rule=FEATURE_RULE, anchor_rule=ANCHOR_RULE,
    prefix_rule='calibrated output codes never affect any feature',
    normalization_rule='unchanged original normalization from embedded calibration target',
    output_rule='complete calibrated stage codes and canonical retained-source service state',
    representation_rule='lossless V29; compressed48 V26 bits48/block256; exact_gram V35; hybrid exact_gram width<=768 else lossless',
    deleted_source_rule='retain source-local descriptors unchanged; exact Gram subtraction requires trusted removed-source contributions',
    trust_rule='trusted preparation or independent reconstruction establishes feature containment and Gram lineage; digests provide identity only')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, name):
    _require(type(value) is int and value > 0, name+' must be a positive built-in integer')
    return value


def _digest(value, name):
    _require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value),
        name+' must be a lowercase SHA-256 digest')
    return value


def _pair(value, name):
    _require(type(value) is list and len(value) == 2 and all(type(v) is int and v > 0 for v in value),
        name+' must be a positive rational pair')
    q = Fraction(*value)
    _require([q.numerator, q.denominator] == value, name+' must be reduced')
    return tuple(value)


def _object(blob, name):
    if type(blob) is not bytes:
        raise TypeError(name+' must be immutable canonical bytes')
    _require(len(blob) <= MAX_TARGET_BYTES, name+' exceeds target byte bound')
    try:
        value = json.loads(blob)
        canonical = canonical_json(value)
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise ValueError(name+' is not canonical JSON') from error
    _require(type(value) is dict and canonical == blob, name+' must be a canonical JSON object')
    return value


def _source(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provider_binding():
    """Provider source identity; campaign/runtime admission supplies trust."""
    return _source(Path(__file__).with_name('features.py'))


def _calibration_manifest(base, implementation_manifest_sha256):
    """Exact frozen V59 manifest contract, derived without loading any weights."""
    _require(type(base['evaluator_id']) is str and base['evaluator_id'].startswith('certified-decoder-v1:'),
        'Unsupported base evaluator identity')
    decoder_hash = base['evaluator_id'].removeprefix('certified-decoder-v1:')
    _digest(decoder_hash, 'base decoder')
    _require(base['evaluator_id'] == 'certified-decoder-v1:'+decoder_hash, 'Unsupported base evaluator identity')
    return dict(schema='fixed-full-precision-anchor-calibration-target-v59',
        base_target_sha256=digest(canonical_json(base)), decoder_sha256=decoder_hash,
        implementation_manifest_sha256=_digest(implementation_manifest_sha256, 'implementation manifest'),
        constructor_source_sha256=_source(ROOT/'research_v59/anchor.py'),
        feature_rule=FEATURE_RULE, anchor_rule=ANCHOR_RULE,
        prefix_rule='calibrated output codes never affect any feature', calibrated_dependencies='empty for every stage',
        original_normalization=base['recipe']['original_token_count'],
        normalization_rule='unchanged original normalization from base target',
        grid_rule='unchanged base-only dyadic24 output-row grids; lower midpoint ties',
        record_rule='positions reset per source; causal within source; no cross-source state',
        teacher_weight_digest_encoding='binary64-matrix-little-endian-row-major-v1',
        teacher_stages=[dict(stage_id=s['stage_id'], shape=s['shape'], weights_sha256=s['weights_sha256']) for s in base['stages']],
        output_rule='complete stage codes only; no canonical repair-state contract declared',
        failure_rule='bounded certified stage solver; unresolved or exhausted resource budget aborts')


def _service_manifest(base, calibration):
    return dict(SERVICE_CONTRACT, anchor_target_sha256=digest(canonical_json(base)),
        calibration_target=calibration, calibration_target_sha256=digest(canonical_json(calibration)),
        decoder_sha256=calibration['decoder_sha256'],
        implementation_manifest_sha256=calibration['implementation_manifest_sha256'],
        provider_sha256=provider_binding(), constructor_source_sha256=_source(__file__))


@dataclass(frozen=True)
class ServiceTarget:
    calibration_target: object
    payload_bytes: bytes

    @property
    def base_target(self):
        return self.calibration_target.base_target

    @property
    def stages(self):
        return self.calibration_target.stages

    @property
    def recipe(self):
        return self.calibration_target.recipe

    @property
    def digest(self):
        return digest(self.payload_bytes)

    def payload(self):
        return json.loads(self.payload_bytes)


def build_service_target(decoder, base_target):
    from research_v59.anchor import build_full_precision_anchor_target
    calibration = build_full_precision_anchor_target(decoder, base_target)
    payload = canonical_json(_service_manifest(base_target.payload(), calibration.payload()))
    BoundTarget(canonical_json(base_target.payload()), payload)
    return ServiceTarget(calibration, payload)


@dataclass(frozen=True)
class StageBinding:
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
    """Immutable V61 base/service bytes; this is not the nearest BoundTarget.

No metadata-only validator can prove that source features were actually produced
by its teacher. Preparation, replay, external Gram trust, and independent fresh
reconstruction retain those obligations. This frozen source family rejects
foreign provider/constructor versions instead of silently relabeling states.
"""
    anchor_payload: bytes
    fixed_payload: bytes

    def __post_init__(self):
        self._read()

    def _read(self):
        base, service = _object(self.anchor_payload, 'base target'), _object(self.fixed_payload, 'V61 service target')
        base_keys = set(BASE_CONTRACT) | set(BASE_SOURCE_KEYS) | {'recipe', 'evaluator_id', 'service_sources_sha256', 'stages'}
        _require(set(base) == base_keys, 'Unsupported base manifest fields')
        _require(all(type(base[k]) is type(v) and base[k] == v for k, v in BASE_CONTRACT.items()),
            'Unsupported base numerical contract')
        for name in BASE_SOURCE_KEYS:
            _digest(base[name], name)
        sources = base['service_sources_sha256']
        _require(type(sources) is dict and 0 < len(sources) <= 256, 'Invalid base source manifest')
        for name, value in sources.items():
            _require(type(name) is str and 0 < len(name) <= 512, 'Invalid base source name')
            _digest(value, 'base source')
        recipe = base['recipe']
        _require(type(recipe) is dict and set(recipe) == {'schema', 'original_token_count', 'bits', 'ridge', 'group_count', 'max_grid_entries'}
            and recipe['schema'] == 'fixed-target-recipe-v1' and type(recipe['bits']) is int and recipe['bits'] == 4,
            'Unsupported complete base recipe')
        original = _integer(recipe['original_token_count'], 'original tokens')
        ridge = _pair(recipe['ridge'], 'ridge')
        _integer(recipe['group_count'], 'group count')
        max_grid_entries = _integer(recipe['max_grid_entries'], 'grid entry limit')
        entries = base['stages']
        _require(type(entries) is list and 0 < len(entries) <= 256, 'Bounded nonempty complete stage list required')
        seen, shapes, grid_entries = [], [], 0
        for entry in entries:
            _require(type(entry) is dict and set(entry) == {'stage_id', 'dependencies', 'shape', 'weights_sha256',
                'ridge', 'normalization', 'grid_axis', 'row_scale_hex', 'significant_bits'}, 'Unsupported base stage fields')
            sid = entry['stage_id']
            _require(type(sid) is str and 0 < len(sid.encode('utf-8')) <= 512 and '\x00' not in sid and sid not in seen,
                'Unique nonempty stage ID required')
            shape = entry['shape']
            _require(type(shape) is list and len(shape) == 2, 'Stage shape must have rows and width')
            rows, width = (_integer(value, 'stage dimension') for value in shape)
            deps = entry['dependencies']
            _require(type(deps) is list and all(type(v) is str for v in deps) and len(deps) == len(seen) and set(deps) == set(seen),
                'Base dependencies must contain the complete original prefix')
            norm, stage_ridge = _pair(entry['normalization'], 'stage normalization'), _pair(entry['ridge'], 'stage ridge')
            _require(norm == (original, 1) and stage_ridge == ridge, 'Stage normalization or ridge differs from base recipe')
            _require(entry['grid_axis'] == 'output_row' and type(entry['significant_bits']) is int and entry['significant_bits'] == 24,
                'Unsupported stage row-grid contract')
            scales = entry['row_scale_hex']
            _require(type(scales) is list and len(scales) == rows, 'One row scale required per output row')
            for scale in scales:
                try:
                    value = float.fromhex(scale) if type(scale) is str else float('nan')
                except (ValueError, OverflowError) as error:
                    raise ValueError('Invalid dyadic24 scale') from error
                _require(math.isfinite(value) and value > 0 and value.hex() == scale, 'Canonical finite positive scale required')
                numerator = Fraction.from_float(value).numerator
                significant = numerator >> ((numerator & -numerator).bit_length()-1)
                _require(significant.bit_length() <= 24 and value >= float.fromhex(BASE_CONTRACT['minimum_row_scale_hex'])
                    and math.isfinite(8*value), 'Row scale cannot form exact finite dyadic24 grid and midpoints')
            _digest(entry['weights_sha256'], 'original teacher stage weights')
            grid_entries += rows*16
            shapes.append((sid, rows, width, norm, stage_ridge, digest(canonical_json(entry))))
            seen.append(sid)
        _require(grid_entries <= max_grid_entries, 'Complete row grids exceed original recipe limit')
        service_keys = set(SERVICE_CONTRACT) | {'anchor_target_sha256', 'calibration_target', 'calibration_target_sha256',
            'decoder_sha256', 'implementation_manifest_sha256', 'provider_sha256', 'constructor_source_sha256'}
        _require(set(service) == service_keys, 'A complete V61 service wrapper is required')
        _require(all(type(service[k]) is type(v) and service[k] == v for k, v in SERVICE_CONTRACT.items()),
            'Unsupported V61 service contract')
        calibration = service['calibration_target']
        _require(type(calibration) is dict, 'Embedded exact V59 calibration manifest required')
        expected = _calibration_manifest(base, service['implementation_manifest_sha256'])
        _require(canonical_json(calibration) == canonical_json(expected),
            'Embedded V59 teacher manifest differs from the bound base or frozen contract')
        _require(canonical_json(service) == canonical_json(_service_manifest(base, calibration)),
            'V61 service digest, decoder, provider or constructor binding differs')
        bindings = tuple(StageBinding(i, sid, rows, width, 4, norm, sridge, stage_hash,
            digest(self.fixed_payload), digest(self.anchor_payload))
            for i, (sid, rows, width, norm, sridge, stage_hash) in enumerate(shapes))
        return original, bindings, service['calibration_target_sha256']

    @property
    def stages(self):
        return self._read()[1]

    @property
    def original_tokens(self):
        return self._read()[0]

    @property
    def calibration_target_sha256(self):
        return self._read()[2]
