"""Create a new candidate only from actual target-admission terminal evidence."""
from pathlib import Path
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_v80.io import require,read,json_read,info
from research_v111.config import ROOT,RUN,ADMISSION,PROFILES,design
from research_v111.gate import verify as verify_gate
from research_v111.storage_plan import build,requests
from research_v111.records import writer
from research_v111.software import SUITES
from research_v88.storage import inspect
from src.run_store import canonical_json

def main(inventory_sha,archive_sha):
    require(Path(__file__).resolve()==RUN/'research_v111/prepare.py','Literal fresh matched preparation required')
    require(not (RUN/'program.json').exists() and not (RUN/'registration.json').exists(),'Preparation already consumed')
    from research_v111.dispatch_failure import verify as prior_run
    prior_failure=prior_run(live_scheduler=True)
    sources=json_read(RUN/'inventory.json');inventory=info(canonical_json(sources))
    require(inventory['sha256']==inventory_sha,'Exact inventory commitment required')
    for name,e in sources.items():read(RUN/name,e,maximum=64*2**20,retain=False)
    archive=read(ROOT/'local_runs/matched-complete-recovery-v111-source-only.tar',maximum=64*2**20,retain=False)
    require(archive['sha256']==archive_sha,'Exact staged source archive required')
    plan=build(sources,archive['bytes']);storage=inspect(requests(plan,sources,archive['bytes'],'checks'))
    path=RUN/'gates/target-admission-terminal.json';bound=sources['gates/target-admission-terminal.json']
    gate,admission,close=verify_gate(path,bound)
    targets={profile:{name:dict(path=str(ADMISSION/profile/'outputs'/name),**{k:e[k] for k in ('bytes','sha256')})
        for name,e in close['seal_audit']['models'][profile]['artifacts'].items()} for profile in PROFILES}
    checkpoint_bytes={profile:sum(read(Path(admission['checkpoint_paths'][profile])/name,retain=False)['bytes']
        for name in admission['profiles'][profile]['checkpoint_files']) for profile in PROFILES}
    from research_v111.preparations import bindings
    p=dict(design(),reused_preparations=bindings(),sources=sources,source_count=len(sources),source_inventory=inventory,source_archive=archive,
        storage_plan=plan,target_terminal=dict(path=str(path),**bound),target_gate=gate,admitted_targets=targets,
        checkpoint_paths=admission['checkpoint_paths'],checkpoint_bytes=checkpoint_bytes,
        software_suites={k:dict(modules=v[0],tests=v[1]) for k,v in SUITES.items()},expected_tests=sum(v[1] for v in SUITES.values()),
        prior_complete_failure=prior_failure,scientific_result=False,registration_is_external=True)
    w=writer();w.write('preparation-storage.json',storage);print(w.write('program.json',p))

if __name__=='__main__':main(*sys.argv[1:])
