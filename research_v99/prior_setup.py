"""Preserve the failed pre-registration V91 namespace as immutable evidence."""
from pathlib import Path
from research_v80.io import read, require
from src.run_store import strict_json

ROOT = Path('/nfs_home/users/poonam/second-20261010/local_runs')
PRIOR = ROOT / 'matched-transfer-admission-v91-20261024-a'
ARCHIVE = dict(bytes=11550720, sha256='4aee02bcf7c18e4c649b2a74b8bd9e926f00ea6f4c3e352a9039a7e77a437426')
INVENTORY = dict(bytes=122566, sha256='5755a6c68ab47a367786821ba140e9711364b84680a86685920f4f36a1823a32')


def verify():
    read(ROOT / 'matched-transfer-admission-v91-source-only.tar', ARCHIVE, maximum=64*2**20, retain=False)
    inventory = strict_json(read(PRIOR / 'inventory.json', INVENTORY, maximum=64*2**20))
    require(len(inventory) == 991, 'Preserved setup inventory differs')
    for name, entry in inventory.items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'Invalid old member')
        read(PRIOR / name, entry, maximum=64*2**20, retain=False)
    actual = {str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()}
    require(actual == set(inventory) | {'inventory.json'}, 'Failed old setup changed or was retried')
    require(not any((PRIOR / n).exists() for n in ('program.json', 'registration.json', 'budget', 'checkpoint')),
            'Old pre-registration failure was reused')
    return dict(status='preserved_pre_registration_setup_failure', source_count=991,
                archive=ARCHIVE, inventory=INVENTORY, old_job_launched=False)
