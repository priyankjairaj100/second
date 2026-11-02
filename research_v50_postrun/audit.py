"""Verify copied synthetic-profile receipts and an optional local V47 array backup."""
import argparse
from pathlib import Path
from research_v48.report import read,require,sha,scheduler_status
from src.run_store import read_completed,canonical_json
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes

ROOT=Path(__file__).resolve().parents[1]
PROGRAM='8b732267fefab478296300837f26e475782c780afdfe2e15104633c9d7d3db95'


def profile(directory,accounting):
    d=Path(directory).resolve();p=read(d/'program.json');ph=sha(d/'program.json')
    require(ph==PROGRAM==read(d/'registration.json')['program_sha256'],'Profile identity differs')
    for name,value in p['sources'].items():require(sha(ROOT/name)==value,'Frozen source differs: '+name)
    remote=Path(p['directory']);repo=remote.parents[1]
    for entry in p['inputs'].values():
        rel=Path(entry['path']).relative_to(repo);require(sha(ROOT/rel)==entry['sha256'],'Preserved failure changed')
    jobs=scheduler_status(Path(accounting).read_text(),{'13268':'software_tests','13269':'registration','13270':'profile'})
    require(jobs['status']=='all_completed','Software profile jobs did not all complete successfully')
    identity=read(d/'worker/identity.json');receipt=read_completed(d/'worker',identity)
    require(receipt is not None and receipt['outcome']['status']=='complete' and receipt['outcome']['returncode']==0,
        'Profile worker did not finish')
    require(identity['identity']==dict(program_sha256=ph) and identity['cwd']==str(repo)
        and identity['command'][1:]==['-B','-m','research_v50.campaign','worker',str(remote)],'Worker identity differs')
    require(all(identity['limits'][k]==v for k,v in p['limits'].items()),'Profile limits differ')
    require(read(d/'worker'/receipt['attempt']/'status.json')==receipt,'Terminal seal differs')
    tx=read(d/'transaction.json');require(tx['slurm_job_id']=='13270' and tx['worker_outcome']==receipt['outcome'],
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
    return dict(schema='copied-synthetic-profile-audit-v50',status='verified_copied_profile',program_sha256=ph,
        inputs=inputs,scheduler=jobs,accounting_sha256=sha(accounting),frozen_sources_verified=len(p['sources']),
        charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],cases=rows,
        empirical_model_inference=False,independent_numerical_reproduction=False,quality_evaluation=False,
        complete_model=False,confirmation=False,acl_ready=False,
        scope='Synthetic component timing only; no extrapolated full-model runtime or scientific speedup.')



def compare(directory,accounting):
    result=profile(directory,accounting)
    from research_v50.neighbors import source
    import hashlib
    baseline=read(ROOT/'validation/v49_profile_audit.json')
    require(baseline['program_sha256']=='5235ba0681eb220f03b72c84a57e8070a7bdd36484d8dccd8472bea807f6de9b'
        and baseline['status']=='verified_copied_profile','Audited baseline differs')
    completion=read(Path(directory)/'outputs/completion.json')
    source_hash=hashlib.sha256(source().encode()).hexdigest()
    for r in completion['cases']:
        build=r['diagnostics']['coefficient_build']
        require(build['source_sha256']==source_hash and build['backend']=='normal_neighbor_primal_v50',
            'Modified kernel identity differs')
    comparisons=[]
    for old,new in zip(baseline['cases'],result['cases']):
        require(all(old[k]==new[k] for k in ('width','rows','tokens','code_sha256')),'Synthetic code or workload differs')
        comparisons.append(dict(width=new['width'],codes_match=True,
            baseline_seconds=old['elapsed_seconds'],candidate_seconds=new['elapsed_seconds'],
            candidate_over_baseline_case_time=new['elapsed_seconds']/old['elapsed_seconds'],
            baseline_coefficient_seconds=old['coefficient_seconds'],candidate_coefficient_seconds=new['coefficient_seconds'],
            candidate_over_baseline_coefficient_time=new['coefficient_seconds']/old['coefficient_seconds']))
    result.update(comparisons=comparisons,baseline_audit_sha256=sha(ROOT/'validation/v49_profile_audit.json'),
        modified_c_source_sha256=source_hash,
        comparison_scope='Fixed synthetic engineering observations, earlier baseline and later candidate, uncontrolled cache/time effects. First-case compilation placement differs; complete worker charges include setup. No confidence interval or complete-model speedup.')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('accounting');parser.add_argument('output')
    args=parser.parse_args();result=compare(args.directory,args.accounting)
    with Path(args.output).open('xb') as stream:stream.write(canonical_json(result))
    print(result['status'])
