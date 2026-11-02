"""Prospective complete transfer write census, NOT an executable admission plan.

Writers exist for small records, controller/ledger records and progress. New
host/entry/worker/fetch/submit/audit callers still need to connect every writer,
bind actual prerequisite receipts and pass separately registered Linux checks.
These totals must never be passed to a live storage gate as qualified capacity.
"""
from research_v84.config import ORDER
from research_v82.fetch import EXPECTED
from research_v90.outputs import allowance
from research_v90.records import Records, SMALL_BYTES, REPORT_BYTES

MIB = 2**20
GIB = 2**30
ADMISSION = ('checks', 'fetch', 'distilgpt2', 'gpt2', 'close')
COMPLETE = ('checks', *(t.replace('/', '--') for t in ORDER), 'primary', 'supplemental')


def metadata_layout(kind):
    if kind not in ('admission', 'complete'): raise ValueError('Unknown transfer chain')
    operations = ADMISSION if kind == 'admission' else COMPLETE
    large = ['program.json', 'inventory.json', 'gates/v89-terminal.json',
             'host-terminal-report.json', 'host-terminal-failure.json']
    large += ['close-report.json'] if kind == 'admission' else [
        'gates/target-admission-terminal.json', 'primary-audit.json', 'supplemental-audit.json']
    layout = {n: REPORT_BYTES for n in large}
    layout['registration.json'] = SMALL_BYTES
    for mode in ('checks', 'chain'):
        for suffix in ('chain-intent.json', 'held-chain.json', 'released-chain.json'):
            layout[mode+'-'+suffix] = SMALL_BYTES
    for op in operations:
        for suffix in ('entry-start.json', 'entry.json', 'host-start.json', 'host.json',
                       'abort-intent.json', 'abort-response.json', 'intent.json',
                       'response.json', 'submission.json', 'release.json'):
            layout[op+'-'+suffix] = SMALL_BYTES
    return layout


def build():
    roles = []
    def add(role, byte_count, files, basis, chain=None, operation=None):
        roles.append(dict(role=role, bytes=byte_count, files=files, basis=basis,
                          chain=chain, operation=operation))
    for kind, operations in [('admission', ADMISSION), ('complete', COMPLETE)]:
        # Source-only uncompressed tar, at most64MiB and4096 regular members.
        # Two archive/extraction copies are allowed for failure preservation.
        add('source_staging', 4*64*MIB, 2+2*4096,
            'proposed future packager must enforce tar/extracted bytes and member ceilings', kind)
        layout = metadata_layout(kind)
        add('exclusive_metadata', sum(layout.values()), len(layout),
            'Records fixed filename census and per-role pre-write byte checks; callers pending', kind)
        for operation in operations:
            add('captured_bootstrap_log', 64*MIB, 1, 'same complete-or-failed collector cap as V89; new caller pending', kind, operation)
            add('external_slurm_log', 4*MIB, 1, 'conservative external-writer allowance; not a formal bound', kind, operation)
    for trial in ORDER:
        a = allowance(trial)
        add('worker_outputs', a['output_bytes'], a['output_files'],
            'V90 exact phase census; V87 unchanged per-artifact/progress/completion byte bounds', 'complete', trial)
    for profile in ('distilgpt2', 'gpt2'):
        add('target_admission_outputs', 8*32*MIB+64*MIB, 9,
            'eight old target artifact ceilings plus full completion; new caller pending', 'admission', profile)
    for chain, trials in [('complete', ORDER), ('admission', ('distilgpt2', 'gpt2'))]:
        for trial in trials:
            # At most six immutable artifacts, identity, two statuses, lock,
            # transient acknowledgment, one attempt, plan and transaction.
            # 32 extents conservatively cover both processes' atomic overlap,
            # failure preservation and a redundant share of the single ledger.
            add('controller_ledger_and_replacement', 32*MIB, 64,
                'new one-use RunStore/PhaseBudget1MiB; caller plan/transaction via Records; 32 extents including overlap', chain, trial)
    add('new_public_checkpoint', sum(e['bytes'] for e in EXPECTED.values()), len(EXPECTED),
        'exclusive exact-size fetch; a partial consumes the same file, never a second attempt', 'admission', 'fetch')
    add('fetch_intent_and_receipt', 2*MIB, 2, 'new finite Records caller required', 'admission', 'fetch')
    temporary = [dict(role='worker_streams', bytes=4*GIB, files=2),
                 dict(role='native_builds', bytes=4*GIB, files=8192),
                 dict(role='software_fixtures', bytes=4*GIB, files=8192)]
    def total(rows):
        files = sum(r['files'] for r in rows); logical = sum(r['bytes'] for r in rows)
        rounded = logical + files*4096
        return dict(logical_bytes=logical, files=files, required_bytes=rounded+(rounded+3)//4+GIB,
                    required_files=files+4096)
    return dict(schema='prospective-transfer-write-census-v90', roles=roles,
        temporary_roles=temporary, project=total(roles), temporary=total(temporary),
        registered=False, integrated_into_launcher=False, linux_qualified=False,
        eligible_for_storage_admission=False, capacity_reserved=False, measured_peak=False,
        formal_disk_bound=False, historical_outputs_credited_as_free=False,
        worker_progress_files=sum(allowance(t)['progress_files'] for t in ORDER),
        source_packages=dict(count=2, maximum_archive_bytes=64*MIB,
                             maximum_extracted_bytes=64*MIB, maximum_members=4096))


if __name__ == '__main__':
    import json
    print(json.dumps(build(), indent=2))
