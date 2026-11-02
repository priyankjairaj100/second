"""V56 software gate fixtures; only miniature logits, no actual model inference."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
from research_v56 import campaign
from research_v55 import diagnostic
from research_v55.test_diagnostic import quality


def fixture(delta=0.):
    q=quality(delta);summary=diagnostic.summarize(q)
    p=dict(schema='exposed-quality-diagnostic-v55',normalization=1664,inputs=dict(v54_program=dict(sha256=campaign.V54)),
        retained_records=[dict(id=str(i),tokens=[1]*128) for i in range(6)],directory='/fixture')
    c=dict(schema='exposed-quality-worker-v55',status='complete',valid_diagnostic=True,program_sha256='p',
        original_normalization=1664,retained_calibration_tokens=768,quality=q,summary=summary,
        development_guards_pass=summary['development_guards_pass'])
    a=dict(schema='exposed-quality-artifact-audit-v55',status='verified',program_sha256='p',campaign='/fixture',
        actual_model_codes_reconstructed=42_467_328,complete_stages=24,sealed_cpu_receipt_verified=True,
        summary=summary,development_guards_pass=summary['development_guards_pass'])
    return p,c,a


class GateTests(unittest.TestCase):
    def test_actual_export_bytes_and_words_on_gpu_runtime_without_inference(self):
        from research_v47.snapshot import load_snapshot
        root=campaign.ROOT/'local_runs/cpu-parameters-v47-20261010-a/outputs'
        self.assertEqual(campaign.sha(root/'parameters.npz'),campaign.ARRAYS)
        self.assertEqual(campaign.sha(root/'manifest.json'),campaign.MANIFEST)
        model=load_snapshot(root/'manifest.json',root/'parameters.npz')
        self.assertEqual(len(model.weights),24);self.assertEqual(model.config.vocabulary_size,50257)
        # Import the full new worker/auditor on Python3.10 without calling any
        # frozen CPU hashlib.file_digest or CPU exact-runtime execution path.
        from research_v56 import audit,worker
        self.assertTrue(callable(audit.audit) and callable(worker.main))

    def test_valid_adverse_cpu_quality_is_admitted(self):
        for delta,expected in ((0.,True),(math.log(1.3),False)):
            p,c,a=fixture(delta)
            self.assertEqual(campaign.validate_cpu_result(p,c,a,'p')['development_guards_pass'],expected)

    def test_unfinished_or_inconsistent_cpu_audit_refuses(self):
        p,c,a=fixture()
        bad=copy.deepcopy(c);bad['status']='failed'
        with self.assertRaises(ValueError):campaign.validate_cpu_result(p,bad,a,'p')
        bad=copy.deepcopy(a);bad['program_sha256']='changed'
        with self.assertRaises(ValueError):campaign.validate_cpu_result(p,c,bad,'p')
        bad=copy.deepcopy(c);bad['quality']['fixed_feature'][0]['nll_sum']+=1
        with self.assertRaises(ValueError):campaign.validate_cpu_result(p,bad,a,'p')
        bad=copy.deepcopy(a);bad['development_guards_pass']=False
        with self.assertRaises(ValueError):campaign.validate_cpu_result(p,c,bad,'p')

    def test_bound_input_rejects_same_size_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'data';path.write_bytes(b'abcd');entry=campaign.bind(path)
            self.assertEqual(campaign.bound(entry),path.resolve());path.write_bytes(b'efgh')
            with self.assertRaises(ValueError):campaign.bound(entry)
