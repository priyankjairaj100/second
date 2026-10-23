"""Bind a preregistered upstream gate after it completes, without guessing its result."""
import hashlib,json
from pathlib import Path
V81_RUN=Path('/nfs_home/users/poonam/second-20261010/local_runs/transfer-software-v81-20261023-a')
V81_SHA='3f89d3c73c21d9d955c9396d6cfbe8150ad98793088f2cca7c6ba5c88c8e5ada'
COUNTS={'legacy':44,'four_cell_integration':5,'profiles':4,'full_geometry_archives':5,'service_guards':4}

def require(x,m):
    if not x:raise ValueError(m)

def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def validate_payloads(completion,report):
    q=json.loads(completion);r=json.loads(report)
    require(q['status']=='complete' and q['error'] is None and q['program_sha256']==V81_SHA and q['job_id']=='15917'
        and q['hostname']=='csis.mn1' and q['empirical_execution'] is False,'Completed registered V81 software required')
    require(q['outputs']['outputs/transfer-results.json']==info(report),'V81 result bytes differ from completion')
    require(all(type(q[k]) is int and q[k]>=0 for k in ('aggregate_cpu_ns','process_cpu_ns','waited_child_cpu_ns')),'Invalid upstream CPU accounting')
    require(q['aggregate_cpu_ns']==q['process_cpu_ns']+q['waited_child_cpu_ns']<=602*10**9,'V81 aggregate CPU differs')
    require(r['suites']=={k:dict(tests=n,failures=0,errors=0,skipped=0) for k,n in COUNTS.items()} and r['empirical_execution'] is False,'V81 exact-count gate differs')
    return dict(schema='admitted-upstream-software-v82',program_sha256=V81_SHA,job_id='15917',completion=info(completion),report=info(report),test_count=62)

def verify(run,*,bind=False):
    from research_v80.io import read,write,json_read
    require(info(read(V81_RUN/'program.json'))['sha256']==V81_SHA,'Upstream program identity differs')
    p=json.loads(read(V81_RUN/'program.json'))
    for name,e in p['sources'].items():read(V81_RUN/name,e,retain=False)
    completion=read(V81_RUN/'completion.json');q=json.loads(completion)
    report=read(V81_RUN/'outputs/transfer-results.json',q['outputs']['outputs/transfer-results.json'])
    binding=validate_payloads(completion,report);destination=Path(run)/'v81-admitted.json'
    if bind:write(destination,binding)
    else:require(json_read(destination)==binding,'Upstream receipt changed after software admission')
    return binding
