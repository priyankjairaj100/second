"""Collect only registered selection/hash metadata, never corpus/token bodies."""
from pathlib import Path
import datetime
import hashlib
import io
import json
import resource
import signal
import sys
import tarfile

resource.setrlimit(resource.RLIMIT_CPU, (30, 31))
resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))
signal.alarm(60)
ROOT = Path('/nfs_home/users/poonam/second-20261010')
RUN = ROOT / 'local_runs/untouched-quality-v71-20261018-a'
REG = '3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
NAMES = {'registration', 'checks', 'data', 'audit', 'selection', 'inventory',
         'before', 'after', 'acquisition', 'frame_audit'}


def info(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read(path):
    assert path.is_relative_to(ROOT) and path.is_file()
    assert not any(p.is_symlink() for p in (path, *path.parents))
    before = path.stat()
    assert before.st_size <= 8 * 2**20
    raw = path.read_bytes()
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns, before.st_ino) == (
        after.st_size, after.st_mtime_ns, after.st_ino)
    return raw


def no_raw_bodies(value):
    if isinstance(value, dict):
        for key, item in value.items():
            assert not (key == 'tokens' and isinstance(item, list))
            assert not (key in {'text', 'body', 'normalized_text'} and isinstance(item, str))
            no_raw_bodies(item)
    elif isinstance(value, list):
        for item in value:
            no_raw_bodies(item)


raw = read(RUN / 'program.json')
assert info(raw)['sha256'] == REG
program = json.loads(raw)
assert set(program['inputs']['quality']) == NAMES | {'records'}
files = {'registration-v71.json': raw}
roles = {}
for name in sorted(NAMES):
    commitment = program['inputs']['quality'][name]
    content = read(Path(commitment['path']))
    assert info(content) == {k: commitment[k] for k in ('bytes', 'sha256')}
    no_raw_bodies(json.loads(content))
    files[name + '.json'] = content
    roles[name + '.json'] = commitment

data_registration = json.loads(files['registration.json'])
commitment = data_registration['inputs']['quality_exclusions']
content = read(Path(commitment['path']))
assert info(content) == {k: commitment[k] for k in ('bytes', 'sha256')}
no_raw_bodies(json.loads(content))
files['historical-quality-exclusions.json'] = content
roles['historical-quality-exclusions.json'] = commitment
assert len(files) == 12 and sum(map(len, files.values())) <= 16 * 2**20
observation = {
    'schema': 'v71-selection-metadata-observation',
    'captured_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'registration_sha256': REG,
    'collector_sha256': info(Path(__file__).read_bytes())['sha256'],
    'roles': roles, 'files': {n: info(b) for n, b in sorted(files.items())},
    'raw_corpus_or_token_bodies_collected': False,
    'model_or_checkpoint_binaries_read': False, 'model_inference': False,
    'job_submitted': False, 'selected_records_body_read': False,
    'scope': 'Frozen selection, exclusion hashes and receipt metadata only. '
             'No prefix read, retokenization, likelihood or reconstruction.',
}
files['collection.json'] = (json.dumps(observation, sort_keys=True, indent=2) + '\n').encode()
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as archive:
    for name, content in sorted(files.items()):
        entry = tarfile.TarInfo(name)
        entry.mode = 0o600
        entry.size = len(content)
        archive.addfile(entry, io.BytesIO(content))
