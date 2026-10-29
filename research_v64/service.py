"""Modern lossless point-service adapter for the frozen V61 numerical target.

This is unregistered software preparation. V63 storage is used as a distinct
format; supplied endpoint codes are never used to implement a repair. A future
worker must include file I/O, startup, full resource admission and audit costs.
Historical source files and their numerical solver remain unchanged.
"""
import json
import time

import numpy as np

from research_v61.service import Service, require
from research_v63 import archive, codec
from research_v43 import dispatcher as dispatch
from src.compact_state import StageCodes
from src.ordered_finite import FiniteWeights
from src.run_store import canonical_json, digest

REPRESENTATION = 'modern_lossless'


class ModernService(Service):
    def admit(self, rows, representation):
        # Inherited extraction uses the literal lossless name for point admission.
        require(representation in (REPRESENTATION, 'lossless'), 'Unsupported modern service representation')
        return super().admit(rows, 'lossless')

    def _records_and_keys(self, rows):
        records = self.records(rows)
        keys = {(s.stage_id, r.record_id) for s in self.bound.stages for r in records}
        return records, keys

    def descriptor(self, stage, row, values, representation):
        require(representation == REPRESENTATION, 'Modern descriptor representation required')
        record = self.records((row,))[0]
        require(type(values) is np.ndarray and values.dtype == np.float64
                and values.shape == (len(record.tokens), stage.width) and np.isfinite(values).all(),
                'Finite binary64 source shape required')
        blob = codec.serialize(codec.encode_factor(values,
            target_sha256=digest(self.bound.fixed_payload), anchor_target_sha256=digest(self.bound.anchor_payload),
            record_id=record.record_id, token_sha256=record.token_sha256, stage_id=stage.stage_id))
        parsed = archive.descriptor(blob, stage, record, self.bound)
        require(parsed.binary64() == values.astype('<f8', copy=False).tobytes(), 'Source words changed')
        return blob

    def prepare_payloads(self, rows, values, representation, telemetry):
        require(representation == REPRESENTATION, 'Modern representation required')
        self.admit(rows, representation)
        _, keys = self._records_and_keys(rows)
        require(set(values) == keys, 'Complete exact feature census required')
        start = time.perf_counter_ns()
        try:
            payloads = {}
            for stage in self.target.stages:
                for row in rows:
                    key = (stage.stage_id, row['id'])
                    payloads[key] = self.descriptor(stage, row, values[key], representation)
                self.mark('payload_stage', stage_id=stage.stage_id, representation=representation)
            return payloads, {}, {}
        finally:
            telemetry['encoding_and_gram_ns'] += time.perf_counter_ns() - start

    def solve(self, rows, representation, payloads, grams, trust, telemetry, *, direct_values=None):
        require(representation == REPRESENTATION and not grams and not trust,
                'Modern point service cannot use Gram state or trust')
        admission = self.admit(rows, representation)
        records, keys = self._records_and_keys(rows)
        require(set(payloads) == keys if direct_values is None else not payloads and set(direct_values) == keys,
                'Exact source census required')
        manifest = json.loads(self.bound.anchor_payload)
        require(self.target.digest == digest(self.bound.fixed_payload)
                and len(self.target.stages) == len(self.bound.stages), 'Complete numerical target binding required')
        # Validate the entire numerical stage sequence before any solver call.
        specs = []
        for stage, entry in zip(self.target.stages, manifest['stages']):
            spec = dispatch.StageSpec.from_stage(stage, target_sha256=self.target.digest)
            require(spec == dispatch.StageSpec.from_manifest(entry, target_sha256=self.target.digest),
                    'Numerical stage differs from bound target')
            specs.append(spec)
        total_tokens = sum(len(r['tokens']) for r in rows)
        outputs = []
        for stage, spec in zip(self.target.stages, specs):
            tick = time.perf_counter_ns()
            sid = stage.stage_id
            weights = FiniteWeights(stage.weights).array()

            def blocks():
                for record in records:
                    key = (sid, record.record_id)
                    if direct_values is None:
                        values = archive.descriptor(payloads[key], stage, record, self.bound).array()
                    else:
                        values = direct_values[key]
                        require(type(values) is np.ndarray and values.dtype == np.float64
                                and values.shape == (len(record.tokens), stage.width) and np.isfinite(values).all(),
                                'Finite binary64 source shape required')
                    point = np.ascontiguousarray(values.T)
                    yield point, point

            answer = dispatch.solve_blocks(spec, weights, blocks(), total_tokens=total_tokens,
                kind='point', block_tokens=max(len(r['tokens']) for r in rows), max_blocks=len(rows),
                policy=self.policy, resident_bytes=4*2**30)
            code = StageCodes.from_array(sid, answer.codes, grid_axis='dyadic_row',
                bits=stage.bits, scale_values=stage.scale_values)
            outputs.append(code)
            from scripts.execute_gram_pilot_v35 import public_result
            row = dict(stage_id=sid, route=answer.route, elapsed_ns=time.perf_counter_ns()-tick,
                fallback=False, certificate_refusal=None, code_sha256=digest(code.packed_indices),
                admission=answer.admission, solver=public_result(answer.solver_result))
            telemetry['stages'].append(row)
            self.mark('stage_certified', **row)
            del answer, weights
        return tuple(outputs), admission

    def serialize(self, rows, codes, representation, payloads, grams, trust, telemetry):
        require(representation == REPRESENTATION and not grams and not trust,
                'Modern point state required')
        tick = time.perf_counter_ns()
        try:
            return archive.pack(self.bound, self.records(rows), codes, payloads)
        finally:
            telemetry['serialization_ns'] += time.perf_counter_ns()-tick

    def repair(self, previous_blob, previous_rows, retained_rows, telemetry):
        """In-memory integration, not a measured complete request transaction.

        No expected endpoint codes are accepted. The caller supplies the actual
        predecessor and registered memberships; the solver computes all new codes.
        """
        self.admit(previous_rows, REPRESENTATION)
        self.admit(retained_rows, REPRESENTATION)
        previous_records = tuple(sorted(self.records(previous_rows), key=lambda r: r.record_id))
        retained_records = self.records(retained_rows)
        prior = {r.record_id: r for r in previous_records}
        require(len(retained_records) < len(previous_records)
                and all(prior.get(r.record_id) == r for r in retained_records), 'Proper retained subset required')
        tick = time.perf_counter_ns()
        try:
            previous = archive.unpack(previous_blob)
            require(previous.target == self.bound and previous.records == previous_records,
                    'Predecessor target or membership differs')
        finally:
            telemetry['predecessor_validation_ns'] = telemetry.get('predecessor_validation_ns', 0) + time.perf_counter_ns()-tick
        keep = {r.record_id for r in retained_records}
        payloads = {(s, r): b for s, r, b in previous.source_payloads if r in keep}
        codes, admission = self.solve(retained_rows, REPRESENTATION, payloads, {}, {}, telemetry)
        blob = self.serialize(retained_rows, codes, REPRESENTATION, payloads, {}, {}, telemetry)
        return blob, codes, admission
