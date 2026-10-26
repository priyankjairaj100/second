"""Exclusive local source package, after an actual V89 terminal report exists.

No network, cluster mutation, registration, submission, checkpoints or corpus.
Reuses the exact V89 source tar; all frozen local counterparts must still match.
"""
from pathlib import Path
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ast,io,json,tarfile
from research_v80.io import require,info,read
from research_v90.admission import ledger_identity
from research_v90.recovery_gate import PROGRAM_SHA
from research_v101.storage_plan import build,requests
from research_v101.software import SUITES
from src.run_store import canonical_json,strict_json
FROZEN_TAR_SHA='e1994e4d8b873f5361752904f117381562463af3bcfbbcebe4a144973cc9019a'
FIXTURES=('pilots/recovery-v89-20261023/execution-20261024/program.json',
          'pilots/transfer-engineering-v90-20261024/cluster-reconciliation.json')


def validate_files(files):
    require(type(files) is dict and 0<len(files)<4096,'Finite exact package census required')
    inventory={name:info(blob) for name,blob in sorted(files.items())}
    ledger_identity('0'*64,inventory)
    require(sum(e['bytes'] for e in inventory.values())<=64*2**20,'Extracted package exceeds64MiB')
    for name,blob in files.items():
        require(Path(name).suffix in ('.py','.txt','.json','.sh','.sbatch','.c'),'Source/receipt-only package required')
        if name.endswith('.py'):ast.parse(blob)
    for suite,(modules,count) in SUITES.items():
        actual=0
        for module in modules:
            tree=ast.parse(files[module.replace('.','/')+'.py'])
            actual+=sum(isinstance(node,ast.FunctionDef) and node.name.startswith('test_') for node in ast.walk(tree))
        require(actual==count,'Prepared suite census differs: '+suite)
    return inventory


def tar_extent(files):
    """Count actual PAX headers and tar record padding before any package write."""
    total=1024
    for name,blob in sorted(files.items()):
        entry=tarfile.TarInfo(name);entry.size=len(blob);entry.mode=0o600
        total+=len(entry.tobuf(format=tarfile.PAX_FORMAT))+(len(blob)+511)//512*512
    result=(total+tarfile.RECORDSIZE-1)//tarfile.RECORDSIZE*tarfile.RECORDSIZE
    require(result<=64*2**20,'Tar package would exceed64MiB before writing')
    return result


def main(frozen_archive,terminal_report,destination):
    repo=Path(__file__).resolve().parents[1]
    require(read(frozen_archive,maximum=64*2**20,retain=False)['sha256']==FROZEN_TAR_SHA,'Exact failed-software V99 source archive required')
    files={}
    with tarfile.open(frozen_archive,'r:') as tar:
        members=tar.getmembers();require(len(members)==1029 and all(m.isfile() for m in members),'Exact regular frozen archive census required')
        require(len({m.name for m in members})==len(members),'Duplicate source archive members')
        old_inventory=strict_json(tar.extractfile('inventory.json').read())
        for name,entry in old_inventory.items():
            data=tar.extractfile(name).read();require(info(data)==entry,'Frozen archive member changed')
            local=repo/name
            if local.exists():read(local,entry,maximum=64*2**20,retain=False)
            files[name]=data
    for version in (101,):
        for path in sorted((repo/f'research_v{version}').iterdir()):
            if path.is_file() and path.suffix in ('.py','.txt','.json','.sh','.sbatch','.c'):
                files[str(path.relative_to(repo))]=read(path,maximum=64*2**20)
    for name in FIXTURES:files[name]=read(repo/name,maximum=64*2**20)
    # The old package omitted this transitive import used by V90 outputs and
    # metadata layout. Preserve its existing source bytes; do not edit V90/V91.
    name='research_v84/config.py';files[name]=read(repo/name,maximum=64*2**20)
    for name in ('v91-preparation-failure.json','v91-failed-setup-review.json'):
        files['gates/'+name]=read(repo/'pilots/optimization-closure-v98-20261026'/name,maximum=64*2**20)
    raw=read(terminal_report,maximum=64*2**20);gate=strict_json(raw)
    require(gate['schema']=='recovery-terminal-v89' and gate['status']=='verified' and gate['program_sha256']==PROGRAM_SHA,
        'Actual successful V89 terminal report required before packaging')
    require(files['gates/v89-terminal.json']==canonical_json(gate),'Actual V89 gate differs from preserved V91 package')
    files['gates/v99-failed-software-carry.json']=read(repo/'pilots/admission-packaging-v99-20261026/failed-software-carry.json',maximum=2**20)
    from research_v101.package_imports import close_dependencies,check_extracted
    reachable=close_dependencies(files,repo)
    isolated_imports=check_extracted(files)
    inventory=validate_files(files);manifest=canonical_json(inventory)
    members={**files,'inventory.json':manifest};expected_archive_bytes=tar_extent(members)
    out=Path(destination).absolute();require(not any(p.is_symlink() for p in (out,*out.parents)),'Nonsymbolic package destination required')
    out.mkdir(parents=True,exist_ok=False);(out/'inventory.json').write_bytes(manifest)
    archive=out/'matched-transfer-admission-v101-source-only.tar'
    with archive.open('xb') as stream,tarfile.open(fileobj=stream,mode='w|') as tar:
        for name,blob in sorted(members.items()):
            member=tarfile.TarInfo(name);member.size=len(blob);member.mode=0o600;tar.addfile(member,io.BytesIO(blob))
    archive_info=read(archive,maximum=64*2**20,retain=False)
    require(archive_info['bytes']==expected_archive_bytes,'Actual tar extent differs from admitted header census')
    plan=build(inventory,archive_info['bytes'])
    report=dict(status='prepared_locally_not_registered',source_count=len(inventory),inventory=info(manifest),archive=archive_info,
        expected_linux_tests=sum(v[1] for v in SUITES.values()),linux_qualified=False,uploaded=False,registered=False,launched=False,
        before_upload_requests=requests(plan,inventory,archive_info['bytes']),storage_plan=plan,
        scientific_result=False,actual_remote_inputs_reverified=False,
        reachable_project_modules=reachable,isolated_extracted_host_imports=isolated_imports)
    (out/'preparation.json').write_bytes(canonical_json(report));print(json.dumps(report,sort_keys=True))

if __name__=='__main__':main(*sys.argv[1:])
