"""Reopen actual V89 terminal/audit inputs for a future transfer registration.

This is read-only and does not create a terminal report, run an experiment or
replace the frozen terminal reporter. Call it only with that reporter's actual
saved canonical output and its independently supplied byte/hash commitment.
Fresh scheduler inspection remains required before any future launch.
"""
from pathlib import Path
from research_v80.io import read, require, info
from research_v89.config import ROOT, RUN, ORDER
from research_v89.recovery import verify_failure_bindings
from research_v83.accounting import scheduler_rows
from research_v86.admission import terminal_disposition
from src.run_store import canonical_json, strict_json

PROGRAM_SHA = '6f9b59c73e33d407dadc6504b666ca67b5c5efb28e1a0fe8e418b470af8ab0e9'
JOB_ORDER = ('checks', *ORDER, 'primary', 'supplemental')
JOBS = {name: dict(job_id=str(16004+i), name='second89-'+name) for i, name in enumerate(JOB_ORDER)}


def validate(terminal, primary, supplemental, program):
    require(terminal['schema'] == 'recovery-terminal-v89' and terminal['status'] == 'verified'
            and terminal['program_sha256'] == PROGRAM_SHA, 'Actual V89 terminal success required')
    require(info(canonical_json(program))['sha256'] == PROGRAM_SHA, 'Exact actual V89 program required')
    require(terminal['evidence'] == dict(actual_audits_and_inputs_reverified=True, comparison_count=8,
            quality_evaluation=False, transfer=False, confirmation=False), 'Complete recovery scope required')
    scheduled = scheduler_rows(terminal['scheduler_raw'], JOBS)
    require(terminal_disposition(terminal['old_scheduler_raw']) == terminal['preserved_failure'],
            'Every old failure/cancellation disposition must remain')
    require(terminal['carried_reservations'] == program['failed_predecessor']['carry_forward'],
            'Old unknown reservation or recovery ceiling changed')
    require(set(terminal['costs']) == set(JOBS), 'Complete thirteen-allocation cost census required')
    for name, expected in JOBS.items():
        c = terminal['costs'][name]
        require(c['job_id'] == expected['job_id'] and c['scheduler_cpu_ns'] == scheduled[name]['cpu_ns']
                and c['scheduler_reporting_quantum_ns'] == scheduled[name]['quantum_ns'],
                'Terminal cost row differs from actual registered scheduler row')
    for kind, audit in [('primary', primary), ('supplemental', supplemental)]:
        require(audit['schema'] == 'disjoint-service-'+kind+'-audit-v89'
                and audit['status'] == 'verified' and audit['program_sha256'] == PROGRAM_SHA,
                'Both actual bound audits required')
        require(audit['confirmation'] is False and audit['quality_evaluation'] is False,
                'Audit scope cannot expand into confirmation or quality')
    wanted = {(arm, step) for arm in program['cells'] for step in (1, 2)}
    comparisons = primary['evidence']['comparisons']
    require(len(comparisons) == 8 and {(r['arm'], r['step']) for r in comparisons} == wanted
            and all(r['actual_bytes_equal'] is True and r['actual_model_bytes_equal'] is True for r in comparisons),
            'Every cell/endpoint needs actual state and model equality')
    require(supplemental['evidence']['primary_receipt_sha256'] == info(canonical_json(primary))['sha256']
            and supplemental['evidence']['eight_actual_model_pairs_equal'] is True,
            'Separate actual-model audit must bind the exact primary')
    for field in ('budget', 'costs', 'controllers', 'host_envelopes'):
        require(primary[field] == supplemental[field], 'Audit accounting or timing disagreement')
    budget = primary['budget']
    require(len(budget['attempts']) == 10 and budget['reserved_unknown_attempts'] == 0
            and not budget['reservation_overrun_attempts'] and not any(budget['over_cap'].values())
            and all(r['state'] == 'settled' for r in budget['attempts'].values()), 'Ten settled new workers required')
    for audit in (primary, supplemental):
        require(all(terminal['inputs'].get(path) == entry for path, entry in audit['inputs'].items()),
                'Terminal input census omitted or changed an audit input')
    return dict(schema='reopened-recovery-gate-v90', status='verified', program_sha256=PROGRAM_SHA,
                actual_comparisons=8, actual_allocations=13, old_unknown_debit_preserved=12602,
                establishes_transfer=False, establishes_general_speedup=False)


def verify(path, expected):
    raw = read(path, expected, maximum=64*2**20)
    terminal = strict_json(raw)
    require(type(terminal) is dict and canonical_json(terminal) == raw, 'Canonical saved terminal report required')
    inventory = terminal.get('inputs')
    require(type(inventory) is dict and 0 < len(inventory) <= 8192, 'Bounded actual terminal input census required')
    signatures = {}
    def signature(p):
        s = p.stat(); return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    for name, entry in inventory.items():
        p = Path(name)
        require(p.is_absolute() and '..' not in p.parts and p.is_relative_to(ROOT)
                and type(entry) is dict and set(entry) == {'bytes', 'sha256'}
                and type(entry['bytes']) is int and 0 <= entry['bytes'] <= 2**30,
                'Pinned bounded recovery input required')
        signatures[name] = signature(p)
        read(p, entry, maximum=2**30, retain=False)
    def metadata(name):
        p = str(RUN/name)
        require(p in inventory, 'Actual required upstream receipt missing from input census')
        blob = read(p, inventory[p], maximum=64*2**20)
        value = strict_json(blob)
        require(canonical_json(value) == blob, 'Canonical actual recovery metadata required')
        return value
    program = metadata('program.json'); primary = metadata('primary-audit.json')
    supplemental = metadata('supplemental-audit.json')
    result = validate(terminal, primary, supplemental, program)
    for group in ('prior_sources', 'new_sources', 'dependency_files', 'historical_ledgers'):
        require(all(inventory.get(name) == entry for name, entry in program[group].items()),
                'Recovery terminal census lacks registered sources or historical ledgers')
    require(verify_failure_bindings(program) == terminal['carried_reservations'],
            'Actual old partial artifacts or unknown debit changed')
    for name, before in signatures.items():
        require(signature(Path(name)) == before, 'Recovery input changed while reopening the gate')
    # Reopen the submitted report too; source verification never silently binds
    # a later replacement after checking the original report's commitment.
    read(path, expected, maximum=64*2**20, retain=False)
    return dict(result, report=info(raw), input_files_reopened=len(inventory),
                report_does_not_replace_fresh_scheduler_inspection=True)
