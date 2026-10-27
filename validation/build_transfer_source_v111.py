"""Review-only source supplement for the failed screen and selected-stage study."""
import ast,json,tarfile,zipfile
from pathlib import Path
from validation.build_review_source_v69 import MAPPING,Rename,replace,info,enc
from validation.package_review_bundle_v105 import zip_payload
R=Path(__file__).resolve().parents[1]
S=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/work/second-speed-campaign')


def build():
    target=R/'reports/development-transfer-source-v111.zip'
    report=R/'validation/v111_transfer_source.json';derivation=R/'docs/REVIEW_SOURCE_DERIVATION_V111.json'
    assert not any(p.exists() for p in (target,report,derivation))
    archive=S/'v110-prepared/token-stage-diagnostic-v110-source-only.tar'
    preparation=json.loads((S/'v110-prepared/preparation.json').read_bytes())
    assert info(archive.read_bytes())==preparation['archive']
    with tarfile.open(archive) as tf:
        members=tf.getmembers();assert all(m.isfile() for m in members) and len(members)==len({m.name for m in members})==1243
        actual={m.name:tf.extractfile(m).read() for m in members}
    inventory=json.loads(actual.pop('inventory.json'));assert len(inventory)==1242
    assert all(info(actual[n])==e for n,e in inventory.items())
    prior={}
    for name in ('development-source-review-v72.zip','development-optimization-source-v105.zip'):
        with zipfile.ZipFile(R/'reports'/name) as z:
            for n in z.namelist():
                relative='/'.join(Path(n).parts[1:])
                if relative in inventory:
                    assert relative not in prior;prior[relative]=(name,z.read(n))
    assert len(prior)==930
    adapted={};coverage={};omitted={};changes={};parsed=0;reverse={v:k for k,v in MAPPING.items()}
    for name,e in sorted(inventory.items()):
        if name.startswith(('gates/','recovery-evidence/')):
            omitted[name]=dict(identity=e,reason='Execution-specific receipt excluded; original preserved in research repository and summarized by E18/E19')
            continue
        raw=actual[name];assert (R/name).read_bytes()==raw
        text=raw.decode();assert not any(v in text for v in MAPPING.values())
        edited=replace(text,MAPPING);assert replace(edited,reverse)==text
        if name.endswith('.py'):
            assert ast.dump(Rename().visit(ast.parse(text)))==ast.dump(ast.parse(edited));parsed+=1
        blob=edited.encode();component=prior[name][0] if name in prior else target.name
        if name in prior:assert blob==prior[name][1]
        else:
            adapted[name]=blob
            if raw!=blob:changes[name]=dict(original=e,derivative=info(blob))
        coverage[name]=dict(component=component,derivative=info(blob))
    assert len(coverage)==1226 and len(adapted)==296 and len(omitted)==16
    adapted['SOURCE_COVERAGE.json']=enc(dict(schema='transfer-source-coverage-v111',executed_archive_entries=1242,
        files=coverage,omitted_execution_receipts=omitted,source_copies_only=True,empirical_reproduction=False))
    adapted['README.txt']=b'''Source inspection supplement for E19,27 October2026

This adds296 source/protocol/test copies to the unchanged930 earlier copies,
covering all1226 source entries of the executed V110 package. Sixteen execution-
specific receipt entries are omitted and enumerated in SOURCE_COVERAGE.json.
The package includes preserved failed V104/V109 source and successful V110
selected-stage code. It does not contain or qualify the prepared V111 screen.

Declared path/account/node/repository strings are reversibly adapted, with Python
AST equality except those strings checked. Source maps and original receipts are
public in the research repository, outside this archive. Adapted sources are for
inspection, not execution against original hash gates. Do not run historical
launchers or retry consumed attempts. No model, corpus, token bodies, runtime
binaries or credentials are added. Small generated test fixtures are retained.
No new project license is assigned; indirect linkability remains possible.

Offline byte/source-coverage checks do not reproduce numerical certification,
independently compare stage codes or validate the copied code for execution.
E19 retains the selected-stage-only boundary and the earlier full-screen failure.
'''
    adapted['MANIFEST.json']=enc({n:info(b) for n,b in sorted(adapted.items())})
    zip_payload(target,'transfer-source',adapted)
    with zipfile.ZipFile(target) as z:assert {n.removeprefix('transfer-source/'):z.read(n) for n in z.namelist()}==adapted
    assert all(info((R/n).read_bytes())==inventory[n] for n in coverage)
    derivation.write_bytes(enc(dict(schema='transfer-source-derivation-v111',exclude_from_review_archive=True,mapping=MAPPING,
        changed_files=changes,original_inventory=inventory,original_archive=preparation['archive'],source_coverage=coverage)))
    result=dict(schema='transfer-source-supplement-v111',archive=info(target.read_bytes()),source_files_added=296,
        inherited_source_files=930,total_source_files=1226,excluded_execution_receipts=16,new_copies_adapted=len(changes),
        python_asts_checked=parsed,all_source_originals_unchanged=True,archive_roundtrip_verified=True,
        empirical_work_executed=False,adapted_code_execution_qualified=False,full_anonymity_verified=False)
    report.write_bytes(enc(result));print(json.dumps(result,sort_keys=True))

if __name__=='__main__':build()
