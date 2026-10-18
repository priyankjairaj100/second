"""Add three verified upstream CPU notices, preserving earlier payload bytes."""
from pathlib import Path
import datetime, hashlib, json, stat, tarfile, tempfile, zipfile
from validation.check_cpu_notice_inventory_v71 import load, check, info
R=Path(__file__).resolve().parents[1]
OLD=R/'reports/development-dependency-notices-v71.zip'
NEW=R/'reports/development-dependency-notices-v71c.zip'

def enc(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def build():
    assert not NEW.exists()
    raw=load();observation,packages,extras=check(raw)
    with zipfile.ZipFile(OLD) as archive:
        prior={str(Path(*Path(n).parts[1:])):archive.read(n) for n in archive.namelist()}
    assert len(prior)==99
    manifest=json.loads(prior['MANIFEST.json']);assert manifest=={n:info(b) for n,b in prior.items() if n!='MANIFEST.json'}
    files=dict(prior);sources=json.loads(files['SOURCES.json'])
    sources['schema']='expanded-installed-notices-v71c'
    sources['additional_cpu_notices']={'package':'numpy','version':'2.3.5','captured_at_utc':observation['captured_at_utc'],
        'scope':'Installed RECORD-selected notice text only; this does not identify all native dependencies or establish historical build/binary correspondence.',
        'binary_bodies_rechecked':False,'full_native_source_correspondence':False,'files':{}}
    for name in extras:
        target='cpu-additional/'+name.removeprefix('numpy/notices/')
        assert target not in files
        files[target]=raw[name]
        source_rel=name.removeprefix('numpy/notices/')
        item=observation['packages']['numpy']['installed_notice_entries'][source_rel]
        assert info(files[target])=={k:item[k] for k in ('bytes','sha256')}
        sources['additional_cpu_notices']['files'][target]=dict(installed_relative_path=source_rel,**info(files[target]))
    sources['additional_cpu_notices']['record_metadata_sha256']=info(raw['numpy/RECORD'])['sha256']
    files['SOURCES.json']=enc(sources)
    readme=prior['README.txt'].decode()
    start=readme.index('This expanded component is staged')
    readme=readme[:start]+'''This version adds three installed NumPy2.3.5 notice texts outside its dist-info
license tree: random generator headers, masked arrays and random implementation.
Their text is unchanged and each matches its installed RECORD size/hash entry.
The four earlier CPU installed texts also match the later observation. This gives
43 notice/attribution texts: five earlier CPU/publisher texts,35 CUDA/Python texts,
and three additional CPU notices. The earlier96 non-index member payloads remain
byte-identical. SOURCES.json records the added files and narrow observation scope.

Use this component only with a guide that binds its new filename/hash. Earlier
components and bundles remain unchanged. No old archive filename is overwritten.
This is a development component, not a final submission, license clearance,
complete native-source inventory or a new scientific result.
'''
    files['README.txt']=readme.encode()
    files['MANIFEST.json']=enc({n:info(b) for n,b in sorted(files.items()) if n!='MANIFEST.json'})
    assert len(files)==102
    preserved=set(prior)-{'MANIFEST.json','README.txt','SOURCES.json'}
    assert len(preserved)==96 and all(files[n]==prior[n] for n in preserved)
    for n,b in files.items():
        assert all(v not in b for v in (b'poonam',b'priyankjairaj',b'/nfs_home/',b'/Users/',b'csis.',b'172.24.16.132')),n
    with zipfile.ZipFile(NEW,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for n,b in sorted(files.items()):
            i=zipfile.ZipInfo('dependency-notices/'+n,(2026,10,18,0,0,0));i.create_system=3;i.external_attr=(stat.S_IFREG|0o644)<<16
            archive.writestr(i,b,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with tempfile.TemporaryDirectory(prefix='second-notices-v71c-') as temp:
        dest=Path(temp)
        with zipfile.ZipFile(NEW) as archive:
            for entry in archive.infolist():
                p=Path(entry.filename);assert not p.is_absolute() and '..' not in p.parts and stat.S_ISREG(entry.external_attr>>16)
                out=dest/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(archive.read(entry))
        base=dest/'dependency-notices';extracted={str(p.relative_to(base)):p.read_bytes() for p in base.rglob('*') if p.is_file()}
        assert extracted==files
        def verify(data):
            expected=json.loads(data['MANIFEST.json']);return expected=={n:info(b) for n,b in data.items() if n!='MANIFEST.json'}
        assert verify(extracted)
        victim=next(n for n in files if n.startswith('cpu-additional/'))
        changed=dict(extracted);changed[victim]+=b'altered';assert not verify(changed)
        missing=dict(extracted);missing.pop(victim);assert not verify(missing)
    result=dict(schema='review-installed-notices-v71c',verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        archive=dict(path=str(NEW.relative_to(R)),**info(NEW.read_bytes())),members=len(files),notice_texts=43,
        added_cpu_notices=3,earlier_payloads_byte_identical=96,clean_extraction_exact=True,
        changed_file_rejected=True,missing_file_rejected=True,full_native_correspondence=False,
        complete_transitive_notices=False,project_license_assigned=False,binaries_included=False,
        previous_component=dict(path=str(OLD.relative_to(R)),**info(OLD.read_bytes())),
        source_observation='validation/v71_cpu_notice_inventory_20261018_b.tar.gz',scientific_result=False,submission_ready=False)
    with (R/'validation/v71c_review_notices.json').open('x') as output:output.write(enc(result).decode())
    print(json.dumps({k:result[k] for k in ('archive','members','notice_texts','earlier_payloads_byte_identical')}))
if __name__=='__main__':build()
