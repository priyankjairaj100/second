Second optimisation feasibility checkpoint, 22 October 2026

Status: UNREGISTERED SOFTWARE PROTOTYPE. No model or dataset experiment, no
cluster launch, no Linux numerical qualification and no new paper result.
The continuation scheduler remains paused at the user's request. The user
separately requested this investigation of speedup, transfer and paper framing.
V74 remains the manuscript/package checkpoint; all scientific results stand.

DECISION

Do not conclude that a broader speedup is impossible. Source inspection found
avoidable implementation costs and an isolated compatible decoder prototype
substantially improves one relevant operation. This justifies software
qualification and a bounded, separately registered performance comparison.
It does not establish a full-request advantage over an optimised lossless
control or support changing the manuscript's claim now.

FILES AND REPRODUCTION

decode.c and fast_decode.py: integer-only native payload decoder. The existing
V26 parser still checks the frame, hashes, dimensions and canonical header.
The C decoder checks every existing payload condition, including flag padding,
reserved flags, escape canonicality, finite exact endpoints and trailing bytes.
The wrapper admits only little-endian systems and bounded shapes/payloads.
No neural runtime guard is disabled. This is a new implementation, not merely
a source-compatible substitution under an old experiment's manifest.

check.py: run with the Second repository's existing Python and an optional
repository argument. For a checkout at the parent directory, the argument can
be omitted. It runs all eight legacy codec tests against both implementations,
then exact-byte differential tests and alternating six-sample local benchmarks.
It temporarily changes one function dispatch in its own single process only;
it does not write a repository source or construct a campaign artifact.

timings.py: optional repository argument; reads the preserved V67 metadata tar
without extraction and produces timing-attribution.json. Nested timers must
not be added to their parents. Streamed Gram time includes descriptor decoding,
block copying and accumulation as well as arithmetic.

sanitize.c: build with cc -std=c11 -O1 -g -fsanitize=address,undefined
-fno-omit-frame-pointer -Wall -Wextra -Werror sanitize.c -o sanitize; run the
result. This checks 100,000 seeded malformed inputs under both sanitizers.
This is not a proof of memory safety or qualification for a different compiler.

software-results.json retains samples, fixture seed, source hashes and platform.
software-results-initial.json retains the initial run. Its 'mutated' total also
included 1,600 boundary cases; the current schema separates these counts.
software-results-counter-fix.json preserves the intervening timing samples
from tool output; the current run followed the portable repository-path change.
All runs passed. These were reporting/portability changes, not decoder fixes.
The first timing-attribution script attempt assumed a predecessor-validation
timer for the cold arm, which has no predecessor; the reader now handles that
arm explicitly. No experiment artifact was changed by either reporting fix.

OBSERVED SOFTWARE EVIDENCE

On macOS 13 arm64, the generated 48-bit/block256 parse(blob).box() fixtures at
128x768 and 128x3072 were about 20 times faster with native payload decoding.
This operation still includes two decodes, parsing, validation and immutable
box construction. Compilation/loading were outside the timing samples.
The current JSON contains the actual medians and all raw samples. No cluster,
model, end-to-end, cold-start, confidence-interval or cross-model speedup follows.

Both implementations pass all eight legacy tests (all exponent classes,
subnormals, signed zeros, guard escapes, exact containment, radius construction,
canonical frames and malformed input). Differential checks cover 40 valid
matrix/radius configurations, 6,810 mutated/truncated cases and 1,600 targeted
boundary configurations, comparing exact output bytes or matching rejection.
Of the mutation cases 2,710 remain valid encodings and 4,100 are rejected by both.
The separate sanitizer harness completes 100,000 cases. Tests are sampled
evidence; a source-level review and Linux qualification are still required.

FINDINGS IN THE EXISTING SERVICE

1. Four decodes for every retained compressed descriptor on a no-replay request.
   research_v61/state.py:_validate_descriptor validates the predecessor once.
   research_v61/service.py:solve uses parse(blob).box(), decoding twice because
   FactorDescriptor.__post_init__ also decodes. Successor build_state validates
   each descriptor once more. src/fixed_factor_codec_v26.py:140 implements this
   as an element-by-element Python loop. These are real costs, not evidence of
   a correctness failure. First optimise the decoder while retaining validation.
   A later stage-scoped validated-object interface can remove redundant passes;
   it must preserve immutable bytes, identities, canonical checks and budgets.

2. The control can improve too. research_v63/codec.py:187 re-encodes all five
   lossless modes during each descriptor construction to verify canonicality.
   ModernService parses again in solving and serialising. Validated immutable
   descriptors can avoid repeated work within a request, after full admission.
   Never delete canonical validation from untrusted input parsing or optimise
   only our arm. The local environment lacks zstandard, so no new local timing
   claim is made for that control; the actual V67 timing receipts are available.

3. Important shared work remains. At endpoint 1, compressed 3072-wide stages
   spend about 3030 s computing coefficients, versus 2917 s in modern lossless.
   This is over half the compressed request. At endpoint 2, token coefficient
   native work is 651 s for boxes versus 514 s for points, plus roughly 55 s of
   feature-bound work for boxes. These are descriptive single observations.
   Improving a shared kernel is valuable but may improve the control as much.

4. V50's verified fast normal-neighbour primitive is installed in the primal
   library only. Native token-point and token-box coefficient libraries still
   use their own nextafter calls. Extending the same exact semantics to BOTH
   libraries is a plausible next optimisation. It requires native bit/exception
   parity on boundaries, zeros, subnormals, infinities and NaNs, strict compiler
   flags, new provenance and complete numerical checks. It has not been done or
   timed here. The existing primal optimisation is already in V67.

5. Routing is not a one-line fix for the larger endpoint. The policy prefers
   token space when 4*tokens<=width, but actual V67 admission at 1536 tokens and
   width3072 rejects token space for BOTH arms. It reserves 137,782,898,688 work
   units for boxes and 195,691,831,296 for points, above the 64,000,000,000 cap.
   Changing the preference does not make that route admissible. At 768 tokens
   the token route is already selected. No budget or fallback rule was changed.

6. Fallbacks are not the main explanation. Compressed internal row fallback
   costs about 22.60 s at endpoint 1 and 0.044 s at endpoint 2, against gaps of
   627.07 s and 453.26 s versus modern lossless. No neural replay occurred.
   Predecessor validation plus serialization differences explain 197.42 s
   (31.48%) and 144.10 s (31.79%) of those gaps; decoding inside solve is extra.
   Even making just those two entire compressed phases free leaves requests
   around 4942/1158 s versus the observed modern 4579/898 s. Optimising only
   those phases cannot reverse these comparisons with all other times fixed.

7. Precision/GPU shortcuts already have important limits. V51's 40-bit arm
   refused certification; V52's 48-bit experiment was an adaptive response.
   Preserve that failure. It is not proof that every 40-bit method must fail.
   V56's GPU result is likelihood parity, not exact feature/calibration parity.
   GPU feature substitution would change the declared target without separate
   equivalence evidence. Neither is a drop-in speed improvement.

ORDERED NEXT WORK (PROPOSAL, NOT LAUNCH AUTHORITY OR REGISTRATION)

A. Qualify the new decoder on the pinned Linux runtime. Review exact integer
   shifts, bounds, admission limits and public parser compatibility; include
   compiler/binary/source hashes and adversarial tests in a NEW source manifest.
   Preserve all original registered code and caps. Same bytes alone do not
   establish that a new implementation was admitted by an old manifest.
B. Implement bounded validated-object reuse symmetrically, and the token
   neighbour primitive in both controls. Measure components first. Keep the
   existing route policy unless a separately justified admitted choice is tested.
C. Freeze a small comparison with old/new code and compressed/modern arms on
   development inputs. Include full request I/O, validation, solver, fallback,
   serialization, disposal, startup attribution, live bytes and peak memory.
   Use at least five balanced-order repetitions per declared condition if
   prospective existing-cap admission permits; otherwise downscope explicitly.
   Verify all codes and actual canonical successor states against a fresh
   reference under the new implementation manifest. Do not reuse one-use jobs.
   Never use untouched quality outcomes to select an optimisation. Any failure
   is retained. Before launch, reconcile Slurm and receipts after restoring
   access; no new SSH attempt was made in this investigation.
D. Decide on transfer after the implementation comparison. An ordinary GPT-2
   checkpoint is the lowest implementation-risk extension: the existing importer
   supports GPT-2 geometry, while service/archive limits currently fix 24 stages
   and 13 records. GPT-2's published config has 12 blocks, so even that extension
   needs a new target and resource admission. It tests checkpoint/depth transfer
   within a family, not architecture-general transfer. A second architecture
   requires a finite feature provider, adapter, proofs of the same interface
   assumptions, quality controls and a separate registration. No target is
   chosen after seeing favourable results and no checkpoint was downloaded here.

SCIENTIFIC DECISION AND WRITING CONSEQUENCES

The correctness argument is conditional on a fixed, source-local feature map,
valid enclosures, the declared quantizer and successful certificates. It is
not intrinsically a claim that every language model will certify cheaply.
Empirical transfer asks a different question: do useful storage, certification,
latency and quality tradeoffs survive a different checkpoint or architecture?
No such measurement is currently available. There is no conclusive evidence
against transfer, and the current timings are not a lower bound on optimised
runtime. Reject the specific weak explanations above, not all future speedups.

A universal speedup is not required for the mathematical contribution and is
not a sensible finite-experiment goal. A repeatable advantage within a clearly
specified operating range would be useful. Broader checkpoint evidence is more
important than claiming universal acceleration for the practical NLP story.
The present evidence (one small model; roughly 9% live-state savings and only
3-5% savings including checkpoint bytes; slower requests than modern lossless)
leaves practical magnitude and breadth modest. A proof plus one narrow instance
can support a careful methods paper, but it is a weaker practical systems/NLP
story. This is an assessment, not an acceptance prediction or impossibility proof.

If a fair new comparison succeeds, frame the benefit by the measured regime
and baselines. If it improves our old implementation but not the modern control,
report an engineering improvement without claiming a method-level speed win.
If no useful win survives, retain the current bounded storage/source-access/
latency framing, lead with the exact repair contract, and present latency as
its measured cost. A transfer result would strengthen scope even without a
latency win. Do not put the 20x software-fixture number in the abstract.

Primary references checked for context, not used as empirical evidence for us:
https://arxiv.org/abs/2210.17323v2 (GPTQ)
https://arxiv.org/abs/2610.02268v1 (ExecCert)
https://arxiv.org/abs/2610.07197v1 (QSS)
https://huggingface.co/openai-community/gpt2/blob/main/config.json (unfrozen
candidate configuration; a future experiment must pin an immutable revision).
Existing certificate and quantized-statistics work makes the specific adaptive
code-repair contract and actual operating benefits the contribution to explain;
merely saying 'certified unlearning' is insufficient differentiation.
