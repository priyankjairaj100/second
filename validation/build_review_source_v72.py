"""Current source review copies, with separately registered accounting recovery."""
from pathlib import Path
import ast,datetime,hashlib,json,zipfile
from validation.build_review_source_v69 import MAPPING,Rename,replace,info,enc
from validation.check_frozen_sources_v72 import check
R=Path(__file__).resolve().parents[1]
def build():
    targets=[R/'reports/development-source-review-v72.zip',R/'docs/REVIEW_SOURCE_DERIVATION_V72.json',R/'validation/v72_review_source_build.json']
    assert not any(p.exists() for p in targets)
    inventory=check()['numerical_sources'];inventory.update(json.loads((R/'validation/v69_source_package_supplement.json').read_bytes())['sources']);assert len(inventory)==583
    reverse={v:k for k,v in MAPPING.items()};adapted={};changed={};parsed=0
    for name,e in sorted(inventory.items()):
        raw=(R/name).read_bytes();assert info(raw)==e;s=raw.decode();assert not any(v in s for v in MAPPING.values()),name
        a=replace(s,MAPPING);assert replace(a,reverse)==s,name
        if name.endswith('.py'):
            before=ast.parse(s,feature_version=(3,10));after=ast.parse(a,feature_version=(3,10));assert ast.dump(Rename().visit(before))==ast.dump(after),name;parsed+=1
        adapted[name]=a.encode()
        if a!=s:changed[name]=dict(original=e,derivative=info(a.encode()),replacement_counts={k:s.count(k) for k in MAPPING if k in s})
    adapted['README.txt']=f'''Current source review component,18 October2026

583 source/protocol/wrapper copies:575 historical/current numerical files, six
separately registered accounting-recovery files and two legacy import helpers.
{len(changed)} copies adapt declared account/repository/node/path strings only.
All copies reverse to preserved originals through a separate private mapping;
all{parsed} Python ASTs differ only by those string replacements. This is not
proof of numerical or operational equivalence after adaptation.

/review/project and /review/runtime are illustrative paths, review_user an account,
reviewcluster.* illustrative nodes and REVIEW_OWNER/REVIEW_REPOSITORY a repository
placeholder. No dependency, model, corpus or runtime binaries, raw article tokens,
live registrations, ledgers or private mappings are included. Tiny generated
fixtures remain. Project release terms are unassigned; no new rights are granted.
Do not run old launchers or use these adapted bytes to satisfy original hashes.
Reproduction needs separately admitted inputs/runtime/paths/budgets and one-use
registration. Never replay existing jobs or alter frozen attempts.

Local fixture check
Use an existing CPython3.12.7/NumPy2.3.5 environment and empty temporary directory:
python -I -B qualify_review_source.py PATH_TO_THIS_DIRECTORY --report REPORT.json
--log TESTS.txt --temporary EMPTY_TEMP_DIRECTORY
Use fresh report/log paths. The checker enforces120/121 CPU seconds and64MiB per
file, denies network/process launches except bash syntax checks, and confines
writes to the supplied outputs. Python audit hooks are not a full OS sandbox.
The same213-test subset covers22 data,94 failed-admission and97 corrected-campaign
fixtures. Production constructors/checkpoint/runtime/Slurm boundaries are mocked;
tiny CPU likelihood fixtures run. Six sequential numerical fixtures are excluded.
The new recovery tests are not part of this portable subset: one requires the
private actual scheduler snapshot, which this anonymous component excludes.
Their earlier local qualification is separate from actual recovery-job success.

V71 actual cluster Linux103 checks, CUDA24 generated comparisons, checkpoint and
sequential audits,1920 GPU losses and24 CPU references are complete. The original
accounting closure failed; separately registered V72 recovery passed without
repeating inference. E17 preserves both outcomes and cost observations. Source
fixtures alone do not reproduce any scientific result. Complete external inputs,
licensing, indirect anonymity and rendered manuscript checks remain unresolved.
All earlier source components remain unchanged under their original names.
'''.encode()
    adapted['qualify_review_source.py']=(R/'validation/qualify_review_source_v71.py').read_bytes()
    assert all(not any(k in b.decode() for k in MAPPING) for b in adapted.values())
    files={n:info(b) for n,b in sorted(adapted.items())}
    adapted['MANIFEST.sha256']=''.join(e['sha256']+'  '+n+'\n' for n,e in files.items()).encode();files['MANIFEST.sha256']=info(adapted['MANIFEST.sha256'])
    with zipfile.ZipFile(targets[0],'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,b in sorted(adapted.items()):
            i=zipfile.ZipInfo('source-review/'+name,(2026,10,18,0,0,0));i.external_attr=0o100644<<16;z.writestr(i,b,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    for name,e in inventory.items():assert info((R/name).read_bytes())==e
    archive=dict(path=str(targets[0].relative_to(R)),**info(targets[0].read_bytes()))
    targets[1].write_bytes(enc(dict(schema='review-source-private-derivation-v72',exclude_from_anonymous_archive=True,mapping=MAPPING,changed_files=changed,original_files=inventory,derivative_files=files,archive=archive)))
    report=dict(schema='review-source-component-build-v72',status='built_pending_clean_fixture_qualification',archive=archive,
        original_source_count=583,unchanged_original_sources=583,adapted_copies=len(changed),python_asts_checked=parsed,
        all_copies_reverse_to_original_bytes=True,python_changes_only_declared_strings=True,package_files=len(files),
        empirical_work_executed=False,full_anonymity_verified=False,full_reproduction_verified=False)
    targets[2].write_bytes(enc(report));print(json.dumps(report))
if __name__=='__main__':build()
