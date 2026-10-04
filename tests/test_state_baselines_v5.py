"""State and baseline software checks. These are not research experiments."""
from dataclasses import fields, replace
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.aggregate_response_service import AggregateIndex, AggregateState, StateParseLimits
from src.repair_service import Record, StageOutput, _json
from tests import test_aggregate_response_service as fixtures


class StateBaselineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AggregateServiceTests()
        self.service, self.calls, self.contexts, self.control = self.fixture.build()
        self.records = self.fixture.records()
        self.source = {r.record_id: r for r in self.records}.__getitem__
        self.state = self.service.fresh(self.records).state
        self.payload = self.state.canonical_bytes()

    def encoded(self, transform):
        data = json.loads(self.payload)
        transform(data)
        return _json(data)

    def test_state_round_trip_after_repeated_deletion(self):
        restored = self.service.load_state(self.payload, expected_digest=self.state.digest)
        self.assertEqual(restored, self.state)
        for removed in self.records[:2]:
            restored = self.service.repair(restored, [removed], self.source).state
            restored = self.service.load_state(restored.canonical_bytes(), expected_digest=restored.digest)
        expected = self.service.fresh(self.records[2:]).state
        self.assertEqual(restored.canonical_bytes(), expected.canonical_bytes())

    def test_new_process_reload_and_delete_matches_fresh_state(self):
        program = """
from pathlib import Path
import sys
from tests import test_aggregate_response_service as fixtures
fixture = fixtures.AggregateServiceTests()
service = fixture.build()[0]
records = fixture.records()
state = service.load_state(Path(sys.argv[1]).read_bytes(), expected_digest=sys.argv[3])
source = {record.record_id: record for record in records}.__getitem__
result = service.repair(state, records[:1], source)
Path(sys.argv[2]).write_bytes(result.state.canonical_bytes())
"""
        expected = self.service.fresh(self.records[1:]).state.canonical_bytes()
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "state.json"
            result_path = Path(directory) / "retained.json"
            source_path.write_bytes(self.payload)
            completed = subprocess.run(
                [sys.executable, "-c", program, str(source_path), str(result_path), self.state.digest],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(result_path.read_bytes(), expected)

    def test_unicode_ids_round_trip(self):
        record = Record("दस्तावेज़-α", b"[1,2]")
        state = self.service.fresh([record]).state
        self.assertEqual(self.service.load_state(state.canonical_bytes()), state)

    def test_digest_and_manifest_bindings(self):
        with self.assertRaisesRegex(ValueError, "expected digest"):
            self.service.load_state(self.payload, expected_digest="0" * 64)
        with self.assertRaisesRegex(ValueError, "service manifest"):
            self.service.load_state(self.encoded(lambda d: d.update(manifest="0" * 64)))
        with self.assertRaisesRegex(ValueError, "service manifest"):
            self.fixture.build(normalization=7)[0].load_state(self.payload)

    def test_noncanonical_json_and_duplicate_keys(self):
        for payload in (b" " + self.payload, self.payload + b"\n",
                        b'{"schema":"aggregate-linear-service-v1",' + self.payload[1:]):
            with self.subTest(payload=payload[:60]), self.assertRaises(ValueError):
                self.service.load_state(payload)
        with self.assertRaisesRegex(ValueError, "missing or unknown"):
            self.service.load_state(self.encoded(lambda d: d.update(unexpected=1)))

    def test_noncanonical_rationals_and_boolean_integers(self):
        def rational(data, value):
            data["model"][0]["codes"][0][0] = value
        for value in ([0, 2], [True, 1], [0, True], [0, -1], [0.0, 1]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.service.load_state(self.encoded(lambda d: rational(d, value)))
        def boolean_group(data):
            data["records"][0]["group"] = False
        with self.assertRaises(ValueError):
            self.service.load_state(self.encoded(boolean_group))

    def test_nested_index_requires_canonical_rationals(self):
        def corrupt(data):
            inner = json.loads(data["groups"][0]["stages"][0]["response"])
            scalar = inner["constant_gram"][0][0]
            inner["constant_gram"][0][0] = [scalar[0] * 2, scalar[1] * 2]
            data["groups"][0]["stages"][0]["response"] = json.dumps(inner, separators=(",", ":"), sort_keys=True)
        with self.assertRaisesRegex(ValueError, "rational is not canonical"):
            self.service.load_state(self.encoded(corrupt))

    def test_duplicate_record_group_and_stage_ids(self):
        def duplicate_record(data):
            data["records"].append(data["records"][0])
        def duplicate_group(data):
            data["groups"].append(data["groups"][0])
        def duplicate_stage(data):
            data["model"].append(data["model"][0])
        for change in (duplicate_record, duplicate_group, duplicate_stage):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.service.load_state(self.encoded(change))

    def test_corrupt_membership_model_and_aggregate(self):
        changes = [lambda d: d["groups"][0].update(membership_digest="0" * 64),
                   lambda d: d["model"][0].update(codes=[[[8, 1], [8, 1]]]),
                   lambda d: d["groups"][0]["stages"][0].update(unavailable=1),
                   lambda d: d["groups"][0]["stages"][0].update(error=None)]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.service.load_state(self.encoded(change))
        def bad_psd(data):
            raw = json.loads(data["groups"][0]["stages"][0]["response"])
            raw["constant_gram"][0][0] = [-1, 1]
            data["groups"][0]["stages"][0]["response"] = json.dumps(raw, separators=(",", ":"), sort_keys=True)
        with self.assertRaisesRegex(ValueError, "not PSD"):
            self.service.load_state(self.encoded(bad_psd))

    def test_explicit_parse_limits(self):
        limits = {"max_bytes": len(self.payload) - 1, "max_records": 1, "max_stages": 1,
                  "max_width": 1, "max_terms": 1, "max_rationals": 1,
                  "max_text_length": 1, "max_depth": 1}
        for name, value in limits.items():
            with self.subTest(limit=name), self.assertRaises(ValueError):
                self.service.load_state(self.payload, limits=replace(StateParseLimits(), **{name: value}))
        with self.assertRaises(ValueError):
            StateParseLimits(max_bytes=True)
        with self.assertRaises(TypeError):
            self.service.load_state(self.payload, limits={})
        with self.assertRaisesRegex(ValueError, "max_integer_digits"):
            self.service.load_state(self.encoded(lambda d: d["groups"][0].update(group=12)),
                                    limits=StateParseLimits(max_integer_digits=1))

    def test_parser_rejects_truncated_float_and_deep_data(self):
        for payload in (self.payload[:-1], b"NaN", b"1e3", b"[" * 1000 + b"0" + b"]" * 1000):
            with self.subTest(payload=payload[:40]), self.assertRaises(ValueError):
                AggregateState.from_canonical_bytes(payload)

    def test_indexed_fresh_ignores_prior_model_and_matches_direct_oracle(self):
        # Alternative valid grid codes must have no effect on reconstruction.
        poisoned = replace(self.state, model=tuple(StageOutput(s.stage_id, ((0, 0),)) for s in self.service.job.stages))
        self.assertNotEqual(poisoned.model, self.state.model)
        result = self.service.indexed_fresh(poisoned, self.source)
        self.assertEqual(result.state.canonical_bytes(), self.payload)
        # No old model validation or access is necessary for an index-only solve.
        absent_model = replace(self.state, model=None)
        self.assertEqual(self.service.indexed_fresh(absent_model, self.source).state.canonical_bytes(), self.payload)

    def test_prepare_index_contains_no_model_and_charges_deletion_once(self):
        prepared = self.service.prepare_index(self.state, [self.records[0]])
        self.assertIsInstance(prepared.index, AggregateIndex)
        self.assertEqual({f.name for f in fields(prepared.index)}, {"manifest_digest", "records", "groups"})
        self.assertEqual(prepared.ledger.count("deleted_intrinsic_extractor_calls"), 2)
        self.assertGreater(prepared.ledger.count("index_serialized_bytes"), 0)
        result = self.service.indexed_fresh(prepared.index, self.source)
        self.assertEqual(result.ledger.count("deleted_intrinsic_extractor_calls"), 0)
        repair = self.service.repair(self.state, [self.records[0]], self.source)
        expected = self.service.fresh(self.records[1:]).state
        self.assertEqual(result.state.canonical_bytes(), expected.canonical_bytes())
        self.assertEqual(result.state, repair.state)
        self.assertEqual(result.stages, repair.stages)
        self.assertEqual(len(prepared.index.digest), 64)

    def test_full_replay_uses_retained_records_and_no_query(self):
        prepared = self.service.prepare_index(self.state, [self.records[0]])
        self.contexts.clear()
        result = self.service.indexed_fresh(prepared.index, self.source, mode="full_replay")
        self.assertEqual(self.contexts, [])
        self.assertEqual(result.ledger.count("retained_source_record_reads"), 2)
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 4)
        self.assertTrue(all(s.route == "forced_full_replay" for s in result.stages))
        self.assertEqual(result.state, self.service.fresh(self.records[1:]).state)
        self.assertEqual(result.state, self.service.repair(self.state, [self.records[0]], self.source,
                                                        mode="full_replay").state)

    def test_invalid_index_mode_or_replayed_source_fails_without_commit(self):
        with self.assertRaises(ValueError):
            self.service.indexed_fresh(self.state, self.source, mode="unknown")
        group = replace(self.state.groups[0], membership_digest="0" * 64)
        with self.assertRaises(ValueError):
            self.service.indexed_fresh(replace(self.state, groups=(group,)), self.source)
        with self.assertRaisesRegex(ValueError, "content differs"):
            self.service.indexed_fresh(self.state, lambda rid: Record(rid, b"[9,9]"), mode="full_replay")
        self.assertEqual(self.state.canonical_bytes(), self.payload)


if __name__ == "__main__":
    unittest.main()
