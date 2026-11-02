"""Prepare labelled selection-metadata copies and a read-only portable checker."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from validation.build_review_source_v69 import MAPPING, replace
from validation.check_quality_selection_v71 import load, check, info, ARCHIVE as OBSERVATION

R = Path(__file__).resolve().parents[1]
OUT = R / 'reports/development-selection-metadata-v71.zip'
PRIVATE = R / 'docs/REVIEW_SELECTION_DERIVATION_V71.json'
REPORT = R / 'validation/v71_review_selection_component.json'


def enc(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def transform(value):
    if isinstance(value, str):
        return replace(value, MAPPING)
    if isinstance(value, list):
        return [transform(x) for x in value]
    if isinstance(value, dict):
        return {replace(k, MAPPING): transform(v) for k, v in value.items()}
    return value


def portable_checker():
    original = (R / 'validation/check_quality_selection_v71.py').read_text()
    tree = ast.parse(original)
    names = ('canonical', 'info', 'pairs', 'parse', 'reconcile_selection')
    nodes = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    functions = '\n\n'.join(ast.get_source_segment(original, nodes[n]) for n in names)
    header = '''"""Read-only saved-hash/selection check; no dataset or numerical execution."""
from pathlib import Path
import hashlib,json,re,sys
SHA = re.compile('[0-9a-f]{64}')

'''
    footer = '''

def main():
    root = Path(__file__).resolve().parent
    def readonly(event,args):
        if event == 'open':
            path,mode,flags = args
            import os
            if isinstance(path,int):
                raise PermissionError('No descriptor opens')
            path = Path(path).resolve()
            if not path.is_relative_to(root) or (mode and any(c in mode for c in 'wax+')) or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                raise PermissionError('Read only within this extracted component')
        elif event.startswith(('socket.','subprocess.')) or event in ('os.system','os.exec','os.posix_spawn','os.spawn','os.remove','os.rename','os.mkdir','os.rmdir','os.symlink','os.link','os.chmod'):
            raise PermissionError('No writes, processes or network')
    sys.addaudithook(readonly)
    entries = list(root.rglob('*'))
    assert all(not p.is_symlink() for p in entries)
    paths = {str(p.relative_to(root)):p for p in entries if p.is_file()}
    assert len(paths) <= 20 and sum(p.stat().st_size for p in paths.values()) <= 16*2**20
    manifest = parse((root/'MANIFEST.json').read_bytes())
    assert set(paths) == set(manifest)|{'MANIFEST.json'}
    for name,expected in manifest.items():
        assert info(paths[name].read_bytes()) == expected
    sources = parse((root/'SOURCES.json').read_bytes())
    x = {}
    for name,commitment in sources['derivative_metadata'].items():
        raw = (root/name).read_bytes()
        assert info(raw) == commitment
        x[name.removesuffix('.json')] = parse(raw)
    result = reconcile_selection(x)
    result.update(status='saved_metadata_decisions_verified',raw_corpus_or_tokens_read=False,
        corpus_to_hash_correspondence_verified=False,likelihood_result=False,
        original_registration_replayed=False,full_historical_input_closure=False)
    print(json.dumps(result,sort_keys=True))

if __name__ == '__main__':
    main()
'''
    source = header + functions + footer
    after = {n.name: n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
    assert all(ast.dump(nodes[n]) == ast.dump(after[n]) for n in names)
    return source.encode(), list(names)


def build():
    assert not any(p.exists() for p in (OUT, PRIVATE, REPORT))
    files = load()
    objects, facts, observation = check(files)
    chosen = sorted(name + '.json' for name in objects)
    payload, originals, changes = {}, {}, {}
    reverse = {value: key for key, value in MAPPING.items()}
    for name in chosen:
        raw = files[name]
        text = raw.decode()
        assert not any(value in text for value in MAPPING.values())
        adapted = replace(text, MAPPING)
        assert replace(adapted, reverse) == text
        assert json.loads(adapted) == transform(json.loads(raw))
        payload[name] = adapted.encode()
        originals[name] = info(raw)
        if adapted != text:
            changes[name] = dict(original=info(raw), derivative=info(payload[name]))
    payload['verify_selection.py'], functions = portable_checker()
    sources = dict(schema='review-selection-metadata-v71',
        derivative_metadata={n: info(payload[n]) for n in chosen},
        original_commitments=originals, current_observation_date=observation['captured_at_utc'],
        saved_data_audit_shared_implementation=True, derivative_strings_include_placeholders=True,
        original_bytes_not_claimed_for_derivatives=True, raw_tokens_or_corpus_included=False,
        actual_parameter_or_likelihood_result=False, full_historical_input_closure=False,
        scope='Registered selection and exclusion metadata, with account/host/path string replacements. '
              'Original hashes refer to the preserved originals, not the derivative bodies.')
    payload['SOURCES.json'] = enc(sources)
    payload['README.txt'] = b'''Selection and exclusion metadata: development review component

This component makes the actual inspected-frame hash inventory, complete before/
after exclusion sets, deterministic selection and saved-data audit receipts
inspectable without redistributing article text, URLs or token sequences. Public
dataset acquisition URLs and hashed article URLs remain in the metadata. It covers
3,801 complete validation-frame articles,2,778 eligible and320 selected. All1,021
short records remain excluded, including their complete-token hashes. The prior
60 quality IDs are preserved. The prior ledger contains7,615 IDs,21,371 content
hashes and29,736 token hashes; the successor has11,416,32,331 and44,538 respectively.

Eleven JSON copies preserve every typed field under declared account/host/path
string replacements. SOURCES.json distinguishes original commitments from the
new copied-body commitments. A private reversible mapping is excluded. This does
not make these copied registrations/receipts the exact executed bytes. Hashes and
source similarity may still link a public project; full indirect anonymity is not
established. No original experiment source, saved artifact, target or limit changed.

Offline check
Extract into a new directory and run an existing CPython3.10+ interpreter:
python3 -I -B verify_selection.py
No dependencies are installed. The script checks its component inventory/hashes,
recomputes every eligibility reason from saved hashes in original frame order,
the exact full-frame successor exclusion union, the fixed sampling order and the
selected metadata. Its five core functions match the separately checked reporting
implementation. It refuses missing, altered or extra files. Audit hooks deny
writes, subprocesses and network; they are not a complete operating-system sandbox.
Check the external ZIP hash as well; editable manifests are not signatures.

Scope of evidence
This is a metadata reconciliation. It does not read or download the compressed
source prefix, retokenize text, verify actual token words, reconstruct models or
compute likelihoods. The completed original data and full-frame audits remain the
source for corpus-to-hash correspondence. Those audits shared the preparation
tokenizer implementation. No corpus-uniform sampling, semantic deduplication,
untouched-quality outcome or model superiority is established by this checker.

The registered quality run remains separate. Its complete CPU/CUDA parity, loss,
model and cost audits are required before quality claims. Historical token bodies,
model/state binaries, the full historical input graph and external runtime are not
included here. Original one-use launchers must never be replayed. Any new numerical
reproduction needs its own input/runtime admission and prospective registration.

This is a staged component for the next coherent review bundle. Existing six-
component archive/guide bindings are unchanged. The expanded dependency notices
are staged separately. No final submission, complete rights assessment or new
project license is supplied by this preparation.
'''
    forbidden = re.compile(rb'priyank|jairaj|poonam|\bcsis\b|csis_|172\.24\.16\.132|/nfs_home/|/Users/', re.I)
    assert not [n for n, raw in payload.items() if forbidden.search(raw)]
    payload['MANIFEST.json'] = enc({n: info(b) for n, b in sorted(payload.items())})
    with zipfile.ZipFile(OUT, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            entry = zipfile.ZipInfo('selection-metadata/' + name, (2026, 10, 18, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with tempfile.TemporaryDirectory(prefix='selection-component-check-') as temp:
        root = Path(temp).resolve() / 'selection-metadata'
        root.mkdir()
        with zipfile.ZipFile(OUT) as archive:
            assert len(archive.namelist()) == len(set(archive.namelist())) == len(payload)
            for entry in archive.infolist():
                path = Path(entry.filename)
                assert path.parts[0] == 'selection-metadata' and len(path.parts) == 2
                assert stat.S_ISREG(entry.external_attr >> 16) and not entry.extra and not entry.comment
                (root / path.name).write_bytes(archive.read(entry))
        assert {p.name: p.read_bytes() for p in root.iterdir()} == payload
        def invoke():
            return subprocess.run([sys.executable, '-I', '-B', str(root / 'verify_selection.py')],
                                  text=True, capture_output=True, timeout=30, cwd=root)
        clean = invoke()
        assert clean.returncode == 0, clean.stderr
        result = json.loads(clean.stdout)
        assert all(result[k] == value for k, value in facts.items())
        probes = {}
        victim = root / 'before.json'
        raw = victim.read_bytes()
        victim.write_bytes(raw + b' ')
        probes['altered_file'] = invoke().returncode != 0
        victim.unlink()
        probes['missing_file'] = invoke().returncode != 0
        victim.write_bytes(raw)
        (root / 'unexpected.txt').write_text('unexpected')
        probes['extra_file'] = invoke().returncode != 0
        assert all(probes.values())
    private = dict(schema='private-selection-derivation-v71',exclude_from_anonymous_review=True,
        mapping=MAPPING,original_observation=dict(path=str(OBSERVATION.relative_to(R)),**info(OBSERVATION.read_bytes())),
        original_files=originals,changed_files=changes,archive=dict(path=str(OUT.relative_to(R)),**info(OUT.read_bytes())))
    PRIVATE.write_bytes(enc(private))
    report = dict(schema='review-selection-component-check-v71',
        verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive=private['archive'],
        original_metadata_files=len(chosen),adapted_files=len(changes),package_members=len(payload),
        typed_roundtrips=len(chosen),metadata_bytes_original=sum(len(files[n]) for n in chosen),
        core_functions_ast_equal=functions,clean_extraction_exact=True,portable_check=result,
        refusal_probes=probes,known_identity_findings=[],private_mapping_packaged=False,
        indirect_anonymity_verified=False,full_historical_input_closure=False,
        integrated_into_current_bundle=False,numerical_experiment_executed=False,
        submission_ready=False)
    REPORT.write_bytes(enc(report))
    print(json.dumps({k: report[k] for k in ('archive','original_metadata_files','adapted_files','package_members','refusal_probes')}))


if __name__ == '__main__':
    build()
