"""Prepare a new canonical registry only from actually closed upstream evidence.

The source-only package and three actual host terminal snapshots must already be
staged in the new namespace. Does not register or submit jobs. Existing outputs
are never overwritten. Source inventory hash is supplied by the packaging receipt.
"""
import hashlib,json,os,sys
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_v84.config import ROOT,RUN,ADMISSION,ADMISSION_SHA,PROFILES,design
from research_v81.profile import PROFILES as MODEL_PROFILES

def require(x,m):
    if not x:raise ValueError(m)
def info(path):
    p=Path(path);require(p.is_file() and not any(q.is_symlink() for q in (p,*p.parents)),'Regular pinned input required')
    n=0;h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(2**20):h.update(b);n+=len(b)
    return dict(bytes=n,sha256=h.hexdigest())
def bind(path):return dict(path=str(path),**info(path))

def main(inventory_sha):
    require(Path(__file__).resolve()==RUN/'research_v84/prepare.py','Literal new namespace required')
    require(info(RUN/'source-inventory.json')['sha256']==inventory_sha,'Source-only package inventory differs')
    sources=json.loads((RUN/'source-inventory.json').read_bytes())
    for name,e in sources.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Relative source path required');require(info(RUN/name)==e,'Staged source differs')
    require(info(ADMISSION/'program.json')['sha256']==ADMISSION_SHA,'Exact actual admission program required')
    admitted=json.loads((ADMISSION/'program.json').read_bytes());close=json.loads((ADMISSION/'close-completion.json').read_bytes())
    require(close['status']=='complete' and close['error'] is None and close['program_sha256']==ADMISSION_SHA and close['result']['status']=='admitted_pending_host_terminal_accounting','Successful actual admission close required')
    gates={};expected={'v80':'89f6a71e5b4f74b667bac64149c77005862d36b2b2e3dedc2a7260fb05c0ad60','v81':'3f89d3c73c21d9d955c9396d6cfbe8150ad98793088f2cca7c6ba5c88c8e5ada','v82':ADMISSION_SHA}
    for version,sha in expected.items():
        path=RUN/'gates'/(version+'-terminal.json');report=json.loads(path.read_bytes())
        require(report['status']=='verified' and report['kind']==version and report['program_sha256']==sha,'Actual terminal gate differs')
        require(all(x['overlapping_clocks_not_summed'] is True for x in report['costs'].values()),'Actual terminal clock reconciliation required')
        if version=='v80':require(report['evidence']['comparison_count']==8 and report['evidence']['actual_audits_and_inputs_reverified'] is True,'Actual V80 closure required')
        elif version=='v81':require(report['evidence']['actual_software_tests']==62,'Actual V81 software pass required')
        else:
            require(report['evidence']['actual_target_admission'] is True and report['evidence']['empirical_transfer'] is False,'Actual V82 target closure required')
            require(report['inputs'][str(ADMISSION/'close-completion.json')]==info(ADMISSION/'close-completion.json'),'Actual admission close bytes changed')
        gates[version]=bind(path)
    targets={};checkpoint_bytes={}
    for profile in PROFILES:
        q=json.loads((ADMISSION/profile/'outputs/completion.json').read_bytes())
        require(q==close['result']['models'][profile] and q['status']=='complete' and q['grid_allowance']==1327104,'Actual target admission changed')
        targets[profile]={}
        for name,e in q['artifacts'].items():
            path=ADMISSION/profile/'outputs'/name;require(info(path)=={k:e[k] for k in ('bytes','sha256')},'Actual target bytes changed');targets[profile][name]=bind(path)
        checkpoint=Path(admitted['checkpoint_paths'][profile]);total=0
        for name,h in MODEL_PROFILES[profile]['checkpoint_files'].items():
            e=info(checkpoint/name);require(e['sha256']==h,'Actual checkpoint bytes differ');total+=e['bytes']
        checkpoint_bytes[profile]=total
    p=dict(design(),directory=str(RUN),sources=sources,source_count=len(sources),source_inventory_sha256=inventory_sha,
        terminal_gates=gates,admitted_targets=targets,checkpoint_paths=admitted['checkpoint_paths'],checkpoint_bytes=checkpoint_bytes,
        actual_admission_completion=bind(ADMISSION/'close-completion.json'))
    raw=json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    with (RUN/'program.json').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    print(json.dumps(dict(program_sha256=hashlib.sha256(raw).hexdigest(),source_count=len(sources),phase_cpu_seconds=p['phase_cpu_seconds'],registered=False,submitted=False)))
if __name__=='__main__':main(sys.argv[1])
