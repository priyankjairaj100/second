"""Malformed saved-metadata rejection; fixtures are never empirical evidence."""
import copy,json,unittest
from reporting_v102.reduce import validate,identity
from research_v104.config import design,OPERATIONS,PROFILES,CELLS,name,RUN


def fixture():
    p=design();p['prior_complete_failure']=dict(carried_software_seconds=72,carried_controller_seconds=19,carried_numerical_controller_seconds=1);raw=json.dumps(p,sort_keys=True,separators=(',',':')).encode();sha=identity(raw)['sha256']
    jobs={op:dict(job_id=str(30000+i),name='second104-'+name(op)) for i,op in enumerate(OPERATIONS)}
    costs={op:dict(job_id=row['job_id'],scheduler_cpu_ns=1000000,scheduler_quantum_ns=1000000,complete_controller_upper_cpu_ns=2000000) for op,row in jobs.items()}
    budget=dict(status='verified',attempts={str(i):dict(state='settled') for i in range(20)},reserved_unknown_attempts=0,reservation_overrun_attempts=[],over_cap={'fixture':False})
    bound={str(RUN/'primary-audit.json'):dict(bytes=12,sha256='a'*64)}
    evidence={profile:dict(comparisons=[dict(profile=profile,cell=cell,step=step,actual_model_bytes_equal=True,actual_state_bytes_equal=True,actual_trust_bytes_equal=True) for cell in CELLS for step in (1,2)]) for profile in PROFILES}
    a=dict(schema='complete-matched-primary-audit-v104',status='verified',program_sha256=sha,budget=budget,inputs={},costs={},worker_output_extents={},evidence=evidence,confirmation=False,quality_evaluation=False)
    b=dict(a,schema='complete-matched-supplemental-audit-v104',evidence=dict(primary_sha256='a'*64,actual_model_pairs_equal=16))
    t=dict(schema='matched-complete-terminal-v104',status='verified',program_sha256=sha,jobs=jobs,costs=costs,budget=budget,inputs=bound,prior_complete_failure=copy.deepcopy(p['prior_complete_failure']),cumulative_software_upper_cpu_ns=72002000000,
        scheduler_raw='\n'.join('|'.join([r['job_id'],r['name'],'COMPLETED','0:0','1','00:00.001','1','16G','csis.mn1']) for r in jobs.values()),
        evidence=dict(actual_model_state_trust_pairs=16,checkpoints=2,related_gpt_family_only=True,single_observation_screen=True,stable_speedup=False,cross_architecture_generality=False,quality_evaluation=False))
    return t,p,a,b,raw

class Reporting(unittest.TestCase):
    def test_complete_shape_is_not_raw_binary_evidence(self):
        values=fixture();self.assertEqual(set(validate(*values)),set(OPERATIONS))
    def test_failure_and_missing_allocation_refuse(self):
        for change in ('failure','missing'):
            t,p,a,b,raw=fixture()
            if change=='failure':t['scheduler_raw']=t['scheduler_raw'].replace('COMPLETED','FAILED',1)
            else:t['jobs'].pop('checks')
            with self.assertRaises(ValueError):validate(t,p,a,b,raw)
    def test_wrong_profile_or_omitted_losing_endpoint_refuses(self):
        for change in ('profile','endpoint'):
            t,p,a,b,raw=fixture();rows=a['evidence']['gpt2']['comparisons']
            if change=='profile':rows[0]['profile']='distilgpt2'
            else:rows.pop()
            with self.assertRaises(ValueError):validate(t,p,a,b,raw)
    def test_changed_audit_input_and_primary_commitment_refuse(self):
        for change in ('input','primary'):
            t,p,a,b,raw=fixture()
            if change=='input':a['inputs']['unbound']=dict(bytes=1,sha256='b'*64)
            else:b['evidence']['primary_sha256']='b'*64
            with self.assertRaises(ValueError):validate(t,p,a,b,raw)
    def test_unknown_debit_and_scope_upgrade_refuse(self):
        for change in ('debit','generality','quality'):
            t,p,a,b,raw=fixture()
            if change=='debit':t['budget']['reserved_unknown_attempts']=1
            elif change=='generality':t['evidence']['cross_architecture_generality']=True
            else:a['quality_evaluation']=True
            with self.assertRaises(ValueError):validate(t,p,a,b,raw)
    def test_cpu_omission_and_failed_equality_refuse(self):
        for change in ('cpu','equality'):
            t,p,a,b,raw=fixture()
            if change=='cpu':t['costs']['checks']['scheduler_cpu_ns']=0
            else:a['evidence']['gpt2']['comparisons'][0]['actual_model_bytes_equal']=False
            with self.assertRaises(ValueError):validate(t,p,a,b,raw)

    def test_prior_charges_and_cumulative_controller_caps_cannot_disappear(self):
        for change in ('software','checks_controller','numerical_controller','prepare_cap','aggregate_cap'):
            t,p,a,b,raw=fixture()
            if change=='software':t['prior_complete_failure']['carried_software_seconds']=4
            elif change=='checks_controller':t['prior_complete_failure']['carried_controller_seconds']=4
            elif change=='numerical_controller':t['prior_complete_failure']['carried_numerical_controller_seconds']=0
            elif change=='prepare_cap':t['costs']['distilgpt2/prepare']['complete_controller_upper_cpu_ns']=302*10**9
            else:
                for op in OPERATIONS[1:-2]:t['costs'][op]['complete_controller_upper_cpu_ns']=302*10**9
                t['costs']['distilgpt2/prepare']['complete_controller_upper_cpu_ns']=301*10**9+1
            with self.assertRaises(ValueError):validate(t,p,a,b,raw)

if __name__=='__main__':unittest.main()
