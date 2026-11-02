"""Exclusive finite census for two allocations and one diagnostic."""
from research_v90.records import Records, SMALL_BYTES
from research_v110.config import RUN, OPERATIONS

LAYOUT = {n: SMALL_BYTES for n in ('program.json', 'registration.json',
    'preparation-storage.json', 'software-results.json')}
for mode in ('checks', 'chain'):
    for tail in ('chain-intent', 'held-chain', 'released-chain'):
        LAYOUT[f'{mode}-{tail}.json'] = SMALL_BYTES
for op in OPERATIONS:
    for tail in ('intent', 'response', 'submission', 'release', 'host-start',
                 'host', 'entry-start', 'entry', 'abort-intent', 'abort-response'):
        LAYOUT[f'{op}-{tail}.json'] = SMALL_BYTES


def writer(root=None):
    return Records(RUN if root is None else root, LAYOUT)


def transaction_writer(root):
    return Records(root, {'plan.json': SMALL_BYTES, 'transaction.json': SMALL_BYTES})
