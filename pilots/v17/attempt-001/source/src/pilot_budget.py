"""Carry the original bounded empirical allowance across later revisions."""
import json
from pathlib import Path
import re


def inherited_allowance(repository):
    root=Path(repository)
    ledgers=[root/'pilots/v10/phase-cpu-budget/ledger.json']
    for directory in (root/'pilots').glob('v*'):
        match=re.fullmatch(r'v([0-9]+)',directory.name)
        if match and int(match[1])>=12:
            ledgers.extend(sorted(directory.glob('*/phase-cpu-budget/ledger.json')))
    charged=0
    for path in ledgers:
        data=json.loads(path.read_bytes())
        for row in data['attempts'].values():
            if row['state']!='settled':raise ValueError('an unsettled empirical worker blocks serial admission')
            value=row['charged_cpu_seconds']
            if type(value) is not int or value<0:raise ValueError('invalid inherited CPU charge')
            charged+=value
    if charged>10800:raise ValueError('inherited empirical allowance already exceeded')
    return charged,10800-charged


def research_worker_lock(repository):
    """Return an exclusive admission context shared across revision launchers."""
    from contextlib import contextmanager
    import fcntl
    @contextmanager
    def locked():
        path=Path(repository)/'pilots/research-worker.lock';path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('a+b') as handle:
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as exc:raise ValueError('another empirical launcher holds the serial admission lock') from exc
            try:yield
            finally:fcntl.flock(handle,fcntl.LOCK_UN)
    return locked()
