"""One-use registration preparation after actual preserved failure inspection."""
from pathlib import Path
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_v80.io import require,read,json_read,info
from research_v110.config import ROOT,RUN,PARENT,PARENT_SHA,design
from research_v110.storage_plan import build,requests
from research_v110.records import writer
from research_v110.software import SUITES
from research_v88.storage import inspect
from src.run_store import canonical_json


def main(inventory_sha,archive_sha):
    require(Path(__file__).resolve()==RUN/'research_v110/prepare.py','Literal new preparation required')
    require(not (RUN/'program.json').exists() and not (RUN/'registration.json').exists(),'Preparation consumed')
    from research_v110.dispatch_failure import verify
    prior=verify(live_scheduler=True)
    from research_v104 import campaign as parent
    p=parent.verify(prerequisite=False);require(parent.sha(PARENT/'program.json')==PARENT_SHA,'Parent changed')
    sources=json_read(RUN/'inventory.json');inventory=info(canonical_json(sources))
    require(inventory['sha256']==inventory_sha,'Exact new inventory required')
    for name,e in sources.items():read(RUN/name,e,maximum=64*2**20,retain=False)
    archive=read(ROOT/'local_runs/token-stage-diagnostic-v110-source-only.tar',maximum=64*2**20,retain=False)
    require(archive['sha256']==archive_sha,'Exact new archive required')
    plan=build(sources,archive['bytes']);storage=inspect(requests(plan,sources,archive['bytes'],'checks'))
    program=dict(design(),sources=sources,source_count=len(sources),source_inventory=inventory,source_archive=archive,
        storage_plan=plan,prior_complete_failure=prior,checkpoint_path=p['checkpoint_paths']['gpt2'],
        admitted_target=p['admitted_targets']['gpt2'],
        software_suites={k:dict(modules=v[0],tests=v[1]) for k,v in SUITES.items()},
        expected_tests=sum(v[1] for v in SUITES.values()))
    w=writer();w.write('preparation-storage.json',storage);print(w.write('program.json',program))


if __name__=='__main__':main(*sys.argv[1:])
