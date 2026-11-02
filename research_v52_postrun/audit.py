"""Audit either a complete48-bit stage or a preserved failure; never infer success."""
import argparse
from pathlib import Path
from research_v48.report import read,sha,require,verify_file,scheduler_status
from research_v52.campaign import ROOT,LIMITS,CAPS
from research_v52.evidence import validate_v51
from research_v51.stage import HISTORICAL_CODE
from src.experiment_inventory import source_hashes
from src.phase_budget import read_budget_snapshot
from src.run_store import digest,read_completed,canonical_json

PROGRAM='f22f6667500b4205107929bd4607c00730ed4df61db1ac13f7f87137a5838ec0'
SOURCE='6b70d703a716cef744f49ba1c55add3a691c3267'


def inspect(directory,accounting):
    d=Path(directory).resolve();p=read(d/'program.json');ph=sha(d/'program.json')
    require(ph==PROGRAM==read(d/'registration.json')['program_sha256'] and
        p['source_commit']==SOURCE and p['precision']==48 and p['limits']==LIMITS and p['caps']==CAPS,
        'Frozen V52 design differs')
    for name,h in p['sources'].items():require(sha(ROOT/name)==h,'Frozen source differs: '+name)
    remote=Path(p['directory']);repo=remote.parents[1]
    for entry in p['inputs'].values():verify_file(ROOT/Path(entry['path']).relative_to(repo),entry)
    evidence=validate_v51();require(evidence==p['v51_evidence'],'Prior point pair or failure evidence changed')
    jobs=scheduler_status(Path(accounting).read_text(),{'13290':'software','13291':'precision48'})
    require(not jobs['missing_jobs'] and jobs['status'] in ('all_completed','terminal_failure_observed'),
        'V52 is not terminal; numerical outcome remains unverified')
    require(jobs['jobs']['13290']['state']=='COMPLETED' and jobs['jobs']['13290']['exit_code']=='0:0',
        'Software allocation did not pass')
    checks=read(ROOT/'local_runs/continuation-v52-20261011/checks.json')
    require(checks['status']=='passed' and checks['tests']==4 and checks['skipped']==0 and
        checks['sources']==p['sources'] and checks['runtime']==p['runtime'],'Software binding differs')
    identity=read(d/'worker/identity.json');receipt=read_completed(d/'worker',identity)
    require(receipt is not None and receipt==read(d/'worker'/receipt['attempt']/'status.json'),
        'Missing terminal seal')
    require(identity['identity']==dict(program_sha256=ph) and identity['cwd']==str(repo) and
        identity['command'][1:]==['-B','-m','research_v52.worker',str(remote)] and
        all(identity['limits'][k]==v for k,v in LIMITS.items()),'Worker binding/limits differ')
    snapshot=read_budget_snapshot(d/'budget',identity=dict(protocol_sha256=ph,source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds=CAPS)
    require(snapshot['status']=='verified' and snapshot['reserved_unknown_attempts']==0 and
        not any(snapshot['over_cap'].values()) and
        snapshot['attempts']=={receipt['budget_attempt_id']:receipt['budget_debit']} and
        receipt['budget_debit']['observed_cpu_ns']==receipt['resource_usage']['total_cpu_ns'],
        'CPU phase is not correctly settled')
    require(identity['phase_budget']==dict(directory=str(remote/'budget'),phase='precision48',
        binding_sha256=snapshot['binding_sha256']),'Worker phase differs')
    tx=read(d/'transaction.json')
    require(tx['slurm_job_id']=='13291' and tx['worker_outcome']==receipt['outcome'],'Transaction differs')
    result=dict(schema='copied-precision48-stage-audit-v52',program_sha256=ph,source_commit=SOURCE,
        frozen_source_hashes_verified=len(p['sources']),bound_inputs_rehashed=len(p['inputs']),
        scheduler=jobs,accounting_sha256=sha(accounting),worker_outcome=receipt['outcome'],budget=snapshot,
        charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],prior_v51_evidence=evidence,
        prior_preparation_reused=True,prior_preparation_charge=430,prior_v51_total_charge=2834,
        complete_model=False,quality_evaluation=False,confirmation=False,acl_ready=False,
        adaptive_development=True,independent_numerical_reexecution=False)
    path=d/'outputs/completion.json'
    if path.exists():
        c=read(path)
        require(c['program_sha256']==ph and c['slurm_job_id']=='13291' and
            c['complete_model'] is False and c['quality_evaluation'] is False and
            c['source_neural_traversals']==0 and c['point_retry'] is False,'Worker scope differs')
        for name,entry in c['artifacts'].items():
            require(Path(name).name==name,'Unsafe artifact path');verify_file(d/'outputs'/name,entry)
        result.update(artifacts_rehashed=len(c['artifacts']),worker_elapsed_seconds=c['worker_elapsed_ns']/1e9,
            peak_rss_kib=c['max_rss_kib'])
        if 'feature_descriptor_bytes' in c:
            size=sum(v['bytes'] for name,v in c['artifacts'].items() if name.startswith('compressed48-'))
            require(c['feature_descriptor_bytes']==size,'Storage total differs')
            result.update(feature_descriptor_bytes=size,
                feature_saving_vs_v51_lossless=1-size/evidence['feature_descriptor_bytes']['lossless'],
                encoding_and_containment_seconds=c['encoding_and_containment_ns']/1e9)
    if receipt['outcome']['status']=='complete':
        require(jobs['status']=='all_completed' and receipt['outcome']['returncode']==0 and
            path.exists() and c['status']=='complete','Inconsistent successful outcome')
        names={f'compressed48-{i:02d}.bin' for i in range(13)}|{'codes.bin'}
        require(set(c['artifacts'])==names and c['code_count']==2359296 and
            c['actual_point_code_bytes_equal'] is True and c['code_sha256']==HISTORICAL_CODE,
            'Incomplete output or wrong commitment')
        prior=ROOT/'local_runs/real-wide-stage-v51-20261011-a'
        blob=(d/'outputs/codes.bin').read_bytes()
        require(len(blob)==1179648 and digest(blob)==HISTORICAL_CODE and
            blob==(prior/'candidate/outputs/codes.bin').read_bytes()==(prior/'reference/outputs/codes.bin').read_bytes(),
            'Actual complete point/box bytes differ')
        require(c['source_manifest_sha256']==sha(prior/'prepare/outputs/inputs.json'),'Source manifest differs')
        from research_v50.neighbors import source
        require(c['backend']['source_sha256']==digest(source().encode()) and
            c['diagnostics']['diagnostics']['coefficient_build']['source_sha256']==digest(source().encode()),
            'Shared kernel differs')
        rows=c['diagnostics']['diagnostics']['rows']
        require(rows['native_certified_rows']+rows['fallback_rows']==768,'Incomplete row verification')
        result.update(status='verified_precision48_complete_stage',actual_complete_code_bytes_equal=True,
            complete_stage_codes=2359296,solve_and_write_seconds=c['solve_and_write_elapsed_ns']/1e9,
            native_certified_rows=rows['native_certified_rows'],interval_fallback_rows=rows['fallback_rows'],
            max_coefficient_radius=rows['max_euclidean_coefficient_radius'])
    else:
        require(jobs['status']=='terminal_failure_observed' and not (d/'outputs/codes.bin').exists(),
            'Failed worker conflicts with successful artifact')
        if path.exists():require(c['status']=='failed','Failure completion differs')
        result.update(status='verified_precision48_failure',error=c.get('error') if path.exists() else None,
            refusal_diagnostics=c.get('refusal_diagnostics') if path.exists() else None)
    result['scope']='One adaptively selected precision on a known development stage. Feature-descriptor storage only; prepared-input timing excludes previously charged neural preparation. No full-model state/deletion/quality/confirmation result.'
    result['inputs']={str(f.relative_to(d)):dict(bytes=f.stat().st_size,sha256=sha(f))
        for f in sorted(d.rglob('*')) if f.is_file() and not f.name.endswith('.lock')}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('accounting');parser.add_argument('output')
    args=parser.parse_args();r=inspect(args.directory,args.accounting)
    with Path(args.output).open('xb') as stream:stream.write(canonical_json(r))
    print(r['status'])
