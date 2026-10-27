"""Read-only reuse of separately sealed complete V104 preparations.

Preparation bytes are reopened in the full binary audit. Request timing includes
reading the predecessor it uses, while preparation CPU remains historical cost.
"""
from research_v111.config import PARENT,PARENT_SHA,PROFILES
from research_v80.io import require,json_read,read,info
from research_v83.terminal import actual_seal
from src.run_store import canonical_json


def bindings():
    result={}
    for profile in PROFILES:
        root=PARENT/profile/'prepare';path=root/'outputs/completion.json'
        completion=json_read(path)
        require(completion['status']=='complete' and completion['complete_model'] is True
            and completion['program_sha256']==PARENT_SHA and completion['trial']==profile+'/prepare',
            'Original complete preparation required')
        result[profile]=dict(path=str(path),**info(canonical_json(completion)))
    return result


def completions(program,inputs):
    require(program['reused_preparations']==bindings(),'Original preparation bindings changed')
    result={}
    for profile,e in program['reused_preparations'].items():
        root=PARENT/profile/'prepare';q=inputs.json(e['path'])
        require(inputs.files[e['path']]=={k:e[k] for k in ('bytes','sha256')},'Preparation completion changed')
        seal=actual_seal(inputs,root/'worker')
        require(seal['outcome']['status']=='complete' and seal['outcome']['returncode']==0
            and seal['budget_debit']['state']=='settled' and seal['budget_reservation_overrun'] is False,
            'Actual complete original preparation seal required')
        for name,entry in q['artifacts'].items():
            require(inputs.read(root/'outputs'/name,retain=False)=={k:entry[k] for k in ('bytes','sha256')},
                'Original preparation artifact changed')
        result[profile+'/prepare']=q
    return result
