"""Original scalar arithmetic with an explicit separately recovered cost gate."""
from pathlib import Path
import json,sys
from validation.check_v71_campaign_metadata import load as metadata_load
from validation.check_v71_completed_losses import load,check,info
from validation.check_v72_recovery import check as check_recovery,REG72
R=Path(__file__).resolve().parents[1]
def main():
    original=metadata_load(R/'campaigns'/sys.argv[1]);recovery=metadata_load(R/'campaigns'/sys.argv[2])
    recovered=check_recovery(original,recovery)
    assert recovered['recovered_quality_evidence_verified'] is True and recovered['original_campaign_successful'] is False
    path=R/'campaigns'/sys.argv[3];files=load(path);collection=json.loads(files['collection.json'])
    assert collection['recovery_registration_sha256']==REG72 and collection['recovery_receipt']==info(recovery['receipt.json'])
    assert collection['original_closure_successful'] is False
    result=check(files,original)
    result.update(schema='v72-recovered-saved-loss-arithmetic',original_closure_failed=True,
        separate_recovery_verified=True,recovery_registration_sha256=REG72,archive=info(path.read_bytes()),
        original_archive=info((R/'campaigns'/sys.argv[1]).read_bytes()),recovery_archive=info((R/'campaigns'/sys.argv[2]).read_bytes()))
    with (R/'validation'/sys.argv[4]).open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
