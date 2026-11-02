"""Tiny provider/service integration fixtures; no real-model experiment.

FixtureService uses independent synthetic features and live canonical codecs
for worker tests. ServiceTests also exercise the actual finite teacher provider
and a tiny certified calibration in the pinned Linux runtime only.
"""
from dataclasses import replace
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from research_v50.neighbors import enabled
from research_v59 import anchor
from research_v59.test_anchor import context, RECORDS, direct_feature_words
from research_v61 import service
from research_v61.target import BoundTarget, build_service_target
from research_v61.state import build_state, delete_state, validate_state, verify_successor
from research_v61.test_state import BUDGET, artifacts, bind, codes, features, fixture, record
from src.run_store import canonical_json, digest


class FixtureService:
    """Synthetic features/codes; no decoder, checkpoint load, or solver."""
    events = []

    def __init__(self, checkpoint, normalization, record_provenance, mark=lambda *a, **k: None):
        self.bound = bind(*fixture(((2, 3), (1, 2)), original=normalization))
        self.target = SimpleNamespace(stages=self.bound.stages, digest=digest(self.bound.fixed_payload))
        self.normalization = normalization
        self.record_provenance = record_provenance
        self.provenance = canonical_json({'fixture': True})
        self.load_ns = 0
        self.gram_budget = BUDGET
        self.mark = mark
        mark('context_ready', elapsed_ns=123, target_sha256=self.target.digest)

    def records(self, rows):
        return tuple(record(row['id'], row['tokens']) for row in rows)

    def admit(self, rows, representation):
        self.events.append(('admit', tuple(r['id'] for r in rows), representation))
        return {'admitted': True}

    def extract(self, rows, telemetry):
        self.events.append(('extract', tuple(r['id'] for r in rows)))
        telemetry['neural_stage_record_pairs'] += len(rows)*len(self.bound.stages)
        return {(stage.stage_id, source.record_id): features(stage, source)
                for stage in self.bound.stages for source in self.records(rows)}

    def solve(self, rows, representation, payloads, grams, trust, telemetry, **kwargs):
        self.events.append(('solve', tuple(r['id'] for r in rows), representation))
        self.mark('stage_certified', elapsed_ns=456, stage_id='fixture-stage')
        return codes(self.bound), {'admitted': True}

    def prepare_payloads(self, rows, values, representation, telemetry):
        self.events.append(('encode', tuple(r['id'] for r in rows), representation))
        result = artifacts(self.bound, self.records(rows), representation)
        return result['source_payloads'], result['stage_grams'], result['gram_trust']

    def serialize(self, rows, stage_codes, representation, payloads, grams, trust, telemetry):
        return build_state(self.bound, self.records(rows), stage_codes, representation,
            source_payloads=payloads, stage_grams=grams, gram_trust=trust, gram_budget=BUDGET)


def tiny_service():
    """Actual service methods and provider around a software-only decoder."""
    decoder, base = context()
    instance = object.__new__(service.Service)
    instance.decoder, instance.base = decoder, base
    instance.target = build_service_target(decoder, base)
    instance.bound = BoundTarget(canonical_json(base.payload()), canonical_json(instance.target.payload()))
    instance.normalization = 4
    instance.record_provenance = {r['id']: json.loads(record(r['id'], r['tokens']).provenance) for r in RECORDS}
    instance.mark = lambda *a, **k: None
    instance.gram_budget = BUDGET
    instance.policy = service.dispatch.ResourcePolicy()
    return instance


def fixture_answer(spec, weights, blocks, **kwargs):
    # Consume and check real blocks; numerical certification is tested separately.
    parts = list(blocks)
    assert sum(lo.shape[1] for lo, hi in parts) == kwargs['total_tokens']
    assert all(lo.shape[0] == spec.width and lo.shape == hi.shape for lo, hi in parts)
    return SimpleNamespace(codes=np.zeros_like(weights), route='fixture',
        admission={'fixture': True}, solver_result={'fixture_only': True})


class ServiceTests(unittest.TestCase):
    def test_execution_provenance_binds_service_original_teacher_and_calibration(self):
        instance = tiny_service()
        checkpoint = {'files_sha256': {'fixture.safetensors': '1'*64}}
        raw = service.execution_provenance(instance.decoder, instance.target, checkpoint)
        value = json.loads(raw)
        self.assertEqual(raw, canonical_json(value))
        self.assertEqual(value['schema'], 'full-precision-source-execution-binding-v61')
        self.assertEqual(value['target_sha256'], instance.target.digest)
        self.assertEqual(value['anchor_target_sha256'], instance.base.digest)
        self.assertEqual(value['calibration_target_sha256'], instance.target.calibration_target.digest)
        self.assertEqual(value['provider_sha256'], service.provider_binding())
        self.assertEqual(value['teacher_stages'], instance.target.calibration_target.payload()['teacher_stages'])
        self.assertEqual(value['decoder'], instance.decoder.kernel_manifest)
        self.assertEqual(value['implementation'], instance.decoder.implementation_manifest)
        self.assertEqual(value['checkpoint'], checkpoint)
        self.assertNotIn('anchor_sha256', value)
        self.assertNotIn('preparer_sha256', value)

    def test_records_use_registered_dataset_provenance(self):
        instance = tiny_service()
        self.assertEqual(instance.records(RECORDS), tuple(record(r['id'], r['tokens']) for r in RECORDS))
        instance.record_provenance['a'] = {'schema': 'execution-only'}
        with self.assertRaises(ValueError):
            instance.records(RECORDS)

    def test_extract_traverses_once_per_source_and_matches_direct_teacher(self):
        instance = tiny_service()
        original = service.iter_source_features
        with patch.object(service, 'iter_source_features', wraps=original) as calls:
            timing = service.telemetry()
            values = instance.extract(list(reversed(RECORDS)), timing)
        self.assertEqual(calls.call_count, 2)
        self.assertEqual([call.args[2]['id'] for call in calls.call_args_list], ['a', 'b'])
        self.assertEqual(timing['neural_stage_record_pairs'], len(instance.target.stages)*2)
        self.assertGreater(timing['source_extraction_ns'], 0)
        for stage in instance.target.stages:
            for row in RECORDS:
                expected = direct_feature_words(instance.decoder, stage.stage_id, row['tokens']).T.copy()
                self.assertEqual(values[stage.stage_id, row['id']].tobytes(), expected.tobytes())

    def test_extraction_refuses_whole_request_before_any_feature_work(self):
        for policy in (replace(service.dispatch.ResourcePolicy(), max_stage_work_units=1),
                       replace(service.dispatch.ResourcePolicy(), max_request_work_units=1)):
            instance = tiny_service()
            instance.policy = policy
            timing = service.telemetry()
            with patch.object(service, 'iter_source_features') as opening:
                with self.assertRaises(ValueError):
                    instance.extract(RECORDS, timing)
                opening.assert_not_called()
            self.assertEqual(timing['neural_stage_record_pairs'], 0)
            self.assertGreater(timing['source_extraction_ns'], 0)
        instance = tiny_service()
        for rows in ([], [RECORDS[0], RECORDS[0]]):
            with patch.object(service, 'iter_source_features') as opening:
                with self.assertRaises(ValueError): instance.extract(rows, service.telemetry())
                opening.assert_not_called()

    def test_failed_extraction_counts_partial_advances_and_closes_stream(self):
        instance = tiny_service()
        closed = []
        def broken(decoder, target, row):
            try:
                yield target.stages[0].stage_id, np.zeros((len(row['tokens']), target.stages[0].width))
                raise ArithmeticError('fixture feature failure')
            finally:
                closed.append(row['id'])
        timing = service.telemetry()
        with patch.object(service, 'iter_source_features', side_effect=broken):
            with self.assertRaises(ArithmeticError): instance.extract(RECORDS, timing)
        self.assertEqual(closed, ['a'])
        self.assertEqual(timing['neural_stage_record_pairs'], 1)
        self.assertGreater(timing['source_extraction_ns'], 0)

    def test_lossless_signed_words_and_compressed_actual_containment(self):
        instance = tiny_service()
        stage, row = instance.target.stages[0], RECORDS[0]
        values = np.array([[0., -0.], [float.fromhex('0x1.0000000000001p0'), -3.125]])
        raw = instance.descriptor(stage, row, values, 'lossless')
        exact = service.lossless.parse(raw, expected_sha256=digest(raw))
        self.assertEqual(values.tobytes(), exact.array().tobytes())
        raw = instance.descriptor(stage, row, values, 'compressed48')
        desc = service.compressed.parse(raw, expected_sha256=digest(raw))
        self.assertEqual(desc.source_sha256, digest(values.astype('<f8').tobytes()))
        self.assertTrue(np.all(desc.box().lower <= values) and np.all(values <= desc.box().upper))

    def test_complete_compressed_admission_reserves_every_exact_fallback(self):
        instance = tiny_service()
        report = instance.admit(RECORDS, 'compressed48')
        expected = 0
        for stage in instance.target.stages:
            spec = service.dispatch.StageSpec.from_stage(stage, target_sha256=instance.target.digest)
            for kind in ('box', 'point'):
                expected += service.dispatch.assess_stage(spec, total_tokens=4, kind=kind,
                    block_tokens=2, max_blocks=2, policy=instance.policy,
                    resident_bytes=4*2**30)['work_units']
        self.assertEqual(report['reserved_work_units'], expected)
        self.assertEqual(len(report['stages']), len(instance.target.stages))
        self.assertEqual(report['maximum_fallback_neural_stage_record_pairs'], 2*len(instance.target.stages))
        instance.policy = replace(instance.policy, max_request_work_units=expected-1)
        with self.assertRaisesRegex(ValueError, 'structural work'):
            instance.admit(RECORDS, 'compressed48')

    def test_multiple_compressed_refusals_replay_sources_only_once(self):
        instance = tiny_service()
        values = instance.extract(RECORDS, service.telemetry())
        payloads, grams, trust = instance.prepare_payloads(RECORDS, values, 'compressed48', service.telemetry())
        kinds = []
        def refuse_box(spec, weights, blocks, **kwargs):
            kinds.append(kwargs['kind'])
            if kwargs['kind'] == 'box':
                raise service.dispatch.DispatchRefused('fixture box unresolved', {})
            return fixture_answer(spec, weights, blocks, **kwargs)
        timing = service.telemetry()
        with patch.object(service.dispatch, 'solve_blocks', side_effect=refuse_box), \
             patch.object(instance, 'extract', wraps=instance.extract) as replay:
            output, _ = instance.solve(RECORDS, 'compressed48', payloads, grams, trust, timing)
        self.assertEqual(replay.call_count, 1)
        self.assertEqual(kinds, ['box', 'point']*len(instance.target.stages))
        self.assertEqual(timing['neural_stage_record_pairs'], 2*len(instance.target.stages))
        self.assertTrue(all(row['fallback'] and row['certificate_refusal'] for row in timing['stages']))
        self.assertEqual(len(output), len(instance.target.stages))
        for code, stage in zip(output, instance.target.stages):
            self.assertEqual(code.scale_values, stage.scale_values)

    def test_replay_must_match_every_committed_source_before_point_fallback(self):
        instance = tiny_service()
        values = instance.extract(RECORDS, service.telemetry())
        payloads, grams, trust = instance.prepare_payloads(RECORDS, values, 'compressed48', service.telemetry())
        wrong = {k: v.copy() for k, v in values.items()}
        last = next(reversed(wrong))
        wrong[last][0, 0] = np.nextafter(wrong[last][0, 0], np.inf)
        kinds = []
        def refuse(spec, weights, blocks, **kwargs):
            kinds.append(kwargs['kind'])
            raise service.dispatch.DispatchRefused('fixture box unresolved', {})
        with patch.object(instance, 'extract', return_value=wrong), \
             patch.object(service.dispatch, 'solve_blocks', side_effect=refuse):
            with self.assertRaisesRegex(ValueError, 'source identity'):
                instance.solve(RECORDS, 'compressed48', payloads, grams, trust, service.telemetry())
        self.assertEqual(kinds, ['box'])

    def test_real_tiny_codes_equal_v59_and_successor_equals_fresh_all_representations(self):
        instance = tiny_service()
        rows = RECORDS[1:]
        original_values = instance.extract(RECORDS, service.telemetry())
        retained_values = instance.extract(rows, service.telemetry())
        with enabled():
            v59, _ = anchor.calibrate(instance.decoder, instance.base, rows)
            actual, _ = instance.solve(rows, 'lossless', {}, {}, {}, service.telemetry(), direct_values=retained_values)
        self.assertEqual(actual, v59)
        self.assertEqual(tuple(c.stage_id for c in actual), instance.decoder.stage_ids)
        # Real target/grid/model bytes with all actual representation codecs.
        # Original placeholder codes are explicitly irrelevant to source deletion.
        for representation in service.REPRESENTATIONS:
            pp, pg, pt = instance.prepare_payloads(RECORDS, original_values, representation, service.telemetry())
            rp, rg, rt = instance.prepare_payloads(rows, retained_values, representation, service.telemetry())
            old = instance.serialize(RECORDS, actual, representation, pp, pg, pt, service.telemetry())
            fresh = instance.serialize(rows, actual, representation, rp, rg, rt, service.telemetry())
            repaired = delete_state(old, ('a',), actual, stage_grams=rg,
                previous_gram_trust=pt, gram_trust=rt, gram_budget=BUDGET)
            verified = verify_successor(old, repaired, fresh, ('a',), previous_gram_trust=pt,
                candidate_gram_trust=rt, fresh_gram_trust=rt, gram_budget=BUDGET)
            self.assertTrue(verified['actual_bytes_equal'])
            view = validate_state(repaired, expected_target=instance.bound,
                expected_records=instance.records(rows), gram_trust=rt, gram_budget=BUDGET)
            self.assertEqual(view.stage_codes, v59)
            self.assertEqual(view.target.original_tokens, 4)


if __name__ == '__main__':
    unittest.main()
