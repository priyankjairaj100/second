"""Reopen actual V104 failed and successful seals; never mutate its namespace."""
import subprocess
from pathlib import Path
from research_v80.io import read,json_read,require,info
from research_v83.terminal import Inputs,actual_seal
from research_v83.accounting import cpu_time
from research_v110.config import RUN,PARENT,PARENT_SHA
from src.run_store import strict_json
FIELDS='--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'


def verify(*,live_scheduler=False):
    from research_v110.setup_failure import verify as setup_failure
    setup=setup_failure()
    blob=read(RUN/'gates/v104-failed-screen-v110.json',maximum=4*2**20)
    gate=strict_json(blob)
    require(gate['parent_program_sha256']==PARENT_SHA,'Exact parent program required')
    from research_v104 import campaign as parent
    p=parent.verify(prerequisite=False)
    require(parent.sha(PARENT/'program.json')==PARENT_SHA,'Original program changed')
    for path,e in gate['inputs'].items():
        require(Path(path).is_relative_to(PARENT),'Diagnostic gate cannot bind unrelated inputs')
        read(path,e,maximum=2*2**30,retain=False)
    raw=gate['scheduler_raw']
    if live_scheduler:
        actual=subprocess.check_output(['sacct','-nP','-j',','.join(str(i) for i in range(16336,16359)),FIELDS],text=True,timeout=20)
        require(actual==raw,'Actual parent scheduler outcomes changed')
    rows={x.split('|')[0]:x.split('|') for x in raw.splitlines() if '.' not in x.split('|')[0]}
    require(set(rows)=={str(i) for i in range(16336,16359)},'All parent outcomes required')
    require(all(rows[str(i)][2:4]==['COMPLETED','0:0'] for i in range(16336,16339))
        and rows['16339'][2:4]==['FAILED','1:0']
        and all(rows[str(i)][2:7]==['CANCELLED','0:0','0','00:00:00','0'] for i in range(16340,16359)),
        'Original failure and unstarted dependents must remain')
    inputs=Inputs();seals={n:actual_seal(inputs,PARENT/n/'worker') for n in
        ('distilgpt2/prepare','gpt2/prepare','gpt2/reference_compressed-1')}
    require(seals['gpt2/reference_compressed-1']['outcome']['status']=='failed'
        and seals['gpt2/reference_compressed-1']['outcome']['returncode']==1,'Actual failed seal required')
    from research_v104.contracts import budget
    ledger=budget(p,PARENT_SHA,read_only=True)
    require(set(ledger['attempts'])=={s['budget_attempt_id'] for s in seals.values()}
        and ledger['reserved_unknown_attempts']==0 and not ledger['reservation_overrun_attempts']
        and not any(ledger['over_cap'].values()),'Exactly the settled old workers required')
    charged=sum(s['budget_debit']['charged_cpu_seconds'] for s in seals.values())
    require(charged==6196 and all(s['budget_debit']['state']=='settled' for s in seals.values()),'Preserve all actual numerical cost')
    controllers=0
    for i,n in zip(range(16337,16340),seals):
        low,q=cpu_time(rows[str(i)][5]);controllers+=low+q-seals[n]['resource_usage']['total_cpu_ns']
    require(controllers==61648485000 and controllers+10**9<=63*10**9,'Conservative carried controller cost differs')
    check=json_read(PARENT/'checks-entry.json');low,q=cpu_time(rows['16336'][5])
    require(low+q+72*10**9<=139*10**9 and low+q-check['software_tree_cpu_ns']+19*10**9<=33*10**9,
        'Preserve prior software and checks-controller costs')
    completion=json_read(PARENT/'gpt2/reference_compressed-1/outputs/completion.json')
    require(completion['status']=='failed' and completion['complete_model'] is False
        and completion['error_type']=='DispatchRefused' and 'status=3, row=0, coordinate=359' in completion['error'],
        'Actual preserved scientific refusal required')
    return dict(status='preserved_failed_screen_and_actual_costs',gate=info(blob),
        parent_program_sha256=PARENT_SHA,charged_numerical_seconds=6196,
        rounded_software_carry=139,rounded_checks_controller_carry=33,
        rounded_numerical_controller_carry=63,complete_model_comparisons=0,preserved_v109_setup_failure=setup)


def check_host_binding(program,start,expected,operation,job):
    require(start['program_sha256']==expected and start['operation']==operation
        and start['job_id']==job and start['live_failure_scheduler_verified'] is True
        and start['prior_failure_verification']==program['prior_complete_failure'],
        'Actual current-allocation parent-state check required')
