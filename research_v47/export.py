"""One-use CPU-only parameter materialization; no neural inference."""
import argparse
import os
from pathlib import Path
import sys
import time
import traceback
from research_v46.campaign import ROOT,read,sha,new,require,bind,bound
from research_v44.campaign import runtime
from research_v47.campaign import sources
from src.phase_budget import PhaseBudget
from src.experiment_inventory import source_hashes
from src.worker_control import WorkerLimits,run_limited
from src.transaction_timing import verify_command_admission

CAP=602


def budget(p):return PhaseBudget(Path(p['directory'])/'budget',identity=dict(
    protocol_sha256=sha(Path(p['directory'])/'program.json'),source_sha256=source_hashes(ROOT)),
    phase_cpu_seconds={'development':CAP})


def verify(directory):
    directory=Path(directory).resolve();p=read(directory/'program.json')
    require(p['directory']==str(directory) and p['sources']==sources() and p['runtime']==runtime()
        and read(directory/'registration.json')['program_sha256']==sha(directory/'program.json'),
        'CPU export source/runtime/program differs')
    for entry in p['inputs'].values():bound(entry)
    return p


def register(directory):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm required')
    directory=Path(directory).resolve();require(ROOT in directory.parents and not directory.exists(),'Fresh export path required')
    paths={name:ROOT/'tmp/models/distilgpt2'/name for name in ('config.json','model.safetensors')}
    failed=ROOT/'local_runs/cuda-parity-v46-20261010-b'
    paths.update(v46_completion=failed/'parity/outputs/completion.json',v46_ledger=failed/'budget/ledger.json')
    require(read(paths['v46_completion'])['status']=='failed'
        and read(paths['v46_completion'])['quality']=={}
        and all(r['state']=='settled' for r in read(paths['v46_ledger'])['attempts'].values()),
        'Preserve settled pre-likelihood V46 failure')
    from research_v38.bootstrap_target import CHECKPOINT_HASHES
    require(all(sha(paths[k])==v for k,v in CHECKPOINT_HASHES.items()),'Checkpoint differs')
    p=dict(schema='cpu-parameter-export-v47',directory=str(directory),sources=sources(),runtime=runtime(),
        inputs={k:bind(v) for k,v in paths.items()},cpu_seconds=600,wall_seconds=900,phase_cpu_seconds=CAP,
        memory_bytes=8*2**30,file_bytes=2*2**30,model_inference=False,automatic_retry=False,
        registration_job=os.environ['SLURM_JOB_ID'])
    directory.mkdir(parents=True);new(directory/'program.json',p)
    new(directory/'registration.json',dict(program_sha256=sha(directory/'program.json')));budget(p)


def run(directory):
    p=verify(directory);directory=Path(p['directory']);require(not (directory/'worker').exists(),'Export already attempted')
    tick=time.perf_counter_ns()
    receipt=run_limited([sys.executable,'-B','-m','research_v47.export','worker',str(directory)],directory/'worker',
        WorkerLimits(cpu_seconds=600,wall_seconds=900,address_space_bytes=8*2**30,threads=1,
            affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=2*2**30),
        identity=dict(program_sha256=sha(directory/'program.json')),cwd=ROOT,phase_budget=budget(p),phase='development')
    new(directory/'transaction.json',dict(worker_outcome=receipt['outcome'],elapsed_ns=time.perf_counter_ns()-tick,
        budget=budget(p).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    return receipt['outcome']['status']


def worker(directory):
    p=verify(directory);directory=Path(p['directory']);ph=sha(directory/'program.json')
    verify_command_admission(ph,'development',[sys.executable,'-B','-m','research_v47.export','worker',str(directory)])
    tick=time.perf_counter_ns();result=dict(schema='cpu-parameter-export-result-v47',status='running',
        program_sha256=ph,model_inference=False)
    try:
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from scripts.run_quality_v30 import NumpyQualityDecoder
        from research_v47.snapshot import write_snapshot
        loaded=load_gpt2_checkpoint(bound(p['inputs']['config.json']).parent,identity_encoding='binary64_tree_v2')
        evaluator=NumpyQualityDecoder(loaded.decoder)
        manifest=write_snapshot(evaluator,directory/'outputs')
        result.update(status='complete',array_count=len(manifest['arrays']),
            array_words_verified=True,checkpoint=loaded.provenance,
            artifacts={name:bind(directory/'outputs'/name) for name in ('manifest.json','parameters.npz')})
    except Exception as error:
        result.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
    finally:
        result['elapsed_ns']=time.perf_counter_ns()-tick;new(directory/'completion.json',result)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('register','run','worker'))
    parser.add_argument('directory');args=parser.parse_args()
    if args.operation=='register':register(args.directory)
    elif args.operation=='worker':worker(args.directory)
    else:sys.exit(0 if run(args.directory)=='complete' else 1)
