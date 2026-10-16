"""Complete fixed-anchor development service with explicit access and state.

Historical numerical kernels are imported unchanged. Source extraction always
uses the original nearest-grid anchor, including during replay and cold rebuild.
This module does not claim ordinary sequential GPTQ or pretraining unlearning.
"""
from dataclasses import asdict
from fractions import Fraction
import gc
import time

import numpy as np

from research_v42.resource_plan import BoundTarget
from research_v35.exact_gram import GramBudget, add_grams, subtract_gram, dumps, loads
from research_v40.native_exact_gram import accumulate
from research_v43 import dispatcher as dispatch
from research_v43.state import Record, GramTrust, build_state, validate_state
from src import fixed_lossless_codec_v29 as lossless
from src import fixed_factor_codec_v26 as compressed
from src.anchor_transformer import prepare_context
from src.checkpoint_adapter import load_gpt2_checkpoint
from src.compact_state import StageCodes
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_target import build_fixed_anchor_target
from src.ordered_finite import FiniteWeights
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.ordered_fixed_service_v30 import prepare_ordered_leaf, ordered_preparer_binding
from src.run_store import canonical_json, digest
from src.target_manifest import TargetRecipe
from research_v38.bootstrap_target import CHECKPOINT_HASHES


REPRESENTATIONS = ('lossless', 'compressed40', 'hybrid_gram')


def gram_budget(normalization):
    # Hybrid Gram is deliberately restricted to the 768-wide stages.
    return GramBudget(max_width=768, max_tokens=normalization, max_sources=3,
        max_product_terms=768*769//2*normalization, max_integer_bits=256,
        max_serialized_bytes=128*2**20, max_memory_bytes=2*2**30)


def gram_stage(stage, representation):
    return representation == 'hybrid_gram' and stage.width <= 768


def require(value, message):
    if not value:
        raise ValueError(message)


class Service:
    def __init__(self, checkpoint, normalization, record_provenance, mark=lambda *a, **k: None):
        self.mark = mark
        self.normalization = normalization
        self.record_provenance = record_provenance
        tick = time.perf_counter_ns()
        loaded = load_gpt2_checkpoint(checkpoint, identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256'] == CHECKPOINT_HASHES, 'Checkpoint identity changed')
        self.decoder = OrderedFiniteDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
        self.base = build_dyadic_row_target(self.decoder,
            TargetRecipe(original_token_count=normalization, group_count=1))
        self.target = build_fixed_anchor_target(self.decoder, self.base)
        self.bound = BoundTarget(canonical_json(self.base.payload()), canonical_json(self.target.payload()))
        require(len(self.target.stages) == 24, 'The complete DistilGPT2 target requires 24 stages')
        self.context = prepare_context(self.decoder, self.base)
        self.gram_budget = gram_budget(normalization)
        self.policy = dispatch.ResourcePolicy()
        self.load_ns = time.perf_counter_ns()-tick
        self.provenance = canonical_json(dict(schema='fixed-source-execution-binding-v43',
            target_sha256=self.target.digest, anchor_target_sha256=self.base.digest,
            decoder=self.decoder.kernel_manifest, implementation=self.decoder.implementation_manifest,
            preparer_sha256=ordered_preparer_binding(), anchor_sha256=self.context.anchor_sha256))
        self.mark('context_ready', elapsed_ns=self.load_ns, target_sha256=self.target.digest)

    def records(self, rows):
        return tuple(Record(row['id'], tuple(row['tokens']), canonical_json(self.record_provenance[row['id']])) for row in rows)

    def extract(self, rows, telemetry):
        """One complete anchor traversal per source; no calibrated-prefix reuse."""
        result = {}
        tick = time.perf_counter_ns()
        for row in rows:
            leaf = prepare_ordered_leaf(self.decoder, self.base, row, context=self.context)
            require(len(leaf.blocks) == 24, 'Source is incomplete')
            for stage, block in zip(self.target.stages, leaf.blocks):
                require(stage.stage_id == block.stage_id, 'Source stage order changed')
                values = block.array()
                require(values.shape == (len(row['tokens']), stage.width), 'Source shape changed')
                result[(stage.stage_id, row['id'])] = np.ascontiguousarray(values)
            telemetry['neural_stage_record_pairs'] += 24
            self.mark('source_replayed', record_id=row['id'])
        telemetry['source_extraction_ns'] += time.perf_counter_ns()-tick
        return result

    def descriptor(self, stage, row, values, representation):
        kwargs = dict(target_sha256=self.target.digest, anchor_target_sha256=self.base.digest,
            record_id=row['id'], token_sha256=digest(canonical_json(row['tokens'])), stage_id=stage.stage_id)
        if representation == 'compressed40':
            desc = compressed.encode_factor(values, bits=40, block_size=256, **kwargs)
            blob = compressed.serialize(desc)
            box = compressed.parse(blob, expected_sha256=digest(blob)).box()
            require(np.all(box.lower <= values) and np.all(values <= box.upper), 'Compression enclosure failed')
        else:
            desc = lossless.encode_factor(values, **kwargs)
            blob = lossless.serialize(desc)
            restored = lossless.parse(blob, expected_sha256=digest(blob)).array()
            require(values.tobytes() == restored.tobytes(), 'Lossless source bits changed')
        return blob

    def prepare_payloads(self, rows, values, representation, telemetry):
        payloads, grams, trust = {}, {}, {}
        tick = time.perf_counter_ns()
        for stage in self.target.stages:
            if gram_stage(stage, representation):
                pooled = None
                for row in rows:
                    item = accumulate(values[(stage.stage_id, row['id'])].T.copy(),
                        source_id=row['id'], normalization=self.normalization, budget=self.gram_budget)
                    pooled = item if pooled is None else add_grams(pooled, item, budget=self.gram_budget)
                    del item
                blob = dumps(pooled, budget=self.gram_budget)
                trust[stage.stage_id] = GramTrust(digest(blob), pooled.sources)
                grams[stage.stage_id] = blob
                del pooled
            else:
                for row in rows:
                    payloads[(stage.stage_id, row['id'])] = self.descriptor(stage, row,
                        values[(stage.stage_id, row['id'])], representation)
            self.mark('payload_stage', stage_id=stage.stage_id, representation=representation)
        telemetry['encoding_and_gram_ns'] += time.perf_counter_ns()-tick
        return payloads, grams, trust

    def admit(self, rows, representation):
        total_tokens = sum(len(row['tokens']) for row in rows)
        reports = []
        units = 0
        for stage in self.target.stages:
            spec = dispatch.StageSpec.from_stage(stage, target_sha256=self.target.digest)
            kind = 'gram' if gram_stage(stage, representation) else ('box' if representation == 'compressed40' else 'point')
            report = dispatch.assess_stage(spec, total_tokens=total_tokens, kind=kind,
                block_tokens=max(len(r['tokens']) for r in rows), max_blocks=len(rows),
                policy=self.policy, resident_bytes=4*2**30)
            require(report['admitted'], 'Complete request has refused stage: '+stage.stage_id)
            units += report['work_units']
            if kind == 'box':
                fallback = dispatch.assess_stage(spec, total_tokens=total_tokens, kind='point',
                    block_tokens=max(len(r['tokens']) for r in rows), max_blocks=len(rows),
                    policy=self.policy, resident_bytes=4*2**30)
                require(fallback['admitted'], 'Exact fallback is not admitted')
                units += fallback['work_units']
            reports.append(report)
        require(units <= self.policy.max_request_work_units, 'Complete request structural work refused')
        return dict(stages=reports, reserved_work_units=units, replay_all_ancestors_reserved=True,
            maximum_fallback_neural_stage_record_pairs=24*len(rows) if representation=='compressed40' else 0,
            resident_reservation_bytes=4*2**30, process_address_space_cap=self.policy.max_process_bytes)

    def solve(self, rows, representation, payloads, grams, trust, telemetry, *, direct_values=None):
        admission = self.admit(rows, representation)
        outputs = []
        replay = None
        total_tokens = sum(len(row['tokens']) for row in rows)
        for stage in self.target.stages:
            tick = time.perf_counter_ns()
            sid = stage.stage_id
            weights = FiniteWeights(stage.weights).array()
            spec = dispatch.StageSpec.from_stage(stage, target_sha256=self.target.digest)
            options = dict(policy=self.policy, resident_bytes=4*2**30)
            fallback = False
            refusal = None
            if gram_stage(stage, representation):
                gram = loads(grams[sid], trusted_sha256=trust[sid].sha256,
                    expected_sources=trust[sid].sources, budget=self.gram_budget)
                answer = dispatch.solve_gram(spec, weights, gram, gram_budget=self.gram_budget, **options)
                del gram
            else:
                def blocks(kind, values=None):
                    for row in rows:
                        key = (sid, row['id'])
                        if values is not None:
                            point = np.ascontiguousarray(values[key].T)
                            yield point, point
                        elif kind == 'box':
                            blob = payloads[key]
                            box = compressed.parse(blob, expected_sha256=digest(blob)).box()
                            yield np.ascontiguousarray(box.lower.T), np.ascontiguousarray(box.upper.T)
                        else:
                            blob = payloads[key]
                            point = np.ascontiguousarray(lossless.parse(blob, expected_sha256=digest(blob)).array().T)
                            yield point, point
                kind = 'box' if representation == 'compressed40' else 'point'
                try:
                    answer = dispatch.solve_blocks(spec, weights, blocks(kind, direct_values),
                        total_tokens=total_tokens, kind=kind,
                        block_tokens=max(len(r['tokens']) for r in rows), max_blocks=len(rows), **options)
                except dispatch.DispatchRefused as error:
                    if kind != 'box':
                        raise
                    fallback = True
                    from scripts.execute_gram_pilot_v35 import public_result
                    refusal = dict(type=type(error).__name__, message=str(error),
                        diagnostics=public_result(error.diagnostics or {}))
                    if replay is None:
                        replay = self.extract(rows, telemetry)
                        # Exact replay must lie within every archived box and
                        # reproduce the committed source bytes at every stage.
                        for key, blob in payloads.items():
                            descriptor = compressed.parse(blob, expected_sha256=digest(blob))
                            require(digest(replay[key].astype('<f8').tobytes()) == descriptor.source_sha256,
                                'Exact replay source identity differs')
                            box = descriptor.box()
                            require(np.all(box.lower <= replay[key]) and np.all(replay[key] <= box.upper),
                                'Exact replay is outside its archived enclosure')
                    answer = dispatch.solve_blocks(spec, weights, blocks('point', replay),
                        total_tokens=total_tokens, kind='point',
                        block_tokens=max(len(r['tokens']) for r in rows), max_blocks=len(rows), **options)
            outputs.append(StageCodes.from_array(sid, answer.codes, grid_axis='dyadic_row',
                bits=stage.bits, scale_values=stage.scale_values))
            row = dict(stage_id=sid, route=answer.route, elapsed_ns=time.perf_counter_ns()-tick,
                fallback=fallback, certificate_refusal=refusal, code_sha256=digest(outputs[-1].packed_indices))
            from scripts.execute_gram_pilot_v35 import public_result
            row.update(admission=answer.admission, solver=public_result(answer.solver_result))
            telemetry['stages'].append(row)
            self.mark('stage_certified', **row)
            del answer, weights
        return tuple(outputs), admission

    def serialize(self, rows, codes, representation, payloads, grams, trust, telemetry):
        tick = time.perf_counter_ns()
        blob = build_state(self.bound, self.records(rows), codes, representation,
            source_payloads=payloads, stage_grams=grams, gram_trust=trust, gram_budget=self.gram_budget)
        telemetry['serialization_ns'] += time.perf_counter_ns()-tick
        return blob


def telemetry():
    return dict(neural_stage_record_pairs=0, source_extraction_ns=0, encoding_and_gram_ns=0,
        serialization_ns=0, disposal_ns=0, stages=[])


def trust_json(trust):
    return {sid:dict(sha256=item.sha256, sources=[asdict(s) for s in item.sources]) for sid,item in trust.items()}


def trust_read(value):
    from research_v35.exact_gram import SourceCommitment
    return {sid:GramTrust(row['sha256'], tuple(SourceCommitment(**s) for s in row['sources']))
            for sid,row in value.items()}
