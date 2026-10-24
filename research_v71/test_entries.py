"""Mocked bounded-controller/worker failures; never launch a real process."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from research_v71 import entry,worker,campaign as c
from research_v67.io import json_read


class EntryTests(unittest.TestCase):
    def test_failed_preflight_is_preserved_and_second_call_cannot_launch(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();p={'hosts':{'cpu':['generated']}};j={'job_id':'123'}
            with patch.object(c,'RUN',root),patch.object(entry,'__file__',str(root/'research_v71/entry.py')),\
                patch.object(c,'load',return_value=p),patch.object(c,'job',return_value=j),\
                patch.object(entry.platform,'node',return_value='generated'),\
                patch.object(entry.gate,'apply_controller_limits',return_value={'affinity_cpus':[3]}),\
                patch.object(c,'verify',side_effect=ValueError('generated immutable input mismatch')),\
                patch.object(entry,'run_limited') as launch:
                with self.assertRaisesRegex(ValueError,'Registered phase failed'):entry.main('parameters','a'*64)
                receipt=json_read(root/'parameters/entry.json');before=(root/'parameters/entry.json').read_bytes()
                self.assertEqual(receipt['status'],'failed');self.assertIn('immutable input',receipt['error']['message'])
                self.assertTrue(receipt['whole_process_cpu_clock']);self.assertTrue(receipt['all_waited_children_included'])
                with self.assertRaises(FileExistsError):entry.main('parameters','a'*64)
                self.assertEqual((root/'parameters/entry.json').read_bytes(),before);launch.assert_not_called()

    def test_worker_requires_live_command_admission_before_output_or_numerical_dispatch(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            with patch.object(c,'RUN',root),patch.object(worker,'__file__',str(root/'research_v71/worker.py')),\
                patch.object(worker.sys,'platform','linux'),patch.object(worker.sys,'dont_write_bytecode',True),\
                patch.object(c,'load',return_value={}),patch.object(c,'job',return_value={'job_id':'123'}),\
                patch.dict(worker.os.environ,{'SLURM_JOB_ID':'123'}),patch.object(c,'command',return_value=['/generated/python']),\
                patch.object(worker,'verify_command_admission',side_effect=ValueError('no active allowance')),\
                patch.object(c,'verify') as verify:
                with self.assertRaisesRegex(ValueError,'active allowance'):worker.main('parameters','a'*64)
                verify.assert_not_called();self.assertFalse((root/'parameters/outputs').exists())


if __name__=='__main__':unittest.main()
