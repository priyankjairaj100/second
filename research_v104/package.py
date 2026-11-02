"""Exact preserved V103 source package plus new source and actual V101 gate."""
from pathlib import Path
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ast,io,json,tarfile
from research_v80.io import require,read,info
from research_v90.admission import ledger_identity
from research_v101.config import design as admission_design
from research_v101.package import tar_extent
from research_v104.software import SUITES
from research_v104.storage_plan import build,requests
from src.run_store import strict_json,canonical_json

def validate_files(files):
    inventory={n:info(b) for n,b in sorted(files.items())};ledger_identity('0'*64,inventory)
    require(0<len(files)<4096 and sum(e['bytes'] for e in inventory.values())<=64*2**20,'Bounded complete source package required')
    for n,b in files.items():
        require(Path(n).suffix in ('.py','.txt','.json','.sh','.sbatch','.c'),'Source/receipt package only')
        if n.endswith('.py'):ast.parse(b)
    for name,(modules,count) in SUITES.items():
        actual=sum(sum(isinstance(node,ast.FunctionDef) and node.name.startswith('test_') for node in ast.walk(
            ast.parse(files[module.replace('.','/')+'.py']))) for module in modules)
        require(actual==count,'Prepared software census differs: '+name)
    return inventory

def main(admission_archive,admission_program,terminal_report,destination):
    repo=Path(__file__).resolve().parents[1];p=strict_json(read(admission_program,maximum=64*2**20))
    raw=read(terminal_report,maximum=64*2**20);report=strict_json(raw)
    require(report['schema']=='matched-target-terminal-v101' and report['status']=='verified'
        and report['program_sha256']==info(canonical_json(p))['sha256']
        and all(p.get(k)==v for k,v in admission_design().items()),'Actual matching V101 terminal/program required')
    carry=read(repo/'pilots/dispatch-failure-v103-20261026/failed-dispatch-carry.json',maximum=2**20)
    failed=strict_json(carry)
    read(admission_archive,failed['source_archive'],maximum=64*2**20,retain=False);files={}
    with tarfile.open(admission_archive,'r:') as tar:
        members=tar.getmembers();require(all(m.isfile() for m in members) and len(members)==failed['source_count']+1
            and len({m.name for m in members})==len(members),'Exact preserved V103 source archive census required')
        inventory=tar.extractfile('inventory.json').read()
        require(info(inventory)==failed['source_inventory'],'Actual source inventory differs')
        for name,e in strict_json(inventory).items():
            blob=tar.extractfile(name).read();require(info(blob)==e,'Actual source member changed')
            if (repo/name).exists():read(repo/name,e,maximum=64*2**20,retain=False)
            files[name]=blob
    for path in sorted((repo/'research_v104').iterdir()):
        if path.is_file() and path.suffix in ('.py','.txt','.json','.sh','.sbatch','.c'):files[str(path.relative_to(repo))]=read(path,maximum=64*2**20)
    require(files['gates/target-admission-terminal.json']==canonical_json(report),'Preserved actual target gate differs')
    files['gates/v103-dispatch-failure-carry.json']=carry
    files['gates/v101-program.json']=canonical_json(p)
    files['gates/target-admission-origin.json']=canonical_json(dict(original_terminal=info(raw),actual_cluster_inputs_require_reopening=True))
    from research_v104.package_imports import close_dependencies,check_extracted
    reachable=close_dependencies(files,repo);isolated_imports=check_extracted(files)
    inventory=validate_files(files);manifest=canonical_json(inventory);members={**files,'inventory.json':manifest};expected=tar_extent(members)
    out=Path(destination).absolute();require(not any(p.is_symlink() for p in (out,*out.parents)),'Nonsymbolic destination required')
    out.mkdir(parents=True,exist_ok=False);(out/'inventory.json').write_bytes(manifest)
    archive=out/'matched-complete-recovery-v104-source-only.tar'
    with archive.open('xb') as stream,tarfile.open(fileobj=stream,mode='w|') as tar:
        for name,blob in sorted(members.items()):
            member=tarfile.TarInfo(name);member.size=len(blob);member.mode=0o600;tar.addfile(member,io.BytesIO(blob))
    extent=read(archive,maximum=64*2**20,retain=False);require(extent['bytes']==expected,'Tar extent differs from declared bound')
    plan=build(inventory,extent['bytes'])
    result=dict(status='prepared_locally_not_registered',source_count=len(inventory),inventory=info(manifest),archive=extent,
        before_upload_requests=requests(plan,inventory,extent['bytes']),storage_plan=plan,
        expected_linux_tests=sum(v[1] for v in SUITES.values()),linux_qualified=False,uploaded=False,registered=False,empirical_execution=False,
        reachable_project_modules=reachable,isolated_extracted_host_imports=isolated_imports)
    (out/'preparation.json').write_bytes(canonical_json(result));print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main(*sys.argv[1:])
