"""Local fixture/preflight tests only; run() has not executed CUDA here."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from research_v69 import cuda_qualification as q


class CudaQualificationPreparationTests(unittest.TestCase):
    def test_all_six_generated_cpu_models_support_exact128_token_test_shape(self):
        models,records=q.fixture()
        self.assertEqual(len(records),4);self.assertTrue(all(len(r['tokens'])==128 for r in records))
        self.assertEqual(models.reference.positions[0,:2].tobytes(),np.array([-0.,float.fromhex('0x0.0000000000001p-1022')]).tobytes())
        for label in q.model_backend.MODELS:
            with models.cpu(label) as evaluator:
                self.assertTrue(all(np.isfinite(evaluator.nll(r['tokens'])) for r in records))

    def test_nonlinux_or_unallocated_process_cannot_create_output_or_initialize_cuda(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'qualification'
            with patch.object(q.sys,'platform','darwin'),patch.object(q.model_backend,'cuda') as gpu:
                with self.assertRaises(ValueError):q.run(out,registration_sha256='a'*64,allocator_bytes=8*2**30)
                gpu.assert_not_called();self.assertFalse(out.exists())
            with patch.object(q.sys,'platform','linux'),patch.dict(q.os.environ,{'SLURM_JOB_ID':''}):
                with self.assertRaises(ValueError):q.run(out,registration_sha256='a'*64,allocator_bytes=8*2**30)
                self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
