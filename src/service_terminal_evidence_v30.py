"""Service-format adapter for trusted local research completion evidence.

These consistency checks detect changed records and missing bindings. They do
not authenticate a hostile filesystem or establish model correctness by hash.
"""
import hashlib
from pathlib import Path
import re
import stat

from .run_store import canonical_json, digest, strict_json

_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_MAX_METADATA = 32 * 2**20


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _regular(path):
    _require(not path.is_symlink() and path.is_file(), 'missing or unsafe evidence file: '+str(path))
    _require(stat.S_ISREG(path.stat().st_mode), 'evidence must be a regular file')
    return path


def _raw(path):
    _regular(path)
    _require(path.stat().st_size <= _MAX_METADATA, 'evidence metadata exceeds byte limit')
    return path.read_bytes()


def _json(path):
    try:
        value = strict_json(_raw(path))
    except (TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid evidence JSON') from exc
    _require(type(value) is dict, 'evidence JSON must contain an object')
    return value


def _name(value):
    _require(type(value) is str and _NAME.fullmatch(value) is not None,
             'unsafe evidence basename')
    return value


def _hash_file(path):
    _regular(path)
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _verify_file(path, entry):
    _require(type(entry) is dict and set(entry) == {'sha256', 'bytes'}, 'invalid evidence file binding')
    _require(type(entry['bytes']) is int and entry['bytes'] >= 0, 'invalid evidence byte count')
    _require(type(entry['sha256']) is str and _SHA.fullmatch(entry['sha256']) is not None,
             'invalid evidence digest')
    _regular(path)
    _require(path.stat().st_size == entry['bytes'] and _hash_file(path) == entry['sha256'],
             'evidence artifact hash or byte count differs: '+str(path))


def _verify_stdout(summary, terminal_digest):
    _require(type(summary.get('tail_utf8')) is str, 'stdout summary has no text tail')
    _require(type(summary.get('bytes')) is int and summary['bytes'] >= 0, 'invalid stdout byte count')
    _require(type(summary.get('tail_max_bytes')) is int and summary['tail_max_bytes'] > 0,
             'invalid stdout tail limit')
    _require(type(summary.get('sha256')) is str and _SHA.fullmatch(summary['sha256']) is not None,
             'invalid stdout digest')
    tail = summary['tail_utf8']
    lines = tail.splitlines()
    _require(bool(lines), 'stdout tail is empty')
    markers = []
    for line in lines:
        try:
            value = strict_json(line)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            continue  # The first retained line can begin inside a larger log line.
        if type(value) is not dict:
            continue
        if set(value) == {'terminal_sha256'}:
            markers.append(value['terminal_sha256'])
        elif value.get('phase') == 'terminal_record_committed':
            _require(set(value) == {'phase', 'sha256'}, 'invalid terminal stdout marker')
            markers.append(value['sha256'])
    _require(markers == [terminal_digest], 'receipt-bound stdout terminal digest differs or is missing')
    # Full retained ASCII/UTF8 logs permit an additional stream digest check.
    # Larger logs retain only a suffix, whose bytes are already receipt-bound.
    if summary['bytes'] <= summary['tail_max_bytes']:
        encoded = tail.encode('utf-8')
        _require(len(encoded) == summary['bytes'] and digest(encoded) == summary['sha256'],
                 'complete stdout tail differs from its stream digest')


def verify_completed(attempt):
    """Return the verified terminal record. Do not mutate any evidence file.

Checks include the transaction, receipt artifacts, settled CPU charge, plan
identity, three terminal copies, the stdout commitment, and output artifacts.
An enclosing controller must separately bind its registered program and inputs.
"""
    attempt = Path(attempt).absolute()
    _require(not attempt.is_symlink() and attempt.is_dir(), 'invalid attempt directory')
    _require(not any(parent.is_symlink() for parent in attempt.parents), 'symlink evidence parent is unsupported')
    worker = attempt/'worker'
    outputs = attempt/'outputs'
    _require(not worker.is_symlink() and worker.is_dir(), 'invalid worker directory')
    _require(not outputs.is_symlink() and outputs.is_dir(), 'invalid output directory')
    try:
        transaction = _json(attempt/'transaction.json')
        receipt_raw = _raw(worker/'result.json')
        _require(transaction['receipt_sha256'] == digest(receipt_raw), 'transaction receipt digest differs')
        receipt = strict_json(receipt_raw)
        _require(type(receipt) is dict and receipt['status'] == 'complete', 'worker receipt is incomplete')
        outcome = receipt['outcome']
        _require(type(outcome) is dict and outcome.get('status') == 'complete'
                 and type(outcome.get('returncode')) is int and outcome['returncode'] == 0,
                 'worker outcome did not complete successfully')
        _require(transaction['worker_outcome'] == outcome, 'transaction and receipt outcomes differ')

        inner_name = receipt['attempt']
        _require(type(inner_name) is str and re.fullmatch(r'attempt-[0-9]{4,}', inner_name) is not None,
                 'unsafe receipt attempt path')
        inner = worker/inner_name
        _require(not inner.is_symlink() and inner.is_dir(), 'invalid receipt attempt directory')
        manifest = receipt['artifacts']
        _require(type(manifest) is dict and bool(manifest), 'receipt has no artifact manifest')
        for name, entry in manifest.items():
            _verify_file(inner/_name(name), entry)
        _require('stdout-summary.json' in manifest and 'request.json' in manifest,
                 'receipt lacks stdout or request binding')

        plan_raw = _raw(attempt/'plan.json')
        plan_digest = digest(plan_raw)
        worker_identity = receipt['worker_identity']
        _require(type(worker_identity) is dict and worker_identity.get('plan_sha256') == plan_digest,
                 'worker plan identity differs')
        identity = _json(worker/'identity.json')
        _require(digest(canonical_json(identity)) == receipt['identity_sha256']
                 and identity.get('identity') == worker_identity, 'worker identity binding differs')
        request = _json(inner/'request.json')
        for key in ('command', 'cwd', 'limits'):
            _require(request.get(key) == identity.get(key), 'request and worker identity differ: '+key)

        debit = receipt['budget_debit']
        _require(type(debit) is dict and debit.get('state') == 'settled', 'worker CPU charge is unsettled')
        observed = debit.get('observed_cpu_ns')
        _require(type(observed) is int and observed >= 0, 'observed CPU use is unavailable')
        _require(type(debit.get('charged_cpu_seconds')) is int
                 and debit['charged_cpu_seconds'] == max(1, (observed+999_999_999)//1_000_000_000),
                 'settled CPU debit differs from observed use')
        _require(type(debit.get('reserved_cpu_seconds')) is int and debit['reserved_cpu_seconds'] > 0,
                 'invalid CPU reservation')
        _require(receipt['resource_usage']['total_cpu_ns'] == observed, 'receipt CPU observations differ')
        _require(transaction['budget']['attempts'][receipt['budget_attempt_id']] == debit,
                 'transaction CPU settlement differs')

        terminal_raw = _raw(outputs/'completion.json')
        _require(terminal_raw == _raw(outputs/'progress.json')
                 and terminal_raw == _raw(attempt/'sealed-progress.json'),
                 'terminal evidence copies differ; preserve and stop')
        result = strict_json(terminal_raw)
        _require(type(result) is dict and result.get('status') == 'complete', 'terminal record is incomplete')
        _require(result.get('plan_sha256') == plan_digest, 'terminal plan identity differs')
        _verify_stdout(_json(inner/'stdout-summary.json'), digest(terminal_raw))
        artifacts = result.get('artifacts')
        derived = False
        if artifacts is None and result.get('schema') in (
                'adaptive-complete-service-transaction-v30', 'sequential-quality-comparison-v30'):
            _require(result.get('complete_model') is True, 'service model is incomplete')
            artifacts = {'model': result.get('model_artifact')}
            if result.get('complete_state') is True:
                artifacts['state'] = result.get('state_artifact')
            derived = True
        _require(type(artifacts) is dict and bool(artifacts), 'terminal output manifest is missing')
        filenames = set()
        for entry in artifacts.values():
            _require(type(entry) is dict and set(entry) == {'file', 'bytes', 'sha256'},
                     'invalid terminal output binding')
            name = _name(entry['file'])
            _require(name not in filenames, 'duplicate terminal output filename')
            filenames.add(name)
            _verify_file(outputs/name, {key: entry[key] for key in ('bytes', 'sha256')})
        if derived:
            result = dict(result, artifacts=artifacts,
                artifact_manifest_source='verified named model_artifact/state_artifact fields; original bytes unchanged')
        return result
    except (KeyError, TypeError, IndexError, UnicodeError, RecursionError) as exc:
        raise ValueError('completion evidence has invalid or missing fields') from exc
