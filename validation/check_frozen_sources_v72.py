"""Verify old freezes and the separately registered accounting-recovery sources."""
from pathlib import Path
import json
from validation.check_frozen_sources_v71 import check as old,local,info,R

def check():
    result=old();p=R/'handoff/registration_v72_accounting.json';raw=p.read_bytes();reg=json.loads(raw)
    all_old=dict(result['numerical_sources'],**result['auxiliary_sources'])
    for remote,e in reg['frozen_sources'].items():
        name=local(remote);assert all_old[name]==e and info((R/name).read_bytes())==e,name
    new={local(n):e for n,e in reg['new_sources'].items()}
    assert len(new)==6 and all(n.startswith('research_v72/') for n in new)
    for name,e in new.items():assert name not in all_old and info((R/name).read_bytes())==e,name
    result['numerical_sources'].update(new)
    result.update(numerical_source_count=581,auxiliary_source_count=5,new_recovery_source_count=6,
        historical_source_freezes_preserved=True,separate_recovery_registration=info(raw))
    result['registrations']['v72_accounting']=info(raw)
    return result
if __name__=='__main__':
    r=check()
    with (R/'validation/v72_frozen_source_check.json').open('x') as f:json.dump(r,f,sort_keys=True,indent=2);f.write('\n')
    print({k:v for k,v in r.items() if k not in ['numerical_sources','auxiliary_sources','registrations']})
