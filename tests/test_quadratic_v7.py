"""Quadratic storage, exact proposals, and complete deletion correctness."""
from dataclasses import replace
from fractions import Fraction as Q
import json
import unittest

from src.aggregate_response_service import AggregateRepairService, AggregateState, StateParseLimits
from src.repair_service import CertifiedPrefix, StageOutput, _Work, _gram, _is_psd
from src.response_moments import RecordMoments, ResponseIndex, record_moments
from tests import test_aggregate_response_service as fixtures


class QuadraticControlTests(unittest.TestCase):
    def fixture(self, *, error_floor=Q(0), query_unknown=False):
        original, calls, contexts, control = fixtures.AggregateServiceTests().build(query_unknown=query_unknown)
        def extract(record, stage):
            # Fixtures provide an exact affine response, not a research dataset.
            calls.append((record.record_id, stage.stage_id))
            if record.record_id in control['missing']:
                return None
            value = json.loads(record.payload)
            base = ((Q(value[0]) + int(control['corrupt']),), (Q(value[1]),))
            jets = (base,) if stage.stage_id == 'first' else (base, ((Q(1),), (Q(0),)))
            contract = original.contracts[stage.stage_id]
            response = record_moments(contract.response_basis, record.record_id, record.content_digest, jets)
            descriptors = (((error_floor,),),) + (((Q(0),),),) * (contract.error_basis.terms - 1)
            error = record_moments(contract.error_basis, record.record_id, record.content_digest, descriptors)
            return response, error
        def target(record, stage, prefix):
            value = original.evaluator(record, stage, prefix)
            return ((value[0][0] + error_floor,), value[1])
        service = AggregateRepairService(original.job, target, extract, original.contracts, original.query,
                    provider_id=original.provider_id, extractor_id=original.extractor_id,
                    reference_weights={s.stage_id: ((Q(0), Q(0)),) for s in original.job.stages},
                    response_tier='quadratic')
        return service, original, fixtures.AggregateServiceTests().records(), calls, contexts, control

    def test_quadratic_proposal_contains_actual_tail_and_retains_oriented_cross_terms(self):
        service, linear, records, _, contexts, _ = self.fixture()
        state = service.fresh(records[:2]).state
        stage = service.job.stages[1]
        prefix = service._engine._prefix(stage, state.model)
        self.assertEqual(prefix.as_mapping()['first'][0][1], 1)
        raw, bounds = service._proposal(state.groups[0], state.groups[0].stages[1], stage, prefix, _Work())
        actuals = [_gram(service.evaluator(r, stage, prefix), _Work()) for r in records[:2]]
        expected = tuple(tuple(sum((x[i][j] for x in actuals), Q(0)) for j in range(2)) for i in range(2))
        self.assertEqual(raw, expected)
        self.assertEqual(bounds, (0, 0))
        # C01 is oriented and nonsymmetric. Its transpose is necessary.
        cross = state.groups[0].stages[1].response.cross_moments[1]
        self.assertNotEqual(cross[0][1], cross[1][0])
        old_linear = linear.fresh(records[:2]).state
        linear_raw, linear_bounds = linear._proposal(old_linear.groups[0], old_linear.groups[0].stages[1],
                                                     stage, prefix, _Work())
        self.assertNotEqual(raw, linear_raw)
        self.assertGreater(linear_bounds[0], 0)
        self.assertTrue(all(ctx.response.records == ctx.error.records == () for ctx in contexts))

    def test_repeated_reordered_and_complete_deletion_match_fresh_bytes(self):
        service, _, records, _, _, _ = self.fixture()
        old = service.fresh(records).state
        source = {r.record_id: r for r in records}.__getitem__
        first = service.repair(old, records[:1], source).state
        sequential = service.repair(first, records[1:2], source).state
        reverse = service.repair(service.repair(old, records[1:2], source).state, records[:1], source).state
        combined = service.repair(old, records[:2], source).state
        fresh = service.fresh(records[2:]).state
        self.assertEqual({x.canonical_bytes() for x in (sequential, reverse, combined, fresh)}, {fresh.canonical_bytes()})
        empty = service.repair(sequential, records[2:], lambda _: self.fail('empty source read')).state
        self.assertEqual(empty.canonical_bytes(), service.fresh(()).state.canonical_bytes())
        self.assertEqual(empty.response_tier, 'quadratic')
        self.assertEqual(empty.stored_aggregate_rational_count, 0)
        self.assertEqual(service.repair(empty, (), lambda _: self.fail('empty source read')).state, empty)
        with self.assertRaisesRegex(ValueError, 'not retained'):
            service.repair(first, records[:1], source)

    def test_storage_and_extraction_costs_bind_quadratic_tier(self):
        service, linear, records, _, _, _ = self.fixture()
        result = service.fresh(records[:2])
        compact = linear.fresh(records[:2])
        self.assertEqual(service.target_manifest_digest, linear.target_manifest_digest)
        self.assertNotEqual(service.manifest_digest, linear.manifest_digest)
        self.assertEqual(result.state.model, compact.state.model)
        self.assertEqual(result.state.stored_aggregate_rational_count, (4 + 6) + (12 + 10))
        self.assertEqual(compact.state.stored_aggregate_rational_count, (4 + 6) + (9 + 10))
        self.assertEqual(result.ledger.count('response_moment_product_terms'), 2 * (4 + 12))
        self.assertEqual(result.ledger.count('error_moment_product_terms'), 2 * (6 + 10))
        self.assertGreater(result.ledger.count('contribution_digest_bytes'), 0)
        self.assertGreater(result.ledger.count('canonical_serialized_bytes'), 0)
        for group in result.state.groups:
            for stage in group.stages:
                self.assertIsInstance(stage.response, ResponseIndex)
                self.assertEqual(stage.response.records, ())

    def test_state_parser_round_trip_tier_confusion_and_resource_limit(self):
        service, linear, records, _, _, _ = self.fixture()
        state = service.fresh(records).state
        payload = state.canonical_bytes()
        self.assertEqual(service.load_state(payload, expected_digest=state.digest), state)
        self.assertEqual(AggregateState.from_canonical_bytes(payload).response_tier, 'quadratic')
        with self.assertRaisesRegex(ValueError, 'different service manifest'):
            linear.load_state(payload)
        with self.assertRaisesRegex(ValueError, 'different service manifest'):
            service.repair(replace(state, response_tier='linear'), (), lambda _: None)
        with self.assertRaisesRegex(ValueError, 'max_rationals'):
            service.load_state(payload, limits=StateParseLimits(max_rationals=10))
        altered = json.loads(payload)
        altered['schema'] = 'aggregate-linear-service-v1'
        encoded = json.dumps(altered, sort_keys=True, separators=(',', ':')).encode()
        with self.assertRaises(ValueError):
            AggregateState.from_canonical_bytes(encoded)
        with self.assertRaisesRegex(TypeError, "tier's response moments"):
            AggregateRepairService(linear.job, linear.evaluator, linear.intrinsic_moments,
                linear.contracts, linear.query, provider_id='p', extractor_id='e', response_tier='quadratic').fresh(records)

    def test_nonzero_finite_error_bounds_actual_quadratic_gram_difference(self):
        service, _, records, _, _, _ = self.fixture(error_floor=Q(1, 10))
        state = service.fresh(records[:2]).state
        stage = service.job.stages[1]
        prefix = CertifiedPrefix(service.job.manifest_digest, (StageOutput('first', ((0, 1),)),))
        raw, bounds = service._proposal(state.groups[0], state.groups[0].stages[1], stage, prefix, _Work())
        actuals = [_gram(service.evaluator(r, stage, prefix), _Work()) for r in records[:2]]
        actual = tuple(tuple(sum((x[i][j] for x in actuals), Q(0)) for j in range(2)) for i in range(2))
        self.assertNotEqual(raw, actual)
        self.assertGreater(bounds[0], 0)
        self.assertEqual(bounds[0], bounds[1])
        for sign in (-1, 1):
            self.assertTrue(_is_psd(tuple(tuple(sign * (actual[i][j] - raw[i][j])
                + (bounds[0] if i == j else 0) for j in range(2)) for i in range(2))))
        repaired = service.repair(state, records[:1], {r.record_id: r for r in records}.__getitem__)
        self.assertEqual(repaired.state.canonical_bytes(), service.fresh(records[1:2]).state.canonical_bytes())

    def test_controls_and_model_free_index_have_same_complete_target(self):
        service, _, records, _, _, _ = self.fixture()
        old = service.fresh(records).state
        source = {r.record_id: r for r in records}.__getitem__
        expected = service.fresh(records[1:]).state.canonical_bytes()
        index = service.prepare_index(old, records[:1]).index
        self.assertEqual(index.response_tier, 'quadratic')
        self.assertNotIn(b'"model"', index.canonical_bytes())
        for mode in ('certified', 'identity_only', 'fixed_reference', 'full_replay'):
            repaired = service.repair(old, records[:1], source, mode=mode)
            fresh = service.indexed_fresh(index, source, mode=mode)
            self.assertEqual(repaired.state.canonical_bytes(), expected)
            self.assertEqual(fresh.state.canonical_bytes(), expected)
            for key in ('retained_replay_evaluator_calls', 'certificate_factorization_calls', 'quadratic_bound_calls'):
                self.assertEqual(repaired.ledger.count(key), fresh.ledger.count(key))

    def test_interval_portfolio_preserves_existing_acceptance_and_state_identity(self):
        service, _, records, _, _, _ = self.fixture()
        portfolio = AggregateRepairService(service.job, service.evaluator, service.intrinsic_moments,
            service.contracts, service.query, provider_id=service.provider_id, extractor_id=service.extractor_id,
            reference_weights=service.reference_weights, response_tier='quadratic', verifier_policy='spectral_or_interval')
        self.assertEqual(portfolio.manifest_digest, service.manifest_digest)
        old = service.fresh(records).state
        source = {r.record_id: r for r in records}.__getitem__
        before = service.repair(old, records[:1], source)
        after = portfolio.repair(old, records[:1], source)
        self.assertEqual(after.state.canonical_bytes(), before.state.canonical_bytes())
        self.assertEqual(after.stages, before.stages)
        self.assertEqual(after.ledger.count('interval_certificate_factorization_calls'), 0)
        self.assertEqual(after.ledger.count('certificate_factorization_calls'), before.ledger.count('certificate_factorization_calls'))
        with self.assertRaisesRegex(ValueError, 'verifier policy'):
            AggregateRepairService(service.job, service.evaluator, service.intrinsic_moments,
                service.contracts, service.query, provider_id='p', extractor_id='e', verifier_policy=[])

    def test_certified_provider_and_box_factory_quadratic_services_match_direct(self):
        from src.certified_transformer import CertifiedDecoder
        from src.chart_construction import ChartRecipe, build_chart, make_service
        from src.target_manifest import TargetRecipe, build_target
        from src.repair_service import Record
        from tests.test_certified_transformer import small_decoder, grids
        from tests.test_checkpoint_adapter import checkpoint_fixture
        decoder, chart = small_decoder()
        quadratic = decoder.make_repair_service(grids(decoder), chart, group_count=1,
                                                response_tier='quadratic')
        records = [Record('a', decoder.record_payload((0, 1))), Record('b', decoder.record_payload((1, 0)))]
        old = quadratic.fresh(records).state
        repaired = quadratic.repair(old, records[:1], {r.record_id: r for r in records}.__getitem__)
        self.assertEqual(repaired.state.canonical_bytes(), quadratic.fresh(records[1:]).state.canonical_bytes())
        self.assertTrue(all(isinstance(s.response, ResponseIndex) for g in old.groups for s in g.stages))
        _, _, base = checkpoint_fixture()
        decoder = CertifiedDecoder(base)
        target = build_target(decoder, TargetRecipe(6, group_count=1))
        construction = build_chart(decoder, target, ChartRecipe(mode='grid-box', response_tier='quadratic'))
        box = make_service(decoder, target, construction)
        record = Record('box', decoder.record_payload((0, 1)))
        original = box.fresh([record]).state
        empty = box.repair(original, [record], lambda _: self.fail('empty read')).state
        self.assertEqual(empty.canonical_bytes(), box.fresh(()).state.canonical_bytes())
        self.assertEqual(original.response_tier, 'quadratic')
        self.assertEqual(original.stored_aggregate_rational_count, construction.preview.aggregate_rationals_all_groups)

    def test_unavailable_replay_and_bad_regeneration_preserve_commit(self):
        service, _, records, _, _, control = self.fixture(query_unknown=True)
        state = service.fresh(records).state
        before = state.canonical_bytes()
        source = {r.record_id: r for r in records}.__getitem__
        result = service.repair(state, records[:1], source)
        self.assertEqual(result.ledger.count('retained_replay_evaluator_calls'), 4)
        self.assertEqual(result.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())
        control['corrupt'] = True
        with self.assertRaisesRegex(ValueError, 'regenerated contribution'):
            service.repair(state, records[:1], source)
        self.assertEqual(state.canonical_bytes(), before)


if __name__ == '__main__':
    unittest.main()
