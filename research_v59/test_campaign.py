"""V59 bindings, refusal and one-use accounting; no model or empirical inputs."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research_v59 import campaign
from src.run_store import canonical_json
from src.transaction_timing import verify_command_admission


class CampaignTests(unittest.TestCase):
    def test_software_requires_exact_sources_runtime_extent_and_no_skips(self):
        from research_v59.checks import MODULES, EXPECTED_TESTS
        check=dict(status='passed',skipped=0,tests=EXPECTED_TESTS,modules=list(MODULES),
            sources={'a':'b'},runtime={'python':'fixture'},real_model_inference=False)
        campaign.check_software(check,check['sources'],check['runtime'])
        for field,value in (('status','failed'),('skipped',1),('tests',EXPECTED_TESTS-1),
                ('modules',[]),('sources',{}),('runtime',{}),('real_model_inference',True)):
            wrong=copy.deepcopy(check);wrong[field]=value
            with self.assertRaises(ValueError):campaign.check_software(wrong,check['sources'],check['runtime'])

    def test_adverse_prior_requires_complete_actual_audit(self):
        p=dict(schema='exposed-quality-diagnostic-v55',directory='/fixture')
        c=dict(schema='exposed-quality-worker-v55',status='complete',valid_diagnostic=True,
            program_sha256=campaign.V55_PROGRAM,original_normalization=1664,retained_calibration_tokens=768,
            code_count=42_467_328,summary={'fixture':'adverse'},development_guards_pass=False)
        a=dict(schema='exposed-quality-artifact-audit-v55',status='verified',program_sha256=campaign.V55_PROGRAM,
            campaign='/fixture',actual_model_codes_reconstructed=42_467_328,complete_stages=24,
            sealed_cpu_receipt_verified=True,summary=c['summary'],development_guards_pass=False)
        campaign.check_prior(p,c,a,campaign.V55_PROGRAM)
        for field,value in (('complete_stages',23),('sealed_cpu_receipt_verified',False),
                ('development_guards_pass',True),('summary',{}),('actual_model_codes_reconstructed',1)):
            wrong=copy.deepcopy(a);wrong[field]=value
            with self.assertRaises(ValueError):campaign.check_prior(p,c,wrong,campaign.V55_PROGRAM)

    def test_bound_input_rejects_same_size_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'input';path.write_bytes(b'first')
            entry=campaign.bind(path)
            self.assertEqual(campaign.bound(entry),path.resolve())
            path.write_bytes(b'other')
            with self.assertRaises(ValueError):campaign.bound(entry)

    def test_literal_command_and_separate_complete_reservation_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'program.json').write_bytes(canonical_json({'fixture':True}))
            command=[campaign.sys.executable,'-B','-m','research_v59.worker',str(root/'plan.json')]
            with patch.object(campaign,'source_hashes',return_value={'fixture.py':'1'*64}),\
                    patch('src.experiment_inventory.source_hashes',return_value={'fixture.py':'1'*64}):
                budget=campaign.budget({'directory':str(root)})
                budget.reserve('development','one',14402)
                admission=dict(phase_budget_root=str(budget.root),phase_budget_binding_sha256=budget.identity_digest,
                    attempt_id='one',phase='development',command=command,cwd=str(campaign.ROOT))
                with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(admission).decode()):
                    verify_command_admission(campaign.sha(root/'program.json'),'development',command)
                    with self.assertRaises(ValueError):
                        verify_command_admission(campaign.sha(root/'program.json'),'development',command[1:])
                self.assertEqual(budget.snapshot()['charged_cpu_seconds']['development'],14402)

    def test_failed_work_remains_charged_and_attempt_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'program.json').write_bytes(canonical_json({'fixture':True}))
            p=dict(directory=str(root),file_size_bytes=2*2**30)
            def failed(command,worker,limits,**kwargs):
                self.assertEqual(command[3],'research_v59.worker')
                self.assertEqual(limits.cpu_seconds,14400)
                plan=campaign.read(command[-1])
                self.assertEqual(plan['schema'],'full-precision-anchor-quality-plan-v59')
                self.assertEqual(plan['directory'],str(root))
                ledger=kwargs['phase_budget'];ledger.reserve('development','failed-fixture',14402)
                ledger.settle('failed-fixture',1_200_000_000)
                return {'outcome':{'status':'failed','returncode':1}}
            with patch.object(campaign,'verify',return_value=(p,{},None,None,None)),\
                    patch.object(campaign,'run_limited',side_effect=failed),\
                    patch.object(campaign,'source_hashes',return_value={'fixture.py':'1'*64}),\
                    patch.object(os,'sched_getaffinity',return_value={0},create=True),\
                    patch.object(campaign.sys,'platform','linux'),\
                    patch.dict(os.environ,SLURM_JOB_ID='fixture'):
                self.assertEqual(campaign.run(root),'failed')
                tx=campaign.read(root/'quality/transaction.json')
                self.assertEqual(tx['budget']['charged_cpu_seconds']['development'],2)
                with self.assertRaisesRegex(ValueError,'already exists'):campaign.run(root)


if __name__=='__main__':unittest.main()
