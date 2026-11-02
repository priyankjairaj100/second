"""Read-only reuse of the frozen V45 selection, without rerunning its sampler.

The old data-phase verifier intentionally compares the then-current inventory
exactly. Later experiment archives add entries; replaying that live-inventory
predicate is inappropriate for reuse of already selected adaptive inputs.
Every original history file, selection commitment, policy, source and runtime
must still match. Additions are disclosed as later history, never new evidence
of disjointness or new selection. Nothing in the old data phase is modified.
"""
from pathlib import Path
from research_v43.campaign import ROOT, read, sha, require
from research_v44.campaign import runtime
from research_v45 import data_phase
from research_v45.data import inventory, POLICY

PROGRAM='4bd64a67eb44151d09d3552231630ab41a937e17e2709b662e93fc542fa994f0'


def compare_history(original,current):
    require(type(original) is dict and type(current) is dict,'History inventories must be objects')
    require(all(k in current and current[k]==v for k,v in original.items()),
        'Original historical input is missing or changed')
    return dict(original_entries=len(original),current_entries=len(current),
        original_entries_unchanged=True,added={k:current[k] for k in sorted(set(current)-set(original))},
        new_independence_claim=False,sampling_reexecuted=False)


def history_delta(original):
    return compare_history(original,inventory())


def validate_archive(directory):
    d=Path(directory).resolve();p=read(d/'program.json')
    require(sha(d/'program.json')==PROGRAM and read(d/'registration.json')['program_sha256']==PROGRAM,
        'Frozen V45 data registration changed')
    require(p['directory']==str(d) and p['policy']==POLICY and p['sources']==data_phase.sources(),
        'Frozen data directory, policy or sources changed')
    require(p['runtime']==runtime(),'Frozen data runtime changed')
    history_delta(p['history'])
    # The caller additionally validates completion, sealed receipts, data bytes,
    # selected metadata, exclusions, both acquired prefixes and exact13x128 shape.
    return p
