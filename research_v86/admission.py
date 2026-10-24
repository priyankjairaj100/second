"""Pure fail-closed disposition and budget rules for a separate V80 recovery.

Cancelled jobs are not successful gates. Scheduler CPU does not settle the old
worker ledger. These rules never change a ledger, submit a job or permit a retry.
"""
from research_v83.accounting import cpu_time

OLD_PROGRAM='89f6a71e5b4f74b667bac64149c77005862d36b2b2e3dedc2a7260fb05c0ad60'
OLD_ATTEMPT='8cdee1b13fefa53728f4df46c269a4802bc377afffcd334dc989014e2354db70'
EXPECTED={str(i):('COMPLETED','0:0') if i==15904 else ('FAILED','120:0') if i in (15905,15917) else ('CANCELLED','0:0') for i in [*range(15904,15918),*range(15921,15926)]}
EXPECTED_ELAPSED={'15904':13,'15905':6439,'15917':2}
OLD_RESERVATION=12602
NEW_RESERVATION=108020
PRESERVED_CEILING=120624
OLD_CONTROLLER_RESERVATION=602
NEW_CONTROLLER_RESERVATION=6020
CONTROLLER_CEILING=7224

def require(ok,message):
    if not ok:raise ValueError(message)

def terminal_disposition(raw):
    """Parse exactly JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,CPUs,Mem,Node."""
    require(type(raw) is str and len(raw)<128*1024,'Bounded scheduler output required')
    allocations={}
    for line in raw.splitlines():
        fields=line.split('|');require(len(fields)==8,'Exact scheduler fields required')
        ident,state,exitcode,elapsed,cpu,cpus,mem,node=fields
        base=ident.split('.')[0];require(base in EXPECTED,'Unexpected scheduler job')
        if '.' in ident:continue
        require(ident not in allocations,'Duplicate scheduler allocation')
        require((state,exitcode)==EXPECTED[ident],'Old job disposition changed or is nonterminal')
        require(elapsed.isdigit() and int(elapsed)==EXPECTED_ELAPSED.get(ident,0),'Old allocation elapsed time changed')
        observed,quantum=cpu_time(cpu)
        if state=='CANCELLED':
            require(cpus=='0' and observed==0 and node in ('None assigned','(null)',''),'Cancelled successor must be unstarted')
        else:require(cpus=='1' and mem=='16G' and node=='csis.mn1','Original allocation resources differ')
        allocations[ident]=dict(job_id=ident,state=state,exit_code=exitcode,elapsed_seconds=int(elapsed),scheduler_cpu_ns=observed,reporting_quantum_ns=quantum)
    require(set(allocations)==set(EXPECTED),'Every old registered allocation is required')
    return dict(allocations=allocations,scientific_success=False,
                scheduler_cpu_ns=sum(x['scheduler_cpu_ns'] for x in allocations.values()),
                scheduler_cpu_does_not_settle_worker=True)

def carry_forward(ledger):
    require(type(ledger) is dict and ledger.get('schema')=='phase-cpu-ledger-v1','Original phase ledger required')
    attempts=ledger.get('attempts');require(type(attempts) is dict and set(attempts)=={OLD_ATTEMPT},'Exact original unknown attempt required')
    require(attempts[OLD_ATTEMPT]==dict(charged_cpu_seconds=OLD_RESERVATION,observed_cpu_ns=None,phase='feasibility',reserved_cpu_seconds=OLD_RESERVATION,state='reserved'),'Do not settle or refund the unresolved old attempt')
    binding=ledger.get('binding',{})
    require(binding.get('phase_cpu_seconds')=={'feasibility':NEW_RESERVATION},'Original phase cap changed')
    require(binding.get('identity',{}).get('protocol_sha256')==OLD_PROGRAM,'Old ledger program identity changed')
    total=OLD_RESERVATION+NEW_RESERVATION;controllers=OLD_CONTROLLER_RESERVATION+NEW_CONTROLLER_RESERVATION
    require(total<=PRESERVED_CEILING and controllers<=CONTROLLER_CEILING,'Combined recovery allowance exceeds preserved ceiling')
    return dict(unsettled_old_worker_reservation=OLD_RESERVATION,new_numerical_reservation=NEW_RESERVATION,
                combined_numerical_reservation=total,preserved_numerical_ceiling=PRESERVED_CEILING,
                remaining_numerical_reservation_margin=PRESERVED_CEILING-total,
                old_controller_reservation=OLD_CONTROLLER_RESERVATION,new_controller_reservation=NEW_CONTROLLER_RESERVATION,
                combined_controller_reservation=controllers,preserved_controller_ceiling=CONTROLLER_CEILING,
                historical_ledger_modified=False,reservation_is_not_observed_cpu=True,
                software_and_audits_have_separate_preserved_caps=True)
