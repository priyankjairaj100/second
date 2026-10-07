"""Software fixtures for the explicit factor_identity_v1 state family."""
from dataclasses import replace
import hashlib
import json
import struct
import unittest

import numpy as np

from src.compact_state import (
    CompactState, FAMILY, LoadLimits, MAGIC, RecordFactor, StageCodes,
    parse, prefix_digest, serialize, token_digest,
)


TARGET = "ab" * 32


def fixture():
    stages = (
        StageCodes.from_array("stage.a", np.array([[0., 1.], [-2., 2.]]),
                              grid_axis="row", bits=4, scale_exponents=(0, 1)),
        StageCodes.from_array("stage.b", np.array([[.5, -2.]]),
                              grid_axis="column", bits=3, scale_exponents=(-1, 1)),
    )
    factors = []
    for index, stage in enumerate(stages):
        for record, tokens in (("article.b", (3, 7)), ("article.a", (4,))):
            values = np.array([[float(t), index + .5] for t in tokens])
            factors.append(RecordFactor.from_array(
                stage.stage_id, record, values,
                prefix_sha256=prefix_digest(TARGET, stages[:index]),
                token_sha256=token_digest(tokens)))
    return CompactState(TARGET, stages, tuple(factors))


def rewrite_header(data, update, *, canonical=True):
    size = struct.unpack("<Q", data[8:16])[0]
    header = json.loads(data[16:16 + size])
    update(header)
    raw = json.dumps(header, sort_keys=True,
                     separators=(",", ":") if canonical else (", ", ": ")).encode("ascii")
    return MAGIC + struct.pack("<Q", len(raw)) + raw + data[16 + size:]


class CompactStateTests(unittest.TestCase):
    def test_all_bit_widths_and_axes_roundtrip(self):
        for bits in range(2, 9):
            half = 1 << (bits - 1)
            indices = np.arange(3 * 257, dtype=np.int64).reshape(3, 257) % (2 * half)
            integers = (indices - half).astype(np.float64)
            for axis in ("row", "column"):
                scales = tuple((i % 7) - 3 for i in range(3 if axis == "row" else 257))
                shifts = np.array(scales)
                shifts = shifts[:, None] if axis == "row" else shifts[None, :]
                values = np.ldexp(integers, shifts)
                codes = StageCodes.from_array("s", values, grid_axis=axis, bits=bits,
                                              scale_exponents=scales)
                self.assertTrue(np.array_equal(codes.indices_array(), indices))
                self.assertTrue(np.array_equal(codes.array(), values))
                self.assertEqual(codes.shape, values.shape)
                self.assertEqual(len(codes.packed_indices), (values.size * bits + 7) // 8)
                with self.assertRaises(ValueError):
                    codes.array().flags.writeable = True

    def test_large_packing_chunk_boundary_and_extreme_scales(self):
        values = (np.arange(65539, dtype=np.int64) % 32 - 16).astype(np.float64)[None, :]
        codes = StageCodes.from_array("s", values, grid_axis="row", bits=5, scale_exponents=(0,))
        self.assertTrue(np.array_equal(codes.array(), values))
        for exponent in (-1074, 1020):
            values = np.ldexp(np.array([[-8., -1., 0., 7.]]), exponent)
            codes = StageCodes.from_array("s", values, grid_axis="row", bits=4,
                                          scale_exponents=(exponent,))
            self.assertTrue(np.array_equal(codes.array(), values))

    def test_exact_serialization_and_immutable_source_copies(self):
        state = fixture()
        raw = serialize(state)
        loaded = parse(raw, expected_sha256=state.digest)
        self.assertEqual(state, loaded)
        self.assertEqual(serialize(loaded), raw)
        self.assertEqual(state.record_ids, ("article.a", "article.b"))
        self.assertEqual(state.code_bytes, 3)
        self.assertEqual(state.factor_bytes, 96)
        self.assertEqual(FAMILY, "factor_identity_v1")
        values = np.array([[-0., 1.]])
        factor = RecordFactor.from_array("stage.a", "x", values,
            prefix_sha256=prefix_digest(TARGET), token_sha256=token_digest((1,)))
        values[:] = 99
        self.assertTrue(np.array_equal(factor.array(), [[0., 1.]]))
        self.assertFalse(np.signbit(factor.array()[0, 0]))
        with self.assertRaises(ValueError):
            factor.array().flags.writeable = True

    def test_fresh_and_repair_order_equality_and_deletion_omission(self):
        original = fixture()
        retained = tuple(f for f in original.factors if f.record_id != "article.b")
        repaired = CompactState(TARGET, original.stages, retained)
        fresh = CompactState(TARGET, original.stages, reversed(retained))
        self.assertEqual(serialize(repaired), serialize(fresh))
        self.assertNotIn(b"article.b", serialize(repaired))
        self.assertEqual(repaired.record_ids, ("article.a",))
        self.assertEqual(repaired.factor_bytes, 32)
        empty = CompactState(TARGET, original.stages, ())
        self.assertEqual(parse(serialize(empty)), empty)
        self.assertEqual(empty.record_ids, ())
        self.assertEqual(empty.factor_bytes, 0)

    def test_prefix_and_membership_invariants(self):
        original = fixture()
        changed = StageCodes.from_array("stage.a", np.array([[1., 1.], [-2., 2.]]),
                                       grid_axis="row", bits=4, scale_exponents=(0, 1))
        with self.assertRaisesRegex(ValueError, "current stage prefix"):
            CompactState(TARGET, (changed, original.stages[1]), original.factors)
        with self.assertRaisesRegex(ValueError, "every retained record"):
            CompactState(TARGET, original.stages, original.factors[:-1])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            CompactState(TARGET, original.stages, original.factors + original.factors[:1])
        factor = replace(original.factors[-1], token_sha256="cc" * 32)
        with self.assertRaisesRegex(ValueError, "token order"):
            CompactState(TARGET, original.stages, original.factors[:-1] + (factor,))
        with self.assertRaisesRegex(ValueError, "unknown stage"):
            CompactState(TARGET, original.stages, (replace(factor, stage_id="unknown"),))

    def test_payload_and_metadata_tampering_and_truncation(self):
        state = fixture()
        raw = serialize(state)
        corrupt = raw[:-1] + bytes([raw[-1] ^ 1])
        with self.assertRaisesRegex(ValueError, "payload hash"):
            parse(corrupt)
        for cut in (0, 7, 15, 32, len(raw) - 1):
            with self.assertRaises(ValueError):
                parse(raw[:cut])
        with self.assertRaisesRegex(ValueError, "trailing"):
            parse(raw + b"x")
        changed = rewrite_header(raw, lambda h: h.update(target_sha256="cd" * 32))
        with self.assertRaisesRegex(ValueError, "trusted digest"):
            parse(changed, expected_sha256=state.digest)
        with self.assertRaises(ValueError):
            parse(changed)

    def test_noncanonical_metadata_rejected(self):
        raw = serialize(fixture())
        mutations = (
            lambda h: h["record_ids"].reverse(),
            lambda h: h["factors"].reverse(),
            lambda h: h.update(extra="forbidden"),
            lambda h: h.update(family="aggregate-v1"),
            lambda h: h["stages"][0].update(rows=True),
            lambda h: h["factors"][0].update(nbytes=True),
        )
        for mutation in mutations:
            with self.assertRaises(ValueError):
                parse(rewrite_header(raw, mutation))
        with self.assertRaisesRegex(ValueError, "not canonical"):
            parse(rewrite_header(raw, lambda h: None, canonical=False))

    def test_resource_limits_precede_payload_allocation(self):
        raw = serialize(fixture())
        for limits in (LoadLimits(max_bytes=16), LoadLimits(max_header_bytes=16),
                       LoadLimits(max_stages=1), LoadLimits(max_records=1),
                       LoadLimits(max_factors=1), LoadLimits(max_code_elements=1),
                       LoadLimits(max_factor_values=1)):
            with self.assertRaises(ValueError):
                parse(raw, limits=limits)
        huge = rewrite_header(raw, lambda h: h["stages"][0].update(rows=2**100))
        with self.assertRaisesRegex(ValueError, "elements exceed"):
            parse(huge)

    def test_invalid_values_and_noncanonical_padding(self):
        for values in (np.array([[.5]]), np.array([[8.]]), np.array([[np.inf]])):
            with self.assertRaises(ValueError):
                StageCodes.from_array("s", values, grid_axis="row", bits=4, scale_exponents=(0,))
        with self.assertRaisesRegex(ValueError, "unused"):
            StageCodes("s", 1, 1, "row", 3, (0,), b"\x80")
        with self.assertRaises(ValueError):
            StageCodes("s", 1, 1, "row", 4, (1021,), b"\x00")
        for value in (float("nan"), float("inf"), -0.0):
            with self.assertRaises(ValueError):
                RecordFactor("s", "r", prefix_digest(TARGET), token_digest((1,)),
                             1, 1, struct.pack("<d", value))
        with self.assertRaises(ValueError):
            token_digest((True,))


if __name__ == "__main__":
    unittest.main()
