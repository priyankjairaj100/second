"""Machine-program enclosure checks. These fixtures are not research data.

Composition checks share kernels and solvers with the service reference.
They are not an independent neural implementation. The exact rational oracle
checks the quantizer algebra separately. Box containment uses numerical order,
which identifies both signed zeros. Bit checks below concern these fixtures;
they do not assert general signed-zero encoding equivalence.
"""
from fractions import Fraction as Q
import itertools
import unittest
import numpy as np

from src.certified_transformer import CertifiedDecoder
from src.finite_feature_boxes import FloatBox, feature_box, logits_box, sequential_feature_boxes
from src.finite_primitives import primitive_scope
from tests.test_transformer_backend import decoder_fixture
from tests.test_certified_transformer import small_decoder


def bits(rows):
    return np.asarray(rows, dtype=np.float64).tobytes()


class FiniteFeatureBoxTests(unittest.TestCase):
    def test_singleton_every_stage_and_final_logits(self):
        for backend in ('rational', 'mpfr_enclosure'):
            for heads in (1, 2):
                decoder = CertifiedDecoder(decoder_fixture(block_count=2, head_count=heads),
                                           primitive_backend=backend)
                tokens = (0, 1, 2)
                stream = sequential_feature_boxes(decoder, tokens, include_logits=True)
                stage, box = next(stream)
                prefix = {}
                for expected in decoder.stage_ids:
                    self.assertEqual(stage, expected)
                    reference = np.asarray(decoder.stage_features(stage, tokens, prefix), dtype=float).T
                    self.assertTrue(box.singleton)
                    self.assertEqual(bits(box.lower), bits(reference))
                    # Every installation differs, including later blocks.
                    installed = tuple(tuple(x + Q((-1)**(i+j), 128) for j, x in enumerate(row))
                                      for i, row in enumerate(decoder.stage_weights(stage)))
                    prefix[stage] = installed
                    if stage == decoder.stage_ids[-1]:
                        with self.assertRaises(StopIteration) as end:
                            stream.send(installed)
                        self.assertEqual(bits(end.exception.value.lower), bits(decoder.logits(tokens, prefix)))
                        self.assertTrue(end.exception.value.singleton)
                    else:
                        stage, box = stream.send(installed)

    def test_activation_formulas_match(self):
        for activation in ('gelu', 'gelu_new'):
            decoder, _ = small_decoder(activation)
            for tokens in ((0,), (0, 1), (2, 1, 0)):
                actual = logits_box(decoder, tokens)
                self.assertTrue(actual.singleton)
                self.assertEqual(bits(actual.lower), bits(decoder.logits(tokens)))

    def test_weight_boxes_enclose_changed_prefixes_at_every_stage(self):
        decoder = CertifiedDecoder(decoder_fixture(block_count=2, head_count=2),
                                   primitive_backend='mpfr_enclosure')
        tokens = (0, 1, 2)
        boxes, candidates = {}, []
        for sign in (-1, 0, 1):
            prefix = {}
            for index, stage in enumerate(decoder.stage_ids):
                weights = decoder.stage_weights(stage)
                direction = tuple(tuple(Q((-1)**(i+j+index), 2**18) for j, _ in enumerate(row))
                                  for i, row in enumerate(weights))
                prefix[stage] = tuple(tuple(w + sign * d for w, d in zip(row, change))
                                      for row, change in zip(weights, direction))
                lo = [[float(w - abs(d)) for w, d in zip(row, change)] for row, change in zip(weights, direction)]
                hi = [[float(w + abs(d)) for w, d in zip(row, change)] for row, change in zip(weights, direction)]
                boxes[stage] = FloatBox(lo, hi)
            candidates.append(prefix)
        for stage in decoder.stage_ids:
            enclosure = feature_box(decoder, tokens, boxes, stage)
            for prefix in candidates:
                actual = np.asarray(decoder.stage_features(stage, tokens, prefix), dtype=float).T
                self.assertTrue(enclosure.contains(actual), stage)
        enclosure = logits_box(decoder, tokens, boxes)
        for prefix in candidates:
            self.assertTrue(enclosure.contains(decoder.logits(tokens, prefix)))

    def test_interval_operations_include_all_machine_endpoint_combinations(self):
        a = FloatBox([-2.0, -0.0, 2.0**-1074], [3.0, 1.0, 2.0**-1022])
        b = FloatBox([-3.0, 2.0, 0.5], [-0.5, 3.0, 2.0])
        for operation in (lambda x, y: x+y, lambda x, y: x-y,
                          lambda x, y: x*y, lambda x, y: x/y):
            enclosure = operation(a, b)
            for left, right in itertools.product((a.lower, a.upper), (b.lower, b.upper)):
                self.assertTrue(enclosure.contains(operation(left, right)))
        self.assertTrue(a.square().contains(np.asarray([0.0, 0.0, 0.0])))
        with self.assertRaises(ValueError):
            FloatBox([1.0], [0.0])
        with self.assertRaises((ValueError, ArithmeticError)):
            a / FloatBox([-1.0]*3, [1.0]*3)

    def test_monotone_primitives_enclose_interior_points(self):
        from src.finite_primitives import rounded
        with primitive_scope('mpfr_enclosure'):
            for name in ('sqrt', 'exp', 'erf', 'tanh'):
                lower = 0.0 if name == 'sqrt' else -1.0
                box = FloatBox(lower, 2.0).primitive(name)
                for value in np.linspace(lower, 2.0, 11):
                    self.assertTrue(box.contains(rounded(name, float(value))))

    def test_inputs_cannot_mutate_boxes(self):
        values = np.asarray([[1.0, 2.0]])
        box = FloatBox.point(values)
        values[0, 0] = -100.0
        self.assertEqual(box.lower[0, 0], 1.0)
        with self.assertRaises(ValueError):
            box.lower.flags.writeable = True
        with self.assertRaises(ValueError):
            box.lower[0, 0] = 7.0
        decoder = CertifiedDecoder(decoder_fixture())
        with self.assertRaises(ValueError):
            feature_box(decoder, (0,), {}, 'unknown')
        with self.assertRaises(ValueError):
            logits_box(decoder, (0,), {'unknown': [[1.0]]})

    def test_complete_singleton_box_quantization_matches_direct_service(self):
        from src.compact_service import CompactIdentityService
        from src.ordered_finite import FiniteWeights
        from src.row_target_manifest import build_row_target
        from src.target_manifest import TargetRecipe
        from src.token_box_certificate import certify_row_scaled_box

        decoder = CertifiedDecoder(decoder_fixture(block_count=2),
                                   primitive_backend='mpfr_enclosure')
        recipe = TargetRecipe(original_token_count=6, bits=3, group_count=1, ridge=Q(1, 10))
        target = build_row_target(decoder, recipe)
        service = CompactIdentityService(decoder, target)
        records = [{'id': 'a', 'tokens': [0, 1]}, {'id': 'b', 'tokens': [2, 1]}]
        for retained in (records[:1], records):
            reference = service.run(retained, method='direct_fresh')
            streams = [sequential_feature_boxes(decoder, record['tokens']) for record in retained]
            current = [next(stream) for stream in streams]
            completed = []
            for index, stage in enumerate(target.stages):
                self.assertTrue(all(stage_id == stage.stage_id for stage_id, _ in current))
                self.assertTrue(all(box.singleton for _, box in current))
                factors = np.concatenate([box.lower for _, box in current], axis=0).T.copy()
                certified = certify_row_scaled_box(
                    FiniteWeights(stage.weights).array(), factors, factors, stage.scale_exponents,
                    bits=stage.bits, ridge=stage.ridge, normalization=stage.normalization)
                self.assertEqual(certified.uncertain_features, 0)
                np.testing.assert_array_equal(certified.codes, reference.stages[index].array())
                completed.append(certified.codes)
                if index + 1 == len(target.stages):
                    for stream in streams:
                        with self.assertRaises(StopIteration):
                            stream.send(certified.codes)
                else:
                    current = [stream.send(certified.codes) for stream in streams]
            self.assertEqual(len(completed), len(decoder.stage_ids))

    def test_changed_prefix_hull_composes_with_sound_certificate_or_abstention(self):
        from src.low_rank_exact import token_sequential_oracle
        from src.ordered_finite import FiniteWeights
        from src.row_scaled_quantizer import row_scale_exponents
        from src.token_box_certificate import TokenBoxUnresolved, certify_row_scaled_box

        decoder = CertifiedDecoder(decoder_fixture(block_count=2),
                                   primitive_backend='mpfr_enclosure')
        tokens = (0, 1)
        ancestor = decoder.stage_ids[0]
        original = decoder.stage_weights(ancestor)
        candidates = []
        for sign in (-1, 1):
            candidates.append({ancestor: tuple(tuple(w + sign * Q((-1)**(i+j), 2**18)
                for j, w in enumerate(row)) for i, row in enumerate(original))})
        hull = {ancestor: FloatBox.hull(candidates[0][ancestor], candidates[1][ancestor])}
        self.assertFalse(hull[ancestor].singleton)
        accepted, abstained, uncertain = 0, 0, 0
        for stage in decoder.stage_ids[1:]:
            enclosure = feature_box(decoder, tokens, hull, stage)
            factors = [np.asarray(decoder.stage_features(stage, tokens, prefix), dtype=float)
                       for prefix in candidates]
            for point in factors:
                self.assertTrue(enclosure.contains(point.T))
            uncertain += int(not enclosure.singleton)
            weights = FiniteWeights(decoder.stage_weights(stage)).array()
            exponents = row_scale_exponents(weights, bits=3)
            try:
                result = certify_row_scaled_box(weights, enclosure.lower.T.copy(),
                    enclosure.upper.T.copy(), exponents, bits=3, ridge=10, normalization=6)
            except TokenBoxUnresolved:
                abstained += 1
                continue
            accepted += 1
            normalized = np.ldexp(weights, -np.asarray(exponents)[:, None])
            exact = lambda array: tuple(tuple(Q.from_float(float(x)) for x in row) for row in array)
            for point in factors:
                truth = token_sequential_oracle(exact(normalized), exact(point),
                    [tuple(range(-4, 4))] * weights.shape[1], ridge=10, normalization=6)
                expected = np.ldexp(np.asarray(truth.codes, dtype=float), np.asarray(exponents)[:, None])
                np.testing.assert_array_equal(result.codes, expected)
        self.assertEqual(accepted + abstained, len(decoder.stage_ids) - 1)
        self.assertGreater(uncertain, 0)
        self.assertGreater(accepted, 0)


if __name__ == '__main__':
    unittest.main()
