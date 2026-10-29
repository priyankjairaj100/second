"""Independent, one-use CUDA parity registration and CPU admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from src.run_store import canonical_json, digest
from src.phase_budget import PhaseBudget
from src.experiment_inventory import source_hashes
from src.worker_control import WorkerLimits, run_limited

ROOT=Path(__file__).resolve().parents[1]
V44_PROGRAM='e3d7b6dfd1ad9199a180aac2e706ef8b2334c709947b2b8b6e90e4a81dc3e02c'
CPU,WALL,CAP=1200,1500,1202


def require(value,message):
    if not value: raise ValueError(message)


def read(path): return json.loads(Path(path).read_bytes())


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(2**20),b''):h.update(block)
    return h.hexdigest()


def new(path,value):
    with Path(path).open('xb') as stream:stream.write(canonical_json(value))


def bind(path):
    p=Path(path).resolve(strict=True)
    return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)


def bound(entry):
    p=Path(entry['path'])
    require(p.is_absolute() and p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256'],
        'Bound file differs: '+str(p))
    return p


def sources():
    folders=['src','scripts','research_v35','research_v38','research_v42','research_v43','research_v44','research_v46','research_v47']
    paths=[p for name in folders for p in (ROOT/name).glob('*.py')]
    paths += [ROOT/'research_v46/PROTOCOL.txt',ROOT/'research_v47/PROTOCOL.txt',ROOT/'research_v47/run_gpu.sbatch']
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}


def runtime():
    import numpy,torch
    result=dict(python=sys.version,executable=bind(sys.executable),numpy=numpy.__version__,
        torch=torch.__version__,cuda_build=torch.version.cuda,packages={},
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total',
            '--format=csv,noheader'],text=True).strip(),
        cublas_workspace=os.environ.get('CUBLAS_WORKSPACE_CONFIG'))
    for name,module in [('numpy',numpy),('torch',torch)]:
        origin=Path(module.__file__).resolve();files={origin}
        if name=='numpy':files.update(origin.parent.rglob('*.so'))
        else:
            files.update(origin.parent.glob('_C*.so'))
            files.update((origin.parent/'lib').glob('*.so'))
        result['packages'][name]={str(p):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(files)}
    require(result['cublas_workspace']==':4096:8' and result['cuda_build'] is not None,
        'The frozen CUDA runtime is required')
    return result


def dependencies():
    root=ROOT/'local_runs/exposed-quality-v44-20261010-b'
    paths=dict(v44_program=root/'program.json',v44_registration=root/'registration.json',
        v44_completion=root/'quality/outputs/completion.json',v44_ledger=root/'budget/ledger.json')
    for key,name in [('base_target','sequential-target.json'),('fixed_target','fixed-target.json'),
        ('sequential_model','sequential-model.bin'),('sequential_metadata','sequential-model-metadata.json')]:
        paths[key]=root/'quality/outputs'/name
    export=ROOT/'local_runs/cpu-parameters-v47-20261010-a'
    paths.update(export_program=export/'program.json',export_registration=export/'registration.json',
        export_completion=export/'completion.json',export_ledger=export/'budget/ledger.json',
        parameter_manifest=export/'outputs/manifest.json',parameter_arrays=export/'outputs/parameters.npz')
    return {k:bind(v) for k,v in paths.items()}


def validate(inputs):
    paths={k:bound(v) for k,v in inputs.items()}
    require(inputs['v44_program']['sha256']==V44_PROGRAM
        and read(paths['v44_registration'])['program_sha256']==V44_PROGRAM,'V44 identity differs')
    p=read(paths['v44_program']);c=read(paths['v44_completion'])
    require(c['status']=='complete' and c['valid_diagnostic'] and c['development_guards_pass']
        and c['program_sha256']==V44_PROGRAM,'A completed V44 diagnostic is required')
    # The GPU module uses Python3.10. Keep its streamed hashlib interface local;
    # never alter the frozen Python3.12 CPU campaign or monkey-patch hashlib.
    from research_v44.campaign import check_audits
    from research_v44.diagnostic import validate_exposed
    old_paths={key:bound(entry) for key,entry in p['inputs'].items()}
    old=read(old_paths['v43_program'])
    require(read(old_paths['v43_registration'])['program_sha256']==p['inputs']['v43_program']['sha256'],
        'V43 registration differs')
    for name,expected in old['sources'].items():
        require(sha(ROOT/name)==expected,'Frozen V43 source differs')
    check_audits(old,p['inputs']['v43_program']['sha256'],read(old_paths['first_audit']),
        read(old_paths['second_audit']),p['inputs']['first_audit']['sha256'],
        p['inputs']['fixed_model']['sha256'],p['inputs']['fixed_state']['sha256'])
    records=validate_exposed(read(old_paths['historical_registration']),read(old_paths['historical_losses']))
    require(records==p['records'],'Exposed articles changed')
    require(len(set(read(old_paths['all_exclusions'])['excluded_from_future_confirmation_ids']))==60,
        'Preserve all historical quality exclusions')
    for key in ('base_target','fixed_target','sequential_model','sequential_metadata'):
        a=c['artifacts'][paths[key].name]
        require(all(a[k]==inputs[key][k] for k in ('sha256','bytes')),'V44 artifact binding differs')
    ledger=read(paths['v44_ledger'])
    require(all(r['state']=='settled' for r in ledger['attempts'].values()),'V44 ledger remains unsettled')
    ep=read(paths['export_program']);ec=read(paths['export_completion'])
    require(read(paths['export_registration'])['program_sha256']==inputs['export_program']['sha256']
        and ec['program_sha256']==inputs['export_program']['sha256']
        and ec['status']=='complete' and ec['array_words_verified'] and ec['model_inference'] is False,
        'Completed CPU word export required')
    require(ep['sources']==sources(),'CPU export sources changed')
    for key,name in [('parameter_manifest','manifest.json'),('parameter_arrays','parameters.npz')]:
        require(all(inputs[key][field]==ec['artifacts'][name][field] for field in ('sha256','bytes')),
            'CPU exported artifact changed')
    require(all(r['state']=='settled' for r in read(paths['export_ledger'])['attempts'].values()),
        'CPU export budget unsettled')
    return p,c


def budget(p):
    return PhaseBudget(Path(p['directory'])/'budget',identity=dict(
        protocol_sha256=sha(Path(p['directory'])/'program.json'),source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'development':CAP})


def register(directory):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm GPU allocation required')
    directory=Path(directory).resolve()
    require(ROOT in directory.parents and not directory.exists(),'Fresh repository campaign required')
    inputs=dependencies();v44,_=validate(inputs)
    p=dict(schema='cuda-likelihood-parity-v47',directory=str(directory),inputs=inputs,
        sources=sources(),runtime=runtime(),registered_source_commit=subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),records=v44['records'],
        cpu_seconds=CPU,wall_seconds=WALL,phase_cpu_seconds=CAP,physical_host_memory_bytes=16*2**30,
        address_space_bytes=128*2**40,gpu_allocator_bytes=8*2**30,slurm_wall_seconds=1800,
        threshold=1e-8,threads=1,automatic_retry=False,new_quality_inputs=False,
        confirmation=False,acl_ready=False,exact_calibration_equivalence=False,
        registration_job=os.environ['SLURM_JOB_ID'])
    directory.mkdir(parents=True);new(directory/'program.json',p)
    new(directory/'registration.json',dict(program_sha256=sha(directory/'program.json')))
    budget(p);print(json.dumps(dict(status='registered',program_sha256=sha(directory/'program.json'))),flush=True)


def verify(directory):
    directory=Path(directory).resolve();p=read(directory/'program.json')
    require(p['directory']==str(directory) and p['schema']=='cuda-likelihood-parity-v47'
        and read(directory/'registration.json')['program_sha256']==sha(directory/'program.json'),
        'V47 registration differs')
    require(p['sources']==sources() and p['runtime']==runtime(),'Registered source/runtime changed')
    v44,_=validate(p['inputs'])
    require(p['records']==v44['records'] and p['threshold']==1e-8
        and (p['cpu_seconds'],p['wall_seconds'],p['phase_cpu_seconds'])==(CPU,WALL,CAP),
        'Frozen parity design differs')
    return p


def run(directory):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm GPU allocation required')
    p=verify(directory);attempt=Path(p['directory'])/'parity';attempt.mkdir(exist_ok=False)
    plan=dict(program=str(Path(p['directory'])/'program.json'),
        program_sha256=sha(Path(p['directory'])/'program.json'),output=str(attempt/'outputs'),
        slurm_job_id=os.environ['SLURM_JOB_ID'])
    new(attempt/'plan.json',plan)
    limits=WorkerLimits(cpu_seconds=CPU,wall_seconds=WALL,address_space_bytes=p['address_space_bytes'],
        threads=1,affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=2*2**30)
    tick=time.perf_counter_ns()
    receipt=run_limited([sys.executable,'-B','-m','research_v47.worker',str(attempt/'plan.json')],
        attempt/'worker',limits,identity=dict(program_sha256=plan['program_sha256']),cwd=ROOT,
        phase_budget=budget(p),phase='development')
    new(attempt/'transaction.json',dict(worker_outcome=receipt['outcome'],elapsed_ns=time.perf_counter_ns()-tick,
        budget=budget(p).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(json.dumps(receipt['outcome']),flush=True)
    return receipt['outcome']['status']


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('register','run'))
    parser.add_argument('directory');args=parser.parse_args()
    if args.operation=='register':register(args.directory)
    else:sys.exit(0 if run(args.directory)=='complete' else 1)
