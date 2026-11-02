"""Canonical target fixtures only; no corpus access or real-model inference."""
import copy
from dataclasses import FrozenInstanceError
import unittest

from research_v61 import target as t
from src.run_store import canonical_json, digest


def fixture(shapes=((2, 3),), original=8):
    """Small full-contract metadata; source hashes here are fixture identities."""
    base = dict(t.BASE_CONTRACT, evaluator_id='certified-decoder-v1:'+'2'*64,
        recipe=dict(schema='fixed-target-recipe-v1', original_token_count=original,
            bits=4, ridge=[1, 100], group_count=1, max_grid_entries=1_000_000),
        service_sources_sha256={'fixture.py': '1'*64}, stages=[])
    base.update({name: '1'*64 for name in t.BASE_SOURCE_KEYS})
    for index, shape in enumerate(shapes):
        base['stages'].append(dict(stage_id='stage.'+str(index), shape=list(shape),
            dependencies=sorted(s['stage_id'] for s in base['stages']), normalization=[original, 1],
            ridge=[1, 100], grid_axis='output_row', significant_bits=24,
            row_scale_hex=[float(1).hex()]*shape[0], weights_sha256=digest(str(index).encode())))
    return base, service_for(base)


def service_for(base):
    return t._service_manifest(base, t._calibration_manifest(base, '3'*64))


def bind(base, service):
    return t.BoundTarget(canonical_json(base), canonical_json(service))


class TargetTests(unittest.TestCase):
    def test_actual_tiny_constructor_preserves_exact_v59_payload_and_distinct_identity(self):
        from research_v59.anchor import build_full_precision_anchor_target
        from src.dyadic_row_target import build_dyadic_row_target
        from src.fixed_anchor_target import build_fixed_anchor_target
        from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
        from src.target_manifest import TargetRecipe
        from tests.test_transformer_backend import decoder_fixture
        decoder = OrderedFiniteDecoder(decoder_fixture(), primitive_backend='mpfr_enclosure')
        base = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=8, group_count=1))
        calibration = build_full_precision_anchor_target(decoder, base)
        nearest = build_fixed_anchor_target(decoder, base)
        service = t.build_service_target(decoder, base)
        bound = bind(base.payload(), service.payload())
        self.assertEqual(service.payload()['calibration_target'], calibration.payload())
        self.assertEqual(bound.calibration_target_sha256, calibration.digest)
        self.assertEqual(service.payload()['calibration_target']['output_rule'],
            'complete stage codes only; no canonical repair-state contract declared')
        self.assertEqual(len({base.digest, nearest.digest, calibration.digest, service.digest}), 4)
        self.assertIs(service.base_target, base)
        self.assertIs(service.recipe, base.recipe)
        self.assertTrue(all(s.dependencies == () for s in service.stages))
        self.assertEqual(service.payload()['provider_sha256'], t.provider_binding())
        self.assertEqual([s.stage_id for s in bound.stages], list(decoder.stage_ids))

    def test_immutable_canonical_bytes_and_stage_bindings(self):
        base, service = fixture(((2, 3), (1, 2)), original=1664)
        target = bind(base, service)
        self.assertEqual(target.original_tokens, 1664)
        self.assertEqual(target.stages[1].normalization, (1664, 1))
        self.assertEqual(target.stages[0].target_sha256, digest(target.fixed_payload))
        with self.assertRaises(FrozenInstanceError): target.fixed_payload = b'{}'
        with self.assertRaises(FrozenInstanceError): target.stages[0].width = 99
        with self.assertRaises(TypeError): t.BoundTarget(bytearray(target.anchor_payload), target.fixed_payload)
        with self.assertRaises(ValueError): t.BoundTarget(target.anchor_payload+b' ', target.fixed_payload)

    def test_full_real_stage_order_accepts_lexically_sorted_dependencies(self):
        base, _ = fixture(((1, 2),)*24)
        ids = [f'block.{i:04d}.{kind}' for i in range(6) for kind in ('qkv', 'attn_out', 'mlp_up', 'mlp_down')]
        for index, entry in enumerate(base['stages']):
            entry.update(stage_id=ids[index], dependencies=sorted(ids[:index]))
        target = bind(base, service_for(base))
        self.assertEqual([s.stage_id for s in target.stages], ids)
        self.assertNotEqual(base['stages'][3]['dependencies'], ids[:3])
        self.assertEqual(len(target.stages), 24)

    def test_nearest_and_bare_v59_targets_cannot_be_relabelled_as_service(self):
        from research_v42.test_resource_plan import fixture as nearest_fixture
        base, service = fixture()
        for foreign in (nearest_fixture()[1], service['calibration_target']):
            with self.assertRaises(ValueError): bind(base, foreign)
        for key, value in [('schema', 'fixed-nearest-anchor-calibration-target-v1'),
                ('state_family', 'fixed_anchor_calibration_v1'), ('state_schema', 'complete-fixed-anchor-successor-v53')]:
            bad = copy.deepcopy(service); bad[key] = value
            with self.assertRaises(ValueError): bind(base, bad)

    def test_teacher_and_embedded_v59_rules_are_checked_after_rehashing(self):
        base, service = fixture(((1, 2), (1, 2)))
        changes = [('anchor_rule', 'nearest grid'), ('original_normalization', 4),
            ('base_target_sha256', '0'*64), ('constructor_source_sha256', '0'*64),
            ('output_rule', 'complete service state'), ('calibrated_dependencies', 'sequential prefixes')]
        for key, value in changes:
            bad = copy.deepcopy(service['calibration_target']); bad[key] = value
            rehashed = t._service_manifest(base, bad)
            with self.assertRaises(ValueError): bind(base, rehashed)
        bad = copy.deepcopy(service['calibration_target']); bad['teacher_stages'][1]['weights_sha256'] = '0'*64
        with self.assertRaises(ValueError): bind(base, t._service_manifest(base, bad))
        bad = copy.deepcopy(service['calibration_target']); bad['teacher_stages'].reverse()
        with self.assertRaises(ValueError): bind(base, t._service_manifest(base, bad))
        bad = copy.deepcopy(service['calibration_target']); bad['teacher_stages'][0]['shape'][0] = True
        with self.assertRaises(ValueError): bind(base, t._service_manifest(base, bad))

    def test_decoder_provider_constructor_and_base_commitments_are_bound(self):
        base, service = fixture()
        for key in ('decoder_sha256', 'implementation_manifest_sha256', 'provider_sha256',
                'constructor_source_sha256', 'anchor_target_sha256', 'calibration_target_sha256'):
            bad = copy.deepcopy(service); bad[key] = '0'*64
            with self.assertRaises(ValueError): bind(base, bad)
        bad = copy.deepcopy(base); bad['stages'][0]['weights_sha256'] = '0'*64
        with self.assertRaises(ValueError): bind(bad, service)
        changed = bind(bad, service_for(bad))
        self.assertNotEqual(changed.fixed_payload, bind(base, service).fixed_payload)

    def test_contradictory_base_recipe_dependencies_and_grids_reject_even_with_new_hashes(self):
        for change in ('normalization', 'ridge', 'prefix', 'duplicate', 'shape', 'bits', 'scales', 'grid_precision', 'grid_limit'):
            base, _ = fixture(((2, 3), (1, 2)))
            if change == 'normalization': base['stages'][0]['normalization'] = [4, 1]
            if change == 'ridge': base['stages'][0]['ridge'] = [1, 10]
            if change == 'prefix': base['stages'][1]['dependencies'] = []
            if change == 'duplicate': base['stages'][1]['stage_id'] = 'stage.0'
            if change == 'shape': base['stages'][0]['shape'] = [2, True]
            if change == 'bits': base['recipe']['bits'] = True
            if change == 'scales': base['stages'][0]['row_scale_hex'][0] = 'inf'
            if change == 'grid_precision': base['stages'][0]['row_scale_hex'][0] = float.fromhex('0x1.0000001p+0').hex()
            if change == 'grid_limit': base['recipe']['max_grid_entries'] = 1
            with self.subTest(change=change), self.assertRaises(ValueError): bind(base, service_for(base))

    def test_finite_arithmetic_and_source_local_base_contract_cannot_change(self):
        for key, value in [('weight_digest_encoding', 'integer_pair_json_v1'), ('attention_scope', 'cross-record'),
                ('scale_fitting', 'fit retained sources'), ('code_count', 8), ('coordinate_order', 'reverse'),
                ('fixed_components', 'retune norms'), ('output_rule', 'service state')]:
            base, _ = fixture(); base[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): bind(base, service_for(base))
        base, _ = fixture(); base['stages'][0]['row_scale_hex'][0] = '0x0.0000000000001p-1022'
        with self.assertRaises(ValueError): bind(base, service_for(base))
        base, _ = fixture(); base['recipe']['ridge'] = [2, 200]
        with self.assertRaises(ValueError): bind(base, service_for(base))


if __name__ == '__main__':
    unittest.main()
