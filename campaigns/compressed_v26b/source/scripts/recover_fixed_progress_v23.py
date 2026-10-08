"""Recover terminal metadata from sealed evidence; never rewrite raw evidence."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.run_store import canonical_json,digest
from src.experiment_inventory import source_hashes
from src.compact_state import parse
from src.compact_service import model_digest


def main():
    campaign=ROOT/'campaigns/fixed_feature_v23';base=campaign/'attempts/cold-001'
    paths=dict(raw_progress=base/'outputs/progress.json',receipt=base/'worker/result.json',
        stdout_summary=base/'worker/attempt-0001/stdout-summary.json',
        transaction=base/'transaction.json',plan=base/'plan.json',model=base/'outputs/model.bin')
    raw={key:path.read_bytes() for key,path in paths.items()}
    progress=json.loads(raw['raw_progress']);receipt=json.loads(raw['receipt'])
    stdout=json.loads(raw['stdout_summary']);tx=json.loads(raw['transaction']);plan=json.loads(raw['plan'])
    assert progress['status']=='running' and progress['phases'][-1]['phase']=='model_write_started'
    assert receipt['outcome']['status']=='complete' and receipt['outcome']['returncode']==0
    assert receipt['budget_debit']['state']=='settled'
    assert receipt['worker_identity']['plan_sha256']==digest(raw['plan'])==progress['plan_sha256']
    assert tx['receipt_sha256']==digest(raw['receipt'])
    assert source_hashes(campaign/'source')==plan['source_sha256']
    assert receipt['artifacts']['stdout-summary.json']['sha256']==digest(raw['stdout_summary'])
    log=stdout['tail_utf8'].encode()
    assert len(log)==stdout['bytes']<=stdout['tail_max_bytes'] and digest(log)==stdout['sha256']
    events=[json.loads(line) for line in log.splitlines()]
    assert events[:len(progress['phases'])]==progress['phases']
    assert len(events)==len(progress['phases'])+2
    assert [event['phase'] for event in events[-2:]]==['model_write_complete','complete']
    assert events[-2]['bytes']==len(raw['model'])
    model=parse(raw['model']);assert not model.factors and len(model.stages)==24
    assert model.target_sha256==progress['fixed_target_sha256']
    assert model_digest(model.stages)==progress['model_sha256']
    assert sum(s.rows*s.columns for s in model.stages)==42467328
    effective=dict(progress,status='complete',complete_model=True,complete_state=False,phases=events,
        model_artifact=dict(file='model.bin',bytes=len(raw['model']),sha256=digest(raw['model'])),
        recovered_terminal_metadata=True,
        recovery_unavailable=['original final progress bytes','original worker_transaction_elapsed_ns'])
    sidecar=dict(schema='sealed-terminal-metadata-recovery-v23',attempt_id='cold-001',
        cause='unknown; saved progress later observed as an earlier prefix despite sealed terminal log',
        scope='metadata recovery only; no rerun, model change, timing change, or scientific promotion',
        evidence={key:dict(path=str(path.relative_to(campaign)),sha256=digest(raw[key])) for key,path in paths.items()},
        reconstructed_fields=['status','complete_model','complete_state','phases','model_artifact'],
        effective_progress=effective,analyzer_sha256=digest(Path(__file__).read_bytes()))
    target=campaign/'recoveries/cold-001.json';target.parent.mkdir(exist_ok=True)
    encoded=canonical_json(sidecar)
    if target.exists() and target.read_bytes()!=encoded:raise ValueError('cannot overwrite differing recovery')
    target.write_bytes(encoded)
    print(json.dumps(dict(recovered=True,sha256=digest(encoded),rerun=False,missing_internal_timer=True)))


if __name__=='__main__':main()
