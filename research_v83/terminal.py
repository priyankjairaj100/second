"""Host-only read-only terminal closure for the fixed V80/V81/V82 jobs.

Run only after the named finite chain is terminal. This never launches/retries a
job or acquires budget locks. Failed/nonterminal attempts refuse closure and are
retained in the existing source/receipt tree. Output is a reporting snapshot.
"""
import datetime,hashlib,json,os,platform,resource,subprocess,sys,time
from pathlib import Path
from research_v83.accounting import require,integer,scheduler_rows,reconcile
from src.run_store import canonical_json,read_completed,strict_json
BASE=Path('/nfs_home/users/poonam/second-20261010')
CONFIG={
 'v80':dict(namespace='four-cell-service-v80-20261023-a',program='89f6a71e5b4f74b667bac64149c77005862d36b2b2e3dedc2a7260fb05c0ad60',jobs={name:dict(job_id=str(15904+i),name='second80-'+name) for i,name in enumerate(['checks','prepare','reference_compressed-1','optimized_compressed-1','reference_modern-1','optimized_modern-1','optimized_modern-2','reference_modern-2','optimized_compressed-2','reference_compressed-2','oracle','primary','supplemental'])}),
 'v81':dict(namespace='transfer-software-v81-20261023-a',program='3f89d3c73c21d9d955c9396d6cfbe8150ad98793088f2cca7c6ba5c88c8e5ada',jobs={'checks':dict(job_id='15917',name='second81-software')}),
 'v82':dict(namespace='matched-transfer-admission-v82-20261023-a',program='5bead3425eb9bb4bec645ac12e681b45e62d87762cef0f15179aecdb427ae27b',jobs={name:dict(job_id=str(15921+i),name='second82-'+name) for i,name in enumerate(['checks','fetch','distilgpt2','gpt2','close'])})}

class Inputs:
    def __init__(self):self.files={};self.payloads={}
    def read(self,path,expected=None,retain=True):
        path=Path(path).absolute();require(path.is_relative_to(BASE) and path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),'Regular project input required')
        before=path.stat();require(before.st_size<=2*2**30 and (not retain or before.st_size<=64*2**20),'Input extent differs')
        h=hashlib.sha256();count=0;parts=[]
        with path.open('rb') as f:
            while b:=f.read(2**20):
                h.update(b);count+=len(b)
                require(count<=before.st_size,'Growing terminal input refused')
                if retain:parts.append(b)
        after=path.stat();require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'Input changed during read')
        actual=dict(bytes=count,sha256=h.hexdigest());require(expected is None or actual==expected,'Actual terminal input commitment differs: '+str(path))
        require(str(path) not in self.files or self.files[str(path)]==actual,'Input changed between reads')
        self.files[str(path)]=actual
        if retain:
            raw=b''.join(parts);self.payloads[str(path)]=raw.decode('utf8');return raw
        return actual
    def json(self,path):return strict_json(self.read(path))
    def unchanged(self):
        for name,e in list(self.files.items()):self.read(name,e,retain=False)

def actual_seal(inputs,root):
    identity=inputs.json(root/'identity.json');result=read_completed(root,identity)
    require(result is not None and result==inputs.json(root/'result.json')==inputs.json(root/result['attempt']/'status.json'),'Actual complete worker seal required')
    for name,e in result['artifacts'].items():inputs.read(root/result['attempt']/name,e,retain=False)
    return result

def main(kind):
    require(kind in CONFIG and sys.platform=='linux' and platform.node()=='csis.mn1','Pinned host-side terminal read required')
    started=time.perf_counter_ns();cpu=time.process_time_ns()
    resource.setrlimit(resource.RLIMIT_CPU,(300,301));resource.setrlimit(resource.RLIMIT_AS,(2*2**30,)*2)
    require(subprocess.check_output(['git','-C',str(BASE),'rev-parse','HEAD'],text=True).strip()=='f900999fcb200509dfad4fc081ce9c87fd172a16','Numerical checkout changed')
    require(not subprocess.check_output(['git','-C',str(BASE),'status','--short'],text=True).strip(),'Numerical checkout is dirty')
    cfg=CONFIG[kind];root=BASE/'local_runs'/cfg['namespace'];inputs=Inputs();p=inputs.json(root/'program.json')
    require(inputs.files[str(root/'program.json')]['sha256']==cfg['program'],'Registered program differs')
    raw=subprocess.check_output(['sacct','-nP','-j',','.join(x['job_id'] for x in cfg['jobs'].values()),'--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=20)
    scheduled=scheduler_rows(raw,cfg['jobs']);costs={};audits={};worker_ids=set()
    groups=('prior_sources','new_sources','dependency_files','historical_ledgers') if kind=='v80' else ('sources',) if kind=='v81' else ('new_sources',)
    for group in groups:
        for name,e in p[group].items():inputs.read(Path(name) if Path(name).is_absolute() else root/name,e,retain=False)
    if kind=='v80':
        for name in cfg['jobs']:
            entry=inputs.json(root/('software-completion.json' if name=='checks' else name+'-entry.json'))
            trial=name in p['trials'];worker=None
            if trial:
                worker=actual_seal(inputs,root/name/'worker');worker_ids.add(worker['budget_attempt_id'])
                require(entry['arguments']==[name] and worker['limits']['cpu_seconds']==p['trials'][name]['cpu_seconds'],'Trial/cap identity differs')
                own=601;aggregate=p['trials'][name]['cpu_seconds']+2+602
            elif name=='checks':
                own=301;aggregate=602;require(entry['tests']==73 and entry['errors']==entry['failures']==entry['skipped']==0,'V80 software failed')
            else:own=p[name+'_audit_caps']['cpu']+1;aggregate=own
            costs[name]=reconcile(entry,scheduled[name],program_sha=cfg['program'],operation='run' if trial else name,own_cap=own,aggregate_cap=aggregate,worker=worker)
        for name in ('primary','supplemental'):
            audit=inputs.json(root/(name+'-audit.json'));audits[name]=audit
            require(audit['status']=='verified' and audit['program_sha256']==cfg['program'],'Completed actual audit required')
            for path,e in audit['inputs'].items():inputs.read(path,e,retain=False)
        primary,supplemental=audits['primary'],audits['supplemental']
        require(supplemental['evidence']['primary_receipt_sha256']==inputs.files[str(root/'primary-audit.json')]['sha256']
            and supplemental['evidence']['eight_actual_model_pairs_equal'] is True and primary['budget']==supplemental['budget'],'Audit receipt bindings differ')
        require(len(primary['evidence']['comparisons'])==8 and all(x['actual_model_bytes_equal'] is True and x['actual_bytes_equal'] is True for x in primary['evidence']['comparisons']),'Eight complete actual comparisons required')
        budget=primary['budget'];require(worker_ids==set(budget['attempts']) and budget['reserved_unknown_attempts']==0 and not budget['reservation_overrun_attempts'] and not any(budget['over_cap'].values()),'Complete settled worker ledger required')
        require(sum(costs[n]['own_cpu_ns']+costs[n]['nonworker_child_cpu_ns'] for n in p['trials'])<=p['controller_allowance_cpu_seconds']*10**9,'Complete controller allowance exceeded')
        evidence=dict(actual_audits_and_inputs_reverified=True,comparison_count=8,quality_evaluation=False,confirmation=False)
    elif kind=='v81':
        q=inputs.json(root/'completion.json');r=inputs.json(root/'outputs/transfer-results.json')
        from research_v82.prerequisite import validate_payloads
        validate_payloads(inputs.read(root/'completion.json'),inputs.read(root/'outputs/transfer-results.json'))
        costs['checks']=reconcile(dict(q,operation='checks'),scheduled['checks'],program_sha=cfg['program'],operation='checks',own_cap=301,aggregate_cap=602)
        for name,e in q['outputs'].items():inputs.read(root/name,e,retain=False)
        evidence=dict(actual_software_tests=62,empirical_execution=False)
    else:
        reports={}
        for name in cfg['jobs']:
            q=inputs.json(root/(name+'-completion.json'));reports[name]=q;target=name in ('distilgpt2','gpt2')
            worker=actual_seal(inputs,root/name/'worker') if target else None
            if worker is not None:worker_ids.add(worker['budget_attempt_id'])
            costs[name]=reconcile(q,scheduled[name],program_sha=cfg['program'],operation=name,own_cap=301,aggregate_cap=903 if target else 602 if name=='checks' else 302,worker=worker,rss_key='max_rss_kib')
            host=inputs.json(root/(name+'-host-gate.json'));require(host['status']=='complete' and host['job_id']==q['job_id'] and host['program_sha256']==cfg['program'],'Prior host gate differs')
        require(reports['checks']['result']==dict(tests=26,failures=0,errors=0,skipped=0),'Admission software census differs')
        final=reports['close']['result'];require(final['status']=='admitted_pending_host_terminal_accounting'
            and all(final['seal_audit'][k] is True for k in ('actual_targets_verified','sealed_workers_verified','matched_records_verified')),'Actual target seal audit required')
        require(worker_ids==set(final['budget']['attempts']) and not any(final['budget']['over_cap'].values()),'Complete two-target ledger required')
        for profile,model in final['models'].items():
            actual=inputs.json(root/profile/'outputs/completion.json');require(model==actual,'Target completion changed after close')
            for name,e in actual['artifacts'].items():inputs.read(root/profile/'outputs'/name,{k:e[k] for k in ('bytes','sha256')},retain=False)
            for name,h in p['profiles'][profile]['checkpoint_files'].items():
                require(inputs.read(Path(p['checkpoint_paths'][profile])/name,retain=False)['sha256']==h,'Actual checkpoint changed')
        evidence=dict(actual_target_admission=True,empirical_transfer=False,quality_evaluation=False)
    # Audit-input hashes were actually reopened; these hashes do not substitute
    # for the model/state equality performed by the separately completed audits.
    inputs.unchanged()
    output=dict(readonly_host_review_cpu_ns=time.process_time_ns()-cpu,readonly_host_review_elapsed_ns=time.perf_counter_ns()-started,readonly_host_review_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,readonly_review_cost_outside_experiment=True,schema='actual-host-terminal-accounting-v83',kind=kind,status='verified',program_sha256=cfg['program'],
        captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scheduler_raw=raw,costs=costs,evidence=evidence,
        scheduler_cpu_ns=sum(x['scheduler_cpu_ns'] for x in costs.values()),observed_process_tree_cpu_ns=sum(x['observed_process_tree_cpu_ns'] for x in costs.values()),
        overlapping_clocks_not_summed=True,inputs=inputs.files,payloads=inputs.payloads)
    print(json.dumps(output,sort_keys=True,separators=(',',':'),allow_nan=False))
if __name__=='__main__':main(sys.argv[1])
