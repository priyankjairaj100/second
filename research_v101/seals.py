"""Verify complete target-admission seals/debits and actual target artifacts."""
import json,sys
from pathlib import Path
from research_v80.io import read,json_read,require
from research_v81.profile import validate_geometry,PROFILES,PROPOSED_GRID_CAP
from research_v81.resource_review import review
from research_v61.target import BoundTarget
from src.run_store import canonical_json,digest
from research_v90.run_store import read_completed
from research_v101.config import TARGET_FILES
from research_v101.contracts import target_contract
from src.worker_control import THREAD_VARIABLES
from research_v82.admission_reports import verify_reports
from research_v80.implementation_audit import verify_implementation
from research_v61.postrun import verify_kernel
ARTIFACTS={'records.json','selection.json','anchor-target.json','service-target.json','calibration-target.json',
    'execution-provenance.json','structural-admission.json','actual-admission.json'}

def verify(root,program,expected,snapshot):
    base=Path('/nfs_home/users/poonam/second-20261010');debits=set();previous={};models={};chosen=None
    for profile in ('distilgpt2','gpt2'):
        d=root/profile;plan=json_read(d/'plan.json');tx=json_read(d/'transaction.json');identity=json_read(d/'worker/identity.json')
        command=[sys.executable,'-B',str(root/'research_v101/target_worker.py'),str(d/'plan.json')]
        require(identity['identity']==dict(program_sha256=expected,profile=profile) and identity['cwd']==str(base)
            and identity['command']==command,'Target sealed identity differs')
        limits=identity['limits']
        contract=target_contract(profile,expected,tx['slurm_job_id'],limits['affinity_cpus'][0],root=root,cwd=base)
        require(plan==contract['plan'] and command==contract['command'] and limits==contract['limits'].payload(), 'Shared literal target contract differs')
        require(limits['cpu_seconds']==600 and limits['wall_seconds']==900 and limits['address_space_bytes']==16*2**30
            and limits['file_size_bytes']==2*2**30 and limits['threads']==1 and len(limits['affinity_cpus'])==1,'Target worker caps differ')
        require(identity['phase_budget']==dict(binding_sha256=snapshot['binding_sha256'],phase='admission',directory=str(root/'budget')),'Target ledger binding differs')
        sealed=read_completed(d/'worker',identity)
        require(sealed is not None and sealed['attempt']=='attempt-0001' and sealed['outcome']==tx['worker_outcome'] and sealed['outcome']['status']=='complete'
            and sealed['outcome']['returncode']==0,'Complete sealed target outcome required')
        request=json_read(d/'worker'/sealed['attempt']/'request.json');ack=json_read(d/'worker'/sealed['attempt']/'limits-applied.json')
        require(request['command']==command and request['cwd']==str(base) and request['limits']==limits
            and ack==sealed['limits_applied'] and ack['request_sha256']==digest(canonical_json(request))
            and ack['cpu_seconds']==[600,601] and ack['address_space']==[16*2**30]*2 and ack['file_size']==[2*2**30]*2
            and ack['affinity_cpus']==limits['affinity_cpus'] and ack['thread_environment']=={k:'1' for k in THREAD_VARIABLES},'Actual target limit acknowledgment differs')
        debit=sealed['budget_attempt_id'];usage=sealed['resource_usage'];b=sealed['budget_debit']
        require(all(type(usage.get(k)) is int and usage[k]>=0 for k in ('user_cpu_ns','system_cpu_ns','total_cpu_ns')),'Invalid actual CPU usage')
        require(debit not in debits and snapshot['attempts'].get(debit)==b and b['state']=='settled'
            and b['observed_cpu_ns']==usage['total_cpu_ns']==usage['user_cpu_ns']+usage['system_cpu_ns']
            and b['reserved_cpu_seconds']==602 and b['charged_cpu_seconds']<=602 and sealed['budget_reservation_overrun'] is False,'Target debit differs')
        debits.add(debit);previous[debit]=b
        prefix=dict(binding_sha256=snapshot['binding_sha256'],phase_cpu_seconds=snapshot['phase_cpu_seconds'],charged_cpu_seconds={'admission':sum(x['charged_cpu_seconds'] for x in previous.values())},attempts=dict(previous),over_cap={'admission':False})
        require(canonical_json(tx['budget'])==canonical_json(prefix),'Target prefix ledger differs')
        output=d/'outputs';c=json_read(output/'completion.json')
        require(plan==dict(profile=profile,program=str(root/'program.json'),program_sha256=expected,output=str(output),slurm_job_id=tx['slurm_job_id'])
            and c['job_id']==plan['slurm_job_id'] and c['program_sha256']==expected and c['status']=='complete' and c['profile']==profile,'Target completion/job differs')
        require(c['schema']=='actual-matched-target-admission-v101', 'Actual new target schema required')
        require({f.name for f in output.iterdir()}==set(TARGET_FILES)|{'completion.json'}, 'Unexpected target output file')
        require(c['neural_execution'] is False and c['calibration_execution'] is False and c['request_benchmark'] is False
            and c['quality_evaluation'] is False and set(c['artifacts'])==ARTIFACTS,'Admission artifact census/scope differs')
        for name,e in c['artifacts'].items():read(output/name,{k:e[k] for k in ('bytes','sha256')},32*2**20,retain=False)
        bound=BoundTarget(read(output/'anchor-target.json'),read(output/'service-target.json'))
        require(validate_geometry(json.loads(bound.anchor_payload),profile)==profile and json.loads(bound.anchor_payload)['recipe']['max_grid_entries']==PROPOSED_GRID_CAP,'Actual target/grid profile differs')
        require(c['stage_count']==len(bound.stages)==4*PROFILES[profile]['blocks'] and c['code_count']==sum(s.rows*s.width for s in bound.stages)==7077888*PROFILES[profile]['blocks'],'Actual complete target extent differs')
        require(c['base_target_sha256']==digest(bound.anchor_payload) and c['service_target_sha256']==digest(bound.fixed_payload)
            and c['calibration_target_sha256']==bound.calibration_target_sha256==digest(read(output/'calibration-target.json')),'Actual target commitments differ')
        execution=json_read(output/'execution-provenance.json')
        require(execution['checkpoint']['files_sha256']==PROFILES[profile]['checkpoint_files']
            and execution['anchor_target_sha256']==digest(bound.anchor_payload) and execution['target_sha256']==digest(bound.fixed_payload)
            and execution['calibration_target_sha256']==bound.calibration_target_sha256,'Execution checkpoint/target binding differs')
        require(json_read(output/'structural-admission.json')==review(bound.anchor_payload),'Actual-manifest structural assessment differs')
        verify_reports(json_read(output/'actual-admission.json'),profile,[s.stage_id for s in bound.stages],digest(bound.fixed_payload))
        verify_kernel(c['implementation']['primal'])
        verify_implementation('prepare',c['implementation'],c['implementation']['primal'])
        selection=read(output/'selection.json');records=read(output/'records.json')
        pair=(selection,records);require(chosen is None or chosen==pair,'Matched rows/selection differ');chosen=pair
        models[profile]=c
    require(debits==set(snapshot['attempts']),'Unexpected or missing target debit')
    return dict(schema='matched-target-seals-v101',models=models,actual_targets_verified=True,sealed_workers_verified=True,matched_records_verified=True,
        numerical_model_transfer=False,terminal_host_accounting_required=True)
