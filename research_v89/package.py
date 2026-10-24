"""Local source-only packaging; no network, registration, cleanup or submission."""
import ast
import io
import json
from pathlib import Path
import sys
import tarfile
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json
from research_v80.io import info, require
from research_v89.storage_plan import build, requests
from research_v89.prepare import SOFTWARE, EXPECTED_TESTS
from research_v86.admission import terminal_disposition
from research_v83.accounting import cpu_time


def normalized_accounting(raw):
    lines = raw.decode().splitlines()
    require(lines[0] == 'JobIDRaw|State|ExitCode|Start|End|Elapsed|TotalCPU|AllocCPUS|ReqMem|MaxRSS|NodeList|Reason',
            'Exact saved original accounting columns required')
    rows = []
    for line in lines[1:]:
        f = line.split('|')
        require(len(f) == 12, 'Original accounting row changed')
        elapsed, _ = cpu_time(f[5])
        require(elapsed % 10**9 == 0, 'Exact integer allocation duration required')
        rows.append('|'.join([*f[:3], str(elapsed//10**9), f[6], f[7], f[8], f[10]]))
    result = '\n'.join(rows)+'\n'
    terminal_disposition(result)
    return result.encode()


def main(frozen_program, output):
    repo = Path(__file__).resolve().parents[1]
    raw = Path(frozen_program).read_bytes()
    require(info(raw)['sha256'] == '5bead3425eb9bb4bec645ac12e681b45e62d87762cef0f15179aecdb427ae27b',
            'Exact V82 frozen source union required')
    frozen = json.loads(raw)
    require(len(frozen['new_sources']) == 871 and len(frozen['protected_auxiliary_sources']) == 5,
            'Complete frozen inventory census required')
    files = {}
    for name, expected in {**frozen['new_sources'], **frozen['protected_auxiliary_sources']}.items():
        path = repo/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and not any(q.is_symlink() for q in (path, *path.parents)), 'Regular relative source required')
        data = path.read_bytes()
        require(info(data) == expected, 'Frozen source changed: '+name)
        files[name] = data
    for version in (83, 85, 86, 87, 88, 89):
        for path in sorted((repo/f'research_v{version}').iterdir()):
            if path.is_file() and path.suffix in ('.py', '.txt', '.sh', '.sbatch', '.c'):
                require(not path.is_symlink(), 'Symbolic source refused')
                files[str(path.relative_to(repo))] = path.read_bytes()
    # Canonical derivative preserves values and binds the original public bytes.
    original = repo/'pilots/continuation-v85-20261023/partial-artifact-bindings.json'
    data = original.read_bytes()
    values = json.loads(data)
    require(len(values['failed_v80_artifacts']) == 104, 'Complete failed artifact census required')
    files['recovery-evidence/partial-artifact-bindings.json'] = canonical_json(values)
    files['recovery-evidence/binding-origin.json'] = canonical_json(dict(source=str(original.relative_to(repo)), **info(data)))
    old_accounting = (repo/'pilots/continuation-v85-20261023/scheduler-accounting.txt').read_bytes()
    files['recovery-evidence/original-accounting.txt'] = old_accounting
    files['recovery-evidence/old-accounting.txt'] = normalized_accounting(old_accounting)
    for name, data in files.items():
        require(Path(name).suffix in ('.py', '.txt', '.sh', '.sbatch', '.c', '.json'), 'Source-only extension required')
        if name.endswith('.py'):
            ast.parse(data)
    count = 0
    for module in SOFTWARE:
        tree = ast.parse(files[module.replace('.', '/')+'.py'])
        count += sum(isinstance(n, ast.FunctionDef) and n.name.startswith('test_') for n in ast.walk(tree))
    require(count == EXPECTED_TESTS, 'Prepared exact Linux test census differs')
    inventory = {n:info(b) for n,b in sorted(files.items())}
    destination = Path(output).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    manifest = canonical_json(inventory)
    (destination/'source-inventory.json').write_bytes(manifest)
    archive = destination/'four-cell-recovery-v89-source-only.tar'
    with archive.open('xb') as stream, tarfile.open(fileobj=stream, mode='w|') as tar:
        for name, data in sorted(dict(files, **{'source-inventory.json':manifest}).items()):
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            entry.mode = 0o600
            tar.addfile(entry, io.BytesIO(data))
    archive_info = info(archive.read_bytes())
    plan = build(inventory, archive_info['bytes'])
    report = dict(status='prepared_locally_not_registered', source_inventory_sha256=info(manifest)['sha256'],
                  source_count=len(inventory), source_bytes=sum(e['bytes'] for e in inventory.values()),
                  archive=archive_info, storage_plan=plan,
                  before_upload_requests=requests(plan, inventory, archive_info['bytes']),
                  before_checks_requests=requests(plan, inventory, archive_info['bytes'], 'checks'),
                  frozen_sources_preserved=871, auxiliary_commitments_preserved=5,
                  expected_linux_tests=EXPECTED_TESTS, actual_linux_gate_executed=False,
                  software_test_count_is_not_a_result=True, uploaded=False, registered=False, launched=False)
    (destination/'preparation.json').write_bytes(canonical_json(report))
    print(json.dumps({k:v for k,v in report.items() if k != 'storage_plan'}, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])
