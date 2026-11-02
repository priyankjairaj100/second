"""Read-only actual recovery, source, runtime and prior-operation admission."""
from pathlib import Path
from research_v80.io import read, json_read, require, info
from research_v90.admission import ledger_identity
from research_v90.recovery_gate import verify as verify_recovery
from research_v91.config import ROOT, RUN, OLD_PROGRAM, OLD_SHA, ORDER, design
from src.run_store import canonical_json


def program(expected, *, registered=True):
    p=json_read(RUN/'program.json')
    require(info(canonical_json(p))['sha256']==expected and all(p.get(k)==v for k,v in design().items()),
            'Exact new admission program required')
    ledger_identity(expected, p['sources'])
    require(p['source_count']==len(p['sources']) and
            p['source_inventory']==info(canonical_json(p['sources'])), 'Source inventory census differs')
    require(json_read(RUN/'inventory.json')==p['sources'], 'Exact staged inventory required')
    for name, entry in p['sources'].items():
        read(RUN/name, entry, maximum=64*2**20, retain=False)
    require(p['recovery_terminal']['path']==str(RUN/'gates/v89-terminal.json'), 'Fixed recovery gate path required')
    from research_v91.software import SUITES
    require(p['software_suites']=={k:dict(modules=v[0],tests=v[1]) for k,v in SUITES.items()}
        and p['expected_software_tests']==sum(v[1] for v in SUITES.values()),'Exact prepared suite census required')
    if registered:
        require(json_read(RUN/'registration.json')==dict(program_sha256=expected), 'New registration differs')
    return p


def prerequisites(p):
    binding=p['recovery_terminal']
    gate=verify_recovery(binding['path'], {k:binding[k] for k in ('bytes','sha256')})
    require(gate==p['recovery_gate'], 'Actual reopened V89 gate changed')
    # The failed V80 experiment still supplies an immutable successful INPUT registry.
    from research_v80 import campaign as historical
    old=json_read(OLD_PROGRAM)
    require(info(canonical_json(old))['sha256']==OLD_SHA, 'Historical input program changed')
    historical.verify_bindings(old)
    rows, provenance=historical.verify_inputs(old)
    return old, rows, provenance


def allocation(operation, expected, job, *, require_release=False):
    require(operation in ORDER and type(job) is str and job.isdigit(), 'Literal operation/job required')
    submission=json_read(RUN/(operation+'-submission.json'))
    require(submission['name']==submission['operation']==operation and submission['arguments']==[]
            and submission['program_sha256']==expected and submission['job_id']==job,
            'Allocated operation differs from recorded one-use submission')
    mode='checks' if operation=='checks' else 'chain'
    held=json_read(RUN/(mode+'-held-chain.json'))
    require(held['program_sha256']==expected and sum(row==submission for row in held['jobs'])==1,
            'Actual validated held chain required before entry')
    # Release response is written after scontrol. Do not create a startup race.
    # Prior-job and terminal review still require that actual response.
    if require_release:
        require(json_read(RUN/(operation+'-release.json'))==dict(program_sha256=expected, job_id=job, released=True),
                'Released registered operation required')


def earlier(operation, expected):
    for name in ORDER[:ORDER.index(operation)]:
        entry=json_read(RUN/(name+'-entry.json')); host=json_read(RUN/(name+'-host.json'))
        require(entry['status']==host['status']=='complete' and entry['error'] is host['error'] is None
                and entry['program_sha256']==host['program_sha256']==expected
                and entry['job_id']==host['job_id'] and entry['operation']==host['operation']==name,
                'Earlier actual entry and host success required')
        allocation(name, expected, entry['job_id'], require_release=True)
        if name=='checks':
            from research_v91.software import validate
            validate(entry['result'])
        require(entry['container_storage_mapping']['status']=='matched_host_devices_and_new_file_groups'
                and host['accounting']['nonnumerical_cpu_ns'] <= (602 if name=='checks' else 302)*10**9,
                'Earlier path mapping/complete controller allowance differs')
