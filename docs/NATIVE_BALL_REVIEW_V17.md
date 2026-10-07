# Revision 17: independent native certificate review

Status: mathematical and source review.
No empirical run occurred during this review.
This review is not formal proof verification.

Reviewed files:

| File | SHA-256 |
|---|---|
| `src/native_ball_quantizer.py` | `543929a1cec335d8b111952b1d24d998d2420cc7abab734f5153e2b201069084` |
| `docs/NATIVE_BALL_PROOF_V17.md` | `612823e36686b577b795a3fbd2bd0ba426f983358c092beb564692d1aa40a8a4` |
| `tests/test_native_ball_v17.py` | `29cd86e68b2e7e6bd95e30c38455792a4d3e7ba752bb7a55a7607e5873063a30` |

## Findings

The reviewed proof and source contain no identified correctness defect.
This conclusion depends on their stated runtime and input premises.
The final review includes the corrected diagnostic counters.
The attempted count increments before each decision.
It therefore includes the first uncertain decision in a stopped row.
The separate prefix count increments after a certified decision and finite accumulator update.
The wrapper allocates four counters and reports both counts separately.
These changes do not alter the numerical certificate.

The accumulator proof includes subtraction, multiplication, accumulation, and absolute-sum errors.
Its positive-sum lower bound covers the observed absolute sum's possible underestimation.
The accumulator coefficient exceeds the proved error coefficient under the declared dimension limit.

For clarity, let t=iu, where i is the coordinate index.
The relevant coefficient is

\[
\frac{\gamma_i+6u}{1-iu}
=u\left(\frac{i}{(1-t)^2}+\frac{6}{1-t}\right).
\]

The declared limit gives t no larger than 2^-33.
Both denominator factors are then smaller than two.
Consequently, the coefficient is smaller than 2(i+6)u.

The additive floor also covers underflow in the rounded residual products.
Its ratio to the smallest subnormal is 2^74.
This exceeds the maximum dimension factor in the supplied underflow argument.

The decision proof separates three error sources.
These are accumulator error, coefficient error, and native dot-product error.
The dot-product argument permits cancellation.
The coefficient error uses a valid Euclidean bound and a conservative accumulator norm.
The exact square check protects the coefficient radius from an underestimated square root.

The source rounds each nonnegative bound operation outward.
Multiplication by two preserves the exact value unless it overflows.
Nonfinite results prevent native acceptance.
An unsupported runtime also prevents native acceptance.

Cell checks implement the declared lower-code tie rule conservatively.
An uncertain native row enters the existing certified solver.
All uncertain rows enter one solver call.
Therefore, exact and refinement limits remain global across those rows.
The native path consumes neither budget before this fallback.
Fallback failure prevents a returned model.

## Scientific boundary

A candidate changes only the first cell checked.
It does not change accumulator work, coefficient work, or decision arithmetic.
Candidate hits can save a grid search.
Candidate validation and unsuccessful checks can add work.

Thus, a native speed gain over the former Python solver demonstrates common implementation progress.
It does not establish a repair advantage over the same fresh native solver.
It also does not establish an advantage over the warm model-only comparator.

The complete feature replay issue remains separate.
Read `BLOCK_LOW_RANK_DESIGN_V17.md` for that implementation boundary.
No reviewed theorem proves a reliable full-model speedup.

## Remaining review scope

This review does not verify the compiler or processor formally.
It does not measure real-model speed or language-model quality.
Software test outcomes belong in the separate test log.
Any material change to the numerical source requires renewed review.
