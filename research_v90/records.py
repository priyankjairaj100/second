"""Exclusive finite record writer for prospective host/entry/launch metadata.

The exact file census must be registered and reused by its storage plan. This
does not bind arbitrary external writers or reserve disk space. Failed partials
are never deleted, overwritten or silently converted to successful records.
"""
import os
from pathlib import Path
from research_v87.outputs import safe_name, require
from src.run_store import canonical_json, digest

SMALL_BYTES = 2**20
REPORT_BYTES = 64*2**20


class Records:
    def __init__(self, root, layout):
        require(type(layout) is dict and 0 < len(layout) <= 512, 'Finite record census required')
        self.root = Path(root).absolute()
        require(not any(p.is_symlink() for p in (self.root, *self.root.parents)), 'Symbolic record root')
        for name, maximum in layout.items():
            safe_name(name)
            require(type(maximum) is int and 0 < maximum <= REPORT_BYTES, 'Bounded record extent required')
        self.layout = dict(layout)
        self.consumed = set()

    def write(self, name, value):
        require(name in self.layout and name not in self.consumed, 'Record outside census or already consumed')
        blob = canonical_json(value)
        require(len(blob) <= self.layout[name], 'Record exceeds its registered byte ceiling')
        target = self.root/name
        require(not any(p.is_symlink() for p in (target, *target.parents)), 'Symbolic record destination')
        self.consumed.add(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        try:
            offset = 0
            while offset < len(blob):
                written = os.write(fd, memoryview(blob)[offset:])
                if written <= 0: raise OSError('Metadata write made no progress')
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        return dict(file=name, bytes=len(blob), sha256=digest(blob))

    def allowance(self):
        return dict(bytes=sum(self.layout.values()), files=len(self.layout),
                    capacity_reserved=False, external_writers_covered=False)
