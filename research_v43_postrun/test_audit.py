"""Tiny artifact fixtures; no neural inference, cluster access or empirical data."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

from research_v42.test_resource_plan import bind, fixture
from research_v43.service import trust_json
from research_v43.state import validate_state
from research_v43.test_state import BUDGET, codes, record, state
from research_v43_postrun.audit import (Inputs, REPRESENTATIONS, TRIAL_REPRESENTATIONS,
    ROOT, audit_states, execution_matches_target, expected_artifacts, model_matches_state,
    verify_worker_receipts)
from src.phase_budget import PhaseBudget, read_budget_snapshot
from src.run_store import RunStore, canonical_json, digest, strict_json


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if type(value) is bytes else canonical_json(value))


class TinyCampaign:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.records = tuple(record(name, tokens) for name, tokens in (
            ('alpha', (1, 2)), ('beta', (3, 4)), ('gamma', (5, 6))))
        decoder = {'fixture': 'decoder-identity'}
        anchor, fixed = fixture(((2, 3), (1, 2)), original=6)
        fixed['decoder_sha256'] = digest(canonical_json(decoder))
        anchor['evaluator_id'] = 'certified-decoder-v1:'+fixed['decoder_sha256']
        self.target = bind(anchor, fixed)
        self.program = dict(records=[dict(id=r.record_id, tokens=list(r.tokens)) for r in self.records],
            record_provenance={r.record_id: strict_json(r.provenance) for r in self.records},
            deletion_order=[r.record_id for r in self.records], normalization=6)
        execution = dict(schema='fixed-source-execution-binding-v43',
            target_sha256=digest(self.target.fixed_payload), anchor_target_sha256=digest(self.target.anchor_payload),
            decoder=decoder, implementation={'fixture': True}, preparer_sha256='3'*64, anchor_sha256='4'*64)
        self.completions = {trial:dict(execution_provenance_sha256=digest(canonical_json(execution)), steps=[])
            for trial in ('prepare', 'oracle', *TRIAL_REPRESENTATIONS)}
        for trial in self.completions:
            write(self.directory/trial/'outputs/execution-provenance.json', execution)
        self.frozen = dict(comparisons=[], timings={}, ratios={})
        self.checkpoint_bytes = 1234
        self.prepared = self.directory/'prepare/outputs'
        self.completions['prepare'].update(preparation={'representations': {}}, code_count=8)
        write(self.prepared/'original-model.bin', self.model(0))
        self.originals = {}
        for rep in REPRESENTATIONS:
            blob, trust = state(self.target, self.records, rep)
            trusted = canonical_json(trust_json(trust))
            self.originals[rep] = blob
            write(self.prepared/(rep+'-original.bin'), blob)
            write(self.prepared/(rep+'-trust.json'), trusted)
            self.completions['prepare']['preparation']['representations'][rep] = self.storage(blob, trusted)
        self.frozen['preparation'] = deepcopy(self.completions['prepare']['preparation'])
        for step in (1, 2):
            retained = self.records[step:]
            oracle_row = dict(step=step, retained_ids=[r.record_id for r in retained],
                prior_state_read=False, independent_retained_token_traversal=True,
                timing={'neural_stage_record_pairs': 2*len(retained)}, representations={})
            write(self.directory/'oracle/outputs'/f'step-{step}-model.bin', self.model(step))
            for rep in REPRESENTATIONS:
                blob, trust = state(self.target, retained, rep, codes(self.target, float(step)))
                trusted = canonical_json(trust_json(trust))
                write(self.directory/'oracle/outputs'/f'step-{step}-{rep}.bin', blob)
                write(self.directory/'oracle/outputs'/f'step-{step}-{rep}-trust.json', trusted)
                oracle_row['representations'][rep] = dict(state_bytes=len(blob), trust_bytes=len(trusted))
                for trial, family in TRIAL_REPRESENTATIONS.items():
                    if family != rep:
                        continue
                    root = self.directory/trial/'outputs'
                    write(root/f'step-{step}-model.bin', self.model(step))
                    write(root/f'step-{step}-state.bin', blob)
                    write(root/f'step-{step}-trust.json', trusted)
                    self.completions[trial]['steps'].append(dict(step=step, representation=rep,
                        retained_ids=[r.record_id for r in retained], deleted_ids=[self.records[step-1].record_id],
                        **self.storage(blob, trusted)))
                    self.frozen['comparisons'].append(dict(trial=trial, step=step, representation=rep,
                        state_sha256=digest(blob), state_bytes=len(blob), complete_model_sha256=digest(self.model(step)),
                        code_count=8, stages=2, retained_records=len(retained), retained_tokens=2*len(retained),
                        deleted_count=1, actual_bytes_equal=True, actual_model_bytes_equal=True,
                        exact_retained_membership_verified=True))
            self.completions['oracle']['steps'].append(oracle_row)
        for trial in TRIAL_REPRESENTATIONS:
            self.frozen['timings'][trial] = dict(
                live_state_bytes=[row['state_bytes']+row['trust_bytes'] for row in self.completions[trial]['steps']],
                complete_deployment_bytes=[row['complete_deployment_bytes'] for row in self.completions[trial]['steps']])
        for control in ('cached', 'hybrid', 'cold'):
            self.frozen['ratios'][control] = {name: [1-a/b for a, b in zip(
                self.frozen['timings']['compressed'][key], self.frozen['timings'][control][key])]
                for name, key in (('compressed_live_state_saving','live_state_bytes'),
                                  ('compressed_deployment_saving','complete_deployment_bytes'))}

    def model(self, step):
        return b''.join(c.packed_indices for c in codes(self.target, float(step)))

    def storage(self, blob, trust):
        return dict(state_bytes=len(blob), trust_bytes=len(trust),
                    complete_deployment_bytes=len(blob)+len(trust)+self.checkpoint_bytes)

    def audit(self):
        return audit_states(self.directory, self.program, self.completions, self.frozen, Inputs(),
                            self.checkpoint_bytes, expected_stages=2, expected_codes=8)

    def seal(self):
        """Create real RunStore receipts and a real settled ledger; no subprocess."""
        self.program.update(trials={trial: dict(cpu_seconds=10, wall_seconds=20)
            for trial in self.completions}, process_address_space_bytes=1024**3,
            file_size_bytes=1024**3, sources={'fixture-source.py': '1'*64})
        program_sha = digest(canonical_json(self.program))
        write(self.directory/'program.json', self.program)
        budget_identity = dict(protocol_sha256=program_sha, source_sha256=self.program['sources'])
        budget = PhaseBudget(self.directory/'budget', identity=budget_identity,
                             phase_cpu_seconds={'feasibility': 100})
        for number, (trial, completion) in enumerate(self.completions.items(), 1):
            root = self.directory/trial
            job = 'fixture-'+str(number)
            plan = dict(trial=trial, program=str(self.directory/'program.json'),
                        program_sha256=program_sha, output=str(root/'outputs'), slurm_job_id=job)
            write(root/'plan.json', plan)
            write(root/'outputs/admission.json', {'fixture_admission': True})
            completion.update(schema='complete-service-worker-v43', trial=trial, status='complete',
                complete_model=True, program_sha256=program_sha, source_sha256=self.program['sources'],
                slurm_job_id=job, artifacts={})
            for name in expected_artifacts(trial):
                blob = (root/'outputs'/name).read_bytes()
                completion['artifacts'][name] = dict(file=name, sha256=digest(blob), bytes=len(blob))
            write(root/'outputs/completion.json', completion)
            identity = dict(schema='limited-worker-identity-v1',
                identity=dict(campaign_sha256=program_sha, trial=trial),
                command=[sys.executable, '-B', '-m', 'research_v43.worker', str(root/'plan.json')],
                cwd=str(ROOT), limits=dict(self.program['trials'][trial],
                    address_space_bytes=self.program['process_address_space_bytes'],
                    file_size_bytes=self.program['file_size_bytes'], threads=1, affinity_cpus=[0]),
                phase_budget=dict(binding_sha256=budget.identity_digest,
                    phase='feasibility', directory=str(self.directory/'budget')))
            observed_cpu_ns = number*100_000_000
            debit_id = digest(canonical_json(dict(trial=trial, fixture=True)))
            budget.reserve('feasibility', debit_id, 12)
            debit = budget.settle(debit_id, observed_cpu_ns)
            outcome = dict(status='complete', kind='exited', returncode=0)
            with RunStore(root/'worker', identity) as store:
                store.write_artifact('request.json', canonical_json(plan))
                store.finish(dict(schema='limited-worker-record-v1', status='complete',
                    outcome=outcome, budget_attempt_id=debit_id, budget_debit=debit,
                    resource_usage={'total_cpu_ns': observed_cpu_ns}))
            write(root/'transaction.json', dict(worker_outcome=outcome, slurm_job_id=job,
                  elapsed_ns=number*1_000_000))
        snapshot = read_budget_snapshot(self.directory/'budget', identity=budget_identity,
                                        phase_cpu_seconds={'feasibility': 100})
        self.frozen['budget'] = budget.snapshot()
        return snapshot


class SupplementalAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.case = TinyCampaign(Path(self.temporary.name).resolve())

    def test_full_tiny_three_representation_two_successor_flow(self):
        result = self.case.audit()
        self.assertEqual(len(result['comparisons']), 8)
        self.assertTrue(all(row['model_export_matches_state_codes'] for row in result['comparisons']))
        self.assertTrue(all(row['registered_record_binding_verified'] for row in result['comparisons']))
        self.assertEqual(set(result['original_storage']), set(REPRESENTATIONS))

    def test_equal_wrong_exports_no_longer_pass_independent_state_and_model_checks(self):
        # All exported models agree and the old comparison's export digest is
        # updated too, while the valid canonical state still contains other codes.
        for trial in ('oracle', *TRIAL_REPRESENTATIONS):
            write(self.case.directory/trial/'outputs/step-1-model.bin', self.case.model(0))
        for row in self.case.frozen['comparisons']:
            if row['step'] == 1:
                row['complete_model_sha256'] = digest(self.case.model(0))
        with self.assertRaisesRegex(ValueError, 'packed state codes'):
            self.case.audit()

    def test_original_export_also_must_equal_every_representation(self):
        write(self.case.prepared/'original-model.bin', self.case.model(1))
        with self.assertRaisesRegex(ValueError, 'packed state codes'):
            self.case.audit()

    def test_registered_token_and_provenance_mismatch_refused(self):
        for change in ('tokens', 'provenance'):
            with self.subTest(change=change):
                original = deepcopy(self.case.program)
                if change == 'tokens':
                    self.case.program['records'][0]['tokens'][0] = 999
                else:
                    self.case.program['record_provenance']['alpha']['dataset_revision'] = 'different'
                with self.assertRaisesRegex(ValueError, 'membership or record provenance'):
                    self.case.audit()
                self.case.program = original

    def test_consistently_wrong_execution_target_binding_refused(self):
        for trial in self.case.completions:
            path = self.case.directory/trial/'outputs/execution-provenance.json'
            execution = strict_json(path.read_bytes())
            execution['target_sha256'] = '0'*64
            write(path, execution)
            self.case.completions[trial]['execution_provenance_sha256'] = digest(canonical_json(execution))
        with self.assertRaisesRegex(ValueError, 'execution provenance|Execution provenance'):
            self.case.audit()

    def test_cross_worker_execution_provenance_change_refused(self):
        path = self.case.directory/'hybrid/outputs/execution-provenance.json'
        execution = strict_json(path.read_bytes())
        execution['implementation'] = {'different': True}
        write(path, execution)
        self.case.completions['hybrid']['execution_provenance_sha256'] = digest(canonical_json(execution))
        with self.assertRaisesRegex(ValueError, 'across arms'):
            self.case.audit()

    def test_state_trust_and_deployment_accounting_recomputed(self):
        for field in ('state_bytes', 'trust_bytes', 'complete_deployment_bytes'):
            with self.subTest(field=field):
                row = self.case.completions['compressed']['steps'][0]
                row[field] += 1
                with self.assertRaisesRegex(ValueError, 'actual bytes'):
                    self.case.audit()
                row[field] -= 1

    def test_frozen_receipt_storage_ratios_and_comparison_hashes_rechecked(self):
        self.case.frozen['ratios']['cached']['compressed_live_state_saving'][0] += 0.1
        with self.assertRaisesRegex(ValueError, 'storage ratio'):
            self.case.audit()
        self.case.frozen['ratios']['cached']['compressed_live_state_saving'][0] -= 0.1
        self.case.frozen['comparisons'][0]['state_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'comparison differs'):
            self.case.audit()

    def test_missing_or_duplicate_frozen_comparison_refused(self):
        self.case.frozen['comparisons'][-1] = deepcopy(self.case.frozen['comparisons'][0])
        with self.assertRaisesRegex(ValueError, 'eight declared comparisons'):
            self.case.audit()

    def test_oracle_route_flags_do_not_replace_actual_byte_checks(self):
        path = self.case.directory/'oracle/outputs/step-1-compressed40.bin'
        blob = path.read_bytes()
        write(path, blob[:-1]+bytes([blob[-1]^1]))
        with self.assertRaises(ValueError):
            self.case.audit()

    def test_model_extent_and_execution_decoder_binding(self):
        blob = self.case.originals['lossless']
        view = validate_state(blob)
        with self.assertRaisesRegex(ValueError, 'trailing or missing'):
            model_matches_state(view, self.case.model(0)+b'\x00')
        execution = strict_json((self.case.prepared/'execution-provenance.json').read_bytes())
        execution['decoder'] = {'other': 'decoder'}
        with self.assertRaisesRegex(ValueError, 'decoder does not bind'):
            execution_matches_target(execution, self.case.target)

    def test_input_inventory_detects_changes_and_rejects_noncanonical_json(self):
        path = self.case.directory/'input.json'
        write(path, {'a': 1})
        inventory = Inputs()
        self.assertEqual(inventory.json(path), {'a': 1})
        write(path, {'a': 2})
        with self.assertRaisesRegex(ValueError, 'changed before receipt'):
            inventory.unchanged()
        write(path, b'{"a":1,"a":2}')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            Inputs().json(path)

    def test_real_sealed_receipts_and_settled_snapshot_feed_full_state_audit_read_only(self):
        snapshot = self.case.seal()
        self.assertEqual(snapshot['status'], 'verified')
        self.assertTrue(all(self.case.frozen['budget'][key] == snapshot[key]
                            for key in self.case.frozen['budget']))
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.case.directory.rglob('*') if p.is_file()}
        inputs = Inputs()
        completions = verify_worker_receipts(self.case.directory, self.case.program, inputs, snapshot)
        result = audit_states(self.case.directory, self.case.program, completions,
            self.case.frozen, inputs, self.case.checkpoint_bytes, expected_stages=2, expected_codes=8)
        inputs.unchanged()
        after = {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.case.directory.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(len(result['comparisons']), 8)
        self.assertEqual(len(snapshot['attempts']), 6)
        self.assertTrue(all(str(self.case.directory/trial/'worker/result.json') in inputs.files
                            for trial in completions))

    def test_sealed_attempt_artifact_tamper_rejected(self):
        snapshot = self.case.seal()
        path = self.case.directory/'cached/worker/attempt-0001/request.json'
        write(path, {'different': 'request'})
        with self.assertRaisesRegex(ValueError, 'saved artifact hash mismatch'):
            verify_worker_receipts(self.case.directory, self.case.program, Inputs(), snapshot)

    def test_actual_output_tamper_rejected_despite_sealed_success(self):
        snapshot = self.case.seal()
        write(self.case.directory/'compressed/outputs/step-1-model.bin', self.case.model(0))
        with self.assertRaisesRegex(ValueError, 'Declared artifact bytes differ'):
            verify_worker_receipts(self.case.directory, self.case.program, Inputs(), snapshot)

    def test_ledger_usage_must_equal_sealed_worker_receipt(self):
        snapshot = self.case.seal()
        first = next(iter(snapshot['attempts'].values()))
        first['observed_cpu_ns'] += 1
        with self.assertRaisesRegex(ValueError, 'CPU debit differs'):
            verify_worker_receipts(self.case.directory, self.case.program, Inputs(), snapshot)


if __name__ == '__main__':
    unittest.main()
