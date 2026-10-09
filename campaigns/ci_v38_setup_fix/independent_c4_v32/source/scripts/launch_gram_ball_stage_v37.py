"""Registered adaptive full-stage control using the shared RN ball row verifier."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.execute_gram_ball_stage_v37 import (admission,bind_inputs,current_sources,hashed,new_file,require,verify_inputs,scientific_refusal)
from src.phase_budget import PhaseBudget
from src.pilot_budget import research_worker_lock
from src.run_store import canonical_json,digest
from src.runtime_contract import capture_runtime_contract
from src.worker_control import WorkerLimits,run_limited

DEFAULT='campaigns/pooled_gram_ball_stage_v37'
ARM_ORDER=['pooled_gram_prepare','pooled_gram_delete','retained_gram_cold','retained_cached_token']

def directory(value):
    p=Path(value)
    if not p.is_absolute():p=ROOT/p
    require(not p.is_symlink() and not any(x.is_symlink() for x in p.parents),'unsafe campaign path')
    return p

def historical_ledgers(campaign):
    return {str(p.relative_to(ROOT)):hashed(p) for base in ('campaigns','pilots','local_runs')
        for p in sorted((ROOT/base).glob('**/phase-cpu-budget/ledger.json')) if campaign not in p.parents}

def register(path,capsule):
    require(not path.exists(),'campaign already exists; no overwrite or retry')
    inputs=bind_inputs(capsule)
    start=time.perf_counter_ns();assessment=admission(inputs);audit_ns=time.perf_counter_ns()-start
    limits=WorkerLimits(wall_seconds=1100,cpu_seconds=880,address_space_bytes=3*2**30,
        threads=1,affinity_cpus=(min(os.sched_getaffinity(0)),))
    limits.check_host()
    program=dict(schema='archive-gram-ball-stage-program-v37',inputs=inputs,source_sha256=current_sources(),runtime=capture_runtime_contract(),
        phase_cpu_seconds={'gram_ball_stage':900},limits=limits.payload(),arm_order=ARM_ORDER,
        stage='block.0000.qkv',rows=list(range(2304)),width=768,original_token_count=256,retained_token_count=128,
        bits=4,ridge=[1,100],normalization=256,confirmation=False,component_only=True,
        admission=assessment,admission_analysis_elapsed_ns=audit_ns,admission_cpu_not_worker_ledger=True,
        historical_ledgers_sha256=historical_ledgers(path),historical_ledger_scope='Every bound prior ledger must remain unchanged; additional future ledgers are permitted. This is not global ledger completeness.',
        runtime_scope='New archive-algebra runtime. Original neural feature generation is trusted historical provenance; never reexecuted or newly attested.',
        failure_policy='One attempt only. Declared bounded certificate refusals produce no codes and continue independent arms. Integrity, runtime, allocation, compiler, resource or execution failures stop. Preserve every outcome; never autoretry or replace samples.',
        success_gate='All exact Gram bytes agree; all 1769472 row codes agree with archived target in three arms. No latency threshold. Certificate refusal is an observed scientific gate failure, not a completed reconstruction; no refusal-time speed ratio is defined.',
        expansion_policy='No automatic expansion. A new registered full-service design must include deleted neural replay and canonical state contracts.',
        timing_policy='Fixed order; one observation per arm; uncontrolled OS caches. Native compilation before all arms, charged separately. Common verification/archive parse/weight load separate. Each arm decodes its required descriptor anew. All Gram formation, parsing, subtraction, serialization, solver certification, code verification, diagnostic dataclass serialization and output writes charged in its arm. V35 placed diagnostic serialization outside arm totals; cross-version times have that scope difference.',
        unavailable_claims=['complete-model speedup','neural feature-generation revalidation','lifetime benefit','population inference','prospective confirmation'],
        adaptive_design='Selected after V36 showed high interval-row cost. Reuses unchanged exact Gram coefficients and the same RN ball row backend available to the cached-feature control. Refused ball rows receive the existing interval verifier with shared coefficients; all fallback work is charged. Same existing stage and deletion; no independent confirmation.',
        statistical_scope='One fixed-order adaptive development observation. No population inference or generalized superiority claim; descriptive within-run ratios only for completed arms; no new independent deletion.')
    path.mkdir(parents=True)
    new_file(path/'program.json',canonical_json(program))
    new_file(path/'registration.json',canonical_json(dict(schema='archive-gram-ball-stage-registration-v37',program_sha256=hashed(path/'program.json'),registered_before_empirical_gram=True)))
    PhaseBudget(path/'phase-cpu-budget',identity={'program_sha256':hashed(path/'program.json')},phase_cpu_seconds=program['phase_cpu_seconds'])
    return dict(status='registered',program_sha256=hashed(path/'program.json'),campaign=str(path),admission=assessment)

def verified_program(path):
    program=json.loads((path/'program.json').read_bytes());registration=json.loads((path/'registration.json').read_bytes())
    require(registration['program_sha256']==hashed(path/'program.json'),'registration differs')
    require(program['source_sha256']==current_sources(),'registered source changed')
    require(program['runtime']==capture_runtime_contract(),'registered software runtime changed')
    current_ledgers=historical_ledgers(path)
    require(all(current_ledgers.get(name)==sha for name,sha in program['historical_ledgers_sha256'].items()),'bound historical ledger changed')
    verify_inputs(program['inputs'])
    return program

def verify_terminal(path,program):
    attempt=path/'attempt';receipt_path=attempt/'worker/result.json'
    plan=json.loads((attempt/'plan.json').read_bytes())
    expected_plan=dict(schema='archive-gram-ball-stage-plan-v37',program_sha256=hashed(path/'program.json'),inputs=program['inputs'],source_sha256=program['source_sha256'],runtime=program['runtime'],arm_order=program['arm_order'],output=str(attempt/'outputs'))
    require(plan==expected_plan,'attempt plan differs from registered program')
    receipt=json.loads(receipt_path.read_bytes());tx=json.loads((attempt/'transaction.json').read_bytes())
    require(tx['receipt_sha256']==hashed(receipt_path) and tx['worker_outcome']==receipt['outcome'],'transaction receipt differs')
    require(receipt['status']=='complete' and receipt['outcome']['status']=='complete' and receipt['outcome']['returncode']==0,'worker failed')
    raw=(attempt/'outputs/completion.json').read_bytes()
    require(raw==(attempt/'sealed-completion.json').read_bytes(),'sealed terminal copy differs')
    terminal=json.loads(raw)
    require(terminal['status']=='complete' and terminal['plan_sha256']==hashed(attempt/'plan.json'),'terminal identity differs')
    inner=attempt/'worker'/receipt['attempt'];stdout=json.loads((inner/'stdout-summary.json').read_bytes())
    marker='GRAM_BALL_STAGE_TERMINAL_SHA256='+digest(raw)
    require(stdout['tail_utf8'].splitlines().count(marker)==1,'terminal stdout digest absent or duplicated')
    identity=json.loads((attempt/'worker/identity.json').read_bytes())
    require(receipt['identity_sha256']==digest(canonical_json(identity)),'worker identity differs')
    require(receipt['worker_identity']=={'plan_sha256':hashed(attempt/'plan.json'),'program_sha256':hashed(path/'program.json')},'worker plan differs')
    expected_command=[str(Path(sys.executable).absolute()),str(ROOT/'scripts/execute_gram_ball_stage_v37.py'),str(attempt/'plan.json')]
    require(identity['command']==expected_command and identity['cwd']==str(ROOT) and identity['limits']==program['limits'],'worker command, cwd, or limits differ')
    request=json.loads((inner/'request.json').read_bytes())
    for key in ('command','cwd','limits'):require(request[key]==identity[key],'request identity differs')
    for name,entry in receipt['artifacts'].items():
        require(Path(name).name==name,'unsafe receipt artifact')
        artifact=inner/name
        require(hashed(artifact)==entry['sha256'] and artifact.stat().st_size==entry['bytes'],'receipt artifact changed')
    for name,entry in terminal['artifacts'].items():
        require(Path(name).name==name,'unsafe output artifact')
        artifact=attempt/'outputs'/name
        require(hashed(artifact)==entry['sha256'] and artifact.stat().st_size==entry['bytes'],'output changed')
    debit=receipt['budget_debit'];cpu=debit['observed_cpu_ns']
    require(debit['state']=='settled' and type(cpu)is int and cpu>=0 and debit['charged_cpu_seconds']==max(1,(cpu+999_999_999)//1_000_000_000),'invalid CPU debit')
    ledger=PhaseBudget(path/'phase-cpu-budget',identity={'program_sha256':hashed(path/'program.json')},phase_cpu_seconds=program['phase_cpu_seconds']).snapshot()
    require(ledger['attempts']=={receipt['budget_attempt_id']:debit},'unexpected phase attempt or debit')
    require(terminal['exact_gram_equality'],'exact Gram equality failure')
    from research_v36.archive_stage_capsule import capsule_files
    from research_v35.direct_gram import DirectGramUnresolved
    from research_v37.direct_gram_ball import DirectGramBallUnresolved
    from src.low_rank_certified import LowRankUnresolved
    manifest,_=capsule_files(program['inputs']['capsule']['path'],program['inputs']['capsule']['sha256'])
    reference_sha256=manifest['payloads']['reference_indices']['raw_sha256']
    require(terminal['arm_order']==ARM_ORDER and set(terminal['arm_outcomes'])=={'delete','cold','cache'},'component arm membership or order differs')
    certified=[]
    for key,row in terminal['arm_outcomes'].items():
        require(row['status'] in ('certified','scientific_refusal'),'unstarted or incomplete registered arm')
        artifact=attempt/'outputs'/(key+'-codes.bin')
        if row['status']=='certified':
            require(row['codes_committed'] and terminal[key+'_codes']['codes']==1769472,'complete stage code count differs')
            require(hashed(artifact)==reference_sha256,'certified artifact differs from archived full-stage reference')
            certified.append(artifact.read_bytes())
        else:
            require(not row['codes_committed'] and not artifact.exists() and key+'_codes' not in terminal,'refused arm committed partial codes')
            classes={'DirectGramUnresolved':DirectGramUnresolved,'DirectGramBallUnresolved':DirectGramBallUnresolved,'LowRankUnresolved':LowRankUnresolved}
            require(row['error_type'] in classes and scientific_refusal(classes[row['error_type']](row['error'])),'terminal refusal does not satisfy registered narrow classification')
    all_certified=len(certified)==3
    require(terminal['scientific_gate_passed']==all_certified and terminal['all_three_code_arrays_equal']==(True if all_certified else None),'scientific gate classification differs')
    require(all(raw==certified[0] for raw in certified),'actual certified code artifacts disagree')
    require((attempt/'outputs/retained-gram.bin').read_bytes()==(attempt/'outputs/cold-retained-gram.bin').read_bytes(),'actual Gram artifacts disagree')
    return dict(status='complete',program_sha256=hashed(path/'program.json'),terminal_sha256=digest(raw),
        charged_cpu_seconds=debit['charged_cpu_seconds'],timings_ns=terminal['timings_ns'],arm_outcomes=terminal['arm_outcomes'],scientific_gate_passed=terminal['scientific_gate_passed'],component_only=True)

def execute(path):
    with research_worker_lock(ROOT):
        program=verified_program(path);attempt=path/'attempt'
        require(not attempt.exists(),'attempt exists; no retry; use --status')
        attempt.mkdir()
        plan=dict(schema='archive-gram-ball-stage-plan-v37',program_sha256=hashed(path/'program.json'),inputs=program['inputs'],
            source_sha256=program['source_sha256'],runtime=program['runtime'],arm_order=program['arm_order'],output=str(attempt/'outputs'))
        new_file(attempt/'plan.json',canonical_json(plan))
        budget=PhaseBudget(path/'phase-cpu-budget',identity={'program_sha256':hashed(path/'program.json')},phase_cpu_seconds=program['phase_cpu_seconds'])
        command=[str(Path(sys.executable).absolute()),str(ROOT/'scripts/execute_gram_ball_stage_v37.py'),str(attempt/'plan.json')]
        tick=time.perf_counter_ns()
        receipt=run_limited(command,attempt/'worker',WorkerLimits.from_payload(program['limits']),
            identity={'program_sha256':hashed(path/'program.json'),'plan_sha256':hashed(attempt/'plan.json')},cwd=ROOT,phase_budget=budget,phase='gram_ball_stage')
        elapsed=time.perf_counter_ns()-tick
        new_file(attempt/'transaction.json',canonical_json(dict(schema='archive-gram-ball-stage-transaction-v37',receipt_sha256=hashed(attempt/'worker/result.json'),
            worker_outcome=receipt['outcome'],controller_elapsed_ns=elapsed,budget=budget.snapshot())))
        require(receipt['outcome']['status']=='complete','worker failed; preserve evidence and do not retry')
        new_file(attempt/'sealed-completion.json',(attempt/'outputs/completion.json').read_bytes())
        report=verify_terminal(path,program);new_file(path/'analysis.json',canonical_json(report));return report

def status(path):
    if not path.exists():return dict(status='unregistered',campaign=str(path))
    program=verified_program(path)
    if not (path/'attempt').exists():return dict(status='registered_unstarted',program_sha256=hashed(path/'program.json'))
    if not (path/'attempt/sealed-completion.json').exists():return dict(status='blocked_incomplete_or_failed_attempt',automatic_retry=False)
    return verify_terminal(path,program)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--campaign',default=DEFAULT);p.add_argument('--capsule',default='data/gram_v36/wikitext-firststage/manifest.json')
    action=p.add_mutually_exclusive_group();action.add_argument('--register',action='store_true');action.add_argument('--execute',action='store_true');action.add_argument('--status',action='store_true')
    a=p.parse_args();campaign=directory(a.campaign)
    result=register(campaign,directory(a.capsule)) if a.register else execute(campaign) if a.execute else status(campaign)
    print(json.dumps(result,sort_keys=True),flush=True)
