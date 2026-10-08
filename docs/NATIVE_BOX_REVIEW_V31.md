# Independent numerical and integration review, revision 31

The reviewed V31 implementation has no identified arithmetic or integration blocker.
This clearance covers software correctness and bounded execution policy.
It does not establish empirical certificate acceptance, latency, memory fit, or publication novelty.
No empirical inference or campaign registration formed part of this review.

## Bound sources

| File | SHA256 |
|---|---|
| `src/native_box_coefficients_v31.py` | `c25b42dd2808e6a39017d81e036725e7a66f17337dcedb4ea5eaca0a0848909f` |
| `src/sparse_box_certificate_v31.py` | `cf20f87c6333e70755978ee29ed73fcff17f782be77b00cc5c8e0fd7571c688f` |
| `src/native_box_compressed_service_v31.py` | `2c495702e449e7fc1b007647b58482f603347b9aaa1f07f74336602be0da88a1` |
| `scripts/run_compressed_service_v31.py` | `8f69db8bb38eadaffee1551b5f53235849027ffb43decf18df4a041ecd2bc621` |
| `scripts/launch_compressed_service_v31.py` | `3ab6406166d42219f2ea87cbaf2c18a9a55a1300d5ead29353e0a76b99434650` |
| `campaigns/compressed_service_v31.spec.json` | `94442128d5610386af241da2e68d25968ed3ec85faec7aaa77e6606af652e024` |
| `docs/NATIVE_BOX_COEFFICIENTS_V31.md` | `7850ff6d488d73ba95e5dc68020da98ec479d2be06e606a38d66570432802e14` |

These hashes identify reviewed files before experimental registration.
Historical numerical sources, campaign snapshots, and adverse results remain unchanged.

## Universal arithmetic argument

For every realized feature matrix inside the supplied box, each suffix matrix satisfies

\[
B_i=\beta I+\sum_{h\ge i}z_hz_h^\top\succeq\beta I,
\qquad \beta>0.
\]

The native sweep encloses each realized matrix entry.
Diagonal products square one shared variable and preserve crossing-zero lower bounds.
Off-diagonal products enclose all endpoint combinations.
Dependencies between entries can widen residual bounds, but cannot invalidate their containment.

For any finite proposal \(p_i\), the residual enclosure contains \(z_i-B_ip_i\).
Its outward squared norm bound \(R_i^2\) gives

\[
\|B_i^{-1}z_i-p_i\|_2^2
\le \|z_i-B_ip_i\|_2^2/\beta^2
\le R_i^2/b_2
\le E_i,
\]

where \(0<b_2\le\beta^2\) is verified using the original directed ridge initializer.
The SPD premise concerns realized Gram matrices, not arbitrary matrices assembled from independent interval endpoints.
No accuracy, symmetry, or positive-definiteness assumption about the nominal inverse enters this proof.

The native schedule retains the Python builder's reverse suffix order and Gram-before-proposal order.
Residual products and squared norms retain ascending token reductions.
Zero-addend handling matches the coefficient reference, including omission of the row kernel's cancellation shortcut.
Strict compiler flags prohibit contraction and fast-math reassociation.
Runtime checks require binary64, nearest rounding, and gradual underflow.
Unsupported finite ranges refuse instead of producing certificate evidence.

Inputs must remain unchanged during each call.
The implementation does not replace an uncertain box with its midpoint.
Midpoints and Sherman–Morrison updates generate untrusted proposals only.
Invalid nominal updates use the existing zero-proposal policy, followed by the same universal residual proof.

## Sparse integration and resource scope

The wrapper retains the exact V30 budget class and requested-coordinate refinement helpers.
Refinement verifies the original proposals and intersects radii about those same centers.
Its coordinate, round, and structural work limits remain unchanged.
No eager full preconditioner, point substitution, or unbounded fallback was introduced.

The initial sparse reservation dominates the helper's \(dT^2+dT+d\) work proxy.
The complete sparse array allowance also dominates the helper's allowance.
The helper therefore needs no second cumulative charge inside the initial reserved phase.
Standalone admission still precedes value scans, numerical allocation, and compilation.
These are structural and engineering bounds, not elapsed-time or whole-process RSS guarantees.

The review requested explicit proposal alignment before legacy row paths.
The final wrapper includes that alignment and a regression using deliberately unaligned evidence.
Numerical values and immutable output ownership remain unchanged.
Compilation diagnostics remain nested within coefficient timing and must not be added twice.

## Worker and prospective comparison

The worker requires the ordered decoder, sparse certificate route, forty-eight-bit descriptors, and block size 256.
Conversion starts from the verified original lossless state and checks every enclosure.
Repair requires that new conversion's completion, source identity, and descriptor precision.
It cannot relabel the forty-bit archive as a forty-eight-bit preparation.

The service preserves the fixed-feature mathematical target and point solver.
Point replay and cold reconstruction share the reviewed ordered neural execution and bounded point implementation.
The specification retains exact comparisons against archived retained models and the forty-bit result.
Its latency gate uses the minimum of all three optimized cold observations.
It also retains lossless timing and complete storage as visible comparators.

The proposed intervention changes implementation and descriptor precision together.
It cannot isolate a causal precision effect from an implementation effect.
The eight extra descriptor bits reduce nominal block steps by 256 only where the minimum-subnormal floor does not bind.
Neither change guarantees certificate acceptance or a complete-model speedup.
The V30 compressed latency failure remains part of the evidence.

## Independent software verification

The following combined suite passed 23 tests in 1.459 seconds:

```bash
python -m unittest tests.test_native_box_coefficients_v31 tests.test_sparse_box_certificate_v31 tests.test_native_box_service_v31 tests.test_native_box_review_v31 -q
```

That duration is software test output, not an empirical speed measurement.
The suite covers exact rational containment, reference encodings, correlated squares, signed zeros, subnormals, alignment, and finite refusal.
It also covers resource admission, requested refinement, conversion provenance, and complete miniature service equality.

The independent adversarial fixture supplies a finite, nonsymmetric, incorrect nominal inverse.
It preserves the correct directed Gram initialization.
The resulting proposals differ from ordinary proposals and remain nonzero without triggering reset.
All 64 rational corners and three interior realizations satisfy every returned squared error bound.
This fixture directly checks that inaccurate finite proposals remain untrusted.

| Test source | SHA256 |
|---|---|
| `tests/test_native_box_coefficients_v31.py` | `5781795e1d09034c90a95f73e7dbc843a86fd60fea0815ed6fa3f66778e007f2` |
| `tests/test_sparse_box_certificate_v31.py` | `f1763995eefc7ccc00d5f1d88852b9aa23d108fd9acf63f6af3d30a5aa7b662e` |
| `tests/test_native_box_service_v31.py` | `bb6c7898687bc3f73b182f13dd821928f18d06b081419f2c8dff60ce7298a95b` |
| `tests/test_native_box_review_v31.py` | `cb1a303c78fa74788e8f5283f27fe03e710835a035f0d289aaf6780883b05d9e` |

Tests support the reviewed implementation; they do not replace the universal enclosure argument.
Successful resource admission likewise does not establish practical completion.
Any empirical conclusion requires the separate registered full transaction and its sealed cost evidence.
