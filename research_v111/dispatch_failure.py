"""Actual prior failures, selected-stage certificate and remaining cost gates."""
import subprocess
from pathlib import Path
from research_v80.io import read,json_read,require,info
from research_v83.terminal import Inputs
from research_v83.accounting import scheduler_rows
from research_v111.config import RUN,DIAGNOSTIC,DIAGNOSTIC_SHA
from research_v110.dispatch_failure import check_host_binding,FIELDS
from src.run_store import strict_json


def verify(*,live_scheduler=False):
    from research_v110 import campaign as prior
    from research_v110.dispatch_failure import verify as failure
    from research_v110.closure import review
    from research_v110.contracts import budget
    preserved=failure(live_scheduler=live_scheduler)
    p=prior.verify(prerequisite=False)
    require(prior.sha(DIAGNOSTIC/'program.json')==DIAGNOSTIC_SHA,'Actual diagnostic program required')
    blob=read(RUN/'gates/v110-selected-stage-closure.json',maximum=4*2**20);gate=strict_json(blob)
    require(gate['status']=='verified_selected_stage_certificate_and_complete_accounting'
        and gate['program_sha256']==DIAGNOSTIC_SHA and gate['numerical_debit_with_prior']==6304
        and gate['full_model_oracle_executed'] is gate['independent_stage_oracle_executed'] is False,
        'Actual scoped diagnostic closure required')
    inputs=Inputs()
    for path,e in gate['inputs'].items():
        require(Path(path).is_relative_to(DIAGNOSTIC),'Diagnostic gate scope differs')
        inputs.read(path,e,retain=False)
    raw=gate['scheduler_raw']
    if live_scheduler:
        actual=subprocess.check_output(['sacct','-nP','-j','16366,16367',FIELDS],text=True,timeout=20)
        require(actual==raw,'Actual diagnostic scheduler state changed')
    jobs=dict(checks=dict(job_id='16366',name='second110-checks'),diagnostic=dict(job_id='16367',name='second110-diagnostic'))
    scheduled=scheduler_rows(raw,jobs);costs={};worker=None
    for operation in jobs:costs[operation],worker=review(operation,p,DIAGNOSTIC_SHA,inputs,scheduled[operation])
    require(costs==gate['costs'] and worker==gate['worker']
        and budget(p,DIAGNOSTIC_SHA,read_only=True)==gate['budget'],'Actual diagnostic costs or ledger changed')
    q=inputs.json(DIAGNOSTIC/'diagnostic/outputs/completion.json')
    require(q==gate['completion'] and q['status']=='certified_stage' and q['route']=='token'
        and q['certified_codes']==2359296 and q['complete_model'] is q['original_streamed_route_executed'] is False,
        'Exact successful selected-stage certificate required')
    require(preserved['charged_numerical_seconds']+worker['budget_debit']['charged_cpu_seconds']==6304
        and 139*10**9+costs['checks']['scheduler_cpu_ns']+costs['checks']['scheduler_quantum_ns']<=207*10**9
        and 33*10**9+costs['checks']['complete_controller_upper_cpu_ns']<=48*10**9
        and 63*10**9+costs['diagnostic']['complete_controller_upper_cpu_ns']<=79*10**9,
        'Actual costs exceed conservative prospective carries')
    return dict(status='preserved_failure_and_scoped_success',gate=info(blob),preserved_failure=preserved,
        diagnostic_program_sha256=DIAGNOSTIC_SHA,carried_numerical_seconds=6304,
        carried_software_seconds=207,carried_checks_controller_seconds=48,
        carried_numerical_controller_seconds=79,complete_model_comparisons=0)
