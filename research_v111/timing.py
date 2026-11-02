"""Actual saved numerical/host clock containment; no neural imports."""
from research_v111.config import RUN,ORDER
from research_v111 import campaign as c
from research_v111.host import reconcile_cpu
from research_v80.io import require

def costs(p,completions,inputs):
    result={};controllers={};program_sha=c.sha(RUN/'program.json')
    for trial in ORDER:
        q=completions[trial];tx=inputs.json(RUN/trial/'transaction.json');name=trial.replace('/','--');entry=inputs.json(RUN/(name+'-entry.json'));start=inputs.json(RUN/(name+'-entry-start.json'))
        require(entry['status']=='complete' and entry['error'] is None and entry['program_sha256']==program_sha and entry['operation']==trial and entry['arguments']==[] and entry['job_id']==tx['slurm_job_id']==start['job_id'] and entry['hostname']==p['host'] and entry['cpu_limits']==[300,10202],'Actual matched controller identity differs')
        require(all(type(entry[k]) is int and entry[k]>=0 for k in ('process_cpu_ns','waited_child_cpu_ns','elapsed_ns')) and entry['process_cpu_ns']<=301*10**9,'Controller observed CPU differs')
        require(0<q['worker_elapsed_ns']<=tx['elapsed_ns']<=entry['elapsed_ns'],'Clock containment differs')
        require(start['program_sha256']==program_sha and start['arguments']==[] and start['operation']==trial and len(entry['affinity_cpus'])==1,'Entry start differs')
        host=inputs.json(RUN/(name+'-host.json'))
        require(host['status']=='complete' and host['error'] is None and host['program_sha256']==program_sha
            and host['job_id']==entry['job_id'] and host['operation']==trial and host['arguments']==[]
            and host['outcome']['exit_code']==0 and host['outcome']['failure'] is None
            and host['outcome']['log']['complete'] is True,'Actual complete host envelope required')
        partition=reconcile_cpu(trial,host['host_process_cpu_ns'],host['preflight_waited_child_cpu_ns'],host['outcome']['subtree_cpu_ns'],entry)
        require(partition==host['accounting'] and entry['elapsed_ns']<=host['elapsed_ns'],'Actual complete host accounting differs')
        require(inputs.read(RUN/(name+'-bootstrap.log'),retain=False)=={k:host['outcome']['log'][k] for k in ('bytes','sha256')},'Complete host log differs')
        controllers[trial]=dict(entry=entry,host=host)
        row=dict(complete_host_elapsed_ns=host['elapsed_ns'],complete_host_cpu_ns=partition['envelope_cpu_ns'],transaction_elapsed_ns=tx['elapsed_ns'],worker_elapsed_ns=q['worker_elapsed_ns'],context_elapsed_ns=q['context_elapsed_ns'],entry_process_cpu_ns=entry['process_cpu_ns'],entry_waited_child_cpu_ns=entry['waited_child_cpu_ns'],worker_max_rss_kib=q['max_rss_kib'])
        if 'request' in q:
            r=q['request'];require(0<r['request_elapsed_ns']<=q['worker_elapsed_ns'],'Request clock containment differs')
            row.update(request_elapsed_ns=r['request_elapsed_ns'],request_timing=r['timing'],live_state_bytes=r['live_state_bytes'])
        result[trial]=row
    require(sum(x['host']['accounting']['nonnumerical_cpu_ns'] for x in controllers.values())<=p['controller_cpu_allowance_seconds']*10**9,'Controller sum exceeds separate allowance')
    return dict(trials=result,entries=controllers,clock_scopes_overlap=True,host_terminal_accounting_pending=True)
