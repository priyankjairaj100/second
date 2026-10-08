"""Audit completed V30 service evidence without model inference or ledger writes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.experiment_inventory import source_hashes
from src.phase_budget import read_budget_snapshot
from src.run_store import canonical_json,digest,strict_json
from src.service_terminal_evidence_v30 import verify_completed


def require(condition,message):
    if not condition:
        raise ValueError(message)


def hashed(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(),'missing or symbolic audit input: '+str(path))
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read_json(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(),'missing or symbolic audit metadata: '+str(path))
    value = strict_json(path.read_bytes())
    require(type(value) is dict,'audit metadata must be an object')
    return value


def verify_plan(campaign,trial,plan,program,program_hash,protocol_hash,results):
    """Bind both static and late-bound inputs to their registered origins."""
    attempt = campaign/'attempts'/trial['id']
    require(plan.get('program_sha256') == program_hash,'plan program binding differs')
    require(plan.get('protocol_sha256') == protocol_hash,'plan protocol binding differs')
    require(plan.get('source_sha256') == program['source_sha256'],'plan source binding differs')
    require(plan.get('phase') == 'feasibility' and plan.get('output') == str(attempt/'outputs'),
            'plan phase or output differs')
    generated = {'source_sha256','protocol_sha256','program_sha256','phase','output'}
    if 'controller_continuation_sha256' in plan:
        path = campaign/'continuation-v1.json'
        continuation = read_json(path)
        require(continuation.get('schema') == 'service-controller-continuation-v30'
            and continuation.get('original_program_sha256') == program_hash
            and continuation.get('original_protocol_sha256') == protocol_hash,
            'continuation does not bind the original registration')
        require(plan['controller_continuation_sha256'] == hashed(path),
                'plan continuation binding differs')
        require(trial['id'] in continuation.get('remaining_trials',[]),
                'trial is outside the registered continuation')
        for key in ('budget_reset','evidence_changed','numerical_source_changed','preparation_repeated',
                    'samples_changed','thresholds_changed'):
            require(continuation.get(key) is False,'continuation changes a preserved premise: '+key)
        generated.add('controller_continuation_sha256')
    require(set(plan) == set(trial['plan'])|generated,'plan contains missing or unregistered fields')
    for key,expected in trial['plan'].items():
        if key != 'inputs':
            require(plan[key] == expected,'registered plan value differs: '+trial['id']+'/'+key)
    static = trial['plan']['inputs']
    late = trial.get('inputs_from_trial',{})
    require(not set(static)&set(late),'late input overrides a registered static input')
    require(set(plan['inputs']) == set(static)|set(late),'plan input access differs from registration')
    for key,entry in static.items():
        require(plan['inputs'][key] == entry,'registered input binding differs: '+key)
    for key,binding in late.items():
        require(binding.get('trial') in results,'late input parent is not an earlier completed trial')
        parent = results[binding['trial']]
        if binding.get('completion') is True:
            require(set(binding) == {'trial','completion'},'late completion binding fields differ')
            path = campaign/'attempts'/binding['trial']/'outputs/completion.json'
        else:
            require(set(binding) == {'trial','artifact'},'late artifact binding fields differ')
            require(binding['artifact'] in parent['artifacts'],'late parent artifact is missing')
            entry = parent['artifacts'][binding['artifact']]
            path = campaign/'attempts'/binding['trial']/'outputs'/entry['file']
        require(plan['inputs'][key] == dict(path=str(path),sha256=hashed(path)),
                'late input does not name its exact registered parent: '+key)
    for entry in plan['inputs'].values():
        require(hashed(Path(entry['path'])) == entry['sha256'],'bound input bytes changed')
        if 'bytes' in entry:
            require(Path(entry['path']).stat().st_size == entry['bytes'],'bound input byte count differs')


def verify_worker_schedule(campaign,trial,transaction,identity,registration,program):
    """Check the literal command, resource limits, clock, and interpreter."""
    command = identity.get('command')
    require(type(command) is list and len(command) == 3,'worker command shape differs')
    require(command[1:] == [str(campaign/'source/scripts'/trial['script']),
                           str(campaign/'attempts'/trial['id']/'plan.json')],
            'worker did not run the registered frozen script and plan')
    require(hashed(Path(command[0]).resolve()) == registration['runtime']['interpreter']['sha256'],
            'worker interpreter differs from registered runtime')
    require(identity.get('cwd') == str(campaign/'source'),'worker cwd differs from frozen source')
    limits = identity.get('limits')
    require(type(limits) is dict and limits == dict(wall_seconds=trial['wall_seconds'],
        cpu_seconds=trial['cpu_seconds'],address_space_bytes=program['address_space_bytes'],
        threads=1,affinity_cpus=program['affinity_cpus'],file_size_bytes=512*2**20,
        termination_grace_seconds=1),'worker resource limits differ from registered controller')
    elapsed = transaction.get('controller_elapsed_ns')
    require(type(elapsed) is int and elapsed > 0,'controller time must be a positive integer')
    require(transaction.get('primary_clock') == program['primary_clock'],'controller clock differs from registration')
    worker_elapsed = transaction['worker_outcome'].get('elapsed_wall_ns')
    require(type(worker_elapsed) is int and 0 <= worker_elapsed <= elapsed,
            'nested worker time exceeds complete controller time')


def verify_service_claims(result,plan,program):
    """Check scientific fields independently of filename and artifact equality."""
    if 'method' not in plan:
        return  # Component gates have their own declared schema and dependency checks.
    require(result.get('schema') == 'adaptive-complete-service-transaction-v30','unexpected complete-service schema')
    require(result.get('method') == plan['method'],'terminal method differs from registration')
    require(result.get('source_sha256') == program['source_sha256'],'terminal source binding differs')
    require(result.get('confirmation') is False and result.get('scientific_promotion') is False
        and result.get('use_candidates') is False,'terminal scientific policy flags differ')
    for key in ('original_token_count','solver_backend','solver_budget','max_point_work_units'):
        require(result.get(key) == plan[key],'terminal policy differs: '+key)
    require(result.get('retained_record_ids') == plan['record_ids']
        and result.get('deleted_record_ids') == plan['deleted_ids'],'terminal membership differs')
    original = read_json(Path(plan['inputs']['records']['path']))
    require(set(original) == {'records'},'original record payload fields differ')
    records = original['records']
    require(result.get('original_record_ids') == [row['id'] for row in records],'terminal original membership differs')
    require(result.get('original_records_sha256') == digest(canonical_json(original)),'terminal original token binding differs')
    require(result.get('records_input_sha256') == plan['inputs']['records']['sha256'],'terminal record file binding differs')
    retained = [row for row in records if row['id'] in set(plan['record_ids'])]
    require(result.get('retained_token_count') == sum(len(row['tokens']) for row in retained),'terminal retained token count differs')
    require(sum(len(row['tokens']) for row in records) == plan['original_token_count'],'original normalization differs from token file')
    require(result.get('checkpoint_files_sha256') == {name:plan['inputs'][key]['sha256'] for name,key in (
        ('config.json','config'),('model.safetensors','weights'))},'terminal checkpoint binding differs')
    require(result.get('complete_model') is True and result.get('model_roundtrip_exact') is True,'model verification is incomplete')
    require(result.get('stage_count') == 24 and type(result.get('stage_ids')) is list
        and len(result['stage_ids']) == len(set(result['stage_ids'])) == 24,'complete stage set is invalid')
    require(type(result.get('model_code_elements')) is int and result['model_code_elements'] > 0,'model element count is invalid')
    stateful = plan['method'] != 'model_only_fresh'
    require(result.get('complete_state') is stateful,'state output contract differs')
    require(set(result['artifacts']) == ({'model','state'} if stateful else {'model'}),'artifact access contract differs')
    if stateful:
        require(result.get('state_roundtrip_canonical') is True
            and result.get('committed_record_ids') == plan['record_ids'],'canonical state verification differs')
    for kind in result['artifacts']:
        require(result[kind+'_artifact'] == result['artifacts'][kind],'named artifact and output manifest disagree')
    diagnostics = result.get('diagnostics',{})
    traversals = diagnostics.get('neural_stage_record_pairs')
    require(traversals == (0 if plan['method'] in ('repair','indexed_fresh') else 24*len(retained)),
            'neural traversal count differs from declared method')
    require(result.get('fixed_target_sha256') != result.get('base_target_sha256'),'fixed and sequential targets collide')


def verify_final_budget(campaign,program,protocol_hash,receipts):
    """Require every phase debit to match one completed registered receipt."""
    snapshot = read_budget_snapshot(campaign/'phase-cpu-budget',
        identity=dict(protocol_sha256=protocol_hash,source_sha256=program['source_sha256']),
        phase_cpu_seconds={'feasibility':program['phase_cpu_cap_seconds']})
    require(snapshot['status'] == 'verified','final phase ledger is unavailable')
    require(snapshot['reserved_unknown_attempts'] == 0,'final phase ledger has unresolved reservations')
    expected = {}
    for receipt in receipts:
        key = receipt['budget_attempt_id']
        require(key not in expected,'a settled CPU debit is reused by multiple trials')
        expected[key] = receipt['budget_debit']
    require(snapshot['attempts'] == expected,'final phase debits differ from all registered completed receipts')
    charged = sum(receipt['budget_debit']['charged_cpu_seconds'] for receipt in receipts)
    require(snapshot['charged_cpu_seconds'] == {'feasibility':charged},'final phase charge differs from receipt sum')
    require(not snapshot['over_cap']['feasibility'],'final phase charge exceeds the registered cap')
    require(not snapshot['reservation_overrun_attempts'],'a worker exceeded its reserved CPU allowance')
    return snapshot


def verify_supersession(campaign,program,program_hash,protocol_hash):
    """Permit explicit cancellation only when no trial attempt was started."""
    path = campaign/'supersession.json'
    ids = [trial['id'] for trial in program['trials']]
    require(len(ids) == len(set(ids)),'duplicate registered trial IDs')
    if not path.exists():
        return [],None
    record = read_json(path)
    require(set(record) == {'schema','program_sha256','protocol_sha256','cancelled_trial_ids',
        'reason','created_unix_ns','final_completed_trial_ids'},'supersession fields differ')
    require(record['schema'] == 'full-service-supersession-v30'
        and record['program_sha256'] == program_hash and record['protocol_sha256'] == protocol_hash,
        'supersession does not bind the original registration')
    require(type(record['created_unix_ns']) is int and record['created_unix_ns'] > 0
        and type(record['reason']) is str and record['reason'].strip(),'supersession lacks time or reason')
    cancelled,completed = record['cancelled_trial_ids'],record['final_completed_trial_ids']
    require(type(cancelled) is list and cancelled and type(completed) is list,
            'supersession requires explicit cancelled and completed trial IDs')
    require(cancelled == [name for name in ids if name in set(cancelled)]
        and completed == [name for name in ids if name in set(completed)]
        and set(cancelled).isdisjoint(completed) and set(cancelled)|set(completed) == set(ids),
        'supersession must partition the original registration exactly')
    observed = {path.name for path in (campaign/'attempts').iterdir() if path.is_dir()}
    require(observed == set(completed),'supersession omits an observed attempt or lists an unstarted completion')
    for name in cancelled:
        require(not (campaign/'attempts'/name).exists(),'cannot cancel a started trial or omit its outcome')
    return cancelled,record


def analyze(campaign):
    started = time.process_time_ns()
    campaign = Path(campaign).absolute()
    program_raw = (campaign/'program.json').read_bytes()
    protocol_raw = (campaign/'protocol.json').read_bytes()
    program,protocol = strict_json(program_raw),strict_json(protocol_raw)
    registration = read_json(campaign/'registration.json')
    program_hash,protocol_hash = digest(program_raw),digest(protocol_raw)
    require(registration['program_sha256'] == program_hash,'registration program binding differs')
    require(registration['protocol_sha256'] == protocol_hash and protocol['program_sha256'] == program_hash,
            'registration protocol binding differs')
    require(protocol.get('phase_cpu_seconds') == {'feasibility':program['phase_cpu_cap_seconds']},'registered CPU caps differ')
    require(source_hashes(campaign/'source') == program['source_sha256'],'frozen dispatch source changed')
    evidence = {}
    def bind(path):
        path = Path(path).absolute()
        name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        evidence[name] = hashed(path)
    for name in ('program.json','protocol.json','registration.json','registered-launcher.py'):
        bind(campaign/name)
    for name,expected in program['controller_sha256'].items():
        require(hashed(campaign/'source'/name) == expected,'frozen controller source changed: '+name)
        bind(campaign/'source'/name)
        if name.startswith('scripts/launch_'):
            require(hashed(campaign/'registered-launcher.py') == expected,'registered launcher snapshot differs')
    continuation_path = campaign/'continuation-v1.json'
    if continuation_path.exists():
        continuation = read_json(continuation_path)
        require(continuation.get('original_program_sha256') == program_hash
            and continuation.get('original_protocol_sha256') == protocol_hash,
            'continuation original bindings differ')
        require(hashed(campaign/'registered-launcher.py') == continuation['original_launcher_sha256'],
                'continuation original launcher differs')
        require(hashed(campaign/'attempts/prepare-128/outputs/completion.json')
            == continuation['verified_preparation_terminal_sha256'],'continuation preparation receipt differs')
        bind(continuation_path)
        for name,expected in continuation['controller_sha256'].items():
            require(hashed(ROOT/name) == expected,'continuation controller source changed: '+name)
            bind(ROOT/name)
    for name,expected in program['historical_frozen_ledgers'].items():
        require(hashed(ROOT/name) == expected,'historical ledger changed: '+name)
        bind(ROOT/name)
    prerequisite = program.get('quality_prerequisite')
    if prerequisite is not None:
        require(hashed(Path(prerequisite['path'])) == prerequisite['sha256'],'quality prerequisite binding changed')
        quality = verify_completed(Path(prerequisite['path']).parent.parent)
        require(quality.get('development_quality_gate_pass') is True and quality.get('historical_parity_pass') is True,
                'quality prerequisite did not pass')
        bind(Path(prerequisite['path']))
    cancelled,supersession = verify_supersession(campaign,program,program_hash,protocol_hash)
    if supersession is not None:
        bind(campaign/'supersession.json')
    rows,results,receipts = [],{},[]
    service_reference = None
    for trial in program['trials']:
        name = trial['id']
        if name in cancelled:
            continue
        require(name not in results,'duplicate registered trial')
        attempt = campaign/'attempts'/name
        result = verify_completed(attempt)
        plan = read_json(attempt/'plan.json')
        verify_plan(campaign,trial,plan,program,program_hash,protocol_hash,results)
        transaction = read_json(attempt/'transaction.json')
        receipt = read_json(attempt/'worker/result.json')
        identity = read_json(attempt/'worker/identity.json')
        verify_worker_schedule(campaign,trial,transaction,identity,registration,program)
        require(receipt['budget_debit']['reserved_cpu_seconds'] == trial['cpu_seconds']+2,
                'CPU reservation differs from registered worker allowance')
        verify_service_claims(result,plan,program)
        if 'method' in plan:
            comparable = {key:result[key] for key in ('fixed_target_sha256','base_target_sha256','target_recipe',
                'stage_ids','model_code_elements','original_records_sha256','checkpoint_files_sha256')}
            if service_reference is None:
                service_reference = comparable
            require(comparable == service_reference,'complete methods use different target or original-source semantics')
        for dependency in trial.get('depends',[]):
            require(dependency['trial'] in results,'dependency is not an earlier completed trial')
            prior = results[dependency['trial']]
            for key,expected in dependency.get('equals',{}).items():
                value = prior
                for part in key.split('.'):
                    value = value[part]
                require(value == expected,'registered dependency gate failed: '+key)
        for comparison in trial.get('compare_to',[]):
            require(comparison['trial'] in results,'comparison is not an earlier completed trial')
            prior = results[comparison['trial']]
            for kind in comparison.get('artifacts',['model']):
                for key in ('bytes','sha256'):
                    require(result['artifacts'][kind][key] == prior['artifacts'][kind][key],
                            'complete cross-method artifact mismatch')
        diagnostic = result.get('diagnostics',{})
        rows.append(dict(trial=name,method=result.get('method','component'),
            controller_seconds=transaction['controller_elapsed_ns']/1e9,
            observed_cpu_seconds=receipt['resource_usage']['total_cpu_ns']/1e9,
            charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],artifacts=result['artifacts'],
            neural_stage_record_pairs=diagnostic.get('neural_stage_record_pairs'),
            anchor_preparation_stage_record_pairs=diagnostic.get('anchor_preparation_stage_record_pairs'),
            stage_count=result.get('stage_count'),code_elements=result.get('model_code_elements')))
        results[name] = result
        receipts.append(receipt)
        for path in sorted(attempt.rglob('*')):
            if path.is_file() and path.suffix in ('.json','.txt','.log'):
                bind(path)
    budget = verify_final_budget(campaign,program,protocol_hash,receipts)
    bind(campaign/'phase-cpu-budget/ledger.json')
    times = {row['trial']:row['controller_seconds'] for row in rows}
    pairs = [dict(pair=i,cold_seconds=times[f'cold-{i:03}'],repair_seconds=times[f'repair-{i:03}'],
        cold_over_repair=times[f'cold-{i:03}']/times[f'repair-{i:03}']) for i in range(1,4)
        if f'cold-{i:03}' in times and f'repair-{i:03}' in times]
    ratios = [row['cold_over_repair'] for row in pairs]
    observed_mean = math.exp(sum(map(math.log,ratios))/len(ratios)) if ratios else None
    return dict(schema='complete-service-audit-v30',status='complete',confirmation=False,
        program_sha256=program_hash,protocol_sha256=protocol_hash,trials=rows,
        complete_cross_method_agreement=True,pairs=pairs,phase_budget=budget,
        cancelled_unstarted_trials=cancelled,supersession=supersession,observed_pair_count=len(pairs),
        three_pair_estimator_available=len(pairs)==3,
        geometric_mean_cold_over_repair=observed_mean if len(pairs)==3 else None,
        descriptive_observed_pair_geometric_mean=observed_mean,
        minimum_cold_over_repair=min(ratios) if ratios else None,
        maximum_cold_over_repair=max(ratios) if ratios else None,
        replication_scope=str(len(pairs))+' observed timing pairs; one shared corpus, model, and deletion request',
        target_scope='fixed nearest-anchor features; distinct from sequential calibration',
        preparation_seconds=times['prepare-128'],preparation_incremental_overhead=None,
        lifetime_claim='unavailable until matched original model-only preparation is measured',
        evidence_sha256=evidence,analysis_source_sha256={name:hashed(ROOT/name) for name in (
            'scripts/analyze_full_service_v30.py','src/service_terminal_evidence_v30.py',
            'src/run_store.py','src/phase_budget.py')},analysis_cpu_ns=time.process_time_ns()-started)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,default=ROOT/'campaigns/full_service_v30')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = analyze(args.campaign)
    with args.output.open('xb') as stream:
        stream.write(canonical_json(result))
    print(json.dumps({key:result[key] for key in ('status','geometric_mean_cold_over_repair',
        'minimum_cold_over_repair','maximum_cold_over_repair','analysis_cpu_ns')}))
