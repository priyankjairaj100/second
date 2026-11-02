"""One-shot, read-only V112 closure and bounded metadata retrieval.

Invoke only when all registered jobs have terminated successfully. This program
does not submit, cancel, resume, retry, or change any cluster job or source.
Connection/verification failure stops the invocation and preserves its receipt.
"""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_v112.config import RUN, OPERATIONS, CELLS, PROFILES, name
from research_v83.accounting import scheduler_rows
from reporting_v113.reduce import main as reduce_saved, historical_hosts

EXPECTED = 'a73ca66d08b50feeccf9601d6d214b00ad21917ae900671cc35d373aef4f4381'
JOBS = {op: dict(job_id=str(16407+i), name='second112-'+name(op))
        for i, op in enumerate(OPERATIONS)}
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
       '-o', 'ConnectionAttempts=1', '-o', 'PubkeyAuthentication=no', 'csis']
MAX_FILE = 16*2**20
MAX_TOTAL = 32*2**20


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(blob):
    return dict(bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())


def receipt_names():
    names = ['program.json', 'primary-audit.json', 'supplemental-audit.json', 'gates/v104-failed-screen-v110.json']
    for profile in PROFILES:
        for cell in CELLS:
            for step in (1, 2):
                op = f'{profile}/{cell}-{step}'
                names.extend([op+'/outputs/completion.json', name(op)+'-host.json'])
    return names


def validate_terminal(report):
    require(report['schema'] == 'matched-complete-terminal-v112'
            and report['status'] == 'verified'
            and report['program_sha256'] == EXPECTED
            and report['jobs'] == JOBS,
            'Exact successful V112 terminal and complete job identities required')
    scheduler_rows(report['scheduler_raw'], JOBS)
    result = {relative: report['inputs'][str(RUN/relative)] for relative in receipt_names()}
    require(all(type(e['bytes']) is int and 0 < e['bytes'] <= MAX_FILE
                and len(e['sha256']) == 64 for e in result.values())
            and sum(e['bytes'] for e in result.values()) <= MAX_TOTAL,
            'Reporting metadata exceeds its transfer bound')
    require(result['program.json']['sha256'] == EXPECTED, 'Terminal program binding differs')
    return result


def decode_payload(payload, wanted):
    require(set(payload) == set(wanted), 'Exact reporting file census required')
    decoded = {}
    for relative, expected in wanted.items():
        text = payload[relative]
        require(type(text) is str and len(text) <= 4*((expected['bytes']+2)//3),
                'Encoded file exceeds its declared size')
        blob = base64.b64decode(text, validate=True)
        require(identity(blob) == expected, 'Unbound or changed reporting receipt: '+relative)
        decoded[relative] = blob
    return decoded


def remote(code, destination, phase, timeout):
    command = SSH + ['python3 -B -c '+shlex.quote(code)]
    (destination/(phase+'-intent.json')).write_text(json.dumps(dict(
        command=command, created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        read_only=True, automatic_retry=False), sort_keys=True)+'\n')
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        (destination/(phase+'-stdout.incomplete')).write_bytes(error.stdout or b'')
        (destination/(phase+'-stderr.incomplete')).write_bytes(error.stderr or b'')
        raise
    (destination/(phase+'-stdout.json')).write_bytes(result.stdout)
    (destination/(phase+'-stderr.txt')).write_bytes(result.stderr)
    require(result.returncode == 0, 'Remote read failed; inspect receipt and stop, no retry')
    require(len(result.stdout) <= 2*MAX_TOTAL, 'Unexpectedly large remote response')
    return result.stdout


def main(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    # Refuse unfinished/failed jobs before invoking the frozen bulk terminal audit.
    code = f'''import sys,subprocess,hashlib,json
from pathlib import Path
run=Path({str(RUN)!r});sys.path.insert(0,str(run))
from research_v83.accounting import scheduler_rows
jobs={JOBS!r}
raw=subprocess.check_output(['sacct','-nP','-j',','.join(r['job_id'] for r in jobs.values()),'--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=20)
scheduler_rows(raw,jobs)
assert hashlib.sha256((run/'program.json').read_bytes()).hexdigest()=={EXPECTED!r}
subprocess.run(['python3','-B',str(run/'research_v112/terminal.py'),{EXPECTED!r}],check=True,timeout=330)
'''
    raw = remote(code, destination, 'terminal', 360)
    terminal = json.loads(raw)
    wanted = validate_terminal(terminal)
    code = f'''import json,base64,hashlib
from pathlib import Path
run=Path({str(RUN)!r});wanted={wanted!r};result={{}};total=0
for relative,expected in wanted.items():
 path=run/relative
 assert not path.is_symlink() and path.is_file() and path.stat().st_size==expected['bytes']<={MAX_FILE}
 blob=path.read_bytes();total+=len(blob)
 assert total<={MAX_TOTAL} and len(blob)==expected['bytes'] and hashlib.sha256(blob).hexdigest()==expected['sha256']
 result[relative]=base64.b64encode(blob).decode('ascii')
print(json.dumps(result,sort_keys=True))
'''
    data = decode_payload(json.loads(remote(code, destination, 'metadata', 90)), wanted)
    gate=json.loads(data['gates/v104-failed-screen-v110.json'])
    historical=historical_hosts(gate)
    code=f'''import json,base64,hashlib
from pathlib import Path
wanted={historical!r};result={{}}
for relative,entry in wanted.items():
 path=Path(entry['path']);expected={{k:entry[k] for k in ('bytes','sha256')}}
 assert not any(p.is_symlink() for p in (path,*path.parents)) and path.is_file() and path.stat().st_size==expected['bytes']<={MAX_FILE}
 blob=path.read_bytes();assert len(blob)==expected['bytes'] and hashlib.sha256(blob).hexdigest()==expected['sha256']
 result[relative]=base64.b64encode(blob).decode('ascii')
print(json.dumps(result,sort_keys=True))
'''
    expected={n:{k:e[k] for k in ('bytes','sha256')} for n,e in historical.items()}
    data.update(decode_payload(json.loads(remote(code,destination,'historical-preparation',90)),expected))
    wanted.update({n:dict(path=e['path'],**expected[n]) for n,e in historical.items()})
    require(sum(map(len,data.values()))<=MAX_TOTAL,'All reporting metadata exceeds transfer bound')
    base = destination/'receipts'
    for relative, blob in data.items():
        path = base/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(blob)
    (destination/'retrieval.json').write_text(json.dumps(dict(
        status='verified_terminal_bound_metadata', files=wanted, total_bytes=sum(map(len, data.values())),
        source_program_sha256=EXPECTED, raw_model_or_corpus_downloaded=False,
        independent_binary_reaudit=False), sort_keys=True, indent=2)+'\n')
    reduce_saved(destination/'terminal-stdout.json', base, destination/'reduction.json')


if __name__ == '__main__':
    main(sys.argv[1])
