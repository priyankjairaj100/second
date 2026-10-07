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
