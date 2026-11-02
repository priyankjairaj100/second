"""Build an exclusive new registry candidate from an exact staged source package.

This is not a submission or a successful software/empirical result. The original
failed program, all partial artifacts and its unsettled ledger stay unchanged.
"""
from pathlib import Path
import sys
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_v80.io import json_read, read, write, require, info
from research_v89.config import ROOT, RUN, design
from research_v89.storage_plan import build, requests
from research_v89.recovery import OLD_RUN, OLD_LEDGER, verify_failure_bindings
from research_v86.admission import OLD_PROGRAM, carry_forward
from research_v88.storage import inspect

SOFTWARE = [
    'research_v63.test_control', 'research_v63.test_runner', 'research_v64.test_service',
    'research_v64.test_linux', 'research_v66.test_operations', 'research_v66.test_linux',
    'research_v79.test_integration', 'research_v89.test_protocol', 'research_v89.test_worker',
    'research_v89.test_receipts', 'research_v89.test_implementation',
    'research_v87.test_outputs', 'research_v88.test_storage', 'research_v85.test_storage',
    'research_v86.test_admission', 'research_v83.test_accounting', 'research_v83.test_inputs',
    'research_v89.test_host', 'research_v89.test_submit', 'research_v89.test_terminal',
    'research_v89.test_submit_flow', 'research_v89.test_envelope']
EXPECTED_TESTS = 162


def main(inventory_sha, archive_sha):
    require(Path(__file__).resolve() == RUN/'research_v89/prepare.py', 'Literal new recovery namespace required')
    require(not (RUN/'program.json').exists() and not (RUN/'registration.json').exists(),
            'New preparation already consumed; never overwrite')
    inventory = RUN/'source-inventory.json'
    require(read(inventory, retain=False)['sha256'] == inventory_sha, 'Source inventory commitment differs')
    sources = json_read(inventory)
    archive = ROOT/'local_runs/four-cell-recovery-v89-source-only.tar'
    archive_info = read(archive, retain=False)
    require(archive_info['sha256'] == archive_sha, 'Actual source-only archive differs')
    plan = build(sources, archive_info['bytes'])
    # Upload/extraction must already have passed a full staging allowance. This
    # second fresh check covers the remaining program and allocation writes.
    storage = inspect(requests(plan, sources, archive_info['bytes'], 'checks'))
    for name, expected in sources.items():
        read(RUN/name, expected, retain=False)
    old = json_read(OLD_RUN/'program.json')
    require(info((OLD_RUN/'program.json').read_bytes())['sha256'] == OLD_PROGRAM,
            'Exact failed predecessor program required')
    frozen = json_read(RUN/'recovery-evidence/partial-artifact-bindings.json')
    failed = dict(program_sha256=OLD_PROGRAM, ledger=dict(path=str(OLD_RUN/'budget/ledger.json'), **OLD_LEDGER),
                  artifacts=frozen['failed_v80_artifacts'],
                  accounting=dict(path=str(RUN/'recovery-evidence/old-accounting.txt'),
                                  **read(RUN/'recovery-evidence/old-accounting.txt', retain=False)),
                  carry_forward=carry_forward(json_read(OLD_RUN/'budget/ledger.json')))
    p = design()
    p.update({k:old[k] for k in ('inputs', 'prior_sources', 'dependency_files', 'historical_ledgers',
                                'runtime', 'shared_checkpoint_bytes', 'resource_admission')})
    p.update(new_sources={str(RUN/n):e for n,e in sources.items()}, new_source_count=len(sources),
             sources=sources, source_inventory=sources, source_inventory_sha256=inventory_sha,
             source_archive_bytes=archive_info['bytes'], source_archive_sha256=archive_sha,
             storage_plan=plan, preparation_storage_observation=storage, failed_predecessor=failed,
             software_modules=SOFTWARE, expected_tests=EXPECTED_TESTS,
             registration_is_external=True, scientific_result=False,
             source_review='Root review; no independent reviewer or numerical result inferred',
             final_accounting_scope='Both audits and actual host terminal reconciliation required')
    verify_failure_bindings(p)
    result = write(RUN/'program.json', p, maximum=64*2**20)
    print(result)


if __name__ == '__main__':
    main(*sys.argv[1:])
