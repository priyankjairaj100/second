"""Bounded, request-scoped memoization of a pure canonical encoder choice.

Only repeated _select(raw) work is reused. Frame checks, limits, exact decoding,
source hashes, codec/runtime binding and canonical-choice comparison stay in
all callers. Keys compare immutable raw bytes, not a digest alone. Cache state
is cleared before returning from a request, including on exceptions.

Single-thread dedicated worker only. New service admission must reserve the
chosen cache allowance in addition to the historical resident reservation.
Logical-byte accounting is not an RSS bound; process limits and measured peak
RSS remain mandatory. No new service launch is implemented by this module.
"""
from collections import OrderedDict
from contextlib import contextmanager
import sys
import threading

_ACTIVE=False

class ChoiceCache:
    def __init__(self, select, *, max_bytes, max_entries=4096):
        if not callable(select) or type(max_bytes) is not int or not 0<=max_bytes<=2**30:
            raise ValueError('Callable selector and byte cap between0 and1GiB required')
        if type(max_entries) is not int or not 1<=max_entries<=4096:
            raise ValueError('Entry cap must be between1 and4096')
        self.select=select
        self.max_bytes=max_bytes
        self.max_entries=max_entries
        self.entries=OrderedDict()
        self.retained_bytes=0
        self.base_mapping_bytes=sys.getsizeof(self.entries)
        self.peak_retained_bytes=0
        self.hits=self.misses=self.evictions=self.bypasses=0
        self.closed=False

    def __call__(self, raw, measurements=None):
        if self.closed:raise RuntimeError('Request cache is closed')
        # Preserve the exact selector interface and its original exceptions for
        # inputs outside the parser's immutable-bytes contract. Measurements
        # always execute the real encoder and never reuse invented timings.
        if type(raw) is not bytes or measurements is not None:
            self.bypasses+=1
            return self.select(raw,measurements)
        cached=self.entries.get(raw)
        if cached is not None:
            self.entries.move_to_end(raw)
            self.hits+=1
            return cached[0]
        self.misses+=1
        result=self.select(raw)
        if (type(result) is not tuple or len(result)!=2 or type(result[0]) is not int
                or type(result[1]) is not bytes):
            raise TypeError('Canonical selector returned a nonimmutable choice')
        # This is a conservative payload/object charge, plus a separately
        # reported mapping size; full-process memory must also be measured.
        charge=(sys.getsizeof(raw)+sys.getsizeof(result)+sys.getsizeof(result[0])
                +sys.getsizeof(result[1])+sys.getsizeof((None,None))+sys.getsizeof(0))
        if charge>self.max_bytes:return result
        while self.entries and (self.retained_bytes+charge>self.max_bytes or len(self.entries)>=self.max_entries):
            _,(_,old_charge)=self.entries.popitem(last=False)
            self.retained_bytes-=old_charge;self.evictions+=1
        self.entries[raw]=(result,charge)
        self.retained_bytes+=charge
        while self.entries and self.retained_bytes+max(0,sys.getsizeof(self.entries)-self.base_mapping_bytes)>self.max_bytes:
            _,(_,old_charge)=self.entries.popitem(last=False)
            self.retained_bytes-=old_charge;self.evictions+=1
        if not self.entries:self.entries.clear()
        self.peak_retained_bytes=max(self.peak_retained_bytes,self.retained_bytes+max(0,sys.getsizeof(self.entries)-self.base_mapping_bytes))
        return result

    def stats(self):
        return dict(hits=self.hits,misses=self.misses,evictions=self.evictions,bypasses=self.bypasses,
            retained_bytes=self.retained_bytes,peak_retained_bytes=self.peak_retained_bytes,
            entries=len(self.entries),mapping_bytes=sys.getsizeof(self.entries),base_mapping_bytes=self.base_mapping_bytes,
            byte_cap=self.max_bytes,entry_cap=self.max_entries,closed=self.closed)

    def close(self):
        self.entries.clear();self.retained_bytes=0;self.closed=True

@contextmanager
def enabled(codec, *, max_bytes, max_entries=4096):
    global _ACTIVE
    if _ACTIVE or threading.active_count()!=1:
        raise RuntimeError('Dedicated single-thread worker required')
    original=codec._select
    cache=ChoiceCache(original,max_bytes=max_bytes,max_entries=max_entries)
    _ACTIVE=True
    codec._select=cache
    try:
        yield cache
    finally:
        codec._select=original
        cache.close()
        _ACTIVE=False
