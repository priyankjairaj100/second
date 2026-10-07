"""Provenance rejection tests; these fixtures are not empirical datasets."""
import copy
from pathlib import Path
import tempfile
import unittest

from src.dyadic_quality_validation import (
    MODEL_ORDER, bound_file, capture_generation, load_generation,
    validate_quality_inputs,
)
from src.run_store import canonical_json, digest


def quality_fixture():
    calibration = {"records": [{"id": "train-a", "tokens": list(range(16))},
                                {"id": "train-b", "tokens": list(range(16))}]}
    records = [{"id": f"wikitext2:validation:article-row-{i}", "tokens": list(range(16))}
               for i in range(4)]
    previous = [{"records": [{"id": "wikitext2:validation:article-row-9"}]}]
    evaluation = {"schema": "v14-prospective-finer-grid-quality", "records": records,
                  "model_order": list(MODEL_ORDER),
                  "prior_exclusions": [previous[0]["records"][0]["id"]]}
    evaluation["excluded_from_future_confirmation_ids"] = (
        evaluation["prior_exclusions"] + [record["id"] for record in records])
    cp = {"model.safetensors": "checkpoint-hash", "config.json": "config-hash"}
    calibration_hash = digest(canonical_json(calibration))
    plan = {"records_sha256": calibration_hash, "deleted_record_ids": ["train-a"],
            "checkpoint_sha256": cp}
    progress = {"original_record_ids": ["train-a", "train-b"],
                "deleted_record_ids": ["train-a"], "retained_record_ids": ["train-b"]}
    return [evaluation, calibration, previous, plan, progress,
            copy.deepcopy(plan), copy.deepcopy(progress), cp, calibration_hash]


class QualityInputTests(unittest.TestCase):
    def test_complete_control_accepts_and_model_omission_order_duplication_reject(self):
        validate_quality_inputs(*quality_fixture())
        for order in (list(MODEL_ORDER[:-1]), list(reversed(MODEL_ORDER)), ["base"] * 4):
            fixture = quality_fixture(); fixture[0]["model_order"] = order
            with self.assertRaisesRegex(ValueError, "four-model order"):
                validate_quality_inputs(*fixture)

    def test_duplicate_record_train_split_and_invalid_tokens_reject(self):
        mutations = [lambda e: e["records"].__setitem__(1, e["records"][0]),
                     lambda e: e["records"][0].__setitem__("id", "wikitext2:train:article-row-1"),
                     lambda e: e["records"][0]["tokens"].__setitem__(0, True)]
        for mutate in mutations:
            fixture = quality_fixture(); mutate(fixture[0])
            with self.assertRaises(ValueError):
                validate_quality_inputs(*fixture)

    def test_reused_article_and_missing_exclusions_reject(self):
        fixture = quality_fixture()
        fixture[0]["records"][0]["id"] = fixture[2][0]["records"][0]["id"]
        with self.assertRaisesRegex(ValueError, "earlier quality"):
            validate_quality_inputs(*fixture)
        for field in ("prior_exclusions", "excluded_from_future_confirmation_ids"):
            fixture = quality_fixture(); fixture[0][field] = []
            with self.assertRaisesRegex(ValueError, "exclusion metadata"):
                validate_quality_inputs(*fixture)

    def test_calibration_overlap_membership_checkpoint_and_source_reject(self):
        fixture = quality_fixture()
        fixture[1]["records"][0]["id"] = fixture[0]["records"][0]["id"]
        with self.assertRaisesRegex(ValueError, "overlaps calibration"):
            validate_quality_inputs(*fixture)
        for index, key, value in ((5, "deleted_record_ids", ["train-b"]),
                                  (6, "retained_record_ids", ["train-a"]),
                                  (5, "checkpoint_sha256", {}),
                                  (3, "records_sha256", "other-source")):
            fixture = quality_fixture(); fixture[index][key] = value
            with self.assertRaisesRegex(ValueError, "membership differs"):
                validate_quality_inputs(*fixture)


class GenerationEvidenceTests(unittest.TestCase):
    def make_generation(self, root, kind):
        root = root / kind; (root / "worker").mkdir(parents=True); (root / "outputs").mkdir()
        plan = {"mode": "full_quantization", "grid_axis": "dyadic_row"}
        plan_raw = canonical_json(plan); (root / "plan.json").write_bytes(plan_raw)
        receipt = {"status": "complete", "budget_debit": {"state": "settled"},
                   "outcome": {"status": "complete", "returncode": 0},
                   "worker_identity": {"plan_sha256": digest(plan_raw)}}
        progress = {"status": "complete", "plan_sha256": digest(plan_raw), "target_sha256": "target"}
        if kind == "dyadic":
            stages = [{"stage_id": "stage", "codes_sha256": "codes"}]
            progress.update(full_model_quantization=True, stages=stages)
            (root / "outputs/model-index.json").write_bytes(canonical_json({"target_sha256": "target", "stages": stages}))
        else:
            raw = b"fixture model"; (root / "outputs/model.bin").write_bytes(raw)
            progress.update(complete_model=True, model_artifact={"file": "model.bin", "sha256": digest(raw), "bytes": len(raw)})
        (root / "worker/result.json").write_bytes(canonical_json(receipt))
        (root / "outputs/progress.json").write_bytes(canonical_json(progress))
        return root, receipt, progress

    def test_complete_evidence_accepts_and_unsettled_receipt_rejects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, receipt, _ = self.make_generation(Path(temporary), "dyadic")
            load_generation(capture_generation(root, "dyadic"))
            receipt["budget_debit"]["state"] = "reserved"
            (root / "worker/result.json").write_bytes(canonical_json(receipt))
            with self.assertRaisesRegex(ValueError, "generation is incomplete"):
                capture_generation(root, "dyadic")

    def test_plan_swap_and_receipt_identity_mismatch_reject(self):
        for component in ("plan", "receipt"):
            with tempfile.TemporaryDirectory() as temporary:
                root, receipt, _ = self.make_generation(Path(temporary), "dyadic")
                if component == "plan":
                    (root / "plan.json").write_bytes(canonical_json({"mode": "another-model"}))
                else:
                    receipt["worker_identity"]["plan_sha256"] = "other-plan"
                    (root / "worker/result.json").write_bytes(canonical_json(receipt))
                with self.assertRaisesRegex(ValueError, "another plan"):
                    capture_generation(root, "dyadic")

    def test_post_capture_mutation_and_rebound_power2_artifact_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = self.make_generation(Path(temporary), "power2")
            bundle = capture_generation(root, "power2")
            path = root / "outputs/model.bin"; path.write_bytes(b"swapped model")
            with self.assertRaisesRegex(ValueError, "bound input changed"):
                load_generation(bundle)
            bundle["model"] = bound_file(path)
            with self.assertRaisesRegex(ValueError, "generation artifact"):
                load_generation(bundle)

    def test_partial_and_swapped_dyadic_index_reject(self):
        for partial in (True, False):
            with tempfile.TemporaryDirectory() as temporary:
                root, _, progress = self.make_generation(Path(temporary), "dyadic")
                if partial:
                    progress["full_model_quantization"] = False
                    (root / "outputs/progress.json").write_bytes(canonical_json(progress))
                else:
                    (root / "outputs/model-index.json").write_bytes(canonical_json({"target_sha256": "another-target", "stages": progress["stages"]}))
                with self.assertRaises(ValueError):
                    capture_generation(root, "dyadic")


if __name__ == "__main__":
    unittest.main()
