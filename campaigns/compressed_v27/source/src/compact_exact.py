"""Immutable compact storage for checkpoint dyadics and canonical streaming.

Each element decodes to the same Fraction as Fraction.from_float(source).
The float view equals float(that Fraction), including conversion of -0 to +0.
No floating arithmetic replaces exact arithmetic. General rationals stay exact.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
import math
import operator
import struct
from typing import Any


_FORMATS = {"F16": (2, "e"), "BF16": (2, "H"), "F32": (4, "f"), "F64": (8, "d")}


@dataclass(frozen=True, slots=True)
class _Storage:
    data: bytes = field(repr=False)
    dtype: str

    def __post_init__(self) -> None:
        if type(self.data) is not bytes:
            raise TypeError("compact storage requires immutable bytes")
        if self.dtype not in _FORMATS:
            raise ValueError("unsupported compact storage dtype")
        width, code = _FORMATS[self.dtype]
        if len(self.data) % width:
            raise ValueError("compact storage byte length does not match dtype")
        for value, in struct.iter_unpack("<" + code, self.data):
            if self.dtype == "BF16":
                value = struct.unpack("<f", struct.pack("<I", value << 16))[0]
            if not math.isfinite(value):
                raise ValueError("nonfinite compact value")

    def __len__(self) -> int:
        return len(self.data) // _FORMATS[self.dtype][0]

    def value(self, index: int) -> float:
        width, code = _FORMATS[self.dtype]
        value = struct.unpack_from("<" + code, self.data, index * width)[0]
        if self.dtype == "BF16":
            value = struct.unpack("<f", struct.pack("<I", value << 16))[0]
        # Fractions do not retain a signed zero. Match the existing target.
        return 0.0 if value == 0 else float(value)


def _index(index: int, size: int) -> int:
    index = operator.index(index)
    if index < 0:
        index += size
    if not 0 <= index < size:
        raise IndexError("compact sequence index out of range")
    return index


@dataclass(frozen=True, slots=True, eq=False)
class CompactDyadicVector(Sequence[Fraction]):
    """An immutable strided exact view, with constant storage per view."""

    _storage: _Storage
    _offset: int
    _length: int
    _stride: int = 1
    __hash__ = None

    def __post_init__(self) -> None:
        if type(self._storage) is not _Storage:
            raise TypeError("invalid compact storage")
        if any(type(x) is not int for x in (self._offset, self._length, self._stride)):
            raise TypeError("compact dimensions must be integers")
        if self._length < 0 or self._stride == 0:
            raise ValueError("invalid compact vector dimensions")
        if self._length:
            endpoints = (self._offset, self._offset + (self._length - 1) * self._stride)
            if min(endpoints) < 0 or max(endpoints) >= len(self._storage):
                raise ValueError("compact vector exceeds storage")

    @classmethod
    def from_bytes(cls, data: bytes, dtype: str) -> CompactDyadicVector:
        storage = _Storage(data, dtype)
        return cls(storage, 0, len(storage))

    def __len__(self) -> int:
        return self._length

    def __getitem__(self, index: int | slice) -> Fraction | CompactDyadicVector:
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            return CompactDyadicVector(self._storage, self._offset + start * self._stride,
                                       len(range(start, stop, step)), self._stride * step)
        return Fraction.from_float(self._storage.value(self._offset + _index(index, len(self)) * self._stride))

    def __iter__(self) -> Iterator[Fraction]:
        return (Fraction.from_float(value) for value in self.floats())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sequence):
            return NotImplemented
        if len(self) != len(other):
            return False
        if isinstance(other, CompactDyadicVector):
            return self is other or all(a == b for a, b in zip(self.floats(), other.floats()))
        return all(a == b for a, b in zip(self, other))

    def floats(self) -> CompactFloatVector:
        return CompactFloatVector(self)

    def float_array(self):
        """Return a read-only NumPy binary64 array when NumPy is available."""
        import numpy as np
        storage = self._storage
        dtype = {"F16": "<f2", "F32": "<f4", "F64": "<f8", "BF16": "<u2"}[storage.dtype]
        base = np.frombuffer(storage.data, dtype=dtype)
        # A negative Python stop changes meaning. Use explicit strides instead.
        view = np.ndarray((self._length,), dtype=base.dtype, buffer=storage.data,
                          offset=self._offset * base.dtype.itemsize,
                          strides=(self._stride * base.dtype.itemsize,)) if self._length else base[:0]
        if storage.dtype == "BF16":
            view = (view.astype(np.uint32) << 16).view(np.float32)
        out = view.astype(np.float64, copy=False)
        if np.any((out == 0) & np.signbit(out)):
            out = out.copy()
            out[out == 0] = 0.0
        out.setflags(write=False)
        return out

    def matrix(self, rows: int, columns: int, *, transpose: bool = False) -> CompactDyadicMatrix:
        if type(rows) is not int or type(columns) is not int or rows < 0 or columns < 0:
            raise ValueError("invalid compact matrix dimensions")
        if len(self) != rows * columns:
            raise ValueError("matrix dimensions do not match compact vector")
        if transpose:
            return CompactDyadicMatrix(self._storage, self._offset, columns, rows,
                                        self._stride, columns * self._stride)
        return CompactDyadicMatrix(self._storage, self._offset, rows, columns,
                                    columns * self._stride, self._stride)


@dataclass(frozen=True, slots=True, eq=False)
class CompactDyadicMatrix(Sequence[CompactDyadicVector]):
    """An immutable matrix with zero-copy transposed and row views."""

    _storage: _Storage
    _offset: int
    _rows: int
    _columns: int
    _row_stride: int
    _column_stride: int
    __hash__ = None

    def __post_init__(self) -> None:
        if type(self._storage) is not _Storage:
            raise TypeError("invalid compact storage")
        dims = (self._offset, self._rows, self._columns, self._row_stride, self._column_stride)
        if any(type(x) is not int for x in dims):
            raise TypeError("compact dimensions must be integers")
        if self._rows < 0 or self._columns < 0:
            raise ValueError("invalid compact matrix dimensions")
        if self._rows and self._columns:
            corners = [self._offset + i * self._row_stride + j * self._column_stride
                       for i in (0, self._rows - 1) for j in (0, self._columns - 1)]
            if min(corners) < 0 or max(corners) >= len(self._storage):
                raise ValueError("compact matrix exceeds storage")

    @property
    def shape(self) -> tuple[int, int]:
        return self._rows, self._columns

    @property
    def storage_bytes(self) -> int:
        return len(self._storage.data)

    def __len__(self) -> int:
        return self._rows

    def __getitem__(self, index: int | slice) -> CompactDyadicVector | CompactDyadicMatrix:
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            return CompactDyadicMatrix(self._storage, self._offset + start * self._row_stride,
                                        len(range(start, stop, step)), self._columns,
                                        step * self._row_stride, self._column_stride)
        return CompactDyadicVector(self._storage, self._offset + _index(index, len(self)) * self._row_stride,
                                   self._columns, self._column_stride)

    def __iter__(self) -> Iterator[CompactDyadicVector]:
        return (self[index] for index in range(len(self)))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sequence):
            return NotImplemented
        return self is other or (len(self) == len(other) and all(a == b for a, b in zip(self, other)))

    def floats(self) -> CompactFloatMatrix:
        return CompactFloatMatrix(self)

    def float_rows(self) -> CompactFloatMatrix:
        return self.floats()

    def float_array(self):
        """Return a read-only NumPy binary64 matrix when NumPy is available."""
        import numpy as np
        storage = self._storage
        dtype = np.dtype({"F16": "<f2", "F32": "<f4", "F64": "<f8", "BF16": "<u2"}[storage.dtype])
        if self._rows and self._columns:
            view = np.ndarray(self.shape, dtype=dtype, buffer=storage.data,
                              offset=self._offset * dtype.itemsize,
                              strides=(self._row_stride * dtype.itemsize, self._column_stride * dtype.itemsize))
        else:
            view = np.empty(self.shape, dtype=dtype)
        if storage.dtype == "BF16":
            view = (view.astype(np.uint32) << 16).view(np.float32)
        out = view.astype(np.float64, copy=False)
        if np.any((out == 0) & np.signbit(out)):
            out = out.copy()
            out[out == 0] = 0.0
        out.setflags(write=False)
        return out


@dataclass(frozen=True, slots=True, eq=False)
class CompactFloatVector(Sequence[float]):
    """Finite values from an exact view without allocating a float tuple."""

    exact: CompactDyadicVector
    __hash__ = None

    def __len__(self) -> int:
        return len(self.exact)

    def __getitem__(self, index: int | slice) -> float | CompactFloatVector:
        if isinstance(index, slice):
            return self.exact[index].floats()
        exact = self.exact
        return exact._storage.value(exact._offset + _index(index, len(self)) * exact._stride)

    def __iter__(self) -> Iterator[float]:
        exact = self.exact
        return (exact._storage.value(exact._offset + index * exact._stride) for index in range(len(self)))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sequence):
            return NotImplemented
        return len(self) == len(other) and all(a == b for a, b in zip(self, other))


@dataclass(frozen=True, slots=True, eq=False)
class CompactFloatMatrix(Sequence[CompactFloatVector]):
    exact: CompactDyadicMatrix
    __hash__ = None

    def float_array(self):
        return self.exact.float_array()

    def __len__(self) -> int:
        return len(self.exact)

    def __getitem__(self, index: int | slice) -> CompactFloatVector | CompactFloatMatrix:
        return self.exact[index].floats()

    def __iter__(self) -> Iterator[CompactFloatVector]:
        return (row.floats() for row in self.exact)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sequence):
            return NotImplemented
        return len(self) == len(other) and all(a == b for a, b in zip(self, other))


def _json_scalar(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def iter_exact_json(value: Any) -> Iterator[bytes]:
    """Yield the canonical JSON bytes previously produced by _serial_exact.

    Fractions use decimal numerator and denominator strings. Object keys use
    string conversion, last-wins collisions, sorting, and standard JSON escapes.
    Live temporary storage depends on nesting and a single value, not tensor size.
    """
    if isinstance(value, Fraction):
        yield b'["' + str(value.numerator).encode("ascii") + b'","' + str(value.denominator).encode("ascii") + b'"]'
    elif isinstance(value, CompactDyadicVector):
        yield b"["
        for index, child in enumerate(value.floats()):
            if index:
                yield b","
            numerator, denominator = child.as_integer_ratio()
            yield b'["' + str(numerator).encode("ascii") + b'","' + str(denominator).encode("ascii") + b'"]'
        yield b"]"
    elif isinstance(value, Mapping):
        mapping = {str(key): child for key, child in value.items()}
        yield b"{"
        for index, key in enumerate(sorted(mapping)):
            if index:
                yield b","
            yield _json_scalar(key)
            yield b":"
            yield from iter_exact_json(mapping[key])
        yield b"}"
    elif isinstance(value, (tuple, list, CompactDyadicVector, CompactDyadicMatrix)):
        yield b"["
        for index, child in enumerate(value):
            if index:
                yield b","
            yield from iter_exact_json(child)
        yield b"]"
    else:
        yield _json_scalar(value)


def exact_json_sha256(value: Any, *, buffer_bytes: int = 65536) -> str:
    """Hash canonical exact JSON without materializing the complete document."""
    if type(buffer_bytes) is not int or buffer_bytes < 1:
        raise ValueError("buffer_bytes must be a positive integer")
    digest = hashlib.sha256()
    buffer = bytearray()
    for part in iter_exact_json(value):
        if len(buffer) + len(part) > buffer_bytes:
            digest.update(buffer)
            buffer.clear()
        if len(part) > buffer_bytes:
            digest.update(part)
        else:
            buffer.extend(part)
    digest.update(buffer)
    return digest.hexdigest()
