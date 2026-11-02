"""Build an external-input guide from existing commitments; never acquire inputs."""
from pathlib import Path
import datetime
import hashlib
import json
import zipfile

R = Path(__file__).resolve().parents[1]
OUT = R / 'reports/review-reproduction-v69'
ARCHIVE = R / 'reports/development-reproduction-guide-v69.zip'


def info(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def read(name):
    return json.loads((R / name).read_text())


def build():
    assert not OUT.exists() and not ARCHIVE.exists(), 'Preserve previous preparations'
    service = read('handoff/registration_v67.json')
    data = read('handoff/registration_v65.json')
    metadata = read('validation/v69_publisher_license_metadata.json')
    pinned = read('validation/v69_pinned_publisher_metadata.json')
    components = {name: info((R / 'reports' / name).read_bytes()) for name in [
        'development-source-review-v69c.zip', 'development-evidence-v69b.zip',
        'development-audit-receipts-v69.zip']}
    revision = metadata['items']['distilgpt2']['revision']
    model = {}
    for label, name in [('checkpoint_weights', 'model.safetensors'), ('checkpoint_config', 'config.json')]:
        e = service['inputs'][label]
        model[name] = {k: e[k] for k in ['bytes', 'sha256']}
    tokenizer = [e for p, e in data['prior_inputs'].items() if p.endswith('/tokenizer.json')]
    assert len(tokenizer) == 1
    model['tokenizer.json'] = tokenizer[0]
    for name, e in model.items():
        e['retrieval_url'] = 'https://huggingface.co/distilbert/distilgpt2/resolve/' + revision + '/' + name
        e['downloaded_for_this_guide'] = False
        e['binding_scope'] = 'Frozen installed experiment input; retrieved bytes must match before use'
    inputs = dict(schema='review-external-input-commitments-v69', components=components,
        model_repository='distilbert/distilgpt2', model_revision=revision, model_files=model,
        model_config_publisher_bytes_verified=pinned['items']['model_config']['sha256'] == model['config.json']['sha256'],
        tokenizer_publisher_bytes_verified=False,
        service_inputs={k: {f: e[f] for f in ['bytes', 'sha256']} for k, e in service['inputs'].items()},
        service_input_count=len(service['inputs']), service_input_bodies_included=False,
        data_policy=data['policy'],
        data_url='https://huggingface.co/datasets/allenai/c4/resolve/' + data['policy']['revision'] + '/en/c4-train.00002-of-01024.json.gz',
        data_prefix_commitment={k: service['inputs']['source_prefix'][k] for k in ['bytes', 'sha256']},
        decoded_frame_complete_records=2349, historical_quality_exclusions=60,
        full_reproduction_verified=False, new_acquisition_or_launch_authorized=False)
    runtime = service['runtime']
    packages = {}
    for name in ['numpy', 'gmpy2']:
        packages[name] = dict(version=runtime['packages'][name]['version'], files={})
        for path, e in runtime['packages'][name]['files'].items():
            rel = path.split('/site-packages/', 1)[1]
            assert rel not in packages[name]['files']
            packages[name]['files'][rel] = e
    dependency_files = {p.split('/deps/', 1)[1]: e for p, e in service['dependency_files'].items()}
    tokenizer_files = {p.split('/site-packages/', 1)[1]: e for p, e in data['tokenizer_runtime_files'].items()}
    assert len(dependency_files) == 11 and len(tokenizer_files) == 18
    environment = dict(schema='review-runtime-commitments-v69',
        cpu_python=runtime['python'], compiler=runtime['compiler'],
        numpy_configuration=runtime['numpy_configuration'], packages=packages,
        tokenizers=dict(version=data['tokenizers_version'], files=tokenizer_files),
        zstandard=dict(version='0.25.0', files=dependency_files),
        scipy=runtime['packages']['scipy'],
        container_sha256='10ffb205f553197e110472e208522d0c73bcaf62e1a0571b860bf7bae49933b1',
        container_rebuild_reproduces_hash=False, container_distributed=False,
        library_file_paths_relative_to_external_installation=True,
        environment_packages_or_container_installed=False,
        local_fixture_environment=dict(python='3.12.7', system='macOS', numpy='2.3.5',
            tests=114, empirical_runtime_qualified=False),
        future_cuda=dict(admission_complete=False, historical_python_family='3.10',
            historical_numpy='2.2.6', historical_torch='2.10.0',
            actual_device_driver_build_and_file_bindings_required=True))
    readme = '''External-input and reproduction guide: development preparation

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
  /absolute/path/to/python3.12 -I -B qualify_review_source.py . \\
    --temporary /absolute/path/to/fresh-fixture-output/tmp \\
    --report /absolute/path/to/fresh-fixture-output/report.json \\
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
'''
    notices = '''External dependencies and attribution record: development preparation

This is an inventory of observed publisher declarations and notice locations,
not a license grant, complete NOTICE file or legal clearance. No third-party
library binaries, wheels, container, corpus or model is redistributed here.
Project ownership and release terms remain unassigned; authors must resolve them
before public code release. Historical execution files remain unchanged.

Checkpoint: DistilGPT2, Hugging Face/distilbert; publisher declares Apache2.0.
https://huggingface.co/distilbert/distilgpt2/blob/2290a62682d06624634c1f46a6ad5be0f47f38aa/README.md
Dataset: C4, Allen Institute for AI; pinned card declares ODC-BY and refers to
Common Crawl content terms. Database terms do not grant every underlying page's
rights. Article text/tokens are excluded from this package.
https://huggingface.co/datasets/allenai/c4/blob/1588ec454efa1a09f29cd18ddd04fe05fc8653a2/README.md
https://opendatacommons.org/licenses/by/1-0/
https://commoncrawl.org/terms-of-use/

Observed PyPI declarations,16 October2026 (exact version pages):
NumPy2.3.5 CPU and2.2.6 historical CUDA: BSD classifier.
https://pypi.org/project/numpy/2.3.5/
https://pypi.org/project/numpy/2.2.6/
gmpy2 2.3.2: LGPL-3.0-or-later.
https://pypi.org/project/gmpy2/2.3.2/
zstandard0.25.0: BSD-3-Clause.
https://pypi.org/project/zstandard/0.25.0/
tokenizers0.23.2: Apache classifier.
https://pypi.org/project/tokenizers/0.23.2/
torch2.10.0: BSD-3-Clause license field; actual installed build is separately bound.
https://pypi.org/project/torch/2.10.0/

RUNTIME.json identifies28 actual NumPy/gmpy2 module/library files,18 tokenizer
runtime files and11 installed codec files, including the codec LICENSE file hash.
This guide does not include their license text. Preserve each installed
distribution's actual dist-info/licenses, LICENSE/NOTICE and bundled-library
notices in the external installation; consult them before redistribution.
NumPy's BLAS/Fortran dependencies, gmpy2's GMP/MPFR/MPC, Python, compiler/libc,
the container base, Torch's bundled libraries and CUDA/driver components require
their own applicable notices. These have not all been collected or cleared here.
The safetensors0.6.2 publisher was inspected previously but no installed/required
version was established; it is deliberately absent from runtime requirements.

The existing manuscript embeds the unmodified ACL style with its original source
header. Its style provenance and attribution must remain in the eventual paper
source bundle. The fixture checker and documentation are project-authored files,
subject to the project's unresolved release terms. No dependency installation or
license replacement is performed by the guide or its verifier.
'''
    payload = {'README.txt': readme.encode(), 'INPUTS.json': encode(inputs),
        'RUNTIME.json': encode(environment), 'DEPENDENCIES.txt': notices.encode(),
        'verify_inputs.py': (R / 'validation/verify_review_inputs_v69.py').read_bytes()}
    forbidden = [b'poonam', b'priyankjairaj', b'/nfs_home', b'/Users/', b'csis.', b'csis_', b'172.24.16.132']
    for name, raw in payload.items():
        assert not any(token in raw for token in forbidden), name
    payload['MANIFEST.json'] = encode({k: info(v) for k, v in sorted(payload.items())})
    OUT.mkdir()
    for name, raw in payload.items():
        with (OUT / name).open('xb') as f:
            f.write(raw)
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, raw in sorted(payload.items()):
            item = zipfile.ZipInfo('reproduction-guide/' + name, date_time=(2026,10,16,0,0,0))
            item.external_attr = 0o100644 << 16
            z.writestr(item, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    sources = ['handoff/registration_v67.json', 'handoff/registration_v65.json',
        'validation/v69_publisher_license_metadata.json', 'validation/v69_pinned_publisher_metadata.json',
        'validation/v69_review_source_c_fixtures.json', 'research_v69/run_cpu.sbatch',
        'research_v69/execution_gate.py', 'research_v68/PROTOCOL.txt']
    report = dict(schema='review-reproduction-guide-build-v69',
        captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        archive=dict(path=str(ARCHIVE.relative_to(R)), **info(ARCHIVE.read_bytes())),
        payload={k: info(v) for k, v in payload.items()}, source_bindings={n: info((R/n).read_bytes()) for n in sources},
        model_inputs=3, service_inputs=len(inputs['service_inputs']), runtime_module_files=28,
        tokenizer_runtime_files=18, codec_files=11, clean_extraction_verified=False,
        external_inputs_acquired=False, full_reproduction_verified=False,
        full_anonymity_verified=False, project_license_assigned=False, complete_transitive_notices=False)
    (R / 'validation/v69_review_reproduction_guide.json').write_bytes(encode(report))
    print(json.dumps(report['archive']))


if __name__ == '__main__':
    build()
