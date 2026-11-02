"""Fresh one-use CPU registration gated on both completed V54 byte audits."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

from research_v54.campaign import new, read, sha
from research_v55.diagnostic import ARTICLE_IDS, GUARDS, PARITY_TOLERANCE, require, validate_exposed
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.run_store import canonical_json, digest
from src.worker_control import WorkerLimits, run_limited

ROOT = Path(__file__).resolve().parents[1]
CPU_SECONDS, WALL_SECONDS, PHASE_CAP = 14400, 18000, 14402
MEMORY_BYTES = 16*2**30
REGISTRATION_SHA256 = 'bafbbd721435f8f188ddb7a0f834ee6df3f097d62e6189e03023a5828254b95c'
EVALUATOR_SHA256 = 'db1253faa8a7d99fc2edf63405d6efe493e8e1a5783f3b4b1c6d970e88137d0d'
HISTORICAL_LOSSES_SHA256 = 'fa9ddadf0506a4d36378fa32ac4af9bea8b2a543222e0fb6f4458df1cef2fd9b'
EXCLUSIONS_SHA256 = '3a620e938c40d35daed69674f703bcb16840178cc7d9527427650a6e0de28876'


def bind(path):
    path = Path(path).resolve(strict=True)
    require(path.is_file(), 'A bound input must be a file')
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def bound(entry):
    path = Path(entry['path'])
    require(path.is_absolute() and path.is_file() and path.stat().st_size == entry['bytes']
        and sha(path) == entry['sha256'], 'Bound input changed: '+str(path))
    return path


def sources():
    from research_v54.campaign import sources as prior_sources
    result=prior_sources()
    for folder in ('research_v55',):
        for path in sorted((ROOT/folder).iterdir()):
            if path.is_file() and (path.suffix=='.py' or path.name=='PROTOCOL.txt'):
                result[str(path.relative_to(ROOT))]=sha(path)
    for name in ('tests/test_checkpoint_adapter.py','tests/test_transformer_backend.py',
                 'cluster_setup/v55_pipeline.sh'):
        result[name]=sha(ROOT/name)
    return result


from research_v44.campaign import runtime


def check_audits(program, program_hash, first, second, first_hash, model_hash, state_hash):
    """Reject metadata-only or mismatched prerequisite assertions."""
    require(first.get('schema') == 'complete-service-artifact-audit-v54'
        and second.get('schema') == 'complete-service-additive-artifact-audit-v54', 'Both declared V54 audit types are required')
    for audit in (first, second):
        require(audit.get('status') == 'verified' and audit.get('program_sha256') == program_hash
            and audit.get('campaign') == program['directory'], 'V54 audit program/campaign binding differs')
    require(second.get('frozen_audit_sha256') == first_hash, 'Independent audit does not bind the first audit bytes')
    require(first.get('all_declared_artifacts_rehashed') is True and first.get('complete_model') is True
        and first.get('original_tokens') == 1664 and first.get('retained_tokens') == [1536,768], 'V54 audit extent differs')
    expected = {(trial, step) for trial in ('cached','compressed','hybrid','cold') for step in (1,2)}
    for table in (first['comparisons'], second['evidence']['comparisons']):
        require(len(table) == 8 and {(r['trial'],r['step']) for r in table} == expected,
            'Both V54 audits must contain all eight actual comparisons')
        for row in table:
            require(row.get('actual_bytes_equal') is True and row.get('actual_model_bytes_equal') is True
                and row.get('exact_retained_membership_verified') is True
                and row.get('code_count') == 42_467_328 and row.get('stages') == 24,
                'V54 comparison did not prove complete model and canonical state bytes')
        selected = next(r for r in table if (r['trial'],r['step']) == ('compressed',2))
        require(selected['complete_model_sha256'] == model_hash and selected['state_sha256'] == state_hash
            and selected['retained_records'] == 6 and selected['retained_tokens'] == 768,
            'Quality inputs differ from audited V54 final successor')
    require(all(r.get('model_export_matches_state_codes') is True
        and r.get('registered_record_binding_verified') is True
        and r.get('cross_representation_target_and_model_verified') is True
        for r in second['evidence']['comparisons']), 'Independent V54 model/record bindings incomplete')


def dependencies(v54_directory, audit_path, independent_audit_path):
    root = Path(v54_directory).resolve()
    paths = dict(v54_program=root/'program.json', v54_registration=root/'registration.json',
        v54_ledger=root/'budget/ledger.json', first_audit=Path(audit_path), second_audit=Path(independent_audit_path),
        fixed_completion=root/'compressed/outputs/completion.json',
        fixed_state=root/'compressed/outputs/step-2-state.bin', fixed_model=root/'compressed/outputs/step-2-model.bin',
        historical_registration=ROOT/'campaigns/quality_v30/registration.json',
        historical_losses=ROOT/'campaigns/research_v30/attempts/quality-001/outputs/completion.json',
        all_exclusions=ROOT/'campaigns/heldout_quality_v30_exclusions.json',
        checkpoint_config=ROOT/'tmp/models/distilgpt2/config.json',
        checkpoint_weights=ROOT/'tmp/models/distilgpt2/model.safetensors')
    return {name:bind(path) for name,path in paths.items()}


def validate_inputs(inputs):
    paths = {name:bound(entry) for name,entry in inputs.items()}
    p = read(paths['v54_program'])
    require(inputs['v54_program']['sha256']=='03a6181b0d32ad023706145fbde28f202ed5d137e95a4b16ecbd19686858465b','Only the registered V54 program is admitted')
    require(p['schema'] == 'adaptive-compressed48-complete-development-v54'
        and p['normalization'] == 1664 and p['tokens_per_record'] == 128
        and len(p['records']) == 13 and all(len(r['tokens']) == 128 for r in p['records'])
        and p['records'] == sorted(p['records'],key=lambda r:r['id']), 'V54 original target/records differ')
    require(read(paths['v54_registration'])['program_sha256'] == inputs['v54_program']['sha256'], 'V54 registration differs')
    for name, expected in p['sources'].items():
        require(sha(ROOT/name) == expected, 'Frozen V54 source changed: '+name)
    check_audits(p, inputs['v54_program']['sha256'], read(paths['first_audit']),read(paths['second_audit']),
        inputs['first_audit']['sha256'],inputs['fixed_model']['sha256'],inputs['fixed_state']['sha256'])
    ledger = read(paths['v54_ledger'])
    require(len(ledger['attempts']) == 6 and all(r['state']=='settled' for r in ledger['attempts'].values()),
        'V54 must be completely settled before quality registration')
    require(sum(r['charged_cpu_seconds'] for r in ledger['attempts'].values()) <= p['phase_cpu_seconds'], 'V54 CPU cap exceeded')
    completion = read(paths['fixed_completion'])
    require(completion['status'] == 'complete' and completion['complete_model'] is True
        and completion['program_sha256'] == inputs['v54_program']['sha256'], 'Actual fixed model worker incomplete')
    for key, name in (('fixed_model','step-2-model.bin'),('fixed_state','step-2-state.bin')):
        require(all(completion['artifacts'][name][field] == inputs[key][field] for field in ('sha256','bytes')),
            'Actual model/state does not match worker completion')
    require(inputs['historical_registration']['sha256'] == REGISTRATION_SHA256
        and inputs['historical_losses']['sha256'] == HISTORICAL_LOSSES_SHA256
        and inputs['all_exclusions']['sha256'] == EXCLUSIONS_SHA256
        and sha(ROOT/'scripts/run_quality_v30.py') == EVALUATOR_SHA256,
        'Exposed registration, historical losses/exclusions, or shared evaluator changed')
    history = read(paths['historical_losses'])
    records = validate_exposed(read(paths['historical_registration']),history)
    exclusions = read(paths['all_exclusions'])
    require(exclusions.get('schema') == 'quality-confirmation-exclusions-v30'
        and len(set(exclusions['excluded_from_future_confirmation_ids'])) == 60
        and set(ARTICLE_IDS) <= set(exclusions['excluded_from_future_confirmation_ids']),
        'Preserve the complete sixty-article historical exclusion registry')
    from research_v38.bootstrap_target import CHECKPOINT_HASHES
    require(inputs['checkpoint_config']['sha256'] == CHECKPOINT_HASHES['config.json']
        and inputs['checkpoint_weights']['sha256'] == CHECKPOINT_HASHES['model.safetensors'], 'Common checkpoint changed')
    require(read(paths['checkpoint_config'])['activation_function'] == 'gelu_new',
        'This diagnostic requires the pinned NumPy gelu_new activation route')
    return p, records, history


def register(directory, v54_directory, audit_path, independent_audit_path, checks):
    require(os.environ.get('SLURM_JOB_ID'), 'Register only on the actual Slurm CPU runtime')
    directory = Path(directory).resolve()
    require(ROOT in directory.parents and not directory.exists(), 'Use a new repository campaign directory')
    check=read(checks)
    require(check['status']=='passed' and check['skipped']==0 and check['tests']==18 and
        check['sources']==sources() and check['runtime']==runtime(),'Bound passing Linux software checks required')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Clean source required')
    inputs = dependencies(v54_directory,audit_path,independent_audit_path)
    inputs['software_checks']=bind(checks)
    old, records, _ = validate_inputs(inputs)
    program = dict(schema='exposed-quality-diagnostic-v55',directory=str(directory),inputs=inputs,
        registered_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sources=sources(),runtime=runtime(),records=records,retained_records=old['records'][-6:],
        sequential_backend='v43_dispatch_with_v50_normal_neighbors',
        normalization=1664,ridge=[1,100],bits=4,significant_bits=24,
        guards=GUARDS,parity_absolute_mean_nll_tolerance=PARITY_TOLERANCE,
        quality_order='all full_precision/nearest controls first; verify all16 old losses; then alternating fixed/sequential per article',
        worker_cpu_seconds=CPU_SECONDS,worker_wall_seconds=WALL_SECONDS,phase_cpu_seconds=PHASE_CAP,
        process_address_space_bytes=MEMORY_BYTES,file_size_bytes=2*2**30,threads=1,
        registration_job=os.environ['SLURM_JOB_ID'],automatic_retry=False,confirmation=False,acl_ready=False,
        new_evaluation_inputs=False,intervals=False,gpu_execution=False,
        evaluator='Unchanged shared ordinary NumPy binary64; not certified finite inference',
        scope='Final retained768/norm1664 V54 model; eight already exposed V30 development articles; no confirmatory or ACL-readiness claim')
    directory.mkdir(parents=True)
    new(directory/'program.json',program)
    new(directory/'registration.json',dict(program_sha256=sha(directory/'program.json')))
    budget(program)
    print(canonical_json(dict(status='registered',program=str(directory/'program.json'))).decode())
    return program


def verify(directory):
    directory = Path(directory).resolve()
    p = read(directory/'program.json')
    require(p['schema']=='exposed-quality-diagnostic-v55' and p['directory']==str(directory), 'V55 program identity differs')
    require(read(directory/'registration.json')['program_sha256']==sha(directory/'program.json'), 'V55 registration changed')
    require(p['sources']==sources() and p['runtime']==runtime(), 'Registered quality source/runtime changed')
    old,records,_=validate_inputs(p['inputs'])
    require(p['records']==records and p['retained_records']==old['records'][-6:] and p['normalization']==1664
        and p['sequential_backend']=='v43_dispatch_with_v50_normal_neighbors'
        and p['guards']==GUARDS and p['parity_absolute_mean_nll_tolerance']==PARITY_TOLERANCE
        and (p['worker_cpu_seconds'],p['worker_wall_seconds'],p['phase_cpu_seconds'])==(CPU_SECONDS,WALL_SECONDS,PHASE_CAP)
        and p['process_address_space_bytes']==MEMORY_BYTES and p['file_size_bytes']==2*2**30 and p['threads']==1
        and p['confirmation'] is False and p['acl_ready'] is False and p['automatic_retry'] is False, 'Frozen diagnostic design differs')
    return p


def budget(p):
    return PhaseBudget(Path(p['directory'])/'budget',identity=dict(
        protocol_sha256=sha(Path(p['directory'])/'program.json'),source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'development':PHASE_CAP})


def run(directory):
    require(os.environ.get('SLURM_JOB_ID'), 'Empirical diagnostic requires Slurm')
    p=verify(directory)
    attempt=Path(p['directory'])/'quality'
    require(not attempt.exists(), 'One-use diagnostic already attempted; no automatic retry')
    attempt.mkdir()
    plan=dict(program=str(Path(p['directory'])/'program.json'),program_sha256=sha(Path(p['directory'])/'program.json'),
        output=str(attempt/'outputs'),slurm_job_id=os.environ['SLURM_JOB_ID'])
    new(attempt/'plan.json',plan)
    limits=WorkerLimits(cpu_seconds=CPU_SECONDS,wall_seconds=WALL_SECONDS,address_space_bytes=MEMORY_BYTES,
        threads=1,affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=p['file_size_bytes'])
    start=time.perf_counter_ns()
    receipt=run_limited([sys.executable,'-B','-m','research_v55.worker',str(attempt/'plan.json')],attempt/'worker',
        limits,identity=dict(program_sha256=plan['program_sha256']),cwd=ROOT,phase_budget=budget(p),phase='development')
    new(attempt/'transaction.json',dict(worker_outcome=receipt['outcome'],elapsed_ns=time.perf_counter_ns()-start,
        budget=budget(p).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(canonical_json(receipt['outcome']).decode(),flush=True)
    return receipt['outcome']['status']


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='operation',required=True)
    reg=sub.add_parser('register')
    for name in ('directory','v54_directory','audit_path','independent_audit_path','checks'):
        reg.add_argument(name)
    launch=sub.add_parser('run');launch.add_argument('directory')
    args=parser.parse_args()
    if args.operation=='register':
        register(args.directory,args.v54_directory,args.audit_path,args.independent_audit_path,args.checks)
    elif run(args.directory)!='complete':
        raise SystemExit(1)
