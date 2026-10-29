"""Exact prospective admission paths; large reports are explicit exceptions."""
from research_v90.records import Records, SMALL_BYTES, REPORT_BYTES
from research_v90.storage_plan import metadata_layout
from research_v99.config import RUN, TARGET_FILES

LAYOUT = metadata_layout('admission')
# A canonical terminal report supplied during staging is bound by program.json.
# It occupies the gates/v89-terminal.json allowance in the inherited census.
LAYOUT['preparation-storage.json'] = SMALL_BYTES
LAYOUT['software-results.json'] = SMALL_BYTES


def writer(root=None):
    return Records(RUN if root is None else root, LAYOUT)


def target_writer(root):
    return Records(root, {**{n:32*2**20 for n in TARGET_FILES}, 'completion.json':REPORT_BYTES})


def transaction_writer(root):
    return Records(root, {'plan.json':SMALL_BYTES, 'transaction.json':SMALL_BYTES})
