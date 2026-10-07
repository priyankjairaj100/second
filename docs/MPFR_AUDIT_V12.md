# Independent MPFR audit

The audit covered finite_primitives.py and its decoder and sequential-generator integrations.
It found a mutable identity binding and fixed it.
The manifest cache now stores bytes and returns independent dictionaries.

Each MPFR enclosure uses explicit precision, exponent limits, rounding direction, and disabled traps.
The exponent interval is [-16384, 16384].
Direct MPFR calls accept finite binary64 inputs with absolute value at most 1024.
Larger arguments use the rational reference path.
Inputs convert exactly because working precision is at least 64 bits.
Directed MPFR endpoints convert to exact rational endpoints.
The existing integer-based binary64 rounder accepts only identical endpoint encodings.

The audit found no enclosure error under MPFR's directed-rounding contract.
Backend scopes restore after decoder calls, generator suspension, exhaustion, and exceptions.
The MPFR backend preserves finite values on the common completion domain.
The audit does not claim identical completion domains, resource use, or rejection behavior.
Backend selection and binary identities enter the decoder binding.

Validation used OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1, and MKL_NUM_THREADS=1.
Fifteen primitive, sequential-generator, and certified-decoder tests passed in 6.654 seconds.
New checks covered hostile ambient contexts, manifest mutation, scoped generators, precision rejection, and exceptions.
Compilation and whitespace checks passed.
No research experiments ran during this audit.
