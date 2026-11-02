"""Create a candidate registry only after reopening the real V89 terminal gate."""
from pathlib import Path
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_v80.io import read,json_read,require,info
from research_v90.recovery_gate import verify as verify_recovery
from research_v99.config import ROOT,RUN,design
from research_v99.storage_plan import build,requests
from research_v99.records import writer
from research_v99.software import SUITES
from research_v88.storage import inspect
from src.run_store import canonical_json
from research_v99.prior_setup import verify as verify_prior_setup


def main(inventory_sha,archive_sha):
    require(Path(__file__).resolve()==RUN/'research_v99/prepare.py','Literal new admission preparation required')
    require(not (RUN/'program.json').exists() and not (RUN/'registration.json').exists(),'Preparation already consumed')
    prior_setup=verify_prior_setup()
    sources=json_read(RUN/'inventory.json');inventory=info(canonical_json(sources))
    require(inventory['sha256']==inventory_sha,'Inventory commitment differs')
    for name,entry in sources.items():read(RUN/name,entry,maximum=64*2**20,retain=False)
    archive=read(ROOT/'local_runs/matched-transfer-admission-v99-source-only.tar',maximum=64*2**20,retain=False)
    require(archive['sha256']==archive_sha,'Exact staged source archive required')
    plan=build(sources,archive['bytes']);storage=inspect(requests(plan,sources,archive['bytes'],'checks'))
    bound=sources['gates/v89-terminal.json'];path=RUN/'gates/v89-terminal.json'
    recovery=verify_recovery(path,bound)
    p=design();p.update(sources=sources,source_count=len(sources),source_inventory=inventory,source_archive=archive,
        storage_plan=plan,recovery_terminal=dict(path=str(path),**bound),recovery_gate=recovery,
        software_suites={k:dict(modules=v[0],tests=v[1]) for k,v in SUITES.items()},
        expected_software_tests=sum(v[1] for v in SUITES.values()),
        prior_setup_failure=prior_setup,registration_is_external=True,scientific_result=False)
    w=writer();w.write('preparation-storage.json',storage)
    receipt=w.write('program.json',p);print(receipt)

if __name__=='__main__':main(*sys.argv[1:])
