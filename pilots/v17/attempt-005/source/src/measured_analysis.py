"""Artifact-verified analysis of frozen measured campaigns; never executes models.

Only loaders issue VerifiedMeasuredEvidence. A dictionary of asserted equality or
timing fields is not evidence. This is consistency verification in a trusted local
archive, not authentication against an adversary who can rewrite the entire store.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
import hashlib
import os
from pathlib import Path
import statistics
import stat

from .result_analysis import AnalysisError, root_interval
from .run_store import canonical_json, digest, strict_json
from .transaction_timing import BOUNDARY

METHODS = ('model_only_fresh', 'repair', 'indexed_fresh', 'direct_fresh')
FRESH_CACHE = 'fresh_transaction_os_cache_uncontrolled'
_ISSUER = object()


class MeasuredAnalysisError(AnalysisError):
    pass


class VerifiedMeasuredEvidence:
    """Detached, immutable loader output; not a cryptographic capability."""
    __slots__ = ('_raw',)

    def __init__(self, payload, *, _issuer=None):
        if _issuer is not _ISSUER:
            raise MeasuredAnalysisError('use an artifact-aware evidence loader')
        validate_measured_evidence_structure(payload)
        object.__setattr__(self, '_raw', canonical_json(payload))

    def __setattr__(self, name, value):
        raise AttributeError('verified evidence is immutable')

    def payload(self):
        return strict_json(self._raw)

    @property
    def sha256(self):
        return digest(self._raw)


def _int(value, label, minimum=0):
    if type(value) is not int or value < minimum or value.bit_length() > 128:
        raise MeasuredAnalysisError(label + ' requires a bounded integer')
    return value


def _read(path, expected=None):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
        raise MeasuredAnalysisError('missing or symbolic evidence: ' + str(path))
    raw = path.read_bytes()
    if expected is not None and digest(raw) != expected:
        raise MeasuredAnalysisError('evidence hash changed: ' + str(path))
    value = strict_json(raw)
    if raw != canonical_json(value):
        raise MeasuredAnalysisError('receipt is not canonical JSON')
    return value, digest(raw)


def _clean(state):
    if type(state) is not dict or state.get('schema') != 'calibration-instrumentation-v1':
        return False
    return (state.get('mode') == 'clean'
        and all(state.get(key) is False for key in (
            'python_profiler_active', 'python_trace_active', 'allocation_tracing_active',
            'global_monitoring_active', 'monitoring_tools_allocated', 'detailed_service_telemetry'))
        and state.get('required_arithmetic_counters_retained') is True
        and state.get('external_native_profiler_status') == 'unobserved')


def _partition(receipt):
    wall = _int(receipt.get('observed_wall_ns'), 'observed wall')
    spans = receipt.get('timing_spans')
    if type(spans) is not list or not spans:
        raise MeasuredAnalysisError('observer lacks its accounting partition')
    cursor = 0
    for span in spans:
        if type(span) is not dict or _int(span.get('start_offset_ns'), 'span start') != cursor:
            raise MeasuredAnalysisError('overlapping or missing observer clock span')
        end = _int(span.get('end_offset_ns'), 'span endpoint')
        if end < cursor or _int(span.get('wall_ns'), 'span wall') != end - cursor:
            raise MeasuredAnalysisError('invalid observer clock span')
        cursor = end
    if cursor != wall or _int(receipt.get('accounting_sum_ns'), 'accounting sum') != wall:
        raise MeasuredAnalysisError('observer clock partition does not cover its transaction')
    return wall


def _child_projection(child, row, target):
    """Detached facts from a verified child; unavailable diagnostics stay null."""
    result = {'child_receipt_path': row.get('child_receipt_path'),
        'child_receipt_sha256': row.get('child_receipt_sha256'),
        'child_outcome': child.get('outcome'), 'target_graph': None, 'target_manifest': None,
        'stage_audits': child.get('artifact', {}).get('stages'),
        'ledger': child.get('artifact', {}).get('ledger', child.get('ledger')),
        'index_preparation_ledger': child.get('index_preparation_ledger'),
        'service_telemetry': child.get('service_telemetry'),
        'quality_payload': child.get('quality')}
    manifest = child.get('preflight', {}).get('target')
    if type(manifest) is dict and digest(canonical_json(manifest)) == target:
        stages = manifest.get('stages')
        if type(stages) is not list or not stages:
            raise MeasuredAnalysisError('verified target lacks its stage graph')
        parents = {}; order = []
        for stage in stages:
            name, dependencies = stage.get('stage_id'), stage.get('dependencies')
            if (type(name) is not str or not name or name in parents or type(dependencies) is not list
                    or len(set(dependencies)) != len(dependencies) or any(p not in parents for p in dependencies)):
                raise MeasuredAnalysisError('invalid verified target dependency order')
            order.append(name); parents[name] = dependencies
        result.update(target_graph={'stage_order': order, 'parents': parents}, target_manifest=manifest)
    else:
        result['target_projection_unavailable_reason'] = 'missing_or_mismatched_child_target'
    return strict_json(canonical_json(result))


def _input_projection(manifest, manifest_path, *, quality=False):
    """Read bound token artifacts only; do not load a model or invent provenance."""
    from .experiment_runner import _referenced_json, _local
    result = {}
    for role in ('calibration', 'heldout') if quality else ('calibration',):
        value, raw = _referenced_json(Path(manifest_path).parent, manifest[role])
        rows = value.get('records')
        if type(rows) is not list:
            raise MeasuredAnalysisError('bound token artifact has no record list')
        counts = {}
        for row in rows:
            if (type(row) is not dict or type(row.get('id')) is not str or not row['id']
                    or row['id'] in counts or type(row.get('tokens')) is not list or not row['tokens']
                    or any(type(token) is not int or token < 0 for token in row['tokens'])):
                raise MeasuredAnalysisError('invalid bound token metadata')
            counts[row['id']] = len(row['tokens'])
        result[role + '_reference'] = {'path': str(_local(Path(manifest_path).parent, manifest[role]['path'])),
            'sha256': digest(raw), 'bytes': len(raw)}
        if role == 'calibration':
            result.update(record_token_counts=counts, source_provenance=value.get('provenance'),
                          source_provenance_verification='bound assertion only; real-source provenance not independently established')
        else:
            if any(n < 2 for n in counts.values()):
                raise MeasuredAnalysisError('heldout record lacks a prediction target')
            result.update(heldout_record_token_counts=counts,
                          heldout_target_tokens=sum(n - 1 for n in counts.values()))
    return result


def _role(row, *, target, execution_mode, seen, slot, role):
    """Re-read primary artifacts; do not accept convenience equality/time flags."""
    if type(row) is not dict:
        raise MeasuredAnalysisError('invalid method row')
    if not row.get('timing_receipt_path'):
        if row.get('status') not in ('not_started', 'not_requested', 'failed', 'running', 'missing', None):
            raise MeasuredAnalysisError('completed role lacks an observer receipt')
        return {'outcome': row.get('status') or 'not_started', 'wall_ns': None,
                'observed_wall_ns': None, 'exact_model': None, 'exact_state': None,
                'failure': row.get('failure')}
    from .measured_comparison import verify_role, _common_model, _read_ref
    derived = verify_role(row, expected_target=target)
    receipt, sha = _read(row['timing_receipt_path'], row.get('timing_receipt_sha256'))
    if receipt.get('schema') != 'measured-transaction-receipt-v1':
        raise MeasuredAnalysisError('unsupported transaction receipt')
    identity, identity_sha = _read(Path(row['timing_receipt_path']).parent / 'identity.json')
    if identity_sha != receipt.get('identity_sha256'):
        raise MeasuredAnalysisError('observer identity differs')
    observation = (identity_sha, receipt.get('attempt'))
    if observation in seen:
        raise MeasuredAnalysisError('one original timing observation occupies multiple planned roles or repetitions')
    seen[observation] = (slot, role)
    wall = _partition(receipt)
    contract = ('model_only' if role == 'model_only_fresh' else
                'quality_evaluation' if role == 'quality' else 'canonical_state')
    if receipt.get('output_contract') != contract or row.get('output_contract') != contract:
        raise MeasuredAnalysisError('method output contract differs')
    if (receipt.get('measurement_boundary') != BOUNDARY
            or row.get('service_boundary') != BOUNDARY):
        raise MeasuredAnalysisError('method transaction boundary differs')
    if row.get('wall_time_ns') != wall or (derived.get('status') != 'failed'
            and row.get('complete_wall_time_ns') != receipt.get('complete_transaction_wall_ns')):
        raise MeasuredAnalysisError('convenience timing differs from observer')
    evidence = {'outcome': 'incomplete_transaction', 'wall_ns': None,
        'observed_wall_ns': wall, 'receipt_sha256': sha, 'receipt_path': row['timing_receipt_path'],
        'observation_id': identity_sha + ':' + str(receipt.get('attempt')),
        'output_contract': contract, 'boundary': BOUNDARY, 'cache_mode': receipt.get('cache_mode'),
        'execution_mode': execution_mode, 'target_manifest_sha256': target,
        'exact_model': None, 'exact_state': None, 'model_sha256': None, 'state_sha256': None,
        'worker_resource_usage': receipt.get('worker_resource_usage'),
        'budget_debit': receipt.get('budget_debit'), 'worker_outcome': receipt.get('worker_outcome'),
        'source_sha256': receipt.get('source_sha256')}
    worker_path = Path(row['timing_receipt_path']).parent / receipt['attempt'] / 'worker' / 'result.json'
    tree_path = Path(row['timing_receipt_path']).parent / receipt['attempt'] / 'transaction-tree.json'
    tree, _ = _read(tree_path)
    sizes = [_int(item.get('bytes'), 'artifact bytes') for item in tree.values()]
    evidence.update(max_artifact_bytes=max(sizes, default=0), transaction_artifact_bytes=sum(sizes),
                    artifact_size_scope='all files in observer-verified transaction tree; excludes observer archive')
    if worker_path.is_file():
        worker, worker_sha = _read(worker_path)
        worker_identity, _ = _read(worker_path.parent / 'identity.json')
        evidence.update(worker_id=worker.get('identity_sha256'), worker_receipt_sha256=worker_sha,
                        worker_limits=worker.get('limits'), budget_attempt_id=worker.get('budget_attempt_id'),
                        worker_phase_budget_binding=worker_identity.get('phase_budget'))
    child = None
    if row.get('child_receipt_path'):
        child, child_sha = _read(row['child_receipt_path'], row.get('child_receipt_sha256'))
        evidence.update(_child_projection(child, row, target))
        evidence['child_receipt_sha256'] = child_sha
    if derived.get('status') == 'failed':
        evidence.update(outcome=derived.get('failure', {}).get('kind', 'failed'), failure=derived.get('failure'))
        return evidence
    if receipt.get('outcome', {}).get('status') != 'complete':
        evidence['failure'] = receipt.get('outcome')
        return evidence
    if child is None:
        raise MeasuredAnalysisError('successful observation lacks a child projection')
    if child.get('outcome', {}).get('status') != 'complete':
        raise MeasuredAnalysisError('completed observer contradicts child outcome')
    child_state = child.get('instrumentation_state', child.get('instrumentation'))
    observer_state = receipt.get('instrumentation_state')
    evidence.update(child_receipt_sha256=child_sha, instrumentation_state=child_state,
                    observer_instrumentation_state=observer_state)
    if role == 'quality':
        quality_path = Path(row['child_receipt_path']).parent / child['attempt'] / 'quality.json'
        quality, quality_sha = _read(quality_path)
        if child.get('quality') != quality:
            raise MeasuredAnalysisError('quality convenience payload differs from committed artifact')
        request, request_sha = _read(row['request_reference']['path'], row['request_reference']['sha256'])
        evidence.update(outcome='complete_quality', wall_ns=None,
            quality_payload=quality, quality_artifact_reference={'path': str(quality_path), 'sha256': quality_sha},
            quality_state_references=request.get('quality_states'), quality_request_sha256=request_sha,
            quality_manifest_sha256=request.get('manifest_sha256'))
        return evidence
    model = _common_model(_read_ref(row['original_model_reference']), target)
    common = _read_ref(row['model_reference'])
    if model != common or digest(model) != row.get('common_model_sha256'):
        raise MeasuredAnalysisError('common target model encoding differs from actual output')
    evidence['model_sha256'] = digest(model)
    evidence['stage_code_sha256'] = {stage['stage_id']: digest(canonical_json(stage['codes']))
                                    for stage in strict_json(model)['stages']}
    if contract == 'canonical_state':
        state_raw = _read_ref(row['state_reference'])
        evidence['state_sha256'] = digest(state_raw)
        state = strict_json(state_raw)
        evidence['record_ids'] = [record['id'] for record in state['records']]
        evidence['record_groups'] = ({record['id']: str(record['group']) for record in state['records']}
                                     if 'groups' in state else None)
        evidence['canonical_group_membership'] = ({str(group['group']): group['ids'] for group in state['groups']}
                                                if 'groups' in state else None)
    else:
        evidence['retained_record_count'] = child.get('retained_records')
    complete_wall = _int(receipt.get('complete_transaction_wall_ns'), 'complete wall', 1)
    if complete_wall != wall:
        raise MeasuredAnalysisError('complete clock differs from observed clock')
    if (receipt.get('eligible_fresh_transaction_latency') is not True
            or receipt.get('child_output_contract_verified') is not True
            or receipt.get('cache_mode') != FRESH_CACHE):
        evidence['outcome'] = 'ineligible_transaction'
    elif (execution_mode != 'clean' or row.get('execution_mode') != 'clean'
            or child.get('execution_mode') != 'clean' or row.get('profiler_active') is not False
            or not _clean(child_state) or not _clean(observer_state)):
        evidence['outcome'] = 'diagnostic_timing'
    else:
        evidence.update(outcome='completed_unverified', wall_ns=wall)
    return evidence


def _exact(rows):
    """All four same-target artifacts are required, including the fresh oracle."""
    models = [rows[name].get('model_sha256') for name in METHODS]
    states = [rows[name].get('state_sha256') for name in ('repair', 'indexed_fresh', 'direct_fresh')]
    known = all(x is not None for x in models + states)
    equal_model = len(set(models)) == 1 if known else None
    equal_state = len(set(states)) == 1 if known else None
    for name, row in rows.items():
        row['exact_model'] = equal_model
        row['exact_state'] = equal_state if name != 'model_only_fresh' else None
        if row['outcome'] == 'completed_unverified':
            row['outcome'] = ('exact_complete' if equal_model and equal_state else
                              'mismatch' if known else 'not_verified')


def _missing(kind='missing_run'):
    return {'outcome': kind, 'wall_ns': None, 'observed_wall_ns': None,
            'exact_model': None, 'exact_state': None}


def validate_measured_evidence_structure(payload):
    """Check the public payload shape; this does not verify or upgrade evidence."""
    if (type(payload) is not dict or payload.get('schema') != 'verified-measured-evidence-v1'
            or payload.get('kind') not in ('single_request', 'sequence_lifetime')):
        raise MeasuredAnalysisError('unsupported measured evidence structure')
    for name in ('inventory_sha256', 'protocol_sha256'):
        value = payload.get(name)
        if type(value) is not str or len(value) != 64 or any(x not in '0123456789abcdef' for x in value):
            raise MeasuredAnalysisError('invalid ' + name)
    slots = payload.get('slots')
    if type(slots) is not list or not slots:
        raise MeasuredAnalysisError('evidence requires planned slots')
    identities = set()
    methods = set(METHODS if payload['kind'] == 'single_request' else ('repair', 'indexed_fresh', 'model_only_fresh'))
    for slot in slots:
        if type(slot) is not dict:
            raise MeasuredAnalysisError('invalid planned slot')
        for name in ('run_id', 'configuration_id', 'phase', 'root_id', 'request_id'):
            if type(slot.get(name)) is not str or not slot[name]:
                raise MeasuredAnalysisError('invalid planned ' + name)
        _int(slot.get('repeat_index'), 'planned repetition')
        identity = tuple(slot[name] for name in ('configuration_id', 'phase', 'root_id', 'request_id', 'repeat_index'))
        if identity in identities:
            raise MeasuredAnalysisError('duplicate planned repetition')
        identities.add(identity)
        if type(slot.get('methods')) is not dict or set(slot['methods']) != methods:
            raise MeasuredAnalysisError('planned methods omitted from evidence')
        for row in slot['methods'].values():
            if type(row) is not dict or type(row.get('outcome')) is not str:
                raise MeasuredAnalysisError('invalid method outcome')
            if row.get('wall_ns') is not None:
                _int(row['wall_ns'], 'complete method clock', 1)
            if row['outcome'] == 'exact_complete' and row.get('wall_ns') is None:
                raise MeasuredAnalysisError('exact completion lacks a usable clock')
    return strict_json(canonical_json(payload))


def _match(record, expected, fields):
    for field in fields:
        if record.get(field) != expected.get(field):
            raise MeasuredAnalysisError('archive differs from frozen ' + field)


def _settings(protocol):
    analysis = protocol.get('analysis', {})
    result = {key: analysis.get('bootstrap_' + key if key in ('seed', 'draws') else key, default)
              for key, default in (('seed', 20261004), ('draws', 2000), ('confidence', .95))}
    root_interval([], **result)
    threshold = protocol.get('gates', {}).get('reliable_speed_lower_interval_minimum', 1.05)
    if type(threshold) not in (float, int) or not math.isfinite(threshold) or threshold <= 1:
        raise MeasuredAnalysisError('invalid frozen speed threshold')
    result['threshold'] = threshold
    return result


def _base(checked, kind, group):
    protocol = checked['protocol']
    return {'schema': 'verified-measured-evidence-v1', 'kind': kind, 'analysis_group': group,
        'inventory_sha256': checked['inventory_sha256'], 'protocol_sha256': checked['protocol_sha256'],
        'protocol_status': checked['protocol'].get('status'),
        'protocol_blocked_fields': checked['protocol'].get('blocked_fields'),
        'settings': _settings(checked['protocol']), 'slots': [],
        'primary_baseline': protocol.get('primary_baseline'), 'primary_candidate': protocol.get('candidate'),
        'primary_comparison_count': protocol.get('analysis', {}).get('primary_comparison_count'),
        'primary_configuration': protocol.get('primary_configuration'),
        'inference_settings_frozen': all(k in protocol.get('analysis', {}) for k in
            ('bootstrap_seed', 'bootstrap_draws', 'confidence')) and
            'reliable_speed_lower_interval_minimum' in protocol.get('gates', {}),
        'scientific_provenance': 'not_established_by_archive_consistency',
        'trust_scope': 'hash-bound local artifacts; not hostile-store authentication',
        'boundary': BOUNDARY, 'external_native_profiler_status': 'unobserved'}


def _slot(entry, plan, protocol_sha):
    manifest = entry['manifest_payload']
    result = {k: entry[k] for k in ('run_id', 'configuration_id', 'phase', 'root_id', 'repeat_index')}
    result.update(request_id=entry.get('request_id', entry.get('sequence_id')),
        target_manifest_sha256=entry['target_manifest_sha256'], protocol_sha256=protocol_sha,
        source_sha256=plan['source_sha256'], execution_mode=plan['execution_mode'],
        service_family=manifest.get('service_family', 'response'),
        response_tier=manifest.get('chart', {}).get('response_tier', 'linear') if manifest.get('chart') else 'linear',
        service_mode=manifest.get('service_mode', 'certified'),
        verifier_policy=manifest.get('verifier_policy', 'spectral'))
    result['configuration_sha256'] = digest(canonical_json({
        'target_manifest_sha256': result['target_manifest_sha256'], 'chart': manifest.get('chart'),
        **{k: result[k] for k in ('service_family', 'response_tier', 'service_mode', 'verifier_policy')}}))
    return result


def _retained(rows, expected):
    """State records validate retained membership; model-only uses bound inputs/count."""
    for row in rows.values():
        if row.get('model_sha256') is None:
            continue
        if 'record_ids' in row and sorted(row['record_ids']) != sorted(expected):
            raise MeasuredAnalysisError('canonical state retained IDs differ from frozen request')
        if 'retained_record_count' in row and row['retained_record_count'] != len(expected):
            raise MeasuredAnalysisError('model-only retained count differs from frozen request')
        row['record_ids'] = sorted(expected)
        row['retained_ids_sha256'] = digest(canonical_json(sorted(expected)))


def _quality_binding(quality, slot, preparation, methods):
    """Bind successful metrics to the exact states and heldout token artifact."""
    if quality.get('outcome') != 'complete_quality':
        return quality
    reference = slot.get('heldout_reference')
    if reference is None or slot.get('heldout_target_tokens') is None:
        raise MeasuredAnalysisError('quality lacks bound heldout token metadata')
    expected = {'original': preparation.get('state_sha256'),
                'direct_fresh': methods['direct_fresh'].get('state_sha256'),
                'repair': methods['repair'].get('state_sha256')}
    actual = quality.get('quality_state_references')
    if (type(actual) is not dict or set(actual) != set(expected)
            or any(value is None or actual[name].get('sha256') != value for name, value in expected.items())):
        raise MeasuredAnalysisError('quality state bindings differ from the measured outputs')
    metrics = quality.get('quality_payload')
    if type(metrics) is not dict or set(metrics) != {'base', 'original', 'direct_fresh', 'repair'}:
        raise MeasuredAnalysisError('quality omitted planned models')
    if any(metric.get('target_tokens') != slot['heldout_target_tokens'] for metric in metrics.values()):
        raise MeasuredAnalysisError('quality denominator differs from heldout input')
    quality.update(heldout_reference=reference, heldout_target_tokens=slot['heldout_target_tokens'])
    return quality


def _resource_snapshots(checked, output_root):
    """Whole output-root files and actual protocol ledger, never global claims."""
    from .phase_budget import read_budget_snapshot
    from .run_store import read_completed
    from .transaction_timing import verify_observer_receipt
    inventory = checked['inventory']
    sources = inventory.get('ordered_inventory', inventory)['source_sha256']
    sources = {name: sha for name, sha in sources.items() if name.startswith('src/')
               or (name.startswith('scripts/run_') and name.endswith('.py'))}
    ledger = read_budget_snapshot(Path(checked['protocol_path']).parent / ('phase-cpu-budget-' + checked['protocol_sha256']),
        identity={'protocol_sha256': checked['protocol_sha256'], 'source_sha256': sources},
        phase_cpu_seconds=checked['phase_cpu_seconds'])
    root = Path(output_root).absolute()
    scope = 'all regular files under this campaign output root at read time; not input, project, allocated-disk or global storage'
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise MeasuredAnalysisError('symbolic archive storage root')
    if not root.exists():
        return ledger, {'status': 'unavailable', 'reason': 'output_root_missing', 'scope': scope,
                        'files': None, 'total_unique_file_bytes': None, 'workers': None}
    if not root.is_dir():
        raise MeasuredAnalysisError('archive storage root is not a directory')
    files = {}; signatures = {}; inodes = {}; transaction_roots = []; workers = []; unique_bytes = 0
    limit_files, limit_file_bytes, limit_total = 200000, 1 << 30, 64 << 30
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise MeasuredAnalysisError('symbolic archived file')
        if path.is_dir():
            continue
        if len(files) >= limit_files:
            raise MeasuredAnalysisError('archive file inventory exceeds bound')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit_file_bytes:
                raise MeasuredAnalysisError('archive file is not bounded regular data')
            h = hashlib.sha256(); size = 0
            while chunk := os.read(fd, 65536):
                h.update(chunk); size += len(chunk)
                if size > limit_file_bytes:
                    raise MeasuredAnalysisError('archive file exceeds read bound')
            if signature(before) != signature(os.fstat(fd)):
                raise MeasuredAnalysisError('archive changed during storage snapshot')
        finally:
            os.close(fd)
        relative = path.relative_to(root).as_posix(); key = (before.st_dev, before.st_ino)
        alias = inodes.setdefault(key, relative)
        if alias == relative:
            unique_bytes += size
        files[relative] = {'bytes': size, 'sha256': h.hexdigest(), 'same_file_as': None if alias == relative else alias}
        signatures[relative] = signature(before)
        if unique_bytes > limit_total:
            raise MeasuredAnalysisError('archive storage exceeds snapshot bound')
        if path.name != 'identity.json':
            continue
        identity, _ = _read(path, files[relative]['sha256'])
        if identity.get('schema') == 'measured-transaction-identity-v1':
            transaction = Path(identity['transaction_root']).absolute()
            if not transaction.is_relative_to(root):
                raise MeasuredAnalysisError('transaction archive leaves campaign storage root')
            transaction_roots.append(transaction)
            receipt_path = path.parent / 'result.json'
            if receipt_path.exists() and _read(receipt_path)[0].get('status') == 'complete':
                verify_observer_receipt(path.parent)
        elif identity.get('schema') == 'limited-worker-identity-v1':
            receipt_path = path.parent / 'result.json'
            if not receipt_path.exists():
                workers.append({'worker_id': digest(canonical_json(identity)), 'status': 'receipt_missing',
                    'phase_budget_binding': identity.get('phase_budget'), 'budget_attempt_id': None})
                continue
            worker, receipt_sha = _read(receipt_path)
            if worker.get('status') == 'complete' and read_completed(path.parent, identity) != worker:
                raise MeasuredAnalysisError('worker archive is not sealed')
            if worker.get('identity_sha256') != digest(canonical_json(identity)):
                raise MeasuredAnalysisError('worker receipt identity differs')
            workers.append({'worker_id': worker['identity_sha256'], 'status': worker.get('status'),
                'worker_receipt_sha256': receipt_sha, 'worker_receipt_path': str(receipt_path),
                'phase_budget_binding': identity.get('phase_budget'), 'budget_attempt_id': worker.get('budget_attempt_id'),
                'budget_debit': worker.get('budget_debit'), 'outcome': worker.get('outcome'),
                'resource_usage': worker.get('resource_usage'), 'limits': worker.get('limits')})
    final_paths = {p.relative_to(root).as_posix() for p in root.rglob('*') if not p.is_dir()}
    if final_paths != set(files) or any(signature((root / name).stat(follow_symlinks=False)) != value
                                       for name, value in signatures.items()):
        raise MeasuredAnalysisError('archive changed during storage snapshot')
    linked = set()
    for worker in workers:
        binding = worker.get('phase_budget_binding'); attempt = worker.get('budget_attempt_id')
        if binding is not None:
            if (ledger['status'] != 'verified' or binding.get('binding_sha256') != ledger['binding_sha256']
                    or binding.get('directory') != str(Path(ledger['path']).parent)
                    or binding.get('phase') not in checked['phase_cpu_seconds']):
                raise MeasuredAnalysisError('archived worker belongs to another or missing protocol budget')
        if attempt is not None:
            if (binding is None or attempt in linked or ledger['attempts'].get(attempt) != worker.get('budget_debit')
                    or worker['budget_debit']['phase'] != binding['phase']):
                raise MeasuredAnalysisError('worker budget attempt/debit differs or is duplicated')
            linked.add(attempt)
    if ledger['status'] == 'verified':
        ledger.update(linked_archived_attempt_ids=sorted(linked),
            attempts_without_worker_in_this_archive=sorted(set(ledger['attempts']) - linked))
    refreshed = read_budget_snapshot(Path(ledger['path']).parent,
        identity=ledger['binding']['identity'], phase_cpu_seconds=checked['phase_cpu_seconds'])
    if refreshed.get('ledger_sha256') != ledger.get('ledger_sha256') or refreshed['status'] != ledger['status']:
        raise MeasuredAnalysisError('protocol ledger changed during archive snapshot')
    totals = {'transaction_file_bytes': 0, 'nontransaction_file_bytes': 0}
    aliases = defaultdict(list)
    for name, info in files.items():
        aliases[info['same_file_as'] or name].append(name)
    transaction_root_set = set(transaction_roots)
    for original, names in aliases.items():
        transaction = any(any(parent in transaction_root_set for parent in (root / name).parents) for name in names)
        for name in names:
            files[name]['classification'] = 'transaction' if transaction else 'nontransaction'
        totals['transaction_file_bytes' if transaction else 'nontransaction_file_bytes'] += files[original]['bytes']
    storage = {'status': 'verified_at_read', 'scope': scope, 'root': str(root), 'files': files, 'workers': workers,
        'total_unique_file_bytes': sum(totals.values()), **totals, 'unique_files': len(aliases), 'file_paths': len(files),
        'all_worker_receipts_sealed': all(worker['status'] == 'complete' for worker in workers),
        'snapshot_sha256': digest(canonical_json(files)), 'hardlink_accounting': 'one byte count per inode; aliases explicit',
        'limits': {'max_files': limit_files, 'max_file_bytes': limit_file_bytes, 'max_total_unique_bytes': limit_total}}
    return ledger, storage


def load_measured_campaign_evidence(inventory_path, output_root, *, analysis_group='primary'):
    from .measured_inventory import validate_measured_campaign_files
    from .measured_comparison import verify_measured_archive
    checked = validate_measured_campaign_files(inventory_path, execute=False)
    payload = _base(checked, 'single_request', analysis_group)
    payload['runtime_contract'] = checked['inventory']['runtime_contract']
    workloads = {w['root_id']: w['original_record_ids'] for w in checked['inventory']['workloads']}
    seen = {}
    for item in checked['checked']:
        entry = item['entry']
        if entry['analysis_group'] != analysis_group:
            continue
        plan = entry['measured_plan_payload']
        slot = _slot(entry, plan, checked['protocol_sha256'])
        manifest_path = Path(checked['inventory_path']).parent / entry['manifest_path']
        manifest, _ = _read(manifest_path)
        slot.update(_input_projection(manifest, manifest_path, quality=plan['quality'] == 'heldout_nll'))
        root = Path(output_root) / 'runs' / entry['run_id']
        if not (root / 'result.json').exists():
            slot.update(archive_status='unsealed' if root.exists() else 'missing',
                        methods={name: _missing('unsealed_run' if root.exists() else 'missing_run') for name in METHODS})
        else:
            record = verify_measured_archive(root)
            _match(record, dict(slot, plan_sha256=entry['measured_plan_sha256']),
                   ('target_manifest_sha256', 'protocol_sha256', 'source_sha256', 'execution_mode', 'plan_sha256'))
            metadata = record.get('metadata', record)
            _match(metadata, slot, ('configuration_id', 'phase', 'root_id', 'request_id', 'repeat_index'))
            if record.get('method_order') != plan['method_order'] or set(record.get('methods', {})) != set(METHODS):
                raise MeasuredAnalysisError('archive method inventory differs')
            rows = {name: _role(record['methods'][name], target=slot['target_manifest_sha256'],
                    execution_mode=slot['execution_mode'], seen=seen, slot=slot['run_id'], role=name) for name in METHODS}
            _exact(rows)
            _retained(rows, [rid for rid in workloads[slot['root_id']] if rid not in set(entry['manifest_payload']['deleted_ids'])])
            preparation = _role(record['setup'], target=slot['target_manifest_sha256'],
                execution_mode=slot['execution_mode'], seen=seen, slot=slot['run_id'], role='setup')
            quality = _role(record['quality'], target=slot['target_manifest_sha256'],
                execution_mode=slot['execution_mode'], seen=seen, slot=slot['run_id'], role='quality')
            slot.update(preparation=preparation, quality=_quality_binding(quality, slot, preparation, rows))
            sealed = record.get('status') == 'complete'
            if not sealed:
                for row in rows.values():
                    if row['outcome'] == 'exact_complete':
                        row.update(outcome='unsealed_parent', wall_ns=None)
            slot.update(archive_status='sealed' if sealed else 'unsealed',
                        result_sha256=digest((root / 'result.json').read_bytes()), methods=rows)
        payload['slots'].append(slot)
    if not payload['slots']:
        raise MeasuredAnalysisError('analysis group has no frozen slots')
    payload['phase_budget_snapshot'], payload['archive_storage_snapshot'] = _resource_snapshots(checked, output_root)
    return VerifiedMeasuredEvidence(payload, _issuer=_ISSUER)


def load_measured_sequence_evidence(inventory_path, output_root, *, analysis_group='primary', execution_mode=None):
    from .measured_sequence import validate_measured_sequence_campaign_files, verify_measured_sequence_archive
    checked = validate_measured_sequence_campaign_files(inventory_path, execute=False)
    if execution_mode not in (None, 'clean', 'diagnostic'):
        raise MeasuredAnalysisError('unsupported frozen execution-mode filter')
    payload = _base(checked, 'sequence_lifetime', analysis_group)
    payload['execution_mode_filter'] = execution_mode
    workloads = {w['root_id']: w['original_record_ids'] for w in checked['inventory']['ordered_inventory']['workloads']}
    seen = {}
    for item in checked['checked']:
        entry, plan = item['entry'], item['plan']
        if entry.get('analysis_group', 'primary') != analysis_group:
            continue
        if execution_mode is not None and plan['execution_mode'] != execution_mode:
            continue
        slot = _slot(entry, plan, checked['protocol_sha256'])
        slot['runtime_contract'] = plan['runtime_contract']
        slot.update(_input_projection(item['manifest'], item['manifest_path'], quality=plan['quality'] == 'heldout_nll'))
        schedule = item['manifest']['requests']
        root = Path(output_root) / 'runs' / entry['run_id']
        unsealed = ((root / 'result.json').exists()
                    and _read(root / 'result.json')[0].get('status') != 'complete')
        if not (root / 'result.json').exists() or unsealed:
            kind = 'unsealed_run' if root.exists() else 'missing_run'
            slot.update(archive_status='unsealed' if root.exists() else 'missing',
                preparation={name: _missing(kind) for name in ('repair', 'model_only_fresh')},
                steps=[dict(request_id=req['request_id'], methods={name: _missing(kind) for name in METHODS}) for req in schedule])
        else:
            record = verify_measured_sequence_archive(root)
            _match(record, dict(slot, plan_sha256=digest(canonical_json(plan))),
                   ('target_manifest_sha256', 'protocol_sha256', 'source_sha256', 'execution_mode', 'plan_sha256'))
            _match(record.get('metadata', {}), dict(slot, sequence_id=slot['request_id']),
                   ('configuration_id', 'phase', 'root_id', 'sequence_id', 'repeat_index'))
            if len(record.get('steps', [])) != len(schedule):
                raise MeasuredAnalysisError('sequence omits planned requests')
            prep = {name: _role(record['preparation'][name], target=slot['target_manifest_sha256'],
                execution_mode=slot['execution_mode'], seen=seen, slot=slot['run_id'],
                role='setup' if name == 'repair' else name) for name in ('repair', 'model_only_fresh')}
            prep_equal = (prep['repair'].get('model_sha256') is not None and
                          prep['repair'].get('model_sha256') == prep['model_only_fresh'].get('model_sha256'))
            for row in prep.values():
                row['exact_model'] = prep_equal
                if row['outcome'] == 'completed_unverified':
                    row['outcome'] = 'exact_complete' if prep_equal else 'not_verified'
            _retained(prep, workloads[slot['root_id']])
            steps, removed = [], []
            for index, (actual, req) in enumerate(zip(record['steps'], schedule)):
                removed += req['deleted_ids']
                expected = {'step_index': index, 'request_id': req['request_id'],
                    'newly_deleted_ids': req['deleted_ids'], 'cumulative_deleted_ids': list(removed)}
                _match(actual, expected, expected)
                if set(actual.get('methods', {})) != set(METHODS):
                    raise MeasuredAnalysisError('sequence step method inventory differs')
                rows = {name: _role(actual['methods'][name], target=slot['target_manifest_sha256'],
                    execution_mode=slot['execution_mode'], seen=seen, slot=slot['run_id'], role=name) for name in METHODS}
                _exact(rows)
                _retained(rows, [rid for rid in workloads[slot['root_id']] if rid not in set(removed)])
                quality = _role(actual.get('quality', {'status': 'not_requested'}), target=slot['target_manifest_sha256'],
                    execution_mode=slot['execution_mode'], seen=seen, slot=slot['run_id'], role='quality')
                steps.append(dict(expected, methods=rows,
                    quality=_quality_binding(quality, slot, prep['repair'], rows)))
            slot.update(archive_status='sealed', result_sha256=digest((root / 'result.json').read_bytes()), preparation=prep, steps=steps)
        lifetime = {}
        for name in ('repair', 'indexed_fresh', 'model_only_fresh'):
            prep = slot['preparation']['model_only_fresh' if name == 'model_only_fresh' else 'repair']
            rows = [prep] + [step['methods'][name] for step in slot['steps']]
            complete = all(row['outcome'] == 'exact_complete' for row in rows)
            lifetime[name] = {'outcome': 'exact_complete' if complete else 'incomplete_lifetime',
                'wall_ns': sum(row['wall_ns'] for row in rows) if complete else None,
                'observed_wall_ns': sum(row['observed_wall_ns'] or 0 for row in rows),
                'preparation_wall_ns': prep['wall_ns'],
                'request_wall_ns': sum(row['wall_ns'] for row in rows[1:]) if complete else None,
                'preparation_shared_with': 'indexed_fresh' if name == 'repair' else 'repair' if name == 'indexed_fresh' else None}
        slot['methods'] = lifetime
        payload['slots'].append(slot)
    if not payload['slots']:
        raise MeasuredAnalysisError('analysis group has no frozen sequences')
    payload['phase_budget_snapshot'], payload['archive_storage_snapshot'] = _resource_snapshots(checked, output_root)
    return VerifiedMeasuredEvidence(payload, _issuer=_ISSUER)


def analyze_verified_evidence(evidence):
    if type(evidence) is not VerifiedMeasuredEvidence:
        raise MeasuredAnalysisError('analysis requires loader-issued artifact evidence')
    payload = evidence.payload()
    settings = payload['settings']; strata = defaultdict(list)
    for slot in payload['slots']:
        key = tuple(slot[k] for k in ('configuration_id', 'phase', 'target_manifest_sha256',
            'execution_mode', 'service_family', 'response_tier', 'service_mode', 'verifier_policy'))
        strata[key].append(slot)
    output = []
    confirmation_strata = [key for key in strata if key[1] == 'confirmation']
    selector = payload.get('primary_configuration')
    selected = [key for key in confirmation_strata if key[0] == selector] if type(selector) is str else confirmation_strata
    sole_primary_stratum = selected[0] if len(selected) == 1 else None
    comparisons = [('ordinary_model_output', 'model_only_fresh'), ('equally_indexed_maintenance', 'indexed_fresh')]
    if payload['kind'] == 'single_request':
        comparisons.append(('canonical_state_reconstruction', 'direct_fresh'))
    for key, slots in sorted(strata.items()):
        requests = defaultdict(list)
        for slot in slots:
            requests[(slot['root_id'], slot['request_id'])].append(slot)
        for label, baseline in comparisons:
            root_logs = defaultdict(list); request_results = []
            counts = {method: Counter(slot['methods'][method]['outcome'] for slot in slots)
                      for method in (baseline, 'repair')}
            for (root, request), repeats in sorted(requests.items()):
                indices = [row['repeat_index'] for row in repeats]
                if len(indices) != len(set(indices)):
                    raise MeasuredAnalysisError('duplicate planned repetition')
                complete = all(row['methods'][method]['outcome'] == 'exact_complete'
                               for row in repeats for method in (baseline, 'repair'))
                log_ratio = None
                if complete:
                    times = {m: statistics.median(row['methods'][m]['wall_ns'] for row in repeats)
                             for m in (baseline, 'repair')}
                    log_ratio = math.log(times[baseline]) - math.log(times['repair'])
                    root_logs[root].append(log_ratio)
                request_results.append({'root_id': root, 'request_id': request,
                    'planned_repeats': len(repeats), 'complete_all_repeats': complete,
                    'log_baseline_over_repair': log_ratio})
            root_means = {root: statistics.fmean(values) for root, values in sorted(root_logs.items())}
            interval = root_interval(list(root_means.values()), **{k: settings[k] for k in ('seed', 'draws', 'confidence')})
            ratio = math.exp(statistics.fmean(root_means.values())) if root_means else None
            ratio_interval = [math.exp(x) for x in interval] if interval else None
            all_complete = all(row['complete_all_repeats'] for row in request_results)
            declared_primary = (baseline == payload.get('primary_baseline')
                and payload.get('primary_candidate') == 'repair' and payload.get('primary_comparison_count') == 1
                and key == sole_primary_stratum)
            frozen_confirmation = (key[1] == 'confirmation' and payload['protocol_status'] == 'frozen_confirmation'
                and payload['protocol_blocked_fields'] == [] and payload['analysis_group'] == 'primary'
                and payload.get('inference_settings_frozen') is True and declared_primary)
            output.append({'configuration_id': key[0], 'phase': key[1], 'target_manifest_sha256': key[2],
                'execution_mode': key[3], 'service_family': key[4], 'response_tier': key[5],
                'service_mode': key[6], 'verifier_policy': key[7], 'comparison': label,
                'baseline': baseline, 'candidate': 'repair', 'planned_slots': len(slots),
                'declared_primary_comparison': declared_primary,
                'planned_roots': len({s['root_id'] for s in slots}), 'available_roots': len(root_means),
                'outcome_counts': {m: dict(c) for m, c in counts.items()}, 'requests': request_results,
                'conditional_ratio': ratio, 'conditional_root_bootstrap_interval': ratio_interval,
                'root_mean_log_ratios': root_means, 'all_planned_exact_clean_complete': all_complete,
                'confirmation_timing_eligible': frozen_confirmation and all_complete and interval is not None,
                'confirmation_speed_rule_met': bool(frozen_confirmation and all_complete and ratio_interval
                                                   and ratio_interval[0] > settings['threshold']),
                'independence_assumption': 'frozen root sampling law; repeated requests and clocks are clustered within root'})
    return {'schema': 'calibration-measured-analysis-v1', 'evidence_sha256': evidence.sha256,
        'inventory_sha256': payload['inventory_sha256'], 'protocol_sha256': payload['protocol_sha256'],
        'kind': payload['kind'], 'analysis_group': payload['analysis_group'], 'settings': settings,
        'results': output, 'empirical_attainment_established': False,
        'interpretation': 'conditional artifact analysis; real workload provenance and all other paper gates remain separate',
        'lifetime_scope': 'one original preparation plus every request; no nested worker clocks, research oracles or quality costs added'}


def analyze_measured_campaign(inventory_path, output_root, *, analysis_group='primary'):
    return analyze_verified_evidence(load_measured_campaign_evidence(inventory_path, output_root, analysis_group=analysis_group))


def analyze_measured_sequences(inventory_path, output_root, *, analysis_group='primary'):
    return analyze_verified_evidence(load_measured_sequence_evidence(inventory_path, output_root, analysis_group=analysis_group))
