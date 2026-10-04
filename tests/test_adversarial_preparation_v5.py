"""Independent correctness attacks for preparation code, without research runs."""
from dataclasses import replace
from fractions import Fraction as Q
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.aggregate_response_service import AggregateState, AggregateRepairService
from src.repair_service import JobSpec, Record, StageSpec, StageOutput, UNKNOWN
from src.run_store import RunStore, canonical_json
from src.result_analysis import AnalysisError, analyze_runs
from src.certified_transformer import CertifiedDecoder, AutomaticResponseProvider
from src.transformer_backend import DecoderConfig, DeterministicDecoder
from src.target_manifest import TargetRecipe, build_target
from src.chart_construction import ChartRecipe, build_chart, preview_chart, make_service
from src.experiment_runner import run_comparison


def exact_service():
    stages = (
        StageSpec("entrée", (), ((Q(2, 5), Q(2, 5)),), ((0, 1), (0, 1)), 1, 1),
        StageSpec("出口", ("entrée",), ((Q(2, 5), Q(2, 5)),), ((0, 1), (0, 1)), 1, 1),
    )
    job = JobSpec(stages, "independent-exact-affine-test", "independent-base-test", 1)
    def evaluate(record, stage, prefix):
        values = json.loads(record.payload)
        shift = 0 if not stage.dependencies else prefix.as_mapping()["entrée"][0][1]
        return ((Q(values[0]) + shift,), (Q(values[1]),))
    return AggregateRepairService(job, evaluate, lambda record, stage: None, {},
                                  lambda context: UNKNOWN, provider_id="none", extractor_id="none")


class AdversarialStateTests(unittest.TestCase):
    def test_unicode_canonical_state_load_and_second_deletion(self):
        service = exact_service()
        records = (Record("हिन्दी", b"[1,1]"), Record("français", b"[0,1]"), Record("中文", b"[1,2]"))
        state = service.fresh(records).state
        loaded = AggregateState.from_canonical_bytes(state.canonical_bytes())
        self.assertEqual(loaded, state)
        source = {record.record_id: record for record in records}.__getitem__
        first = service.repair(loaded, records[:1], source).state
        loaded_again = AggregateState.from_canonical_bytes(first.canonical_bytes())
        second = service.repair(loaded_again, records[1:2], source).state
        self.assertEqual(second.canonical_bytes(), service.fresh(records[2:]).state.canonical_bytes())

    def test_parser_rejects_bool_identity_and_nonreduced_rational(self):
        service = exact_service()
        state = service.fresh((Record("record", b"[1,1]"),)).state
        payload = json.loads(state.canonical_bytes())
        payload["records"][0]["group"] = False
        with self.assertRaises((TypeError, ValueError)):
            AggregateState.from_canonical_bytes(canonical_json(payload))
        payload = json.loads(state.canonical_bytes())
        payload["model"][0]["codes"][0][0] = [0, 2]
        with self.assertRaises((TypeError, ValueError)):
            AggregateState.from_canonical_bytes(canonical_json(payload))

    def test_indexed_fresh_ignores_prior_model_and_matches_direct(self):
        service = exact_service()
        records = (Record("a", b"[1,1]"), Record("b", b"[0,1]"))
        old = service.fresh(records).state
        poisoned = replace(old, model=tuple(StageOutput(x.stage_id, ((1, 1),)) for x in old.model))
        source = {record.record_id: record for record in records}.__getitem__
        a = service.indexed_fresh(old, source)
        b = service.indexed_fresh(poisoned, source)
        self.assertEqual(a.state.canonical_bytes(), old.canonical_bytes())
        self.assertEqual(b.state.canonical_bytes(), old.canonical_bytes())
        prepared = service.prepare_index(old, records[:1])
        self.assertFalse(hasattr(prepared.index, "model"))
        retained = service.indexed_fresh(prepared.index, source)
        self.assertEqual(retained.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())


class AdversarialRunStoreTests(unittest.TestCase):
    def test_reserved_status_name_and_writes_after_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(directory, {"request": "one"})
            store.claim()
            try:
                with self.assertRaises((ValueError, RuntimeError)):
                    store.write_artifact("status.json", b"not status")
                store.write_artifact("model.json", b"model")
                store.finish({"status": "complete"})
                with self.assertRaises((ValueError, RuntimeError)):
                    store.write_artifact("late.json", b"late")
            finally:
                store.close()
            self.assertEqual(RunStore(directory, {"request": "one"}).completed()["status"], "complete")

    def test_completed_attempt_cannot_be_overwritten_and_corruption_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(directory, {"request": "one"})
            with store:
                store.write_artifact("model.json", b"model")
                store.finish({"status": "complete"})
            saved = (Path(directory) / "result.json").read_bytes()
            other = RunStore(directory, {"request": "one"})
            with self.assertRaises((ValueError, RuntimeError)):
                other.claim()
            other.close()
            self.assertEqual((Path(directory) / "result.json").read_bytes(), saved)
            (store.attempt / "model.json").write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                RunStore(directory, {"request": "one"}).completed()

    def test_failed_attempt_keeps_prior_artifacts_and_next_attempt_is_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "interruption"):
                with RunStore(directory, {"request": "one"}) as first:
                    first.write_artifact("partial.json", b"partial")
                    raise RuntimeError("interruption")
            self.assertIsNone(RunStore(directory, {"request": "one"}).completed())
            with RunStore(directory, {"request": "one"}) as second:
                self.assertNotEqual(first.attempt, second.attempt)
                second.write_artifact("model.json", b"model")
                second.finish({"status": "complete"})
            self.assertEqual((first.attempt / "partial.json").read_bytes(), b"partial")

    def test_exception_after_commit_preserves_completion_and_releases_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(LookupError, "after commit"):
                with RunStore(directory, {"request": "one"}) as store:
                    store.write_artifact("model.json", b"model")
                    store.finish({"status": "complete"})
                    raise LookupError("after commit")
            self.assertFalse(store._locked)
            self.assertEqual(RunStore(directory, {"request": "one"}).completed()["status"], "complete")

    def test_lock_metadata_io_failure_releases_the_acquired_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            first = RunStore(directory, {"request": "one"})
            with patch("src.run_store.os.fsync", side_effect=OSError("declared lock metadata failure")):
                with self.assertRaises(OSError):
                    first.claim()
            self.assertFalse(first._locked)
            second = RunStore(directory, {"request": "one"})
            second.claim()
            second.close()


def analysis_record(root="r1", request="q1", target="a" * 64):
    arm = {"status": "complete", "exact_state_equal": True, "exact_model_equal": True,
           "wall_time_ns": 10, "complete_wall_time_ns": 10}
    return {"schema": "calibration-experiment-v1", "configuration_id": "c", "phase": "development",
            "cache_mode": "warm", "root_id": root, "request_id": request, "repeat_index": 0,
            "planned_methods": ["repair", "indexed_fresh"], "status": "complete",
            "service_boundary": "complete_request", "target_manifest_sha256": target,
            "protocol_sha256": "b" * 64,
            "methods": {"repair": dict(arm), "indexed_fresh": dict(arm)}}


class AdversarialAnalysisTests(unittest.TestCase):
    def test_different_targets_cannot_share_one_stratum(self):
        with self.assertRaises(AnalysisError):
            analyze_runs((analysis_record(), analysis_record(root="r2", target="c" * 64)), draws=10)

    def test_missing_planned_attempt_stays_in_denominator(self):
        first = analysis_record()
        missing = analysis_record(root="r2")
        result = analyze_runs((first,), planned_runs=(first, missing), draws=10)
        stratum = result["strata"][0]
        self.assertEqual(stratum["planned_attempt_count"], 2)
        self.assertEqual(stratum["methods"]["repair"]["outcomes"]["missing_run"], 1)
        self.assertEqual(stratum["conditional_ratio"]["eligible_roots"], 1)
        self.assertIsNone(stratum["conditional_ratio"]["root_interval"])

    def test_timing_repeats_do_not_create_independent_roots(self):
        a = analysis_record()
        b = dict(a, repeat_index=1)
        result = analyze_runs((a, b), draws=10)
        stratum = result["strata"][0]
        self.assertEqual(stratum["independent_root_count"], 1)
        self.assertEqual(stratum["planned_request_count"], 1)
        self.assertIsNone(stratum["conditional_ratio"]["root_interval"])

    def test_unverified_interruption_is_not_a_mismatch(self):
        record = analysis_record()
        record["status"] = "failed"
        record["methods"]["repair"].update(status="pending_verification", exact_state_equal=None,
                                              exact_model_equal=None)
        result = analyze_runs((record,), draws=10)
        outcomes = result["strata"][0]["methods"]["repair"]["outcomes"]
        self.assertNotIn("mismatch", outcomes)
        self.assertNotIn("exact_complete", outcomes)


class _DiagnosticDecoder:
    @staticmethod
    def decode_payload(payload):
        return tuple(json.loads(payload))

    @staticmethod
    def logits(tokens, prefix=None):
        return tuple((0.0, 1.0) for _ in tokens)


class AdversarialRunnerTests(unittest.TestCase):
    def test_timeout_retains_its_reason_without_claiming_inequality(self):
        service = exact_service()
        class OneTimeout:
            def __getattr__(self, name):
                return getattr(service, name)
            def prepare_index(self, *args):
                raise TimeoutError("declared software timeout fixture")
        records = (Record("a", b"[1,1]"), Record("b", b"[0,1]"))
        metadata = dict(root_id="r1", request_id="q1", configuration_id="c1", repeat_index=0,
                        phase="software_test", protocol_sha256="b" * 64)
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(directory, {"software_fixture": "timeout"})
            result = run_comparison(_DiagnosticDecoder(), OneTimeout(), records, ("a",),
                                    (Record("eval", b"[1,0]"),), store, metadata)
        self.assertEqual(result["status"], "failed")
        arm = result["methods"]["indexed_fresh"]
        self.assertIsNone(arm["exact_state_equal"])
        self.assertEqual(arm["failure"]["kind"], "timeout")
        analysis = analyze_runs((result,), draws=10)
        self.assertEqual(analysis["strata"][0]["methods"]["indexed_fresh"]["outcomes"], {"timeout": 1})

    def test_initial_restart_validation_reads_the_written_artifact(self):
        class CorruptSavedState(RunStore):
            def write_artifact(self, name, data):
                result = super().write_artifact(name, data)
                if name == "original-state.json":
                    (self.attempt / name).write_bytes(b"corrupted saved state")
                return result
        metadata = dict(root_id="r1", request_id="q1", configuration_id="c1", repeat_index=0,
                        phase="software_test", protocol_sha256="b" * 64)
        records = (Record("a", b"[1,1]"), Record("b", b"[0,1]"))
        with tempfile.TemporaryDirectory() as directory:
            result = run_comparison(_DiagnosticDecoder(), exact_service(), records, ("a",),
                                    (Record("eval", b"[1,0]"),),
                                    CorruptSavedState(directory, {"software_fixture": "disk-corruption"}), metadata)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure"]["stage"], "initial_fresh")


def finite_decoder():
    z, a = Q(0), Q(1, 4)
    return CertifiedDecoder(DeterministicDecoder(
        DecoderConfig(2, 2, 1, 2, 1, 2), token_embeddings=((1, 0), (0, 1)),
        position_embeddings=((0, 0), (0, 0)),
        blocks=({"qkv": ((a, z), (z, a), (a, z), (z, a), (a, z), (z, a)),
                 "attn_out": ((a, z), (z, a)), "mlp_up": ((a, z), (z, a)),
                 "mlp_down": ((a, z), (z, a))},), lm_head=((1, z), (z, 1))))


class AdversarialChartTests(unittest.TestCase):
    def test_changed_actual_stage_contract_cannot_keep_target_digest(self):
        decoder = finite_decoder()
        target = build_target(decoder, TargetRecipe(4, bits=3, group_count=1))
        first = target.stages[0]
        for modified in (replace(first, ridge=2), replace(first, normalization=5),
                         replace(first, grids=tuple((Q(-1), Q(0), Q(1)) for _ in first.grids))):
            forged = replace(target, stages=(modified,) + target.stages[1:])
            self.assertNotEqual(forged.digest, target.digest)
            with self.assertRaises(ValueError):
                build_chart(decoder, forged, ChartRecipe(mode="none"))

    def test_coordinate_chart_represents_complete_endpoint_prefix(self):
        decoder = finite_decoder()
        target = build_target(decoder, TargetRecipe(4, bits=3, group_count=1))
        construction = build_chart(decoder, target, ChartRecipe(mode="coordinate"))
        provider = AutomaticResponseProvider(decoder, construction.chart)
        prefix = {stage.stage_id: tuple(tuple(stage.grids[j][(i + j) % 2 * -1]
                                              for j in range(stage.width)) for i in range(len(stage.weights)))
                  for stage in target.stages[:-1]}
        coefficients = provider.coefficients(target.stages[-1].stage_id, prefix)
        self.assertIsNotNone(coefficients)
        self.assertTrue(all(abs(a) <= r for a, r in zip(coefficients, construction.chart.radii)))
        actual = sum(len(row) for direction in construction.chart.directions
                     for matrix in direction.values() for row in matrix)
        self.assertEqual(actual, construction.preview.direction_entries)

    def test_budget_preview_blocks_full_chart_before_dense_construction(self):
        decoder = finite_decoder()
        target = build_target(decoder, TargetRecipe(4, bits=3, group_count=1))
        recipe = ChartRecipe(mode="coordinate", max_rank=1)
        preview = preview_chart(decoder, target, recipe)
        self.assertFalse(preview.feasible)
        self.assertIn("rank", preview.over_budget)
        with self.assertRaises(ValueError):
            build_chart(decoder, target, recipe)

if __name__ == "__main__":
    unittest.main()
