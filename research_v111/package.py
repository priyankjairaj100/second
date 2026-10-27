"""Preserve all V110 source bytes; add separately qualified full point-policy screen."""
import ast,io,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
from research_v80.io import require,read,info
from research_v101.package import tar_extent
from research_v111.software import SUITES
from research_v111.storage_plan import build,requests
from src.run_store import strict_json,canonical_json
ARCHIVE_SHA='c158220d0af6d505e3ba611fa58cb6278efc22ce00255a592448d663677959e7'


def main(parent_archive,gate_path,destination):
    repo=Path(__file__).resolve().parents[1]
    require(read(parent_archive,maximum=64*2**20,retain=False)['sha256']==ARCHIVE_SHA,'Exact original archive required')
    files={}
    with tarfile.open(parent_archive,'r:') as tar:
        members=tar.getmembers();require(len(members)==1243 and all(m.isfile() for m in members)
            and len({m.name for m in members})==1243,'Exact original member census required')
        inv=strict_json(tar.extractfile('inventory.json').read())
        for n,e in inv.items():
            require(not Path(n).is_absolute() and '..' not in Path(n).parts,'Safe member required')
            b=tar.extractfile(n).read();require(info(b)==e,'Original bytes changed')
            if (repo/n).exists():read(repo/n,e,maximum=64*2**20,retain=False)
            files[n]=b
    for path in sorted((repo/'research_v111').iterdir()):
        if path.is_file() and path.suffix in ('.py','.sh','.sbatch','.txt','.json'):
            files[str(path.relative_to(repo))]=read(path,maximum=4*2**20)
    gate=strict_json(read(gate_path,maximum=4*2**20))
    files['gates/v110-selected-stage-closure.json']=canonical_json(gate)
    from research_v111.package_imports import close_dependencies,check_extracted
    close_dependencies(files,repo)
    for n,b in files.items():
        if n.endswith('.py'):ast.parse(b)
    for label,(modules,count) in SUITES.items():
        actual=sum(sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for n in
            ast.walk(ast.parse(files[m.replace('.','/')+'.py']))) for m in modules)
        require(actual==count,'Test census differs: '+label)
    isolated=check_extracted(files)
    inventory={n:info(b) for n,b in sorted(files.items())};manifest=canonical_json(inventory)
    members={**files,'inventory.json':manifest};expected=tar_extent(members)
    dest=Path(destination).absolute();dest.mkdir(parents=True,exist_ok=False)
    (dest/'inventory.json').write_bytes(manifest)
    archive=dest/'matched-complete-recovery-v111-source-only.tar'
    with archive.open('xb') as stream,tarfile.open(fileobj=stream,mode='w|') as tar:
        for n,b in sorted(members.items()):
            m=tarfile.TarInfo(n);m.size=len(b);m.mode=0o600;tar.addfile(m,io.BytesIO(b))
    extent=read(archive,maximum=64*2**20,retain=False);require(extent['bytes']==expected,'Archive extent differs')
    plan=build(inventory,extent['bytes'])
    report=dict(schema='matched-point-policy-package-v111',status='prepared_not_registered',archive=extent,
        inventory=info(manifest),source_count=len(inventory),parent_source_count=1242,
        isolated_check=isolated,expected_linux_tests=sum(v[1] for v in SUITES.values()),
        storage_plan=plan,before_upload_requests=requests(plan,inventory,extent['bytes']),
        registered=False,uploaded=False,numerical_execution=False)
    (dest/'preparation.json').write_bytes(canonical_json(report));print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main(*sys.argv[1:])
