"""Recheck immutable failed evidence; never settle or mutate its ledger."""
from pathlib import Path
from research_v80.io import read, json_read, require
from research_v86.admission import carry_forward, terminal_disposition, OLD_PROGRAM
from research_v89.config import ROOT

OLD_RUN = ROOT/'local_runs/four-cell-service-v80-20261023-a'
OLD_LEDGER = dict(bytes=15987, sha256='10f95f5eea81d1bb07a92412ef4b4fe2e802060eb4251524f9559837ceabcb27')


def verify_failure_bindings(program):
    f = program['failed_predecessor']
    require(set(f) == {'program_sha256', 'ledger', 'artifacts', 'accounting', 'carry_forward'},
            'Complete failure binding required')
    require(f['program_sha256'] == OLD_PROGRAM and f['ledger'] == dict(path=str(OLD_RUN/'budget/ledger.json'), **OLD_LEDGER),
            'Original failed registration and reserved debit must remain exact')
    read(f['ledger']['path'], OLD_LEDGER, retain=False)
    require(carry_forward(json_read(f['ledger']['path'])) == f['carry_forward'],
            'Old full reservation changed')
    require(type(f['artifacts']) is dict and len(f['artifacts']) == 104,
            'All 104 preserved partial artifact bindings required')
    for name, expected in f['artifacts'].items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'Relative failed artifact path required')
        read(OLD_RUN/path, expected, retain=False)
    require((OLD_RUN/'prepare/outputs/completion.json').stat().st_size == 0,
            'Failed empty completion changed; do not infer successful model')
    accounting = f['accounting']
    terminal_disposition(read(accounting['path'], {k:accounting[k] for k in ('bytes', 'sha256')}).decode())
    return f['carry_forward']
