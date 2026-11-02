"""Verify copied synthetic-profile receipts and an optional local V47 array backup."""
import argparse
from pathlib import Path
from research_v48.report import read,require,sha,scheduler_status
from src.run_store import read_completed,canonical_json
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes

ROOT=Path(__file__).resolve().parents[1]
PROGRAM='5235ba0681eb220f03b72c84a57e8070a7bdd36484d8dccd8472bea807f6de9b'


def profile(directory,accounting):
    d=Path(directory).resolve();p=read(d/'program.json');ph=sha(d/'program.json')
    require(ph==PROGRAM==read(d/'registration.json')['program_sha256'],'Profile identity differs')
    for name,value in p['sources'].items():require(sha(ROOT/name)==value,'Frozen source differs: '+name)
    remote=Path(p['directory']);repo=remote.parents[1]
    for entry in p['inputs'].values():
        rel=Path(entry['path']).relative_to(repo);require(sha(ROOT/rel)==entry['sha256'],'Preserved failure changed')
    jobs=scheduler_status(Path(accounting).read_text(),{'13265':'software_tests','13266':'registration','13267':'profile'})
    require(jobs['status']=='all_completed','Software profile jobs did not all complete successfully')
    identity=read(d/'worker/identity.json');receipt=read_completed(d/'worker',identity)
    require(receipt is not None and receipt['outcome']['status']=='complete' and receipt['outcome']['returncode']==0,
        'Profile worker did not finish')
    require(identity['identity']==dict(program_sha256=ph) and identity['cwd']==str(repo)
        and identity['command'][1:]==['-B','-m','research_v49.campaign','worker',str(remote)],'Worker identity differs')
    require(all(identity['limits'][k]==v for k,v in p['limits'].items()),'Profile limits differ')
    require(read(d/'worker'/receipt['attempt']/'status.json')==receipt,'Terminal seal differs')
    tx=read(d/'transaction.json');require(tx['slurm_job_id']=='13267' and tx['worker_outcome']==receipt['outcome'],
        'Profile transaction differs')
    snapshot=read_budget_snapshot(d/'budget',identity=dict(protocol_sha256=ph,source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'software_profile':602})
    require(snapshot['status']=='verified' and snapshot['reserved_unknown_attempts']==0 and not any(snapshot['over_cap'].values())
        and snapshot['attempts']=={receipt['budget_attempt_id']:receipt['budget_debit']},'Profile ledger differs or is unsettled')
    require(snapshot['binding_sha256']==identity['phase_budget']['binding_sha256']
        and receipt['budget_debit']['observed_cpu_ns']==receipt['resource_usage']['total_cpu_ns'],'CPU charge binding differs')
    c=read(d/'outputs/completion.json')
    require(c['status']=='complete' and c['program_sha256']==ph and len(c['cases'])==3,'Profile completion differs')
    require([r['width'] for r in c['cases']]==[192,768,1536],'Fixed case order differs')
    rows=[]
    for i,r in enumerate(c['cases']):
        require(r['weights_sha256']==p['fixture_hashes'][str(r['width'])]['weights']
            and r['features_sha256']==p['fixture_hashes'][str(r['width'])]['features']
            and r['rows']==4 and r['tokens']==128 and r['status']=='certified','Synthetic fixture binding differs')
        require(read(d/f'outputs/progress-{2*i+1:04d}.json')==dict(phase='case_complete',**r),
            'Completed case and progress disagree')
        a=r['diagnostics'];row=a['rows']
        require(all(type(a[k]) is int and a[k]>=0 for k in ('gram_elapsed_ns','coefficient_elapsed_ns','total_elapsed_ns')),
            'Invalid component times')
        require(row['native_certified_rows']+row['fallback_rows']==4,'Incomplete row certification')
        require(sum(a[k] for k in ('gram_elapsed_ns','coefficient_elapsed_ns'))+row['row_elapsed_ns']<=r['elapsed_ns'],
            'Component times exceed complete case time')
        rows.append(dict(width=r['width'],rows=4,tokens=128,elapsed_seconds=r['elapsed_ns']/1e9,
            gram_seconds=a['gram_elapsed_ns']/1e9,coefficient_seconds=a['coefficient_elapsed_ns']/1e9,
            row_seconds=row['row_elapsed_ns']/1e9,coefficient_fraction=a['coefficient_elapsed_ns']/r['elapsed_ns'],
            fallback_rows=row['fallback_rows'],code_sha256=r['code_sha256']))
    inputs={str(f.relative_to(d)):dict(bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(d.rglob('*')) if f.is_file()}
    return dict(schema='copied-synthetic-profile-audit-v49',status='verified_copied_profile',program_sha256=ph,
        inputs=inputs,scheduler=jobs,accounting_sha256=sha(accounting),frozen_sources_verified=len(p['sources']),
        charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],cases=rows,
        empirical_model_inference=False,independent_numerical_reproduction=False,quality_evaluation=False,
        complete_model=False,confirmation=False,acl_ready=False,
        scope='Synthetic component timing only; no extrapolated full-model runtime or scientific speedup.')


def gpu_backup(directory):
    from research_v47.snapshot import load_snapshot
    d=Path(directory);p=read(d/'completion.json')
    require(p['status']=='complete' and p['program_sha256']=='1803adfd4b9548a605dc468a7c982d077abaaa43f36df6bfce8c4098a7170915',
        'Original parameter export differs')
    require(p['artifacts']['parameters.npz']['sha256']=='c5cc19cde2e526bb3098efaec5c7709ac3714bd781f8753c1c5b77f6c4a67f2b'
        and p['artifacts']['parameters.npz']['bytes']==964501350
        and p['artifacts']['manifest.json']['sha256']=='8e4c3e790b7c1747f6fe114899240c6f14c10b8111f9d7df9f2a41d64e6f5d9d',
        'Historical archive commitments differ')
    for name,entry in p['artifacts'].items():
        f=d/'outputs'/name
        require(f.stat().st_size==entry['bytes'] and sha(f)==entry['sha256'],'Copied GPU archive changed')
    manifest=read(d/'outputs/manifest.json');evaluator=load_snapshot(d/'outputs/manifest.json',d/'outputs/parameters.npz')
    require(len(manifest['arrays'])==78 and len(evaluator.weights)==24 and len(evaluator.blocks)==6,
        'Loaded parameter extent differs')
    return dict(schema='local-gpu-array-backup-audit-v49',status='verified_all_parameter_words',
        archive_bytes=p['artifacts']['parameters.npz']['bytes'],archive_sha256=p['artifacts']['parameters.npz']['sha256'],
        manifest_sha256=p['artifacts']['manifest.json']['sha256'],array_count=78,model_inference=False,
        gpu_execution=False,scope='Rehashed complete original NPZ and validated every stored binary64 parameter array locally; no new likelihood evaluation.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('profile','gpu_backup'))
    parser.add_argument('directory');parser.add_argument('output');parser.add_argument('--accounting')
    args=parser.parse_args()
    result=profile(args.directory,args.accounting) if args.mode=='profile' else gpu_backup(args.directory)
    with Path(args.output).open('xb') as stream:stream.write(canonical_json(result))
    print(result['status'])
