"""Version 26 state software fixtures. These are not empirical datasets."""
from dataclasses import replace
import hashlib
import json
import struct
import unittest
from unittest.mock import patch

import numpy as np

from src.compact_state import CompactState, StageCodes, _json, serialize as encode_model
from src.fixed_compressed_state_v26 import (
    CompressedFactorLeaf, CompressedFactorState, LoadLimits, MAGIC,
    from_factor_state, serialize, parse,
)
from src.fixed_factor_codec_v26 import codec_binding, serialize as encode_descriptor
from src.fixed_factor_state import FixedFactorState, FixedFactorLeaf, FactorBlock
from src.fixed_compressed_state import (
    from_factor_state as convert_v25, serialize as serialize_v25, parse as parse_v25,
)


def factor_state():
    stages = (
        StageCodes.from_array('stage.a', np.array([[0., 1., 2., 3.], [-4., -3., -2., -1.]]),
                             grid_axis='row', bits=3, scale_exponents=(0, 0)),
        StageCodes.from_array('stage.b', np.array([[0., 1.], [2., 3.], [-1., -2.]]),
                             grid_axis='row', bits=3, scale_exponents=(0, 0, 0)),
    )
    anchors = []
    for index, name in enumerate(('z', 'a', 'm')):
        blocks = tuple(FactorBlock.from_array(stage.stage_id,
            np.arange(2*stage.columns, dtype=np.float64).reshape(2, stage.columns)/7 + index/3)
            for stage in stages)
        anchors.append(FixedFactorLeaf(name, (index, index+1), 'b'*64, 'c'*64,
                                      'd'*64, 'e'*64, 'f'*64, blocks))
    return FixedFactorState('a'*64, 'b'*64, 'c'*64, 'd'*64, 'e'*64, 'f'*64, stages, tuple(anchors))


def rewrite_header(raw, update):
    length = struct.unpack_from('<Q', raw, 8)[0]
    header = json.loads(raw[16:16+length])
    update(header)
    encoded = _json(header)
    return MAGIC + struct.pack('<Q', len(encoded)) + encoded + raw[16+length:]


class FixedCompressedStateV26Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exact = factor_state()
        cls.state = from_factor_state(cls.exact, bits=40, block_size=3)

    def test_conversion_keeps_complete_model_and_contains_every_source(self):
        for bits in (16, 24, 32, 40, 48):
            state = from_factor_state(self.exact, bits=bits, block_size=3)
            self.assertEqual(state.record_ids, ('a', 'm', 'z'))
            self.assertEqual(state.stages, self.exact.stages)
            self.assertEqual(state.preparer_sha256, self.exact.preparer_sha256)
            self.assertEqual(state.codec_sha256, codec_binding())
            for exact, compressed in zip(self.exact.anchors, state.anchors):
                self.assertEqual(compressed.tokens, exact.tokens)
                for block, descriptor in zip(exact.blocks, compressed.descriptors):
                    self.assertTrue(descriptor.box().contains(block.array()))
                    self.assertEqual(descriptor.source_sha256, hashlib.sha256(block.binary64).hexdigest())
            raw = serialize(state)
            size = struct.unpack_from('<Q', raw, 8)[0]
            header = json.loads(raw[16:16+size])
            model = encode_model(CompactState(self.exact.target_sha256, self.exact.stages, ()))
            self.assertEqual(raw[16+size:16+size+header['model']['nbytes']], model)

    def test_canonical_roundtrip_fresh_subset_and_history_independence(self):
        raw = self.state.canonical_bytes()
        restored = parse(raw, expected_sha256=self.state.digest)
        self.assertEqual(restored, self.state)
        self.assertEqual(serialize(restored), raw)
        self.assertEqual(self.state.digest, hashlib.sha256(raw).hexdigest())
        reordered = replace(self.state, anchors=tuple(reversed(self.state.anchors)))
        self.assertEqual(serialize(reordered), raw)
        direct = replace(self.state, anchors=self.state.anchors[2:])
        sequential = replace(replace(self.state, anchors=self.state.anchors[1:]), anchors=self.state.anchors[2:])
        fresh = from_factor_state(replace(self.exact, anchors=self.exact.anchors[2:]), bits=40, block_size=3)
        self.assertEqual(serialize(direct), serialize(sequential))
        self.assertEqual(serialize(direct), serialize(fresh))
        for before, after in zip(self.state.anchors[2].descriptors, fresh.anchors[0].descriptors):
            self.assertEqual(encode_descriptor(before), encode_descriptor(after))
        empty = replace(self.state, anchors=())
        self.assertEqual(parse(serialize(empty)), empty)
        self.assertEqual(serialize(empty), serialize(from_factor_state(
            replace(self.exact, anchors=()), bits=40, block_size=3)))

    def test_leaf_rejects_record_token_stage_and_dimension_mismatches(self):
        leaf = self.state.anchors[0]
        descriptor = leaf.descriptors[0]
        variants = (
            replace(descriptor, record_id='other'),
            replace(descriptor, token_sha256='0'*64),
            replace(descriptor, shape=(1, 8)),
        )
        for invalid in variants:
            with self.assertRaisesRegex(ValueError, 'record or token'):
                replace(leaf, descriptors=(invalid, leaf.descriptors[1]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            replace(leaf, descriptors=(descriptor, descriptor))
        for descriptors in ((), (object(),)):
            with self.assertRaises(TypeError):
                replace(leaf, descriptors=descriptors)
        with self.assertRaises(ValueError):
            replace(leaf, tokens=(True, 1))
        normalized = CompressedFactorLeaf(leaf.record_id, list(leaf.tokens), list(leaf.descriptors))
        self.assertEqual(normalized, leaf)

    def test_state_rejects_target_codec_order_and_membership_mismatches(self):
        leaf = self.state.anchors[0]
        for field, value in (('target_sha256', '0'*64), ('anchor_target_sha256', '1'*64),
                             ('codec_sha256', '2'*64)):
            altered = replace(leaf.descriptors[0], **{field: value})
            with self.assertRaisesRegex(ValueError, 'target or codec'):
                replace(self.state, anchors=(replace(leaf, descriptors=(altered, leaf.descriptors[1])),))
        for changes in ({'bits': 24}, {'block_size': 4}):
            with self.assertRaisesRegex(ValueError, 'target or codec'):
                replace(self.state, **changes)
        for descriptors in (leaf.descriptors[:-1], tuple(reversed(leaf.descriptors))):
            with self.assertRaisesRegex(ValueError, 'every ordered model stage'):
                replace(self.state, anchors=(replace(leaf, descriptors=descriptors),))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            replace(self.state, anchors=(leaf, leaf))
        with self.assertRaisesRegex(ValueError, 'must differ'):
            replace(self.state, target_sha256=self.state.anchor_target_sha256)
        with self.assertRaises(TypeError):
            replace(self.state, anchors=(self.exact.anchors[0],))

    def test_parser_caps_and_payload_corruption(self):
        raw = serialize(self.state)
        for bad in (raw+b'x', raw[:-1], raw[:25]+bytes([raw[25]^1])+raw[26:]):
            with self.assertRaises(ValueError):
                parse(bad)
        damaged = bytearray(raw)
        damaged[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            parse(bytes(damaged))
        with self.assertRaisesRegex(ValueError, 'trusted digest'):
            parse(raw, expected_sha256='0'*64)
        limits = (LoadLimits(max_bytes=16), LoadLimits(max_header_bytes=1),
                  LoadLimits(max_records=1), LoadLimits(max_leaf_tokens=1),
                  LoadLimits(max_leaf_values=1), LoadLimits(max_leaf_bytes=1),
                  LoadLimits(max_stages=1), LoadLimits(max_code_elements=1))
        for limit in limits:
            with self.assertRaises(ValueError):
                parse(raw, limits=limit)
        with self.assertRaises(TypeError):
            parse(bytearray(raw))

    def test_parser_preflights_all_leaf_dimensions_before_decoding(self):
        raw = serialize(self.state)
        with patch('src.fixed_compressed_state_v26.decode_descriptor', side_effect=AssertionError('decoded too early')):
            with self.assertRaisesRegex(ValueError, 'values or bytes'):
                parse(raw, limits=LoadLimits(max_leaf_values=11))
            for update in (
                lambda h: h['leaves'][0]['descriptors'][1].update(shape=[2, 100000000]),
                lambda h: h['leaves'][0]['descriptors'][1].update(nbytes=True),
                lambda h: h['leaves'][0]['descriptors'][1].update(stage_id='wrong'),
            ):
                with self.assertRaises(ValueError):
                    parse(rewrite_header(raw, update))

    def test_parser_rejects_index_bindings_noncanonical_json_and_leaf_order(self):
        raw = serialize(self.state)
        for update in (
            lambda h: h.update(codec_sha256='0'*64),
            lambda h: h.update(target_sha256='0'*64),
            lambda h: h.update(bits=24),
            lambda h: h.update(block_size=2),
            lambda h: h['leaves'][0].update(record_id='another'),
            lambda h: h['leaves'][0].update(tokens=[7, 8]),
            lambda h: h['leaves'].reverse(),
        ):
            with self.assertRaises(ValueError):
                parse(rewrite_header(raw, update))
        size = struct.unpack_from('<Q', raw, 8)[0]
        spaced = json.dumps(json.loads(raw[16:16+size]), indent=1).encode('ascii')
        with self.assertRaisesRegex(ValueError, 'noncanonical'):
            parse(MAGIC+struct.pack('<Q', len(spaced))+spaced+raw[16+size:])

    def test_digest_binds_claims_without_proving_unavailable_source_containment(self):
        leaf = self.state.anchors[0]
        altered = replace(leaf.descriptors[0], source_sha256='0'*64)
        different = replace(self.state, anchors=(replace(leaf, descriptors=(altered, leaf.descriptors[1])),))
        raw = serialize(different)
        # Self-consistent hashes cannot prove that the declared source existed.
        self.assertEqual(parse(raw), different)
        with self.assertRaisesRegex(ValueError, 'trusted digest'):
            parse(raw, expected_sha256=self.state.digest)
        self.assertNotEqual(different.digest, replace(self.state, anchors=(leaf,)).digest)
        changed_provenance = replace(self.state, decoder_sha256='0'*64)
        self.assertNotEqual(changed_provenance.digest, self.state.digest)

    def test_conversion_and_empty_state_validate_settings(self):
        for changes in ({'bits': True}, {'bits': 8}, {'block_size': 0}, {'block_size': 4097}):
            with self.assertRaises(ValueError):
                from_factor_state(replace(self.exact, anchors=()), **changes)
        with self.assertRaises(TypeError):
            from_factor_state(self.state)
        with self.assertRaises(TypeError):
            serialize(self.exact)

    def test_default_and_32_40_bit_deletion_states_are_canonical(self):
        default = from_factor_state(self.exact)
        self.assertEqual(default.bits, 40)
        self.assertEqual(default.block_size, 256)
        self.assertEqual(default.codec_sha256, codec_binding())
        for bits in (32, 40):
            original = from_factor_state(self.exact, bits=bits, block_size=7)
            first = replace(original, anchors=original.anchors[1:])
            sequential = replace(first, anchors=first.anchors[1:])
            combined = replace(original, anchors=original.anchors[2:])
            fresh = from_factor_state(replace(self.exact, anchors=self.exact.anchors[2:]),
                                      bits=bits, block_size=7)
            for candidate in (sequential, combined, fresh):
                self.assertEqual(candidate.canonical_bytes(), fresh.canonical_bytes())
                self.assertEqual(parse(candidate.canonical_bytes(), expected_sha256=candidate.digest), candidate)
                self.assertEqual(candidate.stages, self.exact.stages)
            for old, new in zip(original.anchors[2].descriptors, fresh.anchors[0].descriptors):
                self.assertEqual(encode_descriptor(old), encode_descriptor(new))

    def test_old_formats_and_descriptor_types_are_rejected(self):
        old = convert_v25(self.exact, bits=16, block_size=3)
        new = from_factor_state(self.exact, bits=16, block_size=3)
        with self.assertRaisesRegex(ValueError, 'magic'):
            parse(serialize_v25(old))
        with self.assertRaisesRegex(ValueError, 'magic'):
            parse_v25(serialize(new))
        with self.assertRaises(TypeError):
            serialize(old)
        with self.assertRaises(TypeError):
            serialize_v25(new)
        with self.assertRaises(TypeError):
            CompressedFactorLeaf(old.anchors[0].record_id, old.anchors[0].tokens, old.anchors[0].descriptors)
        with self.assertRaisesRegex(ValueError, 'schema'):
            parse(rewrite_header(serialize(new), lambda h: h.update(storage_schema='source_local_compressed_factors_v1')))
        for old_leaf, new_leaf in zip(old.anchors, new.anchors):
            for old_descriptor, new_descriptor in zip(old_leaf.descriptors, new_leaf.descriptors):
                self.assertEqual(old_descriptor.payload, new_descriptor.payload)
                self.assertEqual(old_descriptor.source_sha256, new_descriptor.source_sha256)
                self.assertNotEqual(old_descriptor.codec_sha256, new_descriptor.codec_sha256)


if __name__ == '__main__':
    unittest.main()
