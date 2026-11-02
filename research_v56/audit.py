"""Read-only audit of actual V56 CUDA losses and sealed CPU accounting."""
import os
from pathlib import Path
import sys
import time
from research_v56.campaign import ROOT,verify,require,bound,new
from research_v54.postrun import Inputs,bind_ledger_snapshot
from research_v46.evaluator import compare
from src.run_store import canonical_json,digest,read_completed
from src.phase_budget import read_budget_snapshot
from src.experiment_inventory import source_hashes


def audit(directory,output):
    require(os.environ.get('SLURM_JOB_ID'),'Bounded GPU allocation required')
    directory,output=Path(directory).resolve(),Path(output).resolve()
    require(not output.exists(),'Fresh audit receipt required')
    tick,cpu=time.perf_counter_ns(),time.process_time_ns();inputs=Inputs()
    p=inputs.json(directory/'program.json');ph=digest(canonical_json(p))
    require(verify(directory)==p and inputs.json(directory/'registration.json')['program_sha256']==ph,'GPU registration differs')
    for e in p['inputs'].values():
        require(inputs.read(bound(e),retain=False)=={k:e[k] for k in ('sha256','bytes')},'GPU bound input differs')
    snapshot=read_budget_snapshot(directory/'budget',identity=dict(protocol_sha256=ph,source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'development':p['phase_cpu_seconds']})
    require(snapshot['status']=='verified' and not snapshot['reserved_unknown_attempts'] and not any(snapshot['over_cap'].values()),
        'GPU worker CPU budget unsettled or exceeded')
    bind_ledger_snapshot(directory,snapshot,inputs)
    root=directory/'parity';identity=inputs.json(root/'worker/identity.json')
    tx=inputs.json(root/'transaction.json');plan=inputs.json(root/'plan.json')
    require(identity['identity']==dict(program_sha256=ph) and identity['cwd']==str(ROOT) and
        identity['command']==[sys.executable,'-B','-m','research_v56.worker',str(root/'plan.json')] and
        identity['phase_budget']==dict(directory=str(directory/'budget'),phase='development',binding_sha256=snapshot['binding_sha256']),
        'GPU worker command or CPU phase differs')
    limits=identity['limits']
    require(all(limits[k]==p[k] for k in ('cpu_seconds','wall_seconds','address_space_bytes','file_size_bytes','threads'))
        and len(limits['affinity_cpus'])==1,'GPU worker resource limits differ')
    sealed=read_completed(root/'worker',identity)
    require(sealed is not None and sealed['outcome']==tx['worker_outcome'] and
        sealed['outcome']['status']=='complete' and sealed['outcome']['returncode']==0,'GPU worker incomplete')
    require(sealed==inputs.json(root/'worker/result.json')==inputs.json(root/'worker'/sealed['attempt']/'status.json'),'GPU final seal differs')
    for name,entry in sealed['artifacts'].items():
        require(inputs.read(root/'worker'/sealed['attempt']/name,retain=False)==entry,'Sealed GPU artifact differs')
    require(snapshot['attempts']=={sealed['budget_attempt_id']:sealed['budget_debit']} and
        sealed['budget_debit']['observed_cpu_ns']==sealed['resource_usage']['total_cpu_ns'], 'GPU CPU charge differs')
    require(all(tx['budget'][k]==snapshot[k] for k in tx['budget']),'GPU transaction budget differs')
    require(plan==dict(program=str(directory/'program.json'),program_sha256=ph,output=str(root/'outputs'),slurm_job_id=tx['slurm_job_id']),
        'GPU plan differs')
    c=inputs.json(root/'outputs/completion.json');reference=inputs.json(bound(p['inputs']['cpu_completion']))
    require(c['schema']=='cuda-likelihood-parity-result-v56' and c['status']=='complete' and c['valid_diagnostic'] is True and
        c['program_sha256']==ph and c['slurm_job_id']==tx['slurm_job_id'] and c['dtype']=='float64' and c['tf32'] is False
        and c['amp'] is False and c['deterministic_algorithms'] is True and c['copied_arrays_with_bitwise_roundtrip']==150
        and c['peak_cuda_reserved_bytes']<=p['gpu_allocator_bytes'] and c['first_actual_batch_parity_passed'] is True
        and c['cpu_development_guards_pass']==reference['development_guards_pass'] and c['confirmation'] is False
        and c['certified_inference'] is False and c['exact_calibration_equivalence'] is False,'GPU completion extent or scope differs')
    parity=compare(c['quality'],reference['quality'],[r['id'] for r in p['records']],p['threshold'])
    require(parity==c['parity'] and parity['passed']==c['parity_passed'] and len(parity['checks'])==32,'GPU parity summary differs')
    inputs.unchanged()
    result=dict(schema='cuda-likelihood-artifact-audit-v56',status='verified',campaign=str(directory),program_sha256=ph,
        parity=parity,parity_passed=parity['passed'],cpu_development_guards_pass=reference['development_guards_pass'],
        inputs=inputs.files,budget=snapshot,source_sha256=p['sources'],slurm_job_id=os.environ['SLURM_JOB_ID'],
        analysis_cpu_ns=time.process_time_ns()-cpu,analysis_elapsed_ns=time.perf_counter_ns()-tick,
        analysis_outside_empirical_worker_ledger=True,confirmation=False,acl_ready=False,exact_calibration_equivalence=False,
        scope='32 actual same-model exposed NLL comparisons and CPU accounting verified; no independent inference rerun, certified feature/calibration equivalence or controlled speed claim.')
    new(output,result);print(canonical_json(dict(status='verified',parity_passed=parity['passed'])).decode())
    return result
