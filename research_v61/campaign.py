"""One-use full-precision teacher service; historical evidence stays immutable."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

from research_v59 import campaign as prior
from research_v59.diagnostic import check_result
from research_v54.campaign import validate_data
from research_v54.archive import history_delta
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget, read_budget_snapshot
from src.run_store import canonical_json, digest, read_completed
from src.worker_control import WorkerLimits, run_limited

ROOT = Path(__file__).resolve().parents[1]
new, read, sha, require, runtime = prior.new, prior.read, prior.sha, prior.require, prior.runtime
TRIALS = dict(prepare=dict(cpu_seconds=10800,wall_seconds=14400),
    cached=dict(cpu_seconds=10800,wall_seconds=14400), compressed=dict(cpu_seconds=18000,wall_seconds=21600),
    hybrid=dict(cpu_seconds=14400,wall_seconds=18000), cold=dict(cpu_seconds=12600,wall_seconds=16200),
    oracle=dict(cpu_seconds=14400,wall_seconds=18000))
CAP = sum(v['cpu_seconds']+2 for v in TRIALS.values())
ARM_ORDER = sorted(('cached','compressed','hybrid','cold'),key=lambda name:digest(('second-v53-arm-order:'+name).encode()))
ORDER = ['prepare',*ARM_ORDER,'oracle']
CAMPAIGN_NAME = 'full-precision-service-v61-20261014-a'
V59_PROGRAM = '4a22292c903b4817629bd43449dcf6f22c827f7c31c9e525fcb3fdcca448e835'
V59_COMPLETION = '2c80712913d314aa88d5abede08f324e8a773b9ffb847b58a9b721e7301c731c'
V59_AUDIT = '286a2c74b676e55ff4d463d31545ca8138eb7dce36e515112fb697575a89f6e6'
V59_MODEL = '904d2dc59a22b28d74db20b388bc1acc5d7566150441d65a7318a5d896271192'
V59_TARGET = '3853008973e0a89db5c80d73d30cb4304bc5d9c89fafa80e6f7f15de232a1245'
V54_PROGRAM = '03a6181b0d32ad023706145fbde28f202ed5d137e95a4b16ecbd19686858465b'
V59_ARTIFACTS = dict(v59_candidate_model='candidate-model.bin',v59_candidate_metadata='candidate-model-metadata.json',
    v59_candidate_target='candidate-target.json',v59_candidate_diagnostics='candidate-diagnostics.json',
    v59_first_stage='first-stage-invariant.json',v59_base_target='sequential-target.json',
    v59_execution='execution-provenance.json',v59_historical_parity='historical-parity.json',
    v59_fixed_target='fixed-target.json')
DATA_KEYS = ('data_program','data_completion','data_selection','data_records','data_ledger','data_exclusions')


def bind(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path,*path.parents)) and path.is_file(), 'Regular nonsymbolic bound input required')
    return dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)


def bound(entry):
    path = Path(entry['path'])
    require(path.is_absolute() and not any(p.is_symlink() for p in (path,*path.parents)) and path.is_file()
        and path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], 'Bound input changed: '+str(path))
    return path


def sources():
    result = prior.sources()
    require(len(result) == 412, 'Frozen V59 source inventory changed')
    for path in sorted((ROOT/'research_v61').iterdir()):
        if path.is_file() and (path.suffix == '.py' or path.name == 'PROTOCOL.txt'):
            result[str(path.relative_to(ROOT))] = sha(path)
    result['cluster_setup/v61_pipeline.sh'] = sha(ROOT/'cluster_setup/v61_pipeline.sh')
    return result


def dependencies(v59_directory):
    directory = Path(v59_directory).resolve(strict=True)
    p = read(directory/'program.json')
    require(sha(directory/'program.json') == V59_PROGRAM, 'Only the passed frozen V59 campaign is admitted')
    result = {('v59_software_checks' if key == 'software_checks' else key): bind(bound(entry))
              for key,entry in p['inputs'].items()}
    paths = dict(v59_program=directory/'program.json',v59_registration=directory/'registration.json',
        v59_completion=directory/'quality/outputs/completion.json',v59_audit=directory/'artifact-audit.json',
        v59_ledger=directory/'budget/ledger.json')
    paths.update({key:directory/'quality/outputs'/name for key,name in V59_ARTIFACTS.items()})
    v54 = read(bound(result['v54_program']))
    paths.update({key:bound(v54['inputs'][key]) for key in DATA_KEYS})
    result.update({key:bind(path) for key,path in paths.items()})
    return result


def check_prior(p,c,a,inputs):
    """Require the exact passed screen, not a newly selected favorable result."""
    for key,expected in (('v59_program',V59_PROGRAM),('v59_completion',V59_COMPLETION),
                         ('v59_audit',V59_AUDIT),('v59_candidate_model',V59_MODEL),('v59_candidate_target',V59_TARGET)):
        require(inputs[key]['sha256'] == expected, 'Frozen V59 receipt/artifact changed: '+key)
    require(p['schema'] == 'full-precision-anchor-quality-diagnostic-v59'
        and c['schema'] == 'full-precision-anchor-quality-worker-v59' and c['status'] == 'complete'
        and c['valid_diagnostic'] is True and c['program_sha256'] == V59_PROGRAM
        and c['development_guards_pass'] is True and c['candidate_count'] == 1
        and c['code_count'] == 42_467_328 and c['retained_calibration_tokens'] == 768,
        'Complete passed V59 screen required')
    require(a['schema'] == 'full-precision-anchor-quality-artifact-audit-v59' and a['status'] == 'verified'
        and a['program_sha256'] == V59_PROGRAM and a['campaign'] == p['directory']
        and a['summary'] == c['summary'] and a['development_guards_pass'] is True
        and a['checked_losses'] == 40 and a['complete_stages'] == 24
        and a['actual_model_codes_reconstructed'] == 42_467_328 and a['sealed_cpu_receipt_verified'] is True
        and a['actual_candidate_model_sha256'] == V59_MODEL and a['candidate_target_sha256'] == V59_TARGET,
        'Actual V59 terminal artifact audit required')
    for key,name in V59_ARTIFACTS.items():
        require(c['artifacts'][name] == dict(file=name,**{f:inputs[key][f] for f in ('sha256','bytes')}),
            'V59 completion artifact binding differs: '+key)
    for key in ('v59_program','v59_registration','v59_completion','v59_ledger',*V59_ARTIFACTS):
        entry=inputs[key]
        require(a['inputs'][entry['path']] == {f:entry[f] for f in ('bytes','sha256')}, 'V59 audit input binding differs: '+key)


def validate_inputs(inputs):
    # Reuse frozen validators read-only: metadata arithmetic and actual hash
    # checks only; never rerun a sampler, decoder, calibrator, or likelihood.
    expected = set(prior.LEGACY_KEYS) | set(prior.ARTIFACT_INPUTS) | {
        'v55_program','v55_registration','v55_completion','v55_audit','v55_ledger',
        'v59_software_checks','v59_program','v59_registration','v59_completion','v59_audit','v59_ledger',
        'software_checks',*V59_ARTIFACTS,*DATA_KEYS}
    require(set(inputs) == expected, 'Complete V61 input inventory required')
    paths = {key:bound(entry) for key,entry in inputs.items()}
    p,c,a = (read(paths[key]) for key in ('v59_program','v59_completion','v59_audit'))
    check_prior(p,c,a,inputs)
    require(read(paths['v59_registration']) == dict(program_sha256=V59_PROGRAM), 'Frozen V59 registration changed')
    for key,entry in p['inputs'].items():
        current = inputs['v59_software_checks' if key == 'software_checks' else key]
        require(current == entry, 'Frozen V59 inherited input differs: '+key)
    verified,_,previous,_,previous_completion = prior.verify(paths['v59_program'].parent)
    require(verified == p and p['sources'] == prior.sources(), 'Frozen V59 numerical sources changed')
    require(check_result(c,previous_completion,read(paths['v59_historical_parity'])) == a['summary'],
        'V59 raw loss/guard summary does not reproduce')
    from research_v54.postrun import Inputs
    from research_v59.audit import check_worker_receipt
    snapshot = read_budget_snapshot(paths['v59_ledger'].parent,
        identity=dict(protocol_sha256=V59_PROGRAM,source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'development':prior.PHASE_CAP})
    require(snapshot['status'] == 'verified' and not snapshot['reserved_unknown_attempts']
        and not any(snapshot['over_cap'].values()) and a['budget'] == snapshot, 'V59 settled ledger differs')
    check_worker_receipt(paths['v59_program'].parent,p,Inputs(),snapshot)
    v54 = read(paths['v54_program'])
    require(inputs['v54_program']['sha256'] == V54_PROGRAM and p['retained_records'] == v54['records'][-6:], 'Exact V54 final-six membership required')
    for key in DATA_KEYS:
        require(inputs[key] == v54['inputs'][key], 'Frozen V54 data binding differs: '+key)
    selection = read(paths['data_selection']);records=read(paths['data_records'])['records']
    require(records == v54['records'] and records == sorted(records,key=lambda row:row['id'])
        and len(records) == 13 and all(len(row['tokens']) == 128 for row in records)
        and v54['retained_counts'] == [12,6] and v54['normalization'] == 1664,
        'Exact V54 root/selection required')
    metadata = {row['id']:row for row in selection['selected_metadata']}
    from research_v45.data import POLICY,TOKENIZER_SHA
    provenance = {row['id']:dict(dataset_id='allenai/c4',dataset_revision=POLICY['revision'],split='train-shard1-prefix',
        source_file_sha256=selection['source_files']['new_c4']['sha256'],tokenizer_sha256=TOKENIZER_SHA,
        body_sha256=metadata[row['id']]['body_sha256'],normalized_text_sha256=metadata[row['id']]['normalized_text_sha256'],
        selection_sha256=inputs['data_selection']['sha256']) for row in records}
    require(provenance == v54['record_provenance'], 'Original provenance does not reproduce from fixed selection')
    exclusions = read(paths['historical_exclusions'])['excluded_from_future_confirmation_ids']
    require(len(set(exclusions)) == 60 and exclusions == c['excluded_from_future_confirmation_ids'], 'Preserve all sixty quality exclusions')
    return p,v54,c


def design():
    return dict(normalization=1664,tokens_per_record=128,record_count=13,retained_counts=[12,6],
        trials=TRIALS,trial_order=ORDER,phase_cpu_seconds=CAP,process_address_space_bytes=16*2**30,
        file_size_bytes=2*2**30,precision=48,block_size=256,shared_backend='normal_neighbor_primal_v50',
        adaptive_development=True,complete_model=True,confirmation=False,quality_evaluation=False,
        automatic_retry=False,paid_compute=False,gpu_numeric_execution=False,threads=1,
        state_schema='complete-full-precision-anchor-successor-v61',state_family='full_precision_anchor_service_v61',
        target_schema='fixed-full-precision-anchor-service-target-v61',calibration_target_sha256=V59_TARGET,
        final_six_model_sha256=V59_MODEL,final_six_actual_v59_bytes_required=True,
        allowance_scope='Fresh V61 service allowance only; no historical allowance or timing transferred',
        independent_oracle='Fresh original-teacher retained-token traversal and all-representation states; never prior-state descriptors',
        statistical_scope='One adaptively reused known C4 root; one observation per arm/step; no interval or population claim',
        representation_rule='Lossless, compressed48 block256, and hybrid native exact Grams at eighteen width768 stages with lossless six width3072 stages',
        state_scope='All ordered codes, both service targets, retained tokens/provenance and representation payloads, required trust sidecars and common checkpoint')


def check_software(check,current_sources,current_runtime):
    from research_v61.checks import MODULES,EXPECTED_TESTS
    require(check['status'] == 'passed' and check['skipped'] == 0 and check['tests'] == EXPECTED_TESTS
        and check['modules'] == list(MODULES) and check['sources'] == current_sources
        and check['runtime'] == current_runtime and check['real_model_inference'] is False,
        'Complete passing source/runtime-bound Linux software checks required')


def register(directory,v59_directory,checks):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform == 'linux', 'Pinned Linux Slurm required')
    directory = Path(directory).resolve()
    require(directory == ROOT/'local_runs'/CAMPAIGN_NAME and not directory.exists(), 'Fresh one-use V61 path required')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(), 'Clean committed source required')
    s,r = sources(),runtime();check_software(read(checks),s,r)
    inputs=dependencies(v59_directory);inputs['software_checks']=bind(checks)
    previous,v54,_=validate_inputs(inputs)
    require(r == previous['runtime'] == v54['runtime'], 'Pinned V59/V54 runtime required')
    selection,rows,data_snapshot = validate_data(bound(inputs['data_program']).parent)
    require(rows == v54['records'] and selection == read(bound(inputs['data_selection'])), 'Archive admission selection changed')
    from research_v61.resource_review import review
    structural = review(bound(inputs['v59_base_target']).read_bytes())
    historical = {str(path.relative_to(ROOT)):sha(path) for folder in ('campaigns','pilots','local_runs')
        for path in (ROOT/folder).rglob('ledger.json')}
    program = dict(schema='full-precision-anchor-complete-service-v61',directory=str(directory),
        registered_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        registration_job=os.environ['SLURM_JOB_ID'],sources=s,runtime=r,inputs=inputs,historical_ledgers=historical,
        records=v54['records'],record_provenance=v54['record_provenance'],deletion_order=v54['deletion_order'],
        shape_admission=structural,data_history_delta=history_delta(read(bound(inputs['data_program']))['history']),
        data_phase_charged_cpu_seconds=data_snapshot['charged_cpu_seconds']['data'],
        shared_checkpoint_bytes=sum(inputs[key]['bytes'] for key in ('checkpoint_config','checkpoint_weights')),**design())
    new(directory/'program.json',program);new(directory/'registration.json',dict(program_sha256=sha(directory/'program.json')))
    budget(program)
    print(canonical_json(dict(status='registered',program_sha256=sha(directory/'program.json'),trial_order=ORDER,phase_cpu_seconds=CAP)).decode())
    return program


def verify(directory):
    directory=Path(directory).resolve();p=read(directory/'program.json')
    require(p['schema'] == 'full-precision-anchor-complete-service-v61' and p['directory'] == str(directory)
        and directory == ROOT/'local_runs'/CAMPAIGN_NAME and all(p.get(k) == v for k,v in design().items()), 'Frozen V61 design differs')
    require(read(directory/'registration.json') == dict(program_sha256=sha(directory/'program.json')), 'Registration changed')
    require(p['sources'] == sources() and p['runtime'] == runtime(), 'Source/runtime changed')
    previous,v54,_ = validate_inputs(p['inputs'])
    require(p['runtime'] == previous['runtime'] and all(p[k] == v54[k] for k in ('records','record_provenance','deletion_order')), 'Frozen root/provenance changed')
    require(p['shared_checkpoint_bytes'] == sum(p['inputs'][key]['bytes'] for key in ('checkpoint_config','checkpoint_weights')), 'Checkpoint extent changed')
    from research_v61.resource_review import review
    require(p['shape_admission'] == review(bound(p['inputs']['v59_base_target']).read_bytes()), 'Structural admission changed')
    for name,expected in p['historical_ledgers'].items():
        require(sha(ROOT/name) == expected, 'Historical ledger changed')
    check_software(read(bound(p['inputs']['software_checks'])),p['sources'],p['runtime'])
    return p


def budget(p):
    return PhaseBudget(Path(p['directory'])/'budget',identity=dict(protocol_sha256=sha(Path(p['directory'])/'program.json'),
        source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'feasibility':CAP})


def run(directory,trial):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform == 'linux', 'Pinned Linux Slurm required')
    p=verify(directory);require(trial in TRIALS,'Unknown trial');root=Path(p['directory'])
    for previous in ORDER[:ORDER.index(trial)]:
        require(read(root/previous/'transaction.json')['worker_outcome']['status'] == 'complete'
            and read(root/previous/'outputs/completion.json')['status'] == 'complete', 'Earlier trial did not complete')
    attempt=root/trial;require(not attempt.exists(),'One-use attempt exists; retries prohibited');attempt.mkdir()
    plan=dict(trial=trial,program=str(root/'program.json'),program_sha256=sha(root/'program.json'),
        output=str(attempt/'outputs'),slurm_job_id=os.environ['SLURM_JOB_ID'])
    new(attempt/'plan.json',plan);tick=time.perf_counter_ns()
    receipt=run_limited([sys.executable,'-B','-m','research_v61.worker',str(attempt/'plan.json')],attempt/'worker',
        WorkerLimits(**TRIALS[trial],address_space_bytes=p['process_address_space_bytes'],threads=1,
            affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=p['file_size_bytes']),
        identity=dict(campaign_sha256=sha(root/'program.json'),trial=trial),cwd=ROOT,phase_budget=budget(p),phase='feasibility')
    new(attempt/'transaction.json',dict(worker_outcome=receipt['outcome'],elapsed_ns=time.perf_counter_ns()-tick,
        budget=budget(p).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(canonical_json(receipt['outcome']).decode(),flush=True);return receipt['outcome']['status']


if __name__ == '__main__':
    parser=argparse.ArgumentParser();commands=parser.add_subparsers(dest='operation',required=True)
    reg=commands.add_parser('register')
    for name in ('directory','v59_directory','checks'):reg.add_argument(name)
    dispatch=commands.add_parser('run');dispatch.add_argument('directory');dispatch.add_argument('trial',choices=tuple(TRIALS))
    arguments=parser.parse_args()
    if arguments.operation == 'register':register(arguments.directory,arguments.v59_directory,arguments.checks)
    elif run(arguments.directory,arguments.trial) != 'complete':raise SystemExit(1)
