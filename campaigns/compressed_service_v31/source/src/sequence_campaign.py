"""Frozen, source-bound bulk execution of ordered local deletion sequences.

One limited process executes each complete sequence. Its step methods stay warm.
No models or data are fetched. Research pause and fixed target semantics persist.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import time

from .experiment_campaign import _phase_caps
from .experiment_inventory import _relative, _workload_map, source_hashes
from .experiment_runner import METHODS, _integer, _local, _read_json, _referenced_json, _sha, _text
from .phase_budget import PhaseBudget
from .request_workload import counterbalanced_orders
from .run_store import RunStore, atomic_write, canonical_json, digest, strict_json
from .sequence_runner import (run_sequence_manifest, sequence_archive_snapshot,
                              validate_requests, verify_sequence_archive)
from .worker_control import WorkerLimits, run_limited

EXECUTION_MODE = 'isolated_sequence_worker_warm_step_methods_os_cache_uncontrolled'


def sequence_manifest_payload(manifest):
    if not isinstance(manifest, dict) or manifest.get('schema') != 'calibration-sequence-v1':
        raise ValueError('unsupported sequence manifest')
    payload = strict_json(canonical_json(manifest))
    reference = payload.get('protocol')
    if not isinstance(reference, dict) or set(reference) != {'path', 'sha256'}:
        raise ValueError('sequence manifest requires one protocol reference')
    _text(reference['path'], 'protocol path')
    if reference['sha256'] is not None:
        _sha(reference['sha256'])
    reference['sha256'] = None
    return payload


def sequence_manifest_binding(manifest):
    return digest(canonical_json(sequence_manifest_payload(manifest)))


def _provenance(workload, manifest):
    by_id = {row['request_id']: row for row in workload['requests']}
    schedule = validate_requests(manifest.get('requests'), workload['original_record_ids'])
    cumulative, result = set(), []
    previous = 'original'
    for index, request in enumerate(schedule):
        source = by_id.get(request['request_id'])
        if (source is None or source.get('blocked_reason') is not None
                or source.get('deleted_ids') != request['deleted_ids']
                or source.get('starting_state') != previous):
            raise ValueError('sequence request differs from frozen ordered workload provenance')
        if source.get('execution_requirement') not in (
                ('independent_reset', 'previous_committed_state') if index == 0 else ('previous_committed_state',)):
            raise ValueError('sequence request has an incompatible execution requirement')
        if 'previously_deleted_ids' in source and source['previously_deleted_ids'] != sorted(cumulative):
            raise ValueError('sequence previous deletion set differs from workload')
        cumulative.update(request['deleted_ids'])
        expected = [rid for rid in workload['original_record_ids'] if rid in cumulative]
        if 'cumulative_deleted_ids' in source and source['cumulative_deleted_ids'] != expected:
            raise ValueError('sequence cumulative deletion set differs from workload')
        result.append({'step_index': index, 'request_id': request['request_id'],
                       'source_request_sha256': digest(canonical_json(source))})
        previous = request['request_id']
    return result


def build_sequence_campaign(*, campaign_id, protocol_path, workloads, runs, worker_limits, sources):
    """Freeze supplied manifests and their ordered workload provenance."""
    mapped = _workload_map(workloads)
    entries = []
    for run in runs:
        if not isinstance(run, dict) or set(run) != {'run_id','manifest_path','manifest','target_manifest_sha256'}:
            raise ValueError('sequence run specification has invalid fields')
        manifest = sequence_manifest_payload(run['manifest'])
        workload = mapped[manifest['root_id']][0]
        entry = {k: manifest[k] for k in ('sequence_id','root_id','configuration_id','repeat_index','phase','method_order')}
        entry.update(run_id=run['run_id'], manifest_path=run['manifest_path'], manifest_payload=manifest,
                     manifest_binding_sha256=sequence_manifest_binding(manifest),
                     target_manifest_sha256=run['target_manifest_sha256'],
                     request_provenance=_provenance(workload, manifest))
        entries.append(entry)
    result = {'schema':'calibration-sequence-campaign-v1','campaign_id':campaign_id,'protocol_path':protocol_path,
              'execution_mode':EXECUTION_MODE,'worker_limits':WorkerLimits.from_payload(worker_limits).payload(),
              'source_sha256':sources,'workloads':workloads,'workload_sha256':digest(canonical_json(workloads)),
              'entries':entries}
    validate_sequence_campaign(result)
    return strict_json(canonical_json(result))


def validate_sequence_campaign(campaign):
    fields = {'schema','campaign_id','protocol_path','execution_mode','worker_limits','source_sha256',
              'workloads','workload_sha256','entries'}
    if (not isinstance(campaign, dict) or set(campaign) != fields
            or campaign['schema'] != 'calibration-sequence-campaign-v1' or campaign['execution_mode'] != EXECUTION_MODE):
        raise ValueError('invalid sequence campaign schema')
    _text(campaign['campaign_id'], 'campaign ID')
    _text(campaign['protocol_path'], 'protocol path')
    WorkerLimits.from_payload(campaign['worker_limits'])
    if not isinstance(campaign['source_sha256'], dict) or not campaign['source_sha256']:
        raise ValueError('sequence campaign requires executable source hashes')
    for path, value in campaign['source_sha256'].items():
        _relative(path)
        _sha(value)
    if digest(canonical_json(campaign['workloads'])) != _sha(campaign['workload_sha256']):
        raise ValueError('sequence campaign workload hash differs')
    workloads = _workload_map(campaign['workloads'])
    if not isinstance(campaign['entries'], list) or not campaign['entries']:
        raise ValueError('sequence campaign requires planned entries')
    fields = {'run_id','manifest_path','manifest_payload','manifest_binding_sha256','target_manifest_sha256',
              'sequence_id','root_id','configuration_id','repeat_index','phase','method_order','request_provenance'}
    ids, paths, identities, repeats = set(), set(), set(), {}
    sequence_schedules, configurations = {}, {}
    for entry in campaign['entries']:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ValueError('invalid sequence entry fields')
        run_id = _text(entry['run_id'], 'run ID')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id) or run_id in ids:
            raise ValueError('sequence run IDs must be unique filename-safe identifiers')
        ids.add(run_id)
        path = _relative(entry['manifest_path'])
        if path in paths:
            raise ValueError('duplicate sequence manifest path')
        paths.add(path)
        for key in ('sequence_id','root_id','configuration_id'):
            _text(entry[key], key)
        _integer(entry['repeat_index'], 'repeat index')
        if entry['phase'] not in ('feasibility','development','confirmation','software_test'):
            raise ValueError('unsupported sequence phase')
        if not isinstance(entry['method_order'], list) or sorted(entry['method_order']) != sorted(METHODS):
            raise ValueError('sequence method order must contain every method')
        manifest = entry['manifest_payload']
        if sequence_manifest_payload(manifest) != manifest:
            raise ValueError('embedded sequence manifest must clear only protocol.sha256')
        if sequence_manifest_binding(manifest) != _sha(entry['manifest_binding_sha256']):
            raise ValueError('sequence manifest binding differs')
        for field in ('sequence_id','root_id','configuration_id','repeat_index','phase','method_order'):
            if manifest.get(field) != entry[field]:
                raise ValueError('sequence entry differs from manifest metadata')
        _sha(entry['target_manifest_sha256'])
        configuration = canonical_json({
            'target_manifest_sha256': entry['target_manifest_sha256'],
            'chart': manifest.get('chart'), 'target': manifest.get('target'),
            'checkpoint_files_sha256': manifest.get('checkpoint', {}).get('files_sha256'),
            'service_family': manifest.get('service_family', 'response'),
            'service_mode': manifest.get('service_mode', 'certified'),
            'verifier_policy': manifest.get('verifier_policy', 'spectral')})
        name = entry['configuration_id']
        if name in configurations and configurations[name] != configuration:
            raise ValueError('same sequence configuration changes target or algorithm settings')
        configurations[name] = configuration
        if entry['root_id'] not in workloads:
            raise ValueError('sequence root is absent from workload')
        workload = workloads[entry['root_id']][0]
        if manifest.get('calibration', {}).get('sha256') != workload['prepared_records_sha256']:
            raise ValueError('sequence calibration hash differs from frozen workload')
        if entry['request_provenance'] != _provenance(workload, manifest):
            raise ValueError('sequence ordered request provenance differs')
        order = counterbalanced_orders(seed=workload['seed'], root_id=entry['root_id'],
            request_id=entry['sequence_id'], repeats=entry['repeat_index']+1)[-1]
        if entry['method_order'] != order:
            raise ValueError('sequence method order differs from frozen counterbalance')
        key = tuple(entry[k] for k in ('configuration_id','phase','root_id','sequence_id','repeat_index'))
        if key in identities:
            raise ValueError('duplicate sequence comparison identity')
        identities.add(key)
        group = key[:-1]
        repeats.setdefault(group, []).append(entry['repeat_index'])
        # A sequence identifier cannot silently change membership across repeats/configurations.
        schedule_key = (entry['phase'], entry['root_id'], entry['sequence_id'])
        frozen = canonical_json(manifest['requests'])
        if schedule_key in sequence_schedules and sequence_schedules[schedule_key] != frozen:
            raise ValueError('same sequence identity changes its request schedule')
        sequence_schedules[schedule_key] = frozen
    if any(sorted(values) != list(range(len(values))) for values in repeats.values()):
        raise ValueError('sequence repeats must form a complete zero-based prefix')


def _confirmation_product(campaign, protocol):
    entries = [e for e in campaign['entries'] if e['phase'] == 'confirmation']
    if not entries and protocol.get('status') != 'frozen_confirmation':
        return
    declarations = {}
    for name in ('configuration_ids','root_ids','sequence_ids'):
        values = protocol.get('sequence_confirmation', {}).get(name)
        if (not isinstance(values, list) or not values or any(type(v) is not str or not v for v in values)
                or len(set(values)) != len(values)):
            raise ValueError('sequence confirmation requires explicit unique '+name)
        declarations[name] = values
    repeats = _integer(protocol.get('sequence_confirmation', {}).get('timing_repeats'), 'sequence repeats', 1)
    expected = {(c,r,s,k) for c in declarations['configuration_ids'] for r in declarations['root_ids']
                for s in declarations['sequence_ids'] for k in range(repeats)}
    actual = {(e['configuration_id'],e['root_id'],e['sequence_id'],e['repeat_index']) for e in entries}
    if expected != actual or len(actual) != len(entries):
        raise ValueError('sequence confirmation lacks the exact declared product')


def validate_sequence_campaign_files(path, *, execute=False):
    path = Path(path).absolute()
    campaign, raw = _read_json(path)
    validate_sequence_campaign(campaign)
    if raw != canonical_json(campaign):
        raise ValueError('sequence inventory requires canonical JSON bytes')
    sources = source_hashes(Path(__file__).resolve().parents[1])
    if campaign['source_sha256'] != sources:
        raise ValueError('sequence source hashes differ from frozen inventory')
    limits = WorkerLimits.from_payload(campaign['worker_limits'])
    limits.check_host()
    protocol_path = _local(path.parent, campaign['protocol_path'])
    protocol, protocol_raw = _read_json(protocol_path)
    if not isinstance(protocol, dict) or protocol.get('planned_inventory_sha256') != digest(raw):
        raise ValueError('protocol does not bind exact sequence inventory')
    _confirmation_product(campaign, protocol)
    workloads = _workload_map(campaign['workloads'])
    checked, resolved = [], set()
    for entry in campaign['entries']:
        manifest_path = _local(path.parent, entry['manifest_path'])
        if manifest_path in resolved:
            raise ValueError('sequence manifests resolve to the same file')
        resolved.add(manifest_path)
        manifest, manifest_raw = _read_json(manifest_path)
        if sequence_manifest_binding(manifest) != entry['manifest_binding_sha256']:
            raise ValueError('sequence manifest differs from frozen inventory')
        reference = manifest['protocol']
        if (_local(manifest_path.parent, reference['path']) != protocol_path
                or reference['sha256'] != digest(protocol_raw)):
            raise ValueError('sequence manifest refers to different protocol bytes or path')
        calibration, _ = _referenced_json(manifest_path.parent, manifest['calibration'])
        if [r['id'] for r in calibration['records']] != workloads[entry['root_id']][0]['original_record_ids']:
            raise ValueError('prepared sequence record order differs from workload')
        if execute and entry['phase'] != 'software_test' and 'experiments_paused' in str(protocol.get('status','')):
            raise ValueError('the protocol keeps research experiments paused')
        if entry['phase'] == 'confirmation' and (protocol.get('schema') != 'calibration-protocol-v1'
                or protocol.get('status') != 'frozen_confirmation' or protocol.get('blocked_fields') != []):
            raise ValueError('sequence confirmation requires frozen protocol without blocked fields')
        checked.append({'entry':entry,'manifest_path':manifest_path,'manifest_sha256':digest(manifest_raw)})
    return {'campaign':campaign,'raw':raw,'inventory_path':path,'inventory_sha256':digest(raw),
            'protocol':protocol,'protocol_path':protocol_path,'protocol_sha256':digest(protocol_raw),
            'sources':sources,'limits':limits,'checked':checked,'phase_cpu_seconds':_phase_caps(campaign,protocol,limits)}


def _child(request_path):
    request, _ = _read_json(Path(request_path))
    if set(request) != {'schema','inventory_path','inventory_sha256','protocol_sha256','manifest_sha256','run_id','output'}:
        raise ValueError('invalid sequence worker request')
    if request['schema'] != 'sequence-campaign-child-v1':
        raise ValueError('unsupported sequence worker request')
    def bound():
        current = validate_sequence_campaign_files(request['inventory_path'], execute=True)
        if (current['inventory_sha256'] != request['inventory_sha256']
                or current['protocol_sha256'] != request['protocol_sha256']):
            raise ValueError('sequence inventory or protocol changed during worker execution')
        matches = [x for x in current['checked'] if x['entry']['run_id'] == request['run_id']]
        if len(matches) != 1 or matches[0]['manifest_sha256'] != request['manifest_sha256']:
            raise ValueError('sequence worker manifest changed')
        return matches[0]
    item = bound()
    output = Path(request['output'])
    if (output/'result.json').is_file() and _read_json(output/'result.json')[0].get('status') == 'complete':
        raise ValueError('completed sequence lacks its enclosing durable worker receipt; refuse cached fast recovery')
    if output.exists():
        verify_sequence_archive(output)
    result = run_sequence_manifest(item['manifest_path'], output,
                                   expected_target_sha256=item['entry']['target_manifest_sha256'])
    bound()
    verify_sequence_archive(output)
    return 0 if result.get('status') == 'complete' else 1


def _observe_sequence(output, entry, manifest_sha, protocol_sha):
    observed = {'archive_snapshot':sequence_archive_snapshot(output),
                'steps':[{'step_index':i,'request_id':r['request_id'],'status':'not_started'}
                         for i,r in enumerate(entry['manifest_payload']['requests'])]}
    try:
        verified = verify_sequence_archive(output)
        result = verified['result']
        if result is None:
            failures = []
            for path in sorted(output.glob('preflight-failure-*.json')) if output.exists() else ():
                failed, raw = _read_json(path)
                failures.append({'path': path.name, 'sha256': digest(raw), 'failure': failed.get('failure')})
            if failures:
                observed['preflight_failures'] = failures
            raise ValueError('sequence worker produced no result')
        metadata = result.get('metadata', {})
        for field in ('sequence_id','root_id','configuration_id','repeat_index','phase'):
            if metadata.get(field) != entry[field]:
                raise ValueError('sequence result metadata differs from inventory')
        if (metadata.get('run_manifest_sha256') != manifest_sha or metadata.get('protocol_sha256') != protocol_sha
                or metadata.get('target_manifest_sha256') != entry['target_manifest_sha256']):
            raise ValueError('sequence result input or target binding differs')
        if result.get('requests') != entry['manifest_payload']['requests']:
            raise ValueError('sequence result request order differs')
        observed.update(status=result['status'], steps=result['steps'],
                        result_sha256=digest((output/'result.json').read_bytes()))
        if result['status'] != 'complete':
            observed.update(status='failed',failure=result.get('failure',{'kind':'sequence_incomplete'}))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        observed.update(status='failed',failure={'kind':'invalid_or_missing_sequence_result',
                                               'type':type(exc).__name__,'message':str(exc)})
    return observed


def _verify_completed(root, identity, budget):
    saved = RunStore(root, identity).completed()
    if saved is None:
        return None
    for row in saved['runs']:
        worker_root = root/'workers'/row['run_id']
        worker_identity, _ = _read_json(worker_root/'identity.json')
        worker = RunStore(worker_root, worker_identity).completed()
        if worker is None or digest(canonical_json(worker)) != row['worker_record_sha256']:
            raise ValueError('sequence worker receipt changed')
        request, request_raw = _read_json(root/'requests'/(row['run_id']+'.json'))
        if (request_raw != canonical_json(request)
                or digest(request_raw) != worker['worker_identity']['request_sha256']):
            raise ValueError('saved sequence dispatch request changed')
        attempt = worker.get('budget_attempt_id')
        if attempt is not None and budget.snapshot()['attempts'].get(attempt) != worker.get('budget_debit'):
            raise ValueError('sequence worker CPU debit changed')
        output = root/'sequences'/row['run_id']
        if sequence_archive_snapshot(output) != row['archive_snapshot']:
            raise ValueError('saved sequence archive changed, including failed child artifacts')
        if row['status'] == 'complete':
            verify_sequence_archive(output)
    return saved


def run_sequence_campaign(path, output, *, validate_only=False):
    validated = validate_sequence_campaign_files(path, execute=not validate_only)
    campaign = validated['campaign']
    if validate_only:
        return {'schema':'sequence-campaign-validation-v1','status':'validated',
                'inventory_sha256':validated['inventory_sha256'],'planned_sequences':len(campaign['entries']),
                'phase_cpu_seconds':validated['phase_cpu_seconds'],'empirical_work_executed':False}
    root = Path(output).absolute()
    budget = PhaseBudget(validated['protocol_path'].parent/('phase-cpu-budget-'+validated['protocol_sha256']),
        identity={'protocol_sha256':validated['protocol_sha256'],'source_sha256':validated['sources']},
        phase_cpu_seconds=validated['phase_cpu_seconds'])
    identity = {'inventory_sha256':validated['inventory_sha256'],'protocol_sha256':validated['protocol_sha256'],
                'source_sha256':validated['sources'],'execution_mode':EXECUTION_MODE,
                'phase_budget_binding_sha256':budget.identity_digest}
    complete = _verify_completed(root,identity,budget)
    if complete is not None:
        return complete
    store = RunStore(root,identity)
    store.claim()
    rows = [{'run_id':e['run_id'],'status':'not_started',
             'steps':[{'step_index':i,'request_id':r['request_id'],'status':'not_started'}
                      for i,r in enumerate(e['manifest_payload']['requests'])]} for e in campaign['entries']]
    result = {'schema':'sequence-campaign-result-v1','status':'running','campaign_id':campaign['campaign_id'],
              'inventory_sha256':validated['inventory_sha256'],'protocol_sha256':validated['protocol_sha256'],
              'execution_mode':EXECUTION_MODE,'planned_sequences':len(rows),'runs':rows,
              'worker_elapsed_scope':'whole_worker_diagnostic; step_timings_keep_their_own_original_observations',
              'phase_cpu_budget_binding_sha256':budget.identity_digest}
    started = time.perf_counter_ns()
    try:
        store.write_artifact('inventory.json',validated['raw'])
        store.write_status(result)
        for index,item in enumerate(validated['checked']):
            current = validate_sequence_campaign_files(path,execute=True)
            if (current['inventory_sha256'] != validated['inventory_sha256']
                    or current['protocol_sha256'] != validated['protocol_sha256']):
                raise ValueError('sequence campaign changed during dispatch')
            entry = item['entry']
            run_id = entry['run_id']
            sequence_root = root/'sequences'/run_id
            request = {'schema':'sequence-campaign-child-v1','inventory_path':str(validated['inventory_path']),
                       'inventory_sha256':validated['inventory_sha256'],'protocol_sha256':validated['protocol_sha256'],
                       'manifest_sha256':item['manifest_sha256'],'run_id':run_id,'output':str(sequence_root)}
            request_path = root/'requests'/(run_id+'.json')
            raw = canonical_json(request)
            if request_path.exists():
                if request_path.is_symlink() or request_path.read_bytes() != raw:
                    raise ValueError('sequence child request changed')
            else:
                atomic_write(request_path,raw)
            # Verify any saved prefix before a worker may resume it.
            if sequence_root.exists():
                verify_sequence_archive(sequence_root)
            rows[index]['status'] = 'running'
            store.write_status(result)
            worker = run_limited([sys.executable,'-m','src.sequence_campaign','--child',str(request_path)],
                root/'workers'/run_id,validated['limits'],identity={'inventory_sha256':validated['inventory_sha256'],
                'run_id':run_id,'request_sha256':digest(raw),'source_sha256':validated['sources']},
                phase_budget=budget,phase=entry['phase'])
            rows[index] = dict(run_id=run_id, worker_record_sha256=digest(canonical_json(worker)),
                               worker_outcome=worker['outcome'],
                               **_observe_sequence(sequence_root,entry,item['manifest_sha256'],validated['protocol_sha256']))
            if worker['outcome']['status'] != 'complete':
                if 'failure' in rows[index]:
                    rows[index]['sequence_failure'] = rows[index]['failure']
                rows[index].update(status='failed',failure={'kind':worker['outcome']['kind']})
            store.write_artifact(run_id+'-outcome.json',canonical_json(rows[index]))
            store.write_status(result)
        result.update(status='complete',outcome='complete' if all(r['status']=='complete' for r in rows) else 'failed',
                      completed_sequences=sum(r['status']=='complete' for r in rows),
                      failed_sequences=sum(r['status']!='complete' for r in rows),
                      controller_wall_ns_before_commit=time.perf_counter_ns()-started,
                      phase_cpu_budget_at_completion=budget.snapshot(),
                      completion_meaning='controller sealed all planned outcomes; inspect outcome and each sequence status')
        return store.finish(result)
    except BaseException as exc:
        result.update(status='failed',failure={'type':type(exc).__name__,'message':str(exc)},
                      controller_wall_ns_before_commit=time.perf_counter_ns()-started)
        store.write_status(result)
        raise
    finally:
        store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', type=Path, required=True)
    args = parser.parse_args()
    return _child(args.child)


if __name__ == '__main__':
    raise SystemExit(main())
