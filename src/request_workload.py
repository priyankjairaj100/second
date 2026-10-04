"""Frozen deletion selectors from original-state information only.

This module does not acquire data or run research experiments. Score preparation
replays original features and charges that work. It never tests deletion outcomes.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import time

from .exact_core import sequential_oracle
from .repair_service import CertifiedPrefix, Record
from .run_store import canonical_json, digest

METHODS = ("repair", "indexed_fresh", "direct_fresh")
PRIMARY_REQUESTS = ("uniform_singleton", "uniform_1_of_16", "uniform_1_of_4",
                    "contiguous_1_of_16", "concentrated_1_of_16", "difficult_1_of_16")
SCORE_RULE = "original-energy-share-and-squared-leverage-margin-v1"


def _text(value, name="text"):
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be nonempty text")
    return value


def _integer(value, name="integer", minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _sha(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("invalid SHA256")
    return value


def _ids(values):
    values = tuple(values)
    if not values or any(type(v) is not str or not v for v in values) or len(set(values)) != len(values):
        raise ValueError("record IDs must be unique nonempty strings")
    return values


def _q(value):
    if type(value) is int:
        return Fraction(value)
    if isinstance(value, Fraction):
        return value
    raise ValueError("scores require exact rational values")


def _encode(value):
    return "infinity" if value is None else [value.numerator, value.denominator]


def _decode(value):
    if value == "infinity":
        return None
    if (not isinstance(value, list) or len(value) != 2
            or any(type(x) is not int for x in value) or value[1] <= 0):
        raise ValueError("invalid canonical rational score")
    result = Fraction(*value)
    if result < 0 or _encode(result) != value:
        raise ValueError("score must be nonnegative and canonical")
    return result


class SeedStream:
    """Versioned SHA256 counter stream with rejection sampling.

    Uniformity statements use the declared ideal independent-stream model.
    The implemented stream is deterministic, reproducible, and not truly random.
    """
    def __init__(self, seed: int, domain: str):
        _integer(seed, "seed")
        self.key = canonical_json(["workload-sha256-counter-v1", seed, _text(domain)])
        self.counter = 0

    def below(self, size: int) -> int:
        _integer(size, "range", 1)
        if size > 2**256:
            raise ValueError("range exceeds stream word")
        limit = 2**256 - (2**256 % size)
        while True:
            value = int.from_bytes(sha256(self.key + self.counter.to_bytes(16, "big")).digest(), "big")
            self.counter += 1
            if value < limit:
                return value % size

    def permutation(self, values):
        result = list(values)
        for end in range(len(result) - 1, 0, -1):
            other = self.below(end + 1)
            result[end], result[other] = result[other], result[end]
        return result


def sample_roots(pool_ids, *, count: int, size: int, seed: int, phase: str):
    """Draw independent subsets under the stream model. Preserve pool order."""
    pool = _ids(pool_ids)
    _integer(count, "root count", 1)
    _integer(size, "root size", 1)
    _text(phase, "phase")
    if size > len(pool):
        raise ValueError("root size exceeds source pool")
    roots = []
    for index in range(count):
        root_id = f"{phase}-root-{index:04d}"
        selected = set(SeedStream(seed, root_id).permutation(pool)[:size])
        roots.append({"root_id": root_id, "record_ids": [rid for rid in pool if rid in selected]})
    return {"schema": "calibration-root-draws-v1", "phase": phase, "seed": seed,
            "pool_ids_sha256": digest(canonical_json(list(pool))),
            "law": "independent-domain-stream-uniform-subsets-without-replacement",
            "cross_root_overlap_permitted": True, "roots": roots}


def validate_phase_pools(pools):
    """Require document IDs and normalized text hashes to be phase-disjoint."""
    if not isinstance(pools, dict) or set(pools) != {"development", "confirmation", "evaluation"}:
        raise ValueError("supply development, confirmation, and evaluation pools")
    seen_ids, seen_hashes, seen_records, seen_payloads, document_hashes = {}, {}, {}, {}, {}
    for phase, rows in pools.items():
        if not isinstance(rows, list) or not rows:
            raise ValueError("each phase requires source records")
        local_ids = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"record_id", "document_id", "normalized_text_sha256", "payload_sha256"}:
                raise ValueError("invalid source record metadata")
            rid = _text(row["record_id"])
            document = _text(row["document_id"])
            text_hash = _sha(row["normalized_text_sha256"])
            payload_hash = _sha(row["payload_sha256"])
            if rid in local_ids:
                raise ValueError("duplicate phase record ID")
            local_ids.add(rid)
            if document in document_hashes and document_hashes[document] != text_hash:
                raise ValueError("one source document has inconsistent normalized text hashes")
            document_hashes[document] = text_hash
            for key, seen in ((document, seen_ids), (text_hash, seen_hashes),
                              (rid, seen_records), (payload_hash, seen_payloads)):
                if key in seen and seen[key] != phase:
                    raise ValueError("source document or normalized text crosses phases")
                seen[key] = phase
    return digest(canonical_json(pools))


def _inverse_from_factors(factors):
    """Invert L.T diag(t) L through exact triangular solves."""
    d = len(factors.g)
    columns = []
    for column in range(d):
        y = [Fraction(0)] * d
        for i in range(d - 1, -1, -1):
            y[i] = Fraction(i == column) - sum((factors.L[k][i] * y[k] for k in range(i + 1, d)), Fraction(0))
        z = [y[i] * factors.g[i] for i in range(d)]
        x = [Fraction(0)] * d
        for i in range(d):
            x[i] = z[i] - sum((factors.L[i][k] * x[k] for k in range(i)), Fraction(0))
        columns.append(x)
    return tuple(tuple(columns[j][i] for j in range(d)) for i in range(d))


def _sensitivity(trace):
    """Return max(g_i E_ai / m_ai**2), or None for infinite sensitivity."""
    largest = Fraction(0)
    for row in trace.rows:
        for i, value in enumerate(row.inputs):
            energy = trace.factors.g[i] * row.prefix_energy[i]
            if energy == 0:
                continue
            grid, index = trace.grids[i], row.code_indices[i]
            distances = []
            if index:
                distances.append(value - (grid[index - 1] + grid[index]) / 2)
            if index + 1 < len(grid):
                distances.append((grid[index] + grid[index + 1]) / 2 - value)
            if not distances:
                continue
            margin = min(distances)
            if margin < 0:
                raise ValueError("decision trace lies outside its rounding cell")
            if margin == 0:
                return None
            largest = max(largest, energy / margin**2)
    return largest


def prepare_original_scores(service, state, records, *, prepared_records_sha256: str,
                            source_sha256: dict[str, str]):
    """Compute and verify original-state scores. Never request a deletion repair.

    The caller must include these measured costs in preparation. The returned
    hashes bind trusted inputs; they do not authenticate hostile storage.
    """
    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
    _sha(prepared_records_sha256)
    if not isinstance(source_sha256, dict) or not source_sha256:
        raise ValueError("score producer source hashes are required")
    for key, value in source_sha256.items():
        _text(key)
        _sha(value)
    records = tuple(records)
    if not records or any(not isinstance(record, Record) for record in records):
        raise ValueError("original records are required")
    ids = _ids(record.record_id for record in records)
    if set(ids) != set(state.retained_ids):
        raise ValueError("scores require every original state record")
    stored = {row.record_id: row.content_digest for row in state.records}
    if any(stored[record.record_id] != record.content_digest for record in records):
        raise ValueError("record content differs from the original state")
    if state.manifest_digest != service.manifest_digest:
        raise ValueError("original state belongs to another service")
    original = {stage.stage_id: stage for stage in state.model}
    if set(original) != {stage.stage_id for stage in service.job.stages}:
        raise ValueError("original model stages differ from target")
    concentration = {rid: Fraction(0) for rid in ids}
    difficulty = {rid: Fraction(0) for rid in ids}
    stages, ancestors = [], {}
    for stage in service.job.stages:
        wanted = set(stage.dependencies)
        for dependency in stage.dependencies:
            wanted.update(ancestors[dependency])
        ancestors[stage.stage_id] = wanted
        prefix = CertifiedPrefix(service.job.manifest_digest,
                                 tuple(original[s.stage_id] for s in service.job.stages if s.stage_id in wanted))
        d = stage.width
        grams = {}
        for record in records:
            features = tuple(tuple(_q(x) for x in row) for row in service.evaluator(record, stage, prefix))
            if len(features) != d or any(len(row) != len(features[0]) for row in features):
                raise ValueError("original feature matrix has the wrong shape")
            grams[record.record_id] = tuple(tuple(sum((a*b for a,b in zip(features[i], features[j])), Fraction(0))
                                                    / stage.normalization for j in range(d)) for i in range(d))
        covariance = tuple(tuple(Fraction(stage.ridge if i == j else 0)
                                     + sum((g[i][j] for g in grams.values()), Fraction(0))
                                 for j in range(d)) for i in range(d))
        trace = sequential_oracle(stage.weights, covariance, stage.grids)
        if trace.codes != original[stage.stage_id].codes:
            raise ValueError("original-state replay does not match the stored model")
        inverse, sensitivity = _inverse_from_factors(trace.factors), _sensitivity(trace)
        total_energy = sum((g[i][i] for g in grams.values() for i in range(d)), Fraction(0))
        rows = []
        for rid, gram in grams.items():
            energy = sum((gram[i][i] for i in range(d)), Fraction(0))
            share = energy / total_energy if total_energy else Fraction(0)
            leverage = sum((inverse[i][j] * gram[j][i] for i in range(d) for j in range(d)), Fraction(0))
            if leverage < 0:
                raise ValueError("negative exact leverage")
            score = Fraction(0) if leverage == 0 else None if sensitivity is None else leverage**2 * sensitivity
            concentration[rid] = max(concentration[rid], share)
            if difficulty[rid] is not None:
                difficulty[rid] = None if score is None else max(difficulty[rid], score)
            rows.append({"record_id": rid, "energy_share": _encode(share), "leverage": _encode(leverage)})
        stages.append({"stage_id": stage.stage_id, "margin_sensitivity": _encode(sensitivity), "records": rows})
    return {"schema": "calibration-original-scores-v1", "rule": SCORE_RULE,
            "original_state_sha256": state.digest, "target_manifest_sha256": service.job.manifest_digest,
            "prepared_records_sha256": prepared_records_sha256,
            "record_content_sha256": {record.record_id: record.content_digest for record in records},
            "source_sha256": dict(source_sha256), "uses_deletion_outcomes": False,
            "records": [{"record_id": rid, "concentration": _encode(concentration[rid]),
                         "difficulty": _encode(difficulty[rid])} for rid in ids], "stages": stages,
            "preparation": {"wall_time_ns": time.perf_counter_ns()-wall,
                            "cpu_time_ns": time.process_time_ns()-cpu,
                            "original_feature_evaluations": len(records)*len(service.job.stages),
                            "exact_stage_factorizations": len(service.job.stages),
                            "charge_to": "workload_preparation", "timing_scope": "score_preparation_only"}}


def expand_document_deletion(record_documents: dict[str, str], deleted_document_ids):
    """Expand source withdrawal to every prepared chunk in the declared corpus."""
    if not isinstance(record_documents, dict) or not record_documents:
        raise ValueError("record-to-document membership is required")
    for record_id, document_id in record_documents.items():
        _text(record_id, "record ID")
        _text(document_id, "document ID")
    documents = tuple(deleted_document_ids)
    if len(set(documents)) != len(documents) or not set(documents) <= set(record_documents.values()):
        raise ValueError("withdraw only unique known document IDs")
    chosen = set(documents)
    return [record_id for record_id, document_id in record_documents.items() if document_id in chosen]


def source_withdrawal_request(record_ids, record_sources, *, root_id: str, seed: int,
                              source_metadata_sha256: str):
    """Uniformly choose an admissible documented source under the stream model.

    This function does not manufacture or validate the semantic source labels.
    The caller must obtain them from documented, retained provenance.
    """
    ids = _ids(record_ids)
    if not isinstance(record_sources, dict) or set(record_sources) != set(ids):
        raise ValueError("every record needs its documented source ID")
    for source in record_sources.values():
        _text(source, "source ID")
    if _sha(source_metadata_sha256) != digest(canonical_json(record_sources)):
        raise ValueError("source metadata hash differs")
    candidates = sorted(source for source in set(record_sources.values())
                        if sum(record_sources[rid] == source for rid in ids) < len(ids))
    if not candidates:
        raise ValueError("no nonempty source withdrawal retains calibration records")
    stream = SeedStream(seed, _text(root_id)+"/source_withdrawal")
    source = candidates[stream.below(len(candidates))]
    return {"request_id": "source_withdrawal", "analysis_group": "source_extension",
            "deleted_ids": [rid for rid in ids if record_sources[rid] == source],
            "starting_state": "original", "execution_requirement": "independent_reset",
            "blocked_reason": None, "selected_source_id": source,
            "eligible_source_ids": candidates, "source_metadata_sha256": source_metadata_sha256,
            "selection_rule": "uniform-admissible-source-sorted-ID-v1"}


def build_workload(record_ids, *, root_id: str, seed: int, scores: dict,
                   prepared_records_sha256: str, original_state_sha256: str):
    """Freeze all requests, including blocked sequence and complete-delete controls."""
    ids = _ids(record_ids)
    _text(root_id, "root ID")
    _integer(seed, "seed")
    _sha(prepared_records_sha256)
    _sha(original_state_sha256)
    if (not isinstance(scores, dict) or scores.get("schema") != "calibration-original-scores-v1"
            or scores.get("rule") != SCORE_RULE or scores.get("uses_deletion_outcomes") is not False
            or scores.get("prepared_records_sha256") != prepared_records_sha256
            or scores.get("original_state_sha256") != original_state_sha256):
        raise ValueError("scores do not bind the original request source")
    score_rows = scores.get("records")
    if not isinstance(score_rows, list) or [r.get("record_id") for r in score_rows] != list(ids):
        raise ValueError("score IDs must match the original ordered records")
    by_id = {}
    for row in score_rows:
        if set(row) != {"record_id", "concentration", "difficulty"}:
            raise ValueError("invalid score row")
        concentration, difficulty = _decode(row["concentration"]), _decode(row["difficulty"])
        if concentration is None or concentration > 1:
            raise ValueError("concentration must lie in [0,1]")
        by_id[row["record_id"]] = (concentration, difficulty)
    small, large = (len(ids)+15)//16, (len(ids)+3)//4
    requests = []
    for name in PRIMARY_REQUESTS:
        stream = SeedStream(seed, root_id + "/" + name)
        size = 1 if name == "uniform_singleton" else large if name == "uniform_1_of_4" else small
        if name.startswith("uniform"):
            chosen = set(stream.permutation(ids)[:size])
        elif name.startswith("contiguous"):
            start = stream.below(len(ids)-size+1)
            chosen = set(ids[start:start+size])
        else:
            column = 0 if name.startswith("concentrated") else 1
            def key(rid):
                value = by_id[rid][column]
                return (0 if value is None else 1, Fraction(0) if value is None else -value, rid)
            chosen = set(sorted(ids, key=key)[:size])
        selected = [rid for rid in ids if rid in chosen]
        requests.append({"request_id": name, "analysis_group": "primary", "deleted_ids": selected,
                         "starting_state": "original", "execution_requirement": "independent_reset",
                         "blocked_reason": "no_retained_records" if len(selected) == len(ids) else None})
    permutation = SeedStream(seed, root_id + "/sequential_1_of_16").permutation(ids)
    cumulative = set()
    for step in range(3):
        selected = set(permutation[step*small:(step+1)*small])
        previous = sorted(cumulative)
        cumulative.update(selected)
        requests.append({"request_id": f"sequential_1_of_16_step_{step+1}", "analysis_group": "sequential",
                         "deleted_ids": [rid for rid in ids if rid in selected],
                         "previously_deleted_ids": previous,
                         "cumulative_deleted_ids": [rid for rid in ids if rid in cumulative],
                         "starting_state": "original" if step == 0 else f"sequential_1_of_16_step_{step}",
                         "execution_requirement": "previous_committed_state",
                         "blocked_reason": "root_too_small_for_three_disjoint_requests" if 3*small > len(ids)
                         else "sequential_runner_not_implemented"})
    requests.append({"request_id": "sequential_combined", "analysis_group": "sequence_control",
                     "deleted_ids": [rid for rid in ids if rid in cumulative], "starting_state": "original",
                     "execution_requirement": "independent_reset", "blocked_reason":
                     "no_retained_records" if len(cumulative) == len(ids) else None})
    for name, selected in (("empty_deletion", []), ("complete_deletion", list(ids))):
        requests.append({"request_id": name, "analysis_group": "correctness_control", "deleted_ids": selected,
                         "starting_state": "original", "execution_requirement": "independent_reset",
                         "blocked_reason": "complete_deletion_runner_not_implemented" if selected else None})
    return {"schema": "calibration-workload-v1", "root_id": root_id, "seed": seed,
            "original_record_ids": list(ids), "prepared_records_sha256": prepared_records_sha256,
            "original_state_sha256": original_state_sha256, "scores_sha256": digest(canonical_json(scores)),
            "selector_version": "original-state-selectors-v1", "requests": requests}


def counterbalanced_orders(*, seed: int, root_id: str, request_id: str, repeats: int):
    """Cyclic Latin positions; reverse orientation alternates each complete block."""
    _integer(repeats, "repeat count", 1)
    base = SeedStream(seed, _text(root_id)+"/"+_text(request_id)+"/method-order").permutation(METHODS)
    result = []
    for repeat in range(repeats):
        block, shift = divmod(repeat, len(base))
        orientation = base if block % 2 == 0 else list(reversed(base))
        result.append(orientation[shift:]+orientation[:shift])
    return result
