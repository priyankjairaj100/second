"""Portable, hash-bound extraction of one already evaluated real feature stage.

Export verifies the original full archives with their original codec. Loading
the capsule checks exact archived bytes and bounded lossless decoding, without
claiming local encoder equivalence or rerunning neural feature generation.
This new archival reader does not modify any old state or runtime contract.
"""
from __future__ import annotations
import argparse
import base64
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.run_store import canonical_json, strict_json
from src.fixed_lossless_codec_v29 import MAGIC, SCHEMA, _decode, serialize as original_serialize
from src.compact_state import StageCodes, _dyadic_grid_bytes
from src.dyadic_row_quantizer import dyadic_row_scales

STAGE = 'block.0000.qkv'
DELETED = 'wikitext2:train:article-row-17380'
RETAINED = 'wikitext2:train:article-row-22925'
MAX_CAPSULE_BYTES = 8 * 2**20


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(raw):
    return {'base64': base64.b64encode(raw).decode('ascii'), 'bytes': len(raw), 'sha256': sha(raw)}


def decode(entry, maximum):
    require(type(entry) is dict and set(entry) == {'base64','bytes','sha256'}, 'invalid capsule byte entry')
    require(type(entry['bytes']) is int and 0 < entry['bytes'] <= maximum, 'capsule byte bound exceeded')
    require(type(entry['base64']) is str and len(entry['base64']) <= 4*((maximum+2)//3), 'encoded capsule bound exceeded')
    raw = base64.b64decode(entry['base64'], validate=True)
    require(len(raw) == entry['bytes'] and sha(raw) == entry['sha256'], 'capsule byte hash differs')
    require(base64.b64encode(raw).decode('ascii') == entry['base64'], 'noncanonical base64')
    return raw


@dataclass(frozen=True)
class ArchiveFeature:
    """Authenticated archived encoding, not a locally canonical encoder object."""
    record_id: str
    stage_id: str
    shape: tuple
    source_sha256: str
    target_sha256: str
    mode: int
    payload: bytes
    serialized_descriptor: bytes

    def binary64(self):
        raw = _decode(self.payload, self.mode, self.shape[0]*self.shape[1]*8)
        require(sha(raw) == self.source_sha256, 'decoded archived feature bytes differ')
        require(np.isfinite(np.frombuffer(raw, dtype='<f8')).all(), 'nonfinite archived feature')
        return raw


def serialize_archived_descriptor(descriptor):
    require(type(descriptor) is ArchiveFeature, 'expected an authenticated archive feature')
    return descriptor.serialized_descriptor


def parse_archived_descriptor(raw, record_id, target):
    require(16 <= len(raw) <= 2*2**20 and raw[:8] == MAGIC, 'invalid archived descriptor')
    size = struct.unpack_from('<Q', raw, 8)[0]
    require(0 < size <= 65536 and 16+size <= len(raw), 'archived descriptor header exceeds bound')
    header_raw = raw[16:16+size]
    h = strict_json(header_raw)
    expected = {'schema','target_sha256','anchor_target_sha256','record_id','token_sha256',
                'stage_id','shape','source_sha256','codec_sha256','mode','raw_bytes','payload_bytes','payload_sha256'}
    require(type(h) is dict and set(h) == expected and canonical_json(h) == header_raw,
            'archived descriptor header is not canonical')
    require(h['schema'] == SCHEMA and h['shape'] == [128,768] and h['raw_bytes'] == 128*768*8,
            'archived feature dimensions or schema differ')
    require(h['record_id'] == record_id and h['stage_id'] == STAGE and h['target_sha256'] == target,
            'archived feature identity differs')
    require(type(h['mode']) is int and h['mode'] in (0,1,2), 'unsupported archived feature mode')
    payload = raw[16+size:]
    require(h['payload_bytes'] == len(payload) and h['payload_sha256'] == sha(payload), 'archived payload differs')
    for key in ('target_sha256','anchor_target_sha256','token_sha256','source_sha256','codec_sha256'):
        require(type(h[key]) is str and len(h[key]) == 64 and all(c in '0123456789abcdef' for c in h[key]),
                'invalid archived digest')
    result = ArchiveFeature(record_id, STAGE, (128,768), h['source_sha256'], target,
                            h['mode'], payload, raw)
    result.binary64()
    return result


def load_capsule(path, expected_sha256):
    """Load only a protocol-bound capsule; its extraction provenance is trusted."""
    p = Path(path)
    require(p.is_file() and not p.is_symlink() and not any(x.is_symlink() for x in p.parents), 'unsafe capsule path')
    require(0 < p.stat().st_size <= MAX_CAPSULE_BYTES, 'capsule file exceeds bound')
    raw = p.read_bytes()
    require(sha(raw) == expected_sha256, 'capsule differs from registered hash')
    j = strict_json(raw)
    require(canonical_json(j) == raw and type(j) is dict, 'capsule JSON is noncanonical')
    require(set(j) == {'schema','stage','row_ids','normalization','ridge','bits','target','descriptors',
                      'weights','reference_indices','scales_hex','reference_values_sha256','provenance'},
            'capsule fields differ')
    require(j['schema'] == 'real-feature-capsule-v35' and j['stage'] == STAGE and j['row_ids'] == [0,1,2,3]
            and j['normalization'] == 256 and j['ridge'] == [1,100] and j['bits'] == 4, 'capsule target differs')
    require(set(j['descriptors']) == {DELETED,RETAINED}, 'capsule source membership differs')
    descriptors = {rid:parse_archived_descriptor(decode(entry,2*2**20),rid,j['target'])
                   for rid,entry in j['descriptors'].items()}
    weights_raw = decode(j['weights'],4*768*8)
    require(len(weights_raw) == 4*768*8, 'weight dimensions differ')
    weights = np.frombuffer(weights_raw,dtype='<f8').reshape(4,768).copy()
    require(np.isfinite(weights).all(), 'nonfinite capsule weights')
    require(type(j['scales_hex']) is list and len(j['scales_hex']) == 4, 'invalid capsule scales')
    scales = tuple(float.fromhex(s) for s in j['scales_hex'])
    require([s.hex() for s in scales] == j['scales_hex'] and scales == dyadic_row_scales(weights), 'canonical scales differ')
    packed = decode(j['reference_indices'],4*768//2)
    require(len(packed) == 4*768//2, 'reference index dimensions differ')
    stage = StageCodes(STAGE,4,768,'dyadic_row',4,(),packed,scales)
    indices = stage.indices_array()
    reference = np.empty((4,768),dtype=np.float64)
    for row in range(4):
        reference[row] = np.frombuffer(_dyadic_grid_bytes(scales[row],4),dtype='<f8')[indices[row]]
    require(sha(reference.astype('<f8').tobytes()) == j['reference_values_sha256'], 'reference values differ')
    return dict(descriptors=descriptors,retained_descriptor=descriptors[RETAINED],weights=weights,
                reference=reference,scales=scales,target=j['target'],metadata=j)


def create_capsule(output):
    """Extract only known archive bytes. No Gram or new code computation occurs."""
    from scripts.execute_gram_pilot_v35 import bind_inputs, read_archives, checkpoint_rows, reference_rows, new_file
    entries = bind_inputs()
    original,retained,descriptors,retained_descriptor = read_archives(entries)
    weights = checkpoint_rows(entries['weights']['path'])
    reference = reference_rows(retained)
    scales = tuple(retained.stages[0].scale_values[:4])
    require(scales == dyadic_row_scales(weights), 'archived and weight-derived row scales differ')
    reference_stage = StageCodes.from_array(STAGE,reference,bits=4,grid_axis='dyadic_row',scale_values=scales)
    j = dict(schema='real-feature-capsule-v35',stage=STAGE,row_ids=[0,1,2,3],normalization=256,
             ridge=[1,100],bits=4,target=original.target_sha256,
             descriptors={rid:encode(original_serialize(d)) for rid,d in descriptors.items()},
             weights=encode(weights.astype('<f8').tobytes()),reference_indices=encode(reference_stage.packed_indices),
             scales_hex=[s.hex() for s in scales],reference_values_sha256=sha(reference.astype('<f8').tobytes()),
             provenance=dict(original_inputs={key:dict(path=str(Path(entry['path']).relative_to(ROOT)),
                                sha256=entry['sha256'],bytes=entry['bytes']) for key,entry in entries.items()},
                 original_source_kind='real WikiText-2 archived fixed nearest-anchor calibration features',
                 original_retained_descriptor_equality_verified=True,original_codec_parsing_verified=True,
                 feature_generation_reexecuted=False,gram_formed=False,new_quantization_performed=False,
                 storage_scope='Original descriptor bytes preserved; current loader verifies exact decoded source words, not local encoder identity.',
                 extraction_source_sha256=sha(Path(__file__).read_bytes())))
    raw = canonical_json(j)
    require(len(raw) <= MAX_CAPSULE_BYTES, 'capsule too large')
    new_file(output,raw)
    restored = load_capsule(output,sha(raw))
    require(np.array_equal(restored['weights'],weights) and np.array_equal(restored['reference'],reference), 'capsule roundtrip differs')
    for rid,d in descriptors.items():
        require(restored['descriptors'][rid].binary64() == d.binary64(), 'feature capsule roundtrip differs')
    return dict(path=str(output),sha256=sha(raw),bytes=len(raw),real_sources=2,rows=4,width=768,
                exact_original_feature_words_verified=True,new_quantization_performed=False,gram_formed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export',type=Path,required=True)
    args = parser.parse_args()
    import json
    print(json.dumps(create_capsule(args.export),sort_keys=True))
