"""Package E20 only from the exact completed V112 collection; no cluster access."""
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reporting_v117.render import checked_collection, render, identity, encoded, require
from reporting_v113.collect import EXPECTED, JOBS
from validation.package_review_bundle_v105 import zip_payload


def payload(collection):
    collection = Path(collection)
    result, bindings = checked_collection(collection)
    files = render(result)
    terminal = json.loads((collection/'terminal-stdout.json').read_bytes())
    primary = json.loads((collection/'receipts/primary-audit.json').read_bytes())
    supplemental = json.loads((collection/'receipts/supplemental-audit.json').read_bytes())
    program = json.loads((collection/'receipts/program.json').read_bytes())
    pairs = []
    for profile in ('distilgpt2', 'gpt2'):
        for row in primary['evidence'][profile]['comparisons']:
            pairs.append({k: row[k] for k in ('profile', 'cell', 'step',
                'actual_model_bytes_equal', 'actual_state_bytes_equal', 'actual_trust_bytes_equal')})
    require(len(pairs) == supplemental['evidence']['actual_model_pairs_equal'] == 16,
            'Both completed audits and every same-checkpoint comparison required')
    scope = dict(terminal['evidence'])
    summary = dict(schema='e20-matched-evidence-v119', program_sha256=EXPECTED,
        jobs=JOBS, actual_terminal=identity((collection/'terminal-stdout.json').read_bytes()),
        actual_primary=identity((collection/'receipts/primary-audit.json').read_bytes()),
        actual_supplemental=identity((collection/'receipts/supplemental-audit.json').read_bytes()),
        evidence=scope, comparisons=pairs,
        design={k: program[k] for k in ('stage_counts', 'retained_counts', 'point_route_policy')},
        original_records=4, tokens_per_record=128, fixed_normalization=512,
        independent_binary_audits_executed_on_cluster=True,
        this_package_reexecutes_pipeline=False, this_package_reaudits_binaries=False,
        numerical_limits_changed=False, old_attempts_or_sources_changed=False)
    files['audit-summary.json'] = encoded(summary)
    files['results.json'] = encoded(dict(schema='e20-all-request-scalars-v119',
        rows=result['rows'], comparisons=result['comparisons'], scope=scope,
        individual_optimization_effect_identified=False,
        preparation_shared_across_cells=True, preparation_reexecuted=False))
    files['provenance.json'] = encoded(dict(schema='e20-saved-input-commitments-v119',
        program_sha256=EXPECTED, actual_terminal=result['actual_terminal'],
        receipt_identities={name: {k: entry[k] for k in ('bytes', 'sha256')}
                            for name, entry in result['inputs'].items()},
        original_receipts_preserved=True, derivative_not_numerical_reexecution=True,
        source_hashes={name: identity((ROOT/name).read_bytes()) for name in (
            'validation/build_matched_evidence_v119.py', 'reporting_v117/render.py',
            'reporting_v113/collect.py', 'reporting_v113/reduce.py', 'reporting_v93/cost_scope.py')}))
    files['README.txt'] = b'''E20: complete matched point-token screen

This derivative preserves all sixteen requests from two related GPT-family
checkpoints, both retained endpoints, and four implementation cells. The two
completed cluster audits compare every model, state and trust sidecar against
fresh reconstruction of the same checkpoint. The original terminal binds the
audits, sources, artifacts, allocations and complete accounting. This packaging
step rechecks that bound metadata; it neither reruns models nor reaudits binaries.

The exposed four-record root contains 128 tokens per record. Normalization remains
512 as records are deleted 4->3->2. The point-token route was fixed prospectively
for all cells and oracles; box/Gram policies and approved grids did not change.
Both earlier preparations are reused and retain their full historical costs.
The earlier failed matched attempt and selected-stage diagnostic remain E19.

Every request is one observation, with uncontrolled OS cache. Individual effects
of bundled optimizations are not identified. Stable latency, cross-architecture
generality and predictive quality are not established. Earlier E17 quality is a
different target and is not transferred. The signed contrast convention is
candidate minus modern control: positive values mean slower or larger.

All request rows, nested source accesses, fallbacks and disjoint timing phases
are preserved. Decoder-only timing is unavailable. Preparation is shared; do not
assign its entire cost to one arm or silently call it zero. Scheduler, worker and
controller clocks overlap. Prior failed costs and the unrelated 12,602-second
unknown debit remain separate; no complete historical compute total is claimed.

The component contains descriptive metadata and no model/runtime/corpus binaries,
raw tokens or credentials. Hashes and job IDs can permit identity linkage. Its
integrity check is not a reproduction, anonymity or submission-readiness claim.
'''
    for name, expected in bindings.items():
        require(identity(Path(name).read_bytes()) == expected,
                'Input changed before evidence packaging')
    files['MANIFEST.json'] = encoded({n: identity(b) for n, b in sorted(files.items())})
    return files


def main(collection, destination):
    destination = Path(destination)
    require(not destination.exists(), 'New exclusive evidence archive required')
    files = payload(collection)
    zip_payload(destination, 'matched-evidence', files)
    with zipfile.ZipFile(destination) as archive:
        require({Path(n).name: archive.read(n) for n in archive.namelist()} == files,
                'Evidence archive roundtrip differs')
    print(json.dumps(dict(status='packaged_closed_matched_evidence',
        path=str(destination), archive=identity(destination.read_bytes()),
        files=len(files), requests=16, numerical_reexecution=False), sort_keys=True))


if __name__ == '__main__':
    main(*sys.argv[1:])
