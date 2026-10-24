import sys,pathlib,hashlib,json,resource,time,datetime,subprocess
root=pathlib.Path('/nfs_home/users/poonam/second-20261010')
run=root/'local_runs/four-cell-recovery-v89-20261023-a'
sys.path[:0]=[str(run),str(root)]
resource.setrlimit(resource.RLIMIT_CPU,(120,121));resource.setrlimit(resource.RLIMIT_AS,(2*2**30,)*2)
from research_v83.terminal import Inputs,actual_seal
from research_v83.accounting import scheduler_rows
from research_v89.terminal import cost
from research_v89.config import design
from research_v89.storage_plan import artifacts,requests
from research_v87.outputs import inspect_outputs
from research_v88.storage import evaluate
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes
from src.run_store import canonical_json,digest
start=time.perf_counter_ns();cpu=time.process_time_ns()
expected='6f9b59c73e33d407dadc6504b666ca67b5c5efb28e1a0fe8e418b470af8ab0e9'
inputs=Inputs();p=inputs.json(run/'program.json')
assert digest(canonical_json(p))==expected and all(p.get(k)==v for k,v in design().items())
assert inputs.json(run/'registration.json')==dict(program_sha256=expected)
for name in ('research_v89/terminal.py','research_v89/host.py','research_v89/storage_plan.py','research_v89/config.py','research_v87/outputs.py','research_v83/terminal.py','research_v83/accounting.py','research_v88/storage.py'):
 inputs.read(run/name,p['source_inventory'][name],retain=False)
host=inputs.json(run/'optimized_compressed-1-host.json');entry=inputs.json(run/'optimized_compressed-1-entry.json')
hstart=inputs.json(run/'optimized_compressed-1-host-start.json');tx=inputs.json(run/'optimized_compressed-1/transaction.json')
plan=inputs.json(run/'optimized_compressed-1/plan.json');identity=inputs.json(run/'optimized_compressed-1/worker/identity.json')
sealed=actual_seal(inputs,run/'optimized_compressed-1/worker')
assert sealed['attempt']=='attempt-0001' and sealed['budget_reservation_overrun'] is False
assert identity['identity']==dict(campaign_sha256=expected,trial='optimized_compressed-1') and identity['cwd']==str(root)
assert identity['command']==[str(root/'.venv-container/bin/python'),'-B',str(run/'research_v89/worker.py'),str(run/'optimized_compressed-1/plan.json')]
limits=identity['limits']
assert all(limits[k]==v for k,v in p['trials']['optimized_compressed-1'].items())
assert limits['address_space_bytes']==16*2**30 and limits['file_size_bytes']==2*2**30 and limits['threads']==1 and len(limits['affinity_cpus'])==1
assert tx['worker_outcome']==sealed['outcome'] and tx['slurm_job_id']=='16007'
assert plan==dict(trial='optimized_compressed-1',program=str(run/'program.json'),program_sha256=expected,output=str(run/'optimized_compressed-1/outputs'),slurm_job_id='16007')
assert host['arguments']==entry['arguments']==['optimized_compressed-1']
s=read_budget_snapshot(run/'budget',identity=dict(protocol_sha256=expected,source_sha256=source_hashes(root)),phase_cpu_seconds={'feasibility':p['phase_cpu_seconds']})
assert s['status']=='verified' and s['attempts'][sealed['budget_attempt_id']]==sealed['budget_debit']
assert not s['reservation_overrun_attempts'] and not any(s['over_cap'].values())
debit=sealed['budget_debit'];usage=sealed['resource_usage']
assert debit['state']=='settled' and debit['observed_cpu_ns']==usage['total_cpu_ns']==usage['user_cpu_ns']+usage['system_cpu_ns']
assert debit['reserved_cpu_seconds']==12602 and debit['charged_cpu_seconds']<=12602
ack=inputs.json(run/'optimized_compressed-1/worker/attempt-0001/limits-applied.json')
request=inputs.json(run/'optimized_compressed-1/worker/attempt-0001/request.json')
assert request['command']==identity['command'] and request['limits']==limits and request['cwd']==str(root)
assert ack==sealed['limits_applied'] and ack['request_sha256']==digest(canonical_json(request))
assert ack['cpu_seconds']==[12600,12601] and ack['address_space']==[16*2**30]*2 and ack['file_size']==[2*2**30]*2
raw=subprocess.check_output(['sacct','-nP','-j','16007','--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=15)
sched=scheduler_rows(raw,{'optimized_compressed-1':dict(job_id='16007',name='second89-optimized_compressed-1')})['optimized_compressed-1']
costs=cost(host,entry,sched,p,'run',sealed)
for x in (host,entry,hstart):
 assert x['program_sha256']==expected and x['job_id']=='16007' and x['operation']=='run' and x['arguments']==['optimized_compressed-1']
wanted=requests(p['storage_plan'],p['source_inventory'],p['source_archive_bytes'],'optimized_compressed-1')
snap=hstart['snapshot'];assert wanted==hstart['requests']==snap['requested']
assert hstart['admission']==evaluate(wanted,snap['observations'],snap['quota_text'],snap['group_reports'])
mapping=entry['container_storage_mapping']
assert mapping['status']=='matched_host_devices_and_new_file_groups' and mapping['paths_redirected'] is False
for scope,path in [('project',str(run)),('temporary','/tmp')]:
 o=snap['observations'][scope]
 assert mapping['observations'][scope]==dict(path=path,device=o['device'],write_group=o['write_group'])
inputs.read(run/'optimized_compressed-1-bootstrap.log',{k:host['outcome']['log'][k] for k in ('bytes','sha256')},retain=False)
assert inputs.read(run/'optimized_compressed-1-16007.log',retain=False)['bytes']<=4*2**20
completion=inputs.json(run/'optimized_compressed-1/outputs/completion.json')
assert completion['schema']=='four-cell-complete-service-worker-v89' and completion['status']=='complete' and completion['complete_model'] is True
assert completion['program_sha256']==expected and completion['trial']=='optimized_compressed-1' and completion['slurm_job_id']=='16007'
assert completion['source_files_sha256']==digest(canonical_json(p['new_sources']))
assert set(completion['artifacts'])==artifacts('optimized_compressed-1')
extent=inspect_outputs(run/'optimized_compressed-1/outputs',artifacts('optimized_compressed-1'),p['model_bytes'])
for name,b in completion['artifacts'].items():assert extent['files'][name]['bytes']==b['bytes']
assert completion['request']['code_count']==p['code_count']==42467328
assert completion['request']['arm']=='compressed'
assert len(completion['request']['retained_ids'])==12 and len(completion['request']['deleted_ids'])==1
assert len(completion['request']['timing']['stages'])==p['stage_count']==24
assert len({r['stage_id'] for r in completion['request']['timing']['stages']})==24
assert completion['implementation']['cell']=='optimized_compressed'
inputs.unchanged()
out=dict(schema='request-receipt-review-v96',status='metadata_seal_storage_and_accounting_verified',observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),program_sha256=expected,job_id='16007',scheduler_raw=raw,costs=costs,budget_debit=debit,live_ledger_observation=dict(sha256=s['ledger_sha256'],bytes=s['ledger_bytes'],attempts=len(s['attempts']),reserved_unknown_attempts=s['reserved_unknown_attempts'],not_a_frozen_terminal_ledger=True),extent=extent,host_elapsed_ns=host['elapsed_ns'],worker_elapsed_ns=completion['worker_elapsed_ns'],worker_max_rss_kib=completion['max_rss_kib'],completion=completion,inputs=inputs.files,payloads={str(run/'optimized_compressed-1-host.json'):host,str(run/'optimized_compressed-1-entry.json'):entry,str(run/'optimized_compressed-1/worker/result.json'):sealed},scope=dict(bulk_output_hashes_rechecked=False,independent_model_state_equality=False,comparison_complete=False,transfer=False,quality_evaluation=False,reason='No bulk artifact reread while timed requests run; both frozen terminal audits remain required'),readonly_review_cpu_ns=time.process_time_ns()-cpu,readonly_review_elapsed_ns=time.perf_counter_ns()-start)
print(json.dumps(out,sort_keys=True,separators=(',',':')))
