# Independent ordered decoder review

The reviewed implementation preserves the declared finite target on the common completion domain.
No numerical blocker was found at these source hashes.

| Source | SHA-256 |
|---|---|
| `src/ordered_attention_v30.py` | `cd27378a1814b7407ae61ed99a1e69b34b382659795df56c39da666292fd71f8` |
| `src/ordered_finite_decoder_v30.py` | `ab490c42759297709f36ae5b8e94485d0e3d80370ced061e21ce9a11764d043a` |

This review supersedes the earlier attention-only review for these sources.
It covers the generalized primitive helper and the explicit decoder integration.
It does not establish empirical speed or review the entire service controller.

## Directed primitive endpoints

Each ordinary binary64 argument converts exactly within the explicit 104-bit MPFR contexts.
The contexts bind rounding direction, exponent limits, subnormal behavior, and exception settings.
They restore the ambient context before endpoint conversion and fallback.

For each supported primitive, directed endpoints enclose its exact real value.
Endpoint conversion uses the public exact integer ratio and the repository's integer-based binary64 rounding.
Equal endpoint encodings therefore determine one nearest-even binary64 result.
No approximate float conversion enters the acceptance decision.

The exponent range covers the ordinary arguments and their nonzero results.
The ordinary arguments satisfy absolute value at most 1024.
Square-root arguments are nonnegative.
Zero is handled separately, preserving signed zero for square root, tanh, and erf.
The exponential returns one for either zero encoding.

Arguments outside the ordinary range retain the original fallback.
Negative square-root arguments also retain its rejection behavior.
Ambiguous endpoint encodings use the same fallback after both contexts exit.
Nonfinite input values are rejected before evaluation.

The helper can accept inputs where the older absolute enclosure exhausted its precision allowance.
Consequently, identical refusal behavior is explicitly excluded.
The claim concerns equal accepted finite values wherever both implementations complete.

## Finite arithmetic schedule

Attention evaluates only causal pairs.
Each score visits head coordinates in the original order.
Each product occupies a separate temporary before addition.
The maximum uses strict comparisons and therefore preserves the first maximizing key.
Subtraction uses the original negation-and-addition schedule.
Softmax denominators and weighted values visit keys in ascending order.

Activation batching changes only the order among independent entries.
The erf form retains the original half-product, division, primitive, addition, and final product.
The tanh form retains all three left-associated cubic products.
It also retains the declared binary64 coefficient.
Separate NumPy operations prevent contraction across these steps.

Runtime checks retain the binary64, nearest-rounding, and gradual-underflow premises.
The caller must not change the floating-point environment during evaluation.
Independent batching can alter which error occurs first.
Neither equal exception order nor equal memory behavior is claimed.

## Decoder and installed prefixes

The full executor preserves every stage dependency and residual addition.
Its stage stop points match the original executor.
The sequential generator installs each supplied stage before computing the next stage input.
An independent restart check verified every yielded stage after each installed matrix.
This check uses the reference decoder directly, rather than another incremental generator.

The last stage output remains unnecessary when generating calibration inputs only.
The implementation therefore retains the established final-stage shortcut.
Each generator advancement enters and restores its primitive scope.
Suspension, shape failures, explicit exceptions, and closure leave no active primitive scope.

Prepared prefixes retain immutable installed matrices and the original validation rules.
The existing fixtures verify prepared logits and protected state.

## Target identity and execution provenance

The inherited evaluator identity denotes the unchanged finite model target.
The separate implementation manifest binds the new execution sources and NumPy version.
Its mutable return value cannot change the decoder's stored manifest.
No global function replacement enables the optimization.

The ordered services use a distinct preparation binding.
Historical state must not be relabeled as newly prepared state.
The service integration requires separate review and complete model equality checks.
Execution receipts must retain the implementation manifest alongside the target identity.

## Focused verification

The existing attention, endpoint, and decoder suites passed 22 fixtures in 0.223 seconds.
Six independent fixtures then passed in 0.088 seconds.
These reported durations are software test output, not empirical timing evidence.

The additional fixtures cover these cases:

- Adjacent exponential arguments around binary64 overflow and rounding to zero.
- Noncontiguous arrays under hostile ambient MPFR settings for all four primitives.
- Context restoration when an ambiguous primitive fallback raises.
- Independent reference restarts after every installed stage across two blocks.
- Generator failures and explicit exceptions without primitive-scope leakage.
- Current execution source hashes with unchanged target identity.

The fixtures reside in `tests/test_ordered_decoder_review_v30.py`.
No empirical worker ran during this review.
No numerical source or frozen campaign snapshot changed.
Real feature identity and complete timing comparisons remain empirical gates.
