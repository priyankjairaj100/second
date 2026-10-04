"""Atomic local run records for a trusted filesystem.

A completed record binds every artifact hash. Interrupted attempts remain visible.
This module does not authenticate hostile storage or erase old physical bytes.
"""
from __future__ import annotations

from hashlib import sha256
import json
import fcntl
import os
from pathlib import Path
import re
import socket
import tempfile
import time


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def strict_json(data: bytes):
    return json.loads(data, object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def atomic_write(path: Path, payload: bytes) -> None:
    """Replace one file, then sync its parent directory on POSIX."""
    if path.is_symlink():
        raise ValueError("refuse a symlink output")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class RunStore:
    """One exclusive writer, immutable attempts, and one verified completion."""
    def __init__(self, root: str | Path, identity: dict):
        raw = Path(root).absolute()
        if raw.is_symlink() or any(p.is_symlink() for p in raw.parents):
            raise ValueError("symlink directories are not supported")
        raw.mkdir(parents=True, exist_ok=True)
        self.root = raw.resolve()
        self.identity = strict_json(canonical_json(identity))
        self.identity_digest = digest(canonical_json(identity))
        self.artifacts: dict[str, dict] = {}
        self.attempt: Path | None = None
        self._locked = False
        self._sealed = False

    def _path(self, name: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or name in (".", ".."):
            raise ValueError("artifact names must be simple filenames")
        if self.attempt is None or not self._locked or self._sealed:
            raise RuntimeError("an active, unsealed writer is required")
        if name == "status.json":
            raise ValueError("status.json is reserved")
        path = self.attempt / name
        if path.is_symlink():
            raise ValueError("symlink artifact")
        return path

    def completed(self) -> dict | None:
        path = self.root / "result.json"
        if not path.exists():
            return None
        if path.is_symlink():
            raise ValueError("symlink result")
        result = strict_json(path.read_bytes())
        if result.get("identity_sha256") != self.identity_digest:
            raise ValueError("run identity differs from saved result")
        if result.get("status") != "complete":
            return None
        attempt_name = result.get("attempt")
        if not isinstance(attempt_name, str) or not re.fullmatch(r"attempt-[0-9]{4,}", attempt_name):
            raise ValueError("invalid saved attempt")
        attempt = self.root / attempt_name
        if attempt.is_symlink() or not attempt.is_dir():
            raise ValueError("invalid saved attempt directory")
        artifacts = result.get("artifacts")
        if not isinstance(artifacts, dict) or not artifacts:
            raise ValueError("completed run has no artifact manifest")
        for name, expected in artifacts.items():
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
                raise ValueError("unsafe saved artifact name")
            p = attempt / name
            if p.is_symlink() or not p.is_file():
                raise ValueError("missing saved artifact")
            data = p.read_bytes()
            if expected != {"sha256": digest(data), "bytes": len(data)}:
                raise ValueError("saved artifact hash mismatch")
        return result

    def claim(self) -> None:
        """Use a persistent POSIX advisory lock. Process exit releases the lock."""
        if self._locked or self.attempt is not None:
            raise RuntimeError("store instances support one attempt")
        lock = self.root / "writer.lock"
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(fd)
            raise RuntimeError("another writer holds this run")
        self._lock_fd = fd
        self._locked = True
        try:
            payload = canonical_json({"pid": os.getpid(), "host": socket.gethostname(),
                                      "identity_sha256": self.identity_digest})
            os.ftruncate(fd, 0)
            offset = 0
            while offset < len(payload):
                written = os.write(fd, payload[offset:])
                if written <= 0:
                    raise OSError("writer lock metadata write failed")
                offset += written
            os.fsync(fd)
            if self.completed() is not None:
                raise RuntimeError("run already completed")
            identity_path = self.root / "identity.json"
            identity_bytes = canonical_json(self.identity)
            if identity_path.exists():
                if identity_path.is_symlink() or identity_path.read_bytes() != identity_bytes:
                    raise ValueError("run identity differs from saved identity")
            else:
                atomic_write(identity_path, identity_bytes)
            number = 1
            while True:
                attempt = self.root / f"attempt-{number:04d}"
                try:
                    attempt.mkdir()
                    break
                except FileExistsError:
                    number += 1
            self.attempt = attempt
            self.write_status({"status": "running", "started_unix_ns": time.time_ns()})
        except BaseException:
            self.close()
            raise

    def write_artifact(self, name: str, data: bytes) -> dict:
        if type(data) is not bytes:
            raise TypeError("artifact content must be bytes")
        path = self._path(name)
        if path.exists() or name in self.artifacts:
            raise ValueError("artifact already exists")
        atomic_write(path, data)
        metadata = {"sha256": digest(data), "bytes": len(data)}
        self.artifacts[name] = metadata
        return dict(metadata)

    def write_status(self, values: dict) -> None:
        if self.attempt is None or not self._locked or self._sealed:
            raise RuntimeError("an active, unsealed writer is required")
        result = dict(values, identity_sha256=self.identity_digest,
                      attempt=self.attempt.name, artifacts=dict(self.artifacts))
        atomic_write(self.attempt / "status.json", canonical_json(result))
        atomic_write(self.root / "result.json", canonical_json(result))

    def finish(self, result: dict) -> dict:
        if result.get("status") != "complete" or not self.artifacts:
            raise ValueError("finish requires complete status and saved artifacts")
        self.write_status(result)
        self._sealed = True
        return strict_json((self.root / "result.json").read_bytes())

    def close(self) -> None:
        if self._locked:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self._lock_fd)
                self._locked = False

    def __enter__(self):
        self.claim()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc is not None and self.attempt is not None and not self._sealed:
                self.write_status({"status": "failed", "failure": {
                    "kind": "exception", "type": exc_type.__name__, "message": str(exc)}})
        finally:
            self.close()
        return False
