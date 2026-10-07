"""Execute the registered diagnostic slots serially, preserving every outcome."""
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json,atomic_write,digest
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'pilots/v13'


def settled(identifier):
    p=ARCHIVE/identifier/'phase-cpu-budget/ledger.json'
    if not p.exists():return False
    attempts=json.loads(p.read_bytes())['attempts']
    receipt=ARCHIVE/identifier/'worker/result.json'
    if not receipt.exists():return False
    result=json.loads(receipt.read_bytes())
    return (bool(attempts) and all(row['state']=='settled' for row in attempts.values())
            and result.get('budget_debit',{}).get('state')=='settled')


def completed(identifier):
    p=ARCHIVE/identifier/'worker/result.json'
    if not settled(identifier) or not p.exists():return False
    return json.loads(p.read_bytes()).get('outcome',{}).get('status')=='complete'


def output(identifier):return json.loads((ARCHIVE/identifier/'outputs/progress.json').read_bytes())


def main():
    program=ARCHIVE/'prospective-program.json'
    data=json.loads(program.read_bytes())
    status=dict(schema='v13-diagnostic-program-outcomes',program_sha256=digest(program.read_bytes()),slots=[],scientific_promotion=False)
    def save():atomic_write(ARCHIVE/'program-outcomes.json',canonical_json(status))
    # A previously admitted preparation can finish before this serial driver starts.
    before=time.monotonic()
    while not settled('attempt-002'):
        if time.monotonic()-before>930:raise TimeoutError('preparation settlement did not appear')
        time.sleep(5)
    for slot in data['attempts']:
        identifier=slot['id'];role=slot['role']
        if identifier in ('attempt-001','attempt-002'):
            status['slots'].append(dict(id=identifier,role=role,status='complete' if completed(identifier) else 'failed'));save();continue
        reason=None
        if not completed('attempt-002'):reason='preparation failed'
        if slot.get('prior') and not completed(slot['prior']):reason='required predecessor failed'
        if role=='prospective_quality_control':
            comparison=[output(x) for x in ('attempt-003','attempt-004','attempt-005','attempt-006') if completed(x)]
            if len(comparison)!=4 or len({x['model_sha256'] for x in comparison})!=1:
                reason='complete four-method model agreement missing'
            elif len({x['state_artifact']['sha256'] for x in comparison if x['complete_state']})!=1:
                reason='canonical state agreement missing'
        if reason:
            status['slots'].append(dict(id=identifier,role=role,status='unstarted',reason=reason));save();continue
        method='repair' if role in ('sequential_delete_to_empty','combined_delete_to_empty') else 'quality' if role=='prospective_quality_control' else role
        command=[sys.executable,str(ROOT/'scripts/launch_compact_service_pilot.py'),'--id',identifier,'--method',method]
        for index in slot.get('delete_indices',[]):command.extend(['--delete-index',str(index)])
        if slot.get('prior'):command.extend(['--prior-attempt',slot['prior']])
        if (ARCHIVE/identifier).exists():
            if not settled(identifier):raise ValueError('existing unsettled slot requires inspection')
        else:
            print(json.dumps(dict(event='launch',id=identifier,method=method)),flush=True)
            code=subprocess.run(command,cwd=ROOT).returncode
            if code and not (ARCHIVE/identifier).exists():
                status['slots'].append(dict(id=identifier,role=role,status='unstarted',reason='admission rejected',launcher_returncode=code));save();continue
        status['slots'].append(dict(id=identifier,role=role,status='complete' if completed(identifier) else 'failed'));save()
    status['status']='settled';save()
    print(json.dumps(status),flush=True)


if __name__=='__main__':main()
