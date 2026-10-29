"""Prospective actual-byte state/model audit for each separately bound checkpoint."""
import gc,json
from pathlib import Path
from research_v104.config import CELLS,LOCAL_ORDER,predecessor
from research_v104 import campaign as c
from research_v81 import archive
from research_v81.profile import PROFILES
from research_v81.operations import REPRESENTATIONS,MODERN
from research_v61.state import Record,validate_state,verify_successor
from research_v61.service import trust_read
from research_v61.target import BoundTarget
from research_v61.postrun import model_matches_state
from research_v35.exact_gram import GramBudget
from research_v80.io import require
from src.run_store import canonical_json,digest,strict_json

def execution_matches_target(execution,target,profile):
    fixed=strict_json(target.fixed_payload)
    require(execution['schema']=='full-precision-source-execution-binding-v61'
        and execution['target_sha256']==digest(target.fixed_payload) and execution['anchor_target_sha256']==digest(target.anchor_payload)
        and execution['calibration_target_sha256']==target.calibration_target_sha256,'Actual execution/target binding differs')
    require(digest(canonical_json(execution['decoder']))==fixed['decoder_sha256']
        and digest(canonical_json(execution['implementation']))==fixed['implementation_manifest_sha256']
        and execution['provider_sha256']==fixed['provider_sha256']
        and execution['teacher_stages']==fixed['calibration_target']['teacher_stages']
        and execution['checkpoint']['files_sha256']==PROFILES[profile]['checkpoint_files'],'Original teacher/checkpoint binding differs')

def gram_budget():return GramBudget(max_width=768,max_tokens=512,max_sources=4,max_product_terms=768*769//2*512,max_integer_bits=256,max_serialized_bytes=128*2**20,max_memory_bytes=2*2**30)

def state_view(blob,trust,rep,records,target,budget):
    require(canonical_json(strict_json(trust))==trust,'Canonical trust bytes required');trust=trust_read(strict_json(trust))
    if rep==MODERN:
        require(not trust,'Modern state cannot carry Gram trust');view=archive.unpack(blob)
        require(view.target==target and view.records==records,'Complete modern target/membership differs')
    else:
        view=validate_state(blob,expected_target=target,expected_records=records,gram_trust=trust,gram_budget=budget)
        require(view.representation==rep,'State representation differs')
    return view,trust

def verify_profile(directory,profile,p,completions,inputs):
    root=Path(directory)/profile;rows,prov=c.load_records(p)
    records=tuple(Record(r['id'],tuple(r['tokens']),canonical_json(prov[r['id']])) for r in rows)
    entries=p['admitted_targets'][profile];target=BoundTarget(c.bound(entries['anchor-target.json']),c.bound(entries['service-target.json']))
    budget=gram_budget();expected_stages=p['stage_counts'][profile];expected_codes=p['code_counts'][profile];executions=[]
    for local in LOCAL_ORDER:
        key=profile+'/'+local;e=inputs.json(root/local/'outputs/execution-provenance.json')
        require(digest(canonical_json(e))==completions[key]['execution_provenance_sha256'],'Execution receipt differs')
        executions.append(e)
        require(completions[key]['service_target_sha256']==digest(target.fixed_payload)
            and completions[key]['base_target_sha256']==digest(target.anchor_payload)
            and completions[key]['calibration_target_sha256']==target.calibration_target_sha256,'Actual profile target differs')
    require(all(e==executions[0] for e in executions),'Checkpoint execution differs across cells')
    execution_matches_target(executions[0],target,profile)
    prep=root/'prepare/outputs';original_model=inputs.read(prep/'model.bin');original_sizes={}
    for rep in REPRESENTATIONS:
        blob=inputs.read(prep/(rep+'-state.bin'));trust=inputs.read(prep/(rep+'-trust.json'));view,_=state_view(blob,trust,rep,records,target,budget)
        extent=model_matches_state(view,original_model)
        require(extent['code_count']==expected_codes and extent['stages']==expected_stages,'Complete original profile extent differs')
        require(completions[profile+'/prepare']['preparation']['states'][rep]['live_state_bytes']==len(blob)+len(trust),'Original storage metadata differs')
        if rep==MODERN:require(archive.restore(view)==inputs.read(prep/'lossless-state.bin'),'Original modern restoration differs')
        original_sizes[rep]=dict(state_bytes=len(blob),trust_bytes=len(trust),live_state_bytes=len(blob)+len(trust))
        del blob,trust,view;gc.collect()
    comparisons=[];sizes={cell:[] for cell in CELLS}
    for cell,arm in CELLS.items():
        rep='compressed48' if arm=='compressed' else MODERN
        for step,n in enumerate(p['retained_counts'],1):
            key=profile+'/'+cell+'-'+str(step);out=Path(directory)/key/'outputs';oracle=root/'oracle/outputs'/f'step-{step}'
            prior,pn,tn=predecessor(key);old=Path(directory)/prior/'outputs';before=records[-(4 if step==1 else 3):];after=records[-n:]
            pb=inputs.read(old/pn);pt=inputs.read(old/tn);cb=inputs.read(out/'state.bin');ct=inputs.read(out/'trust.json');fb=inputs.read(oracle/(rep+'-state.bin'));ft=inputs.read(oracle/(rep+'-trust.json'))
            pv,ptrust=state_view(pb,pt,rep,before,target,budget);cv,ctrust=state_view(cb,ct,rep,after,target,budget);fv,ftrust=state_view(fb,ft,rep,after,target,budget)
            require(cb==fb and ct==ft,'Actual complete state/trust differs from fresh retained-teacher reconstruction')
            kept={r.record_id for r in after};deleted=[r.record_id for r in before if r.record_id not in kept]
            require(cv.source_map()=={k:v for k,v in pv.source_map().items() if k[1] in kept},'Retained source bytes changed')
            if rep==MODERN:
                require(archive.restore(cv)==inputs.read(oracle/'lossless-state.bin'),'Successor modern restoration differs')
            else:verify_successor(pb,cb,fb,deleted,previous_gram_trust=ptrust,candidate_gram_trust=ctrust,fresh_gram_trust=ftrust,gram_budget=budget)
            model=inputs.read(out/'model.bin');fresh=inputs.read(oracle/'model.bin');require(model==fresh,'Actual complete model differs from same-checkpoint fresh oracle')
            extent=model_matches_state(cv,model);model_matches_state(fv,fresh);model_matches_state(pv,inputs.read(old/'model.bin'))
            require(extent['stages']==expected_stages and extent['code_count']==expected_codes,'Successor complete extent differs')
            request=completions[key]['request'];freshmeta=completions[profile+'/oracle']['steps'][step-1]
            require(request['arm']==arm and request['representation']==rep and request['retained_ids']==[r.record_id for r in after] and request['deleted_ids']==deleted,'Request operation/membership differs')
            require(freshmeta['retained_ids']==request['retained_ids'] and freshmeta['prior_state_read'] is False and freshmeta['independent_retained_token_traversal'] is True
                and freshmeta['common_timing']['neural_stage_record_pairs']==expected_stages*n,'Complete independent retained traversal required')
            require(request['live_state_bytes']==len(cb)+len(ct),'Successor storage metadata differs')
            sizes[cell].append(dict(state_bytes=len(cb),trust_bytes=len(ct),live_state_bytes=len(cb)+len(ct),checkpoint_inclusive_bytes=len(cb)+len(ct)+p['checkpoint_bytes'][profile]))
            comparisons.append(dict(profile=profile,cell=cell,step=step,actual_model_bytes_equal=True,actual_state_bytes_equal=True,actual_trust_bytes_equal=True,independent_retained_traversal=True,**extent))
            del pb,pt,cb,ct,fb,ft,pv,cv,fv,model,fresh;gc.collect()
    return dict(profile=profile,target_sha256=digest(target.fixed_payload),comparisons=comparisons,storage=sizes,original_storage=original_sizes)
