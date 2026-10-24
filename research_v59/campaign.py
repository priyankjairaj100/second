"""One new fixed-full-precision-anchor screen; historical experiments stay frozen."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

from research_v55 import campaign as prior
from research_v55.diagnostic import check_result
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.run_store import canonical_json
from src.worker_control import WorkerLimits, run_limited

ROOT = Path(__file__).resolve().parents[1]
new, read, sha, bind, bound, require = prior.new, prior.read, prior.sha, prior.bind, prior.bound, prior.require
runtime = prior.runtime
GUARDS = dict(max_pooled_candidate_over_sequential=1.05, max_article_candidate_over_sequential=1.20)
PARITY_TOLERANCE = prior.PARITY_TOLERANCE
CPU_SECONDS, WALL_SECONDS, PHASE_CAP = 14400, 18000, 14402
MEMORY_BYTES = 16*2**30
V55_PROGRAM = '4de04c4a0bd5db485c7ccd7511a4d5094195afdce15c115a909346879b84125f'
V55_COMPLETION = '1c35aa42d570e51d17f800e538bf6118ccf4a0ede85d0903ddc1ed3c2689b135'
V55_AUDIT = 'fa4a762a2ca6389968a503c0e224d1bd3f0d1bf0bb0aedb7acd24dd9d251b042'
FIRST_STAGE_SHA256 = 'f397e6c54c44b3143921c67d49bc16bb39d7587ff66dcd740a4edcd5363863a0'
LEGACY_KEYS = dict(v54_program='v54_program', v54_registration='v54_registration',
    v54_ledger='v54_ledger', v54_audit='first_audit', v54_independent_audit='second_audit',
    v54_completion='fixed_completion', v54_state='fixed_state', v54_model='fixed_model',
    historical_registration='historical_registration', historical_losses='historical_losses',
    historical_exclusions='all_exclusions', checkpoint_config='checkpoint_config',
    checkpoint_weights='checkpoint_weights')
ARTIFACT_INPUTS = dict(v55_sequential_model='sequential-model.bin',
    v55_sequential_metadata='sequential-model-metadata.json',
    v55_sequential_target='sequential-target.json', v55_fixed_target='fixed-target.json',
    v55_sequential_diagnostics='sequential-diagnostics.json',
    v55_execution_provenance='execution-provenance.json')


def sources():
    result = prior.sources()
    for path in sorted((ROOT/'research_v59').iterdir()):
        if path.is_file() and (path.suffix == '.py' or path.name == 'PROTOCOL.txt'):
            result[str(path.relative_to(ROOT))] = sha(path)
    result['cluster_setup/v59_pipeline.sh'] = sha(ROOT/'cluster_setup/v59_pipeline.sh')
    return result


def dependencies(v55_directory):
    root = Path(v55_directory).resolve(strict=True)
    program = read(root/'program.json')
    require(sha(root/'program.json') == V55_PROGRAM, 'Only the completed V55 root is admitted')
    result = {key:bind(bound(program['inputs'][old])) for key,old in LEGACY_KEYS.items()}
    paths = dict(v55_program=root/'program.json', v55_registration=root/'registration.json',
        v55_completion=root/'quality/outputs/completion.json', v55_audit=root/'artifact-audit.json',
        v55_ledger=root/'budget/ledger.json')
    paths.update({key:root/'quality/outputs'/name for key,name in ARTIFACT_INPUTS.items()})
    result.update({key:bind(path) for key,path in paths.items()})
    return result


def check_prior(program, completion, audit, program_hash):
    """A valid adverse outcome is the fixed starting point, never a pass prerequisite."""
    require(program_hash == V55_PROGRAM and program['schema'] == 'exposed-quality-diagnostic-v55',
        'Pinned V55 program required')
    require(completion['schema'] == 'exposed-quality-worker-v55' and completion['status'] == 'complete'
        and completion['valid_diagnostic'] is True and completion['program_sha256'] == program_hash
        and completion['original_normalization'] == 1664 and completion['retained_calibration_tokens'] == 768
        and completion['code_count'] == 42_467_328, 'Complete V55 quality result required')
    require(audit['schema'] == 'exposed-quality-artifact-audit-v55' and audit['status'] == 'verified'
        and audit['program_sha256'] == program_hash and audit['campaign'] == program['directory']
        and audit['actual_model_codes_reconstructed'] == 42_467_328 and audit['complete_stages'] == 24
        and audit['sealed_cpu_receipt_verified'] is True, 'Actual complete V55 artifact audit required')
    require(completion['summary'] == audit['summary'] and completion['development_guards_pass'] is False
        and audit['development_guards_pass'] is False, 'Preserve the frozen adverse V55 quality finding')


def validate_inputs(inputs):
    expected = set(LEGACY_KEYS) | set(ARTIFACT_INPUTS) | {
        'v55_program','v55_registration','v55_completion','v55_audit','v55_ledger','software_checks'}
    require(set(inputs) == expected, 'Complete explicit V59 input inventory required')
    paths = {name:bound(entry) for name,entry in inputs.items()}
    require(inputs['v55_program']['sha256'] == V55_PROGRAM
        and inputs['v55_completion']['sha256'] == V55_COMPLETION
        and inputs['v55_audit']['sha256'] == V55_AUDIT, 'Frozen V55 receipts changed')
    p,c,a = (read(paths[key]) for key in ('v55_program','v55_completion','v55_audit'))
    require(read(paths['v55_registration'])['program_sha256'] == V55_PROGRAM,
        'V55 registration differs')
    check_prior(p,c,a,V55_PROGRAM)
    require(p['sources'] == prior.sources(), 'A frozen V55 numerical source changed')
    # Reuse the frozen validator on its exact old keys. This verifies both V54
    # audits, actual model/state hashes, original root, checkpoint, and exclusions.
    inherited = {old:inputs[key] for key,old in LEGACY_KEYS.items()}
    for old,entry in inherited.items():
        require(entry == p['inputs'][old], 'V55 input binding changed: '+old)
    old,records,history = prior.validate_inputs(inherited)
    require(p['records'] == records and p['retained_records'] == old['records'][-6:]
        and p['normalization'] == 1664 and p['guards'] == prior.GUARDS
        and p['parity_absolute_mean_nll_tolerance'] == PARITY_TOLERANCE, 'V55 design differs')
    summary = check_result(c,history,c['historical_parity'])
    require(summary == a['summary'], 'V55 recorded losses do not reproduce audited summary')
    for key,name in ARTIFACT_INPUTS.items():
        entry = c['artifacts'][name]
        require(all(entry[f] == inputs[key][f] for f in ('sha256','bytes')),
            'Frozen sequential target/model artifact differs: '+key)
    for key in ('v55_completion','v55_ledger',*ARTIFACT_INPUTS,'v54_model','v54_state'):
        entry = inputs[key]
        require(a['inputs'][str(paths[key])] == {f:entry[f] for f in ('sha256','bytes')},
            'V55 audit does not bind current actual input: '+key)
    ledger = read(paths['v55_ledger'])
    require(len(ledger['attempts']) == 1 and all(r['state'] == 'settled' for r in ledger['attempts'].values())
        and sum(r['charged_cpu_seconds'] for r in ledger['attempts'].values()) <= p['phase_cpu_seconds'],
        'V55 must remain settled within its own budget')
    meta = read(paths['v55_sequential_metadata'])
    require(len(meta['stages']) == 24 and meta['stages'][0]['sha256'] == FIRST_STAGE_SHA256,
        'Frozen first-stage invariant differs')
    return p, records, c


def design():
    """Every prospective numeric/scope choice compared again before dispatch."""
    return dict(candidate='one fixed full-precision checkpoint anchor; no calibrated prefix',
        backend='v43_dispatch_with_v50_normal_neighbors', normalization=1664, ridge=[1,100],
        bits=4, significant_bits=24, guards=GUARDS, parity_absolute_mean_nll_tolerance=PARITY_TOLERANCE,
        first_stage_packed_sha256=FIRST_STAGE_SHA256, controls=['full_precision','nearest_rounding','fixed_feature','sequential'],
        quality_order='full_precision, nearest_rounding, fixed_feature, sequential: eight articles each; verify all32; construct one candidate; eight candidate losses',
        worker_cpu_seconds=CPU_SECONDS, worker_wall_seconds=WALL_SECONDS, phase_cpu_seconds=PHASE_CAP,
        process_address_space_bytes=MEMORY_BYTES, file_size_bytes=2*2**30, threads=1,
        stage_array_cap_bytes=8*2**30, stage_work_cap=64_000_000_000, request_work_cap=1_000_000_000_000,
        declared_other_residency_bytes=4*2**30, automatic_retry=False, confirmation=False, acl_ready=False,
        new_evaluation_inputs=False, intervals=False, gpu_execution=False, repair_service=False,
        feature_drift_traversals=False, candidate_count=1, teacher_stage_record_advances=144,
        quality_evaluations=40,
        evaluator='Unchanged shared ordinary NumPy binary64; not certified finite inference',
        scope='Exposed development screen after the failed V55 nearest-anchor result; no held-out or service-performance claim')


def check_software(check, current_sources, current_runtime):
    from research_v59.checks import MODULES, EXPECTED_TESTS
    require(check['status'] == 'passed' and check['skipped'] == 0 and check['tests'] == EXPECTED_TESTS
        and check['modules'] == list(MODULES) and check['sources'] == current_sources
        and check['runtime'] == current_runtime and check['real_model_inference'] is False,
        'Complete passing source/runtime-bound Linux software checks required')


def register(directory, v55_directory, checks):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform == 'linux', 'Register only on pinned Linux Slurm')
    directory = Path(directory).resolve()
    require(ROOT in directory.parents and not directory.exists(), 'Fresh repository campaign path required')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),
        'Clean committed source required')
    s,r = sources(),runtime()
    check_software(read(checks),s,r)
    inputs = dependencies(v55_directory)
    inputs['software_checks'] = bind(checks)
    previous,records,_ = validate_inputs(inputs)
    require(r == previous['runtime'], 'Use the same pinned numerical runtime as V55')
    program = dict(schema='full-precision-anchor-quality-diagnostic-v59', directory=str(directory),
        registered_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sources=s, runtime=r, inputs=inputs, records=records, retained_records=previous['retained_records'],
        registration_job=os.environ['SLURM_JOB_ID'], **design())
    directory.mkdir(parents=True)
    new(directory/'program.json',program)
    new(directory/'registration.json',dict(program_sha256=sha(directory/'program.json')))
    budget(program)
    print(canonical_json(dict(status='registered',program=str(directory/'program.json'))).decode())
    return program


def verify(directory):
    directory = Path(directory).resolve()
    p,reg = read(directory/'program.json'),read(directory/'registration.json')
    require(p['schema'] == 'full-precision-anchor-quality-diagnostic-v59' and p['directory'] == str(directory)
        and reg['program_sha256'] == sha(directory/'program.json'), 'V59 registration differs')
    require(p['sources'] == sources() and p['runtime'] == runtime(), 'Registered source/runtime changed')
    previous,records,completion = validate_inputs(p['inputs'])
    require(p['runtime'] == previous['runtime'] and p['records'] == records
        and p['retained_records'] == previous['retained_records']
        and all(p.get(k) == v for k,v in design().items()), 'Frozen V59 design differs')
    check_software(read(bound(p['inputs']['software_checks'])),p['sources'],p['runtime'])
    return p,reg,previous,records,completion


def budget(program):
    # The protocol digest covers the complete V59 source inventory; the generic
    # dispatcher subset is additionally bound, without modifying frozen helpers.
    return PhaseBudget(Path(program['directory'])/'budget', identity=dict(
        protocol_sha256=sha(Path(program['directory'])/'program.json'), source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'development':PHASE_CAP})


def run(directory):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform == 'linux', 'Empirical worker requires Linux Slurm')
    p,*_ = verify(directory)
    attempt = Path(p['directory'])/'quality'
    require(not attempt.exists(), 'One-use V59 attempt already exists; no retry')
    attempt.mkdir()
    plan = dict(schema='full-precision-anchor-quality-plan-v59', directory=p['directory'],
        program=str(Path(p['directory'])/'program.json'), program_sha256=sha(Path(p['directory'])/'program.json'),
        output=str(attempt/'outputs'), slurm_job_id=os.environ['SLURM_JOB_ID'])
    new(attempt/'plan.json',plan)
    limits = WorkerLimits(cpu_seconds=CPU_SECONDS, wall_seconds=WALL_SECONDS,
        address_space_bytes=MEMORY_BYTES, threads=1, affinity_cpus=(min(os.sched_getaffinity(0)),),
        file_size_bytes=p['file_size_bytes'])
    start = time.perf_counter_ns()
    receipt = run_limited([sys.executable,'-B','-m','research_v59.worker',str(attempt/'plan.json')],
        attempt/'worker',limits, identity=dict(program_sha256=plan['program_sha256']),
        cwd=ROOT,phase_budget=budget(p),phase='development')
    new(attempt/'transaction.json',dict(worker_outcome=receipt['outcome'],elapsed_ns=time.perf_counter_ns()-start,
        budget=budget(p).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(canonical_json(receipt['outcome']).decode(),flush=True)
    return receipt['outcome']['status']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='operation',required=True)
    reg = commands.add_parser('register')
    for name in ('directory','v55_directory','checks'): reg.add_argument(name)
    run_parser = commands.add_parser('run'); run_parser.add_argument('directory')
    args = parser.parse_args()
    if args.operation == 'register': register(args.directory,args.v55_directory,args.checks)
    elif run(args.directory) != 'complete': raise SystemExit(1)
