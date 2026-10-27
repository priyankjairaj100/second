"""Malformed saved-metadata rejection; fixtures are never empirical evidence."""
import copy,json,unittest
from reporting_v113.reduce import validate,identity
from research_v112.config import design,OPERATIONS,PROFILES,CELLS,name,RUN


def fixture():
    p=design();p['prior_complete_failure']=dict(carried_software_seconds=207,carried_checks_controller_seconds=48,carried_numerical_controller_seconds=79,carried_numerical_seconds=6304);raw=json.dumps(p,sort_keys=True,separators=(',',':')).encode();sha=identity(raw)['sha256']
    jobs={op:dict(job_id=str(30000+i),name='second112-'+name(op)) for i,op in enumerate(OPERATIONS)}
    costs={op:dict(job_id=row['job_id'],scheduler_cpu_ns=1000000,scheduler_quantum_ns=1000000,complete_controller_upper_cpu_ns=2000000) for op,row in jobs.items()}
    budget=dict(status='verified',attempts={str(i):dict(state='settled',charged_cpu_seconds=1) for i in range(18)},charged_cpu_seconds={'feasibility':18},reserved_unknown_attempts=0,reservation_overrun_attempts=[],over_cap={'fixture':False})
    bound={str(RUN/'primary-audit.json'):dict(bytes=12,sha256='a'*64)}
    evidence={profile:dict(comparisons=[dict(profile=profile,cell=cell,step=step,actual_model_bytes_equal=True,actual_state_bytes_equal=True,actual_trust_bytes_equal=True) for cell in CELLS for step in (1,2)]) for profile in PROFILES}
    a=dict(schema='complete-matched-primary-audit-v112',status='verified',program_sha256=sha,budget=budget,inputs={},costs={},worker_output_extents={},evidence=evidence,confirmation=False,quality_evaluation=False)
    b=dict(a,schema='complete-matched-supplemental-audit-v112',evidence=dict(primary_sha256='a'*64,actual_model_pairs_equal=16))
    t=dict(schema='matched-complete-terminal-v112',status='verified',program_sha256=sha,jobs=jobs,costs=costs,budget=budget,inputs=bound,prior_complete_failure=copy.deepcopy(p['prior_complete_failure']),cumulative_software_upper_cpu_ns=207002000000,cumulative_checks_controller_upper_cpu_ns=48002000000,cumulative_numerical_controller_upper_cpu_ns=79036000000,cumulative_numerical_seconds=6322,
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

    def test_prior_charges_and_cumulative_caps_cannot_disappear(self):
        for field in ('carried_software_seconds','carried_checks_controller_seconds','carried_numerical_controller_seconds','carried_numerical_seconds'):
            t,p,a,b,raw=fixture();t['prior_complete_failure'][field]=0
            with self.assertRaises(ValueError):validate(t,p,a,b,raw)
        for field in ('cumulative_software_upper_cpu_ns','cumulative_checks_controller_upper_cpu_ns','cumulative_numerical_controller_upper_cpu_ns','cumulative_numerical_seconds'):
            t,p,a,b,raw=fixture();t[field]=0
            with self.assertRaises(ValueError):validate(t,p,a,b,raw)
    def test_repeated_old_preparation_debit_and_missing_charge_refuse(self):
        for change in ('old_attempt','charge'):
            t,p,a,b,raw=fixture()
            if change=='old_attempt':t['budget']['attempts']['old_prepare']=dict(state='settled',charged_cpu_seconds=1)
            else:t['budget']['charged_cpu_seconds']['feasibility']=0
            with self.assertRaises(ValueError):validate(t,p,a,b,raw)

if __name__=='__main__':unittest.main()
