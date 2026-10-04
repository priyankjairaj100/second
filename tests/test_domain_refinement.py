"""Exact algebraic correctness fixtures; no empirical data or timing study."""
import unittest
from dataclasses import replace
from fractions import Fraction as Q
from itertools import product

from src.domain_refinement import (RationalInterval, GramBinding, GramBox,
    spectral_ball_box, signed_loewner_box, intersect_gram_boxes, interval_reverse_ldl, certify_gram_box)
from src.exact_core import sequential_oracle, certify_relative_enclosure, reverse_ldl


class DomainRefinementTests(unittest.TestCase):
    def setUp(self):
        self.binding = GramBinding('target', 'stage', 'a' * 64, 'b' * 64, Q(12))

    def test_intersection_strictly_improves_both_routes(self):
        weights, codes = ((Q(49, 100), Q(0)),), ((0, 0),)
        grids = ((-1, 0, 1),) * 2
        centers = (((2, Q(9, 10)), (Q(9, 10), 2)),
                   ((2, Q(-9, 10)), (Q(-9, 10), 2)))
        radius = Q(91, 100)
        boxes = tuple(spectral_ball_box(self.binding, center, radius, str(i))
                      for i, center in enumerate(centers))
        for center, box in zip(centers, boxes):
            self.assertFalse(certify_gram_box(weights, codes, grids, box, 1).accepted)
            # This exactly matches the v6 fixed-ridge spectral conversion.
            self.assertFalse(certify_relative_enclosure(weights, center, grids,
                                                        1 - radius, 1 + radius).accepted)
        joined = intersect_gram_boxes(boxes)
        result = certify_gram_box(weights, codes, grids, joined, 1)
        self.assertTrue(result.accepted)
        self.assertEqual(result.candidate, sequential_oracle(weights, ((2, 0), (0, 2)), grids).codes)
        self.assertFalse(result.enclosure_and_ridge_premises_verified_by_module)
        self.assertEqual(joined.evidence_ids, ('0', '1'))

    def test_point_bounds_match_exact_factors_and_oracle(self):
        # The chosen covariance is I + A A^T, so its ridge floor is one.
        covariance = ((6, 2, -1), (2, 3, 1), (-1, 1, 3))
        weights = ((Q(1, 2), Q(-1, 2), Q(7, 4)), (Q(-7, 4), Q(3, 4), Q(0)))
        grids = ((-1, 0, 1),) * 3
        oracle = sequential_oracle(weights, covariance, grids)
        box = spectral_ball_box(self.binding, covariance, 0, 'point')
        result = certify_gram_box(weights, oracle.codes, grids, box, 1)
        self.assertTrue(result.accepted)
        for row, exact in zip(result.lower_factors, oracle.factors.L):
            self.assertEqual(tuple(x.lo for x in row), exact)
            self.assertTrue(all(x.lo == x.hi for x in row))
        self.assertEqual(tuple(x.lo for x in result.pivots), oracle.factors.t)
        self.assertTrue(all(x.lo == x.hi for x in result.pivots))

    def test_lower_ties_saturation_and_singleton_cells(self):
        box = spectral_ball_box(self.binding, ((1,),), 0, 'point')
        for weight, expected in ((Q(-3), -1), (Q(-1, 2), -1), (Q(1, 2), 0), (Q(3), 1)):
            for candidate in (-1, 0, 1):
                result = certify_gram_box(((weight,),), ((candidate,),), ((-1, 0, 1),), box, 1)
                self.assertEqual(result.accepted, candidate == expected)
        self.assertTrue(certify_gram_box(((100,),), ((7,),), ((7,),), box, 1).accepted)
        # A nonzero-width interval can touch its inclusive upper cell exactly.
        broad = GramBox(self.binding, ((1, 0), (0, 1)), ((1, 1), (1, 1)), ('upper-tie',))
        result = certify_gram_box(((Q(1, 2), 0),), ((0, 0),), ((0, 1), (0, 1)), broad, 1)
        self.assertTrue(result.accepted)
        self.assertEqual(result.checks[1].input_interval.hi, Q(1, 2))

    def test_inclusion_monotonicity_with_ridge_clipping(self):
        outer = spectral_ball_box(self.binding, ((3, Q(1, 5)), (Q(1, 5), 3)), Q(1, 3), 'outer')
        inner = spectral_ball_box(self.binding, ((3, Q(1, 5)), (Q(1, 5), 3)), Q(1, 9), 'inner')
        point = spectral_ball_box(self.binding, ((3, Q(1, 5)), (Q(1, 5), 3)), 0, 'point')
        weights = ((Q(1, 4), Q(1, 4)),)
        candidates, grids = ((0, 0),), ((-1, 0, 1),) * 2
        previous = certify_gram_box(weights, candidates, grids, outer, 1)
        for box in (inner, point):
            current = certify_gram_box(weights, candidates, grids, box, 1)
            self.assertTrue(box.subset_of(previous.covariance_box))
            for old, new in zip(previous.checks, current.checks):
                self.assertTrue(new.input_interval.subset_of(old.input_interval))
            self.assertFalse(previous.accepted and not current.accepted)
            previous = current
        # A broad diagonal range crosses zero. The actual ridge premise permits division.
        clipped = GramBox(self.binding, ((-2, 0), (0, -2)), ((3, 0), (0, 3)), ('ridge',))
        factors, pivots = interval_reverse_ldl(clipped, 1)
        self.assertTrue(all(pivot.lo == 1 for pivot in pivots))
        self.assertEqual(factors[1][0], RationalInterval.point(0))

    def test_containment_for_all_rational_boundary_fixtures(self):
        box = GramBox(self.binding, ((2, Q(-1, 10)), (Q(-1, 10), 2)),
                      ((3, Q(1, 10)), (Q(1, 10), 3)), ('boundaries',))
        factors, pivots = interval_reverse_ldl(box, 1)
        for a, b, c in product((Q(2), Q(3)), (Q(-1, 10), Q(0), Q(1, 10)), (Q(2), Q(3))):
            exact = reverse_ldl(((a, b), (b, c)))
            for i in range(2):
                self.assertTrue(pivots[i].lo <= exact.t[i] <= pivots[i].hi)
                for j in range(2):
                    self.assertTrue(factors[i][j].lo <= exact.L[i][j] <= factors[i][j].hi)

    def test_intersection_is_canonical_and_checks_bindings(self):
        a = spectral_ball_box(self.binding, ((2, 0), (0, 2)), Q(1, 2), 'a')
        b = spectral_ball_box(self.binding, ((2, 0), (0, 2)), Q(1, 4), 'b')
        self.assertEqual(intersect_gram_boxes((a, b, a)), intersect_gram_boxes((b, a)))
        self.assertEqual(intersect_gram_boxes((a,)), a)
        for field, value in (('normalization', Q(13)), ('target_id', 'other'),
                             ('stage_id', 'other'), ('retained_digest', 'c' * 64), ('prefix_digest', 'd' * 64)):
            wrong = replace(b, binding=replace(self.binding, **{field: value}))
            with self.assertRaises(ValueError):
                intersect_gram_boxes((a, wrong))
        distant = spectral_ball_box(self.binding, ((8, 0), (0, 8)), 0, 'distant')
        with self.assertRaises(ValueError):
            intersect_gram_boxes((a, distant))
        with self.assertRaises(ValueError):
            intersect_gram_boxes(())

    def test_invalid_or_singular_premises_never_accept(self):
        box = spectral_ball_box(self.binding, ((0,),), 0, 'singular')
        with self.assertRaises(ValueError):
            certify_gram_box(((0,),), ((0,),), ((0,),), box, 1)
        for ridge in (0, -1, True, 0.5):
            with self.assertRaises((ValueError, TypeError)):
                interval_reverse_ldl(box, ridge)
        for args in (((True,),), ((0.5,),)):
            with self.assertRaises(TypeError):
                spectral_ball_box(self.binding, args, 0, 'invalid')
        with self.assertRaises(ValueError):
            spectral_ball_box(self.binding, ((1, 2), (3, 4)), 0, 'asymmetric')
        with self.assertRaises(ValueError):
            spectral_ball_box(self.binding, ((1,),), -1, 'negative')
        with self.assertRaises(ValueError):
            certify_gram_box(((0,),), ((9,),), ((0, 1),), box, 1)
        with self.assertRaises(ValueError):
            replace(self.binding, prefix_digest='invalid')
        with self.assertRaises(ValueError):
            RationalInterval(2, 1)

    def test_interval_arithmetic_and_square(self):
        interval = RationalInterval(-2, 3)
        self.assertEqual(interval.square(), RationalInterval(0, 9))
        self.assertEqual(interval * interval, RationalInterval(-6, 9))
        self.assertEqual(interval.divide_positive(RationalInterval(2, 4)), RationalInterval(-1, Q(3, 2)))
        with self.assertRaises(ValueError):
            interval.divide_positive(RationalInterval(-1, 2))

    def test_signed_bounds_keep_sharp_offdiagonal_radius(self):
        box = signed_loewner_box(self.binding, ((3, 0), (0, 3)), 3, 1, 'signed')
        self.assertEqual(box.lower, ((0, -2), (-2, 0)))
        self.assertEqual(box.upper, ((4, 2), (2, 4)))
        # The error [[-1,2],[2,-1]] has eigenvalues -3 and 1.
        # Its offdiagonal entry attains the bound (3+1)/2 exactly.
        self.assertEqual(box.upper[0][1], Q(2))
        for negative, positive in ((-1, 0), (0, -1)):
            with self.assertRaises(ValueError):
                signed_loewner_box(self.binding, ((3,),), negative, positive, 'invalid')

    def test_service_portfolio_accepts_scalar_tie_without_replay(self):
        from src.aggregate_response_service import AggregateRepairService
        from src.linear_response import linear_record_moments
        from src.repair_service import JobSpec, Record, StageSpec
        from src.response_moments import ResponseBasis, record_moments
        from src.response_service_adapter import ResponseQuery, ResponseStageContract
        from src.service_telemetry import ServiceTelemetry

        stage = StageSpec('only', (), ((Q(1, 2),),), ((0, 1),), 1, 1)
        job = JobSpec((stage,), 'scalar-exact-feature', 'intrinsic-zero-anchor', 1)
        response = ResponseBasis('response', 1, 1, True)
        error = ResponseBasis('error', 1, 3, True)
        contract = ResponseStageContract(response, error, 0)
        def intrinsic(record, stage):
            anchor = linear_record_moments(response, record.record_id, record.content_digest, (((Q(0),),),))
            residual = record_moments(error, record.record_id, record.content_digest,
                                      (((Q(1),),), ((Q(0),),), ((Q(0),),)))
            return anchor, residual
        def target(record, stage, prefix):
            return ((Q(1),),)
        def query(ctx):
            return ResponseQuery(ctx.binding, (), Q(0), 'exact residual norm one')
        def build(policy):
            return AggregateRepairService(job, target, intrinsic, {'only': contract}, query,
                provider_id='scalar-proof', extractor_id='zero-anchor', verifier_policy=policy)
        baseline, portfolio = build('spectral'), build('spectral_or_interval')
        records = (Record('a', b'a'), Record('b', b'b'))
        original = baseline.fresh(records).state
        expected = baseline.fresh(records[1:]).state
        source = {record.record_id: record for record in records}.__getitem__
        baseline_result = baseline.repair(original, records[:1], source)
        telemetry = ServiceTelemetry()
        improved = portfolio.repair(original, records[:1], lambda _: self.fail('unexpected retained replay'),
                                     telemetry=telemetry)
        self.assertEqual(improved.state.canonical_bytes(), expected.canonical_bytes())
        self.assertEqual(baseline_result.state.canonical_bytes(), expected.canonical_bytes())
        self.assertEqual(improved.stages[0].route, 'interval_transport_certificate')
        self.assertEqual(improved.state.model[0].codes, ((Q(0),),))
        self.assertEqual(improved.ledger.count('retained_replay_evaluator_calls'), 0)
        self.assertEqual(baseline_result.ledger.count('retained_replay_evaluator_calls'), 1)
        self.assertEqual(improved.ledger.count('interval_candidate_factorization_calls'), 1)
        self.assertEqual(improved.ledger.count('interval_certificate_factorization_calls'), 1)
        self.assertEqual(telemetry.payload()['events']['certificate.nonpositive_lower_scale'], 1)


if __name__ == '__main__':
    unittest.main()
