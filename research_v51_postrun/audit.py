"""Verify copied actual artifacts, terminal seals, accounting and complete codes."""
import argparse
from pathlib import Path
from research_v48.report import read, sha, require, verify_file, scheduler_status
from research_v51.campaign import ORDER, TRIALS, CAPS, COMMON
from research_v51.stage import STAGE_ID, HISTORICAL_CODE
from src.experiment_inventory import source_hashes
from src.phase_budget import read_budget_snapshot
from src.run_store import canonical_json, read_completed, digest

ROOT=Path(__file__).resolve().parents[1]
PROGRAM='af83f983447e022a5e5b386ddf60eb62db804db57dbd652212eab51fe9b7d10b'


def inspect(directory,accounting):
    d=Path(directory).resolve();p=read(d/'program.json');ph=sha(d/'program.json')
    require(ph==PROGRAM==read(d/'registration.json')['program_sha256'],'Frozen registration differs')
    require(p['source_commit']=='2c1a2bc699e4633bdab7243bb9e042be2f884c83' and
        p['order']==list(ORDER) and p['trials']==TRIALS and p['caps']==CAPS and
        p['common_limits']==COMMON,'Frozen design differs')
    for name,h in p['sources'].items():require(sha(ROOT/name)==h,'Frozen source changed: '+name)
    remote=Path(p['directory']);remote_repo=remote.parents[1]
    for entry in p['inputs'].values():
        local=ROOT/Path(entry['path']).relative_to(remote_repo)
        verify_file(local,entry)
    checks=read(ROOT/Path(p['inputs']['checks']['path']).relative_to(remote_repo))
    require(checks['status']=='passed' and checks['tests']==10 and checks['skipped']==0 and
        checks['sources']==p['sources'] and checks['runtime']==p['runtime'],'Software checks differ')
    jobs=scheduler_status(Path(accounting).read_text(),{'13275':'software','13276':'stage_gate'})
    require(jobs['status'] in ('all_completed','terminal_failure_observed') and
        not jobs['missing_jobs'],'Gate is not terminal; numerical outcome remains unverified')
    require(jobs['jobs']['13275']['state']=='COMPLETED' and jobs['jobs']['13275']['exit_code']=='0:0',
        'Software allocation failed')
    snap=read_budget_snapshot(d/'budget',identity=dict(protocol_sha256=ph,source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds=CAPS)
    require(snap['status']=='verified' and snap['reserved_unknown_attempts']==0 and
        not any(snap['over_cap'].values()),'Unsettled or over-cap gate')
    receipts={};measurements={};failure=None;artifacts=0;seen_attempts={}
    for trial in ORDER:
        root=d/trial
        if failure is not None:
            require(not root.exists(),'A trial ran after gate failure')
            continue
        require(root.is_dir(),'Missing planned trial before terminal outcome')
        identity=read(root/'worker/identity.json');receipt=read_completed(root/'worker',identity)
        require(receipt is not None and receipt==read(root/'worker'/receipt['attempt']/'status.json'),
            'Missing or inconsistent terminal seal')
        require(identity['identity']==dict(program_sha256=ph,trial=trial) and
            identity['cwd']==str(remote_repo) and identity['command'][1:]==
            ['-B','-m','research_v51.worker',str(remote),trial],'Worker identity differs')
        limits=dict(**TRIALS[trial],**COMMON)
        require(all(identity['limits'][k]==v for k,v in limits.items()),'Worker limits differ')
        require(identity['phase_budget']==dict(directory=str(remote/'budget'),phase=trial,
            binding_sha256=snap['binding_sha256']),'Phase binding differs')
        tx=read(root/'transaction.json')
        require(tx['slurm_job_id']=='13276' and tx['worker_outcome']==receipt['outcome'],'Transaction differs')
        debit=receipt['budget_debit'];attempt=receipt['budget_attempt_id']
        require(snap['attempts'][attempt]==debit and debit['state']=='settled' and
            debit['phase']==trial and debit['observed_cpu_ns']==receipt['resource_usage']['total_cpu_ns'],
            'CPU charge differs')
        seen_attempts[attempt]=debit;receipts[trial]=receipt
        completion=root/'outputs/completion.json'
        if receipt['outcome']['status']!='complete':
            failure=dict(trial=trial,outcome=receipt['outcome'],charged_cpu_seconds=debit['charged_cpu_seconds'])
            if completion.exists():
                c=read(completion)
                require(c['status']=='failed' and c['program_sha256']==ph,'Failure completion differs')
                failure['worker_error']=c.get('error')
            continue
        require(receipt['outcome']['returncode']==0,'Nonzero successful worker')
        c=read(completion)
        require(c['status']=='complete' and c['program_sha256']==ph and c['trial']==trial and
            c['complete_model'] is False and c['quality_evaluation'] is False,'Completion scope differs')
        for name,entry in c['artifacts'].items():
            require(Path(name).name==name,'Unsafe artifact path');verify_file(root/'outputs'/name,entry);artifacts+=1
        measurements[trial]=dict(measurement=c['measurement'],worker_elapsed_seconds=c['worker_elapsed_ns']/1e9,
            max_rss_kib=c['max_rss_kib'],charged_cpu_seconds=debit['charged_cpu_seconds'],
            controller_elapsed_seconds=tx['elapsed_ns']/1e9)
    require(seen_attempts==snap['attempts'],'Unexpected or missing ledger attempt')
    result=dict(schema='copied-real-wide-stage-audit-v51',program_sha256=ph,frozen_sources_verified=len(p['sources']),
        scheduler=jobs,accounting_sha256=sha(accounting),budget=snap,measurements=measurements,
        artifacts_rehashed=artifacts,complete_model=False,quality_evaluation=False,confirmation=False,
        acl_ready=False,independent_numerical_reexecution=False)
    if failure:
        require(jobs['status']=='terminal_failure_observed' and not (d/'gate.json').exists(),
            'Failure conflicts with success artifact')
        result.update(status='verified_terminal_stage_failure',failure=failure)
    else:
        require(jobs['status']=='all_completed','Slurm failed after workers; needs separate review')
        gate=read(d/'gate.json')
        require(gate['status']=='passed' and gate['program_sha256']==ph and gate['code_count']==2359296,
            'Gate completion differs')
        for name in ORDER:
            require(gate['trials'][name]['completion_sha256']==sha(d/name/'outputs/completion.json') and
                gate['trials'][name]['transaction_sha256']==sha(d/name/'transaction.json'),'Gate links differ')
        actual={name:(d/name/'outputs/codes.bin').read_bytes() for name in ORDER[1:]}
        require(all(len(b)==1179648 and b==actual['reference'] and digest(b)==HISTORICAL_CODE for b in actual.values()),
            'Full packed stage bytes differ')
        manifest=read(d/'prepare/outputs/inputs.json');records=manifest['records']
        require([r['record_id'] for r in records]==[r['id'] for r in p['records']] and
            manifest['normalization']==1664 and manifest['total_tokens']==1664 and
            manifest['stage_id']==STAGE_ID and [r['full_traversal_compared'] for r in records]==[True]+[False]*12,
            'Prepared source extent differs')
        for name in ORDER[1:]:
            m=measurements[name]['measurement']
            require(m['code_sha256']==HISTORICAL_CODE and m['code_count']==2359296 and
                m['source_manifest_sha256']==sha(d/'prepare/outputs/inputs.json') and
                m['route']=='streamed' and m['point_retry'] is False,'Stage result binding differs')
            if name!='reference':
                from research_v50.neighbors import source
                require(m['backend']['source_sha256']==digest(source().encode()) and
                    m['backend']['backend']=='normal_neighbor_primal_v50','Candidate kernel differs')
        result.update(status='verified_complete_real_stage',all_three_actual_code_blobs_equal=True,
            historical_code_commitment_matches=True,historical_code_bytes_available=False,
            complete_stage_codes=2359296,
            scope='Single known development stage. Historical comparison is hash-only; fresh three-way comparison uses actual complete bytes. Fixed order, no population speedup or full-model runtime extrapolation.')
    result['inputs']={str(f.relative_to(d)):dict(bytes=f.stat().st_size,sha256=sha(f))
        for f in sorted(d.rglob('*')) if f.is_file() and not f.name.endswith('.lock')}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('accounting');parser.add_argument('output')
    args=parser.parse_args();result=inspect(args.directory,args.accounting)
    with Path(args.output).open('xb') as stream:stream.write(canonical_json(result))
    print(result['status'])
