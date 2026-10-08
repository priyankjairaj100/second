"""Execute only the frozen V23 sequence, stopping at its first blocked step."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.run_store import atomic_write,canonical_json,digest


def main():
    campaign=ROOT/'campaigns/fixed_feature_v23'
    raw=(campaign/'program.json').read_bytes();program=json.loads(raw)
    status=dict(schema='fixed-timing-continuation-v23',program_sha256=digest(raw),
        controller_sha256=digest(Path(__file__).read_bytes()),attempts=[],status='running')
    for index,trial in enumerate(program['trials']):
        attempt=campaign/'attempts'/trial['id']
        if attempt.exists():
            receipt=attempt/'worker/result.json'
            if not receipt.exists():raise ValueError('an existing unsettled attempt blocks continuation')
            value=json.loads(receipt.read_bytes())
            if value['outcome']['status']!='complete':raise ValueError('a failed attempt blocks continuation')
            status['attempts'].append(dict(id=trial['id'],status='previously_complete'))
            continue
        print(json.dumps(dict(starting=trial['id'])),flush=True)
        worker=subprocess.run([sys.executable,str(ROOT/'scripts/launch_fixed_timing_v23.py'),'--id',trial['id']],
            cwd=ROOT,capture_output=True,text=True)
        if worker.returncode:
            status.update(status='stopped',reason=worker.stderr.strip(),
                unstarted=[row['id'] for row in program['trials'][index:]])
            break
        value=json.loads((attempt/'transaction.json').read_bytes())
        archive_start=time.perf_counter_ns()
        progress_path=attempt/'outputs/progress.json'
        if progress_path.exists():
            progress_raw=progress_path.read_bytes()
            atomic_write(attempt/'sealed-progress.json',progress_raw)
            atomic_write(attempt/'postclock-archive.json',canonical_json(dict(
                scope='auxiliary archival after primary transaction clock; no model execution',
                progress_sha256=digest(progress_raw),transaction_sha256=digest((attempt/'transaction.json').read_bytes()),
                elapsed_ns=time.perf_counter_ns()-archive_start)))
        row=dict(id=trial['id'],status=value['worker_outcome']['status'],
            seconds=value['outer_transaction_elapsed_ns']/1e9,
            charged_cpu_seconds=value['budget_debit']['charged_cpu_seconds'])
        status['attempts'].append(row);print(json.dumps(row),flush=True)
        if row['status']!='complete':
            status.update(status='stopped',reason='worker failed',
                unstarted=[r['id'] for r in program['trials'][index+1:]])
            break
        atomic_write(campaign/'continuation.json',canonical_json(status))
    else:status.update(status='complete',unstarted=[])
    atomic_write(campaign/'continuation.json',canonical_json(status))
    print(json.dumps(dict(status=status['status'],unstarted=status.get('unstarted',[]),reason=status.get('reason'))),flush=True)


if __name__=='__main__':main()
