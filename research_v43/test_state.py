"""Tiny complete-state fixtures; no empirical data or neural model execution.

The fixture feature generator is deliberately independent of stored descriptors.
It exercises the state oracle plumbing, not scientific feature reconstruction.
"""
from dataclasses import replace
from fractions import Fraction
import struct
import unittest

import numpy as np

from research_v35.exact_gram import GramBudget, accumulate, add_grams, dumps, subtract_gram
from research_v42.test_resource_plan import bind, fixture
from research_v43.state import (
    GramTrust, MAGIC, Record, StateLimits, build_state, compare_fresh,
    delete_state, sha, validate_state, verify_successor,
)
from src.compact_state import StageCodes
from src import fixed_factor_codec_v26 as compressed, fixed_lossless_codec_v29 as lossless
from src.run_store import canonical_json, strict_json


BUDGET = GramBudget(max_width=8, max_tokens=16, max_sources=8,
    max_product_terms=1024, max_serialized_bytes=2**20, max_memory_bytes=2**20)


def record(name, tokens):
    return Record(name, tuple(tokens), canonical_json(dict(dataset_id='fixture-corpus',
        dataset_revision='immutable-fixture-revision', source_file_sha256='1'*64,
        body_sha256=sha(name.encode()), tokenizer_sha256='2'*64, split='development')))


def codes(target, value=0.):
    return tuple(StageCodes.from_array(s.stage_id, np.full((s.rows, s.width), value),
        grid_axis='dyadic_row', bits=4, scale_values=(1.,)*s.rows) for s in target.stages)


def features(stage, source):
    # Tiny deterministic token-major factors rebuilt from tokens, not state.
    return np.array([[(t + j + stage.index) % 7 / 8 for j in range(stage.width)]
                     for t in source.tokens], dtype=np.float64)


def artifacts(target, records, representation):
    sources, grams, trust = {}, {}, {}
    for stage in target.stages:
        gram_mode = representation == 'exact_gram' or (
            representation == 'hybrid_gram' and stage.width <= 768)
        if gram_mode:
            pooled = None
            for source in sorted(records, key=lambda r: r.record_id):
                contribution = accumulate(features(stage, source).T.copy(),
                    source_id=source.record_id,
                    normalization=Fraction(*stage.normalization), budget=BUDGET)
                pooled = contribution if pooled is None else add_grams(pooled, contribution, budget=BUDGET)
            if pooled is None:
                # Obtain the canonical empty algebra result through trusted
                # construction/subtraction, never a parsed-only PSD assertion.
                seed = accumulate(np.zeros((stage.width, 1)), source_id='empty-seed',
                    normalization=Fraction(*stage.normalization), budget=BUDGET)
                pooled = subtract_gram(seed, seed, budget=BUDGET)
            blob = dumps(pooled, budget=BUDGET)
            grams[stage.stage_id] = blob
            trust[stage.stage_id] = GramTrust(sha(blob), pooled.sources)
        else:
            codec = compressed if representation == 'compressed40' else lossless
            for source in records:
                kwargs = dict(target_sha256=sha(target.fixed_payload),
                    anchor_target_sha256=sha(target.anchor_payload), record_id=source.record_id,
                    token_sha256=source.token_sha256, stage_id=stage.stage_id)
                if codec is compressed:
                    kwargs.update(bits=40, block_size=256)
                descriptor = codec.encode_factor(features(stage, source), **kwargs)
                sources[stage.stage_id, source.record_id] = codec.serialize(descriptor)
    return dict(source_payloads=sources, stage_grams=grams, gram_trust=trust, gram_budget=BUDGET)


def state(target, records, representation, stage_codes=None):
    result = artifacts(target, records, representation)
    return build_state(target, records, codes(target) if stage_codes is None else stage_codes,
        representation, **result), result['gram_trust']


def header_edit(blob, edit):
    length = struct.unpack_from('<Q', blob, 8)[0]
    header = strict_json(blob[16:16+length])
    edit(header)
    encoded = canonical_json(header)
    return MAGIC + struct.pack('<Q', len(encoded)) + encoded + blob[16+length:]


class StateTests(unittest.TestCase):
    def setUp(self):
        self.target = bind(*fixture(((2, 3), (1, 2)), original=8))
        self.records = (record('alpha', (1, 2)), record('beta', (3, 4)))

    def test_all_representations_roundtrip_and_source_order_canonical(self):
        for representation in ('lossless', 'compressed40', 'exact_gram', 'hybrid_gram'):
            with self.subTest(representation=representation):
                blob, trust = state(self.target, self.records, representation)
                reversed_blob, _ = state(self.target, tuple(reversed(self.records)), representation)
                self.assertEqual(blob, reversed_blob)
                view = validate_state(blob, expected_target=self.target,
                    expected_records=self.records, gram_trust=trust, gram_budget=BUDGET)
                self.assertEqual(view.records, self.records)
                self.assertEqual(view.stage_codes, codes(self.target))
                self.assertEqual(view.representation, representation)
                # Target bytes, packed model codes, tokens and provenance are
                # included, beyond just descriptor/Gram storage.
                self.assertIn(self.target.anchor_payload, blob)
                self.assertIn(self.target.fixed_payload, blob)
                self.assertIn(b'"tokens":[1,2]', blob)
                self.assertGreater(len(blob), sum(map(len, view.source_map().values())) +
                    sum(map(len, view.gram_map().values())))

    def test_complete_24_stages_and_actual_4bit_bytes(self):
        target = bind(*fixture(((1, 3),)*24, original=8))
        blob, _ = state(target, self.records, 'lossless')
        view = validate_state(blob)
        self.assertEqual(len(view.stage_codes), 24)
        self.assertEqual([len(c.packed_indices) for c in view.stage_codes], [2]*24)
        self.assertEqual([c.bits for c in view.stage_codes], [4]*24)
        for invalid in (codes(target)[:-1], tuple(reversed(codes(target)))):
            with self.assertRaises(ValueError):
                state(target, self.records, 'lossless', invalid)

    def test_hybrid_policy_uses_only_narrow_grams_and_wide_lossless(self):
        target = bind(*fixture(((1, 3), (1, 769)), original=8))
        blob, trust = state(target, self.records, 'hybrid_gram')
        view = validate_state(blob, gram_trust=trust, gram_budget=BUDGET)
        self.assertEqual(set(view.gram_map()), {'stage.0'})
        self.assertEqual(set(view.source_map()), {('stage.1', 'alpha'), ('stage.1', 'beta')})
        self.assertEqual(set(trust), {'stage.0'})
        with self.assertRaisesRegex(ValueError, 'source/stage payloads'):
            build_state(target, self.records, codes(target), 'hybrid_gram',
                source_payloads=view.source_map(), stage_grams={}, gram_budget=BUDGET)

    def test_successive_deletions_and_fresh_empty_reconstruction(self):
        for representation in ('lossless', 'compressed40', 'exact_gram', 'hybrid_gram'):
            with self.subTest(representation=representation):
                previous, previous_trust = state(self.target, self.records, representation)
                retained = self.records
                for removed in self.records:
                    retained = tuple(r for r in retained if r != removed)
                    fresh, fresh_trust = state(self.target, retained, representation)
                    supplied = artifacts(self.target, retained, representation)
                    repaired = delete_state(previous, iter([removed.record_id]), codes(self.target),
                        stage_grams=supplied['stage_grams'], previous_gram_trust=previous_trust,
                        gram_trust=supplied['gram_trust'], gram_budget=BUDGET)
                    result = verify_successor(previous, repaired, fresh, iter([removed.record_id]),
                        previous_gram_trust=previous_trust, candidate_gram_trust=supplied['gram_trust'],
                        fresh_gram_trust=fresh_trust, gram_budget=BUDGET)
                    self.assertTrue(result['actual_bytes_equal'])
                    self.assertTrue(result['exact_retained_membership_verified'])
                    self.assertFalse(result['independently_regenerated_features_verified_here'])
                    self.assertEqual(result['deleted_count'], 1)
                    self.assertEqual(result['retained_records'], len(retained))
                    view = validate_state(repaired, gram_trust=supplied['gram_trust'], gram_budget=BUDGET)
                    self.assertEqual(view.target.original_tokens, 8)
                    self.assertTrue(all(key[1] != removed.record_id for key in view.source_map()))
                    previous, previous_trust = repaired, supplied['gram_trust']

    def test_delete_order_reaches_same_canonical_state(self):
        first = self.records + (record('gamma', (5,)),)
        original, _ = state(self.target, first, 'lossless')
        direct = delete_state(original, ('alpha', 'beta'), codes(self.target))
        step = delete_state(original, ('beta',), codes(self.target))
        stepped = delete_state(step, ('alpha',), codes(self.target))
        fresh, _ = state(self.target, first[2:], 'lossless')
        self.assertEqual(direct, stepped)
        self.assertTrue(compare_fresh(stepped, fresh)['actual_bytes_equal'])

    def test_absent_duplicate_and_incomplete_deletions_rejected(self):
        previous, _ = state(self.target, self.records, 'lossless')
        for ids in (('absent',), ('alpha', 'alpha')):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                delete_state(previous, ids, codes(self.target))
        with self.assertRaisesRegex(ValueError, 'membership'):
            verify_successor(previous, previous, previous, ('alpha',))

    def test_extra_or_missing_source_payloads_rejected(self):
        prepared = artifacts(self.target, self.records, 'lossless')
        for key, mode in ((('stage.0', 'alpha'), 'remove'), (('stage.0', 'deleted'), 'add')):
            changed = dict(prepared['source_payloads'])
            changed.pop(key) if mode == 'remove' else changed.update({key: next(iter(changed.values()))})
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'source/stage payloads'):
                build_state(self.target, self.records, codes(self.target), 'lossless', source_payloads=changed)

    def test_descriptor_token_target_stage_and_record_provenance_checked(self):
        baseline = artifacts(self.target, self.records, 'lossless')['source_payloads']
        source = self.records[0]
        stage = self.target.stages[0]
        kwargs = dict(target_sha256=sha(self.target.fixed_payload),
            anchor_target_sha256=sha(self.target.anchor_payload), record_id=source.record_id,
            token_sha256=source.token_sha256, stage_id=stage.stage_id)
        for key in kwargs:
            changed = dict(kwargs)
            changed[key] = '0'*64 if key.endswith('sha256') else 'different'
            blob = lossless.serialize(lossless.encode_factor(features(stage, source), **changed))
            payloads = dict(baseline, **{})
            payloads[stage.stage_id, source.record_id] = blob
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'identity, provenance'):
                build_state(self.target, self.records, codes(self.target), 'lossless', source_payloads=payloads)

    def test_retained_record_provenance_cannot_change_in_successor(self):
        previous, _ = state(self.target, self.records, 'lossless')
        changed = strict_json(self.records[1].provenance)
        changed['dataset_revision'] = 'different-revision'
        altered = (replace(self.records[1], provenance=canonical_json(changed)),)
        candidate, _ = state(self.target, altered, 'lossless')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            verify_successor(previous, candidate, candidate, ('alpha',))

    def test_actual_code_bytes_and_artifacts_compared_not_hash_list_only(self):
        fresh, _ = state(self.target, self.records, 'lossless')
        changed, _ = state(self.target, self.records, 'lossless', codes(self.target, 1.))
        # Both envelopes are well formed and fully committed. The oracle must
        # still compare actual bytes rather than accept each local hash table.
        validate_state(changed)
        with self.assertRaisesRegex(ValueError, 'canonical successor bytes differ'):
            compare_fresh(changed, fresh)
        prepared = artifacts(self.target, self.records, 'lossless')
        source, stage = self.records[0], self.target.stages[0]
        altered = lossless.encode_factor(features(stage, source) + 1.,
            target_sha256=sha(self.target.fixed_payload), anchor_target_sha256=sha(self.target.anchor_payload),
            record_id=source.record_id, token_sha256=source.token_sha256, stage_id=stage.stage_id)
        prepared['source_payloads'][stage.stage_id, source.record_id] = lossless.serialize(altered)
        changed = build_state(self.target, self.records, codes(self.target), 'lossless', **prepared)
        with self.assertRaisesRegex(ValueError, 'descriptors changed'):
            verify_successor(fresh, changed, changed, ())

    def test_gram_external_trust_and_source_membership_required(self):
        blob, trust = state(self.target, self.records, 'exact_gram')
        with self.assertRaisesRegex(ValueError, 'external'):
            validate_state(blob, gram_budget=BUDGET)
        with self.assertRaises(TypeError):
            validate_state(blob, gram_trust=trust)
        altered = dict(trust)
        altered['stage.0'] = replace(altered['stage.0'], sha256='0'*64)
        with self.assertRaises(ValueError):
            validate_state(blob, gram_trust=altered, gram_budget=BUDGET)
        prepared = artifacts(self.target, self.records[:1], 'exact_gram')
        with self.assertRaisesRegex(ValueError, 'Gram source membership'):
            build_state(self.target, self.records, codes(self.target), 'exact_gram', **prepared)
        altered = dict(trust)
        altered['stage.0'] = replace(altered['stage.0'], sources=())
        with self.assertRaises(ValueError):
            validate_state(blob, gram_trust=altered, gram_budget=BUDGET)

    def test_bound_grid_bits_target_and_original_normalization_checked(self):
        prepared = artifacts(self.target, self.records, 'lossless')
        changed = list(codes(self.target))
        changed[0] = replace(changed[0], scale_values=(2.,)*changed[0].rows)
        with self.assertRaisesRegex(ValueError, 'bound row scales'):
            build_state(self.target, self.records, changed, 'lossless', **prepared)
        changed[0] = StageCodes.from_array('stage.0', np.zeros((2, 3)),
            grid_axis='dyadic_row', bits=3, scale_values=(1., 1.))
        with self.assertRaisesRegex(ValueError, 'bound row scales'):
            build_state(self.target, self.records, changed, 'lossless', **prepared)
        blob, _ = state(self.target, self.records, 'lossless')
        other = bind(*fixture(((2, 3), (1, 2)), original=9))
        with self.assertRaisesRegex(ValueError, 'target manifests'):
            validate_state(blob, expected_target=other)

    def test_tamper_trailing_noncanonical_and_missing_stage_rejected(self):
        blob, _ = state(self.target, self.records, 'lossless')
        for tampered in (blob[:-1] + bytes([blob[-1] ^ 1]), blob+b'extra', blob[:15],
                         header_edit(blob, lambda h: h['records'][0].update(token_sha256='0'*64)),
                         header_edit(blob, lambda h: h['records'].reverse()),
                         header_edit(blob, lambda h: h['stages'].pop())):
            with self.subTest(length=len(tampered)), self.assertRaises(ValueError):
                validate_state(tampered)
        length = struct.unpack_from('<Q', blob, 8)[0]
        noncanonical = MAGIC + struct.pack('<Q', length+1) + blob[16:16+length] + b' ' + blob[16+length:]
        with self.assertRaisesRegex(ValueError, 'canonical'):
            validate_state(noncanonical)

    def test_limits_reject_oversize_headers_records_tokens_and_state(self):
        blob, _ = state(self.target, self.records, 'lossless')
        for limits in (StateLimits(max_bytes=len(blob)-1), StateLimits(max_header_bytes=10),
                       StateLimits(max_records=1), StateLimits(max_tokens=3), StateLimits(max_stages=1)):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                validate_state(blob, limits=limits)
        excessive = (record('too-many', tuple(range(9))),)
        with self.assertRaisesRegex(ValueError, 'original normalization'):
            build_state(self.target, excessive, codes(self.target), 'lossless')

    def test_record_and_representation_contract(self):
        with self.assertRaises(ValueError):
            Record('a', (), self.records[0].provenance)
        with self.assertRaises(ValueError):
            Record('a', (True,), self.records[0].provenance)
        with self.assertRaises(ValueError):
            Record('a', (1,), b'{}')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            build_state(self.target, self.records*2, codes(self.target), 'lossless')
        with self.assertRaisesRegex(ValueError, 'unsupported state representation'):
            build_state(self.target, (), codes(self.target), 'unspecified')
        first, _ = state(self.target, self.records, 'lossless')
        other, _ = state(self.target, self.records, 'compressed40')
        with self.assertRaisesRegex(ValueError, 'same representation'):
            compare_fresh(first, other)


if __name__ == '__main__':
    unittest.main()
