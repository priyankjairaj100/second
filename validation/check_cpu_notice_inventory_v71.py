"""Reconcile a reporting-only CPU notice inventory with saved registration pins."""
from pathlib import Path, PurePosixPath
from email.parser import BytesParser
import base64, csv, datetime, hashlib, io, json, posixpath, tarfile, zipfile
R = Path(__file__).resolve().parents[1]
ARCHIVE = R / 'validation/v71_cpu_notice_inventory_20261018_b.tar.gz'
REG = '3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
ROOT = '/nfs_home/users/poonam/second-20261010'

def info(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def load():
    with tarfile.open(ARCHIVE) as archive:
        members=archive.getmembers()
        assert len(members)==len({m.name for m in members})==20
        assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts for m in members)
        assert sum(m.size for m in members)<8*2**20
        return {m.name:archive.extractfile(m).read() for m in members}

def check(files):
    c=json.loads(files['collection.json'])
    assert c['files']=={n:info(b) for n,b in files.items() if n!='collection.json'}
    assert c['registration_sha256']==REG
    assert c['collector_sha256']==info((R/'validation/collect_cpu_notice_inventory_v71.py').read_bytes())['sha256']
    raw=(R/'handoff/registration_v71_quality.json').read_bytes();assert info(raw)['sha256']==REG
    p=json.loads(raw);pins={}
    def visit(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k.startswith(ROOT+'/') and isinstance(v,dict) and {'bytes','sha256'}<=v.keys():
                    entry={a:v[a] for a in ('bytes','sha256')};assert k not in pins or pins[k]==entry;pins[k]=entry
                else:visit(v)
        elif isinstance(x,list):
            for v in x:visit(v)
    visit(p['dependency_files']);visit(p['runtimes']['cpu'])
    assert set(c['packages'])=={'gmpy2','numpy','tokenizers','zstandard'}
    summaries={}
    for name,d in c['packages'].items():
        metadata=BytesParser().parsebytes(files[name+'/METADATA'])
        assert metadata['Name'].lower()==name and metadata['Version']==d['version']
        parent=PurePosixPath(d['directory']).parent
        rows=list(csv.reader(io.StringIO(files[name+'/RECORD'].decode())))
        assert len(rows)==len({row[0] for row in rows})
        native={};notices={};matches={};unhashed=[];actual={}
        for rel,digest,length in rows:
            assert not PurePosixPath(rel).is_absolute()
            absolute=posixpath.normpath(str(parent/rel));assert absolute.startswith(ROOT+'/')
            if digest:
                assert digest.startswith('sha256=') and length.isdigit()
                entry=dict(bytes=int(length),sha256=base64.urlsafe_b64decode(digest[7:]+'='*(-len(digest[7:])%4)).hex())
            else:
                assert not length;entry=None
            if '.so' in PurePosixPath(rel).name:
                assert entry is not None;native[rel]=entry
            if absolute in pins:
                if entry is None:
                    assert absolute==d['directory']+'/RECORD';unhashed.append(rel)
                    assert info(files[name+'/RECORD'])==pins[absolute]
                else:
                    assert entry==pins[absolute];matches[rel]=entry
            if PurePosixPath(rel).name.lower().startswith(('license','licence','copying','notice','authors','eula')):
                key=name+'/notices/'+str(PurePosixPath(absolute).relative_to(parent))
                assert info(files[key])==entry
                notices[rel]=dict(file=key,**entry)
        for basename in ('METADATA','RECORD','WHEEL'):
            absolute=d['directory']+'/'+basename
            if absolute in pins:
                assert info(files[name+'/'+basename])==pins[absolute]
                actual[basename]=pins[absolute]
        assert native==d['native_entries'] and notices==d['installed_notice_entries']
        assert matches==d['record_matches_registered_files'] and unhashed==d['unhashed_registered_record_entries']
        assert actual==d['actual_text_files_match_registered']
        assert d['metadata_pinned']==('METADATA' in actual)
        summaries[name]=dict(version=d['version'],record_native_entries=len(native),installed_notice_files=len(notices),
            record_matches_registered_files=len(matches),actual_text_pins_matched=len(actual),
            unhashed_record_self_entries=len(unhashed))
    original={
      'gmpy2/notices/gmpy2-2.3.2.dist-info/licenses/COPYING':'gmpy2/licenses/COPYING',
      'gmpy2/notices/gmpy2-2.3.2.dist-info/licenses/COPYING.LESSER':'gmpy2/licenses/COPYING.LESSER',
      'numpy/notices/numpy-2.3.5.dist-info/LICENSE.txt':'numpy/LICENSE.txt',
      'zstandard/notices/zstandard-0.25.0.dist-info/licenses/LICENSE':'zstandard/licenses/LICENSE'}
    with zipfile.ZipFile(R/'reports/development-dependency-notices-v71.zip') as archive:
        for current,earlier in original.items():assert files[current]==archive.read('dependency-notices/earlier/notices/'+earlier)
    extras=sorted(n for n in files if '/notices/' in n and n not in original)
    assert extras==['numpy/notices/numpy/_core/include/numpy/random/LICENSE.txt',
                    'numpy/notices/numpy/ma/LICENSE','numpy/notices/numpy/random/LICENSE.md']
    return c,summaries,extras

if __name__=='__main__':
    files=load();c,packages,extra=check(files)
    probes={}
    for name in ['tokenizers/RECORD',extra[0]]:
        changed=dict(files);changed[name]=changed[name]+b'\n'
        try:check(changed)
        except AssertionError:probes[name]='rejected'
        else:raise AssertionError('Altered metadata/notice accepted')
    result=dict(schema='cpu-notice-inventory-reconciliation-v71',checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        observed_at_utc=c['captured_at_utc'],archive=dict(path=str(ARCHIVE.relative_to(R)),**info(ARCHIVE.read_bytes())),
        status='metadata_and_record_commitments_reconciled',packages=packages,member_count=len(files),
        actual_notice_files=7,earlier_notice_files_byte_identical=4,additional_notice_files=extra,additional_notices_integrated=False,
        record_native_entries=29,record_entries_matching_registered_pins=56,actual_metadata_files_matching_registered_pins=4,
        refusal_probes=probes,model_or_corpus_read=False,new_job=False,binary_bodies_rechecked=False,
        native_source_versions_determined=False,original_wheel_build_correspondence=False,
        complete_transitive_notices=False,redistribution_clearance=False,scientific_result=False,
        unresolved=['GMP/MPFR/MPC exact source versions and attribution; SONAMEs are not release-version evidence',
          'tokenizers installed notice absent; pinned publisher notice remains a source-level declaration',
          'Rust/transitive-native, Python base/container/compiler/libc and GPU driver/system scope',
          'author-controlled project release terms'])
    with (R/'validation/v71_cpu_notice_inventory_reconciliation.json').open('x') as output:
        json.dump(result,output,indent=2,sort_keys=True);output.write('\n')
    print(json.dumps({k:result[k] for k in ('status','member_count','record_native_entries','actual_notice_files','record_entries_matching_registered_pins','additional_notice_files')}))
