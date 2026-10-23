"""Deterministic development-source selection before any transfer result."""
import hashlib,json
SEED='second-matched-depth-transfer-v82:'

def require(x,m):
    if not x:raise ValueError(m)

def select(records,provenance):
    require(type(records) is list and len(records)==13,'Original thirteen-row V65 root required')
    require(records==sorted(records,key=lambda r:r['id']) and len({r['id'] for r in records})==13,'Original ID order/census differs')
    require(set(provenance)=={r['id'] for r in records},'Complete original provenance required')
    require(all(set(r)=={'id','tokens'} and type(r['id']) is str and type(r['tokens']) is list
        and len(r['tokens'])==128 and all(type(t) is int and 0<=t<50257 for t in r['tokens']) for r in records),'Source shape/vocabulary differs')
    rank=sorted(records,key=lambda r:(hashlib.sha256((SEED+r['id']).encode()).hexdigest(),r['id']))
    chosen=sorted(rank[:4],key=lambda r:r['id'])
    # No new feature or quality measurement is used to rank sources.
    payload=dict(schema='matched-depth-development-selection-v82',seed=SEED,
        all_root_ids=[r['id'] for r in records],hash_ranked_ids=[r['id'] for r in rank],
        selected_ids=[r['id'] for r in chosen],excluded_from_this_workload=[r['id'] for r in records if r not in chosen],
        retained_ids=[[r['id'] for r in chosen[-n:]] for n in (3,2)],normalization=512,
        root_tokens=512,retained_tokens=[384,256],confirmation=False,
        source_status='Previously exposed V65 development rows; preserve all historical exclusions')
    return chosen,{r['id']:provenance[r['id']] for r in chosen},payload
