"""Prospective read-only sealed outcome and exact ledger verification."""
from research_v100.config import ROOT,RUN,TRIALS
from research_v100.campaign import command
from research_v100.config import expected_artifacts
from research_v80.implementation_audit import verify_implementation
from research_v61.postrun import verify_kernel
from research_v80.io import require
from src.run_store import canonical_json,digest
from research_v90.run_store import read_completed
from src.worker_control import THREAD_VARIABLES

def verify(p,inputs,snapshot):
    result={};seen={};program_sha=digest(canonical_json(p))
    for trial in p['trial_order']:
        root=RUN/trial;identity=inputs.json(root/'worker/identity.json');tx=inputs.json(root/'transaction.json');plan=inputs.json(root/'plan.json');limits=identity['limits']
        require(identity['identity']==dict(program_sha256=program_sha,trial=trial) and identity['command']==command(root/'plan.json') and identity['cwd']==str(ROOT),'Worker identity differs')
        require(all(limits[k]==v for k,v in TRIALS[trial].items()) and limits['address_space_bytes']==16*2**30 and limits['file_size_bytes']==2*2**30 and limits['threads']==1 and len(limits['affinity_cpus'])==1,'Worker caps differ')
        require(identity['phase_budget']==dict(binding_sha256=snapshot['binding_sha256'],phase='feasibility',directory=str(RUN/'budget')),'Worker budget binding differs')
        seal=read_completed(root/'worker',identity)
        require(seal is not None and seal['attempt']=='attempt-0001' and seal==inputs.json(root/'worker/result.json')==inputs.json(root/'worker'/seal['attempt']/'status.json') and seal['outcome']==tx['worker_outcome'] and seal['outcome']['status']=='complete' and seal['outcome']['returncode']==0,'Actual successful seal required')
        for name,e in seal['artifacts'].items():require(inputs.read(root/'worker'/seal['attempt']/name,retain=False)==e,'Sealed artifact changed')
        request=inputs.json(root/'worker'/seal['attempt']/'request.json');ack=inputs.json(root/'worker'/seal['attempt']/'limits-applied.json')
        require(request['command']==identity['command'] and request['cwd']==str(ROOT) and request['limits']==limits and ack==seal['limits_applied'] and ack['request_sha256']==digest(canonical_json(request)) and ack['cpu_seconds']==[limits['cpu_seconds'],limits['cpu_seconds']+1] and ack['address_space']==[16*2**30]*2 and ack['file_size']==[2*2**30]*2 and ack['affinity_cpus']==limits['affinity_cpus'] and ack['thread_environment']=={k:'1' for k in THREAD_VARIABLES},'Actual limit acknowledgment differs')
        bid=seal['budget_attempt_id'];b=seal['budget_debit'];u=seal['resource_usage']
        require(all(type(u.get(k)) is int and u[k]>=0 for k in ('total_cpu_ns','user_cpu_ns','system_cpu_ns')),'Invalid CPU record')
        require(bid not in seen and snapshot['attempts'].get(bid)==b and b['state']=='settled' and b['observed_cpu_ns']==u['total_cpu_ns']==u['user_cpu_ns']+u['system_cpu_ns'] and b['charged_cpu_seconds']==max(1,(u['total_cpu_ns']+10**9-1)//10**9)<=limits['cpu_seconds']+2 and b['reserved_cpu_seconds']==limits['cpu_seconds']+2 and seal['budget_reservation_overrun'] is False,'Exact settled debit differs')
        seen[bid]=b
        prefix=dict(binding_sha256=snapshot['binding_sha256'],phase_cpu_seconds=snapshot['phase_cpu_seconds'],charged_cpu_seconds={'feasibility':sum(x['charged_cpu_seconds'] for x in seen.values())},attempts=dict(seen),over_cap={'feasibility':False})
        require(tx['budget']==prefix,'Transaction prefix ledger differs')
        require(plan==dict(trial=trial,program=str(RUN/'program.json'),program_sha256=program_sha,output=str(root/'outputs'),slurm_job_id=tx['slurm_job_id']),'Worker literal plan differs')
        q=inputs.json(root/'outputs/completion.json');result[trial]=q
        require(q['schema']=='matched-complete-service-worker-v100' and q['status']=='complete' and q['complete_model'] is True and q['program_sha256']==program_sha and q['slurm_job_id']==plan['slurm_job_id'] and q['trial']==trial and q['profile']==trial.split('/')[0] and q['source_files_sha256']==digest(canonical_json(p['sources'])),'Complete actual matched result differs')
        require(set(q['artifacts'])==expected_artifacts(trial),'Complete worker artifact census differs')
        for name,e in q['artifacts'].items():require(e==dict(file=name,**inputs.read(root/'outputs'/name,retain=False)),'Worker artifact bytes differ')
        verify_kernel(q['shared_primal_kernel']);verify_implementation(trial.split('/')[1],q['implementation'],q['shared_primal_kernel'])
    require(set(seen)==set(snapshot['attempts']),'Every matched ledger attempt required')
    return result
