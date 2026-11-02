"""Generated metadata mutation tests; never a successful empirical gate."""
import copy,unittest
from research_v91.config import design,ORDER,TARGET_FILES
from research_v92.gate import validate
from research_v80.io import info
from src.run_store import canonical_json

def fixture():
    p=dict(design(),recovery_gate={'fixture_only':True});sha=info(canonical_json(p))['sha256']
    jobs={name:dict(job_id=str(20000+i),name='second91-'+name) for i,name in enumerate(ORDER)}
    s=dict(status='verified',attempts={name:dict(state='settled') for name in ('a','b')},reserved_unknown_attempts=0,
        reservation_overrun_attempts=[],over_cap={'admission':False})
    report=dict(schema='matched-target-terminal-v91',status='verified',program_sha256=sha,actual_target_admission=True,
        empirical_transfer=False,quality_evaluation=False,jobs=jobs,recovery_gate=p['recovery_gate'],budget=s,
        scheduler_raw='\n'.join('|'.join([row['job_id'],row['name'],'COMPLETED','0:0','1','00:00.001','1','16G','csis.mn1']) for row in jobs.values()),
        costs={name:{} for name in jobs})
    models={name:dict(status='complete',profile=name,program_sha256=sha,job_id=jobs[name]['job_id'],artifacts={n:{} for n in TARGET_FILES}) for name in ('distilgpt2','gpt2')}
    close=dict(schema='matched-target-close-v91',status='admitted_pending_host_terminal_accounting',program_sha256=sha,budget=s,
        empirical_transfer=False,neural_execution=False,calibration_execution=False,quality_evaluation=False,
        seal_audit=dict(schema='matched-target-seals-v91',actual_targets_verified=True,sealed_workers_verified=True,
            matched_records_verified=True,numerical_model_transfer=False,models=models))
    return report,p,close
class Gate(unittest.TestCase):
    def test_scope_shape_only_fixture_is_not_a_reopened_gate(self):
        r,p,c=fixture();self.assertEqual(set(validate(r,p,c)),set(ORDER));self.assertNotIn('inputs',r)
    def test_failed_missing_or_wrong_allocation_refuses(self):
        for change in ('failed','omitted','name'):
            r,p,c=fixture()
            if change=='failed':r['scheduler_raw']=r['scheduler_raw'].replace('COMPLETED','FAILED',1)
            elif change=='omitted':r['jobs'].pop('gpt2')
            else:r['jobs']['gpt2']['name']='second82-gpt2'
            with self.assertRaises(ValueError):validate(r,p,c)
    def test_unknown_debit_or_scope_upgrade_refuses(self):
        for change in ('debit','scope','profile','artifact'):
            r,p,c=fixture()
            if change=='debit':r['budget']['reserved_unknown_attempts']=1
            elif change=='scope':r['empirical_transfer']=True
            elif change=='profile':c['seal_audit']['models']['gpt2']['profile']='distilgpt2'
            else:c['seal_audit']['models']['gpt2']['artifacts'].pop('records.json')
            with self.assertRaises(ValueError):validate(r,p,c)
    def test_changed_grid_or_program_digest_refuses(self):
        r,p,c=fixture();p['grid_allowance']+=1
        with self.assertRaises(ValueError):validate(r,p,c)
        r,p,c=fixture();r['program_sha256']='f'*64
        with self.assertRaises(ValueError):validate(r,p,c)
if __name__=='__main__':unittest.main()
