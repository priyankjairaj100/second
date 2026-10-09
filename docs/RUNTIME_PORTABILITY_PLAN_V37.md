# Prospective runtime portability plan

Date: 9 October 2026.

The current C4 neural execution blocker remains unresolved.
This document records a read-only engineering assessment, not a completed implementation or experiment.
No native probe, compilation, neural evaluation, or runtime substitution supported this assessment.

## Finding

A new live runtime collector is technically plausible without `/proc/self/maps` and `/proc/cpuinfo`.
It cannot transparently replace the registered collector or resume the failed C4 transaction.
The replacement needs its own version, review, evidence, registration, and fresh preparation.

No fake proc files, copied historical CPU fields, fabricated library identities, or silent monkeypatching are permitted.
Unavailable live evidence must cause an explicit failure.
The historical registration, failure, sources, and ledger remain unchanged.

## Actual consumers and required facts

| Source | Required facts and use |
|---|---|
| `src/transformer_backend.py`, `_check_runtime` | CPython IEEE binary64; supported Linux architecture; live `fegetround()` equals nearest; gradual underflow rather than FTZ/DAZ. These checks remain necessary. |
| `src/transformer_backend.py`, `_runtime_manifest` | Reads `/proc/self/maps` to identify loaded `libm` and `libpython` paths, then hashes their files. Reads the first `/proc/cpuinfo` record for stable CPU identity and dispatch fields. Also binds Python executable, math extension, libc version, architecture, byte order, and binary64 properties. |
| `src/finite_primitives.py`, `_primitive_manifest_bytes` | The MPFR backend independently reads `/proc/self/maps` for loaded GMP, MPFR, and MPC libraries. It hashes these and loaded `gmpy2` extension files. It records library versions and the explicit MPFR context. Replacing only the transformer manifest leaves this blocker intact. |
| `src/checkpoint_adapter.py`, `load_gpt2_checkpoint` | Constructs `DeterministicDecoder` through a hardcoded imported constructor. Its constructor builds the proc-dependent manifest. A new loader path is needed; changing a global constructor silently is unacceptable. |
| `src/certified_transformer.py`, `CertifiedDecoder.__init__` | Embeds the base decoder manifest and primitive manifest in the certified evaluator identity. |
| `src/ordered_finite_decoder_v30.py`, `OrderedFiniteDecoder` | Preserves the certified mathematical target and separately records its implementation identity. It inherits the proc-dependent construction path. |
| `src/target_manifest.py` and `src/dyadic_row_target.py` | Target payloads inherit the evaluator identity. Changing runtime identity therefore changes downstream target digests. |
| `scripts/run_ordered_service_v30.py` | Constructs both neural manifests. Repair requires preparation and current target digests, implementation manifests, and preparer identities to agree. Historical states cannot silently become compatible with a different target identity. |
| `src/runtime_contract.py` | Records portable software, interpreter, architecture, and module identities. Its documentation explicitly excludes physical CPU identity and native dynamic dependencies. Passing this contract does not replace the neural manifests. |
| `scripts/preflight_environment_v34.py` | Checks actual neural and primitive manifest construction before expensive work. Its current failure remains authoritative for the unchanged backend. |
| `scripts/launch_independent_requests_v32.py` and continuations | Pin software runtime, numerical sources, trial identity, and resource limits. A new collector cannot be inserted into an old registration. |

The current service controller uses `src.worker_control.py` and `run_limited` for worker accounting.
The broader repository also contains proc-dependent observer code in `src/transaction_timing.py`.
Any future controller must audit its actual dependency path separately.
This assessment does not establish that every execution prerequisite is available.

## What live alternatives could establish

`dl_iterate_phdr` enumerates loaded ELF shared objects and their program headers.
A versioned collector could use it to identify loaded library paths without proc maps.
It should also verify relevant resolved symbol owners using a reviewed loader API.
It must hash the actual readable library files, including GMP and MPFR dependencies.
Missing, deleted, unreadable, ambiguous, or unsupported loader entries must cause refusal.

This is a live library-identity mechanism, not a claim that file hashes attest every mapped memory byte.
The existing implementation also assumes stable trusted library files when hashing loaded paths.
The new collector must state that assumption and preserve or strengthen its guarantees.
It should record provenance separately from ASLR-dependent addresses.

Real CPUID can report x86 vendor, family, model, stepping, brand, and hardware feature registers.
It does not reproduce the old `/proc/cpuinfo` flags field.
Kernel documentation explains that those flags include software-created features and kernel-enabled capabilities.
Some CPUID-advertised features require additional operating-system enablement.

A reviewed x86 dispatch binding should therefore consider all of:

- Raw, bounded CPUID leaves and subleaves relevant to the supported libraries.
- XGETBV/XCR0, invoked only when its architectural prerequisites hold.
- Live auxiliary-vector capabilities, including applicable HWCAP and HWCAP2 entries.
- Relevant glibc CPU tunables and actual resolved implementation identities.
- Collection on the same allowed CPU affinity used by the worker.
- Repeated collection or explicit invariants concerning migration and dynamic library loading.

CPUID faulting, unavailable APIs, unsupported architectures, or insufficient evidence must fail closed.
An x86 implementation must not pretend to attest AArch64 hardware.
Historical CPU facts cannot fill missing live observations.

## Target and preparation consequences

The correctly rounded mathematical neural operations may remain unchanged under a reviewed collector redesign.
That possibility does not establish identity equality, equal completion behavior, or historical state compatibility.

The existing evaluator hashes its runtime manifests.
Target digests and prepared states consequently bind those identities.
A new manifest schema must produce an explicitly new evaluator and target identity.
Both sides of a new empirical comparison need the same fresh registered preparation and runtime.
Historical latency cannot become a within-registration comparator merely because checkpoint weights match.

Do not edit pinned historical source snapshots or rewrite old receipts.
An isolated, explicitly named backend and loader should retain the original implementations for reproducibility.
Existing numerical helper reuse must remain explicit and source-bound.

## Minimum implementation and validation gates

1. **Specify the contract.** Enumerate every required runtime fact, collection source, supported architecture, and refusal case.
2. **Implement a separate collector.** Bind its source, compiled helper, compiler, and flags. Preserve current rounding and underflow checks.
3. **Review live library discovery.** Check expected library completeness, duplicate identities, symbol ownership, and readable stable files.
4. **Review CPU dispatch evidence.** Use CPUID together with required OS state and tunables. Do not manufacture a proc-compatible flags string.
5. **Create explicit construction paths.** Add a versioned loader and decoder initialization path without global replacement of registered constructors.
6. **Test refusal behavior.** Cover missing APIs, unavailable libraries, changed hashes, unsupported CPUs, affinity changes, and incomplete observations.
7. **Cross-check on a compatible Linux host.** Collect old and new observations in the same process or controlled child. Explain every difference in represented facts.
8. **Check numerical equivalence separately.** Use finite arithmetic fixtures and prescribed real-data comparisons. Correctness tests do not establish equal runtime identity or latency.
9. **Register fresh experiments.** Freeze source inventories, identities, resource limits, samples, methods, and comparisons before execution.
10. **Prepare fresh state.** Run both new comparators under the new registration. Preserve all failures and charge complete preparation and request costs.

These gates have not been completed.
No claim that the C4 environment is repaired follows from this plan.
Running the existing registered program on a genuinely compatible local environment remains the simpler continuation path.

## Primary documentation consulted

- Linux kernel, x86 feature flags: https://docs.kernel.org/arch/x86/cpuinfo.html
- Linux kernel, userspace XSTATE: https://docs.kernel.org/arch/x86/xstate.html
- GNU C Library, auxiliary vector and `getauxval`: https://www.sourceware.org/glibc/manual/latest/html_node/Auxiliary-Vector.html
- GNU C Library, hardware capability tunables: https://sourceware.org/glibc/manual/latest/html_node/Hardware-Capability-Tunables.html
- Linux man-pages, `dl_iterate_phdr`: https://www.man7.org/linux/man-pages/man3/dl_iterate_phdr.3.html

These sources establish API behavior and limitations.
They do not establish that the required APIs work in this execution environment.
