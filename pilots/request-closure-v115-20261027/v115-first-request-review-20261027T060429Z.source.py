from pathlib import Path
import sys,json,subprocess,datetime,time,resource,hashlib
root=Path('/nfs_home/users/poonam/second-20261010')
run=root/'local_runs/matched-complete-recovery-v112-20261026-a'
sys.path.insert(0,str(run))
resource.setrlimit(resource.RLIMIT_CPU,(60,61));resource.setrlimit(resource.RLIMIT_AS,(512*2**20,)*2)
started=time.perf_counter_ns()
from research_v112 import campaign,protocol
from research_v112.config import expected_artifacts,name
from research_v112.closure import review
from research_v83.accounting import scheduler_rows
from research_v83.terminal import Inputs
from src.run_store import canonical_json,digest
expected='a73ca66d08b50feeccf9601d6d214b00ad21917ae900671cc35d373aef4f4381'
op='gpt2/reference_compressed-1';job='16408';key=name(op)
fields='--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'
raw=subprocess.check_output(['sacct','-nP','-j',job,fields],text=True,timeout=20)
parent=[r.split('|') for r in raw.splitlines() if r.split('|')[0]==job]
assert len(parent)==1
if parent[0][2:4]!=['COMPLETED','0:0']:
 print(json.dumps(dict(status='not_ready_no_receipt_review',scheduler_raw=raw,captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),automatic_retry=False)))
 sys.exit(0)
p=campaign.verify(prerequisite=False);assert campaign.sha(run/'program.json')==expected
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==p['numerical_checkout']
assert not subprocess.check_output(['git','-c','core.preloadIndex=false','-c','index.threads=1','-C',str(root),'status','--porcelain'],text=True).strip()
protocol.allocation(op,expected,job,require_release=True)
inputs=Inputs();assert inputs.json(run/'program.json')==p
scheduled=scheduler_rows(raw,{op:dict(job_id=job,name='second112-'+key)})
cost,worker=review(op,p,expected,inputs,scheduled[op])
q=inputs.json(run/op/'outputs/completion.json')
assert q['schema']=='matched-complete-service-worker-v112' and q['status']=='complete' and q['complete_model'] is True
assert q['program_sha256']==expected and q['slurm_job_id']==job and q['trial']==op and q['profile']=='gpt2'
assert q['source_files_sha256']==digest(canonical_json(p['sources']))
assert q['request']['code_count']==p['code_counts']['gpt2'] and len(q['request']['retained_ids'])==p['retained_counts'][0]
assert set(q['artifacts'])==expected_artifacts(op)
for filename,e in q['artifacts'].items():
 assert e==dict(file=filename,**inputs.read(run/op/'outputs'/filename,retain=False))
policy=q['implementation']['point_route_policy']
assert policy['closed'] is True and policy['point_route']=='token' and policy['cross_route_retry'] is False
assert policy['policy']==p['point_route_policy'] and policy['adapter_sha256']==p['sources']['research_v112/policy.py']['sha256']
stages=q['request']['timing']['stages']
assert len(stages)==len({r['stage_id'] for r in stages})==p['stage_counts']['gpt2']
for stage in stages:
 a=stage['admission']
 if a['kind']=='point':assert stage['route']==a['selected_route']=='token' and a['selection_policy']==p['point_route_policy']
inputs.unchanged()
print(json.dumps(dict(status='verified_actual_first_request_receipt_and_accounting',program_sha256=expected,operation=op,scheduler_raw=raw,cost=cost,worker_budget_debit=worker['budget_debit'],inputs=inputs.files,stages=len(stages),code_count=q['request']['code_count'],point_route_policy=policy,live_state_bytes=q['request']['live_state_bytes'],complete_host_elapsed_ns=inputs.json(run/(key+'-host.json'))['elapsed_ns'],independent_model_equality_verified=False,speed_comparison=False,full_model_transfer_claim=False,readonly_review_cost_outside_experiment=True,readonly_host_cpu_ns=time.process_time_ns(),readonly_host_elapsed_ns=time.perf_counter_ns()-started,captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),sort_keys=True))
