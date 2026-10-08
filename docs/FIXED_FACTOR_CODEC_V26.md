# Wider packed factor enclosures

Revision 26 extends packed dyadic cells to 16, 24, 32, 40, and 48 bits.
It uses a separate module, schema, magic version, and source binding.
Revision 24 remains unchanged.
The existing compressed state and repair service remain unchanged.

Wider cells use more storage and give narrower factor bounds.
They may reduce failures of output certification.
No certificate acceptance or speed improvement follows from this component alone.
No real-data execution forms part of this revision.

## Interface and version boundary

`src/fixed_factor_codec_v26.py` preserves the descriptor interface from revision 24.
It provides `encode_factor`, `FactorDescriptor`, `serialize`, `parse`, and `LoadLimits`.
Its descriptor exposes `box()`, `center_radius()`, `escape_count`, and `digest`.

The schema is `source-local-dyadic-factor-enclosure-v2`.
The magic is `VCFC`, version two.
Revision 24 parsers reject these files.
The descriptor binds its target, source identifier, tokens, stage, shape, precision, and original factor hash.

The module copies the exact arithmetic from revision 24.
It imports no arithmetic primitives from that codec.
`codec_dependencies()` identifies the new module and its two shared project helpers.
`codec_binding()` hashes that canonical source manifest.
The helpers are `compact_state.py` and `finite_feature_boxes.py`.
Their bindings cover canonical metadata and the returned immutable box type.
Runtime package versions remain the enclosing program's responsibility.

The 16-bit and 24-bit payloads preserve the previous arithmetic and packing.
Their complete descriptor bytes differ because version and source bindings differ.

## Exact cells and representable endpoints

Fix one block and precision \(b\in\{16,24,32,40,48\}\).
Let \(t\) be its largest binary exponent, with zero assigned exponent \(-1074\).
Define

\[
e_b=\max\{t-(b-2),-1074\},\qquad \Delta_b=2^{e_b}.
\]

For a finite source value \(x\), integer bit operations compute

\[
k_b=\lfloor x/\Delta_b\rfloor.
\]

No floating division computes this integer.
An exact grid value gets the singleton interval \([x,x]\).
Other values get

\[
[k_b\Delta_b,(k_b+1)\Delta_b].
\]

The packed signed integer uses exactly \(b/8\) bytes.
Its range contains every generated cell index.
Indeed, \(|x|<2^{t+1}\) implies \(|x|/\Delta_b<2^{b-1}\).
The lower clamp only decreases this quotient.
Negative flooring can reach \(-2^{b-1}\), which remains representable.

Each endpoint coefficient has at most \(b\) binary digits.
Thus, even at 48 bits, it fits binary64's 53-digit significand.
Trailing powers of two reduce the required significand further.
The lower exponent clamp prevents a value below the smallest positive subnormal step.

For \(e_b>-1074\), the symmetric representation uses

\[
c_b=(2k_b+1)2^{e_b-1},\qquad r_b=2^{e_b-1}.
\]

The center coefficient has at most \(b+1\le49\) binary digits.
This conservative bound leaves room within binary64's 53-digit significand.
The midpoint and radius therefore remain exact when finite.
At the smallest subnormal step, the implementation uses the lower endpoint and one full-step radius.
This avoids an unrepresentable half-step radius.
Singleton cells and escapes have zero radius.

## Overflow and nested refinement

All precisions share the revision 24 escape guard:

\[
G=32767\cdot2^{1009}
=\texttt{0x1.fffc000000000p+1023}.
\]

Values with \(|x|>G\) use their exact binary64 words as escapes.
The escape choice is independent of precision.
For the largest exponent, \(G\) lies exactly on every supported dyadic grid.
Therefore, nonescaped endpoints remain bounded by \(G\).
Their centers lie between their endpoints.
Endpoints, centers, and radii remain finite.

Fix the source values, block partition, and block maxima.
For \(b'>b\), \(e_{b'}\le e_b\), and every coarse boundary lies on the finer grid.
Thus, each finer cell lies inside its coarse cell.
A coarse singleton remains a singleton under refinement.
An escaped value remains the same singleton at every precision.
Consequently,

\[
\operatorname{box}_{48}(x)
\subseteq\operatorname{box}_{40}(x)
\subseteq\operatorname{box}_{32}(x)
\subseteq\operatorname{box}_{24}(x)
\subseteq\operatorname{box}_{16}(x).
\]

Changing the block partition is outside this nesting statement.
The symmetric center-radius box can be wider at the smallest subnormal step.
The direct endpoint box defines the stated nesting guarantee.

Numeric zero endpoints use positive zero.
The original factor hash still binds signed-zero source bytes.
The parser rejects reserved flags, nonzero padding, invalid exponents, and unnecessary exact escapes.
It also rejects unsupported precisions and noncanonical headers.

## Trust and measurement limits

Trusted source preparation establishes containment.
Self-consistent hashes cannot prove containment for an unavailable source.
Parsing checks structure, bounds, and declared content bindings.
It does not establish the original preparation history.

The software fixtures cover every finite exponent class and all supported precisions.
They cover subnormals, signed zeros, overflow guards, exact rational bounds, and nested cells.
They also cover actual integer packing, immutable output arrays, version rejection, and parser bounds.

These tests do not establish useful certification rates.
Higher precision also increases decode cost and stored bytes.
A registered diagnostic must measure these effects before service integration.
