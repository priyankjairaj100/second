"""Independent sparse-recurrence checks; software fixtures, no performance study."""

from dataclasses import replace
from fractions import Fraction as F
import unittest

from src.exact_core import reverse_ldl, sequential_oracle
from src.sparse_repair import sparse_repair
try:
    from .test_exact_core_independent import constrained_oracle
except ImportError:  # unittest discover -s tests imports top-level modules.
    from test_exact_core_independent import constrained_oracle


class AdversarialSparseTests(unittest.TestCase):
    def test_changed_factor_against_independent_constrained_solves(self):
        old_h = ((4, 1, -1), (1, 3, 1), (-1, 1, 4))
        targets = (
            ((4, -1, 1), (-1, 3, -1), (1, -1, 4)),
            ((2, 0, 0), (0, 2, 0), (0, 0, 2)),
            ((6, 2, 1), (2, 5, 2), (1, 2, 4)),
        )
        grids = ((-2, -1, 0, 1, 2),) * 3
        weights = tuple((F(i, 3), F(i + 2, 4), F(2 - i, 5)) for i in range(-4, 5))
        old = sequential_oracle(weights, old_h, grids)
        changes = 0
        for target in targets:
            new_b = reverse_ldl(target).B
            expected = constrained_oracle(weights, target, grids)
            fallback = sparse_repair(weights, old, new_b)
            self.assertEqual(fallback.codes, expected)
            self.assertTrue(fallback.old_trace_verified)
            self.assertTrue(fallback.used_envelopes_verified_by_module)
            self.assertFalse(fallback.target_provenance_verified_by_module)

            def exact_envelope(row, coordinate):
                displacement = -sum(
                    (new_b[coordinate][h] - old.factors.B[coordinate][h])
                    * (weights[row][h] - old.rows[row].codes[h])
                    for h in range(coordinate)
                )
                return displacement, displacement

            checked = sparse_repair(weights, old, new_b, exact_envelope, verify_envelopes=True)
            self.assertEqual(checked.codes, expected)
            self.assertEqual(checked.work.exact_fallbacks, 0)
            changes += checked.work.changed_codes
        self.assertGreater(changes, 0)

    def test_stale_trace_rejected_before_any_candidate_returns(self):
        weights = ((F(1, 3), F(2, 3)),)
        old = sequential_oracle(weights, ((2, 1), (1, 2)), ((0, 1),) * 2)
        altered = replace(old.rows[0], inputs=(F(0), old.rows[0].inputs[1]))
        with self.assertRaises(ValueError):
            sparse_repair(weights, replace(old, rows=(altered,)), old.factors.B)

    def test_false_external_envelope_requires_explicit_unverified_status(self):
        weights = ((F(1, 3), F(2, 3)),)
        old = sequential_oracle(weights, ((2, 1), (1, 2)), ((0, 1),) * 2)
        dishonest = lambda row, coordinate: (F(10), F(10))
        with self.assertRaises(ValueError):
            sparse_repair(weights, old, old.factors.B, dishonest, verify_envelopes=True)
        unverified = sparse_repair(weights, old, old.factors.B, dishonest)
        self.assertFalse(unverified.used_envelopes_verified_by_module)
        self.assertFalse(unverified.target_provenance_verified_by_module)
