"""Read-only complete V61 state, lineage, model and CPU receipt audit.

No neural inference, quantization, or ledger mutation. This closes artifact
binding/accounting gaps in the frozen auditor; it does not turn execution
metadata into hostile-storage authentication or an independent numerical proof.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
import time

from research_v61.campaign import ROOT, verify, bound
from research_v61.service import gram_budget, trust_read
from research_v61.state import Record, validate_state
from research_v38.bootstrap_target import CHECKPOINT_HASHES
from src.experiment_inventory import source_hashes
from src.phase_budget import read_budget_snapshot
from src.run_store import canonical_json, digest, read_completed, strict_json

TRIAL_REPRESENTATIONS = dict(cached='lossless', compressed='compressed48',
                            hybrid='hybrid_gram', cold='lossless')
REPRESENTATIONS = ('lossless', 'compressed48', 'hybrid_gram')


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Inputs:
    """Hash consumed regular files and detect replacement during this audit."""
    def __init__(self):
        self.files = {}
        self.signatures = {}

    @staticmethod
    def signature(path):
        require(not path.is_symlink() and path.is_file(), 'Input is not a regular file: '+str(path))
        info = path.stat()
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def read(self, path, *, retain=True, maximum=2*2**30):
        path = Path(path).absolute()
        before = self.signature(path)
        require(before[2] <= maximum, 'Input exceeds byte bound: '+str(path))
        chunks, hashed, count = [], hashlib.sha256(), 0
        with path.open('rb') as stream:
            while chunk := stream.read(1024*1024):
                hashed.update(chunk)
                count += len(chunk)
                require(count <= maximum, 'Input exceeds byte bound while reading: '+str(path))
                if retain:
                    chunks.append(chunk)
        require(before == self.signature(path), 'Input changed during reading: '+str(path))
        entry = dict(bytes=count, sha256=hashed.hexdigest())
        key = str(path)
        require(key not in self.files or self.files[key] == entry, 'Input changed between reads: '+key)
        self.files[key], self.signatures[key] = entry, before
        return b''.join(chunks) if retain else entry

    def json(self, path):
        blob = self.read(path, maximum=64*2**20)
        value = strict_json(blob)
        require(type(value) is dict and canonical_json(value) == blob,
                'Canonical JSON object required: '+str(path))
        return value

    def unchanged(self):
        """Rehash final bytes: unchanged NFS metadata does not imply unchanged content."""
        for name, original_signature in self.signatures.items():
            path, expected = Path(name), self.files[name]
            message = 'Input changed before receipt: '+name
            before = self.signature(path)
            require(before == original_signature, message)
            hashed, count = hashlib.sha256(), 0
            with path.open('rb') as stream:
                while chunk := stream.read(1024*1024):
                    count += len(chunk)
                    # Bound reads even if a growing file's metadata is stale.
                    require(count <= expected['bytes'], message)
                    hashed.update(chunk)
            require(before == self.signature(path), message)
            require(dict(bytes=count, sha256=hashed.hexdigest()) == expected, message)


def bind_ledger_snapshot(directory, snapshot, inputs):
    """Bind the bytes parsed by the ledger reader to this audit's inventory."""
    actual = inputs.read(Path(directory)/'budget/ledger.json', retain=False)
    require(actual == dict(bytes=snapshot['ledger_bytes'], sha256=snapshot['ledger_sha256']),
            'Ledger changed between snapshot and input inventory')


def registered_records(program):
    rows = program['records']
    records = tuple(Record(row['id'], tuple(row['tokens']),
        canonical_json(program['record_provenance'][row['id']])) for row in rows)
    require(records == tuple(sorted(records, key=lambda item: item.record_id)),
            'Registered records are not canonically ordered')
    require(len({r.record_id for r in records}) == len(records), 'Duplicate registered record')
    require(program['deletion_order'] == [r.record_id for r in records],
            'Registered deletion order differs from worker sequence')
    require(sum(map(lambda r: len(r.tokens), records)) == program['normalization'],
            'Registered original token normalization differs')
    return records


def model_matches_state(view, model):
    """Compare every actual ordered code byte, without allocating a joined model."""
    offset = 0
    packed = memoryview(model)
    for code in view.stage_codes:
        end = offset + len(code.packed_indices)
        require(packed[offset:end] == code.packed_indices,
                'Exported model differs from packed state codes at '+code.stage_id)
        offset = end
    require(offset == len(model), 'Exported model has trailing or missing packed codes')
    return dict(model_sha256=digest(model), model_bytes=len(model),
                code_count=sum(c.rows*c.columns for c in view.stage_codes),
                stages=len(view.stage_codes))


def storage_matches_metadata(metadata, state_blob, trust_blob, checkpoint_bytes):
    actual = dict(state_bytes=len(state_blob), trust_bytes=len(trust_blob),
                  complete_deployment_bytes=len(state_blob)+len(trust_blob)+checkpoint_bytes)
    for key, value in actual.items():
        require(type(metadata.get(key)) is int and metadata[key] == value,
                'Reported storage differs from actual bytes: '+key)
    return dict(actual, live_state_bytes=len(state_blob)+len(trust_blob))


def execution_matches_target(execution, target):
    fixed = strict_json(target.fixed_payload)
    require(execution.get('schema') == 'full-precision-source-execution-binding-v61',
            'Execution provenance schema differs')
    require(execution.get('target_sha256') == digest(target.fixed_payload) and
            execution.get('anchor_target_sha256') == digest(target.anchor_payload) and
            execution.get('calibration_target_sha256') == target.calibration_target_sha256,
            'Execution provenance does not bind actual state target')
    require(digest(canonical_json(execution['decoder'])) == fixed['decoder_sha256']
        and digest(canonical_json(execution['implementation'])) == fixed['implementation_manifest_sha256']
        and execution['provider_sha256'] == fixed['provider_sha256']
        and execution['teacher_stages'] == fixed['calibration_target']['teacher_stages'],
        'Execution decoder, implementation or original teacher binding differs')
    require(execution['checkpoint']['files_sha256'] == CHECKPOINT_HASHES, 'Execution checkpoint identity differs')


def expected_artifacts(trial):
    names = {'execution-provenance.json', 'admission.json'}
    if trial == 'prepare':
        names.add('original-model.bin')
        for rep in REPRESENTATIONS:
            names.update((rep+'-original.bin', rep+'-trust.json'))
    elif trial == 'oracle':
        for step in (1, 2):
            names.add(f'step-{step}-model.bin')
            for rep in REPRESENTATIONS:
                names.update((f'step-{step}-{rep}.bin', f'step-{step}-{rep}-trust.json'))
    else:
        for step in (1, 2):
            names.update(f'step-{step}-{suffix}' for suffix in ('model.bin', 'state.bin', 'trust.json'))
    return names


def audit_states(directory, program, completions, frozen, inputs, checkpoint_bytes,
                 *, expected_stages=24, expected_codes=42_467_328):
    """Artifact checks, also exercised with tiny complete targets in fixtures."""
    directory = Path(directory)
    records = registered_records(program)
    budget = gram_budget(program['normalization'])
    executions = {}
    for trial in completions:
        path = directory/trial/'outputs/execution-provenance.json'
        executions[trial] = inputs.json(path)
        require(digest(canonical_json(executions[trial])) == completions[trial]['execution_provenance_sha256'],
                'Completion execution provenance commitment differs')
    require(all(value == executions['prepare'] for value in executions.values()),
            'Worker execution provenance differs across arms/oracle')
    comparisons = {(row['trial'], row['step']): row for row in frozen['comparisons']}
    require(len(comparisons) == len(frozen['comparisons']) == 8 and
            set(comparisons) == {(trial, step) for trial in TRIAL_REPRESENTATIONS for step in (1, 2)},
            'Frozen audit does not cover exactly the eight declared comparisons')
    prepared = directory/'prepare/outputs'
    original_model = inputs.read(prepared/'original-model.bin')
    target, originals, original_storage = None, {}, {}
    for rep in REPRESENTATIONS:
        blob = inputs.read(prepared/(rep+'-original.bin'))
        trust_blob = inputs.read(prepared/(rep+'-trust.json'))
        view = validate_state(blob, expected_target=target, expected_records=records,
            gram_trust=trust_read(strict_json(trust_blob)), gram_budget=budget)
        require(view.representation == rep, 'Original representation differs')
        target = view.target if target is None else target
        require(target.original_tokens == program['normalization'], 'State original normalization differs')
        extent = model_matches_state(view, original_model)
        require(extent['stages'] == expected_stages and extent['code_count'] == expected_codes,
                'Complete registered model extent differs')
        original_storage[rep] = storage_matches_metadata(
            completions['prepare']['preparation']['representations'][rep], blob, trust_blob, checkpoint_bytes)
        originals[rep] = view
    execution_matches_target(executions['prepare'], target)
    calibration = inputs.read(bound(program['inputs']['v59_candidate_target']))
    base = inputs.read(bound(program['inputs']['v59_base_target']))
    reference_model = inputs.read(bound(program['inputs']['v59_candidate_model']))
    require(target.anchor_payload == base and canonical_json(strict_json(target.fixed_payload)['calibration_target']) == calibration
        and target.calibration_target_sha256 == digest(calibration), 'Actual state target differs from frozen V59 numerical target')
    for completion in completions.values():
        require(completion['service_target_sha256'] == digest(target.fixed_payload)
            and completion['calibration_target_sha256'] == digest(calibration)
            and completion['base_target_sha256'] == digest(base), 'Completion actual target commitments differ')
    require(completions['prepare']['code_count'] == expected_codes, 'Original model count metadata differs')
    require(frozen['preparation'] == completions['prepare']['preparation'], 'Frozen preparation metadata differs')
    outputs, storage = [], {}
    for trial, rep in TRIAL_REPRESENTATIONS.items():
        previous = originals[rep]
        storage[trial] = []
        require(len(completions[trial]['steps']) == 2, 'Worker step count differs')
        for step in (1, 2):
            before_count = len(records) if step == 1 else program['retained_counts'][step-2]
            after_count = program['retained_counts'][step-1]
            expected = records[len(records)-after_count:]
            deleted = records[len(records)-before_count:len(records)-after_count]
            root, oracle = directory/trial/'outputs', directory/'oracle/outputs'
            current = inputs.read(root/f'step-{step}-state.bin')
            current_trust = inputs.read(root/f'step-{step}-trust.json')
            fresh = inputs.read(oracle/f'step-{step}-{rep}.bin')
            fresh_trust = inputs.read(oracle/f'step-{step}-{rep}-trust.json')
            new = validate_state(current, expected_target=target, expected_records=expected,
                gram_trust=trust_read(strict_json(current_trust)), gram_budget=budget)
            fresh_view = validate_state(fresh, expected_target=target, expected_records=expected,
                gram_trust=trust_read(strict_json(fresh_trust)), gram_budget=budget)
            require(new.representation == fresh_view.representation == rep, 'Successor representation differs')
            require(current == fresh, 'Successor actual bytes differ from independent fresh state')
            require(current_trust == fresh_trust, 'Successor external Gram trust bytes differ')
            before = previous.source_map()
            require(all(before.get(key) == value for key, value in new.source_map().items()),
                    'Retained descriptor changed during deletion')
            model = inputs.read(root/f'step-{step}-model.bin')
            fresh_model = inputs.read(oracle/f'step-{step}-model.bin')
            require(model == fresh_model, 'Exported model differs from fresh oracle')
            if step == 2:
                require(model == reference_model, 'Final-six actual model differs from frozen V59 candidate')
            extent = model_matches_state(new, model)
            model_matches_state(fresh_view, fresh_model)
            # All representations use the same oracle export, establishing
            # cross-representation model equality as well as target equality.
            require(extent['stages'] == expected_stages and extent['code_count'] == expected_codes,
                    'Successor complete model extent differs')
            report = dict(trial=trial, step=step, representation=rep,
                state_sha256=digest(current), state_bytes=len(current),
                complete_model_sha256=extent['model_sha256'], code_count=extent['code_count'],
                stages=extent['stages'], retained_records=len(expected),
                retained_tokens=sum(len(r.tokens) for r in expected), deleted_count=len(deleted),
                actual_bytes_equal=True, actual_model_bytes_equal=True,
                exact_retained_membership_verified=True)
            require(all(comparisons[trial, step].get(key) == value for key, value in report.items()),
                    'Frozen audit comparison differs from actual artifacts')
            row = completions[trial]['steps'][step-1]
            require(row['step'] == step and row['representation'] == rep and
                    row['retained_ids'] == [r.record_id for r in expected] and
                    row['deleted_ids'] == [r.record_id for r in deleted], 'Request membership metadata differs')
            actual_storage = storage_matches_metadata(row, current, current_trust, checkpoint_bytes)
            storage[trial].append(actual_storage)
            oracle_row = completions['oracle']['steps'][step-1]
            require(oracle_row['step'] == step and oracle_row['retained_ids'] == [r.record_id for r in expected]
                    and oracle_row['prior_state_read'] is False and oracle_row['independent_retained_token_traversal'] is True
                    and oracle_row['timing']['neural_stage_record_pairs'] == expected_stages*len(expected),
                    'Oracle execution metadata differs from declared independent route')
            oracle_size = oracle_row['representations'][rep]
            require(oracle_size['state_bytes'] == len(fresh) and oracle_size['trust_bytes'] == len(fresh_trust),
                    'Oracle storage metadata differs')
            outputs.append(dict(report, model_export_matches_state_codes=True,
                cross_representation_target_and_model_verified=True, registered_record_binding_verified=True,
                v59_quality_anchor_actual_bytes_equal=True if step == 2 else None,
                storage=actual_storage))
            previous = new
        for key in ('live_state_bytes', 'complete_deployment_bytes'):
            require(frozen['timings'][trial][key] == [row[key] for row in storage[trial]],
                    'Frozen audit storage totals differ: '+trial+'/'+key)
    for control in ('cached', 'hybrid', 'cold'):
        for name, key in (('compressed_live_state_saving', 'live_state_bytes'),
                          ('compressed_deployment_saving', 'complete_deployment_bytes')):
            actual = [1-a[key]/b[key] for a, b in zip(storage['compressed'], storage[control])]
            require(frozen['ratios'][control][name] == actual, 'Frozen storage ratio differs')
    return dict(comparisons=outputs, original_storage=original_storage,
        anchor_target_sha256=digest(target.anchor_payload), fixed_target_sha256=digest(target.fixed_payload),
        calibration_target_sha256=target.calibration_target_sha256, v59_final_model_sha256=digest(reference_model),
        all_final_six_models_equal_actual_v59_candidate=True,
        original_model_sha256=digest(original_model), checkpoint_bytes=checkpoint_bytes)


def verify_kernel(kernel):
    from research_v50.neighbors import source, HELPER
    from src import primal_certificate_v30 as primal
    require(kernel['backend']=='normal_neighbor_primal_v50' and
        kernel['source_sha256']==digest(source().encode()) and
        kernel['original_c_source_sha256']==digest(primal._C_SOURCE.encode()) and
        kernel['wrapper_sha256']==digest((ROOT/'research_v50/neighbors.py').read_bytes()) and
        kernel['flags']==list(primal.native_box._FLAGS), 'Shared primal backend differs')


def verify_worker_receipts(directory, program, inputs, snapshot):
    """Bind sealed controller outcomes/debits without creating ledger locks."""
    result, debit_ids = {}, set()
    program_sha = digest(canonical_json(program))
    prefix_attempts = {}
    require(set(program['trial_order']) == set(program['trials']) and len(program['trial_order']) == len(program['trials']),
        'Complete unique worker order required')
    for trial in program['trial_order']:
        limits = program['trials'][trial]
        root = directory/trial
        transaction, plan = inputs.json(root/'transaction.json'), inputs.json(root/'plan.json')
        identity = inputs.json(root/'worker/identity.json')
        require(identity['identity'] == dict(campaign_sha256=program_sha, trial=trial) and
                identity['cwd'] == str(ROOT) and
                identity['command'] == [sys.executable, '-B', '-m', 'research_v61.worker', str(root/'plan.json')],
                'Sealed worker identity/command differs: '+trial)
        require(identity['phase_budget'] == dict(binding_sha256=snapshot['binding_sha256'],
                phase='feasibility', directory=str(directory/'budget')), 'Worker budget binding differs')
        actual_limits = identity['limits']
        require(all(actual_limits[key] == value for key, value in limits.items()) and
                actual_limits['address_space_bytes'] == program['process_address_space_bytes'] and
                actual_limits['file_size_bytes'] == program['file_size_bytes'] and
                actual_limits['threads'] == 1 and len(actual_limits['affinity_cpus']) == 1,
                'Worker resource limits differ')
        sealed = read_completed(root/'worker', identity)
        require(sealed is not None and sealed['outcome'] == transaction['worker_outcome'] and
                sealed['outcome']['status'] == 'complete' and sealed['outcome']['returncode'] == 0,
                'Sealed worker outcome differs')
        # Include the receipt and all its already validated artifacts in the
        # additive input inventory, not just the convenience transaction file.
        require(inputs.json(root/'worker/result.json') == sealed and
                inputs.json(root/'worker'/sealed['attempt']/'status.json') == sealed,
                'Sealed result and terminal status differ')
        for name in sealed['artifacts']:
            observed = inputs.read(root/'worker'/sealed['attempt']/name, retain=False)
            require(observed == sealed['artifacts'][name],
                    'Sealed artifact changed before input inventory: '+trial+'/'+name)
        request=inputs.json(root/'worker'/sealed['attempt']/'request.json')
        ack=inputs.json(root/'worker'/sealed['attempt']/'limits-applied.json')
        from src.worker_control import THREAD_VARIABLES
        require(request['command'] == identity['command'] and request['cwd'] == identity['cwd']
            and request['limits'] == actual_limits, 'Executed request differs from sealed identity')
        require(ack == sealed['limits_applied'] and ack['request_sha256'] == digest(canonical_json(request))
            and ack['cpu_seconds'] == [limits['cpu_seconds'],limits['cpu_seconds']+1]
            and ack['address_space'] == [program['process_address_space_bytes']]*2
            and ack['file_size'] == [program['file_size_bytes']]*2
            and ack['affinity_cpus'] == actual_limits['affinity_cpus']
            and ack['thread_environment'] == {name:'1' for name in THREAD_VARIABLES}, 'Applied worker limit acknowledgment differs')
        debit = sealed['budget_attempt_id']
        require(debit not in debit_ids and canonical_json(snapshot['attempts'].get(debit)) == canonical_json(sealed['budget_debit']),
                'Sealed worker CPU debit differs from ledger')
        usage=sealed['resource_usage']
        require(all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('user_cpu_ns','system_cpu_ns','total_cpu_ns'))
            and usage['user_cpu_ns']+usage['system_cpu_ns'] == usage['total_cpu_ns']
            and sealed['budget_debit']['observed_cpu_ns'] == usage['total_cpu_ns']
            and sealed['budget_debit']['state'] == 'settled'
            and sealed['budget_debit']['reserved_cpu_seconds'] == limits['cpu_seconds']+2
            and sealed['budget_debit']['charged_cpu_seconds'] <= limits['cpu_seconds']+2
            and sealed['budget_reservation_overrun'] is False,
                'Observed CPU usage differs from settled debit')
        debit_ids.add(debit)
        prefix_attempts[debit]=sealed['budget_debit']
        used=sum(row['charged_cpu_seconds'] for row in prefix_attempts.values())
        expected_budget=dict(binding_sha256=snapshot['binding_sha256'],phase_cpu_seconds=snapshot['phase_cpu_seconds'],
            charged_cpu_seconds={'feasibility':used},attempts=dict(prefix_attempts),
            over_cap={'feasibility':used>snapshot['phase_cpu_seconds']['feasibility']})
        require(canonical_json(transaction['budget']) == canonical_json(expected_budget), 'Transaction prefix CPU ledger differs')
        require(plan == dict(trial=trial, program=str(directory/'program.json'), program_sha256=program_sha,
                output=str(root/'outputs'), slurm_job_id=transaction['slurm_job_id']), 'Worker plan differs')
        result[trial] = inputs.json(root/'outputs/completion.json')
        completion = result[trial]
        verify_kernel(completion['shared_primal_kernel'])
        require(completion['schema'] == 'complete-full-precision-service-worker-v61' and completion['trial'] == trial and
                completion['status'] == 'complete' and completion['complete_model'] is True and
                completion['program_sha256'] == program_sha and completion['source_sha256'] == program['sources'] and
                completion['slurm_job_id'] == plan['slurm_job_id'], 'Completion binding differs')
        require(completion['v59_final_model_actual_bytes_equal'] is (None if trial == 'prepare' else True),
            'Worker final-six actual V59 equality witness differs')
        require(set(completion['artifacts']) == expected_artifacts(trial), 'Worker artifact inventory differs')
        for name, entry in completion['artifacts'].items():
            observed = inputs.read(root/'outputs'/name, retain=False)
            require(entry == dict(file=name, **observed), 'Declared artifact bytes differ: '+trial+'/'+name)
    require(debit_ids == set(snapshot['attempts']), 'CPU ledger has missing/extra worker attempts')
    return result


def audit(directory, frozen_receipt, output):
    start, cpu_start = time.perf_counter_ns(), time.process_time_ns()
    require(os.environ.get('SLURM_JOB_ID'), 'Run this bounded post-run audit under Slurm')
    directory, frozen_receipt, output = (Path(p).absolute() for p in (directory, frozen_receipt, output))
    require(not output.exists() and not output.is_symlink() and output.suffix == '.json',
            'Output must be a fresh JSON path')
    inputs = Inputs()
    program = inputs.json(directory/'program.json')
    # Frozen verification reads source/runtime/historical identities only.
    require(verify(directory) == program, 'Frozen program verification differs')
    registration = inputs.json(directory/'registration.json')
    require(registration['program_sha256'] == digest(canonical_json(program)),
            'Registration changed before input inventory')
    for entry in program['inputs'].values():
        require(inputs.read(bound(entry),retain=False) == {k:entry[k] for k in ('bytes','sha256')}, 'Bound campaign input differs')
    for name,expected in program['sources'].items():
        require(inputs.read(ROOT/name,retain=False)['sha256'] == expected, 'Bound campaign source differs')
    frozen = inputs.json(frozen_receipt)
    require(frozen['schema'] == 'complete-full-precision-service-artifact-audit-v61' and frozen['status'] == 'verified' and
            frozen['campaign'] == str(directory) and frozen['program_sha256'] == digest(canonical_json(program)) and
            frozen['all_declared_artifacts_rehashed'] is True, 'Frozen audit receipt identity differs')
    require(program['normalization'] == 1664 and program['record_count'] == 13 and
            program['tokens_per_record'] == 128 and program['retained_counts'] == [12, 6] and
            len(program['records']) == 13 and all(len(row['tokens']) == 128 for row in program['records']),
            'This additive audit requires the registered V61 workload')
    snapshot = read_budget_snapshot(directory/'budget',
        identity=dict(protocol_sha256=digest(canonical_json(program)), source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'feasibility': program['phase_cpu_seconds']})
    require(snapshot['status'] == 'verified' and not snapshot['reserved_unknown_attempts'] and
            not any(snapshot['over_cap'].values()), 'Campaign budget is unsettled or over cap')
    bind_ledger_snapshot(directory, snapshot, inputs)
    require(frozen['budget'] == snapshot,
            'Frozen audit budget differs from actual settled ledger')
    require(frozen['fresh_campaign_cpu_seconds'] == snapshot['charged_cpu_seconds']['feasibility']
        and frozen['allowance_scope'] == program['allowance_scope'], 'Fresh V61 CPU accounting scope differs')
    completions = verify_worker_receipts(directory, program, inputs, snapshot)
    checkpoint_bytes = 0
    for name, expected_sha in CHECKPOINT_HASHES.items():
        entry = inputs.read(ROOT/'tmp/models/distilgpt2'/name, retain=False)
        require(entry['sha256'] == expected_sha, 'Pinned checkpoint file differs: '+name)
        checkpoint_bytes += entry['bytes']
    require(checkpoint_bytes == program['shared_checkpoint_bytes'] == frozen['shared_checkpoint_bytes'],
            'Reported common checkpoint extent differs')
    evidence = audit_states(directory, program, completions, frozen, inputs, checkpoint_bytes)
    # Timing is bound to its actual receipt, not independently remeasured here.
    for trial, rep in TRIAL_REPRESENTATIONS.items():
        require(frozen['timings'][trial]['request_elapsed_ns'] ==
                [row['request_elapsed_ns'] for row in completions[trial]['steps']], 'Frozen request times differ')
    implementation = {path.name: inputs.read(path, retain=False) for path in sorted(Path(__file__).parent.glob('*.py'))}
    inputs.unchanged()
    result = dict(schema='complete-full-precision-service-additive-artifact-audit-v61', status='verified',
        campaign=str(directory), program_sha256=digest(canonical_json(program)),
        frozen_audit_path=str(frozen_receipt), frozen_audit_sha256=inputs.files[str(frozen_receipt)]['sha256'],
        implementation=implementation, inputs=inputs.files, slurm_job_id=os.environ['SLURM_JOB_ID'],
        evidence=evidence, ledger_snapshot=snapshot,
        analysis_elapsed_ns=time.perf_counter_ns()-start, analysis_cpu_ns=time.process_time_ns()-cpu_start,
        analysis_outside_empirical_worker_ledger=True, frozen_sources_changed=False,
        scope='Actual ordered model codes, common targets, registered retained records/provenance, full canonical bytes, trust sidecars and literal storage checked against frozen execution receipts.',
        caveats=['Trusted controlled execution and filesystem remain assumptions; hashes do not authenticate hostile execution.',
            'No neural feature regeneration, checkpoint-to-target recomputation, quantization or solver rerun in this additive audit.',
            'Independent fresh execution is the frozen oracle worker route, not an independently implemented numerical engine.',
            'Deployment bytes mean state plus required Gram trust sidecar plus config/checkpoint; runtime/system installation and retained audit history remain outside that subtotal.',
            'Attributed preparation/lifetime timers retain the frozen audit convention; omitted shared preparation overhead is reported separately, not converted here into a standalone lifetime measurement.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(canonical_json(result))
        stream.flush()
        os.fsync(stream.fileno())
    print(canonical_json(dict(status='verified',output=str(output),comparisons=len(evidence['comparisons']),
        receipt_sha256=digest(canonical_json(result)))).decode())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign_directory')
    parser.add_argument('frozen_audit_receipt')
    parser.add_argument('fresh_output')
    arguments = parser.parse_args()
    audit(arguments.campaign_directory, arguments.frozen_audit_receipt, arguments.fresh_output)
