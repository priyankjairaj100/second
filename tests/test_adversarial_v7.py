"""Independent v7 contract attacks. These fixtures are not research evidence."""
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction as Q
from itertools import product
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch

from src.aggregate_response_service import AggregateRepairService, AggregateState
from src.identity_cache import IdentityCacheService
from src.isolated_comparison import (_child, _child_identity, _verify_completed,
    build_isolated_plan, isolated_source_hashes, run_isolated)
from src.domain_refinement import GramBinding, GramBox, interval_reverse_ldl, signed_loewner_box
from src.exact_core import reverse_ldl
from src.linear_response import linear_record_moments
from src.phase_budget import BudgetExhausted, PhaseBudget
from src.repair_service import JobSpec, Record, StageSpec, _Work, _gram, _is_psd
from src.response_moments import ResponseBasis, record_moments
from src.response_service_adapter import ResponseQuery, ResponseStageContract
from src.run_store import RunStore, canonical_json, digest, strict_json
from src.result_analysis import AnalysisError, analyze_runs
from src.sequence_runner import run_sequence
from tests import test_aggregate_response_service as aggregate_fixtures
from tests.test_result_analysis import record as analysis_record
from tests import test_worker_control as worker_fixtures


class AdversarialIsolatedComparisonTests(unittest.TestCase):
    def fixture(self, root, role):
        service, *_ = aggregate_fixtures.AggregateServiceTests().build()
        records = tuple(aggregate_fixtures.AggregateServiceTests().records())
        state = service.fresh(records).state
        state_path = root / "original.json"
        state_path.write_bytes(state.canonical_bytes())
        manifest_path = root / "manifest.json"
        manifest_path.write_bytes(canonical_json({"deleted_ids": ["a"], "phase": "software_test"}))
        request = {"schema": "isolated-child-request-v1", "role": role,
            "manifest_path": str(manifest_path), "manifest_sha256": digest(manifest_path.read_bytes()),
            "source_sha256": {}, "target_manifest_sha256": "a" * 64,
            "plan_sha256": "b" * 64, "output": str(root / role),
            "original_state": None if role == "setup" else {"path": str(state_path), "sha256": state.digest}}
        path = root / "request.json"
        path.write_bytes(canonical_json(request))
        prepared = {"service": service, "records": records, "service_mode": "certified",
            "metadata": {"target_manifest_sha256": "a" * 64, "chart_sha256": "c" * 64}, "preflight": None}
        return path, request, prepared

    def test_each_child_calls_only_its_requested_method(self):
        import contextlib
        for role in ("setup", "repair", "indexed_fresh", "direct_fresh"):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, request, prepared = self.fixture(root, role)
                allowed = {"setup": {"fresh", "load_state"},
                           "repair": {"repair", "load_state"},
                           "indexed_fresh": {"prepare_index", "indexed_fresh", "load_state"},
                           "direct_fresh": {"fresh"}}[role]
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch("src.isolated_comparison._verify_sources"))
                    stack.enter_context(patch("src.isolated_comparison._run_manifest", return_value=prepared))
                    for method in {"fresh", "repair", "prepare_index", "indexed_fresh", "load_state"} - allowed:
                        stack.enter_context(patch.object(AggregateRepairService, method,
                            side_effect=AssertionError("unrequested method: " + method)))
                    self.assertTrue(_child(path))
                saved = RunStore(request["output"], _child_identity(request)).completed()
                self.assertEqual(saved["outcome"]["status"], "complete")

    def test_child_commit_failure_always_releases_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, request, prepared = self.fixture(root, "setup")
            with patch("src.isolated_comparison._verify_sources"), \
                 patch("src.isolated_comparison._run_manifest", return_value=prepared), \
                 patch.object(RunStore, "finish", side_effect=OSError("declared receipt failure")):
                with self.assertRaisesRegex(OSError, "receipt"):
                    _child(path)
            writer = RunStore(request["output"], _child_identity(request))
            try:
                writer.claim()
            finally:
                writer.close()

    def test_research_pause_blocks_every_worker_and_creates_no_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory, manifest = worker_fixtures.CampaignControlTests().fixture(root, phase="development")
            campaign = strict_json(inventory.read_bytes())
            plan = build_isolated_plan(manifest_path="run.json", manifest=manifest,
                target_manifest_sha256=campaign["entries"][0]["target_manifest_sha256"],
                worker_limits=campaign["worker_limits"], sources=isolated_source_hashes())
            path = root / "isolated.json"
            path.write_bytes(canonical_json(plan))
            with patch("src.isolated_comparison.run_limited") as launch:
                with self.assertRaisesRegex(ValueError, "paused"):
                    run_isolated(path, root / "output")
            launch.assert_not_called()
            self.assertFalse((root / "output").exists())

    def test_resume_verifies_artifacts_of_unsealed_failed_children(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = {"role": "repair", "fixture": "unsealed-child"}
            (root / "requests").mkdir()
            (root / "requests" / "repair.json").write_bytes(canonical_json(request))
            worker_root = root / "workers" / "repair"
            with RunStore(worker_root, {"fixture": "worker"}) as worker:
                worker.write_artifact("failure.json", b"{}")
                worker.finish({"status": "complete", "outcome": {"status": "failed"}})
            child_root = root / "children" / "repair"
            child = RunStore(child_root, _child_identity(request))
            child.claim()
            child.write_artifact("partial-state.json", b"committed partial artifact")
            child.write_status({"status": "failed", "failure": {"kind": "interrupted"}})
            child.close()
            saved = {"children": {"repair": {"request": request,
                "worker_result_sha256": digest((worker_root / "result.json").read_bytes()),
                "child_result_sha256": digest((child_root / "result.json").read_bytes())}}}
            budget = PhaseBudget(root / "budget", identity={}, phase_cpu_seconds={"software_test": 10})
            _verify_completed(root, saved, budget)
            (child.attempt / "partial-state.json").write_bytes(b"changed partial artifact")
            with self.assertRaisesRegex(ValueError, "artifact hash"):
                _verify_completed(root, saved, budget)


class AdversarialConfigurationAnalysisTests(unittest.TestCase):
    def test_one_configuration_cannot_mix_family_tier_or_verifier(self):
        changes = {"service_family": "identity_cache", "response_tier": "quadratic",
                   "verifier_policy": "spectral_or_interval"}
        for field, value in changes.items():
            with self.subTest(field=field):
                first, second = analysis_record("r0"), analysis_record("r1")
                second[field] = value
                with self.assertRaisesRegex(AnalysisError, field):
                    analyze_runs((first, second), draws=10)

    def test_planned_configuration_cannot_silently_default_to_another_policy(self):
        actual = analysis_record("r0")
        planned = dict(actual, verifier_policy="spectral_or_interval")
        with self.assertRaisesRegex(AnalysisError, "verifier_policy"):
            analyze_runs((actual,), planned_runs=(planned,), draws=10)

    def test_new_configuration_fields_reject_unhashable_values(self):
        for field in ("service_family", "response_tier", "verifier_policy"):
            actual = analysis_record("r0")
            actual[field] = []
            with self.subTest(field=field), self.assertRaises(AnalysisError):
                analyze_runs((actual,), draws=10)


class AdversarialIntervalPortfolioTests(unittest.TestCase):
    def test_three_dimensional_mixed_schur_updates_enclose_exact_factors(self):
        binding = GramBinding("fixture", "s", "a" * 64, "b" * 64, Q(1))
        box = GramBox(binding,
            tuple(tuple(Q(4) if i == j else Q(-1, 4) for j in range(3)) for i in range(3)),
            tuple(tuple(Q(5) if i == j else Q(1, 4) for j in range(3)) for i in range(3)),
            ("algebraic-boundary-fixture",))
        factors, pivots = interval_reverse_ldl(box, 1)
        for diagonal in product((Q(4), Q(5)), repeat=3):
            for off in product((Q(-1, 4), Q(1, 4)), repeat=3):
                covariance = ((diagonal[0], off[0], off[1]),
                              (off[0], diagonal[1], off[2]),
                              (off[1], off[2], diagonal[2]))
                # Strict diagonal dominance proves this fixture's ridge premise.
                exact = reverse_ldl(covariance)
                for i in range(3):
                    self.assertLessEqual(pivots[i].lo, exact.t[i])
                    self.assertLessEqual(exact.t[i], pivots[i].hi)
                    for j in range(3):
                        self.assertLessEqual(factors[i][j].lo, exact.L[i][j])
                        self.assertLessEqual(exact.L[i][j], factors[i][j].hi)

    def test_wide_two_dimensional_portfolio_normalizes_once_and_needs_no_replay(self):
        stage = StageSpec("s", (), ((0, 0),), ((-1, 0, 1),) * 2, 1, 7)
        job = JobSpec((stage,), "wide-interval-fixture", "rank-zero-reference", 1)
        response = ResponseBasis("rank-zero-response", 2, 1, True)
        error = ResponseBasis("conservative-finite-error", 1, 3, True)
        contract = ResponseStageContract(response, error, 0)

        def extract(record, stage):
            jets = (((Q(1),), (Q(-1),)),)
            return (linear_record_moments(response, record.record_id, record.content_digest, jets),
                    record_moments(error, record.record_id, record.content_digest,
                                   (((Q(10),),), ((Q(0),),), ((Q(0),),))))

        service = AggregateRepairService(job, lambda record, stage, prefix: ((Q(1),), (Q(-1),)),
            extract, {"s": contract}, lambda context: ResponseQuery(context.binding, (), Q(0), "wide sound bound"),
            provider_id="wide", extractor_id="fixed", verifier_policy="spectral_or_interval")
        records = (Record("a", b"a"), Record("b", b"b"))
        original = service.fresh(records).state
        calls = []

        def capture(binding, center, negative, positive, evidence_id):
            calls.append((binding, center, negative, positive))
            return signed_loewner_box(binding, center, negative, positive, evidence_id)

        with patch("src.aggregate_response_service.signed_loewner_box", capture):
            result = service.repair(original, records[:1], lambda _: self.fail("retained replay"))
        self.assertEqual(result.stages[0].route, "interval_transport_certificate")
        self.assertEqual(result.ledger.count("retained_replay_evaluator_calls"), 0)
        self.assertEqual(len(calls), 1)
        binding, center, negative, positive = calls[0]
        self.assertEqual(binding.normalization, 7)
        self.assertEqual(center, ((Q(8, 7), Q(-1, 7)), (Q(-1, 7), Q(8, 7))))
        retained = service.prepare_index(original, records[:1]).index
        group = retained.groups[0]
        prefix = service._engine._prefix(stage, ())
        _, raw_bounds = service._proposal(group, group.stages[0], stage, prefix, _Work())
        self.assertEqual((negative, positive), tuple(value / 7 for value in raw_bounds))
        self.assertGreaterEqual(negative, 1)
        self.assertEqual(result.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())


class AdversarialQuadraticTests(unittest.TestCase):
    def fixture(self):
        a = (Q(-2, 3), Q(3, 5))
        epsilon = Q(1, 50)
        stage = StageSpec("s", (), ((Q(2, 5), Q(2, 5)),), ((0, 1), (0, 1)), 10, 7)
        job = JobSpec((stage,), "signed-response-fixture", "fixed-jets", 1)
        response_basis = ResponseBasis("signed-response", 2, 3, True)
        error_basis = ResponseBasis("finite-error", 1, 5, True)
        contract = ResponseStageContract(response_basis, error_basis, 4)

        def jets(record):
            n = Q(strict_json(record.payload))
            return (((n, Q(2)), (Q(1), Q(-1))),
                    ((Q(1), Q(3)), (Q(2), Q(-1))),
                    ((Q(-2), Q(1)), (Q(1), Q(4))))

        def target(record, stage, prefix):
            values = jets(record)
            return tuple(tuple(values[0][i][j] + sum(a[t] * values[t + 1][i][j] for t in range(2))
                               + (epsilon if i == j else -epsilon) for j in range(2)) for i in range(2))

        def extract(record, stage):
            response = record_moments(response_basis, record.record_id, record.content_digest, jets(record))
            errors = (((2 * epsilon,),),) + (((Q(0),),),) * 4
            error = record_moments(error_basis, record.record_id, record.content_digest, errors)
            return response, error

        service = AggregateRepairService(job, target, extract, {"s": contract},
            lambda context: ResponseQuery(context.binding, a, Q(0), "declared exact signed response"),
            provider_id="signed-response", extractor_id="fixed-jets", response_tier="quadratic")
        records = (Record("r0", b"1"), Record("r1", b"2"))
        return service, records

    def test_signed_multidirection_cross_terms_and_error_bound_enclose_actual_gram(self):
        service, records = self.fixture()
        state = service.fresh(records).state
        stage = service.job.stages[0]
        prefix = service._engine._prefix(stage, state.model)
        actuals = [_gram(service.evaluator(record, stage, prefix), _Work()) for record in records]
        actual = tuple(tuple(sum((matrix[i][j] for matrix in actuals), Q(0)) for j in range(2)) for i in range(2))
        for mode in ("certified", "fixed_reference"):
            with self.subTest(mode=mode):
                raw, bounds = service._proposal(state.groups[0], state.groups[0].stages[0], stage,
                                               prefix, _Work(), mode)
                self.assertGreater(bounds[0], 0)
                for direction in (-1, 1):
                    difference = tuple(tuple(direction * (actual[i][j] - raw[i][j])
                                       + (bounds[0] if i == j else 0) for j in range(2)) for i in range(2))
                    self.assertTrue(_is_psd(difference))
        repaired = service.repair(state, records[:1], {r.record_id: r for r in records}.__getitem__)
        self.assertEqual(repaired.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())

    def test_quadratic_nested_index_rejects_duplicate_keys_and_record_payloads(self):
        service, records = self.fixture()
        state = service.fresh(records).state
        data = strict_json(state.canonical_bytes())
        encoded = data["groups"][0]["stages"][0]["response"]
        data["groups"][0]["stages"][0]["response"] = encoded.replace('"records":[]', '"records":[],"records":[]')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            AggregateState.from_canonical_bytes(canonical_json(data))
        data = strict_json(state.canonical_bytes())
        nested = json.loads(encoded)
        nested["records"] = [{"record_id": "r0", "source_digest": records[0].content_digest,
                              "columns": 2, "payload_digest": "0" * 64}]
        data["groups"][0]["stages"][0]["response"] = canonical_json(nested).decode("ascii")
        with self.assertRaisesRegex(ValueError, "per-record"):
            AggregateState.from_canonical_bytes(canonical_json(data))


class AdversarialIdentityCacheTests(unittest.TestCase):
    def fixture(self):
        stages = (
            StageSpec("a", (), ((Q(2, 5), Q(2, 5)),), ((0, 1), (0, 1)), 1, 1),
            StageSpec("b", ("a",), ((Q(0),),), ((0, 1),), 1, 1),
            StageSpec("c", ("b",), ((Q(2, 5), Q(2, 5)),), ((0, 1), (0, 1)), 1, 1),
        )
        job = JobSpec(stages, "transitive-cache-fixture", "fixed-reference", 1)
        calls = []

        def evaluate(record, stage, prefix):
            calls.append((record.record_id, stage.stage_id))
            if stage.stage_id == "b":
                return ((Q(1),),)
            first, second = strict_json(record.payload)
            delta = 0 if stage.stage_id == "a" else prefix.as_mapping()["a"][0][1]
            return ((Q(first) + delta,), (Q(second),))

        service = IdentityCacheService(job, evaluate)
        records = (Record("r0", b"[1,1]"), Record("r1", b"[0,1]"), Record("r2", b"[0,0]"))
        return service, records, calls

    def test_transitive_change_replays_even_when_direct_parent_code_stays_equal(self):
        service, records, calls = self.fixture()
        original = service.fresh(records).state
        source = {r.record_id: r for r in records}.__getitem__
        calls.clear()
        repaired = service.repair(original, records[:1], source, expected_digest=original.digest)
        self.assertNotEqual(original.model[0], repaired.state.model[0])
        self.assertEqual(original.model[1], repaired.state.model[1])
        self.assertEqual(repaired.stages[2].route, "changed_ancestor_replay")
        self.assertEqual(repaired.stages[2].retained_evaluations, 2)
        self.assertIn(("r1", "c"), calls)
        self.assertEqual(repaired.state.canonical_bytes(), service.fresh(records[1:]).state.canonical_bytes())

    def test_second_deletion_uses_refreshed_prefix_and_equals_combined_deletion(self):
        service, records, calls = self.fixture()
        original = service.fresh(records).state
        source = {r.record_id: r for r in records}.__getitem__
        first = service.repair(original, records[:1], source, expected_digest=original.digest).state
        calls.clear()
        second = service.repair(first, records[1:2], source, expected_digest=first.digest)
        self.assertTrue(all(a.route == "old_ancestor_identity" for a in second.stages))
        self.assertFalse(any(record_id == "r2" for record_id, _ in calls))
        combined = service.repair(original, records[:2], source, expected_digest=original.digest).state
        fresh = service.fresh(records[2:]).state
        self.assertEqual(second.state.canonical_bytes(), combined.canonical_bytes())
        self.assertEqual(combined.canonical_bytes(), fresh.canonical_bytes())


class AdversarialSequenceTests(unittest.TestCase):
    def fixture(self):
        service, *_ = aggregate_fixtures.AggregateServiceTests().build()
        records = tuple(aggregate_fixtures.AggregateServiceTests().records())
        decoder = SimpleNamespace(decode_payload=lambda _: (0, 1),
            logits=lambda tokens, prefix=None: ((0.0, 0.0), (0.0, 0.0)))
        heldout = (Record("heldout", b"[0,0]"),)
        metadata = {"sequence_id": "fixture", "root_id": "r", "configuration_id": "c",
                    "repeat_index": 0, "phase": "software_test", "protocol_sha256": "0" * 64}
        return decoder, service, records, heldout, metadata

    def test_initial_plan_write_failure_releases_writer(self):
        decoder, service, records, heldout, metadata = self.fixture()
        original_write = RunStore.write_artifact

        def failing_write(store, name, payload):
            if name == "plan.json":
                raise OSError("declared plan output failure")
            return original_write(store, name, payload)

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(RunStore, "write_artifact", failing_write):
                try:
                    run_sequence(decoder, service, records, [{"request_id": "q", "deleted_ids": ["a"]}],
                                 heldout, directory, metadata)
                except OSError:
                    pass
            root = Path(directory)
            identity = strict_json((root / "identity.json").read_bytes())
            writer = RunStore(directory, identity)
            try:
                writer.claim()
            finally:
                writer.close()

    def test_failed_step_resume_preserves_predecessor_and_uses_committed_state(self):
        decoder, service, records, heldout, metadata = self.fixture()
        schedule = [{"request_id": "q0", "deleted_ids": ["a"]},
                    {"request_id": "q1", "deleted_ids": ["b"]}]
        original_repair = AggregateRepairService.repair

        def failing_repair(instance, state, deleted, source, **kwargs):
            deleted = tuple(deleted)
            if {r.record_id for r in deleted} == {"b"}:
                raise TimeoutError("declared second-step failure")
            return original_repair(instance, state, deleted, source, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(AggregateRepairService, "repair", failing_repair):
                failed = run_sequence(decoder, service, records, schedule, heldout, directory, metadata)
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["steps"][0]["status"], "complete")
            self.assertEqual(failed["steps"][1]["status"], "failed")
            first_hash = failed["steps"][0]["result_sha256"]
            resumed = run_sequence(decoder, service, records, schedule, heldout, directory, metadata)
            self.assertEqual(resumed["status"], "complete", resumed.get("failure"))
            self.assertEqual(resumed["steps"][0]["result_sha256"], first_hash)
            self.assertEqual(resumed["steps"][1]["predecessor_state_sha256"], resumed["steps"][0]["state_sha256"])
            self.assertEqual(resumed["final_retained_ids"], ["c"])
            root = Path(directory)
            self.assertEqual(len(list((root / "initial").glob("attempt-*"))), 1)
            self.assertEqual(len(list((root / "step-0000").glob("attempt-*"))), 1)
            self.assertEqual(len(list((root / "step-0001").glob("attempt-*"))), 2)


class AdversarialPhaseBudgetTests(unittest.TestCase):
    def test_snapshot_cannot_raise_the_admission_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = PhaseBudget(directory, identity={"fixture": "detached_snapshot"},
                                 phase_cpu_seconds={"software_test": 10})
            budget.reserve("software_test", "first", 6)
            snapshot = budget.snapshot()
            snapshot["phase_cpu_seconds"]["software_test"] = 1000
            with self.assertRaises(BudgetExhausted):
                budget.reserve("software_test", "second", 6)
            self.assertEqual(budget.snapshot()["phase_cpu_seconds"], {"software_test": 10})

    def test_independent_handles_serialize_concurrent_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            gate = threading.Barrier(8)

            def attempt(index):
                budget = PhaseBudget(directory, identity={"fixture": "concurrency"},
                                     phase_cpu_seconds={"software_test": 10})
                gate.wait(timeout=10)
                try:
                    budget.reserve("software_test", str(index), 3)
                    return True
                except BudgetExhausted:
                    return False

            with ThreadPoolExecutor(max_workers=8) as pool:
                admitted = list(pool.map(attempt, range(8)))
            self.assertEqual(sum(admitted), 3)
            budget = PhaseBudget(directory, identity={"fixture": "concurrency"},
                                 phase_cpu_seconds={"software_test": 10})
            self.assertEqual(budget.snapshot()["charged_cpu_seconds"], {"software_test": 9})

    def test_interrupted_reservation_survives_restart_and_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            arguments = {"identity": {"fixture": "interruption"},
                         "phase_cpu_seconds": {"software_test": 8}}
            PhaseBudget(directory, **arguments).reserve("software_test", "interrupted", 6)
            resumed = PhaseBudget(directory, **arguments)
            with self.assertRaises(ValueError):
                resumed.reserve("software_test", "interrupted", 6)
            with self.assertRaises(BudgetExhausted):
                resumed.reserve("software_test", "retry", 3)
            self.assertEqual(resumed.snapshot()["charged_cpu_seconds"]["software_test"], 6)
            resumed.settle("interrupted", 1_000_000_001)
            resumed.reserve("software_test", "retry", 6)
            self.assertEqual(resumed.snapshot()["charged_cpu_seconds"]["software_test"], 8)


if __name__ == "__main__":
    unittest.main()
