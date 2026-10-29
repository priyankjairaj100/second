"""Synthetic report refusals; no actual upstream success is asserted."""
from copy import deepcopy
from pathlib import Path
import json
import unittest
from research_v90 import recovery_gate as gate
from research_v86.admission import terminal_disposition
from src.run_store import canonical_json, digest


def fixture():
    root = Path(__file__).resolve().parents[1]
    program = json.loads((root/'pilots/recovery-v89-20261023/execution-20261024/program.json').read_bytes())
    old_raw = json.loads((root/'pilots/transfer-engineering-v90-20261024/cluster-reconciliation.json').read_bytes())['accounting']['stdout']
    primary = dict(schema='disjoint-service-primary-audit-v89', status='verified', program_sha256=gate.PROGRAM_SHA,
        confirmation=False, quality_evaluation=False, evidence=dict(comparisons=[dict(arm=arm, step=step,
        actual_bytes_equal=True, actual_model_bytes_equal=True) for arm in program['cells'] for step in (1, 2)]),
        budget=dict(attempts={str(i):dict(state='settled') for i in range(10)}, reserved_unknown_attempts=0,
                    reservation_overrun_attempts=[], over_cap={'feasibility':False}),
        costs={'synthetic':True}, controllers={'synthetic':True}, host_envelopes={'synthetic':True}, inputs={})
    supplemental = dict(primary, schema='disjoint-service-supplemental-audit-v89',
                        evidence=dict(primary_receipt_sha256=digest(canonical_json(primary)), eight_actual_model_pairs_equal=True))
    raw = ''.join(f"{e['job_id']}|{e['name']}|COMPLETED|0:0|1|00:00.100|1|16G|csis.mn1\n" for e in gate.JOBS.values())
    scheduled = gate.scheduler_rows(raw, gate.JOBS)
    terminal = dict(schema='recovery-terminal-v89', status='verified', program_sha256=gate.PROGRAM_SHA,
        evidence=dict(actual_audits_and_inputs_reverified=True, comparison_count=8, quality_evaluation=False,
                      transfer=False, confirmation=False), scheduler_raw=raw, old_scheduler_raw=old_raw,
        preserved_failure=terminal_disposition(old_raw), carried_reservations=program['failed_predecessor']['carry_forward'],
        inputs={}, costs={name:dict(job_id=e['job_id'], scheduler_cpu_ns=scheduled[name]['cpu_ns'],
            scheduler_reporting_quantum_ns=scheduled[name]['quantum_ns']) for name,e in gate.JOBS.items()})
    return terminal, primary, supplemental, program


class RecoveryGateTests(unittest.TestCase):
    def test_exact_synthetic_structure_does_not_expand_scientific_scope(self):
        result = gate.validate(*fixture())
        self.assertFalse(result['establishes_transfer'])
        self.assertFalse(result['establishes_general_speedup'])

    def test_software_or_failed_or_old_report_cannot_replace_terminal(self):
        for field, value in [('schema','software-completion'), ('status','running'), ('program_sha256','0'*64)]:
            args = deepcopy(fixture()); args[0][field] = value
            with self.assertRaises(ValueError): gate.validate(*args)

    def test_missing_or_duplicate_cell_is_not_eight_comparisons(self):
        args = deepcopy(fixture()); args[1]['evidence']['comparisons'][0] = args[1]['evidence']['comparisons'][1]
        with self.assertRaises(ValueError): gate.validate(*args)

    def test_changed_primary_or_nonidentical_successor_refuses(self):
        for field in ('actual_bytes_equal','actual_model_bytes_equal'):
            args = deepcopy(fixture()); args[1]['evidence']['comparisons'][0][field] = False
            with self.assertRaises(ValueError): gate.validate(*args)
        args = deepcopy(fixture()); args[2]['evidence']['primary_receipt_sha256'] = '0'*64
        with self.assertRaises(ValueError): gate.validate(*args)

    def test_pending_or_missing_allocation_refuses(self):
        args = deepcopy(fixture()); args[0]['scheduler_raw'] = args[0]['scheduler_raw'].replace('COMPLETED','RUNNING',1)
        with self.assertRaises(ValueError): gate.validate(*args)
        args = deepcopy(fixture()); del args[0]['costs']['oracle']
        with self.assertRaises(ValueError): gate.validate(*args)

    def test_refunded_unknown_old_work_and_unsettled_new_work_refuse(self):
        args = deepcopy(fixture()); args[0]['carried_reservations'] = dict(args[0]['carried_reservations'], unsettled_old_worker_reservation=0)
        with self.assertRaises(ValueError): gate.validate(*args)
        args = deepcopy(fixture()); args[1]['budget']['reserved_unknown_attempts'] = 1
        with self.assertRaises(ValueError): gate.validate(*args)

    def test_omitted_audit_input_refuses_even_with_verified_label(self):
        args = deepcopy(fixture()); args[1]['inputs']['/missing/input'] = dict(bytes=3,sha256='a'*64)
        args[2]['evidence']['primary_receipt_sha256'] = digest(canonical_json(args[1]))
        with self.assertRaisesRegex(ValueError, 'input census'): gate.validate(*args)


if __name__ == '__main__': unittest.main()
