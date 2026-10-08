"""Launch the registered changed-target quality screen within inherited costs."""
import hashlib,json,os,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import atomic_write,canonical_json,digest
from src.experiment_inventory import source_hashes
from src.pilot_budget import inherited_allowance,research_worker_lock
from src.phase_budget import PhaseBudget
from src.worker_control import WorkerLimits,run_limited


def main():
    root=Path(__file__).resolve().parents[1];archive=root/'pilots/v21'
    raw=(archive/'program.json').read_bytes();program=json.loads(raw)
    if program['status']!='prospectively_registered' or program['scope']!='explicit_new_target_quality_screen':raise ValueError('unexpected program')
    attempt=archive/program['attempt_id']
    if attempt.exists():raise ValueError('cannot overwrite an attempt')
    used,left=inherited_allowance(root);cap=program['cpu_seconds']
    if type(cap) is not int or not 1<=cap<=240 or left<cap+2:raise ValueError('inherited allowance insufficient')
    inputs={}
    for name,entry in program['inputs'].items():
        path=root/entry['path']
        with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=entry['sha256']:raise ValueError('registered input changed: '+name)
        inputs[name]=dict(entry,path=str(path))
    snapshot=attempt/'source';snapshot.mkdir(parents=True)
    for folder in ('src','scripts'):
        (snapshot/folder).mkdir()
        for path in (root/folder).glob('*.py'):shutil.copyfile(path,snapshot/folder/path.name)
    policy=dict(schema='fixed-quality-policy-v21',program_sha256=digest(raw),cpu_seconds=cap,wall_seconds=cap,
        inherited_cap_cpu_seconds=10800,prior_charged_cpu_seconds=used,remaining_allowance_cpu_seconds=left,
        scientific_promotion=False,confirmation=False,repair_timing=False,scope=program['scope'],
        os_cache='uncontrolled',other_machine_activity='uncontrolled')
    protocol=canonical_json(policy);atomic_write(attempt/'protocol.json',protocol);atomic_write(attempt/'program.json',raw)
    plan=dict(program=program,program_sha256=digest(raw),inputs=inputs,source_sha256=source_hashes(snapshot),
        checkpoint=str(root/'tmp/models/distilgpt2'),output=str(attempt/'outputs'),protocol_sha256=digest(protocol))
    path=attempt/'plan.json';atomic_write(path,canonical_json(plan))
    from src.runtime_contract import capture_runtime_contract
    atomic_write(attempt/'runtime.json',canonical_json(capture_runtime_contract()))
    budget=PhaseBudget(attempt/'phase-cpu-budget',identity={'protocol_sha256':digest(protocol),'source_sha256':plan['source_sha256']},phase_cpu_seconds={'feasibility':left})
    receipt=run_limited([sys.executable,str(snapshot/'scripts/run_fixed_quality_v21.py'),str(path)],attempt/'worker',
        WorkerLimits(cap,cap,6*2**30,1,(min(os.sched_getaffinity(0)),)),identity={'pilot':'new-fixed-anchor-quality-v21','plan_sha256':digest(path.read_bytes())},cwd=snapshot,phase_budget=budget,phase='feasibility')
    print(json.dumps({k:receipt.get(k) for k in ('outcome','budget_debit','resource_usage')}))

if __name__=='__main__':
    with research_worker_lock(Path(__file__).resolve().parents[1]):main()
