"""Synthetic saved-report rejection checks; not measured model evidence."""
import copy,unittest
from research_v82.admission_reports import verify_reports,POLICY,REPRESENTATIONS

def fixture():
    ids=['stage.'+str(i) for i in range(24)];reports=[]
    for n in (4,3,2):
        for rep in REPRESENTATIONS:
            stages=[]
            for sid in ids:
                stages.append(dict(stage_id=sid,width=768,admitted=True,policy=dict(POLICY),kind='box' if rep=='compressed48' else 'gram' if rep=='hybrid_gram' else 'point',target_sha256='a'*64,total_tokens=128*n,block_tokens=128,max_blocks=n,resident_bytes=9*2**30,whole_process_fit_guaranteed=False,selected_route='fixture',candidates={'fixture':dict(admitted=True,complete_rows_and_bounded_fallback_reserved=True,work_units=10,explicit_array_bytes=16,process_known_bytes=9*2**30+16)},work_units=10,explicit_array_bytes=16))
            reports.append(dict(retained=n,representation=rep,stages=stages,resident_reservation_bytes=9*2**30,process_address_space_cap=16*2**30,replay_all_ancestors_reserved=True,maximum_fallback_neural_stage_record_pairs=24*n if rep=='compressed48' else 0,reserved_work_units=480 if rep=='compressed48' else 240))
    return dict(reports=reports),ids
class SavedReports(unittest.TestCase):
    def test_complete_census_and_full_fallback_budget_pass(self):
        p,ids=fixture();self.assertTrue(verify_reports(p,'distilgpt2',ids,'a'*64))
    def test_partial_or_duplicate_census_refuses(self):
        p,ids=fixture()
        for bad in (dict(reports=p['reports'][:-1]),dict(reports=p['reports'][:1]*12)):
            with self.assertRaises(ValueError):verify_reports(bad,'distilgpt2',ids,'a'*64)
    def test_refused_stage_altered_target_and_policy_refuse(self):
        for key,value in [('admitted',False),('target_sha256','b'*64),('resident_bytes',0),('policy',{})]:
            p,ids=fixture();p['reports'][0]['stages'][0][key]=value
            with self.assertRaises(ValueError):verify_reports(p,'distilgpt2',ids,'a'*64)
    def test_omitted_fallback_reservation_and_array_overrun_refuse(self):
        p,ids=fixture();p['reports'][1]['reserved_work_units']=240
        with self.assertRaises(ValueError):verify_reports(p,'distilgpt2',ids,'a'*64)
        p,ids=fixture();p['reports'][0]['stages'][0]['candidates']['fixture']['explicit_array_bytes']=9*2**30
        with self.assertRaises(ValueError):verify_reports(p,'distilgpt2',ids,'a'*64)
if __name__=='__main__':unittest.main()
