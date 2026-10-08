# Remove redundant exact-value scans during evaluator setup

The revision 21 quality worker spent 87.781431140 seconds between model serialization and its first evaluation record.
That interval includes comparator parsing, code conversion, and both evaluator constructions.
It is not an isolated measurement of the redundant scan.
The complete worker still finished within its registered limit.
No interruption occurred.

`PreparedFinitePrefix` previously sent every compact matrix through the generic prefix validator.
That validator iterates each element and constructs a `Fraction` to check its type.
The compact storage constructor already validates every encoded value as finite.
The exact matrix class owns immutable bytes and exposes only exact dyadic values.
The additional element scan therefore adds no validation for this exact class.

The new path checks each stage identifier and matrix shape.
It then installs the same immutable floating view used by the original path.
Other representations still use the complete generic validation.
Subclasses do not receive the shortcut.

For a validated compact matrix `M`, the original conversion is

\[
\operatorname{floats}(\operatorname{matrix}(M))=M.\operatorname{floats}().
\]

The matrix validator returns `M` after checking its dimensions.
The new path performs that dimension check directly.
Both paths normalize signed zeros identically.
No decoder arithmetic, reduction order, or quantizer target changes.

Eight focused tests passed.
They compare output bits against the original decoder path.
They cover all four compact storage formats, reversed strides, and mixed representations.
They also cover malformed shapes, unknown stages, immutable capture, and subclass rejection.
A guarded iterator test establishes that compact setup performs no element iteration.

The setup scan changes from linear work in installed coordinates to work in installed stages.
Storage construction and code conversion still have their original costs.
Model inference retains its original cost.
The improvement applies equally to every evaluated model.

This change was made after the revision 21 worker completed.
Its reported quality numbers therefore use the archived earlier evaluator.
No new real-model timing establishes this optimization's measured wall-time benefit.
It establishes no repair-specific speedup.

Evidence: `pilots/v22/evaluator-software-tests.txt` and `tests/test_prepared_finite_v22.py`.
