"""Saved generated loss-file audit and mutation fixtures; inference is fake."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from research_v69 import loss_audit as a,quality_flow as f
from research_v69.test_quality_flow import RECORDS,BINDINGS,factory,cpu
from src.run_store import canonical_json


class LossAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name).resolve();reference=cpu(self.root)
        f.collect('gpu_quality',RECORDS,factory([],adverse=True),BINDINGS,self.root/'gpu',registration_sha256='a'*64,cpu_reference=reference)
    def tearDown(self):self.temp.cleanup()
    def audit(self):return a.audit(self.root/'gpu',RECORDS,BINDINGS,registration_sha256='a'*64,cpu_directory=self.root/'cpu')

    def test_actual_all1920_losses_and_cpu_reference_are_audited_with_negative_result(self):
        result=self.audit();self.assertEqual(result['actual_loss_files_compared'],1920)
        self.assertEqual(result['actual_cpu_reference_audit']['actual_loss_files_compared'],24)
        self.assertTrue(result['statistics_recomputed']);self.assertFalse(result['all_endpoint_gates_pass'])
        self.assertFalse(result['independent_likelihood_reexecution'])

    def test_last_saved_loss_and_prediction_count_mutations_refuse(self):
        path=self.root/'gpu/loss-sequential_6-0319.json';original=path.read_bytes()
        changed=json.loads(original);changed['nll_sum']+=1;path.write_bytes(canonical_json(changed))
        with self.assertRaises(ValueError):self.audit()
        changed=json.loads(original);changed['predictions']=126;path.write_bytes(canonical_json(changed))
        completion=self.root/'gpu/completion.json';r=json.loads(completion.read_bytes());r['quality']['sequential_6'][-1]['predictions']=126;completion.write_bytes(canonical_json(r))
        with self.assertRaisesRegex(ValueError,'loss binding'):self.audit()

    def test_fake_guard_success_and_reordered_parity_barrier_refuse(self):
        path=self.root/'gpu/statistics.json';original=path.read_bytes();changed=json.loads(original);changed['all_endpoint_gates_pass']=True;path.write_bytes(canonical_json(changed))
        with self.assertRaisesRegex(ValueError,'statistics'):self.audit()
        path.write_bytes(original)
        for path in (self.root/'gpu').glob('progress-*.json'):
            x=json.loads(path.read_bytes())
            if x['phase']=='all_six_models_passed_parity':
                x['comparisons']=1;path.write_bytes(canonical_json(x));break
        else:raise AssertionError('Expected barrier fixture')
        with self.assertRaisesRegex(ValueError,'progress order'):self.audit()

    def test_changed_cpu_reference_file_or_undeclared_gpu_file_refuses(self):
        path=self.root/'cpu/loss-original-0000.json';original=path.read_bytes();changed=json.loads(original);changed['nll_sum']+=1;path.write_bytes(canonical_json(changed))
        with self.assertRaises(ValueError):self.audit()
        path.write_bytes(original);(self.root/'gpu/extra.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'Unexpected'):self.audit()


if __name__=='__main__':unittest.main()
