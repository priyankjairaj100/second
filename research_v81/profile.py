"""Exact prospective profile guards; no checkpoint loading or numerical run."""
import json
from pathlib import Path

PROFILES=json.loads(Path(__file__).with_name('profiles.json').read_text())
SHAPES=((2304,768),(768,768),(3072,768),(768,3072))
KINDS=('qkv','attn_out','mlp_up','mlp_down')
NORMALIZATION=512
CURRENT_GRID_CAP=1_000_000
PROPOSED_GRID_CAP=1_327_104

def require(ok,message):
    if not ok:raise ValueError(message)

def validate_geometry(base,profile=None):
    require(type(base) is dict and type(base.get('stages')) is list,'Bounded stage manifest required')
    stages=base['stages']
    choices={4*v['blocks']:k for k,v in PROFILES.items()}
    require(len(stages) in choices,'Only complete six/twelve-block profiles allowed')
    chosen=choices[len(stages)]
    require(profile is None or chosen==profile,'Checkpoint profile and depth differ')
    recipe=base['recipe']
    require(recipe['original_token_count']==NORMALIZATION and recipe['bits']==4 and recipe['ridge']==[1,100],'Fixed matched-root recipe required')
    for index,stage in enumerate(stages):
        block,kind=divmod(index,4)
        require(stage['stage_id']==f'block.{block:04d}.{KINDS[kind]}'
            and stage['shape']==list(SHAPES[kind]) and stage['normalization']==[NORMALIZATION,1]
            and stage['ridge']==[1,100] and stage['grid_axis']=='output_row'
            and stage['significant_bits']==24,'Complete ordered stage geometry/recipe differs')
    count=sum(s['shape'][0] for s in stages)*16
    require(type(recipe.get('max_grid_entries')) is int and count<=recipe['max_grid_entries']<=PROPOSED_GRID_CAP,'Complete row grids exceed registered bound')
    return chosen

def validate_records(records):
    require(0<len(records)<=4 and len({r.record_id for r in records})==len(records),'Four-source extent required')
    require(all(len(r.tokens)==128 and all(type(t) is int and 0<=t<50257 for t in r.tokens) for r in records),'128 GPT2-vocabulary tokens per source required')
