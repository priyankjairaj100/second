"""Prospective integrated write census; no live admission without real gates."""
from research_v80.io import require
from research_v90.admission import ledger_identity
from research_v90.outputs import allowance,verify_progress_sources
from research_v100.config import ROOT,RUN,ORDER,OPERATIONS
from research_v100.records import LAYOUT
MIB=2**20
GIB=2**30

def build(sources,archive_bytes):
    ledger_identity('0'*64,sources);verify_progress_sources()
    require(0<len(sources)<4096 and sum(e['bytes'] for e in sources.values())<=64*MIB
        and type(archive_bytes) is int and 0<archive_bytes<=64*MIB,'Bounded source package required')
    roles=[dict(role='source_staging',bytes=2*archive_bytes+2*sum(e['bytes'] for e in sources.values()),
        files=2+2*len(sources),operation=None),dict(role='metadata',bytes=sum(LAYOUT.values()),files=len(LAYOUT),operation=None)]
    for operation in OPERATIONS:roles.append(dict(role='logs',bytes=68*MIB,files=2,operation=operation))
    for trial in ORDER:
        a=allowance(trial)
        roles.extend([dict(role='worker_outputs',bytes=a['output_bytes'],files=a['output_files'],operation=trial),
            dict(role='controller_ledger_overlap',bytes=32*MIB,files=64,operation=trial)])
    return dict(schema='complete-matched-write-plan-v100',roles=roles,
        temporary_roles=[dict(role='worker_streams',bytes=4*GIB,files=2),dict(role='native_builds',bytes=4*GIB,files=8192),
            dict(role='software_fixtures',bytes=4*GIB,files=8192)],formal_disk_bound=False,capacity_reserved=False,
        measured_peak=False,external_slurm_writer_limit_enforced=False,old_outputs_credited_as_free=False)

def requests(plan,sources,archive_bytes,operation=None):
    require(plan==build(sources,archive_bytes),'Exact integrated source-bound write plan required')
    require(operation is None or operation in OPERATIONS,'Known matched operation required')
    remaining=set(OPERATIONS if operation is None else OPERATIONS[OPERATIONS.index(operation):])
    roles=[r for r in plan['roles'] if (r['operation'] is None or r['operation'] in remaining)
        and (operation is None or r['role']!='source_staging')]
    def extent(rows):
        files=sum(r['files'] for r in rows);logical=sum(r['bytes'] for r in rows)+files*4096
        return dict(required_bytes=logical+(logical+3)//4+GIB,required_files=files+4096)
    return dict(project=dict(path=str(ROOT/'local_runs' if operation is None else RUN),**extent(roles)),
        temporary=dict(path='/tmp',**extent(plan['temporary_roles'])))
