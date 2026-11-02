"""Source-bound allowance for this five-allocation admission only.

The later twenty-worker screen needs its own implementation and capacity gate.
No V90 prospective full-screen allowance is promoted to launch admission here.
"""
from research_v80.io import require
from research_v90.admission import ledger_identity
from research_v99.config import ROOT, RUN, ORDER
from research_v99.records import LAYOUT
from research_v99.fetch import EXPECTED
MIB=2**20
GIB=2**30


def build(sources, archive_bytes):
    ledger_identity('0'*64,sources)
    require(0<len(sources)<4096 and sum(e['bytes'] for e in sources.values())<=64*MIB
        and type(archive_bytes) is int and 0<archive_bytes<=64*MIB,'Bounded exact source package required')
    roles=[dict(role='source_staging',bytes=2*archive_bytes+2*sum(e['bytes'] for e in sources.values()),
                files=2+2*len(sources),operation=None),
           dict(role='metadata',bytes=sum(LAYOUT.values()),files=len(LAYOUT),operation=None),
           dict(role='public_checkpoint',bytes=sum(e['bytes'] for e in EXPECTED.values())+2*MIB,
                files=4,operation='fetch')]
    for name in ORDER:
        roles.append(dict(role='logs',bytes=68*MIB,files=2,operation=name))
    for name in ('distilgpt2','gpt2'):
        roles.append(dict(role='target_outputs',bytes=8*32*MIB+64*MIB,files=9,operation=name))
        roles.append(dict(role='controller_and_ledger',bytes=32*MIB,files=64,operation=name))
    return dict(schema='target-admission-write-plan-v99',roles=roles,
        temporary_roles=[dict(role='worker_streams',bytes=4*GIB,files=2),
            dict(role='native_builds',bytes=4*GIB,files=8192),
            dict(role='software_fixtures',bytes=4*GIB,files=8192)],
        formal_disk_bound=False,capacity_reserved=False,measured_peak=False,
        later_complete_screen_covered=False,external_slurm_writer_limit_enforced=False)


def requests(plan,sources,archive_bytes,operation=None):
    require(plan==build(sources,archive_bytes),'Exact source-derived plan required')
    require(operation is None or operation in ORDER,'Unknown admission phase')
    remaining=set(ORDER if operation is None else ORDER[ORDER.index(operation):])
    roles=[r for r in plan['roles'] if (r['operation'] is None or r['operation'] in remaining)
        and (operation is None or r['role']!='source_staging')]
    def allowance(rows):
        files=sum(r['files'] for r in rows);logical=sum(r['bytes'] for r in rows)+4096*files
        return dict(bytes=logical+(logical+3)//4+GIB,files=files+4096)
    # V85/V88 API uses required_bytes / required_files names.
    project=allowance(roles);tmp=allowance(plan['temporary_roles'])
    return dict(project=dict(path=str(ROOT/'local_runs' if operation is None else RUN),
                 required_bytes=project['bytes'],required_files=project['files']),
            temporary=dict(path='/tmp',required_bytes=tmp['bytes'],required_files=tmp['files']))
