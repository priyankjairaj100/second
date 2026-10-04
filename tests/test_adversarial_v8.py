"""Independent v8 contract attacks. These are software fixtures only."""
from contextlib import ExitStack
from fractions import Fraction as Q
from pathlib import Path
from types import SimpleNamespace
import os
import tempfile
import unittest
from unittest.mock import patch

from src.run_store import RunStore, canonical_json, digest, strict_json
from src.service_telemetry import DiagnosticLimits, ServiceTelemetry, diagnostic, operation


class AdversarialDiagnosticTests(unittest.TestCase):
    def test_nested_categories_reserve_their_counter_capacity_on_entry(self):
        collector = ServiceTelemetry(diagnostic_limits=DiagnosticLimits(max_counter_keys=1))
        with ExitStack() as stack:
            for number in range(20):
                stack.enter_context(collector.span("nested-" + str(number)))
        timings = collector.payload()["timings"]
        self.assertLessEqual(len(timings), 2)  # One named category plus one explicit overflow bucket.
        self.assertEqual(sum(row["calls"] for row in timings.values()), 20)

    def test_large_rational_diagnostics_never_serialize_full_integers(self):
        collector = ServiceTelemetry(diagnostic_limits=DiagnosticLimits(max_integer_bits=32))
        collector.diagnostic("s", "bound", values={"radius": Q(1 << 100_000, 3)})
        payload = collector.payload()
        encoded = payload["certificate_funnel"]["stages"][0]["events"]["bound"]["first"]["radius"]
        self.assertEqual(encoded["encoding"], "rational_magnitude")
        self.assertEqual(encoded["numerator_bits"], 100_001)
        self.assertNotIn("numerator", encoded)
        self.assertLess(len(canonical_json(payload)), 10_000)

    def test_diagnostic_failure_does_not_abort_model_and_failed_operations_remain_failed(self):
        def bad_builder(_):
            raise ArithmeticError("declared diagnostic encoding fixture")

        @operation
        def succeeds():
            diagnostic("s", "stage_started")
            diagnostic("s", "bound", build=bad_builder)
            diagnostic("s", "stage_completed")
            return SimpleNamespace(state=SimpleNamespace(model=("exact",)))

        @operation
        def fails():
            diagnostic("later", "stage_started")
            raise ArithmeticError("declared evaluator failure")

        collector = ServiceTelemetry()
        self.assertEqual(succeeds(telemetry=collector).state.model, ("exact",))
        with self.assertRaises(ArithmeticError):
            fails(telemetry=collector)
        funnel = collector.payload()["certificate_funnel"]
        self.assertEqual(funnel["counters"]["encoding_failures"], 1)
        self.assertEqual([entry["status"] for entry in funnel["operations"]], ["complete", "failed"])
        self.assertEqual([entry["produced_complete_model"] for entry in funnel["operations"]], [True, False])
        self.assertEqual(funnel["stages"][-1]["status"], "failed")


class AdversarialArithmeticAuditTests(unittest.TestCase):
    def test_transient_endpoint_and_exception_restored_phase_remain_observable(self):
        from src.arithmetic_audit import ArithmeticAudit
        with ArithmeticAudit(max_attributions=2) as audit:
            with audit.phase("outer"):
                try:
                    with audit.phase("temporary"):
                        value = Q((1 << 12_345) + 1, 7)
                        del value
                        raise LookupError("abandon temporary arithmetic")
                except LookupError:
                    pass
                final = Q(1, 2)
        payload = audit.payload()
        self.assertEqual(final, Q(1, 2))
        self.assertEqual(payload["constructed_fraction_endpoints"]["fraction_objects"], 2)
        self.assertEqual(payload["constructed_fraction_endpoints"]["maximum_numerator_bits"], 12_346)
        self.assertEqual(payload["by_phase"]["outer"]["fraction_objects"], 1)
        self.assertEqual(payload["by_phase"]["temporary"]["fraction_objects"], 1)
        self.assertFalse(payload["clean_latency_eligible"])

    def test_partial_runner_output_cannot_be_reported_as_a_fresh_arithmetic_audit(self):
        from src.arithmetic_audit import audit_local_run
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "partial"
            output.mkdir()
            (output / "started.txt").write_bytes(b"earlier arithmetic was not observed")
            with self.assertRaisesRegex(FileExistsError, "fresh runner"):
                audit_local_run("experiment", root / "does-not-exist.json", output, root / "audit.json")
            self.assertFalse((root / "audit.json").exists())


class AdversarialModelFreshTests(unittest.TestCase):
    def test_resume_revalidates_source_identity_and_used_calibration_bytes(self):
        from src.model_fresh import run_model_fresh
        from src.experiment_inventory import source_hashes
        from tests import test_isolated_comparison_v7 as fixtures
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, manifest = fixtures.IsolatedComparisonTests().fixture(root)
            path = root / "run.json"
            result = run_model_fresh(path, root / "model")
            self.assertEqual(result["outcome"]["status"], "complete")
            sources = source_hashes(Path(__file__).resolve().parents[1])
            sources[next(iter(sources))] = "0" * 64
            with patch("src.experiment_inventory.source_hashes", return_value=sources):
                with self.assertRaisesRegex(ValueError, "identity"):
                    run_model_fresh(path, root / "model")
            calibration = root / manifest["calibration"]["path"]
            calibration.write_bytes(calibration.read_bytes() + b" ")
            with patch("src.model_fresh.fresh_model", side_effect=AssertionError("must not recompute")):
                with self.assertRaisesRegex(ValueError, "hash"):
                    run_model_fresh(path, root / "model")
            self.assertEqual(strict_json((root / "model" / "result.json").read_bytes()), result)

    def test_unadmitted_model_only_feasibility_fails_before_loading_or_output(self):
        from src.model_fresh import run_model_fresh
        from tests import test_isolated_campaign_v8 as fixtures
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixtures.IsolatedCampaignTests().fixture(root, phase="feasibility")
            with patch.dict(os.environ):
                os.environ.pop("CALIBRATION_PHASE_CPU_ADMISSION", None)
                with patch("src.experiment_runner._run_manifest", side_effect=AssertionError("checkpoint loaded")) as prepare:
                    with self.assertRaisesRegex(ValueError, "phase CPU admission"):
                        run_model_fresh(root / "run.json", root / "out")
                prepare.assert_not_called()
            self.assertFalse((root / "out").exists())


@unittest.skipUnless(hasattr(os, "sched_setaffinity"), "Linux workers required")
class AdversarialInventoryTests(unittest.TestCase):
    def test_confirmation_child_cannot_replace_the_frozen_target_binding(self):
        from src.isolated_comparison import _child
        from tests import test_isolated_campaign_v8 as fixtures
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inventory_path, inventory = fixtures.IsolatedCampaignTests().fixture(root, phase="confirmation")
            entry = inventory["entries"][0]
            request = {"schema": "isolated-child-request-v1", "role": "repair",
                "manifest_path": str(root / "run.json"),
                "manifest_sha256": digest((root / "run.json").read_bytes()),
                "source_sha256": inventory["source_sha256"],
                "target_manifest_sha256": "f" * 64,
                "plan_sha256": entry["isolated_plan_sha256"],
                "output": str(root / "child"), "original_state": None,
                "inventory": {"path": str(inventory_path), "sha256": digest(inventory_path.read_bytes()),
                              "run_id": entry["run_id"], "plan_path": str(root / "plan.json")}}
            request_path = root / "child-request.json"
            request_path.write_bytes(canonical_json(request))
            with patch("src.isolated_comparison._run_manifest", side_effect=AssertionError("checkpoint loaded")) as prepare:
                self.assertFalse(_child(request_path))
            prepare.assert_not_called()
            receipt = strict_json((root / "child" / "result.json").read_bytes())
            self.assertEqual(receipt["outcome"]["status"], "failed")
            self.assertIn("inventory binding", receipt["outcome"]["failure"]["message"])

    def test_direct_research_child_cannot_bypass_the_parent_cpu_admission(self):
        from src.isolated_comparison import _child
        from tests import test_isolated_campaign_v8 as fixtures
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, inventory = fixtures.IsolatedCampaignTests().fixture(root, phase="feasibility")
            entry = inventory["entries"][0]
            request = {"schema": "isolated-child-request-v1", "role": "setup",
                "manifest_path": str(root / "run.json"),
                "manifest_sha256": digest((root / "run.json").read_bytes()),
                "source_sha256": inventory["source_sha256"],
                "target_manifest_sha256": entry["target_manifest_sha256"],
                "plan_sha256": entry["isolated_plan_sha256"],
                "output": str(root / "child"), "original_state": None}
            request_path = root / "child-request.json"
            request_path.write_bytes(canonical_json(request))
            with patch.dict(os.environ):
                os.environ.pop("CALIBRATION_PHASE_CPU_ADMISSION", None)
                with patch("src.isolated_comparison._run_manifest", side_effect=AssertionError("checkpoint loaded")) as prepare:
                    self.assertFalse(_child(request_path))
                prepare.assert_not_called()
            receipt = strict_json((root / "child" / "result.json").read_bytes())
            self.assertEqual(receipt["outcome"]["status"], "failed")
            self.assertIn("phase CPU admission", receipt["outcome"]["failure"]["message"])

    def test_sequence_resume_checks_request_files_outside_the_sequence_archive(self):
        from src.sequence_campaign import run_sequence_campaign
        from tests import test_sequence_campaign_v8 as fixtures
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, _, _ = fixtures.fixture(root)
            result = run_sequence_campaign(path, root / "out")
            self.assertEqual(result["outcome"], "complete", result["runs"])
            request = root / "out" / "requests" / "run0.json"
            request.write_bytes(request.read_bytes() + b" ")
            with patch("src.sequence_campaign.run_limited", side_effect=AssertionError("resume launched worker")):
                with self.assertRaisesRegex(ValueError, "request"):
                    run_sequence_campaign(path, root / "out")


@unittest.skipUnless(hasattr(os, "sched_setaffinity"), "Linux workers required")
class AdversarialTransactionTests(unittest.TestCase):
    def test_reused_timing_requires_unchanged_bound_inputs_outside_output_tree(self):
        from src.transaction_timing import measure_command, transaction_source_hashes
        from tests import test_transaction_timing_v8 as fixtures
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inputs = root / "input.json"
            inputs.write_bytes(b'{"pinned":true}')
            fixture = fixtures.TransactionTimingTests()
            options = dict(identity={"fixture": True}, source_sha256=transaction_source_hashes(),
                           input_sha256={str(inputs): digest(inputs.read_bytes())})
            command = fixture.command(root / "transaction")
            result = measure_command(command, root / "transaction", root / "observer", fixture.limits(), **options)
            self.assertTrue(result["new_latency_observation"], result)
            inputs.write_bytes(b'{"pinned":false}')
            with patch("src.transaction_timing.run_limited", side_effect=AssertionError("resume launched worker")):
                with self.assertRaisesRegex(ValueError, "input hash"):
                    measure_command(command, root / "transaction", root / "observer", fixture.limits(), **options)

    def test_successful_quality_child_cannot_be_mislabelled_as_canonical_state_transaction(self):
        from src.transaction_timing import _validate_output
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "child"
            store = RunStore(root, {"fixture": True})
            store.claim()
            store.write_artifact("quality.json", b"{}")
            store.finish({"schema": "isolated-child-result-v1", "status": "complete", "role": "quality",
                          "outcome": {"status": "complete"}})
            store.close()
            with self.assertRaisesRegex(ValueError, "output contract differs"):
                _validate_output(root, "canonical_state")


if __name__ == "__main__":
    unittest.main()
