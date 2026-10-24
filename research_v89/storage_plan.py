"""Finite conservative write allowances for a NEW recovery, not reservations.

Worker extents are enforced by V87. Other roles below are conservative reviewed
allowances; the file-count and byte totals are not a formal disk-usage guarantee.
No old file is deleted or credited as reclaimable capacity.
"""
from pathlib import PurePosixPath
from research_v89.config import ROOT, RUN, ORDER
from research_v87.outputs import allowance

MIB = 2**20
GIB = 2**30
REPRESENTATIONS = ('lossless', 'compressed48', 'hybrid_gram', 'modern_lossless')
OPERATIONS = ('checks', *ORDER, 'primary', 'supplemental')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def artifacts(trial):
    require(trial in ORDER, 'Unknown recovery trial')
    base = {'execution-provenance.json', 'admission.json'}
    rebuilt = {'model.bin'} | {r+'-'+s for r in REPRESENTATIONS
                              for s in ('state.bin', 'trust.json')}
    return base | (rebuilt if trial == 'prepare' else
                   {f'step-{i}/'+n for i in (1, 2) for n in rebuilt}
                   if trial == 'oracle' else {'model.bin', 'state.bin', 'trust.json'})


def build(sources, archive_bytes):
    """Exact source extents, fixed copy counts, and conservative nonworker roles."""
    require(type(sources) is dict and 0 < len(sources) < 4096,
            'Finite exact source inventory required')
    require(type(archive_bytes) is int and 0 < archive_bytes <= 64*MIB,
            'Actual bounded source-only archive extent required')
    for name, e in sources.items():
        p = PurePosixPath(name)
        require(type(name) is str and str(p) == name and not p.is_absolute()
                and '..' not in p.parts and set(e) == {'bytes', 'sha256'}
                and type(e['bytes']) is int and 0 <= e['bytes'] <= 64*MIB
                and type(e['sha256']) is str and len(e['sha256']) == 64
                and all(c in '0123456789abcdef' for c in e['sha256']),
                'Exact source-only file binding required')
    roles = []

    def add(name, byte_count, files, basis, operation=None):
        roles.append(dict(role=name, bytes=byte_count, files=files,
                          basis=basis, operation=operation))

    # Two complete archive/extraction copies accommodate interrupted staging.
    add('source_staging', 2*archive_bytes+2*sum(e['bytes'] for e in sources.values()),
        2+2*len(sources), 'exact extents; two copies allowed')
    add('registration_and_inventory', 8*64*MIB, 16,
        'conservative metadata and atomic replacement allowance')
    for trial in ORDER:
        a = allowance(artifacts(trial), 21_233_664)
        add('worker_outputs', a['output_bytes'], a['output_files'],
            'V87 enforced logical output extents', trial)
        # RunStore request, identity, status/result, seven artifacts, locks,
        # plan/transaction and shared ledger, including interrupted replacements.
        add('controller_and_ledger', 32*64*MIB, 64,
            'conservative 32 metadata extents including replacement overlap', trial)
    for op in OPERATIONS:
        add('entry_host_and_storage_receipts', 6*64*MIB, 12,
            'six bounded new metadata writes plus partial/overlap allowance', op)
        add('submission', 7*MIB, 14,
            'conservative intent/response/held/release/chain allowance', op)
        add('captured_bootstrap_log', 64*MIB, 1,
            'host collector stops the new allocation on overflow', op)
        add('slurm_bootstrap_log', 4*MIB, 1,
            'conservative allowance; external Slurm writer is not RLIMIT-bound', op)
    for op in ('primary', 'supplemental'):
        add('audit_report', 64*MIB, 1, 'new audit writer limit', op)
    add('terminal_accounting', 2*64*MIB, 4,
        'conservative actual host terminal reports and failure preservation')
    return dict(schema='recovery-write-plan-v89', roles=roles,
                source_archive_bytes=archive_bytes, source_files=len(sources),
                temporary_roles=[
                    dict(role='worker_streams', bytes=4*GIB, files=2,
                         basis='two inherited streams; worker 2GiB RLIMIT_FSIZE'),
                    dict(role='native_builds', bytes=4*GIB, files=8192,
                         basis='conservative allowance; compiler internals not bounded'),
                    dict(role='software_fixtures', bytes=4*GIB, files=8192,
                         basis='conservative separate allowance; Linux measurement pending')],
                allocation_margin_numerator=1, allocation_margin_denominator=4,
                allocation_fixed_margin_bytes=GIB, allocation_fragment_bytes=4096,
                additional_directory_inodes=4096, capacity_reserved=False,
                total_is_conservative_allowance=True, formal_disk_bound=False,
                container_mapping_qualified=False, measured_peak=False)


def requests(plan, sources, archive_bytes, operation=None):
    require(plan == build(sources, archive_bytes), 'Write plan differs from source-derived plan')
    require(operation is None or operation in OPERATIONS, 'Unknown write phase')
    # Completed files are already in observed quota usage; their maxima are not
    # charged a second time as future capacity. All unclassified shared roles
    # remain, deliberately conservative. Staging is included before upload only.
    remaining = set(OPERATIONS if operation is None else OPERATIONS[OPERATIONS.index(operation):])
    roles = [r for r in plan['roles'] if r['operation'] is None or r['operation'] in remaining]
    if operation is not None:
        roles = [r for r in roles if r['role'] != 'source_staging']

    def total(rows, path):
        files = sum(r['files'] for r in rows)
        logical = sum(r['bytes'] for r in rows)
        rounded = logical+files*plan['allocation_fragment_bytes']
        return dict(path=str(path), required_bytes=rounded+(rounded+3)//4+GIB,
                    required_files=files+4096)

    return dict(project=total(roles, ROOT/'local_runs'),
                temporary=total(plan['temporary_roles'], '/tmp'))
