"""Mathematical software fixtures. No research datasets or results occur here."""
from copy import deepcopy
from fractions import Fraction as Q
from types import SimpleNamespace
import unittest

from src.exact_core import sequential_oracle
from src.experiment_inventory import (analysis_plan, build_campaign, manifest_binding,
                                     validate_campaign)
from src.repair_service import JobSpec, Record, StageOutput, StageSpec
from src.request_workload import (METHODS, PRIMARY_REQUESTS, SCORE_RULE, SeedStream,
                                  _inverse_from_factors, _sensitivity, build_workload,
                                  counterbalanced_orders, expand_document_deletion,
                                  prepare_original_scores, sample_roots, source_withdrawal_request,
                                  validate_phase_pools)
from src.run_store import canonical_json, digest


def fixture_scores(ids):
    return {"schema": "calibration-original-scores-v1", "rule": SCORE_RULE,
            "uses_deletion_outcomes": False, "prepared_records_sha256": "1"*64,
            "original_state_sha256": "2"*64,
            "records": [{"record_id": rid, "concentration": [Q(i,len(ids)).numerator, Q(i,len(ids)).denominator],
                         "difficulty": [i*i, 1]} for i, rid in enumerate(ids)]}


def fixture_workload():
    ids = [f"record-{i:02d}" for i in range(16)]
    return build_workload(ids, root_id="software-root", seed=10, scores=fixture_scores(ids),
                          prepared_records_sha256="1"*64, original_state_sha256="2"*64)


def fixture_campaign():
    workload = fixture_workload()
    manifests = []
    for request in workload["requests"][:6]:
        orders = counterbalanced_orders(seed=workload["seed"], root_id=workload["root_id"],
                                        request_id=request["request_id"], repeats=3)
        for repeat, order in enumerate(orders):
            manifest = {"schema": "calibration-run-v1", "root_id": workload["root_id"],
                        "request_id": request["request_id"], "configuration_id": "fixture",
                        "repeat_index": repeat, "phase": "software_test", "method_order": order,
                        "deleted_ids": request["deleted_ids"], "protocol": {"path": "protocol.json", "sha256": "3"*64},
                        "calibration": {"path": "records.json", "sha256": "1"*64}}
            manifests.append({"manifest": manifest, "manifest_path": f"manifests/run-{len(manifests)}.json",
                              "target_manifest_sha256": "4"*64})
    limits = {"wall_seconds": 10, "cpu_seconds": 10, "address_space_bytes": 2**30,
              "threads": 1, "affinity_cpus": [0], "termination_grace_seconds": 0, "file_size_bytes": 2**20}
    return build_campaign(campaign_id="software-fixture", protocol_path="protocol.json",
                          worker_limits=limits, manifests=manifests, workloads=[workload],
                          source_sha256={"src/fixture.py": "5"*64})


class WorkloadTests(unittest.TestCase):
    def test_exact_inverse_and_margin_cases(self):
        trace = sequential_oracle(((Q(1,4), Q(3,5)),), ((3,1),(1,2)), ((0,1),(0,1)))
        self.assertEqual(_inverse_from_factors(trace.factors), ((Q(2,5),Q(-1,5)),(Q(-1,5),Q(3,5))))
        self.assertGreater(_sensitivity(trace), 0)
        tied = sequential_oracle(((Q(1,4),Q(1,2)),), ((1,0),(0,1)), ((0,1),(0,1)))
        self.assertIsNone(_sensitivity(tied))
        zero = sequential_oracle(((0,Q(1,2)),), ((1,0),(0,1)), ((0,1),(0,1)))
        self.assertEqual(_sensitivity(zero), 0)
        singleton = sequential_oracle(((Q(1,4),Q(1,2)),), ((1,0),(0,1)), ((0,),(0,)))
        self.assertEqual(_sensitivity(singleton), 0)

    def test_original_score_producer_checks_model_and_content(self):
        stage = StageSpec("s", (), ((Q(1,4),Q(3,5)),), ((0,1),(0,1)), Q(1), Q(1))
        job = JobSpec((stage,), "software-evaluator", "software-reference")
        records = (Record("a",b"a"), Record("b",b"b"))
        features = {"a": ((Q(1),),(Q(0),)), "b": ((Q(0),),(Q(2),))}
        calls = []
        def evaluate(record, spec, prefix):
            calls.append((record.record_id, spec.stage_id, prefix.digest))
            return features[record.record_id]
        model = StageOutput("s", sequential_oracle(stage.weights, ((2,0),(0,5)), stage.grids).codes)
        state = SimpleNamespace(retained_ids=("a","b"),
                                records=tuple(SimpleNamespace(record_id=r.record_id, content_digest=r.content_digest) for r in records),
                                manifest_digest="s"*64, model=(model,), digest="2"*64)
        service = SimpleNamespace(job=job, evaluator=evaluate, manifest_digest="s"*64)
        scores = prepare_original_scores(service, state, records, prepared_records_sha256="1"*64,
                                          source_sha256={"src/fixture.py": "3"*64})
        self.assertEqual(len(calls), 2)
        self.assertEqual(scores["records"][0]["concentration"], [1,5])
        self.assertEqual(scores["records"][1]["concentration"], [4,5])
        self.assertEqual(scores["stages"][0]["records"][0]["leverage"], [1,2])
        self.assertEqual(scores["stages"][0]["records"][1]["leverage"], [4,5])
        self.assertFalse(scores["uses_deletion_outcomes"])
        self.assertGreater(scores["preparation"]["wall_time_ns"], 0)
        with self.assertRaises(ValueError):
            prepare_original_scores(service, state, (Record("a",b"changed"), records[1]),
                                    prepared_records_sha256="1"*64, source_sha256={"x": "3"*64})
        state.model = (StageOutput("s", ((1,1),)),)
        with self.assertRaises(ValueError):
            prepare_original_scores(service, state, records, prepared_records_sha256="1"*64,
                                    source_sha256={"x": "3"*64})

    def test_original_scorer_includes_transitive_ancestors(self):
        stages = tuple(StageSpec(name, dependencies, ((0,),), ((0,1),), Q(1), Q(1))
                       for name, dependencies in (("a",()), ("b",("a",)), ("c",("b",))))
        job = JobSpec(stages,"software", "software")
        record = Record("r",b"r")
        observed = {}
        def evaluate(record, stage, prefix):
            observed[stage.stage_id] = tuple(prefix.as_mapping())
            return ((Q(1),),)
        service = SimpleNamespace(job=job, evaluator=evaluate, manifest_digest="1"*64)
        state = SimpleNamespace(retained_ids=("r",), records=(SimpleNamespace(record_id="r",content_digest=record.content_digest),),
                                model=tuple(StageOutput(stage.stage_id,((0,),)) for stage in stages),
                                manifest_digest="1"*64,digest="2"*64)
        prepare_original_scores(service,state,(record,),prepared_records_sha256="3"*64,source_sha256={"x":"4"*64})
        self.assertEqual(observed["c"],("a","b"))

    def test_requests_are_deterministic_sized_disjoint_and_scored(self):
        workload = fixture_workload()
        self.assertEqual(workload, fixture_workload())
        requests = {row["request_id"]: row for row in workload["requests"]}
        self.assertEqual([len(requests[name]["deleted_ids"]) for name in PRIMARY_REQUESTS],[1,1,4,1,1,1])
        self.assertEqual(requests["concentrated_1_of_16"]["deleted_ids"],["record-15"])
        self.assertEqual(requests["difficult_1_of_16"]["deleted_ids"],["record-15"])
        sequence = [requests[f"sequential_1_of_16_step_{i}"] for i in (1,2,3)]
        self.assertEqual(len(set(rid for row in sequence for rid in row["deleted_ids"])),3)
        self.assertEqual(sequence[-1]["cumulative_deleted_ids"],requests["sequential_combined"]["deleted_ids"])
        self.assertIsNotNone(requests["complete_deletion"]["blocked_reason"])
        self.assertEqual(requests["empty_deletion"]["analysis_group"],"correctness_control")

    def test_infinite_score_and_lexicographic_ties(self):
        ids = ["z", "a", "b"]
        scores = fixture_scores(ids)
        for row in scores["records"]:
            row["concentration"]=[1,3]
            row["difficulty"]="infinity"
        workload = build_workload(ids,root_id="fixture",seed=0,scores=scores,
                                  prepared_records_sha256="1"*64,original_state_sha256="2"*64)
        self.assertEqual(workload["requests"][4]["deleted_ids"],["a"])
        self.assertEqual(workload["requests"][5]["deleted_ids"],["a"])
        scores["uses_deletion_outcomes"]=True
        with self.assertRaises(ValueError):
            build_workload(ids,root_id="fixture",seed=0,scores=scores,
                           prepared_records_sha256="1"*64,original_state_sha256="2"*64)

    def test_root_sampling_and_phase_boundaries(self):
        draws = sample_roots([str(i) for i in range(20)],count=3,size=8,seed=7,phase="development")
        self.assertEqual(draws,sample_roots([str(i) for i in range(20)],count=3,size=8,seed=7,phase="development"))
        self.assertTrue(all(len(set(root["record_ids"]))==8 for root in draws["roots"]))
        pools = {phase:[{"record_id":phase,"document_id":phase,"normalized_text_sha256":str(i)*64,"payload_sha256":str(i+3)*64}]
                 for i,phase in enumerate(("development","confirmation","evaluation"),1)}
        self.assertEqual(len(validate_phase_pools(pools)),64)
        pools["evaluation"][0]["normalized_text_sha256"]="1"*64
        with self.assertRaises(ValueError): validate_phase_pools(pools)

    def test_phase_pool_rejects_token_leakage_and_inconsistent_document_hash(self):
        pools = {phase:[{"record_id":phase,"document_id":phase,"normalized_text_sha256":str(i)*64,"payload_sha256":str(i+3)*64}]
                 for i,phase in enumerate(("development","confirmation","evaluation"),1)}
        changed=deepcopy(pools)
        changed["evaluation"][0]["payload_sha256"]=changed["development"][0]["payload_sha256"]
        with self.assertRaises(ValueError): validate_phase_pools(changed)
        changed=deepcopy(pools)
        extra=dict(changed["development"][0],record_id="other-chunk",normalized_text_sha256="a"*64)
        changed["development"].append(extra)
        with self.assertRaises(ValueError): validate_phase_pools(changed)

    def test_document_withdrawal_expands_all_chunks(self):
        self.assertEqual(expand_document_deletion({"a:0":"a","b:0":"b","a:1":"a"},["a"]),["a:0","a:1"])
        with self.assertRaises(ValueError): expand_document_deletion({"a:0":"a"},["missing"])

    def test_source_withdrawal_uses_bound_complete_membership(self):
        sources={"a":"source-1", "b":"source-2", "c":"source-1"}
        result=source_withdrawal_request(list(sources),sources,root_id="r",seed=10,
                                         source_metadata_sha256=digest(canonical_json(sources)))
        chosen=result["selected_source_id"]
        self.assertEqual(result["deleted_ids"],[rid for rid in sources if sources[rid]==chosen])
        self.assertLess(len(result["deleted_ids"]),3)
        with self.assertRaises(ValueError):
            source_withdrawal_request(list(sources),sources,root_id="r",seed=10,source_metadata_sha256="0"*64)
        single={"a":"one","b":"one"}
        with self.assertRaises(ValueError):
            source_withdrawal_request(list(single),single,root_id="r",seed=10,
                                      source_metadata_sha256=digest(canonical_json(single)))

    def test_method_orders_balance_positions(self):
        orders = counterbalanced_orders(seed=10,root_id="r",request_id="q",repeats=6)
        for start in (0,3):
            for position in range(3):
                self.assertEqual({row[position] for row in orders[start:start+3]},set(METHODS))
        self.assertEqual(len({tuple(order) for order in orders}),6)
        with self.assertRaises(ValueError): SeedStream(True,"bad")


class InventoryTests(unittest.TestCase):
    def test_inventory_roundtrip_and_analysis_resolution(self):
        campaign=fixture_campaign()
        self.assertEqual(validate_campaign(campaign),campaign)
        plan=analysis_plan(campaign,protocol_sha256="a"*64)
        self.assertEqual(len(plan["planned_runs"]),18)
        self.assertEqual({row["protocol_sha256"] for row in plan["planned_runs"]},{"a"*64})
        self.assertTrue(all(row["request_id"] in PRIMARY_REQUESTS for row in plan["planned_runs"]))
        self.assertEqual(plan["campaign_sha256"],digest(canonical_json(campaign)))

    def test_binding_excludes_only_protocol_digest(self):
        manifest=fixture_campaign()["entries"][0]["manifest_payload"]
        original=manifest_binding(manifest)
        manifest["protocol"]["sha256"]="b"*64
        self.assertEqual(manifest_binding(manifest),original)
        manifest["protocol"]["path"]="changed.json"
        self.assertNotEqual(manifest_binding(manifest),original)

    def test_inventory_rejects_tampered_membership_and_missing_repeat(self):
        campaign=fixture_campaign()
        changed=deepcopy(campaign)
        changed["entries"][0]["manifest_payload"]["deleted_ids"]=["record-15"]
        changed["entries"][0]["manifest_binding_sha256"]=manifest_binding(changed["entries"][0]["manifest_payload"])
        with self.assertRaises(ValueError): validate_campaign(changed)
        changed=deepcopy(campaign)
        del changed["entries"][0]
        with self.assertRaises(ValueError): validate_campaign(changed)
        changed=deepcopy(campaign)
        changed["workloads"][0]["requests"][0]["deleted_ids"]=["record-15"]
        with self.assertRaises(ValueError): validate_campaign(changed)

    def test_inventory_rejects_duplicates_and_unbalanced_order(self):
        campaign=fixture_campaign()
        changed=deepcopy(campaign)
        changed["entries"].append(deepcopy(changed["entries"][0]))
        with self.assertRaises(ValueError): validate_campaign(changed)
        changed=deepcopy(campaign)
        row=changed["entries"][0]
        row["method_order"]=list(reversed(row["method_order"]))
        row["manifest_payload"]["method_order"]=row["method_order"]
        row["manifest_binding_sha256"]=manifest_binding(row["manifest_payload"])
        with self.assertRaises(ValueError): validate_campaign(changed)


if __name__ == "__main__":
    unittest.main()
