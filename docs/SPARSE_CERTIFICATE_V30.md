# Budgeted requested-coordinate certification, V30

Status: implemented and verified with exact software fixtures.
No empirical model run or speed claim follows from these fixtures.
The target remains the existing fixed-feature dyadic target.
This implementation does not solve the original sequential-feature problem.

## Implemented interface

`src/sparse_box_certificate_v30.py` exports `certify_sparse_ball_dyadic_box`.
The alias `certify_ball_dyadic_box` supports an explicit service backend map.
Historical V28 sources remain unchanged.

```python
from src.sparse_box_certificate_v30 import (
    SparseCertificateBudget, certify_sparse_ball_dyadic_box,
)

result = certify_sparse_ball_dyadic_box(
    weights, lower, upper, scale_values,
    bits=4, significant_bits=24, ridge=ridge, normalization=normalization,
    budget=SparseCertificateBudget(
        max_work_units=250_000_000,
        max_workspace_bytes=512 * 2**20,
        max_preconditioned_coordinates=16,
        max_rounds=4,
    ),
)
```

The budget values shown are the defaults.
They are engineering limits, not scientifically selected workload sizes.
Every field must be a nonnegative built-in integer.
The function returns immutable codes only after every row passes.
A rejection raises `TokenBoxUnresolved` and attaches `native_diagnostics`.

The function accepts V28's exact-fallback limits for call compatibility.
It validates these limits but starts no exact fallback.
`allow_python_fallback` must remain false.
Setting it true raises `ValueError`.
Singleton inputs use the same bounded certificate path.
A service can retain its existing separate point route for singleton inputs.
Inputs must remain unchanged during the call.

## Algorithm

1. Check shapes and declared resource allowances before numerical array scans.
2. Reserve work for initial bounds, ridge coefficients, and the ball pass.
3. Run V28's unchanged initial ball pass.
4. Retry only failed complete rows with shared ridge component radii.
5. Collect each remaining row's actual failure coordinate.
6. Form their coordinate union and exclude coordinates already checked.
7. Reserve the reverse sweep, requested defect checks, and complete-row retry.
8. Verify stronger evidence only at the requested coordinates.
9. Intersect these radii with existing radii around their unchanged proposals.
10. Retry remaining complete rows with the mixed coefficient table.
11. Continue within coordinate and round limits, or refuse.

The native interval kernel always sees full-width rows.
The algorithm discards partial rows after failure.
Previously certified complete rows never enter a later retry.
No eager all-coordinate preconditioner or Python universal fallback is reachable.
The function starts no point solver for uncertain boxes.

## Why mixed evidence is valid

Let the original proposal for coordinate \(i\) be \(p_i\).
The initial ridge certificate proves

\[
\|c_i-p_i\|_2\le\rho_i.
\]

Thus every component also satisfies \(|c_{ik}-p_{ik}|\le\rho_i\).
A requested check proves a second component radius \(e_{ik}\).
It uses the residual of the **original** proposal \(p_i\).
It does not substitute a newly reconstructed proposal.
Therefore

\[
|c_{ik}-p_{ik}|\le\min\{\rho_i,e_{ik}\}.
\]

The mixed table keeps \(p_i\) unchanged at every coordinate.
Unrequested coordinates retain their existing ridge radii.
Requested certificates retain immutable copies of their checked proposals and radii.
The implementation checks proposal equality before installing each radius.
It accepts no external cached certificate.

Each reverse sweep constructs interval suffix Gram matrices.
It also reconstructs nominal inverse updates.
These updates are untrusted proposals for the preconditioning matrix.
Directed residual and defect checks provide the numerical proof.
The reused `_preconditioned_error` routine requires a verified contraction and supersolution.
An invalid preconditioner supplies no new evidence.
The existing ridge evidence remains available.

The complete-row verifier preserves the exact coordinate order and lower-code tie rule.
An accepted code equals the exact oracle throughout the supplied feature box.
The caller still must establish containment of the true features.
Hashes and parser checks do not establish that premise.

A repeated failure at an already checked coordinate causes rejection.
The same stored evidence cannot become stronger through another identical check.
This rule prevents unbounded retries.
It can reject boxes that another algorithm could certify.

## Bounded structural work

Let \(d\) denote input width and \(T\) denote retained tokens.
Let \(m\) denote output rows and \(b\) denote quantization bits.
Let \(g=2^b\) denote grid size.
For round \(j\), let \(K_j\) denote newly requested coordinates.
Let \(s_j=d-\min K_j\) denote visited suffix coordinates.
Let \(r_j\) denote rows retried in that round.

The stronger construction has structural cost

\[
O\!\left(\sum_j s_jT^2+\sum_j |K_j|T^3\right).
\]

V28's eager stronger path checks every coordinate at cost \(O(dT^3)\).
The new path checks only observed failure coordinates.
Repeated sweeps remain charged.
The normal ridge path still costs \(O(dT^2)\).
This change alone does not solve large-token scaling.

The scheduler reserves these exact integer proxies.

| Operation | Reserved work units |
|---|---:|
| Initial bounds, coefficients, and ball rows | \(dT^2+md(2T+b+1)+dT+mg\) |
| Shared ridge row retry | \(rd(2T+b+1)\) |
| Requested preconditioner round | \(s_jT^2+|K_j|T^3\) |
| Mixed row retry | \(r_jd(2T+b+1)\) |

These units are structural proxies, not FLOPs or CPU seconds.
Fixed arithmetic constants differ across operations.
Reservations can exceed actual work after an early refusal.
They never measure completed work or elapsed time.
The code reserves the complete retry before starting its stronger coefficient sweep.
The caller must enforce process timeouts separately.

`max_preconditioned_coordinates` bounds the number of distinct checks, including rejected checks.
`max_rounds` bounds the number of adaptive sweeps.
A coordinate is never checked twice.
The certificate cache requires \(O(KT)\) values.
It stores no per-coordinate inverse matrices.

## Workspace admission

The function computes this allowance before any size-dependent numerical scan:

\[
8\left[64T^2+24dT+32md+8mg+8KT+64(m+d+T+1)\right]\text{ bytes},
\]

where \(K=\min\{d,\text{max\_preconditioned\_coordinates}\}\).
The allowance charges inputs, alignment copies, intermediate arrays, and output arrays.
It deliberately uses generous coefficients.
It excludes compiler overhead, allocator behavior, interpreter state, and other process objects.
It is an **engineering array allowance**, not a proved process memory bound.
A successful check does not guarantee memory fit.
The caller must retain an external process memory limit.

A rejected allowance causes no coefficient construction or native compilation.
A work refusal also occurs before its associated operation starts.
Malformed candidate dimensions fail before candidate-value scans.

## Diagnostics

Successful results include these fields.

- `preconditioner_requested_coordinates`: all distinct attempted coordinates.
- `preconditioner_verified_coordinates`: coordinates with proved stronger evidence.
- `preconditioner_rounds`: completed or entered adaptive rounds.
- `coefficient_suffix_coordinates_visited`: actual reconstructed suffix coordinates.
- `unresolved_coordinate_rounds`: original row identities and actual failure coordinates.
- `work_units_reserved`: total accepted reservations.
- `resource_reservations`: each operation and its reserved units.
- `workspace_array_allowance_bytes`: admitted engineering allowance.
- `native_passes`: native timing, attempted decisions, and row failure records.

Rejections attach corresponding diagnostics and a `resource_refusal` reason when applicable.
Whole-call timing includes validation, compilation, coefficient construction, native passes, and result construction.
Nested diagnostic clocks must not be added to whole-call timing.

## Verification and limits

Run the focused software fixtures with this command.

```bash
python -m unittest tests.test_sparse_box_certificate_v30 -v
```

Fifteen fixtures cover exact corners, interior points, lower-code ties, and empty-token inputs.
They also cover proposal pairing, adaptive rounds, shared coordinate unions, and discarded partial rows.
Resource tests prove refusal before expensive construction.
Input tests cover alignment, immutability, candidates, and unsupported fallback options.

The hard two-coordinate fixture now checks only coordinate one.
It visits one suffix and matches every exact corner.
Another fixture uses two adaptive rounds without repeating earlier coefficient checks.
A two-row fixture shares one sweep across distinct failure coordinates.
These are numerical software fixtures, not synthetic empirical datasets.

No measured full-model speed improvement follows.
No broader quality claim follows.
A primal backend and registered real-data scaling tests remain necessary.
Compatible reconstruction baselines must receive this backend when applicable.
