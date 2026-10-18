"""Verify current and failed-campaign sources against their actual registrations."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
ROOT=Path('/nfs_home/users/poonam/second-20261010')
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def local(name):
    p=Path(name)
    if not p.is_absolute():return 'validation/'+name
    parts=p.relative_to(ROOT).parts
    if parts[0]=='local_runs':parts=parts[2:]
    if len(parts)==1:return 'validation/'+parts[0]
    return str(Path(*parts))
def check():
    numerical={};admin={};registrations={}
    groups={'v70_frame':['frozen_sources','new_sources'],'v71_quality':['new_sources'],
            'v68':['administrative_sources'],'v69_runtime':['new_sources']}
    for version,keys in groups.items():
        raw=(R/f'handoff/registration_{version}.json').read_bytes();p=json.loads(raw)
        registrations[version]=info(raw)
        for key in keys:
            for name,e in p[key].items():
                rel=local(name);target=admin if rel.startswith('validation/') else numerical
                if version=='v69_runtime':
                    actual=info((R/rel).read_bytes());assert actual['sha256']==e,rel
                    e=actual # This older administrative registration stores a digest only.
                assert rel not in target or target[rel]==e
                target[rel]=e;assert info((R/rel).read_bytes())==e,rel
    assert len(numerical)==575 and len(admin)==5
    # Reconcile the older failed campaign directly, not only through V70's inventory.
    for version,keys in {'v67':['prior_sources','new_sources'],'v68':['frozen_sources','new_sources'],
                         'v69_quality':['new_sources']}.items():
        raw=(R/f'handoff/registration_{version}.json').read_bytes();p=json.loads(raw)
        registrations[version]=info(raw)
        for key in keys:
            for name,e in p[key].items():assert numerical[local(name)]==e
    return dict(status='all_registered_source_bytes_match',numerical_source_count=575,
        auxiliary_source_count=5,numerical_sources=numerical,auxiliary_sources=admin,
        registrations=registrations,failed_v69_sources_preserved=True)
if __name__=='__main__':
    result=check();(R/'validation/v71_frozen_source_check.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['numerical_sources','auxiliary_sources','registrations']}))
