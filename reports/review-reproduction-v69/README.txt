External-input and reproduction guide: development preparation

This companion explains the current source, summary and receipt components. It
does not make the package submission-ready or reproduce the numerical results.
No input, library, model or container was acquired while making this guide.

1. Verify the three components offline

Place the three ZIP files named in INPUTS.json in one directory. Extract this
guide into a separate fresh directory and use an existing Python3.10+ interpreter:

  python3 -I -B verify_inputs.py --components /absolute/path/to/components

The command streams the existing ZIP bytes and checks their exact sizes and
SHA256 values, plus this guide's own manifest. It does not extract or execute the
source, contact the network or write files. The ZIP hash published separately
must also be checked; an editable manifest is not an authenticity signature.
No --components argument checks only this guide. Extra files in the guide directory
are refused. Run from the directory containing verify_inputs.py.

2. Reproduce the qualified local fixture subset

Extract development-source-review-v69c.zip into a fresh destination. Its top-level
directory is source-review. Choose an existing CPython3.12 environment with NumPy
2.3.5. The observed fixture runtime was CPython3.12.7/macOS; it is not the empirical
Linux runtime. No install command or floating requirements file substitutes for
the admitted numerical environment. From source-review, using that interpreter:

  mkdir /absolute/path/to/fresh-fixture-output
  mkdir /absolute/path/to/fresh-fixture-output/tmp
  /absolute/path/to/python3.12 -I -B qualify_review_source.py . \
    --temporary /absolute/path/to/fresh-fixture-output/tmp \
    --report /absolute/path/to/fresh-fixture-output/report.json \
    --log /absolute/path/to/fresh-fixture-output/tests.txt

Use new output paths for each software check; the checker refuses overwrite. It
checks536 manifest entries and runs22 V68 plus92 V69 fixtures:114 tests with zero
errors/failures/skips are required. It records loaded project module origins and
checks unchanged source bytes. The original validation used156 project modules
and three namespace packages, all from the extraction. Production checkpoint
import, calibration, runtime/limit admission and Slurm are mocked; tiny generated
CPU likelihood and statistical fixtures run. No empirical likelihood is computed.

The checker imposes120/121 CPU seconds and64MiB per file, restricts writes to the
chosen output/temp paths, and uses Python audit hooks to deny network calls and
subprocesses except bash -n syntax checks. Audit hooks are not a full OS sandbox.
An intentional immutable-input exception in stderr is part of a passing refusal
fixture; assess the final report and unittest results. Do not run blanket test
discovery: older tests require historical data/receipts absent from this component.

3. Identify external model and data inputs without silently replacing them

INPUTS.json gives exact byte commitments and revision-specific publisher URLs for
model.safetensors, config.json and tokenizer.json. Downloading is a separate,
prospectively admitted operation. Review applicable publisher terms first. After
authorized acquisition into a separate directory, verify only existing files:

  python3 -I -B verify_inputs.py --model-directory /absolute/path/to/model

This hashes all three files but never parses/loads the checkpoint. The checkpoint
weights identity agrees with the observed publisher LFS metadata and config bytes
were matched at that revision. The tokenizer commitment is from the executed data
registration; matching its current publisher bytes has not been checked here.
Reject a mismatch; do not replace commitments or use latest/main as a substitute.

The active service uses the V65 training-shard2 prefix: exactly2MiB compressed
bytes, with the recorded prefix hash, at the fixed C4 revision in INPUTS.json.
V65's protocol requires one bounded HTTP206 request, complete newline records,
64MiB maximum decoded content, at most20000 records and no transfer expansion or
retry. Its existing attempt is consumed: do not run its old launcher. Thirteen
records were selected in the declared hash order from2349 complete records,
with128 tokens each and no BOS/EOS. Membership is13 ->12 ->6. The existing saved
prefix and tokens remain external to the review package. A new retrieval cannot
be assumed to reproduce their bytes before verification.

The fixed root also depends on the complete historical exclusion inventory,
original base/calibration targets and actual data/qualification receipts. All15
direct V67 input commitments are listed without machine paths; their bodies are
not supplied here. Records and model/state arrays are deliberately not replaced
by fabricated examples. The full historical input/receipt closure is still needed
for a clean empirical reproduction. An unchanged SHA256 alone does not inspect
the recorded numerical state or demonstrate the claimed equality.

V68's proposed untouched-quality frame is DIFFERENT: validation-shard1, an8MiB
compressed range and8MiB decoded frame,320 selected articles, all prior exposures
and the entire V65 frame excluded. It is unregistered and unexecuted. Do not fetch
it or treat it as part of the completed evidence. Consult source-review's
research_v65/PROTOCOL.txt, research_v67/PROTOCOL.txt, research_v68/PROTOCOL.txt and
research_v69/PROTOCOL.txt for the exact versioned rules and gates.

4. Preserve runtime and execution boundaries

RUNTIME.json records the observed Linux CPU interpreter, compiler, numerical
library and tokenizer commitments, plus the installed codec inventory. Relative
library paths replace machine roots; all byte hashes retain the original scope.
The source component's34 identifier-adapted files are separately labelled copies.
They cannot satisfy the original registered-source hashes, paths or job identity.
Do not delete guards, rewrite historical receipts or launch their wrappers.

The numerical CPU runtime is CPython3.12.14, NumPy2.3.5, gmpy2 2.3.2 and the
isolated zstandard0.25.0 installation in a pinned Linux container. Tokenizers0.23.2
is required for data selection. The recorded package versions do not suffice:
native modules, GMP/MPFR/MPC, BLAS, compiler, Python modules, process limits and
container bytes are bound. SciPy was absent and is not required for the pinned
gelu_new route. The safetensors FILE format does not imply the safetensors Python
package is used. The historical GPU environment is separate; future V69 still
needs actual driver/device/build/file admission and CUDA qualification.

A fresh empirical reproduction needs a new registration and empty run paths,
complete actual inputs/exclusions, source/runtime qualification, scheduler and
resource admission, one-use intents, and saved terminal artifacts/costs. Preserve
the original scientific rules when comparing results; changed environments must
be reported as separate reproductions. V67's CPU64 software gate and later model/
state/oracle/cost audits are distinct from these114 local fixtures. V69's proposed
98 Linux checks and separate CUDA gate have not run. Cap values are ceilings,
not measured costs or completion estimates. No empirical command is supplied as
ready-to-run while these prerequisites are absent.

5. Evidence and release status

development-evidence-v69b.zip supplies selected summaries for E01--E15.
development-audit-receipts-v69.zip supplies nine labelled receipt derivatives;
their typed fields are preserved under string mappings. Neither archive includes
all raw numerical inputs or performs the original saved-byte audits. Original
receipts/commitments and failures remain preserved separately. The four exposed
quality screens reuse the same eight articles; they are not untouched confirmation.

See DEPENDENCIES.txt for publisher declarations and external notice locations.
Project release terms, transitive notices, complete empirical input closure,
whole-package anonymity, rendered page checks and claim-required evidence remain
open. The guide makes those gaps explicit; it does not grant redistribution rights
or declare a final anonymous or submission-ready archive.
