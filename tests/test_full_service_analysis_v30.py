"""Adversarial audit metadata fixtures. These launch no research workers."""
import ast
import copy
from pathlib import Path
import sys
import tempfile
import unittest

from scripts import analyze_full_service_v30 as audit
from src.run_store import canonical_json,digest


class FullServiceAnalysisTests(unittest.TestCase):
    def test_critical_audit_checks_cannot_disappear_under_python_optimization(self):
        tree = ast.parse(Path(audit.__file__).read_text())
        self.assertFalse(any(isinstance(node,ast.Assert) for node in ast.walk(tree)))

    def test_late_inputs_must_match_exact_registered_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = Path(directory)
            outputs = campaign/'attempts/prepare/outputs';outputs.mkdir(parents=True)
            source = outputs/'state.bin';source.write_bytes(b'parent state')
            alternate = campaign/'alternate.bin';alternate.write_bytes(source.read_bytes())
            trial = dict(id='repair',plan=dict(method='repair',inputs={}),
                inputs_from_trial={'prior_state':dict(trial='prepare',artifact='state')})
            program = dict(source_sha256={'source':'a'*64})
            plan = dict(method='repair',inputs={'prior_state':dict(path=str(source),sha256=digest(source.read_bytes()))},
                source_sha256=program['source_sha256'],program_sha256='b'*64,protocol_sha256='c'*64,
                phase='feasibility',output=str(campaign/'attempts/repair/outputs'))
            results = {'prepare':dict(artifacts={'state':dict(file='state.bin',bytes=len(source.read_bytes()),sha256=digest(source.read_bytes()))})}
            audit.verify_plan(campaign,trial,plan,program,'b'*64,'c'*64,results)
            bad = copy.deepcopy(plan);bad['inputs']['prior_state']['path'] = str(alternate)
            with self.assertRaises(ValueError):
                audit.verify_plan(campaign,trial,bad,program,'b'*64,'c'*64,results)
            bad = copy.deepcopy(plan);bad['inputs']['extra'] = bad['inputs']['prior_state']
            with self.assertRaises(ValueError):
                audit.verify_plan(campaign,trial,bad,program,'b'*64,'c'*64,results)

    def test_controller_continuation_requires_exact_bound_preserved_premises(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = Path(directory)
            trial = dict(id='repair',plan=dict(method='repair',inputs={}))
            program = dict(source_sha256={'source':'a'*64})
            sidecar = dict(schema='service-controller-continuation-v30',
                original_program_sha256='b'*64,original_protocol_sha256='c'*64,
                remaining_trials=['repair'],budget_reset=False,evidence_changed=False,
                numerical_source_changed=False,preparation_repeated=False,
                samples_changed=False,thresholds_changed=False)
            path = campaign/'continuation-v1.json';path.write_bytes(canonical_json(sidecar))
            plan = dict(method='repair',inputs={},source_sha256=program['source_sha256'],
                program_sha256='b'*64,protocol_sha256='c'*64,phase='feasibility',
                output=str(campaign/'attempts/repair/outputs'),controller_continuation_sha256=audit.hashed(path))
            audit.verify_plan(campaign,trial,plan,program,'b'*64,'c'*64,{})
            bad = dict(plan,controller_continuation_sha256='0'*64)
            with self.assertRaisesRegex(ValueError,'continuation binding'):
                audit.verify_plan(campaign,trial,bad,program,'b'*64,'c'*64,{})
            sidecar['samples_changed'] = True;path.write_bytes(canonical_json(sidecar))
            plan['controller_continuation_sha256'] = audit.hashed(path)
            with self.assertRaisesRegex(ValueError,'preserved premise'):
                audit.verify_plan(campaign,trial,plan,program,'b'*64,'c'*64,{})

    def test_schedule_checks_command_limits_and_positive_nested_clocks(self):
        campaign = Path('/absolute/campaign')
        trial = dict(id='repair',script='run_fixture.py',cpu_seconds=4,wall_seconds=6)
        program = dict(address_space_bytes=2**30,affinity_cpus=[0],primary_clock='registered clock')
        identity = dict(command=[sys.executable,str(campaign/'source/scripts/run_fixture.py'),
            str(campaign/'attempts/repair/plan.json')],cwd=str(campaign/'source'),
            limits=dict(wall_seconds=6,cpu_seconds=4,address_space_bytes=2**30,threads=1,
                        affinity_cpus=[0],file_size_bytes=512*2**20,termination_grace_seconds=1))
        registration = dict(runtime=dict(interpreter=dict(sha256=audit.hashed(Path(sys.executable).resolve()))))
        transaction = dict(controller_elapsed_ns=10,primary_clock='registered clock',worker_outcome=dict(elapsed_wall_ns=8))
        audit.verify_worker_schedule(campaign,trial,transaction,identity,registration,program)
        for field,value in (('controller_elapsed_ns',0),('controller_elapsed_ns',True),('primary_clock','other')):
            bad = dict(transaction,**{field:value})
            with self.assertRaises(ValueError):
                audit.verify_worker_schedule(campaign,trial,bad,identity,registration,program)
        bad = copy.deepcopy(identity);bad['command'][1] = '/different/run_fixture.py'
        with self.assertRaises(ValueError):
            audit.verify_worker_schedule(campaign,trial,transaction,bad,registration,program)
        bad = copy.deepcopy(identity);bad['limits']['threads'] = 2
        with self.assertRaises(ValueError):
            audit.verify_worker_schedule(campaign,trial,transaction,bad,registration,program)
        bad = copy.deepcopy(transaction);bad['worker_outcome']['elapsed_wall_ns'] = 11
        with self.assertRaises(ValueError):
            audit.verify_worker_schedule(campaign,trial,bad,identity,registration,program)

    def budget_fixture(self,root):
        program = dict(source_sha256={'source':'a'*64},phase_cpu_cap_seconds=5)
        binding = dict(identity=dict(protocol_sha256='b'*64,source_sha256=program['source_sha256']),
            phase_cpu_seconds={'feasibility':5},scope='trusted_worker_cpu_admission_not_process_tree_containment')
        debit = dict(phase='feasibility',reserved_cpu_seconds=3,state='settled',charged_cpu_seconds=1,observed_cpu_ns=1000)
        receipts = [dict(budget_attempt_id='gate',budget_debit=dict(debit)),
                    dict(budget_attempt_id='service',budget_debit=dict(debit))]
        ledger = dict(schema='phase-cpu-ledger-v1',binding=binding,
                      attempts={receipt['budget_attempt_id']:receipt['budget_debit'] for receipt in receipts})
        path = root/'phase-cpu-budget/ledger.json';path.parent.mkdir()
        path.write_bytes(canonical_json(ledger))
        return program,receipts,ledger,path

    def test_phase_charge_includes_component_gates_and_every_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program,receipts,ledger,path = self.budget_fixture(root)
            report = audit.verify_final_budget(root,program,'b'*64,receipts)
            self.assertEqual(report['charged_cpu_seconds'],{'feasibility':2})
            with self.assertRaises(ValueError):
                audit.verify_final_budget(root,program,'b'*64,receipts[1:])
            ledger['attempts']['extra'] = copy.deepcopy(ledger['attempts']['gate'])
            path.write_bytes(canonical_json(ledger))
            with self.assertRaises(ValueError):
                audit.verify_final_budget(root,program,'b'*64,receipts)

    def test_unsettled_debit_cannot_be_omitted_or_reported_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program,receipts,ledger,path = self.budget_fixture(root)
            ledger['attempts']['gate'].update(state='reserved',charged_cpu_seconds=3,observed_cpu_ns=None)
            path.write_bytes(canonical_json(ledger))
            with self.assertRaises(ValueError):
                audit.verify_final_budget(root,program,'b'*64,receipts)

    def test_supersession_requires_unstarted_trials_and_preserves_all_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'attempts/done').mkdir(parents=True)
            program = dict(trials=[dict(id='done'),dict(id='later')])
            record = dict(schema='full-service-supersession-v30',program_sha256='a'*64,protocol_sha256='b'*64,
                cancelled_trial_ids=['later'],final_completed_trial_ids=['done'],reason='shared solver supersedes baseline',
                created_unix_ns=1)
            path = root/'supersession.json';path.write_bytes(canonical_json(record))
            cancelled,_ = audit.verify_supersession(root,program,'a'*64,'b'*64)
            self.assertEqual(cancelled,['later'])
            (root/'attempts/later').mkdir()
            with self.assertRaises(ValueError):
                audit.verify_supersession(root,program,'a'*64,'b'*64)


if __name__ == '__main__':
    unittest.main()
