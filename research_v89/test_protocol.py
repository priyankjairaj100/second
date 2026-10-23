"""Protocol/path/resource failure tests; no empirical model or data access."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from research_v89 import campaign as c,config,worker
from research_v80.io import read,write,info,json_read
from src.run_store import canonical_json

class ProtocolTests(unittest.TestCase):
    def test_balanced_order_and_exact_fresh_allowance(self):
        self.assertEqual(len(config.ORDER),len(set(config.ORDER)))
        self.assertEqual(set(config.ORDER),set(config.TRIALS))
        self.assertEqual(config.ORDER[1:5],[a+'-1' for a in config.ARM_ORDER])
        self.assertEqual(config.ORDER[5:9],[a+'-2' for a in reversed(config.ARM_ORDER)])
        self.assertEqual(config.CAP,108020)
        self.assertGreater(config.design()['controller_cpu_hard_seconds'],max(x['cpu_seconds']+1 for x in config.TRIALS.values()))

    def test_second_request_reads_same_arm_successor(self):
        for arm in config.ARMS:
            self.assertEqual(worker.predecessor(arm+'-2'),(arm+'-1','state.bin','trust.json'))
            self.assertEqual(worker.predecessor(arm+'-1')[0],'prepare')
        with self.assertRaises(ValueError):worker.predecessor('reference_modern-3')

    def test_exclusive_writer_and_exact_byte_read(self):
        with TemporaryDirectory() as folder:
            p=Path(folder).resolve()/'result';receipt=write(p,b'actual',raw=True)
            self.assertEqual(read(p,info(b'actual')),b'actual')
            self.assertEqual(receipt,dict(file='result',**info(b'actual')))
            with self.assertRaises(FileExistsError):write(p,b'retry',raw=True)
            self.assertEqual(p.read_bytes(),b'actual')

    def test_mutated_bound_file_refuses(self):
        with TemporaryDirectory() as folder:
            p=Path(folder).resolve()/'input';p.write_bytes(b'old');expected=info(p.read_bytes());p.write_bytes(b'new')
            with self.assertRaises(ValueError):read(p,expected)

    def test_symlink_ancestor_and_oversize_refuse(self):
        with TemporaryDirectory() as folder:
            r=Path(folder).resolve();(r/'actual').mkdir();(r/'actual/x').write_bytes(b'bytes');(r/'link').symlink_to(r/'actual',target_is_directory=True)
            with self.assertRaises(ValueError):read(r/'link/x')
            with self.assertRaises(ValueError):read(r/'actual/x',maximum=4)
            with self.assertRaises(ValueError):write(r/'new',b'bytes',raw=True,maximum=4)

    def test_noncanonical_metadata_refuses(self):
        with TemporaryDirectory() as folder:
            p=Path(folder).resolve()/'input';p.write_bytes(b'{ }')
            with self.assertRaises(ValueError):json_read(p)

    def test_existing_attempt_refuses_before_worker_dispatch(self):
        with TemporaryDirectory() as folder:
            r=Path(folder).resolve();(r/'prepare').mkdir()
            with patch.object(c,'RUN',r),patch.object(c,'verify',return_value={}),patch.object(c.sys,'platform','linux'),patch.dict(c.os.environ,SLURM_JOB_ID='123'),patch.object(c,'run_limited') as execute:
                with self.assertRaisesRegex(ValueError,'One-use attempt'):c.run('prepare')
                execute.assert_not_called()

    def test_missing_or_failed_predecessor_stops_dispatch(self):
        with TemporaryDirectory() as folder:
            r=Path(folder).resolve();write(r/'prepare/transaction.json',dict(worker_outcome=dict(status='failed')))
            with patch.object(c,'RUN',r),patch.object(c,'verify',return_value={}),patch.object(c.sys,'platform','linux'),patch.dict(c.os.environ,SLURM_JOB_ID='123'),patch.object(c,'run_limited') as execute:
                with self.assertRaisesRegex(ValueError,'Earlier one-use trial'):c.run(config.ORDER[1])
                execute.assert_not_called()

    def test_incomplete_input_census_refuses_before_read(self):
        with patch.object(c,'bound') as opening:
            with self.assertRaises(ValueError):c.verify_inputs(dict(inputs={}))
            opening.assert_not_called()

    def test_replaced_root_refuses_before_data_read(self):
        p=dict(inputs={'data_records':dict(sha256='0'*64),'data_selection':dict(sha256=config.SELECTION_SHA)})
        with patch.object(c,'entry_json') as opening:
            with self.assertRaises(ValueError):c.load_records(p)
            opening.assert_not_called()

    def test_worker_artifact_census_is_complete_and_distinct(self):
        self.assertEqual(len(worker.expected_artifacts('prepare')),11)
        self.assertEqual(len(worker.expected_artifacts('oracle')),20)
        for arm in config.ARMS:self.assertEqual(worker.expected_artifacts(arm+'-1'),{'execution-provenance.json','admission.json','state.bin','trust.json','model.bin'})

class ControllerAuditTests(unittest.TestCase):
    def fixture(self,root):
        from research_v89 import audit
        p=config.design();write(root/'program.json',p);sha=c.sha(root/'program.json');completions={}
        for trial in p['trial_order']:
            r=dict(status='complete',error=None,program_sha256=sha,operation='run',arguments=[trial],job_id='321',
                hostname='csis.mn1',affinity_cpus=[0],cpu_limits=[600,16802],child_cpu_is_numerical_ledger_work=True,
                process_cpu_ns=10**9,waited_child_cpu_ns=10**9,elapsed_ns=3*10**9)
            write(root/(trial+'-entry.json'),r)
            write(root/(trial+'-entry-start.json'),{k:r[k] for k in ['program_sha256','operation','arguments','job_id','hostname','affinity_cpus']})
            write(root/trial/'transaction.json',dict(elapsed_ns=2*10**9));completions[trial]=dict(slurm_job_id='321')
        return p,completions

    def test_controller_cpu_counted_once_and_overage_refuses(self):
        from research_v89 import audit
        with TemporaryDirectory() as folder:
            root=Path(folder).resolve();p,completions=self.fixture(root)
            with patch.object(audit,'RUN',root):
                result=audit.entry_costs(p,completions,audit.AuditInputs())
                self.assertEqual(result['process_cpu_ns'],10*10**9)
                q=root/'prepare-entry.json';r=json_read(q);r['process_cpu_ns']=602*10**9;q.write_bytes(canonical_json(r))
                with self.assertRaises(ValueError):audit.entry_costs(p,completions,audit.AuditInputs())

    def test_wrong_controller_job_cannot_use_complete_receipt(self):
        from research_v89 import audit
        with TemporaryDirectory() as folder:
            root=Path(folder).resolve();p,completions=self.fixture(root);completions['prepare']['slurm_job_id']='999'
            with patch.object(audit,'RUN',root):
                with self.assertRaises(ValueError):audit.entry_costs(p,completions,audit.AuditInputs())

if __name__=='__main__':unittest.main()
