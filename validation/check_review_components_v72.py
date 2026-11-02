"""Current eight-component byte, navigation and direct-identity check; no execution."""
from pathlib import Path
import datetime,hashlib,json,re,stat,zipfile
R=Path(__file__).resolve().parents[1]
NAMES={'development-source-review-v72.zip':586,'development-evidence-v69b.zip':5,
       'development-audit-receipts-v69.zip':11,'development-reproduction-guide-v72.zip':6,
       'development-dependency-notices-v71c.zip':102,'development-selection-metadata-v71.zip':15,'development-service-evidence-v70.zip':5,'development-quality-evidence-v72.zip':10}
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def check():
    inventory={};texts={};artifacts={}
    for name,count in NAMES.items():
        path=R/'reports'/name;artifacts[name]=info(path.read_bytes())
        with zipfile.ZipFile(path) as z:
            items=z.infolist();assert len(items)==len(set(z.namelist()))==count
            assert sum(i.file_size for i in items)<64*2**20 and len({Path(i.filename).parts[0] for i in items})==1
            files={}
            for i in items:
                p=Path(i.filename)
                # ZipFile.writestr defaults to permission bits without a Unix type.
                # Accept that regular byte member, but never links, devices or dirs.
                assert not p.is_absolute() and '..' not in p.parts and not i.is_dir()
                assert stat.S_IFMT(i.external_attr>>16) in {0,stat.S_IFREG}
                assert not i.extra and not i.comment and i.file_size<16*2**20
                rel=str(Path(*p.parts[1:]));b=z.read(i);files[rel]=b;texts[name+'/'+rel]=b.decode()
        if 'MANIFEST.sha256' in files:
            m=dict(line.split('  ',1)[::-1] for line in files['MANIFEST.sha256'].decode().splitlines())
            assert set(m)==set(files)-{'MANIFEST.sha256'}
            for n,h in m.items():assert info(files[n])['sha256']==h
        else:
            m=json.loads(files['MANIFEST.json']);assert set(m)==set(files)-{'MANIFEST.json'}
            for n,e in m.items():assert info(files[n])==e
        inventory[name]={n:info(b) for n,b in files.items()}
    for name in ['reports/manuscript_v72.tex','reports/REVIEW_PACKAGE_README_V72.txt']:
        b=(R/name).read_bytes();artifacts[name]=info(b);texts[name]=b.decode()
    forbidden=re.compile(r'priyank|jairaj|poonam|\bcsis\b|csis_|172\.24\.16\.132|/nfs_home/|/Users/|github\.com/priyankjairaj100',re.I)
    findings=[dict(file=n,line=i,match=m.group()) for n,t in texts.items() for i,line in enumerate(t.splitlines(),1) for m in forbidden.finditer(line)]
    allowed=dict(file='development-dependency-notices-v71c.zip/cuda/distributions/sympy-1.14.0.dist-info/licenses/AUTHORS',line=590,match='Priyank')
    assert findings==[allowed],findings
    assert texts[allowed['file']].splitlines()[589]=='Priyank Patel <pspbot7@gmail.com>'
    assert not any(any(k in n for k in ['DERIVATION','EVIDENCE_INDEX_MAP','SOURCE_RECEIPT_SELECTION']) for n in texts)
    paper=texts['reports/manuscript_v72.tex'];nav=texts['reports/REVIEW_PACKAGE_README_V72.txt']
    references={e.strip() for group in re.findall(r'\\evidence\{([^}]+)\}',paper) for e in group.split(',')}
    assert references=={'E'+str(i).zfill(2) for i in range(1,18)}
    index=texts['development-evidence-v69b.zip/EVIDENCE_INDEX.txt']
    assert all(re.search(r'^'+e+':',index,re.M) for e in references-{'E16','E17'})
    assert {'E16_primary_receipt.json','E16_supplemental_receipt.json','E16_comparison_and_costs.json'}<=set(inventory['development-service-evidence-v70.zip'])
    assert all(name in nav for name in NAMES)
    guide='development-reproduction-guide-v72.zip/'
    supplied=json.loads(texts[guide+'INPUTS.json'])['components']
    assert supplied=={n:artifacts[n] for n in NAMES if n!='development-reproduction-guide-v72.zip'}
    for p in [f'research_v{v}/PROTOCOL.txt' for v in [65,67,68,69,70,71,72]]:
        assert p in inventory['development-source-review-v72.zip'] and p in texts[guide+'README.txt']
    fixtures=json.loads((R/'validation/v72_review_source_fixtures.json').read_bytes())
    assert fixtures['status']=='passed' and fixtures['tests']==213 and fixtures['source_files_unchanged']
    assert fixtures['failures']==fixtures['errors']==fixtures['skipped']==0 and not fixtures['denied_audit_events']
    selection=json.loads((R/'validation/v71_review_selection_component.json').read_bytes())
    assert selection['clean_extraction_exact'] and selection['typed_roundtrips']==11
    assert all(selection['refusal_probes'].values())
    assert selection['portable_check']['selected_records']==320 and selection['portable_check']['likelihood_result'] is False
    assert info((R/'reports/development-selection-metadata-v71.zip').read_bytes())=={k:selection['archive'][k] for k in ['bytes','sha256']}
    quality=json.loads((R/'validation/v72_quality_companion.json').read_bytes())
    assert quality['status']=='typed_derivatives_and_saved_scalar_check_verified'
    assert info((R/'reports/development-quality-evidence-v72.zip').read_bytes())=={k:quality['archive'][k] for k in ['bytes','sha256']}
    opened=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/outputs/second-research-draft.tex')
    assert opened.read_bytes()==(R/'reports/manuscript_v72.tex').read_bytes()
    return dict(schema='cross-component-review-v72',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='inventories_hashes_navigation_and_direct_identifiers_checked',artifacts=artifacts,
        archive_members=sum(NAMES.values()),text_files_checked=len(texts),internal_manifests_verified=8,
        evidence_references=sorted(references),protocol_links_verified=7,known_identity_findings=[],upstream_attribution_matches=findings,upstream_attribution_reviewed_and_preserved=True,private_mapping_files_included=False,
        clean_source_fixture_tests=213,manuscript_matches_open_file=True,full_source_manual_review=False,
        indirect_identity_linkability_assessed=False,full_anonymity_verified=False,full_empirical_input_closure=False,
        full_transitive_notices=False,full_reproduction_verified=False,empirical_work_executed=False,submission_ready=False)
if __name__=='__main__':
    r=check();out=R/'validation/v72_cross_component_review.json'
    with out.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:r[k] for k in ['status','archive_members','text_files_checked','internal_manifests_verified','clean_source_fixture_tests']}))
