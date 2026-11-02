"""Finite metadata paths for twenty workers and three enclosing operations."""
from research_v90.records import Records,SMALL_BYTES
from research_v90.storage_plan import metadata_layout
from research_v92.config import RUN
LAYOUT=metadata_layout('complete')
LAYOUT['preparation-storage.json']=SMALL_BYTES
LAYOUT['software-results.json']=SMALL_BYTES

def writer(root=None):return Records(RUN if root is None else root,LAYOUT)
def transaction_writer(root):return Records(root,{'plan.json':SMALL_BYTES,'transaction.json':SMALL_BYTES})
