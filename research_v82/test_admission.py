"""Prepared Linux-side failure/one-use guards; generated receipts are not evidence."""
from unittest.mock import patch,MagicMock
import unittest
from research_v82 import controller,target_worker as w
class AdmissionGuards(unittest.TestCase):
    def test_mac_target_refuses_before_plan_or_checkpoint(self):
        with patch.object(w.sys,'platform','darwin'),patch.object(w,'json_read') as read:
            with self.assertRaisesRegex(ValueError,'Pinned Linux'):w.load_plan('/unused')
            read.assert_not_called()
    def test_job_mismatch_refuses_before_live_worker_admission(self):
        plan=dict(profile='gpt2',program=str(w.RUN/'program.json'),program_sha256='a'*64,
            output=str(w.RUN/'gpt2/outputs'),slurm_job_id='wrong')
        with patch.object(w.sys,'platform','linux'),patch.object(w.platform,'node',return_value='csis.mn1'),patch.dict(w.os.environ,SLURM_JOB_ID='1'),patch.object(w,'json_read',return_value=plan),patch.object(w,'verify_command_admission') as admission:
            with self.assertRaisesRegex(ValueError,'Literal worker plan'):w.load_plan(w.RUN/'gpt2/plan.json')
            admission.assert_not_called()
    def test_failed_plan_consumes_process_attempt(self):
        with patch.object(w,'_CONSUMED',False),patch.object(w,'load_plan',side_effect=ValueError('bad plan')) as read:
            with self.assertRaisesRegex(ValueError,'bad plan'):w.main('/unused')
            with self.assertRaisesRegex(ValueError,'Fresh target-admission'):w.main('/unused')
            self.assertEqual(read.call_count,1)
    def test_close_refuses_unsettled_or_extra_target_attempts(self):
        for attempts,over in [({'a':{'state':'settled'}},False),({'a':{'state':'settled'},'b':{'state':'active'}},False),({'a':{'state':'settled'},'b':{'state':'settled'}},True)]:
            b=MagicMock();b.snapshot.return_value=dict(attempts=attempts,over_cap={'admission':over})
            with patch.object(controller,'budget',return_value=b):
                with self.assertRaisesRegex(ValueError,'settled target'):controller.close({},'hash')
    def test_close_refuses_incomplete_actual_stage_extent(self):
        b=MagicMock();b.snapshot.return_value=dict(attempts={'a':{'state':'settled'},'b':{'state':'settled'}},over_cap={'admission':False})
        bad=dict(status='complete',program_sha256='hash',profile='distilgpt2',stage_count=23,code_count=42467328,grid_allowance=1327104)
        with patch.object(controller,'budget',return_value=b),patch.object(controller,'json_read',return_value=bad):
            with self.assertRaisesRegex(ValueError,'Complete target extent'):controller.close({},'hash')
if __name__=='__main__':unittest.main()
