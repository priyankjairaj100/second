"""Prospective four-cell service adapter. Not yet Linux integration-qualified.

Each empirical transaction must run in a fresh single-thread process. Codec
framing, target identities and finite solver contracts remain historical.
Execution identity includes every activated adapter separately from the target.
"""
from contextlib import contextmanager, ExitStack
import gc
import hashlib
import importlib.util
from pathlib import Path
import shutil
import tempfile
import threading
import time

from research_v43 import dispatcher
from research_v50.neighbors import enabled as primal_enabled
from research_v63 import codec as modern_codec
from research_v66.operations import AllRepresentationsService, request
from research_v76.token_neighbors import enabled as token_enabled
from research_v77.canonical_reuse import enabled as reuse_enabled
from src import fixed_factor_codec_v26 as compressed_codec
from src.transformer_backend import _check_runtime

CELLS = {'reference_compressed': 'compressed', 'reference_modern': 'modern',
         'optimized_compressed': 'compressed', 'optimized_modern': 'modern'}
CACHE_BYTES = 2**30
RESIDENT_BYTES = 9*2**30
ROOT = Path(__file__).resolve().parents[1]
_ACTIVE = False
_TRANSACTION_CONSUMED = False


class IntegratedService(AllRepresentationsService):
    def admit(self, rows, representation):
        if not _ACTIVE:
            raise RuntimeError('Registered implementation scope required')
        report = super().admit(rows, representation)
        if not all(stage['resident_bytes'] >= RESIDENT_BYTES for stage in report['stages']):
            raise RuntimeError('Actual stage residency was not reserved')
        return dict(report, resident_reservation_bytes=RESIDENT_BYTES)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def decoder_enabled():
    """Compile byte-identical qualified V75 files in a private directory."""
    original = compressed_codec._decode_payload
    with tempfile.TemporaryDirectory(prefix='second-v79-decoder-') as directory:
        directory = Path(directory)
        for name in ('decode.c', 'fast_decode.py'):
            shutil.copyfile(ROOT/'research_v75'/name, directory/name)
        spec = importlib.util.spec_from_file_location('_second_v79_decoder', directory/'fast_decode.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        native = module.library()
        metadata = dict(adapter_sha256=sha(__file__), wrapper_sha256=sha(directory/'fast_decode.py'),
                        c_source_sha256=sha(directory/'decode.c'), binary_sha256=sha(native._name),
                        backend='qualified_v75_native_payload_decoder')
        compressed_codec._decode_payload = module.decode_payload
        try:
            yield metadata
        finally:
            compressed_codec._decode_payload = original
            # The process may retain the loaded code mapping until shutdown.
            # No source-factor data is cached here; process RSS covers mappings.
            del native, module


@contextmanager
def execution(cell):
    """Whole-request implementation scope, including setup and cache cleanup."""
    global _ACTIVE
    if cell not in CELLS:
        raise ValueError('Unregistered implementation cell')
    if _ACTIVE or threading.active_count() != 1:
        raise RuntimeError('Fresh dedicated single-thread process required')
    _check_runtime()
    original_assess = dispatcher.assess_stage
    def assess(spec, total_tokens, **options):
        # Apply the same conservative resident allowance to all four cells.
        # This also reaches admission performed inside the actual solver.
        resident = options.get('resident_bytes', 0)
        if type(resident) is not int or resident < 0:
            raise ValueError('Nonnegative integer residency required')
        options['resident_bytes'] = max(RESIDENT_BYTES, resident)
        return original_assess(spec, total_tokens, **options)
    metadata = dict(cell=cell, arm=CELLS[cell], implementation_sha256=sha(__file__),
                    resident_reservation_bytes=RESIDENT_BYTES, cache_allowance_bytes=0,
                    cache=None, closed=False)
    _ACTIVE = True
    dispatcher.assess_stage = assess
    cache = None
    try:
        with ExitStack() as stack:
            metadata['primal'] = stack.enter_context(primal_enabled())
            if cell.startswith('optimized_'):
                metadata['tokens'] = stack.enter_context(token_enabled())
                if CELLS[cell] == 'compressed':
                    metadata['decoder'] = stack.enter_context(decoder_enabled())
                else:
                    cache = stack.enter_context(reuse_enabled(modern_codec, max_bytes=CACHE_BYTES))
                    metadata['cache_allowance_bytes'] = CACHE_BYTES
                    metadata['cache_adapter_sha256'] = sha(ROOT/'research_v77/canonical_reuse.py')
            try:
                yield metadata
            finally:
                if cache is not None:
                    metadata['cache_before_close'] = cache.stats()
    finally:
        dispatcher.assess_stage = original_assess
        if cache is not None:
            metadata['cache'] = cache.stats()
        metadata['closed'] = True
        _ACTIVE = False


def transaction(factory, previous_rows, rows, cell, read_predecessor, write):
    """Single-use process API. Outer timing encloses context load and cleanup.

Input/source admission and final receipt sealing belong to the surrounding
controller's still wider clock. This is not a complete controller/launcher.
"""
    global _TRANSACTION_CONSUMED
    if _TRANSACTION_CONSUMED:
        raise RuntimeError('Fresh process required for every request; no retry')
    _TRANSACTION_CONSUMED = True
    start = time.perf_counter_ns()
    service = None
    result = None
    try:
        with execution(cell) as implementation:
            try:
                service = factory()
                result = request(service, previous_rows, rows, CELLS[cell], read_predecessor, write)
            finally:
                del service
                gc.collect()
        result['implementation'] = implementation
        return result
    finally:
        gc.collect()
        if result is not None:
            result['context_request_cleanup_elapsed_ns'] = time.perf_counter_ns()-start
