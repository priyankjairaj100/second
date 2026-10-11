"""Verify copied cold-run receipts; never infer actual model/state equality."""
from pathlib import Path
import datetime,json,sys
repo=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repo))
from src.run_store import read_completed,strict_json,digest,canonical_json
base=Path(sys.argv[1]).resolve(strict=True)
read=lambda name:strict_json((base/name).read_bytes())
manifest=json.loads((base/'collection-manifest.json').read_bytes())
for name,entry in manifest['files'].items():
 blob=(base/name).read_bytes()
 assert entry==dict(bytes=len(blob),sha256=digest(blob))
program=read('program.json');ph=digest((base/'program.json').read_bytes())
assert ph=='03a6181b0d32ad023706145fbde28f202ed5d137e95a4b16ecbd19686858465b'
assert read('registration.json')['program_sha256']==ph
assert all(digest((repo/name).read_bytes())==value for name,value in program['sources'].items())
identity=read('cold/worker/identity.json');sealed=read_completed(base/'cold/worker',identity)
transaction=read('cold/transaction.json');completion=read('cold/outputs/completion.json')
remote=program['directory'];root=remote.split('/local_runs/')[0]
assert identity['identity']==dict(campaign_sha256=ph,trial='cold') and identity['cwd']==root
assert identity['command']==[root+'/.venv-container/bin/python','-B','-m','research_v54.worker',remote+'/cold/plan.json']
limits=identity['limits']
assert all(limits[k]==v for k,v in program['trials']['cold'].items())
assert limits['threads']==1 and len(limits['affinity_cpus'])==1
assert limits['address_space_bytes']==program['process_address_space_bytes'] and limits['file_size_bytes']==program['file_size_bytes']
assert sealed is not None and sealed==read('cold/worker/'+sealed['attempt']+'/status.json')
assert sealed['outcome']==transaction['worker_outcome'] and sealed['outcome']['status']=='complete' and sealed['outcome']['returncode']==0
assert read('cold/plan.json')==dict(trial='cold',program=remote+'/program.json',program_sha256=ph,output=remote+'/cold/outputs',slurm_job_id='13312')
ledger=read('budget/ledger.json');bid=sealed['budget_attempt_id'];debit=sealed['budget_debit']
assert ledger['attempts'][bid]==debit==transaction['budget']['attempts'][bid]
assert debit['state']=='settled' and sealed['resource_usage']['total_cpu_ns']==debit['observed_cpu_ns']
assert debit['charged_cpu_seconds']==max(1,(debit['observed_cpu_ns']+999999999)//1000000000)
binding=digest(canonical_json(ledger['binding']))
assert ledger['binding']['identity']['protocol_sha256']==ph
assert ledger['binding']['phase_cpu_seconds']=={'feasibility':program['phase_cpu_seconds']}
assert identity['phase_budget']==dict(binding_sha256=binding,directory=remote+'/budget',phase='feasibility')
attempt='cold/worker/'+sealed['attempt']+'/'
request=read(attempt+'request.json');applied=read(attempt+'limits-applied.json')
reservation=read(attempt+'budget-reservation.json');observed=read(attempt+'pre-settlement-observation.json')
assert request['command']==identity['command'] and request['cwd']==identity['cwd'] and request['limits']==limits
assert applied['request_sha256']==digest((base/attempt/'request.json').read_bytes())
assert applied['cpu_seconds']==[limits['cpu_seconds'],limits['cpu_seconds']+1]
assert applied['address_space']==[limits['address_space_bytes']]*2 and applied['file_size']==[limits['file_size_bytes']]*2
assert applied['affinity_cpus']==limits['affinity_cpus'] and all(v=='1' for v in applied['thread_environment'].values())
assert reservation['binding_sha256']==binding and reservation['budget_attempt_id']==bid
assert reservation['budget_debit']==dict(phase='feasibility',state='reserved',observed_cpu_ns=None,
 reserved_cpu_seconds=debit['reserved_cpu_seconds'],charged_cpu_seconds=debit['reserved_cpu_seconds'])
assert observed['budget_attempt_id']==bid and observed['resource_usage']==sealed['resource_usage'] and observed['outcome']==sealed['outcome']
assert completion['program_sha256']==ph and completion['source_sha256']==program['sources']
assert completion['status']=='complete' and completion['complete_model'] and completion['slurm_job_id']=='13312'
assert completion['schema']=='complete-service-worker-v54' and completion['trial']=='cold'
assert len(completion['steps'])==2
steps=[]
for number,row in enumerate(completion['steps'],1):
 count=program['retained_counts'][number-1]
 assert row['step']==number and row['retained_ids']==program['deletion_order'][-count:]
 assert row['timing']['neural_stage_record_pairs']==24*count and len(row['timing']['stages'])==24
 steps.append(dict(step=number,retained_tokens=128*count,reported_request_seconds=row['request_elapsed_ns']/1e9,
  reported_stages=24,reported_neural_stage_record_pairs=row['timing']['neural_stage_record_pairs'],
  reported_model_sha256=completion['artifacts'][f'step-{number}-model.bin']['sha256']))
result=dict(schema='copied-cold-receipt-check-v1',status='verified_copied_metadata_only',
 checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),program_sha256=ph,
 collection_manifest_sha256=digest((base/'collection-manifest.json').read_bytes()),
 copied_files_rehashed=len(manifest['files']),source_files_rehashed=len(program['sources']),
 sealed_worker_receipt_verified=True,declared_command_and_limits_verified=True,selected_cpu_debit_verified=True,
 request_and_applied_limits_link_verified=True,phase_binding_and_reservation_link_verified=True,
 debit=debit,reported_worker_seconds=completion['worker_elapsed_ns']/1e9,
 reported_transaction_seconds=transaction['elapsed_ns']/1e9,steps=steps,
 all_campaign_reservations_settled=all(v['state']=='settled' for v in ledger['attempts'].values()),
 actual_output_binaries_rehashed=False,actual_model_state_parsed=False,oracle_comparison_performed=False,
 scope='Copied terminal metadata, sealed controller logs and selected settled CPU debit only. Both final V54 audits remain required; this check does not establish numerical correctness, actual model/state agreement, speedup or quality.')
print(json.dumps(result,indent=2))
