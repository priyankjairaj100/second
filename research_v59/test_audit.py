"""Tiny receipt and manifest fixtures; no inference or real checkpoint access."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from research_v43.dispatcher import ResourcePolicy, StageSpec, assess_stage
from research_v59 import audit
from research_v59.anchor import ANCHOR_RULE, FEATURE_RULE
from src.compact_state import StageCodes
from src.run_store import canonical_json, digest


def context():
    # Real complete stage ordering and lexically sorted manifest dependencies.
    # Shapes and words are deliberately tiny software data, not model evidence.
    ids = [f'block.{block:04d}.{kind}' for block in range(6) for kind in ('qkv', 'attn_out', 'mlp_up', 'mlp_down')]
    entries = [dict(stage_id=sid, dependencies=sorted(ids[:index]), shape=[1, 2],
        weights_sha256=digest(sid.encode()), grid_axis='output_row', significant_bits=24,
        row_scale_hex=[float(1).hex()], ridge=[1, 100], normalization=[1664, 1]) for index, sid in enumerate(ids)]
    execution = dict(decoder={'fixture': 'ordered'}, implementation={'fixture': 'manifest'})
    base = dict(recipe=dict(original_token_count=1664, bits=4, ridge=[1, 100], group_count=1),
        significant_bits=24, weight_digest_encoding='binary64_matrix_v1', stages=entries,
        evaluator_id='certified-decoder-v1:'+digest(canonical_json(execution['decoder'])))
    target = dict(schema='fixed-full-precision-anchor-calibration-target-v59', base_target_sha256=digest(canonical_json(base)),
        decoder_sha256=digest(canonical_json(execution['decoder'])),
        implementation_manifest_sha256=digest(canonical_json(execution['implementation'])),
        constructor_source_sha256='f'*64, feature_rule=FEATURE_RULE, anchor_rule=ANCHOR_RULE,
        prefix_rule='calibrated output codes never affect any feature', calibrated_dependencies='empty for every stage',
        original_normalization=1664, normalization_rule='unchanged original normalization from base target',
        grid_rule='unchanged base-only dyadic24 output-row grids; lower midpoint ties',
        record_rule='positions reset per source; causal within source; no cross-source state',
        teacher_weight_digest_encoding='binary64-matrix-little-endian-row-major-v1',
        teacher_stages=[dict(stage_id=e['stage_id'], shape=e['shape'], weights_sha256=e['weights_sha256']) for e in entries],
        output_rule='complete stage codes only; no canonical repair-state contract declared',
        failure_rule='bounded certified stage solver; unresolved or exhausted resource budget aborts')
    model = tuple(StageCodes(sid, 1, 2, 'dyadic_row', 4, (), b'\x88', (1.,)) for sid in ids)
    target_hash = digest(canonical_json(target))
    reports = [assess_stage(StageSpec.from_manifest(entry, target_sha256=target_hash), 768,
        kind='point', block_tokens=128, max_blocks=6, policy=ResourcePolicy(), resident_bytes=4*2**30) for entry in entries]
    rows = [dict(stage_id=sid, feature_tokens=768, input_width=2, output_rows=1, route=reports[index]['selected_route'],
        teacher_parent_stage_id=ids[index-1] if index else None,
        teacher_parent_weights_sha256=entries[index-1]['weights_sha256'] if index else None,
        output_code_sha256=digest(model[index].packed_indices), feature_elapsed_ns=2, solver_elapsed_ns=3,
        elapsed_ns=6, solver_diagnostics=dict(fixture_only=True)) for index, sid in enumerate(ids)]
    diagnostics = dict(schema='full-precision-anchor-calibration-v59', target_sha256=target_hash,
        base_target_sha256=digest(canonical_json(base)), feature_rule=FEATURE_RULE, anchor_rule=ANCHOR_RULE,
        implementation='ordered-finite-decoder-v30', implementation_manifest_sha256=target['implementation_manifest_sha256'],
        records=6, retained_tokens=768, original_normalization=1664, neural_stage_record_pairs=144,
        prior_model_access=False, prior_factor_access=False, calibrated_prefix_access=False,
        point_admission=reports, admission_elapsed_ns=1, stages=rows, service_elapsed_ns=145)
    return base, execution, target, model, diagnostics


class FixtureInputs:
    def __init__(self, objects, raw):
        self.objects, self.raw = objects, raw

    def json(self, path):
        return self.objects[str(path)]

    def read(self, path, *, retain=False):
        return self.raw[str(path)]


def receipts():
    directory = Path('/fixture/v59')
    root = directory/'quality'
    program = dict(worker_cpu_seconds=14400, worker_wall_seconds=18000,
        process_address_space_bytes=16*2**30, file_size_bytes=2*2**30)
    ph = digest(canonical_json(program))
    debit = dict(state='settled', observed_cpu_ns=1_100_000_000, charged_cpu_seconds=2)
    snapshot = dict(binding_sha256='binding', attempts={'attempt': debit}, phase_cpu_seconds={'development': 14402},
        charged_cpu_seconds={'development': 2}, over_cap={'development': False})
    identity = dict(identity=dict(program_sha256=ph), cwd=str(audit.ROOT),
        command=[sys.executable, '-B', '-m', 'research_v59.worker', str(root/'plan.json')],
        phase_budget=dict(directory=str(directory/'budget'), phase='development', binding_sha256='binding'),
        limits=dict(cpu_seconds=14400, wall_seconds=18000, address_space_bytes=16*2**30,
            file_size_bytes=2*2**30, threads=1, affinity_cpus=[0]))
    sealed = dict(attempt='attempt-one', outcome=dict(status='complete', returncode=0),
        artifacts={'stdout.bin': dict(bytes=0, sha256=digest(b''))}, budget_attempt_id='attempt',
        budget_debit=debit, resource_usage=dict(total_cpu_ns=1_100_000_000))
    plan = dict(schema='full-precision-anchor-quality-plan-v59', directory=str(directory),
        program=str(directory/'program.json'), program_sha256=ph,
        output=str(root/'outputs'), slurm_job_id='fixture')
    tx = dict(worker_outcome=sealed['outcome'], budget=copy.deepcopy(snapshot), slurm_job_id='fixture')
    objects = {str(root/'worker/identity.json'): identity, str(root/'transaction.json'): tx,
        str(root/'plan.json'): plan, str(root/'worker/result.json'): copy.deepcopy(sealed),
        str(root/'worker/attempt-one/status.json'): copy.deepcopy(sealed)}
    inputs = FixtureInputs(objects, {str(root/'worker/attempt-one/stdout.bin'): sealed['artifacts']['stdout.bin']})
    return directory, program, inputs, snapshot, sealed


class AuditTests(unittest.TestCase):
    def test_real_ordered_ids_with_sorted_complete_dependencies_are_accepted(self):
        base, execution, target, model, diagnostics = context()
        self.assertNotEqual(base['stages'][3]['dependencies'], [r['stage_id'] for r in base['stages'][:3]])
        self.assertEqual(audit.check_candidate_target(target, base, execution, constructor_sha256='f'*64), digest(canonical_json(target)))
        report = audit.check_candidate_diagnostics(diagnostics, model, target, base)
        self.assertEqual(report['complete_stages'], 24)
        self.assertEqual(report['neural_stage_record_pairs'], 144)
        self.assertTrue(report['complete_admissions_rederived'])

    def test_teacher_target_cannot_relabel_nearest_or_changed_recipe(self):
        base, execution, target, _, _ = context()
        changes = [('schema', 'fixed-nearest-anchor-calibration-target-v1'), ('base_target_sha256', 'wrong'),
            ('constructor_source_sha256', 'wrong'), ('anchor_rule', 'nearest'), ('original_normalization', 768),
            ('calibrated_dependencies', 'prefix'), ('implementation_manifest_sha256', 'wrong')]
        for key, value in changes:
            bad = copy.deepcopy(target); bad[key] = value
            with self.assertRaises(ValueError): audit.check_candidate_target(bad, base, execution, constructor_sha256='f'*64)
        bad = copy.deepcopy(target); bad['teacher_stages'][5]['weights_sha256'] = '0'*64
        with self.assertRaises(ValueError): audit.check_candidate_target(bad, base, execution, constructor_sha256='f'*64)
        bad = copy.deepcopy(execution); bad['decoder']['fixture'] = 'foreign'
        with self.assertRaises(ValueError): audit.check_candidate_target(target, base, bad, constructor_sha256='f'*64)
        for field in ('dependencies', 'ridge', 'normalization'):
            bad = copy.deepcopy(base)
            bad['stages'][4][field] = {'dependencies': [], 'ridge': [1, 10], 'normalization': [768, 1]}[field]
            with self.assertRaises(ValueError): audit.check_candidate_target(target, bad, execution, constructor_sha256='f'*64)

    def test_teacher_parent_is_checkpoint_weight_hash_never_candidate_code_hash(self):
        base, _, target, model, diagnostics = context()
        for key, value in [('teacher_parent_stage_id', 'other'), ('teacher_parent_weights_sha256', digest(model[3].packed_indices)),
                ('output_code_sha256', 'wrong'), ('input_width', 3), ('route', 'unreserved')]:
            bad = copy.deepcopy(diagnostics); bad['stages'][4][key] = value
            with self.assertRaises(ValueError): audit.check_candidate_diagnostics(bad, model, target, base)
        bad = copy.deepcopy(diagnostics); bad['calibrated_prefix_access'] = True
        with self.assertRaises(ValueError): audit.check_candidate_diagnostics(bad, model, target, base)

    def test_admission_rederived_with_complete_fallback_and_all_stages(self):
        base, _, target, model, diagnostics = context()
        variants = []
        bad = copy.deepcopy(diagnostics); bad['point_admission'][0]['work_units'] -= 1; variants.append(bad)
        bad = copy.deepcopy(diagnostics); bad['point_admission'][2]['resident_bytes'] = 0; variants.append(bad)
        bad = copy.deepcopy(diagnostics); bad['point_admission'][3]['policy']['max_stage_work_units'] *= 2; variants.append(bad)
        bad = copy.deepcopy(diagnostics); bad['stages'].pop(); variants.append(bad)
        bad = copy.deepcopy(diagnostics); bad['neural_stage_record_pairs'] = 288; variants.append(bad)
        bad = copy.deepcopy(diagnostics); bad['stages'][0]['elapsed_ns'] = 1; variants.append(bad)
        bad = copy.deepcopy(diagnostics); bad['aborted'] = True; variants.append(bad)
        for changed in variants:
            with self.assertRaises(ValueError): audit.check_candidate_diagnostics(changed, model, target, base)

    def test_literal_new_worker_command_limits_and_one_settled_debit(self):
        directory, program, inputs, snapshot, sealed = receipts()
        with patch.object(audit, 'read_completed', return_value=sealed):
            self.assertEqual(audit.check_worker_receipt(directory, program, inputs, snapshot)[0], sealed)
        for mutate in ('command', 'phase', 'limits', 'plan', 'debit', 'empty_budget'):
            directory, program, inputs, snapshot, sealed = receipts()
            root = directory/'quality'
            identity = inputs.objects[str(root/'worker/identity.json')]
            if mutate == 'command': identity['command'][3] = 'research_v55.worker'
            if mutate == 'phase': identity['phase_budget']['phase'] = 'feasibility'
            if mutate == 'limits': identity['limits']['threads'] = 2
            if mutate == 'plan': inputs.objects[str(root/'plan.json')]['output'] = '/other'
            if mutate == 'debit': snapshot['attempts'] = {'other': sealed['budget_debit']}
            if mutate == 'empty_budget': inputs.objects[str(root/'transaction.json')]['budget'] = {}
            with patch.object(audit, 'read_completed', return_value=sealed):
                with self.assertRaises(ValueError): audit.check_worker_receipt(directory, program, inputs, snapshot)

    def test_partial_terminal_or_failed_worker_is_not_a_verified_result(self):
        for kind in ('absent', 'failed', 'seal', 'controller_bytes'):
            directory, program, inputs, snapshot, sealed = receipts()
            returned = sealed
            if kind == 'absent': returned = None
            if kind == 'failed': returned = dict(sealed, outcome=dict(status='failed', returncode=1))
            if kind == 'seal': inputs.objects[str(directory/'quality/worker/result.json')]['attempt'] = 'other'
            if kind == 'controller_bytes': inputs.raw[str(directory/'quality/worker/attempt-one/stdout.bin')] = dict(bytes=1, sha256='wrong')
            with patch.object(audit, 'read_completed', return_value=returned):
                with self.assertRaises(ValueError): audit.check_worker_receipt(directory, program, inputs, snapshot)

    def test_audit_requires_linux_allocation_before_reading_or_writing(self):
        with patch.object(audit.sys, 'platform', 'darwin'), patch.dict(audit.os.environ, SLURM_JOB_ID='fixture'):
            with self.assertRaisesRegex(ValueError, 'bounded Linux Slurm'): audit.audit('/unread', '/unwritten')
        with patch.object(audit.sys, 'platform', 'linux'), patch.dict(audit.os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'bounded Linux Slurm'): audit.audit('/unread', '/unwritten')


if __name__ == '__main__':
    unittest.main()
