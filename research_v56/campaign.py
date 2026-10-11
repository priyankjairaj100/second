"""New GPU parity gate; Python3.10-safe input hashing, no exact CPU execution."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from research_v47.campaign import ROOT,require,read,sha,new,bind,bound,runtime
from src.run_store import canonical_json,digest
from src.phase_budget import PhaseBudget
from src.experiment_inventory import source_hashes
from src.worker_control import WorkerLimits,run_limited

CPU,WALL,CAP=1200,1500,1202
EXPORT='1803adfd4b9548a605dc468a7c982d077abaaa43f36df6bfce8c4098a7170915'
ARRAYS='c5cc19cde2e526bb3098efaec5c7709ac3714bd781f8753c1c5b77f6c4a67f2b'
MANIFEST='8e4c3e790b7c1747f6fe114899240c6f14c10b8111f9d7df9f2a41d64e6f5d9d'
V54='03a6181b0d32ad023706145fbde28f202ed5d137e95a4b16ecbd19686858465b'


def sources():
    base=read(ROOT/'research_v56/SOURCE_BASE.json')
    for name,h in base.items():require(sha(ROOT/name)==h,'Frozen V55 dependency changed: '+name)
    for path in sorted((ROOT/'research_v56').iterdir()):
        if path.is_file() and path.suffix in ('.py','.txt','.json','.sbatch'):
            base[str(path.relative_to(ROOT))]=sha(path)
    base['cluster_setup/v56_pipeline.sh']=sha(ROOT/'cluster_setup/v56_pipeline.sh')
    return base


def dependencies():
    root=ROOT/'local_runs/exposed-quality-v55-20261011-a';out=root/'quality/outputs'
    paths=dict(cpu_program=root/'program.json',cpu_registration=root/'registration.json',cpu_audit=root/'artifact-audit.json',
        cpu_completion=out/'completion.json',cpu_ledger=root/'budget/ledger.json')
    for key,name in [('base_target','sequential-target.json'),('fixed_target','fixed-target.json'),
        ('sequential_model','sequential-model.bin'),('sequential_metadata','sequential-model-metadata.json')]:
        paths[key]=out/name
    export=ROOT/'local_runs/cpu-parameters-v47-20261010-a'
    paths.update(export_program=export/'program.json',export_registration=export/'registration.json',
        export_completion=export/'completion.json',export_ledger=export/'budget/ledger.json',
        parameter_manifest=export/'outputs/manifest.json',parameter_arrays=export/'outputs/parameters.npz')
    return {name:bind(path) for name,path in paths.items()}


def validate_cpu_result(p,c,a,program_hash):
    from research_v55.diagnostic import summarize
    require(p['schema']=='exposed-quality-diagnostic-v55' and p['normalization']==1664 and
        p['inputs']['v54_program']['sha256']==V54 and len(p['retained_records'])==6 and
        all(len(r['tokens'])==128 for r in p['retained_records']), 'V55 calibration input differs')
    require(c['schema']=='exposed-quality-worker-v55' and c['status']=='complete' and c['valid_diagnostic'] is True
        and c['program_sha256']==program_hash and c['original_normalization']==1664 and c['retained_calibration_tokens']==768,
        'A valid completed CPU diagnostic is required')
    require(a['schema']=='exposed-quality-artifact-audit-v55' and a['status']=='verified' and a['program_sha256']==program_hash
        and a['campaign']==p['directory'] and a['actual_model_codes_reconstructed']==42_467_328
        and a['complete_stages']==24 and a['sealed_cpu_receipt_verified'] is True,'Actual complete CPU audit required')
    summary=summarize(c['quality'])
    require(summary==c['summary']==a['summary'] and
        summary['development_guards_pass']==c['development_guards_pass']==a['development_guards_pass'],
        'CPU losses, summary or quality guard flags differ')
    # Deliberately do not require development_guards_pass: valid adverse results
    # receive the same parity check, avoiding favorable-outcome selection.
    return summary


def validate(inputs):
    paths={name:bound(entry) for name,entry in inputs.items()}
    p,c,a=(read(paths[k]) for k in ('cpu_program','cpu_completion','cpu_audit'))
    ph=inputs['cpu_program']['sha256']
    require(read(paths['cpu_registration'])['program_sha256']==ph,'CPU registration differs')
    validate_cpu_result(p,c,a,ph)
    require(p['sources']==read(ROOT/'research_v56/SOURCE_BASE.json'),'V55 source inventory differs')
    for name,h in p['sources'].items():require(sha(ROOT/name)==h,'Frozen CPU source changed: '+name)
    old_paths={k:bound(v) for k,v in p['inputs'].items()}
    from research_v55.diagnostic import validate_exposed,check_result
    records=validate_exposed(read(old_paths['historical_registration']),read(old_paths['historical_losses']))
    require(records==p['records'] and len(set(read(old_paths['all_exclusions'])['excluded_from_future_confirmation_ids']))==60,
        'Exposed records or exclusion registry differ')
    # Recompute parity as well as quality summaries, rather than trust booleans.
    check_result(c,read(old_paths['historical_losses']),c['historical_parity'])
    for key in ('base_target','fixed_target','sequential_model','sequential_metadata'):
        entry=c['artifacts'][paths[key].name]
        require(all(entry[f]==inputs[key][f] for f in ('sha256','bytes')),'CPU model artifact changed')
    for key in ('cpu_completion','cpu_ledger','base_target','fixed_target','sequential_model','sequential_metadata'):
        require(a['inputs'][str(paths[key])]=={f:inputs[key][f] for f in ('sha256','bytes')},'CPU audit input changed')
    for key in ('fixed_model','fixed_state'):
        entry=p['inputs'][key]
        require(a['inputs'][entry['path']]=={f:entry[f] for f in ('sha256','bytes')},'Audited fixed model changed')
    ledger=read(paths['cpu_ledger'])
    require(len(ledger['attempts'])==1 and all(r['state']=='settled' for r in ledger['attempts'].values()),'CPU ledger unsettled')
    require(inputs['export_program']['sha256']==EXPORT==read(paths['export_registration'])['program_sha256']
        and inputs['parameter_arrays']['sha256']==ARRAYS and inputs['parameter_manifest']['sha256']==MANIFEST,
        'Pinned CPU parameter export changed')
    ep,ec=read(paths['export_program']),read(paths['export_completion'])
    require(ec['program_sha256']==EXPORT and ec['status']=='complete' and ec['array_words_verified'] is True
        and ec['model_inference'] is False,'Completed CPU word export required')
    for name,h in ep['sources'].items():require(sha(ROOT/name)==h,'Export source changed')
    for key,name in [('parameter_manifest','manifest.json'),('parameter_arrays','parameters.npz')]:
        require(all(inputs[key][f]==ec['artifacts'][name][f] for f in ('sha256','bytes')),'Exported artifact binding differs')
    require(all(r['state']=='settled' for r in read(paths['export_ledger'])['attempts'].values()),'Export budget unsettled')
    return p,c


def budget(p):
    return PhaseBudget(Path(p['directory'])/'budget',identity=dict(protocol_sha256=sha(Path(p['directory'])/'program.json'),
        source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'development':CAP})


def register(directory,checks):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm GPU allocation required')
    directory=Path(directory).resolve();require(ROOT in directory.parents and not directory.exists(),'Fresh campaign path required')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Clean committed source required')
    s,r=sources(),runtime();check=read(checks)
    require(check['status']=='passed' and check['tests']==12 and check['skipped']==0 and check['sources']==s and check['runtime']==r,
        'Passing bound CUDA software checks required')
    inputs=dependencies();inputs['software_checks']=bind(checks);cpu,_=validate(inputs)
    p=dict(schema='cuda-likelihood-parity-v56',directory=str(directory),inputs=inputs,sources=s,runtime=r,
        registered_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),records=cpu['records'],
        cpu_seconds=CPU,wall_seconds=WALL,phase_cpu_seconds=CAP,physical_host_memory_bytes=16*2**30,
        address_space_bytes=128*2**40,gpu_allocator_bytes=8*2**30,file_size_bytes=2*2**30,slurm_wall_seconds=1800,
        threshold=1e-8,threads=1,automatic_retry=False,new_quality_inputs=False,confirmation=False,acl_ready=False,
        exact_calibration_equivalence=False,registration_job=os.environ['SLURM_JOB_ID'])
    directory.mkdir(parents=True);new(directory/'program.json',p)
    new(directory/'registration.json',dict(program_sha256=sha(directory/'program.json')));budget(p)
    return p


def verify(directory):
    directory=Path(directory).resolve();p=read(directory/'program.json')
    require(p['schema']=='cuda-likelihood-parity-v56' and p['directory']==str(directory) and
        read(directory/'registration.json')['program_sha256']==sha(directory/'program.json'),'V56 registration changed')
    require(p['sources']==sources() and p['runtime']==runtime(),'GPU sources or runtime changed')
    cpu,_=validate(p['inputs'])
    require(p['records']==cpu['records'] and p['threshold']==1e-8 and
        (p['cpu_seconds'],p['wall_seconds'],p['phase_cpu_seconds'])==(CPU,WALL,CAP) and
        p['address_space_bytes']==128*2**40 and p['gpu_allocator_bytes']==8*2**30 and
        p['physical_host_memory_bytes']==16*2**30 and p['file_size_bytes']==2*2**30 and p['threads']==1 and
        p['automatic_retry'] is False and p['confirmation'] is False,'GPU design changed')
    return p


def run(directory):
    p=verify(directory);root=Path(p['directory'])/'parity';root.mkdir(exist_ok=False)
    plan=dict(program=str(Path(p['directory'])/'program.json'),program_sha256=sha(Path(p['directory'])/'program.json'),
        output=str(root/'outputs'),slurm_job_id=os.environ['SLURM_JOB_ID'])
    new(root/'plan.json',plan);tick=time.perf_counter_ns()
    receipt=run_limited([sys.executable,'-B','-m','research_v56.worker',str(root/'plan.json')],root/'worker',
        WorkerLimits(cpu_seconds=CPU,wall_seconds=WALL,address_space_bytes=p['address_space_bytes'],threads=1,
            affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=p['file_size_bytes']),
        identity=dict(program_sha256=plan['program_sha256']),cwd=ROOT,phase_budget=budget(p),phase='development')
    new(root/'transaction.json',dict(worker_outcome=receipt['outcome'],elapsed_ns=time.perf_counter_ns()-tick,
        budget=budget(p).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(canonical_json(receipt['outcome']).decode(),flush=True)
    return receipt['outcome']['status']


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('checks');args=parser.parse_args()
    register(args.directory,args.checks)
    if run(args.directory)!='complete':raise SystemExit(1)
    from research_v56.audit import audit
    audit(args.directory,Path(args.directory)/'artifact-audit.json')
