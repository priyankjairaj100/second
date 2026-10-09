# Runtime cross-check

The cross-check compares genuine old and new observations in one process.
It requires readable procfs and the original numerical dependencies.
It uses no model or empirical dataset.

Run this command before model workers:

```bash
.venv/bin/python scripts/check_runtime_portability_v38.py --output campaigns/ci_v38/runtime-portability.json
```

The command selects the lowest allowed CPU by default.
Use `--cpu` to select another allowed CPU.
The command restores its original affinity before exit.
An existing output file causes refusal.

The script loads NumPy and gmpy2 before either manifest.
It records raw manifests and bounded proc evidence.
It compares loaded libm, Python, math, GMP, MPFR, MPC, and gmpy2 identities.
It also checks every new required file against genuine proc maps.

The old collector reads the first CPU record.
The script separately finds the selected CPU record.
It requires common identity fields and flags to agree.
It derives vendor, family, model, stepping, and brand from live CPUID registers.
Those values must agree with the selected CPU record.
Logical CPU numbers remain separate from APIC numbers.

The script checks a declared subset of architectural flags.
Reported AVX features also require the relevant XCR0 state.
Unmapped proc flags remain visible in the output.
The script does not claim complete equivalence between flags and CPUID.

| Outcome | Original backend | Portable gate 7 |
|---|---|---|
| `passed` | Admitted | Passed for this host |
| `unsupported_portable_interface` | Admitted after fresh old observations agree | Open |
| `contradictory_runtime_facts` | Blocked | Open |
| `unexpected_error` | Blocked | Open |

Only a narrow list of unavailable interfaces permits the second outcome.
The original collector must already pass in that case.
The script clears its old manifest caches and collects fresh observations again.
Old libraries, CPU mappings, sources, and affinity must remain unchanged.
Hash changes, unexpected symbol owners, and unknown errors block the original backend.

The JSON records wall time, process CPU time, and child CPU time.
It also records source hashes and the precise refusal reason.
No successful cross-check makes historical states compatible with the new schema.
Fresh registration and numerical validation remain separate requirements.
