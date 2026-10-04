"""Algebraic correctness fixtures; no empirical datasets or timing claims."""
from fractions import Fraction as Q
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.aggregate_response_service import AggregateRepairService
from src.box_response_provider import BoxResponseProvider, ParameterBox, grid_box
from src.certified_transformer import AutomaticResponseProvider, CertifiedDecoder, _Finite, _execute
from src.linear_response import LinearResponseIndex, shifted_linear_response_bound
from src.repair_service import Record, StageSpec, UnknownBound, _is_psd
from src.response_moments import ResponseIndex
from src.target_manifest import TargetRecipe, build_target
from tests.test_certified_transformer import grids, small_decoder


def narrow_box(decoder, width=Q(1, 4096)):
    first = decoder.stage_ids[0]
    bounds = tuple(tuple((value - width, value + width) for value in row)
                   for row in decoder.stage_weights(first))
    return ParameterBox({first: bounds}, 'fixed narrow box before calibration')


class BoxResponseProviderTests(unittest.TestCase):
    def test_immutable_strict_box_and_shape_checks(self):
        decoder, _ = small_decoder()
        box = narrow_box(decoder)
        self.assertEqual(box.canonical_bytes(), narrow_box(decoder).canonical_bytes())
        with self.assertRaises(TypeError):
            box.bounds_by_stage['other'] = ()
        with self.assertRaises(ValueError):
            ParameterBox({}, '', 96)
        with self.assertRaises(ValueError):
            ParameterBox({}, 'fixed', True)
        for endpoints in ((0.1, Q(1)), (True, Q(1))):
            with self.assertRaises(TypeError):
                ParameterBox({'s': ((endpoints,),)}, 'fixed')
        with self.assertRaises(ValueError):
            ParameterBox({'s': (((1, 0),),)}, 'fixed')
        with self.assertRaises(ValueError):
            BoxResponseProvider(decoder, ParameterBox({'unknown': (((0, 1),),)}, 'fixed'))
        with self.assertRaises(ValueError):
            BoxResponseProvider(decoder, ParameterBox({decoder.stage_ids[0]: (((0, 1),),)}, 'fixed'))
        provider = BoxResponseProvider(decoder, box)
        with self.assertRaises(AttributeError):
            provider.box = box

    def test_grid_box_contains_every_grid_prefix_and_has_no_affine_restriction(self):
        decoder, chart = small_decoder()
        target = build_target(decoder, TargetRecipe(6, group_count=1))
        box = grid_box(decoder, target, 'fixed full-grid box')
        provider = BoxResponseProvider(decoder, box)
        self.assertNotIn(decoder.stage_ids[-1], box.bounds_by_stage)
        self.assertEqual(sum(2 * len(row) for bounds in box.bounds_by_stage.values() for row in bounds),
                         2 * sum(len(stage.weights) * stage.width for stage in target.stages[:-1]))
        prefix = {}
        for stage in target.stages:
            self.assertTrue(provider.contains_prefix(stage.stage_id, prefix))
            prefix[stage.stage_id] = tuple(tuple(stage.grids[j][(i+j) % len(stage.grids[j])]
                                                for j in range(stage.width)) for i in range(len(stage.weights)))
        first, second = decoder.stage_ids[:2]
        changed = [list(row) for row in decoder.stage_weights(first)]
        changed[0][0] += Q(1, 4096)
        self.assertIsNone(AutomaticResponseProvider(decoder, chart).coefficients(second, {first: changed}))
        self.assertTrue(provider.contains_prefix(second, {first: changed}))

    def test_membership_uses_installed_finite_weights_and_all_dependencies(self):
        decoder, _ = small_decoder()
        provider = BoxResponseProvider(decoder, narrow_box(decoder))
        first, second, third = decoder.stage_ids[:3]
        changed = [list(row) for row in decoder.stage_weights(first)]
        changed[0][0] += Q(1, 4096)
        self.assertTrue(provider.contains_prefix(second, {first: changed}))
        changed[0][0] += Q(1, 4096)
        self.assertFalse(provider.contains_prefix(second, {first: changed}))
        later = [list(row) for row in decoder.stage_weights(second)]
        later[0][0] += Q(1, 4096)
        self.assertFalse(provider.contains_prefix(third, {second: later}))
        self.assertTrue(provider.contains_prefix(first, {second: later}))
        # Distinct exact proposals that install the same binary64 value qualify.
        base_only = BoxResponseProvider(decoder, ParameterBox({}, 'fixed base-only box'))
        changed = [list(row) for row in decoder.stage_weights(first)]
        changed[0][0] += Q(1, 2**80)
        self.assertTrue(base_only.contains_prefix(second, {first: changed}))
        context = SimpleNamespace(stage=SimpleNamespace(stage_id=third), binding='binding',
                                  prefix=SimpleNamespace(as_mapping=lambda: {second: later}))
        self.assertIsInstance(provider.query(context), UnknownBound)

    def test_out_of_span_finite_features_and_gram_are_enclosed(self):
        decoder, chart = small_decoder()
        provider = BoxResponseProvider(decoder, narrow_box(decoder))
        first, stage_id = decoder.stage_ids[:2]
        stage = StageSpec(stage_id, decoder.dependencies(stage_id), decoder.stage_weights(stage_id),
                          grids(decoder)[stage_id], 1, 1)
        record = Record('proof', decoder.record_payload((0, 1)))
        moments = provider.intrinsic_moments(record, stage)
        self.assertIsNotNone(moments)
        response, error = moments
        response_index = LinearResponseIndex.from_records(response.basis, (response,))
        error_index = ResponseIndex.from_records(error.basis, (error,))
        bound = shifted_linear_response_bound(response_index, error_index, (), 1, 1)
        self.assertEqual(bound.omitted_psd_trace_normalized, 0)
        region = provider.feature_enclosures(stage_id, (0, 1))
        for sign in (-1, 1):
            changed = [list(row) for row in decoder.stage_weights(first)]
            changed[0][0] += sign * Q(1, 4096)
            changed[4][1] -= sign * Q(1, 4096)
            prefix = {first: changed}
            self.assertIsNone(AutomaticResponseProvider(decoder, chart).coefficients(stage_id, prefix))
            values = decoder.stage_features(stage_id, (0, 1), prefix)
            for row, enclosures in zip(values, region):
                for value, enclosure in zip(row, enclosures):
                    self.assertLessEqual(enclosure.value.lo - enclosure.error, value)
                    self.assertGreaterEqual(enclosure.value.hi + enclosure.error, value)
            gram = tuple(tuple(sum(a*b for a, b in zip(xi, xj)) for xj in values) for xi in values)
            for direction in (-1, 1):
                matrix = tuple(tuple(direction * (gram[i][j] - bound.raw_surrogate_gram[i][j])
                                     + (bound.normalized_absolute_gram_error if i == j else 0)
                                     for j in range(len(gram))) for i in range(len(gram)))
                self.assertTrue(_is_psd(matrix))

    def test_lazy_parameter_allocation_and_unchanged_finite_schedule(self):
        decoder, chart = small_decoder()
        provider = BoxResponseProvider(decoder, narrow_box(decoder))
        first, second = decoder.stage_ids[:2]
        with patch.object(BoxResponseProvider, '_parameter_weights', autospec=True,
                          side_effect=AssertionError('first-stage inputs need no parameter wrappers')):
            provider.feature_enclosures(first, (0, 1))
        original = BoxResponseProvider._parameter_weights
        accesses = []
        def tracked(instance, stage):
            accesses.append(stage)
            return original(instance, stage)
        with patch.object(BoxResponseProvider, '_parameter_weights', tracked):
            provider.feature_enclosures(second, (0, 1))
        self.assertEqual(accesses, [first])
        eager = {stage: tuple(tuple(_Finite(value) for value in row)
                             for row in decoder.base._float_weights[stage]) for stage in decoder.stage_ids}
        for stop in (*decoder.stage_ids, None):
            expected = _execute(decoder.base, (0, 1), eager, lambda x: _Finite(float(x)), stop)
            actual = decoder._eval((0, 1), {}, stop)
            self.assertEqual(actual, expected)
        with patch('src.certified_transformer._StageWeights.__getitem__',
                   side_effect=AssertionError('first-stage chart inputs need no parameter wrappers')):
            AutomaticResponseProvider(decoder, chart).feature_jets(first, (0, 1), region=True)

    def test_repair_and_replay_have_identical_canonical_state(self):
        decoder, _ = small_decoder()
        target = build_target(decoder, TargetRecipe(6, ridge=Q(1), group_count=1))
        provider = BoxResponseProvider(decoder, narrow_box(decoder))
        job = target.make_job(provider.reference_id)
        def evaluate(record, stage, prefix):
            return decoder.stage_features(stage.stage_id, decoder.decode_payload(record.payload), prefix.as_mapping())
        service = AggregateRepairService(job, evaluate, provider.intrinsic_moments, provider.contracts,
                                        provider.query, provider_id=provider.provider_id,
                                        extractor_id=provider.reference_id)
        records = tuple(Record(str(i), decoder.record_payload(tokens))
                        for i, tokens in enumerate(((0, 1), (1, 0), (0, 2))))
        old = service.fresh(records)
        by_id = {record.record_id: record for record in records}
        repaired = service.repair(old.state, (records[0],), by_id.__getitem__)
        fresh = service.fresh(records[1:])
        self.assertEqual(repaired.state.canonical_bytes(), fresh.state.canonical_bytes())
        retained_index = service.prepare_index(old.state, (records[0],)).index
        direct = service.indexed_fresh(retained_index, by_id.__getitem__, mode='full_replay')
        self.assertEqual(repaired.state.canonical_bytes(), direct.state.canonical_bytes())

    def test_interval_proof_failure_marks_contribution_unavailable(self):
        decoder, _ = small_decoder()
        provider = BoxResponseProvider(decoder, narrow_box(decoder))
        stage_id = decoder.stage_ids[1]
        stage = StageSpec(stage_id, decoder.dependencies(stage_id), decoder.stage_weights(stage_id),
                          grids(decoder)[stage_id], 1, 1)
        record = Record('proof', decoder.record_payload((0, 1)))
        with patch.object(BoxResponseProvider, 'feature_enclosures', side_effect=ArithmeticError('proof failed')):
            self.assertIsNone(provider.intrinsic_moments(record, stage))

    def test_hybrid_anchor_skips_unneeded_evaluation_and_has_exact_identity_error(self):
        decoder, _ = small_decoder()
        provider = BoxResponseProvider(decoder, narrow_box(decoder))
        record = Record('proof', decoder.record_payload((0, 1)))
        stages = tuple(StageSpec(stage, decoder.dependencies(stage), decoder.stage_weights(stage),
                                 grids(decoder)[stage], 1, 1) for stage in decoder.stage_ids)
        with patch.object(CertifiedDecoder, 'stage_features', side_effect=AssertionError('midpoint needs no finite anchor')):
            moments = provider.intrinsic_moments(record, stages[1])
            self.assertIsNotNone(moments)
        with patch.object(BoxResponseProvider, 'feature_enclosures', side_effect=AssertionError('base-only inputs need no intervals')):
            _, error = provider.intrinsic_moments(record, stages[0])
            self.assertTrue(all(value == 0 for matrix in error.cross_moments for row in matrix for value in row))
        region = provider.feature_enclosures(stages[1].stage_id, (0, 1))
        midpoint = tuple(tuple((bound.value.lo + bound.value.hi) / 2 for bound in row) for row in region)
        expected = tuple(tuple(sum(a*b for a, b in zip(xi, xj)) for xj in midpoint) for xi in midpoint)
        self.assertEqual(moments[0].constant_gram, expected)


if __name__ == '__main__':
    unittest.main()
