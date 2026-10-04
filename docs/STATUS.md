# Current project status

Updated 4 October 2026, revision 4.

The latest request asks for a comprehensive list of remaining research tasks.
See [RESEARCH_TODO.md](RESEARCH_TODO.md) for priorities, completion criteria, and decision gates.
This planning update changes no implementation or empirical result.
Research experiments remain paused.
Software correctness checks remain within scope.

## Completed implementation

The reference implementation now connects the theory to a concrete certified decoder.

| Previous blocker | Implemented result | Remaining limit |
| --- | --- | --- |
| Complete service stored individual matrices | Compact group response and remainder sums | O(NL) metadata still remains |
| Changed-prefix bounds required trusted user values | Automatic interval jets, mixed Hessians, and finite-error bounds | Fixed affine chart can reject realistic changes |
| Nonlinear library calls lacked proved rounding bounds | Rational enclosures and certified binary64 rounding | Slow scalar program; unresolved operations abort |
| Local checkpoint interface was absent | Strict GPT-2 safetensors adapter | No pretrained checkpoint evaluation yet |

The aggregate service verifies deleted-record contributions before exact subtraction.
It certifies proposals against the new ancestor prefix.
Unknown bounds trigger selected retained replay.
The final state matches fresh retained construction.
Repeated deletion preserves canonical state bytes.

The certified provider uses a corpus-independent affine chart.
It computes value, derivative, mixed-curvature, and numerical-error bounds automatically.
It checks chart membership against installed finite weights.
Its stable softmax proof separates ideal derivatives from finite branch effects.
No caller-supplied tolerance substitutes for the numerical proof.

The local adapter supports single and sharded safetensors.
It handles four floating storage types and both supported GELU variants.
It records source hashes and rejects unsupported architectures.

## Numerical scope

V_cert defines a new finite feature program with certified nonlinear primitives.
It remains distinct from legacy library-math V and floating quantizer E.
Imported checkpoint weights do not establish native Hugging Face output equality.
Proof abstention causes replay.
Finite-evaluator failure aborts the transaction without returning a model.

## Evidence and remaining work

Correctness tests and independent review cover the new modules.
See docs/VALIDATION.md for final results and exact source hashes.
These checks do not measure model quality, certificate coverage, or latency.

Useful chart coverage remains unknown on real language models.
The experiment runner and equally indexed fresh baseline remain unimplemented.
The current empirical protocol must be reconstructed because the earlier protocol is unavailable.
Interval bounds may become too loose across long sequences and deep networks.
Large charts increase preparation, storage, and verification costs.
The checkpoint adapter loads parameters eagerly into Python objects.
Large-model memory use remains untested.
Fast GPU kernels and scheduler integration remain future engineering work.

An equally indexed fresh solver can use the same response summaries.
No universal strict advantage over that solver follows.
Full service measurements must charge setup, deleted extraction, metadata, replay, verification, output, and state maintenance.
Research experiments will resume only when the user authorizes that phase.

## Claim discipline

The main contribution remains exact sequential calibration deletion with certified changed ancestors and canonical retained state.
The lower-storage interval construction supplies O(r d²+r²) response entries per group.
The stated zero-replay and speed conditions remain conditional mathematical results.
They are not practical speedup evidence.

The matrix shape constant follows classical geometry.
Taylor verification, polynomial statistics, and derivative-based deletion sketches have primary precedents.
The repository makes no exhaustive priority claim.
It also makes no hostile-storage authentication, physical memory erasure, or proof-assistant claim.

Earlier raw experiment files remain missing.
Historical metrics are reconstructed context, not recovered evidence.

The report's unconditional fallback wording needs one documented correction.
Every such statement must require successful finite evaluation for the partial V_cert program.
The current implementation and numerical contract already enforce this distinction.
