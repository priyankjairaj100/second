"""Bounded cross-component inventory and known-identity review, without execution."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import stat
import zipfile

R=Path(__file__).resolve().parents[1]


def info(raw):
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def check():
    names=['development-source-review-v69c.zip','development-evidence-v69b.zip',
        'development-audit-receipts-v69.zip','development-reproduction-guide-v69.zip']
    artifacts={};texts={};inventory={}
    pattern=re.compile(r'priyank|jairaj|poonam|\bcsis\b|csis_|172\.24\.16\.132|/nfs_home/|/Users/|github\.com/priyankjairaj100',re.I)
    findings=[]
    for name,expected in zip(names,[537,5,11,6]):
        path=R/'reports'/name;artifacts[name]=info(path.read_bytes())
        with zipfile.ZipFile(path) as z:
            entries=z.infolist();assert len(entries)==len(set(z.namelist()))==expected
            assert sum(i.file_size for i in entries)<64*2**20
            roots={Path(i.filename).parts[0] for i in entries};assert len(roots)==1
            files={}
            for i in entries:
                p=Path(i.filename)
                assert not p.is_absolute() and '..' not in p.parts and not i.is_dir()
                assert stat.S_ISREG(i.external_attr>>16) and i.file_size<16*2**20
                assert not i.extra and not i.comment
                raw=z.read(i);assert len(raw)==i.file_size
                rel=str(Path(*p.parts[1:]));files[rel]=raw
                texts[name+'/'+rel]=raw.decode('utf-8')
            if 'MANIFEST.sha256' in files:
                manifest={line[66:]:line[:64] for line in files['MANIFEST.sha256'].decode().splitlines()}
                assert set(manifest)==set(files)-{'MANIFEST.sha256'}
                for rel,h in manifest.items():assert info(files[rel])['sha256']==h
            else:
                manifest=json.loads(files['MANIFEST.json'])
                assert set(manifest)==set(files)-{'MANIFEST.json'}
                for rel,e in manifest.items():assert info(files[rel])==e
            inventory[name]={rel:info(raw) for rel,raw in files.items()}
    for name in ['reports/manuscript_v69.tex','reports/REVIEW_PACKAGE_README_V69.txt']:
        raw=(R/name).read_bytes();artifacts[name]=info(raw);texts[name]=raw.decode()
    private_names=['REVIEW_SOURCE_DERIVATION','REVIEW_RECEIPT_DERIVATION','REVIEW_HISTORY_DERIVATION',
        'EVIDENCE_INDEX_MAP','SOURCE_RECEIPT_SELECTION']
    assert not any(any(token in name for token in private_names) for name in texts)
    for name,t in texts.items():
        for n,line in enumerate(t.splitlines(),1):
            for match in pattern.finditer(line):findings.append(dict(file=name,line=n,match=match.group()))
    assert not findings,findings
    paper=texts['reports/manuscript_v69.tex']
    references=set()
    for group in re.findall(r'\\evidence\{([^}]+)\}',paper):
        references.update(x.strip() for x in group.split(','))
    assert references=={'E'+str(i).zfill(2) for i in range(1,16)}
    index=texts['development-evidence-v69b.zip/EVIDENCE_INDEX.txt']
    assert all(re.search(r'^'+re.escape(e)+':',index,re.M) for e in references)
    crosswalk={
        'E12':['E10_primary.json','E10_additive.json','E12_exposed_quality.json','E11_cpu_cuda_parity.json'],
        'E13':['E13_adaptive_quality.json'],
        'E14':['E14_primary_recovery.json','E14_additive_recovery.json'],
        'E15':['E15_lossless_measurement.json','E15_lossless_audit.json']}
    receipts=inventory['development-audit-receipts-v69.zip']
    assert set(sum(crosswalk.values(),[]))=={n for n in receipts if n.endswith('.json')}
    navigation=texts['reports/REVIEW_PACKAGE_README_V69.txt']
    assert all(n in navigation for n in sum(crosswalk.values(),[]))
    source=inventory['development-source-review-v69c.zip']
    guide=texts['development-reproduction-guide-v69.zip/README.txt']
    for p in ['research_v65/PROTOCOL.txt','research_v67/PROTOCOL.txt','research_v68/PROTOCOL.txt','research_v69/PROTOCOL.txt']:
        assert p in source and p in guide
    supplied=json.loads(texts['development-reproduction-guide-v69.zip/INPUTS.json'])['components']
    assert supplied=={n:artifacts[n] for n in names[:3]}
    opened=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/outputs/second-research-draft.tex')
    assert opened.read_bytes()==(R/'reports/manuscript_v69.tex').read_bytes()
    result=dict(schema='cross-component-review-v69',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='inventories_hashes_known_identifiers_and_navigation_checked',artifacts=artifacts,
        archive_members=sum(len(x) for x in inventory.values()),text_files_checked=len(texts),
        internal_manifests_verified=4,known_identity_findings=findings,private_mapping_files_included=False,
        evidence_references=sorted(references),receipt_filename_crosswalk=crosswalk,
        stale_filename_grouping_resolved_by_navigation=True,protocol_links_verified=4,
        manuscript_matches_open_file=True,manuscript_edited=False,
        reviewer_prose_scope_review_completed=True,full_source_manual_review=False,
        indirect_identity_linkability_assessed=False,full_anonymity_verified=False,
        full_empirical_input_closure=False,full_transitive_notices=False,
        full_reproduction_verified=False,empirical_work_executed=False,submission_ready=False)
    (R/'validation/v69_cross_component_review.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ['status','archive_members','text_files_checked','internal_manifests_verified','submission_ready']}))


if __name__=='__main__':check()
