"""Optional binary64 identity for the complete exact decoder parameter tree.

This encoding changes identifiers, not values or evaluation. Each numeric leaf
must be exactly representable in binary64. Every tree key and tensor shape is
bound. Signed zeros follow the existing Fraction conversion to positive zero.
No external digest cache replaces validation or source-file verification.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from fractions import Fraction
import hashlib
import json

from .binary64_identity import binary64_matrix_sha256
from .compact_exact import CompactDyadicMatrix, CompactDyadicVector


IDENTITY_ENCODING = "binary64_tree_v2"


def _is_exact_number(value):
    return type(value) is int or isinstance(value, Fraction)


def _is_vector(value):
    return type(value) is CompactDyadicVector or (
        isinstance(value, (tuple, list)) and bool(value) and all(_is_exact_number(x) for x in value))


def binary64_parameter_tree(value):
    """Return tagged tree metadata with one binary digest per numeric tensor."""
    if type(value) is CompactDyadicMatrix:
        return {"kind": "matrix", "shape": list(value.shape),
                "encoding": "binary64_matrix_v1", "sha256": binary64_matrix_sha256(value)}
    if _is_vector(value):
        matrix = value.matrix(1, len(value)) if type(value) is CompactDyadicVector else (value,)
        return {"kind": "vector", "shape": [len(value)],
                "encoding": "binary64_matrix_v1", "sha256": binary64_matrix_sha256(matrix)}
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise TypeError("parameter tree keys must be strings")
        return {"kind": "mapping", "items": [[key, binary64_parameter_tree(value[key])] for key in sorted(value)]}
    if isinstance(value, (tuple, list)):
        if value and all(_is_vector(row) for row in value):
            width = len(value[0])
            if any(len(row) != width for row in value):
                raise ValueError("parameter matrix must be rectangular")
            return {"kind": "matrix", "shape": [len(value), width],
                    "encoding": "binary64_matrix_v1", "sha256": binary64_matrix_sha256(value)}
        return {"kind": "sequence", "items": [binary64_parameter_tree(child) for child in value]}
    if _is_exact_number(value):
        return {"kind": "scalar", "encoding": "binary64_matrix_v1",
                "sha256": binary64_matrix_sha256(((value,),))}
    raise TypeError("parameter identity requires exact numeric tensors and named trees")


def binary64_parameter_sha256(parameters):
    payload = {"schema": "decoder-parameters-binary64-tree-v2", "tree": binary64_parameter_tree(parameters)}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
