"""Read-only planner fixtures: no model, empirical data, compiler, or GPU work."""
from contextlib import ExitStack, redirect_stdout
from dataclasses import FrozenInstanceError
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research_v42.resource_plan import BoundTarget, DEFAULT_TARGET_DIR, main, plan_request


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def fixture(shapes=((2, 3),), original=1664):
    stages = []
    for i, shape in enumerate(shapes):
        stages.append(dict(stage_id='stage.' + str(i), shape=list(shape),
            dependencies=[s['stage_id'] for s in stages], normalization=[original, 1],
            ridge=[1, 100], grid_axis='output_row', significant_bits=24,
            row_scale_hex=['0x1.0000000000000p+0'] * shape[0], weights_sha256='1' * 64))
    anchor = dict(schema='fixed-v-cert-dyadic-row-grid-diagnostic-target-v1',
        evaluator_id='certified-decoder-v1:' + '2' * 64,
        numerical_contract='correctly-rounded finite sequential features; exact rational metric; fixed base-only output-row dyadic24 grids; lower ties',
        grid_recipe='output-row-extrema-smallest-dyadic24-cover-with-exact-midpoints-v1',
        coordinate_order='input coordinate ascending; output row ascending; declared stage order',
        normalization_rule='original calibration token total; fixed for every retained subset',
        scale_fitting='base weights only; no calibration fitting or retained-data refit',
        significant_bits=24, code_count=16, code_min=-8, code_max=7,
        minimum_row_scale_hex='0x0.0000000000002p-1022',
        zero_row_scale_rule='minimum admissible positive scale; exact half-step midpoint required',
        recipe=dict(schema='fixed-target-recipe-v1', bits=4,
                    original_token_count=original, ridge=[1, 100]), stages=stages)
    fixed = dict(schema='fixed-nearest-anchor-calibration-target-v1',
        anchor_target_sha256=hashlib.sha256(encoded(anchor)).hexdigest(),
        decoder_sha256='2' * 64, provider_sha256='3' * 64, constructor_source_sha256='4' * 64,
        feature_rule='every stage uses its fixed source-local nearest-grid anchor features',
        output_rule='calibrate each stage independently in the fixed anchor feature metric',
        prefix_rule='calibrated output codes never affect any feature',
        anchor_rule='base-only canonical dyadic grids; nearest rounding; lower midpoint ties',
        normalization_rule='unchanged original normalization from anchor target',
        state_family='fixed_anchor_calibration_v1')
    return anchor, fixed


def bind(anchor, fixed):
    fixed = dict(fixed, anchor_target_sha256=hashlib.sha256(encoded(anchor)).hexdigest())
    return BoundTarget(encoded(anchor), encoded(fixed))


class ResourcePlanTests(unittest.TestCase):
    def test_wide_coefficient_pass_does_not_admit_full_token_solver(self):
        target = bind(*fixture(((768, 3072),)))
        result = plan_request(target, 768)
        token = result['stages'][0]['routes']['token_point']
        self.assertTrue(token['coefficient_assessment']['admitted'])
        self.assertFalse(token['solver_admitted'])
        # Independently fixed values from the complete V30 schedule, including
        # both row passes and all sixteen bounded refinements.
        self.assertEqual(token['work_units'], 43_488_927_744)
        self.assertEqual(token['explicit_array_bytes'], 603_987_968)
        self.assertEqual(token['max_refinement_coordinates'], 16)
        self.assertEqual(set(token['solver_blockers']), {
            'complete_token_work_exceeds_existing_limit',
            'complete_token_arrays_exceed_existing_limit'})
        self.assertEqual(result['solver_blocked_stage_ids'], ['stage.0'])

    def test_every_real_stage_is_reported_at_both_requested_sizes(self):
        target = BoundTarget((DEFAULT_TARGET_DIR / 'base-target.json').read_bytes(),
                             (DEFAULT_TARGET_DIR / 'fixed-target.json').read_bytes())
        expected = [stage.stage_id for stage in target.stages]
        wide = {stage.stage_id for stage in target.stages if stage.width == 3072}
        self.assertEqual(len(expected), 24)
        self.assertEqual(len(wide), 6)
        for tokens in (768, 1536):
            result = plan_request(target, tokens)
            self.assertEqual([s['binding']['stage_id'] for s in result['stages']], expected)
            self.assertEqual(result['route_blocked_stage_ids'], expected)
            self.assertTrue(wide <= set(result['solver_blocked_stage_ids']))
            for stage in result['stages']:
                self.assertEqual(stage['binding']['normalization'], (1664, 1))
                self.assertIsNone(stage['selected_route'])
                for route in stage['routes'].values():
                    self.assertFalse(route['route_admitted'])
                    self.assertTrue(route['route_blockers'])

    def test_stream_partition_is_conservative_not_assumed_full_blocks(self):
        target = bind(*fixture())
        result = plan_request(target, 129)
        route = result['stages'][0]['routes']['streamed_primal_ball']
        self.assertEqual(route['max_blocks'], 129)
        self.assertEqual(result['streamed_max_blocks'], 129)
        self.assertEqual(route['block_tokens'], 128)

    def test_tiny_solver_success_still_refuses_unreviewed_service(self):
        result = plan_request(bind(*fixture()), 2)
        self.assertTrue(result['stages'][0]['any_solver_admitted'])
        self.assertFalse(result['request_admitted'])
        self.assertFalse(result['solver_dispatch_implemented'])
        self.assertFalse(result['canonical_state_oracle_implemented'])
        self.assertFalse(result['target_provenance_authenticated'])
        self.assertIn('canonical_successor_state_contract_and_independent_oracle_missing',
                      result['request_blockers'])
        self.assertFalse(result['stages'][0]['routes']['token_box']['complete_solver_assessed'])

    def test_cumulative_token_reservations_are_not_reset_per_stage(self):
        result = plan_request(bind(*fixture(((768, 3072), (768, 3072)))), 768)
        total = result['token_cumulative']
        self.assertEqual(total['work_units'], 2 * 43_488_927_744)
        self.assertEqual(total['existing_request_limit'], 48_000_000_000)
        self.assertFalse(total['within_existing_limit'])
        self.assertEqual(len(result['stages']), 2)

    def test_binding_is_immutable_and_fresh_report_edits_do_not_change_it(self):
        target = bind(*fixture())
        with self.assertRaises(FrozenInstanceError):
            target.anchor_payload = b'{}'
        with self.assertRaises(FrozenInstanceError):
            target.stages[0].width = 7
        first = plan_request(target, 2)
        first['stages'][0]['binding']['width'] = 9
        self.assertEqual(plan_request(target, 2)['stages'][0]['binding']['width'], 3)

    def test_changed_shape_or_grid_cannot_keep_old_target_identity(self):
        anchor, fixed = fixture()
        old = bind(anchor, fixed)
        for key, value in [('weights_sha256', '5' * 64),
                           ('row_scale_hex', ['0x1.0000000000000p+1'] * 2),
                           ('shape', [2, 4])]:
            changed = json.loads(encoded(anchor))
            changed['stages'][0][key] = value
            with self.assertRaisesRegex(ValueError, 'does not bind'):
                BoundTarget(encoded(changed), old.fixed_payload)
            new = bind(changed, fixed)
            self.assertNotEqual(old.stages[0].stage_sha256, new.stages[0].stage_sha256)
            self.assertNotEqual(old.stages[0].target_sha256, new.stages[0].target_sha256)

    def test_different_original_normalization_is_bound_not_replaced_by_retention(self):
        first = plan_request(bind(*fixture(original=1664)), 2)
        second = plan_request(bind(*fixture(original=2048)), 2)
        self.assertNotEqual(first['target_sha256'], second['target_sha256'])
        self.assertEqual(first['stages'][0]['binding']['normalization'], (1664, 1))
        self.assertEqual(second['stages'][0]['binding']['normalization'], (2048, 1))

    def test_malformed_or_unsupported_target_contracts_are_rejected(self):
        for change in ('duplicate', 'prefix', 'normalization', 'ridge', 'bits', 'shape', 'scales'):
            anchor, fixed = fixture(((2, 3), (2, 3)))
            if change == 'duplicate':
                anchor['stages'][1]['stage_id'] = 'stage.0'
            elif change == 'prefix':
                anchor['stages'][1]['dependencies'] = []
            elif change == 'normalization':
                anchor['stages'][0]['normalization'] = [2, 1]
            elif change == 'ridge':
                anchor['stages'][0]['ridge'] = [1, 10]
            elif change == 'bits':
                anchor['recipe']['bits'] = True
            elif change == 'shape':
                anchor['stages'][0]['shape'] = [2, True]
            elif change == 'scales':
                anchor['stages'][0]['row_scale_hex'][0] = 'inf'
            with self.subTest(change=change), self.assertRaises(ValueError):
                bind(anchor, fixed)
        anchor, fixed = fixture()
        fixed['prefix_rule'] = 'use recalibrated ancestors'
        with self.assertRaisesRegex(ValueError, 'numerical contract'):
            bind(anchor, fixed)

    def test_canonical_json_and_immutable_input_are_required(self):
        target = bind(*fixture())
        with self.assertRaises(ValueError):
            BoundTarget(target.anchor_payload + b'\n', target.fixed_payload)
        with self.assertRaises(TypeError):
            BoundTarget(bytearray(target.anchor_payload), target.fixed_payload)

    def test_anchor_semantics_and_decoder_must_agree_with_fixed_wrapper(self):
        for key, value in (
            ('coordinate_order', 'input coordinate descending'),
            ('grid_recipe', 'refit grids from retained features'),
            ('code_count', 256), ('code_min', -128), ('code_max', 127),
            ('significant_bits', 53),
            ('normalization_rule', 'renormalize after deletion'),
            ('evaluator_id', 'certified-decoder-v1:' + '5' * 64),
        ):
            anchor, fixed = fixture()
            anchor[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                bind(anchor, fixed)

    def test_inexpressible_grids_are_rejected_without_weight_access(self):
        for value in (float.fromhex('0x0.0000000000001p-1022'),
                      float.fromhex('0x1.0000000000001p+0'),
                      float.fromhex('0x1.fffffffffffffp+1023')):
            anchor, fixed = fixture()
            anchor['stages'][0]['row_scale_hex'][0] = value.hex()
            with self.subTest(scale=value.hex()), self.assertRaisesRegex(ValueError, 'dyadic24 grid'):
                bind(anchor, fixed)

    def test_empty_retention_preserves_original_target_and_reports_all_stages(self):
        target = bind(*fixture(((2, 3), (1, 2))))
        result = plan_request(target, 0)
        self.assertEqual(len(result['stages']), 2)
        self.assertEqual(result['streamed_max_blocks'], 0)
        self.assertEqual(result['original_tokens'], 1664)
        self.assertTrue(all(s['binding']['normalization'] == (1664, 1) for s in result['stages']))
        self.assertFalse(result['request_admitted'])

    def test_invalid_requested_extents_are_rejected_before_any_assessment(self):
        target = bind(*fixture())
        for tokens in (True, -1, 1665, 1.5):
            with self.subTest(tokens=tokens), self.assertRaises(ValueError):
                plan_request(target, tokens)
        for block_tokens in (False, 0, -1, 1.5):
            with self.assertRaises(ValueError):
                plan_request(target, 2, block_tokens=block_tokens)

    def test_planning_cannot_allocate_numerical_arrays_or_run_native_builds(self):
        target = bind(*fixture())
        plan_request(target, 2)  # Import helpers before instrumenting numerical entry points.
        with ExitStack() as stack:
            for name in ('numpy.empty', 'numpy.zeros', 'numpy.array', 'numpy.concatenate',
                         'subprocess.run', 'subprocess.Popen'):
                stack.enter_context(patch(name, side_effect=AssertionError('unexpected numerical or process work')))
            result = plan_request(target, 768)
        self.assertFalse(result['numerical_arrays_allocated'])
        self.assertFalse(result['empirical_worker_launched'])

    def test_cli_writes_fresh_output_only_and_is_deterministic(self):
        target = bind(*fixture())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            anchor, fixed, output = root / 'anchor.json', root / 'fixed.json', root / 'plan.json'
            anchor.write_bytes(target.anchor_payload)
            fixed.write_bytes(target.fixed_payload)
            args = ['--anchor-target', str(anchor), '--fixed-target', str(fixed),
                    '--retained-tokens', '2', '0', '--output', str(output)]
            with redirect_stdout(io.StringIO()):
                main(args)
            original = output.read_bytes()
            report = json.loads(original)
            self.assertEqual([c['retained_tokens'] for c in report['cases']], [2, 0])
            self.assertIn('research_v42/resource_plan.py', report['cases'][0]['source_sha256'])
            with self.assertRaises(FileExistsError):
                main(args)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(plan_request(target, 2), plan_request(target, 2))


if __name__ == '__main__':
    unittest.main()
