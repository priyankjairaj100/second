"""Registration/admission failure fixtures; no real-model or corpus execution."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research_v61 import campaign as c


def prior_fixture():
    keys=('v59_program','v59_registration','v59_completion','v59_audit','v59_ledger',*c.V59_ARTIFACTS)
    inputs={key:dict(path='/fixture/'+key,bytes=17,sha256='1'*64) for key in keys}
    for key,sha in (('v59_program',c.V59_PROGRAM),('v59_completion',c.V59_COMPLETION),
                    ('v59_audit',c.V59_AUDIT),('v59_candidate_model',c.V59_MODEL),('v59_candidate_target',c.V59_TARGET)):
        inputs[key]['sha256']=sha
    program=dict(schema='full-precision-anchor-quality-diagnostic-v59',directory='/fixture')
    completion=dict(schema='full-precision-anchor-quality-worker-v59',status='complete',valid_diagnostic=True,
        program_sha256=c.V59_PROGRAM,development_guards_pass=True,candidate_count=1,code_count=42_467_328,
        retained_calibration_tokens=768,summary={'fixture':'passed'},artifacts={name:dict(file=name,**{f:inputs[key][f] for f in ('sha256','bytes')})
            for key,name in c.V59_ARTIFACTS.items()})
    audit=dict(schema='full-precision-anchor-quality-artifact-audit-v59',status='verified',program_sha256=c.V59_PROGRAM,
        campaign='/fixture',summary=completion['summary'],development_guards_pass=True,checked_losses=40,
        complete_stages=24,actual_model_codes_reconstructed=42_467_328,sealed_cpu_receipt_verified=True,
        actual_candidate_model_sha256=c.V59_MODEL,candidate_target_sha256=c.V59_TARGET,
        inputs={entry['path']:{f:entry[f] for f in ('bytes','sha256')} for key,entry in inputs.items() if key!='v59_audit'})
    return program,completion,audit,inputs


class CampaignTests(unittest.TestCase):
    def test_exact_passed_prior_receipt_is_admitted(self):
        c.check_prior(*prior_fixture())

    def test_failed_or_incomplete_quality_does_not_authorize_service(self):
        for key,value in (('development_guards_pass',False),('status','failed'),('valid_diagnostic',False),
                          ('candidate_count',2),('code_count',1)):
            p,result,a,inputs=prior_fixture();result[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Complete passed V59'):
                c.check_prior(p,result,a,inputs)

    def test_actual_artifact_audit_cannot_be_replaced_by_metadata_assertion(self):
        for key,value in (('status','metadata_only'),('sealed_cpu_receipt_verified',False),('complete_stages',23),
                          ('actual_candidate_model_sha256','0'*64),('checked_losses',32)):
            p,result,a,inputs=prior_fixture();a[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Actual V59 terminal'):
                c.check_prior(p,result,a,inputs)

    def test_changed_fixed_receipt_or_missing_audit_binding_refused(self):
        p,result,a,inputs=prior_fixture();inputs['v59_candidate_model']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Frozen V59 receipt/artifact'):
            c.check_prior(p,result,a,inputs)
        p,result,a,inputs=prior_fixture();a['inputs'][inputs['v59_ledger']['path']]['bytes']+=1
        with self.assertRaisesRegex(ValueError,'V59 audit input binding'):
            c.check_prior(p,result,a,inputs)
        p,result,a,inputs=prior_fixture();result['artifacts']['candidate-model-metadata.json']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'completion artifact'):
            c.check_prior(p,result,a,inputs)

    def test_bound_inputs_reject_actual_mutation_and_symbolic_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();path=root/'metadata.json';path.write_bytes(b'{}')
            entry=c.bind(path);self.assertEqual(c.bound(entry),path)
            path.write_bytes(b'[]')
            with self.assertRaisesRegex(ValueError,'Bound input changed'):c.bound(entry)
            link=root/'link';link.symlink_to(path)
            with self.assertRaisesRegex(ValueError,'nonsymbolic'):c.bind(link)

    def test_existing_attempt_never_reaches_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();(root/'prepare').mkdir()
            with patch.dict(c.os.environ,{'SLURM_JOB_ID':'fixture'}),patch.object(c.sys,'platform','linux'), \
                 patch.object(c,'verify',return_value={'directory':str(root)}),patch.object(c,'run_limited') as execute:
                with self.assertRaisesRegex(ValueError,'One-use attempt exists'):c.run(root,'prepare')
                execute.assert_not_called()

    def test_complete_input_census_precedes_reads(self):
        with self.assertRaisesRegex(ValueError,'Complete V61 input inventory'):
            c.validate_inputs({})

    def test_software_gate_rejects_incomplete_skipped_or_unbound_checks(self):
        from research_v61.checks import MODULES,EXPECTED_TESTS
        sources={'fixture.py':'1'*64};runtime={'runtime':'fixture'}
        check=dict(status='passed',tests=EXPECTED_TESTS,skipped=0,modules=list(MODULES),
            sources=sources,runtime=runtime,real_model_inference=False)
        c.check_software(check,sources,runtime)
        for key,value in (('tests',EXPECTED_TESTS-1),('skipped',1),('modules',list(MODULES)[:-1]),
                          ('status','failed'),('sources',{'fixture.py':'2'*64}),
                          ('runtime',{'runtime':'changed'}),('real_model_inference',True)):
            changed=deepcopy(check);changed[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Complete passing source/runtime-bound'):
                c.check_software(changed,sources,runtime)


if __name__=='__main__':unittest.main()
