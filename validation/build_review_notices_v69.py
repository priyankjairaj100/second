"""Package exact observed notices only; no dependency or input acquisition."""
from pathlib import Path
import datetime, hashlib, json, re, stat, tarfile, tempfile, zipfile

R=Path(__file__).resolve().parents[1]
ARCHIVE=R/'reports/development-dependency-notices-v69.zip'

def info(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def encode(obj):return (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def build():
    assert not ARCHIVE.exists(), 'Preserve prior archive'
    record=json.loads((R/'validation/v69_installed_dependency_notice_check.json').read_text())
    original=R/record['archive']['path']
    assert info(original.read_bytes())=={k:record['archive'][k] for k in ['bytes','sha256']}
    files={};provenance={}
    with tarfile.open(original,'r:gz') as t:
        for name,e in record['files'].items():
            m=t.getmember(name);assert m.isfile() and m.size<=2**20
            raw=t.extractfile(m).read();assert info(raw)==e
            files['notices/'+name]=raw
            provenance['notices/'+name]=dict(**e,origin='Installed CPU distribution license tree',
                observed_at_utc=record['captured_at_utc'],
                binding_scope='Observed distribution notice; only zstandard was already part of the frozen runtime inventory')
    assert len(files)==4
    directory=R/'validation/publisher-notices-v69/tokenizers'
    license_raw=(directory/'LICENSE').read_bytes();cargo=(directory/'Cargo.toml').read_bytes()
    assert blob(license_raw)=='261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64'
    assert blob(cargo)=='e9d6bcc3c749a7f0f674a37275aa115ba34afba9'
    assert b'version = "0.23.2"' in cargo and b'license = "Apache-2.0"' in cargo
    revision='88a4498ad4ea1a9487b0a9b0ff881383fd5a06a3'
    base='https://github.com/huggingface/tokenizers/blob/'+revision+'/'
    files['notices/tokenizers/LICENSE']=license_raw
    provenance['notices/tokenizers/LICENSE']=dict(**info(license_raw),origin='Publisher source at immutable commit',
        repository='huggingface/tokenizers',revision=revision,version='0.23.2',url=base+'LICENSE',
        git_blob_sha1=blob(license_raw),cargo_metadata=dict(**info(cargo),url=base+'tokenizers/Cargo.toml',git_blob_sha1=blob(cargo)),
        binding_scope='Publisher source notice; installed wheel/source equivalence not verified')
    sources=dict(schema='review-observed-notice-sources-v69',files=provenance,
        installed_package_versions=dict(numpy='2.3.5',gmpy2='2.3.2',tokenizers='0.23.2',zstandard='0.25.0'),
        dependency_binaries_included=False,complete_transitive_notices=False,
        tokenizer_installed_dist_info_notice_found=False,project_license_assigned=False)
    files['SOURCES.json']=encode(sources)
    files['README.txt']=b'''Observed dependency notices: development companion

Five unchanged notice texts are included: NumPy LICENSE, gmpy2 COPYING and
COPYING.LESSER, zstandard LICENSE, and the tokenizers publisher LICENSE.
SOURCES.json distinguishes installed distribution notices from publisher source.
No package, shared library, model, corpus or container is included or installed.

The four installed CPU texts were observed in versioned distribution directories.
The zstandard text matches an original frozen runtime commitment. The other
notice bytes were observed later and do not retroactively extend runtime pins.
NumPy's file contains its supplied bundled-library notices. Generic GPL/LGPL
texts do not by themselves identify every GMP/MPFR/MPC component notice.

Tokenizers' installed distribution directory had no notice. The supplied text
comes instead from its publisher's immutable source commit, whose Cargo metadata
declares version0.23.2 and Apache-2.0. Its Git blob commitment was verified. This
does not prove which Rust dependencies/features are in the installed wheel or
establish installed-wheel/source equivalence. Rust transitive notices remain open.

Python/system/compiler/container and the future GPU environment's complete
notices are not supplied. These are external installations, not vendored binaries.
No license is assigned to the research project's own source by this companion.
The authors' release terms and final artifact review remain separate.

MANIFEST.json lists the size and SHA256 of every other member. Verify this ZIP's
externally supplied hash and then the manifest before relying on these copies.
This is a supplement to the four existing review components, not a replacement.
Their bytes and the manuscript are unchanged. This archive is not an experiment
result, complete rights assessment or submission-ready package.
'''
    files['MANIFEST.json']=encode({n:info(raw) for n,raw in sorted(files.items())})
    assert len(files)==8
    pattern=re.compile(rb'priyank|jairaj|poonam|\bcsis\b|172\.24\.16\.132|/nfs_home/|/Users/',re.I)
    assert not any(pattern.search(raw) for raw in files.values())
    with zipfile.ZipFile(ARCHIVE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(files.items()):
            entry=zipfile.ZipInfo('dependency-notices/'+name,(2026,10,16,0,0,0))
            entry.create_system=3;entry.external_attr=(stat.S_IFREG|0o644)<<16
            entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,raw)
    with tempfile.TemporaryDirectory(prefix='second-notice-review-') as temp:
        root=Path(temp)
        with zipfile.ZipFile(ARCHIVE) as z:
            assert len(z.namelist())==len(set(z.namelist()))==8
            for entry in z.infolist():
                path=Path(entry.filename);assert not path.is_absolute() and '..' not in path.parts
                assert stat.S_ISREG(entry.external_attr>>16) and not entry.extra and not entry.comment
                out=root/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(entry))
        extracted={str(p.relative_to(root/'dependency-notices')):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        assert extracted==files
        manifest=json.loads(extracted['MANIFEST.json'])
        assert manifest=={n:info(raw) for n,raw in extracted.items() if n!='MANIFEST.json'}
    result=dict(schema='review-observed-dependency-notices-v69',verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        archive=dict(path=str(ARCHIVE.relative_to(R)),**info(ARCHIVE.read_bytes())),files=8,notice_texts=5,
        notice_bytes=sum(len(raw) for name,raw in files.items() if name.startswith('notices/')),
        notice_sources=provenance,clean_extraction_exact=True,manifest_checked=True,known_identity_findings=[],
        notice_texts_unchanged=True,original_four_components_unchanged=True,manuscript_edited=False,
        earlier_publisher_failure_preserved=True,installed_tokenizer_notice_missing=True,
        installed_wheel_source_equivalence_verified=False,complete_transitive_notices=False,
        project_license_assigned=False,packages_installed=False,scientific_result=False,submission_ready=False)
    output=R/'validation/v69_review_dependency_notices.json'
    with output.open('xb') as stream:stream.write(encode(result))
    print(json.dumps({k:result[k] for k in ['archive','files','notice_texts','notice_bytes','submission_ready']}))

if __name__=='__main__':build()
