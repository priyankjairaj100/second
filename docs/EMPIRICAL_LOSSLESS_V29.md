# Lossless repair control, information bound, and scaling gate

Updated 8 October 2026, UTC.
This checkpoint adds a mandatory lossless control and strengthens the theory.
It preserves the numerical target and every earlier result.

## 1. Main result

Lossless repair beat matched cold reconstruction in one complete development comparison.
All calibrated model codes and complete retained state bytes matched their references.

| Registered method | Complete time | CPU charge | Neural stage-record traversals |
|---|---:|---:|---:|
| Indexed reconstruction | 44.067929996 s | 44 s | 0 |
| Repair | 49.062973723 s | 49 s | 0 |
| Cold reconstruction | 54.443484033 s | 55 s | 24 |

The primary cold/repair ratio is **1.109665393×**.
The cold/indexed ratio is 1.235444552×.
The indexed result cannot replace the registered repair result in a headline.

Repair and indexed reconstruction share the same numerical path and stored information.
Their single timings nevertheless differ by 11.33%, relative to indexed reconstruction.
This variation is comparable to the observed repair advantage.
Consequently, these observations do not establish reliable speedup or statistical equality between the indexed methods.

The registered seed was 29.
It fixed the order as indexed reconstruction, repair, then cold reconstruction.
One shuffled order is not repeated randomized evidence.
OS caches and unrelated machine activity remained uncontrolled.
No broader experiment was promoted from this result.

The request uses DistilGPT2 and the same WikiText development corpus as V28.
The original corpus has two sixteen-token records.
The request removes one record and retains the other.
No new quality, corpus, model, or independent deletion request was evaluated.

## 2. What the lossless control changes

The encoder stores each source-stage factor separately.
It chooses deterministically among raw bytes, zlib, and byte-shuffled zlib.
The decoder reconstructs every original binary64 feature bit, including signed zero.
Its bounded parser rejects invalid sizes, extra streams, noncanonical encodings, and changed bindings.

This is a standard lossless control, not a claimed new compression method.
FPC, ALP, and Zstandard remain useful stronger controls.
The lossless codec removes feature uncertainty before the common exact point solver.
It therefore needs no additional universal enclosure certificate.

The service validates retained membership and target provenance.
Repair and indexed reconstruction decode the retained descriptors.
They reuse the surviving canonical payloads after computing the exact retained model.
Neither method uses previous model codes as numerical proposals.
Fresh preparation independently produces the same complete retained state.

Strict input parsing still decodes and recompresses every supplied descriptor.
That includes descriptors belonging to deleted records.
The complete timing includes this parsing work.
The later service call decodes only retained descriptors.
These two scopes must remain distinct when interpreting its counters.

Both indexed methods decoded twenty-four retained descriptors and reused their payloads.
They encoded zero new descriptors during repair.
They performed zero neural traversals and avoided all twenty-four possible retained traversals.
The cold method executed all twenty-four retained traversals.

The fixed base checkpoint and calibration-independent nearest-grid anchor remain unchanged.
The target still differs from ordinary sequential GPTQ calibration.
The result removes calibration influence under this declared target.
It makes no claim about removing knowledge acquired during pretraining.

## 3. Complete storage comparison

The archive audit encoded complete original and retained states.
These are actual serialized sizes, not projections.

| Complete state | Original corpus | Retained corpus |
|---|---:|---:|
| Raw exact factors | 30,458,753 bytes | 26,326,066 bytes |
| Lossless factors | 29,462,403 bytes | 25,832,592 bytes |
| V28 forty-bit enclosures | 27,666,729 bytes | 24,930,099 bytes |

Lossless storage saves **1.874469205%** of the raw complete retained state.
The forty-bit state saves **3.493621546%** against the stronger lossless state.
Its previously reported 5.302603891% saving uses raw exact state as the denominator.
Both denominators must be visible in future comparisons.

The retained lossless state occupies 902,493 more bytes than the forty-bit state.
Their numerical model outputs are identical on this request.
The forty-bit service's earlier 51.231991286-second timing is historical development evidence.
It was not rerun within this new matched group.
We cannot infer a causal cross-version latency difference from those separate timings.

Every complete state includes calibrated model codes, source descriptors, tokens, indexes, and framing.
The common checkpoint remains required for uncalibrated parameters.
These percentages exclude that checkpoint and do not describe total deployment storage.
All compared states use the same packed model-code representation.

The probe also examined exact common-lattice packing.
No retained 256-value block fit within fifty-six common-lattice bits.
That probe did not establish a useful simple dyadic alternative.
Its raw zlib and shuffled zlib results remain preserved.
Probe figures describe factor payloads; they cannot replace complete state sizes.

## 4. Exactness and canonical state

All three complete models match across twenty-four stages and 42,467,328 calibrated codes.
The indexed and repair states match the independently encoded retained archive byte-for-byte.
All seventy-two archived factors reconstruct exactly across the original and retained states.
All twenty-four surviving descriptors remain byte-identical after deletion.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| Complete calibrated model | 22,192,646 | `d27c824322d0399f99a78c2b9d7e369e6b9a547085fa1cc25f92703536962927` |
| Original lossless state | 29,462,403 | `63ba700e8085fb33387ef0052d74d1442a4e7d1323b52a0e7632eb0d4799dad4` |
| Retained lossless state | 25,832,592 | `55a131c625861ad278eb13144bad319da02b07bb9e9017fa15d026199dec31e7` |

Separate-agent internal review found a full-deletion provenance bug before the pilot.
An empty retained set bypassed validation that normally occurred through surviving leaves.
The service now compares provenance with the current exact result before returning any indexed state.
Regression fixtures cover complete deletion with stale provenance.

The complete focused suite passed **35 tests**.
Its suite time was 0.983 seconds; measured child CPU was 1.689073 seconds.
The worker also passed fourteen input-contract fixtures before registration.
These software fixtures are not empirical datasets or language-quality evidence.
See `campaigns/lossless_software_check_v29.json`.

## 5. Complete costs and evidence integrity

The primary clock covers the controller transaction through its sealed receipt and receipt hash.
It starts after the declared controller input and bootstrap gates.
The worker repeats input validation inside the timed transaction.
The transaction includes checkpoint loading, compilation, parsing, decoding, solving, validation, and complete output.
Worker and service clocks are nested diagnostics; never add them to the primary clock.

Repair and indexed reconstruction write the model and complete retained state.
Cold reconstruction writes the model only.
We do not subtract the additional state-output cost from repair.
The comparison therefore exposes both output contracts explicitly.

The cold worker receives the registered token manifest and fixed checkpoint.
Only retained tokens enter its calibration procedure.
It reads no previous model, stored factors, or archive metadata.
Every method uses the same exact point solver and fresh-process native compilation.

Each worker now writes an immutable terminal record.
It prints that record's digest into the receipt-bound output log.
The controller compares the terminal, live, and sealed progress records.
It repeats that check before starting another trial.
Any discrepancy stops execution and preserves the original records.

All three V29 trials pass these checks.
Separate-agent internal review verified eighteen receipt artifacts and 366 bound files.
It also checked actual model and state bytes after completion.
The historical V23 and V27 discrepancies remain unchanged and disclosed.
Their causes remain unknown.

## 6. Preparation and budget accounting

The codec initially hashed the Python executable repeatedly during descriptor validation.
A bounded cache now keys runtime hashes by file identity and metadata.
Before-and-after checks detect file changes during a hash read.
This cache assumes the declared trusted runtime.
It does not authenticate hostile storage from metadata alone.

The first archive and its ten bound source files remain preserved.
The cache change produced a separately bound successor archive in `lossless_state_audit_v29b`.
It did not overwrite the original registration, source, state, or result.
The complete state sizes stayed unchanged; provenance hashes changed as required.

The first archive audit used 17.701466047 CPU seconds.
The successor audit used 13.0286 CPU seconds, rounded here.
Both scopes exclude final report serialization and writing.
Their exact costs appear in the corresponding summaries.
The earlier factor probe has its own cost receipt.
These are archive-analysis costs, separate from empirical worker accounting.
Neither archive audit performed neural inference, quantization, or service timing.

The current continuation registered a separate local phase with a 240 CPU-second cap.
The three registered trials charged 148 seconds, leaving 92 seconds.
No further trial is registered in this phase.
The older phase remains at 898 of 900 seconds charged or reserved.
That includes the unchanged 122-second reservation with unknown observed CPU usage.
The original ledger remains at 10,775 of 10,800 seconds.
Combined charged or reserved usage is **11,821 seconds**.
No old allowance was reset or pooled.
No paid compute was used.

These timings do not measure ordinary original lossless preparation.
Archive conversion cost cannot replace preparation-inclusive lifetime measurement.

## 7. Stronger model-response theorem

The earlier information argument distinguished exact metric queries from model queries.
The new construction directly separates quantized model responses.
It uses the canonical four-bit scale, finite inputs, and strictly positive rounding margins.

For every balanced sign assignment, the original metric and model are identical.
One singleton deletion makes a model code reveal the removed record's sign.
The original metric has condition number one.
Every retained metric has condition number at most three.
Thus the separation does not require an ill-conditioned metric or a midpoint tie.

For the stated ID-only interface without external record access, the archive must contain

\[
b\ge\left\lceil\log_2\binom{N}{N/2}\right\rceil
\]

bits under the specified fixed-length convention.
An explicit cumulative probe extension replaces \(b\) with \(b+k\).
Its \(k\) counts probes across all singleton counterfactual queries from the same original snapshot.
It is not a per-request probe bound.

The proof and finite binary64 domain appear in `docs/RESPONSE_LOWER_BOUND_V29.md`.
The note also states randomized joint-success and arbitrary-precision variants separately.
Margins shrink with corpus size.
The construction does not establish transformer realizability, privacy, state erasure, or practical speed.
Classical counting supplies the proof mechanism; no priority claim follows from this note.

## 8. Scaling barrier and next experimental gates

The current numerical backend forms dense matrices indexed by retained tokens.
One binary64 token matrix requires \(8T^2\) bytes.
At 262,144 retained tokens, that matrix alone requires **512 GiB**.
Sparse output-row verification does not remove this shared allocation.

The new admission helper rejects requests that violate a necessary memory bound.
It performs exact integer calculations without allocating numerical arrays.
A passing result means only that this lower bound does not rule out the request.
It guarantees neither memory fit nor completion nor speed.
The helper does not dispatch to an unimplemented primal certificate.

The scaling audit also identifies conditional \(O(dT^3)\) preconditioning.
Bounded coordinate-specific preconditioning is the next narrow algorithm improvement.
A verified feature-space route is required before realistic token expansion.
Both routes must preserve the same finite target and charge all conversion costs.
See `docs/SCALING_AUDIT_V29.md` and `campaigns/calibration_admission_plans_v29.json`.

The next empirical protocol must follow these gates:

1. Complete the scalable solver and compare exact outputs before testing large calibration sets.
2. Add stronger lossless controls with the same source-local and complete-output contracts.
3. Test fixed-anchor quality against sequential calibration, nearest rounding, and full precision using untouched documents.
4. Freeze acceptable quality margins, runtime estimators, and storage denominators before confirmation.
5. Use independent deletion requests and repeated, prospectively ordered complete transactions.
6. Add models and corpora only after each smaller feasibility screen passes.
7. Measure original preparation, changing retained state, fallback, output, and complete lifetime cost.
8. Register untouched confirmation after freezing the final target and method.

All twelve previously evaluated articles remain excluded from confirmation.
The existing quality evidence still contains only two articles and thirty predictions.
The old forty-cell program cannot be launched unchanged after the target redesign.
The updated literature audit further narrows claims about frozen representations and executable certificates.
See `docs/NOVELTY_AUDIT_V29.md` for primary sources and unresolved retrieval gaps.

The project now has a stronger control, a stronger information theorem, and an explicit scaling gate.
It still lacks the evidence needed for an ACL-ready empirical methods paper.

## 9. Restart and audit commands

Read `RESUME.md`, this report, and `campaigns/lossless_summary_v29.json` first.
Read `campaigns/lossless_internal_review_v29.json` for the separate-agent internal audit.

To rebuild the derived summary with local artifact verification:

```bash
python scripts/summarize_lossless_v29.py --verify-artifacts
```

Omit the flag when ignored binary artifacts are unavailable.
The report records whether it reverified those binaries.
The command does not run a model.
Do not rerun launchers into existing campaign directories.
Preserve the frozen source snapshots and register fresh paths for any future measurements.
