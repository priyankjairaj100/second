"""Cold reconstruction and atomic publication with no persistent feature cache."""
import gc
import json
import os
import time
from pathlib import Path
from research_v135 import source_state
from research_v61.service import telemetry
from src.run_store import canonical_json, digest


def require(ok, message):
    if not ok:
        raise ValueError(message)


def reconstruct(service, records, hook=lambda phase: None):
    rows = [{'id': r.record_id, 'tokens': list(r.tokens)} for r in records]
    require(service.records(rows) == tuple(records), 'Source provenance or words differ')
    timing = telemetry()
    service.admit(rows, 'lossless')
    hook('after_proposal')
    old_mark = service.mark
    def mark(event, **kw):
        old_mark(event, **kw)
        if event == 'source_replayed':
            hook('during_replay')
    service.mark = mark
    try:
        values = service.extract(rows, timing)
    finally:
        service.mark = old_mark
    temporary = sum(v.nbytes for v in values.values())
    try:
        codes, admission = service.solve(rows, 'lossless', {}, {}, {}, timing,
                                        direct_values=values)
    finally:
        del values
        gc.collect()
    require(timing['neural_stage_record_pairs'] == len(records)*len(service.bound.stages),
            'Every retained source must traverse every stage once')
    return codes, dict(timing=timing, admission=admission,
                       temporary_feature_array_bytes=temporary,
                       retained_ids=[r.record_id for r in records],
                       persistent_features=False, persistent_gram=False)


def publish(destination, artifacts, hook=lambda phase: None):
    """Exclusive sibling scratch and rename; no published successor on refusal."""
    destination = Path(destination)
    require(not destination.exists() and not destination.is_symlink(),
            'Successor destination already exists')
    require(set(artifacts) == {'state.bin', 'model.bin', 'trust.json'}, 'Exact artifact set required')
    state = source_state._decode(artifacts['state.bin'])
    require(b''.join(c.packed_indices for c in state[2]) == artifacts['model.bin'],
            'Model differs from canonical state')
    require(artifacts['trust.json'] == b'{}', 'Source-only state has no Gram trust')
    scratch = destination.with_name('.'+destination.name+'.partial')
    scratch.mkdir(exist_ok=False)
    inventory = {}
    for name, data in artifacts.items():
        with (scratch/name).open('xb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        inventory[name] = dict(bytes=len(data), sha256=digest(data))
        require((scratch/name).read_bytes() == data, 'Published words differ')
    hook('before_seal')
    with (scratch/'manifest.json').open('xb') as f:
        f.write(canonical_json(inventory)); f.flush(); os.fsync(f.fileno())
    fd = os.open(scratch, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
    hook('before_publish')
    require(not destination.exists(), 'Concurrent publication refused')
    os.rename(scratch, destination)
    fd = os.open(destination.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return inventory


def repair(service, predecessor, retained_ids, destination, provider=None,
           hook=lambda phase: None):
    start = time.perf_counter_ns()
    before = digest(predecessor)
    view = source_state.select_retained(predecessor, retained_ids, provider)
    require(view.target == service.bound, 'Predecessor target differs')
    codes, result = reconstruct(service, view.records, hook)
    tick = time.perf_counter_ns()
    blob = source_state.successor(view, retained_ids, codes)
    result['serialization_ns'] = time.perf_counter_ns()-tick
    result['artifacts'] = publish(
        destination, {'state.bin': blob, 'model.bin': b''.join(c.packed_indices for c in codes),
                      'trust.json': b'{}'}, hook)
    require(digest(predecessor) == before, 'Predecessor mutated')
    result.update(request_elapsed_ns=time.perf_counter_ns()-start,
                  predecessor_sha256=before, mode=view.mode,
                  predecessor_bytes=len(predecessor), live_state_bytes=len(blob)+2,
                  canonical_state_bytes=len(blob), trust_bytes=2,
                  source_access='stored_tokens' if view.mode == 'tokens' else 'external_retained_references')
    return result
