# Live runtime collector

The V38 collector creates a new runtime identity without procfs.
It does not restore compatibility with historical states.
It does not alter any registered numerical source.

## API

`collect_runtime("transformer")` returns a fresh JSON-compatible dictionary.
`collect_runtime("mpfr")` returns the primitive runtime dictionary.
`assert_runtime_unchanged(manifest)` collects live evidence again.
It raises `RuntimeEvidenceError` when evidence differs.

Both domains require Linux x86-64 and one allowed CPU.
The caller must preserve affinity during evaluation.
The caller must also preserve loader state, dispatch settings, and floating-point controls.
The collector checks these conditions at transaction boundaries.
It cannot detect every change between those boundaries.

## Hardware and operating system evidence

The native helper checks CPUID permission through `ARCH_GET_CPUID`.
A bounded child checks CPUID and XGETBV before the Python process uses them.
The collector records raw CPUID registers within explicit bounds.
These include feature, topology, cache, XSTATE, extended, and advertised hypervisor records.
XGETBV runs only when CPUID reports XSAVE and OSXSAVE.
The collector records the actual XCR0 value.

`getauxval` supplies HWCAP, HWCAP2, platform, page size, and secure-mode facts.
These observations do not reproduce Linux CPU flags.
Missing entries cause refusal.
Secure loader mode also causes refusal.

The collector compares allowed affinity with `sched_getcpu`.
It repeats CPU collection before returning.
The helper checks rounding controls and gradual underflow.
It excludes sticky exception flags from the identity.
Ordinary inexact arithmetic can change those flags.

The identity includes observed loader and numerical dispatch variables.
It also includes NumPy's live feature selection.
The caller must not change dispatch variables after library initialization.
The collector assumes this trusted process rule.

## Loaded binary evidence

`dl_iterate_phdr` supplies actual loaded ELF objects.
The collector resolves paths and rejects ambiguous mappings.
It reads bounded ELF dependency records from actual files.
It recursively binds each required dependency to one loaded owner.
The dependency check uses filenames and SONAME values.

The transformer domain includes libm, Python, math, NumPy, libc, and the loader.
It also includes their full ELF dependency closure.
This closure includes loaded BLAS dependencies.
The primitive domain includes GMP, MPFR, MPC, gmpy2, libc, and the loader.
It also includes their full dependency closure.

Static Python and built-in math use their actual executable owner.
The collector never invents a separate libpython object.
`RTLD_NOLOAD` opens existing library handles without substituting new libraries.
The main executable uses the existing process handle.

`dladdr` checks required symbol owners against the live inventory.
The identity records resolved addresses relative to each binary base.
These values bind resolved implementations without retaining ASLR addresses.
Global libm, libc, and Python symbols must agree with their library handles.
Loader preload and audit modules cause refusal.

Each file receives a SHA-256 digest.
File identity, size, and timestamps must remain stable during hashing.
Helper source, compiler, compiler version, flags, probe, and shared binary are bound.
Returned dictionaries cannot alter the internal helper cache.

Library files must remain trusted and stable.
File hashing does not attest every mapped memory byte.
The collector does not protect against malicious code within the Python process.

## Validation scope

Focused fixtures cover genuine collection and explicit refusal paths.
They also check stable identity after loading the primitive domain.
These fixtures contain no empirical model experiment.

A compatible Linux host must compare old and new observations.
That external cross-check remains a separate gate.
Numerical equivalence and fresh experiment registration also remain separate gates.
Passing runtime fixtures does not complete the C4 campaign.
