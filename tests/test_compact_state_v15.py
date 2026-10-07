"""Software checks for exact dyadic row state and V13 byte compatibility."""
from dataclasses import replace
from fractions import Fraction as Q
import hashlib
import math
import struct
import unittest

import numpy as np

from src.compact_state import CompactState, StageCodes, parse, prefix_digest, serialize
from tests.test_compact_state_v13 import TARGET, fixture, rewrite_header


class DyadicCompactStateTests(unittest.TestCase):
    def test_old_power_of_two_bytes_remain_identical(self):
        raw = serialize(fixture())
        self.assertEqual(len(raw), 1963)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "100217b97aa0a093e12aa8f53c5412a3cfc3ea596d482131a3e939ab06e2fd09")
        self.assertEqual(serialize(parse(raw)), raw)

    def test_every_code_all_bits_and_exact_dyadic_scales(self):
        for bits in range(2, 9):
            half = 1 << (bits - 1)
            scales = (0.1875, 3.0 * 2.0**-1073, 3.0 * 2.0**(1022 - bits))
            rows = [[float(Q.from_float(s) * code) for code in range(-half, half)] for s in scales]
            values = np.array(rows, dtype=np.float64)
            codes = StageCodes.from_array("s", values, grid_axis="dyadic_row", bits=bits,
                                          scale_values=scales)
            self.assertEqual(codes.scale_exponents, ())
            self.assertEqual(codes.scale_values, scales)
            self.assertTrue(np.array_equal(codes.array().view("u8"), values.view("u8")))
            self.assertTrue(np.array_equal(codes.indices_array(),
                                           np.tile(np.arange(2 * half), (3, 1))))
            self.assertEqual(codes.metadata()["scale_values_hex"], [s.hex() for s in scales])
            with self.assertRaises(ValueError):
                codes.array().flags.writeable = True
            state = CompactState(TARGET, (codes,), ())
            self.assertEqual(parse(serialize(state)), state)
            self.assertEqual(serialize(parse(serialize(state))), serialize(state))

    def test_mixed_state_preserves_factor_and_prefix_bindings(self):
        old = fixture()
        stages = (old.stages[0], StageCodes.from_array(
            "stage.b", np.array([[.375, -.5625]]), grid_axis="dyadic_row", bits=4,
            scale_values=(.1875,)))
        factors = tuple(replace(f, prefix_sha256=prefix_digest(TARGET, stages[:1]))
                        if f.stage_id == "stage.b" else f for f in old.factors)
        state = CompactState(TARGET, stages, factors)
        self.assertEqual(parse(serialize(state)), state)
        fresh = CompactState(TARGET, stages, reversed(factors))
        self.assertEqual(serialize(fresh), serialize(state))
        removed = CompactState(TARGET, stages, tuple(f for f in factors if f.record_id == "article.a"))
        self.assertNotIn(b"article.b", serialize(removed))

    def test_near_grid_values_cannot_pass_rounded_division(self):
        grid = StageCodes.from_array("s", np.array([[-0., .1875, -.375]]),
                                     grid_axis="dyadic_row", bits=4, scale_values=(.1875,))
        self.assertEqual(struct.pack("<d", grid.array()[0, 0]), b"\0" * 8)
        for value in (math.nextafter(.1875, math.inf), math.nextafter(.1875, 0.0), 1.5):
            with self.assertRaisesRegex(ValueError, "exact member"):
                StageCodes.from_array("s", np.array([[value]]), grid_axis="dyadic_row",
                                      bits=4, scale_values=(.1875,))

    def test_invalid_scale_precision_midpoints_range_and_types(self):
        for scales in ((0.,), (-1.,), (math.inf,), (math.nan,), (1,),
                       (2.0**-1074,), (math.nextafter(1., 2.),), (2.0**1021,), ()):
            with self.assertRaises(ValueError):
                StageCodes.from_array("s", np.array([[0.]]), grid_axis="dyadic_row", bits=4,
                                      scale_values=scales)
        with self.assertRaises(ValueError):
            StageCodes.from_array("s", np.array([[0.]]), grid_axis="dyadic_row", bits=4,
                                  scale_values=(.1875,), scale_exponents=(0,))
        with self.assertRaises(ValueError):
            StageCodes.from_array("s", np.array([[0.]]), grid_axis="row", bits=4,
                                  scale_exponents=(0,), scale_values=(.1875,))

    def test_canonical_dyadic_metadata_rejects_alternate_encodings(self):
        codes = StageCodes.from_array("s", np.array([[0., .1875]]),
                                     grid_axis="dyadic_row", bits=4, scale_values=(.1875,))
        raw = serialize(CompactState(TARGET, (codes,), ()))
        for text in ("0x1.8p-3", "0X1.8000000000000P-3", "0.1875", "nan", "inf", "-0x0.0p+0"):
            changed = rewrite_header(raw, lambda h: h["stages"][0].update(scale_values_hex=[text]))
            with self.assertRaises(ValueError):
                parse(changed)
        changed = rewrite_header(raw, lambda h: h["stages"][0].update(scale_exponents=[]))
        with self.assertRaises(ValueError):
            parse(changed)


if __name__ == "__main__":
    unittest.main()
