"""Durable CPU admission accounting for trusted local comparison workers.

The ledger caps admitted allowances. It is not CPU containment for descendants.
Unknown attempts retain their entire allowance until valid usage is recorded.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
from types import MappingProxyType

from .run_store import atomic_write, canonical_json, digest, strict_json


class BudgetExhausted(RuntimeError):
    """The next complete worker allowance does not fit the phase budget."""


def _positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} requires a positive integer")
    return value


def _validate_ledger(ledger, binding):
    if (type(ledger) is not dict or set(ledger) != {'schema', 'binding', 'attempts'}
            or ledger['schema'] != 'phase-cpu-ledger-v1' or ledger['binding'] != binding
            or type(ledger['attempts']) is not dict):
        raise ValueError('budget ledger identity or schema differs')
    caps = binding['phase_cpu_seconds']
    for key, row in ledger['attempts'].items():
        if type(key) is not str or not key or type(row) is not dict:
            raise ValueError('invalid budget attempt')
        fields = {'phase', 'reserved_cpu_seconds', 'state', 'charged_cpu_seconds', 'observed_cpu_ns'}
        if set(row) != fields or type(row['phase']) is not str or row['phase'] not in caps:
            raise ValueError('invalid budget attempt fields')
        _positive(row['reserved_cpu_seconds'], 'reservation'); _positive(row['charged_cpu_seconds'], 'debit')
        if row['state'] == 'reserved':
            if row['observed_cpu_ns'] is not None or row['charged_cpu_seconds'] != row['reserved_cpu_seconds']:
                raise ValueError('invalid pending budget debit')
        elif row['state'] == 'settled':
            usage = row['observed_cpu_ns']
            if type(usage) is not int or usage < 0 or row['charged_cpu_seconds'] != max(1, (usage + 999_999_999) // 1_000_000_000):
                raise ValueError('invalid settled budget debit')
        else:
            raise ValueError('invalid budget state')
    return ledger


def read_budget_snapshot(directory, *, identity, phase_cpu_seconds, max_bytes=16*1024*1024, max_attempts=100000):
    """Read one bounded atomic ledger without creating directories, files or locks.

    Completeness covers this trusted protocol ledger at read time, not a project,
    a host, or future admissions. Concurrent replacement causes rejection.
    """
    _positive(max_bytes, 'maximum ledger bytes'); _positive(max_attempts, 'maximum attempts')
    if type(phase_cpu_seconds) is not dict or not phase_cpu_seconds or len(phase_cpu_seconds) > 64:
        raise ValueError('bounded phase CPU caps are required')
    for phase, cap in phase_cpu_seconds.items():
        if type(phase) is not str or not phase or len(phase) > 256:
            raise ValueError('invalid phase name')
        _positive(cap, 'phase cap')
        if cap.bit_length() > 128:
            raise ValueError('phase cap exceeds diagnostic bound')
    binding = strict_json(canonical_json({'identity': identity, 'phase_cpu_seconds': phase_cpu_seconds,
        'scope': 'trusted_worker_cpu_admission_not_process_tree_containment'}))
    root = Path(directory).absolute(); path = root / 'ledger.json'
    if root.is_symlink() or any(p.is_symlink() for p in root.parents) or path.is_symlink():
        raise ValueError('symbolic budget snapshot path')
    base = {'schema': 'phase-cpu-read-snapshot-v1', 'path': str(path), 'binding': binding,
        'binding_sha256': digest(canonical_json(binding)), 'phase_cpu_seconds': phase_cpu_seconds,
        'scope': 'complete trusted protocol ledger at read time; not project/global/hostile completeness',
        'read_only': True}
    if not path.exists():
        return dict(base, status='unavailable', reason='ledger_missing', ledger_sha256=None,
                    attempts=None, charged_cpu_seconds=None, over_cap=None)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
            raise ValueError('budget ledger is not a bounded regular file')
        chunks = []; size = 0
        while True:
            chunk = os.read(fd, min(65536, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk); size += len(chunk)
            if size > max_bytes:
                raise ValueError('budget ledger exceeds read bound')
        after = os.fstat(fd); current = path.stat(follow_symlinks=False)
        signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if signature(before) != signature(after) or signature(after) != signature(current):
            raise ValueError('budget ledger changed during snapshot')
    finally:
        os.close(fd)
    raw = b''.join(chunks); ledger = strict_json(raw)
    if canonical_json(ledger) != raw:
        raise ValueError('budget ledger requires canonical bytes')
    _validate_ledger(ledger, binding)
    if len(ledger['attempts']) > max_attempts:
        raise ValueError('budget ledger exceeds attempt bound')
    for key, row in ledger['attempts'].items():
        if len(key) > 1024 or any(type(v) is int and v.bit_length() > 128 for v in row.values()):
            raise ValueError('budget attempt exceeds diagnostic bound')
    used = {phase: sum(row['charged_cpu_seconds'] for row in ledger['attempts'].values() if row['phase'] == phase)
            for phase in phase_cpu_seconds}
    return dict(base, status='verified', ledger_sha256=digest(raw), ledger_bytes=len(raw),
        attempts=ledger['attempts'], charged_cpu_seconds=used,
        reserved_unknown_attempts=sum(row['state'] == 'reserved' for row in ledger['attempts'].values()),
        reservation_overrun_attempts=[key for key,row in ledger['attempts'].items()
                                      if row['charged_cpu_seconds'] > row['reserved_cpu_seconds']],
        over_cap={phase: used[phase] > phase_cpu_seconds[phase] for phase in phase_cpu_seconds})


class PhaseBudget:
    """Serialize reservations and debits with one POSIX advisory lock."""
    def __init__(self, directory, *, identity, phase_cpu_seconds):
        root = Path(directory).absolute()
        if root.is_symlink() or any(path.is_symlink() for path in root.parents):
            raise ValueError("symlink budget directories are unsupported")
        if not isinstance(phase_cpu_seconds, dict) or not phase_cpu_seconds:
            raise ValueError("phase CPU caps are required")
        if any(type(key) is not str or not key for key in phase_cpu_seconds):
            raise ValueError("phase names must be nonempty strings")
        for cap in phase_cpu_seconds.values():
            _positive(cap, "phase cap")
        root.mkdir(parents=True, exist_ok=True)
        self.root = root.resolve()
        self.binding = {"identity": identity, "phase_cpu_seconds": phase_cpu_seconds,
                        "scope": "trusted_worker_cpu_admission_not_process_tree_containment"}
        self.binding = strict_json(canonical_json(self.binding))
        self.identity_digest = digest(canonical_json(self.binding))
        self.caps = MappingProxyType(dict(phase_cpu_seconds))
        with self._locked():
            path = self.root / "ledger.json"
            if not path.exists():
                atomic_write(path, canonical_json({"schema": "phase-cpu-ledger-v1",
                    "binding": self.binding, "attempts": {}}))
            self._read()

    @contextmanager
    def _locked(self):
        fd = os.open(self.root / "ledger.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _read(self):
        path = self.root / "ledger.json"
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symbolic budget ledger")
        ledger = strict_json(path.read_bytes())
        return _validate_ledger(ledger, self.binding)

    def _save(self, ledger):
        atomic_write(self.root / "ledger.json", canonical_json(ledger))

    def reserve(self, phase, attempt_id, cpu_seconds):
        """Reserve before launch. Repeated reservation IDs are forbidden."""
        if type(phase) is not str or phase not in self.caps or type(attempt_id) is not str or not attempt_id:
            raise ValueError("invalid phase or attempt identity")
        _positive(cpu_seconds, "reservation")
        with self._locked():
            ledger = self._read()
            if attempt_id in ledger["attempts"]:
                raise ValueError("budget attempt identity already exists")
            used = sum(row["charged_cpu_seconds"] for row in ledger["attempts"].values() if row["phase"] == phase)
            if used + cpu_seconds > self.caps[phase]:
                raise BudgetExhausted(f"phase {phase} has {max(0, self.caps[phase] - used)} CPU seconds available; worker requires {cpu_seconds}")
            row = {"phase": phase, "reserved_cpu_seconds": cpu_seconds, "state": "reserved",
                   "charged_cpu_seconds": cpu_seconds, "observed_cpu_ns": None}
            ledger["attempts"][attempt_id] = row
            self._save(ledger)
            return dict(row)

    def settle(self, attempt_id, observed_cpu_ns):
        """Record wait4 usage. Never release a reservation without usage."""
        if type(observed_cpu_ns) is not int or observed_cpu_ns < 0:
            raise ValueError("observed CPU nanoseconds must be a nonnegative integer")
        with self._locked():
            ledger = self._read()
            if attempt_id not in ledger["attempts"]:
                raise ValueError("budget attempt was not reserved")
            row = ledger["attempts"][attempt_id]
            if row["state"] == "settled":
                if row["observed_cpu_ns"] != observed_cpu_ns:
                    raise ValueError("settled budget usage differs")
                return dict(row)
            row.update(state="settled", observed_cpu_ns=observed_cpu_ns,
                       charged_cpu_seconds=max(1, (observed_cpu_ns + 999_999_999) // 1_000_000_000))
            self._save(ledger)
            return dict(row)

    def snapshot(self):
        with self._locked():
            ledger = self._read()
            used = {phase: sum(row["charged_cpu_seconds"] for row in ledger["attempts"].values()
                               if row["phase"] == phase) for phase in self.caps}
            return {"binding_sha256": self.identity_digest, "phase_cpu_seconds": dict(self.caps),
                    "charged_cpu_seconds": used, "attempts": ledger["attempts"],
                    "over_cap": {phase: used[phase] > self.caps[phase] for phase in self.caps}}
