"""Preserve the unregistered V109 host preparation failure and staged bytes."""
from pathlib import Path
from research_v80.io import require,read,json_read
from research_v110.config import ROOT


def verify():
    prior=ROOT/'local_runs/token-stage-diagnostic-v109-20261026-a'
    archive=ROOT/'local_runs/token-stage-diagnostic-v109-source-only.tar'
    a=read(archive,maximum=64*2**20,retain=False)
    require(a==dict(bytes=13445120,sha256='e305f782fced1853c00d42d5504c1bcbad5ce8ac520a51f8d7e18b56315324c0'),
        'Original V109 archive changed')
    manifest=read(prior/'inventory.json',maximum=2**20,retain=False)
    require(manifest==dict(bytes=149603,sha256='622405b5a86022448bd64f7783b0894272e7f3760ee7235a230f4075dab84639'),
        'Original V109 inventory changed')
    inventory=json_read(prior/'inventory.json');require(len(inventory)==1216,'Original V109 census differs')
    for n,e in inventory.items():read(prior/n,e,maximum=64*2**20,retain=False)
    require({str(p.relative_to(prior)) for p in prior.rglob('*') if p.is_file()}==set(inventory)|{'inventory.json'},
        'V109 acquired unexpected program, registry, job or worker records; inspect')
    return dict(status='preserved_unregistered_host_preparation_failure',archive=a,inventory=manifest,
        numerical_work=False,registered=False,original_files=1217,setup_cost_outside_registered_experiment=True)
