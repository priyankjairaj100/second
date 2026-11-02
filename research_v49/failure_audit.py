"""Read the terminal V45 failure without mutating its ledger or promoting progress."""
from pathlib import Path
from research_v48.report import read,sha,require,scheduler_status,PROFILES,V45_JOBS
from src.run_store import canonical_json,read_completed
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes

ROOT=Path(__file__).resolve().parents[1]


def inspect(directory,accounting):
    directory=Path(directory).resolve();program=read(directory/'program.json');ph=sha(directory/'program.json')
    require(ph==PROFILES['v45']['program']==read(directory/'registration.json')['program_sha256'],'V45 identity differs')
    for name,value in program['sources'].items():require(sha(ROOT/name)==value,'Frozen source differs: '+name)
    jobs=scheduler_status(Path(accounting).read_text())
    require(jobs['status']=='terminal_failure_observed' and not jobs['missing_jobs'],'Complete failure accounting required')
    require(jobs['jobs']['13228']['state']=='FAILED' and jobs['jobs']['13228']['exit_code']=='1:0',
        'Preparation scheduler outcome differs')
    require(all(jobs['jobs'][j]['state'].startswith('CANCELLED') for j in V45_JOBS if j!='13228'),
        'Downstream jobs were not all cancelled')
    root=directory/'prepare';identity=read(root/'worker/identity.json');receipt=read_completed(root/'worker',identity)
    require(receipt is not None and identity['identity']==dict(campaign_sha256=ph,trial='prepare'),
        'Sealed failed preparation is missing')
    require(receipt==read(root/'worker'/receipt['attempt']/'status.json'),'Terminal status differs')
    require(receipt['outcome']['status']=='failed' and receipt['outcome']['kind']=='cpu_limit'
        and receipt['outcome']['signal']==24 and receipt['outcome']['returncode']==-24,'Not the declared CPU-limit failure')
    tx=read(root/'transaction.json')
    require(tx['slurm_job_id']=='13228' and tx['worker_outcome']==receipt['outcome'],'Transaction differs')
    snapshot=read_budget_snapshot(directory/'budget',identity=dict(protocol_sha256=ph,source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'feasibility':program['phase_cpu_seconds']})
    require(snapshot['status']=='verified' and snapshot['reserved_unknown_attempts']==0 and not any(snapshot['over_cap'].values())
        and snapshot['attempts']=={receipt['budget_attempt_id']:receipt['budget_debit']},'Failure charge is not settled/bound')
    require(receipt['budget_debit']['observed_cpu_ns']==receipt['resource_usage']['total_cpu_ns'],
        'CPU observation differs from charge')
    require(identity['phase_budget']==dict(directory=str(Path(program['directory'])/'budget'),phase='feasibility',
        binding_sha256=snapshot['binding_sha256']), 'Identity budget differs')
    require(identity['limits']['cpu_seconds']==program['trials']['prepare']['cpu_seconds']==4800,'Frozen limit differs')
    require(not (root/'outputs/completion.json').exists() and not (root/'outputs/original-model.bin').exists()
        and not (directory/'artifact-audit.json').exists() and not (directory/'postrun-audit.json').exists(),
        'Unexpected final artifacts need separate review')
    paths=sorted((root/'outputs').glob('progress-*.json'))
    require([p.name for p in paths]==[f'progress-{n:04d}.json' for n in range(len(paths))],'Progress has gaps')
    rows=[read(p) for p in paths]
    require(all(a['elapsed_ns']<=b['elapsed_ns'] for a,b in zip(rows,rows[1:])),'Progress time order differs')
    stages=[r for r in rows if r['phase']=='stage_certified']
    replayed=[r['record_id'] for r in rows if r['phase']=='source_replayed']
    require(replayed==[r['id'] for r in program['records']],'Source progress differs from original order')
    expected=[f'block.{i:04d}.{name}' for i in range(6) for name in ('qkv','attn_out','mlp_up','mlp_down')]
    require([r['stage_id'] for r in stages]==expected[:len(stages)] and len(stages)==11,'Certified prefix differs')
    require(all(r['fallback'] is False for r in stages),'Unexpected fallback requires review')
    inputs={str(p.relative_to(directory)):dict(bytes=p.stat().st_size,sha256=sha(p))
        for p in sorted(directory.rglob('*')) if p.is_file()}
    return dict(schema='v45-terminal-failure-audit-v49',status='verified_terminal_cpu_limit_failure',
        program_sha256=ph,frozen_sources_verified=len(program['sources']),scheduler=jobs,
        accounting_sha256=sha(accounting),inputs=inputs,worker_outcome=receipt['outcome'],
        worker_cpu_ns=receipt['resource_usage']['total_cpu_ns'],charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],
        budget_settled=True,complete_model=False,completed_stage_count=len(stages),stage_count=24,
        last_certified_stage=stages[-1]['stage_id'],source_records_replayed=len(replayed),stage_progress=stages,
        quality_evaluation=False,confirmation=False,acl_ready=False,
        progress_scope='Partial progress copied and internally checked; source records and stage codes were not independently reexecuted. No full model or final byte audit exists.')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory');parser.add_argument('accounting');parser.add_argument('output')
    args=parser.parse_args();result=inspect(args.directory,args.accounting)
    with Path(args.output).open('xb') as stream:stream.write(canonical_json(result))
    print(result['status'])
