"""Pure census and budget checks on saved actual-stage admission reports."""
from research_v82.prerequisite import require
from research_v81.profile import PROFILES
REPRESENTATIONS=('lossless','compressed48','hybrid_gram','modern_lossless')
POLICY=dict(max_process_bytes=16*2**30,max_array_bytes=8*2**30,max_stage_work_units=64_000_000_000,
    max_request_work_units=1_000_000_000_000,max_point_refinement_coordinates=16,max_box_preconditioned_coordinates=16,max_box_rounds=4)

def verify_reports(payload,profile,stage_ids,target_sha):
    reports=payload['reports'];count=4*PROFILES[profile]['blocks']
    require(len(stage_ids)==count and len(reports)==12,'Complete admission census required')
    require([(x['retained'],x['representation']) for x in reports]==[(n,r) for n in (4,3,2) for r in REPRESENTATIONS],'Admission profile/order differs')
    points={}
    for report in reports:
        n,rep=report['retained'],report['representation'];stages=report['stages']
        require(len(stages)==count and [s['stage_id'] for s in stages]==stage_ids,'Actual admission stage census differs')
        require(report['resident_reservation_bytes']==9*2**30 and report['process_address_space_cap']==16*2**30
            and report['replay_all_ancestors_reserved'] is True,'Actual admission resource/access policy differs')
        require(report['maximum_fallback_neural_stage_record_pairs']==(count*n if rep=='compressed48' else 0),'Full fallback census differs')
        total=0
        for s in stages:
            kind='box' if rep=='compressed48' else 'gram' if rep=='hybrid_gram' and s['width']<=768 else 'point'
            require(s['admitted'] is True and s['policy']==POLICY and s['kind']==kind and s['target_sha256']==target_sha
                and s['total_tokens']==128*n and s['block_tokens']==128 and s['max_blocks']==n
                and s['resident_bytes']==9*2**30 and s['whole_process_fit_guaranteed'] is False,'Actual stage admission differs')
            selected=s['candidates'][s['selected_route']]
            require(selected['admitted'] is True and selected['complete_rows_and_bounded_fallback_reserved'] is True
                and selected['work_units']==s['work_units']<=POLICY['max_stage_work_units']
                and selected['explicit_array_bytes']==s['explicit_array_bytes']<=POLICY['max_array_bytes']
                and selected['process_known_bytes']==9*2**30+s['explicit_array_bytes']<=POLICY['max_process_bytes'],'Selected stage budgets differ')
            require(type(s['work_units']) is int and s['work_units']>=0 and type(s['explicit_array_bytes']) is int and s['explicit_array_bytes']>=0,'Invalid stage counts')
            total+=s['work_units']
        if rep=='lossless':points[n]=total
        if rep=='compressed48':total+=points[n]
        require(report['reserved_work_units']==total<=POLICY['max_request_work_units'],'Whole request including full fallback differs')
    return True
