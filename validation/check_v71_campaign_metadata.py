"""Saved-seal/cost and terminal-receipt review, without model or likelihood execution."""
from pathlib import Path
import hashlib,json,re,sys,tarfile,tempfile
from src.run_store import strict_json
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes
from research_v71 import campaign as campaign,cost_accounting as costs,closure
R=Path(__file__).resolve().parents[1]
TEMP=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/work')
REG='3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
PHASES=[*campaign.ORDER,'closure']
JOBS={phase:str(15405+i) for i,phase in enumerate(PHASES)}
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(path):
    with tarfile.open(path) as t:
        members=t.getmembers()
        assert len(members)<350 and len({m.name for m in members})==len(members)
        assert all(m.isfile() and m.size<4*2**20 and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        assert sum(m.size for m in members)<32*2**20
        return {m.name:t.extractfile(m).read() for m in members}
def check(files):
    c=strict_json(files['collection.json']);p=strict_json(files['program.json'])
    assert files['program.json']==(R/'handoff/registration_v71_quality.json').read_bytes()
    assert info(files['program.json'])['sha256']==c['registration_sha256']==REG and c['jobs']==JOBS
    assert c['files']=={n:info(b) for n,b in files.items() if n!='collection.json'}
    assert c['completed_worker_seal_artifacts_included'] is True and c['model_or_corpus_bytes_collected'] is False
    for name,e in p['new_sources'].items():assert info(files[str(Path(name).relative_to(p['directory']))])==e
    rows={}
    for line in c['accounting'].splitlines():
        row=line.split('|');assert len(row)==6 and row[0].split('.')[0] in JOBS.values()
        if '.' not in row[0]:assert row[0] not in rows;rows[row[0]]=row
    assert set(rows)==set(JOBS.values())
    statuses={phase:rows[job][1] for phase,job in JOBS.items()}
    result=dict(schema='v71-saved-campaign-metadata-review',observed_at_utc=c['captured_at_utc'],
        registration_sha256=REG,jobs=JOBS,job_states=statuses,status='pending_terminal',
        completed_phase_costs={},quality_guard_pass=None,terminal_quality_result_verified=False,
        model_state_bytes_checked_locally=False,likelihood_reexecuted=False,
        shared_accounting_code=True,independent_numerical_validation=False)
    ledger=strict_json(files['budget/ledger.json'])
    assert ledger['binding']['identity']==dict(protocol_sha256=REG,source_sha256=source_hashes(R))
    assert ledger['binding']['phase_cpu_seconds']=={'quality':39616}
    with tempfile.TemporaryDirectory(prefix='v71-receipt-review-',dir=TEMP) as temp:
        root=Path(temp).resolve()
        for name,b in files.items():
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
        snapshot=read_budget_snapshot(root/'budget',identity=ledger['binding']['identity'],phase_cpu_seconds={'quality':39616},max_attempts=8)
        active=[k for k,v in snapshot['attempts'].items() if v['state']=='reserved'];assert len(active)<=1
        for phase in campaign.ORDER:
            job=JOBS[phase];binding=strict_json(files[phase+'/job-binding.json'])
            assert binding['registration_sha256']==REG and binding['phase']==phase and binding['job_id']==job
            if statuses[phase]!='COMPLETED':continue
            entry=strict_json(files[phase+'/entry.json']);complete=strict_json(files[phase+'/outputs/completion.json'])
            identity=campaign.worker_identity(p,phase,entry['affinity_cpus'][0],snapshot)
            checked=costs.worker(root/phase/'worker',identity,snapshot,active_attempt_id=active[0] if active else None)
            raw='\n'.join(line for line in c['accounting'].splitlines() if line.split('|')[0].split('.')[0]==job)
            scheduler=costs.scheduler_rows(raw,{phase:job})[phase]
            row=costs.reconcile(phase,entry,checked,scheduler,registration_sha256=REG)
            assert row['execution_successful'] and entry['outputs']['completion.json']==info(files[phase+'/outputs/completion.json'])
            assert complete['schema']=='quality-phase-worker-v71' and complete['registration_sha256']==REG
            assert complete['job_id']==job and complete['phase']==phase and complete['status']=='complete' and complete['error'] is None
            result['completed_phase_costs'][phase]=row
        result['active_worker_reservations']={k:snapshot['attempts'][k] for k in active}
        result['settled_worker_cpu_seconds']=sum(v['charged_cpu_seconds'] for v in snapshot['attempts'].values() if v['state']=='settled')
        result['actual_completed_worker_seals_checked_locally']=len(result['completed_phase_costs'])
        result['sequential_progress_counts']={phase:len([n for n in files if re.fullmatch(phase+r'/outputs/construction/progress-\d{4}\.json',n)]) for phase in ['sequential_12','sequential_6']}
        if any(s not in {'RUNNING','PENDING','COMPLETED','CONFIGURING','COMPLETING'} for s in statuses.values()):
            result['status']='failed_or_cancelled_campaign_preserved'
        if not all(s=='COMPLETED' for s in statuses.values()):return result
        accounting=costs.complete(result['completed_phase_costs'],snapshot)
        receipt=strict_json(files['closure/receipt.json']);assert receipt['result']['accounting']==accounting
        assert receipt['result']['ledger']==info(files['budget/ledger.json'])
        assert receipt['result']['phases']=={phase:info(files[phase+'/outputs/completion.json']) for phase in campaign.ORDER}
        terminal=strict_json(files['terminal/outputs/completion.json'])['result']
        assert terminal['status']=='verified_actual_artifacts' and terminal['sequential_actual_saved_codes_reaudited'] is True
        assert terminal['actual_checkpoint_parameter_audit']['actual_checkpoint_reference_compared'] is True
        loss=terminal['loss_audit'];assert loss['status']=='verified' and loss['actual_loss_files_compared']==1920
        assert loss['actual_cpu_reference_audit']['actual_loss_files_compared']==24 and loss['statistics_recomputed'] is True
        assert type(terminal['quality_guard_pass']) is bool and terminal['quality_guard_pass']==loss['all_endpoint_gates_pass']==receipt['result']['quality_guard_pass']
        raw='\n'.join(line for line in c['accounting'].splitlines() if line.split('|')[0].split('.')[0]==JOBS['closure'])
        observed=closure.verify_observer(receipt,raw,registration_sha256=REG,closure_job=JOBS['closure'])
        assert observed['all_registered_execution_succeeded'] and observed['actual_artifacts_verified']
        result.update(status='verified_terminal_receipt_metadata',terminal_quality_result_verified=True,
            quality_guard_pass=terminal['quality_guard_pass'],complete_registered_costs=observed,
            scope='Completed cluster model/loss audits and all costs are reconciled; omitted model and loss bodies were not recomputed locally. Root review is not independent numerical validation.')
        return result
if __name__=='__main__':
    source=R/'campaigns'/sys.argv[1];result=check(load(source));result['archive']=info(source.read_bytes())
    with (R/'validation'/sys.argv[2]).open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ['status','observed_at_utc','actual_completed_worker_seals_checked_locally','settled_worker_cpu_seconds','sequential_progress_counts','terminal_quality_result_verified']}))
