"""Reject false completion and tampered claims using published historical receipts."""
import copy
from pathlib import Path
import tempfile
import unittest
from research_v48.report import read,sha,compare_audits,verified_costs,scheduler_status,V45_JOBS,verify_file

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'campaigns/csis_full_model_v43'


class SchedulerEvidence(unittest.TestCase):
    def complete(self):return '\n'.join(f'{job}|COMPLETED|0:0' for job in V45_JOBS)
    def test_missing_job_cannot_pass(self):
        self.assertEqual(scheduler_status('')['status'],'unknown_missing_scheduler_records')
        partial=self.complete().replace('13235|COMPLETED|0:0','')
        self.assertEqual(scheduler_status(partial)['missing_jobs'],['13235'])
    def test_failed_cancelled_and_running_preserved(self):
        for state in ('FAILED','TIMEOUT','CANCELLED','OUT_OF_MEMORY'):
            report=scheduler_status(self.complete().replace('13228|COMPLETED|0:0',f'13228|{state}|1:0'))
            self.assertEqual(report['status'],'terminal_failure_observed')
            self.assertEqual(report['jobs']['13228']['state'],state)
        self.assertEqual(scheduler_status(self.complete().replace('COMPLETED','RUNNING'))['status'],'not_all_terminal')
    def test_every_job_and_exit_code_required(self):
        self.assertEqual(scheduler_status(self.complete())['status'],'all_completed')
        self.assertEqual(scheduler_status(self.complete().replace('13234|COMPLETED|0:0','13234|COMPLETED|1:0'))['status'],
            'terminal_failure_observed')
        with self.assertRaises(ValueError):scheduler_status(self.complete()+'\n13228|COMPLETED|0:0')


class AuditClaims(unittest.TestCase):
    def setUp(self):
        self.first=read(EVIDENCE/'artifact-audit.json');self.second=read(EVIDENCE/'postrun-audit.json')
        self.ph=self.first['program_sha256'];self.fh=sha(EVIDENCE/'artifact-audit.json')
    def check(self):compare_audits(self.first,self.second,'v43',self.ph,self.fh)
    def test_completed_historical_evidence(self):self.check()
    def test_missing_or_duplicate_comparison_refused(self):
        self.second['evidence']['comparisons'][-1]=copy.deepcopy(self.second['evidence']['comparisons'][0])
        with self.assertRaisesRegex(ValueError,'distinct comparisons'):self.check()
    def test_false_code_membership_or_model_extent_refused(self):
        for field,value in [('model_export_matches_state_codes',False),('retained_tokens',768),('code_count',100)]:
            self.setUp();self.second['evidence']['comparisons'][0][field]=value
            with self.assertRaises(ValueError):self.check()
    def test_wrong_primary_commitment_refused(self):
        self.second['frozen_audit_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'bind primary'):self.check()
    def test_conflicting_output_bytes_refused(self):
        self.second['evidence']['comparisons'][0]['complete_model_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'disagree'):self.check()
    def test_adverse_costs_retained_and_ratios_recomputed(self):
        trials=('prepare','cached','compressed','hybrid','cold')
        completions={t:read(EVIDENCE/t/'outputs/completion.json') for t in trials}
        transactions={t:read(EVIDENCE/t/'transaction.json') for t in trials}
        result=verified_costs(self.first,completions,transactions,self.first['shared_checkpoint_bytes'])
        self.assertTrue(all(v>1 for v in result['ratios']['cached']['compressed_over_control_request_time']))
        self.first['ratios']['cached']['compressed_over_control_request_time'][0]=0.5
        with self.assertRaisesRegex(ValueError,'ratios differ'):
            verified_costs(self.first,completions,transactions,self.first['shared_checkpoint_bytes'])
    def test_changed_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'artifact.bin';p.write_bytes(b'abcd');entry=dict(bytes=4,sha256=sha(p))
            verify_file(p,entry);p.write_bytes(b'abce')
            with self.assertRaises(ValueError):verify_file(p,entry)


if __name__=='__main__':unittest.main()
