"""Narrow read-only V34 admission for one preserved terminal-copy discrepancy.

All other paths retain V33 verification, including its exact prior WikiText exception. This exception does not
rewrite evidence, explain the cause, or claim the original three-copy guard passed.
"""
from pathlib import Path
import re

from src.run_store import canonical_json, digest, strict_json
from scripts.verify_terminal_recovery_v33 import verify_completed as prior_verify_completed
from src.service_terminal_evidence_v30 import (
    verify_completed as strict_verify_completed, _require, _raw, _json,
    _verify_file, _verify_stdout, _name)

ROOT=Path(__file__).resolve().parents[1]
INCIDENT_RELATIVE='campaigns/independent_c4_v32/attempts/c4-delete-0-cold'
PROGRAM_SHA256='72a47ecee599217f32a89bddf8ece7dae6273dcb19b49f8bb8cd1c06ab6a842c'
PROTOCOL_SHA256='a40135ab93ed716ff655a3dced19cb319b30c00262f1d50364ab55e5b8e66fe1'
TERMINAL_SHA256='b16ca849e55b8a2558b2cc3e8b609184e61fa1475464763e8b227d68ad3596f5'
LIVE_SHA256='e2f76585be4eef13997ead916ce9fb1bc014ba7967eb7008a09b25bf716fcb72'
SNAPSHOT_RELATIVE='campaigns/recovery_v34/c4-cold0-preserved-snapshot'
SNAPSHOT_SHA256='5669090d59491e5ff54fb6dfe0a64fc294a6ae6e374594f24858f92e25d3f4aa'
AUDIT_RELATIVE='campaigns/recovery_v34/c4-cold0-incident-independent-audit.json'
AUDIT_SHA256='57df74042ea0313a05d1c006f955aea5fce1ef5b9fee3f2d9fa8836427d3be92'


def verify_completed(attempt):
    attempt=Path(attempt).absolute()
    if attempt != ROOT/INCIDENT_RELATIVE:
        return prior_verify_completed(attempt)
    campaign=attempt.parent.parent
    _require(digest(_raw(campaign/'program.json'))==PROGRAM_SHA256
        and digest(_raw(campaign/'protocol.json'))==PROTOCOL_SHA256,
        'incident program or protocol differs')
    snapshot=ROOT/SNAPSHOT_RELATIVE
    raw=_raw(snapshot/'manifest.json')
    _require(digest(raw)==SNAPSHOT_SHA256,'preserved incident manifest changed')
    manifest=strict_json(raw)
    _require(manifest['source']==INCIDENT_RELATIVE and manifest['cause']=='unknown',
        'preserved incident provenance differs')
    for name,entry in manifest['files'].items():
        _require(not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe incident path')
        _verify_file(snapshot/name,entry)
        _verify_file(attempt/name,entry)
    _require(digest(_raw(ROOT/AUDIT_RELATIVE))==AUDIT_SHA256,'independent incident audit changed')
    result=_verify_known_incident(attempt)
    _require(result['model_artifact']['sha256']==manifest['model_sha256'],'incident model differs')
    return result


def _verify_known_incident(attempt):
    """Return the verified terminal record. Do not mutate any evidence file.

Checks include the transaction, receipt artifacts, settled CPU charge, plan
identity, completion/seal equality, the exact pinned stale-live copy, stdout,
and output artifacts. The original three-copy guard remains failed.
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
        live_raw = _raw(outputs/'progress.json')
        _require(terminal_raw == _raw(attempt/'sealed-progress.json'),
                 'recovered completion and controller seal differ')
        _require(digest(terminal_raw) == TERMINAL_SHA256 and digest(live_raw) == LIVE_SHA256,
                 'incident is not the exact reviewed terminal/live pair')
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
