"""Run the prospective matched batching controls after the reference program."""
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json,atomic_write,digest
from scripts.run_registered_v13 import ROOT,ARCHIVE,completed,settled,output


def main():
    started=time.monotonic();path=ARCHIVE/'program-outcomes.json'
    while not path.exists() or json.loads(path.read_bytes()).get('status')!='settled':
        if time.monotonic()-started>5400:raise TimeoutError('reference program did not settle')
        time.sleep(5)
    planpath=ARCHIVE/'prospective-batching.json';plan=json.loads(planpath.read_bytes())
    result=dict(schema='v13-batching-outcomes',plan_sha256=digest(planpath.read_bytes()),slots=[])
    ready=all(completed(x) for x in ('attempt-003','attempt-004','attempt-005','attempt-006'))
    if ready:
        rows=[output(x) for x in ('attempt-003','attempt-004','attempt-005','attempt-006')]
        ready=len({x['model_sha256'] for x in rows})==1 and len({x['state_artifact']['sha256'] for x in rows if x['complete_state']})==1
    for slot in plan['runs']:
        identifier=slot['id']
        if not ready:
            result['slots'].append(dict(id=identifier,status='unstarted',reason='reference correctness missing'));continue
        command=[sys.executable,str(ROOT/'scripts/launch_compact_service_pilot.py'),'--id',identifier,'--method',slot['method'],'--solver-backend','batched']
        for index in slot['delete_indices']:command.extend(['--delete-index',str(index)])
        if slot.get('prior'):command.extend(['--prior-attempt',slot['prior']])
        if (ARCHIVE/identifier).exists():
            if not settled(identifier):raise ValueError('unsettled existing followup requires inspection')
        else:
            print(json.dumps(dict(event='launch',id=identifier,method=slot['method'],solver_backend='batched')),flush=True)
            code=subprocess.run(command,cwd=ROOT).returncode
            if code and not (ARCHIVE/identifier).exists():
                result['slots'].append(dict(id=identifier,status='unstarted',reason='admission rejected'));continue
        result['slots'].append(dict(id=identifier,status='complete' if completed(identifier) else 'failed'))
        atomic_write(ARCHIVE/'batching-outcomes.json',canonical_json(result))
    result['status']='settled';atomic_write(ARCHIVE/'batching-outcomes.json',canonical_json(result));print(json.dumps(result),flush=True)


if __name__=='__main__':
    import fcntl
    with (ARCHIVE/'batching-controller.lock').open('a+b') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        main()
