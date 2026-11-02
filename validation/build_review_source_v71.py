"""Prepare current registered source copies, preserving every earlier component."""
from pathlib import Path
import ast,datetime,hashlib,json,zipfile
from validation.build_review_source_v69 import MAPPING,Rename,replace,info,enc
from validation.check_frozen_sources_v71 import check
R=Path(__file__).resolve().parents[1]
def build():
    targets=[R/'reports/development-source-review-v71.zip',R/'docs/REVIEW_SOURCE_DERIVATION_V71.json',R/'validation/v71_review_source_build.json']
    assert not any(p.exists() for p in targets)
    inventory=check()['numerical_sources']
    inventory.update(json.loads((R/'validation/v69_source_package_supplement.json').read_bytes())['sources'])
    assert len(inventory)==577
    reverse={v:k for k,v in MAPPING.items()};adapted={};changed={};parsed=0
    for name,e in sorted(inventory.items()):
        b=(R/name).read_bytes();assert info(b)==e;s=b.decode();assert not any(v in s for v in MAPPING.values()),name
        a=replace(s,MAPPING);assert replace(a,reverse)==s,name
        if name.endswith('.py'):
            before=ast.parse(s,feature_version=(3,10));after=ast.parse(a,feature_version=(3,10))
            assert ast.dump(Rename().visit(before))==ast.dump(after),name;parsed+=1
        adapted[name]=a.encode()
        if a!=s:changed[name]=dict(original=e,derivative=info(a.encode()),replacement_counts={k:s.count(k) for k in MAPPING if k in s})
    adapted['README.txt']=f'''Current source review component,18 October2026

This component contains577 source/protocol/wrapper copies:575 registered historical
and current numerical files plus two unchanged legacy static-import helpers. It
preserves the failed earlier admission implementation alongside the corrected
quality/frame-audit implementations. The old v69c component remains unchanged.
{len(changed)} copies adapt only declared account/repository/node/path strings.
All copies reverse exactly to preserved original bytes using a separate private
map. All{parsed} Python ASTs differ only by these declared string replacements.
This is not proof of numerical or operational equivalence after adaptation.

/review/project and /review/runtime are illustrative paths, review_user an account,
reviewcluster.* illustrative nodes and REVIEW_OWNER/REVIEW_REPOSITORY a repository
placeholder. These are not live services. No dependency/model/corpus/environment
binaries, real article tokens, live registrations, ledgers or private mappings are
included. Tiny generated source fixtures are retained. Project release terms are
unassigned; this component does not grant new rights or cover all dependencies.

Do not run old empirical launchers or satisfy original source hashes with these
adapted bytes. A reproduction needs separately admitted paths, actual inputs,
runtime/source bindings, resource budgets, one-use registration and attempts.
Never replay existing job IDs or alter a frozen experiment to run this component.

Local fixture check
Use an existing CPython3.12.7/NumPy2.3.5 environment and an empty temporary directory:
python -I -B qualify_review_source.py PATH_TO_THIS_DIRECTORY --report REPORT.json
--log TESTS.txt --temporary EMPTY_TEMP_DIRECTORY
Use fresh report/log paths. The checker enforces120/121 CPU seconds and64MiB per
file, denies network and process launches except bash syntax checks, and confines
writes to the supplied temporary directory/report/log. Python audit hooks are not
a full OS sandbox. It expects213 generated local tests:22 data,94 failed-campaign
source fixtures and97 corrected-campaign fixtures. Production constructors,
checkpoint/runtime/Slurm boundaries are mocked. Tiny CPU likelihood fixtures run.
The six inherited sequential numerical fixtures are not part of this local subset.

Actual cluster Linux103 checks and generated CUDA24 comparisons are separately
recorded in the research handoff. Their success is not untouched empirical quality.
The active model construction and downstream losses/audits remain unfinished at
this package checkpoint. Clean extraction and these fixtures do not reproduce the
scientific experiment. Full external-input closure, licensing, indirect anonymity,
actual runtime reproduction and final manuscript checks remain incomplete.
'''.encode()
    adapted['qualify_review_source.py']=(R/'validation/qualify_review_source_v71.py').read_bytes()
    assert all(not any(k in b.decode() for k in MAPPING) for b in adapted.values())
    files={n:info(b) for n,b in sorted(adapted.items())}
    adapted['MANIFEST.sha256']=''.join(e['sha256']+'  '+n+'\n' for n,e in files.items()).encode()
    files['MANIFEST.sha256']=info(adapted['MANIFEST.sha256'])
    with zipfile.ZipFile(targets[0],'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,b in sorted(adapted.items()):
            i=zipfile.ZipInfo('source-review/'+name,date_time=(2026,10,18,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
    for name,e in inventory.items():assert info((R/name).read_bytes())==e
    archive=dict(path=str(targets[0].relative_to(R)),**info(targets[0].read_bytes()))
    targets[1].write_bytes(enc(dict(schema='review-source-private-derivation-v71',exclude_from_anonymous_archive=True,mapping=MAPPING,changed_files=changed,original_files=inventory,derivative_files=files,archive=archive)))
    report=dict(schema='review-source-component-build-v71',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='built_pending_clean_fixture_qualification',archive=archive,original_source_count=577,unchanged_original_sources=577,exact_byte_original_copies=577-len(changed),adapted_copies=len(changed),python_asts_checked=parsed,all_copies_reverse_to_original_bytes=True,python_changes_only_declared_strings=True,package_files=len(files),full_anonymity_verified=False,full_reproduction_verified=False,original_execution_changed=False,empirical_work_executed=False)
    targets[2].write_bytes(enc(report));print(json.dumps(report))
if __name__=='__main__':build()
