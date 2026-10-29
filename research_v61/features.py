"""Source-local finite features under the original checkpoint teacher.

This provider uses the same ordered finite operations as the frozen V59
constructor. It has no calibrated-prefix input. Each source starts its own
stream, and every installed predecessor is copied from pinned original words.
"""
import hashlib
from pathlib import Path

import numpy as np

from research_v59.anchor import ANCHOR_RULE, FEATURE_RULE, _immutable_teacher
from src.compact_service import _records
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder, ordered_sequential_features
from src.run_store import canonical_json, digest


def require(value, message):
    if not value:
        raise ValueError(message)


def provider_binding():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def feature_contract(decoder, target):
    """Check the provider/teacher identity without running a feature traversal."""
    require(type(decoder) is OrderedFiniteDecoder, 'Explicit ordered finite decoder required')
    payload = target.payload()
    calibration = target.calibration_target.payload()
    require(payload['schema'] == 'fixed-full-precision-anchor-service-target-v61'
        and payload['provider_sha256'] == provider_binding()
        and payload['calibration_target'] == calibration
        and payload['calibration_target_sha256'] == target.calibration_target.digest
        and digest(canonical_json(calibration)) == target.calibration_target.digest,
        'Service target does not bind this provider and exact calibration target')
    require(calibration['schema'] == 'fixed-full-precision-anchor-calibration-target-v59'
        and calibration['feature_rule'] == FEATURE_RULE and calibration['anchor_rule'] == ANCHOR_RULE
        and calibration['decoder_sha256'] == digest(canonical_json(decoder.kernel_manifest))
        and calibration['implementation_manifest_sha256'] == digest(canonical_json(decoder.implementation_manifest))
        and payload['anchor_target_sha256'] == calibration['base_target_sha256'] == target.base_target.digest,
        'Original teacher evaluator or base identity differs')
    stages = tuple(target.stages)
    teachers = calibration['teacher_stages']
    require(tuple(s.stage_id for s in stages) == tuple(decoder.stage_ids)
        and tuple(t['stage_id'] for t in teachers) == tuple(decoder.stage_ids)
        and all(not s.dependencies for s in stages), 'Complete fixed-teacher stage extent required')
    for stage, teacher in zip(stages, teachers):
        require(teacher['shape'] == [len(stage.weights), stage.width], 'Teacher stage geometry differs')
    return stages, teachers


def iter_source_features(decoder, target, record):
    """Yield all (stage ID, token-major binary64 words) for exactly one source.

    The yielded arrays own immutable bytes. Closing this generator, including
    after a downstream failure, closes its only underlying feature stream.
    Values sent by a caller cannot become teacher weights.
    """
    stages, teachers = feature_contract(decoder, target)
    rows = _records(decoder, [record])
    require(len(rows) == 1, 'Exactly one source required')
    _, tokens = rows[0]
    stream = ordered_sequential_features(decoder, tokens)
    try:
        for index, stage in enumerate(stages):
            try:
                if index == 0:
                    sid, values = next(stream)
                else:
                    previous = teachers[index-1]
                    teacher = _immutable_teacher(decoder, previous['stage_id'], previous['weights_sha256'])
                    require(list(teacher.shape) == previous['shape'], 'Original teacher shape differs')
                    sid, values = stream.send(teacher)
                    del teacher
            except StopIteration as error:
                raise ValueError('Original-teacher source traversal ended before all stages') from error
            require(sid == stage.stage_id, 'Original-teacher source stage order differs')
            point = np.ascontiguousarray(np.asarray(values, dtype=np.float64))
            require(point.shape == (len(tokens), stage.width) and np.isfinite(point).all(),
                'Original-teacher feature shape or finite words invalid')
            frozen = np.frombuffer(point.tobytes(order='C'), dtype=np.float64).reshape(point.shape)
            del point, values
            yield sid, frozen
            del frozen
    finally:
        stream.close()
