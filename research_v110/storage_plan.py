"""Source-bound finite diagnostic write allowance, not a disk reservation."""
from research_v80.io import require
from research_v110.config import ROOT, RUN, OPERATIONS
from research_v110.records import LAYOUT
MIB=2**20
GIB=2**30


def build(sources,archive_bytes):
    require(0<len(sources)<4096 and sum(e['bytes'] for e in sources.values())<=64*MIB
        and type(archive_bytes) is int and 0<archive_bytes<=64*MIB,'Bounded sources required')
    return dict(schema='token-stage-write-plan-v110',
        staging_bytes=2*archive_bytes+2*sum(e['bytes'] for e in sources.values()),
        staging_files=2+2*len(sources),metadata_bytes=sum(LAYOUT.values()),
        metadata_files=len(LAYOUT),operation_log_bytes=68*MIB,
        diagnostic_output_bytes=4*MIB,diagnostic_output_files=3,
        controller_ledger_bytes=32*MIB,controller_ledger_files=64,
        temporary_bytes=12*GIB,temporary_files=16386,
        capacity_reserved=False,formal_disk_bound=False,old_outputs_credited_as_free=False,
        external_slurm_writer_limit_enforced=False)


def requests(plan,sources,archive_bytes,operation=None):
    require(plan==build(sources,archive_bytes),'Exact source-bound write plan required')
    require(operation is None or operation in OPERATIONS,'Known operation required')
    def extent(size,files):
        logical=size+files*4096
        return dict(required_bytes=logical+(logical+3)//4+GIB,required_files=files+4096)
    size=plan['metadata_bytes']+2*plan['operation_log_bytes']+plan['diagnostic_output_bytes']+plan['controller_ledger_bytes']
    files=plan['metadata_files']+4+plan['diagnostic_output_files']+plan['controller_ledger_files']
    if operation is None:
        size+=plan['staging_bytes'];files+=plan['staging_files']
    return dict(project=dict(path=str(ROOT/'local_runs' if operation is None else RUN),**extent(size,files)),
        temporary=dict(path='/tmp',**extent(plan['temporary_bytes'],plan['temporary_files'])))
