"""Read-only verification of actual controller seals, limits and CPU debits."""
import sys
from pathlib import Path
from research_v80.config import ROOT
from research_v80.implementation_audit import verify_implementation
from research_v80.campaign import command
from research_v80.worker import expected_artifacts
from research_v80.io import require
from research_v61.postrun import verify_kernel
from src.run_store import canonical_json,digest,read_completed

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
                identity['command'] == command(root/'plan.json'),
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
        verify_implementation(trial,completion['implementation'],completion['shared_primal_kernel'])
        require(completion['schema'] == 'four-cell-complete-service-worker-v80' and completion['trial'] == trial and
                completion['status'] == 'complete' and completion['complete_model'] is True and
                completion['program_sha256'] == program_sha and completion['source_files_sha256'] == digest(canonical_json(program['new_sources'])) and
                completion['slurm_job_id'] == plan['slurm_job_id'], 'Completion binding differs')
        require(set(completion['artifacts']) == expected_artifacts(trial), 'Worker artifact inventory differs')
        for name, entry in completion['artifacts'].items():
            observed = inputs.read(root/'outputs'/name, retain=False)
            require(entry == dict(file=name, **observed), 'Declared artifact bytes differ: '+trial+'/'+name)
    require(debit_ids == set(snapshot['attempts']), 'CPU ledger has missing/extra worker attempts')
    return result

