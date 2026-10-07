# Finite feature boxes

This module bounds the declared binary64 decoder.
It does not bound an ideal real-valued decoder.
It does not certify native GPTQ, CUDA, or Hugging Face execution.

The implementation supports fixed weights and intervals of installed weights.
Each interval contains finite binary64 values.
The implementation uses immutable NumPy arrays for endpoints.

## Interface

```python
from src.finite_feature_boxes import (
    FloatBox, sequential_feature_boxes, feature_box, logits_box,
)

stream = sequential_feature_boxes(decoder, tokens)
stage_id, features = next(stream)
stage_id, features = stream.send(installed_matrix)

# Each feature box has shape [token_count, input_width].
# A weight box has shape [output_width, input_width].
candidate_weights = FloatBox(lower_weights, upper_weights)
box = feature_box(decoder, tokens, {ancestor_stage: candidate_weights}, stage)
full_output = logits_box(decoder, tokens, installed_prefix)
```

`sequential_feature_boxes` follows the existing sequential stage order.
It yields each stage input before applying that stage's installed weights.
Its final stage needs no output calculation by default.
With `include_logits=True`, its return value contains the final output box.

`feature_box` evaluates one stage input from the supplied tokens and prefix.
`logits_box` also evaluates the final normalization and language head.
Missing prefix entries use the decoder's base weights.

Float conversion follows the finite decoder's input convention.
An input rational is converted to binary64 first.
These constructors do not provide outward conversion for arbitrary real intervals.
Such callers must supply outward binary64 endpoints.

## Guarantee

Fix validated tokens and the declared certified decoder.
For each installed stage, choose a binary64 matrix inside its supplied box.
Suppose the interval calculation completes without rejection.
Then each reported box contains that choice's finite stage input.
The final output box has the same guarantee when requested.

Containment uses numerical order, which identifies both signed zeros.
It does not assign separate order positions to signed-zero encodings.
Point executions preserve the supplied point arithmetic schedule.

The guarantee applies to the selected primitive backend's completion domain.
It does not assert equal completion domains across primitive backends.

## Proof

Let RN denote correctly rounded binary64 conversion under round-to-nearest-even.
RN is monotone on finite ordered real inputs.
Therefore, evaluating RN at ordered operation extrema bounds every finite result.

For addition, extrema occur at the corresponding lower and upper endpoints.
Negation is exact and reverses endpoints.
For multiplication, extrema occur among four corner products.
Division uses four corners when the denominator interval excludes zero.
The implementation evaluates each corner using the target binary64 operation.

These endpoints enclose machine results directly.
They need no extra outward ulp for this finite target.
They are not generally enclosures of the underlying exact real operation.

Squaring uses the same operand twice.
Its lower bound is zero when the interval contains zero.
Otherwise, its extrema occur at squared endpoints.
This correlation avoids a negative variance bound from generic interval multiplication.

The four primitive functions are monotone on their permitted domains.
The existing primitive implementation proves each endpoint's correctly rounded result.
Unresolved endpoint rounding rejects the calculation.

Each dot product follows the declared coordinate order.
It performs a separate multiplication followed by addition at each coordinate.
It never uses a BLAS reduction or fused multiplication and addition.
Array operations batch independent coordinates only.

Normalization preserves the declared mean and variance schedules.
It uses the configured epsilon without modification.
Both activation functions preserve their declared operation order and constants.

Attention preserves the causal mask and head order.
It uses the declared correctly rounded square-root divisor.
The maximum score lies between the maxima of score endpoints.
Subtracting its box encloses each finite shifted score.
Every actual shifted score is nonpositive, so the upper bound can intersect zero.

At least one score equals the selected maximum exactly.
Its shifted score is zero, and its exponential is one.
All other exponentials are nonnegative.
The declared ordered denominator sum is therefore at least one.
This fact permits intersection of its lower bound with one.

Every finite softmax probability lies between zero and one.
The implementation intersects probability boxes with that interval.
Attention then follows the declared ordered weighted sum.

Induction through the operation schedule proves each block's enclosure.
Induction through installed stages proves the sequential guarantee.
The final normalization and head use the same argument.

## Runtime and rejection

Generator entry and each advancement check the binary64 runtime.
Checks require round-to-nearest-even and gradual underflow.
Separate vector probes check subnormal arithmetic and a rounding tie.
The primitive backend scope cannot leak across a suspended generator.

Nonfinite inputs, endpoint overflow, invalid dimensions, and zero-containing denominators reject the calculation.
Wide boxes can reject even when a selected point execution would complete.
This conservative rejection does not invalidate successful enclosures.
Direct low-level FloatBox operations assume the same checked runtime.

Endpoint arrays own immutable bytes.
External array changes cannot alter a box after construction.

## Cost and limits

This implementation reads the retained record's tokens.
Its interval execution counts as retained-source work.
It does not establish avoided feature evaluation after an ancestor changes.
It does not yet use an anchor trace or a stored response certificate.

Fixed installed matrices produce point boxes without artificial width growth.
Uncertain matrices can produce wide boxes through normalization and attention.
Useful width, computation cost, and memory cost require real measurements.
No full-model repair speedup follows from this module.

This module does not construct a canonical repair state.
It does not repair or certify the quantizer's token-space system.
Those integrations need separate contracts and tests.

## Software checks

Six tests cover every stage and the final output on small decoder fixtures.
Checks include two blocks, two head settings, both activations, and both primitive backends.
Every fixed-prefix stage matches the reference finite values exactly.
Interval prefixes contain several changed-prefix point executions.
Other checks cover arithmetic corners, primitives, subnormals, immutable storage, and invalid inputs.

Command:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m unittest tests.test_finite_feature_boxes_v13 -v
```

The six tests passed in this session.
These fixtures are software checks, not empirical research datasets.
