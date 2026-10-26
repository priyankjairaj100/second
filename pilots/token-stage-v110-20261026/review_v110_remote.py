"""Read-only actual diagnostic/qualification review; no job or numerical execution."""
import datetime,json,pathlib,resource,subprocess,sys,time
ROOT=pathlib.Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/token-stage-diagnostic-v110-20261026-a'
sys.path[:0]=[str(RUN),str(ROOT)]
resource.setrlimit(resource.RLIMIT_CPU,(300,301));resource.setrlimit(resource.RLIMIT_AS,(2*2**30,)*2)
from research_v110 import campaign
from research_v110.closure import review
from research_v110.dispatch_failure import FIELDS
from research_v110.contracts import budget
from research_v83.accounting import scheduler_rows,cpu_time
from research_v83.terminal import Inputs,actual_seal
from research_v80.io import json_read,require,read
start=time.process_time_ns();p=campaign.verify(prerequisite=False);sha=campaign.sha(RUN/'program.json')
require(sha=='29e114bb8cae47f5dc8fa70a346d62cd575e6b0dfc959b286903bed0071e2602','Registered actual program changed')
raw=subprocess.check_output(['sacct','-nP','-j','16366,16367',FIELDS],text=True,timeout=20)
queue=subprocess.check_output(['squeue','-u','poonam','-h','-o','%i|%j|%T'],text=True,timeout=20)
report=dict(schema='actual-token-stage-review-v110',captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),program_sha256=sha,scheduler_raw=raw,queue=queue,source_files_verified=1242,complete_model_comparisons=0)
if '16367|second110-diagnostic|COMPLETED|0:0|' in raw:
    jobs=dict(checks=dict(job_id='16366',name='second110-checks'),diagnostic=dict(job_id='16367',name='second110-diagnostic'))
    scheduled=scheduler_rows(raw,jobs);inputs=Inputs();costs={}
    for op in jobs:
        costs[op],worker=review(op,p,sha,inputs,scheduled[op])
    completion=inputs.json(RUN/'diagnostic/outputs/completion.json')
    require(completion['status']=='certified_stage' and completion['program_sha256']==sha
        and completion['job_id']=='16367' and completion['route']=='token'
        and completion['complete_model'] is completion['transfer_evidence'] is completion['speed_comparison'] is False,
        'Only a bound certified-stage result is admitted')
    require(completion['original_streamed_route_executed'] is False and completion['certified_codes']==3072*768,'Diagnostic extent/scope changed')
    code=completion['code_metadata'];e=completion['artifacts']['codes.bin']
    inputs.read(RUN/'diagnostic/outputs/codes.bin',{k:e[k] for k in ('bytes','sha256')},retain=False)
    require(e['bytes']==1179648==code['nbytes'] and e['sha256']==code['sha256']
        and code['stage_id']=='block.0011.mlp_up' and code['rows']==3072 and code['columns']==768 and code['bits']==4,'Complete actual stage code extent differs')
    original=json_read(campaign.PARENT/'program.json')
    target=json_read(pathlib.Path(original['admitted_targets']['gpt2']['anchor-target.json']['path']))
    row=next(x for x in target['stages'] if x['stage_id']=='block.0011.mlp_up')
    require(code['scale_values_hex']==row['row_scale_hex'],'Original fixed grids changed')
    ledger=budget(p,sha,read_only=True)
    require(set(ledger['attempts'])=={worker['budget_attempt_id']} and ledger['reserved_unknown_attempts']==0
        and not ledger['reservation_overrun_attempts'] and not any(ledger['over_cap'].values()),'Exactly one settled diagnostic required')
    inputs.unchanged()
    report.update(status='verified_selected_stage_certificate_and_complete_accounting',completion=completion,worker=worker,
        costs=costs,budget=ledger,inputs=inputs.files,actual_packed_extent_verified=True,
        full_model_oracle_executed=False,independent_stage_oracle_executed=False,
        numerical_debit_with_prior=6196+worker['budget_debit']['charged_cpu_seconds'])
elif '16367|second110-diagnostic|FAILED|' in raw or '16367|second110-diagnostic|TIMEOUT|' in raw or '16367|second110-diagnostic|OUT_OF_MEMORY|' in raw:
    report['status']='terminal_diagnostic_failure'
    inputs=Inputs()
    if (RUN/'diagnostic/worker/result.json').is_file():report['worker']=actual_seal(inputs,RUN/'diagnostic/worker')
    for name in ['diagnostic-entry.json','diagnostic-host.json','diagnostic/outputs/completion.json','diagnostic/transaction.json']:
        if (RUN/name).is_file():report[name]=inputs.json(RUN/name)
    report['inputs']=inputs.files
    for name in ['diagnostic-16367.log','diagnostic-bootstrap.log']:
        if (RUN/name).is_file():report[name]=read(RUN/name,maximum=64*2**20).decode()[-16000:]
else:
    report['status']='not_terminal'
    report['completion_exists']=(RUN/'diagnostic/outputs/completion.json').exists()
report['readonly_cpu_ns']=time.process_time_ns()-start;report['readonly_review_cost_outside_experiment']=True
print(json.dumps(report,sort_keys=True,separators=(',',':')))
