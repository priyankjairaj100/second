"""Validate activated implementation and cleanup independently of result codes."""
from pathlib import Path
import re
from research_v79 import implementation as impl
from research_v76 import token_neighbors
from research_v80.config import CELLS, RESIDENT
from research_v80.io import require
from src.run_store import digest
from src import native_token_coefficients_v30 as point, native_box_coefficients_v31 as box

ROOT=Path(__file__).resolve().parents[1]
def file_sha(name):return digest((ROOT/name).read_bytes())
def hash_value(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None

def verify_implementation(trial, meta, primal):
    cell='reference_modern' if trial in ('prepare','oracle') else trial.rsplit('-',1)[0]
    require(cell in CELLS and meta['cell']==cell and meta['arm']==CELLS[cell] and meta['closed'] is True
        and meta['primal']==primal and meta['resident_reservation_bytes']==RESIDENT
        and meta['implementation_sha256']==file_sha('research_v79/implementation.py'),'Implementation scope/binding differs')
    optimized=cell.startswith('optimized_')
    require(('tokens' in meta)==optimized,'Fair shared token optimization differs')
    if optimized:
        require(set(meta['tokens'])=={point.__name__,box.__name__},'Both token libraries required')
        for module in (point,box):
            record=meta['tokens'][module.__name__]
            require(record['backend']=='normal_neighbor_token_v76'
                and record['source_sha256']==digest(token_neighbors.transformed(module._C_SOURCE).encode())
                and record['original_c_source_sha256']==digest(module._C_SOURCE.encode())
                and record['wrapper_sha256']==digest(Path(module.__file__).read_bytes())
                and record['adapter_sha256']==file_sha('research_v76/token_neighbors.py')
                and record['flags']==list(module.native_box._FLAGS)
                and hash_value(record['binary_sha256']) and record['compile_elapsed_ns']>0,'Token source/build identity differs')
    require(('decoder' in meta)==(cell=='optimized_compressed'),'Decoder dispatch differs')
    if cell=='optimized_compressed':
        decoder=meta['decoder']
        require(decoder['backend']=='qualified_v75_native_payload_decoder'
            and decoder['adapter_sha256']==meta['implementation_sha256']
            and decoder['wrapper_sha256']==file_sha('research_v75/fast_decode.py')
            and decoder['c_source_sha256']==file_sha('research_v75/decode.c')
            and hash_value(decoder['binary_sha256']),'Decoder build binding differs')
    if cell=='optimized_modern':
        require(meta['cache_allowance_bytes']==impl.CACHE_BYTES
            and meta['cache_adapter_sha256']==file_sha('research_v77/canonical_reuse.py'),'Cache source/cap differs')
        before,after=meta['cache_before_close'],meta['cache']
        require(before['closed'] is False and after['closed'] is True
            and after['entries']==after['retained_bytes']==0,'Cache cleanup absent')
        for state in (before,after):
            require(state['byte_cap']==impl.CACHE_BYTES and state['entry_cap']==4096
                and 0<=state['peak_retained_bytes']<=impl.CACHE_BYTES,'Cache charge exceeded')
            require(all(type(state[k]) is int and state[k]>=0 for k in ('hits','misses','evictions','bypasses','entries','retained_bytes')),'Invalid cache counts')
        require(all(before[k]==after[k] for k in ('hits','misses','evictions','bypasses','peak_retained_bytes')),'Cache counters changed at clear')
    else:
        require(meta['cache'] is None and meta['cache_allowance_bytes']==0
            and 'cache_before_close' not in meta and 'cache_adapter_sha256' not in meta,'Unexpected cache in control')
    return True
