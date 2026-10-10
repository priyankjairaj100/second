import copy
import os
from types import SimpleNamespace
import unittest
import numpy as np
from research_v46.evaluator import compare,TorchQualityDecoder
from scripts.run_quality_v30 import NumpyQualityDecoder,nll_from_logits


def fixture():
    random=np.random.default_rng(46)
    evaluator=NumpyQualityDecoder.__new__(NumpyQualityDecoder)
    evaluator.np=np
    evaluator.config=SimpleNamespace(model_width=4,head_count=2,activation='gelu_new',layernorm_epsilon=1e-5)
    evaluator.base=SimpleNamespace(_tokens=lambda tokens:tuple(tokens))
    evaluator.embeddings=random.normal(size=(11,4));evaluator.positions=random.normal(size=(8,4))
    evaluator.head=random.normal(size=(11,4));evaluator.head_bias=random.normal(size=11)
    evaluator.final_scale=random.normal(size=4);evaluator.final_bias=random.normal(size=4)
    evaluator.weights={};evaluator.blocks=[]
    for index in range(2):
        block={k:random.normal(size=4) for k in ('norm1_scale','norm1_bias','norm2_scale','norm2_bias')}
        for name,shape in [('qkv',(12,4)),('attn_out',(4,4)),('mlp_up',(8,4)),('mlp_down',(4,8))]:
            evaluator.weights[f'block.{index:04d}.{name}']=random.normal(size=shape)*0.1
            block[name+'_bias']=random.normal(size=shape[0])*0.1
        evaluator.blocks.append(block)
    return evaluator


class MatchedLosses(unittest.TestCase):
    def setUp(self):
        self.ids=['article-'+str(i) for i in range(8)]
        self.rows={label:[dict(id=rid,nll_sum=127.,predictions=127) for rid in self.ids]
            for label in ('full_precision','nearest_rounding','fixed_feature','sequential')}

    def test_full_extent_passes(self):
        result=compare(self.rows,self.rows,self.ids)
        self.assertTrue(result['passed']);self.assertEqual(len(result['checks']),32)

    def test_deviation_is_preserved_as_loss(self):
        altered=copy.deepcopy(self.rows);altered['fixed_feature'][3]['nll_sum']+=1e-4
        self.assertFalse(compare(altered,self.rows,self.ids)['passed'])

    def test_missing_article_or_nan_rejected(self):
        altered=copy.deepcopy(self.rows);altered['fixed_feature'].pop()
        with self.assertRaises(ValueError):compare(altered,self.rows,self.ids)
        altered=copy.deepcopy(self.rows);altered['sequential'][0]['nll_sum']=float('nan')
        with self.assertRaises(ValueError):compare(altered,self.rows,self.ids)


class DecoderParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:import torch
        except ImportError:raise unittest.SkipTest('PyTorch unavailable; CUDA fixtures must pass on Slurm')
        cls.torch=torch;cls.device=os.environ.get('V46_TEST_DEVICE','cpu')
        if cls.device=='cuda' and not torch.cuda.is_available():
            raise RuntimeError('Requested CUDA fixture device is unavailable')
        torch.set_num_threads(1);torch.backends.cuda.matmul.allow_tf32=False
        torch.backends.cudnn.allow_tf32=False;torch.use_deterministic_algorithms(True)

    def test_complete_batch_and_replacement_prefix(self):
        cpu=fixture();gpu=TorchQualityDecoder(cpu,self.device);tokens=[1,3,5,2,4]
        changed={k:v*0.75 for k,v in cpu.weights.items()}
        with self.torch.inference_mode():
            for prefix in (None,changed):
                installed=None if prefix is None else gpu.prefix(prefix)
                expected=cpu.logits(tokens,prefix);actual=gpu.logits(tokens,installed).cpu().numpy()
                np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-11)
                self.assertLess(abs(gpu.nll(tokens,installed)-nll_from_logits(expected,tokens)),1e-11)
        if self.device=='cuda':self.assertTrue(gpu.head.is_cuda)

    def test_future_tokens_cannot_change_past_logits(self):
        gpu=TorchQualityDecoder(fixture(),self.device)
        with self.torch.inference_mode():
            a=gpu.logits([1,3,5,2,4]).cpu().numpy()
            b=gpu.logits([1,3,5,7,8]).cpu().numpy()
        np.testing.assert_array_equal(a[:3],b[:3])

    def test_bitwise_copy_and_dtype_guard(self):
        gpu=TorchQualityDecoder(fixture(),self.device)
        words=np.array([0.,-0.,float.fromhex('0x0.0000000000001p-1022'),1.],dtype=np.float64)
        self.assertEqual(gpu.copy(words).cpu().numpy().tobytes(),words.tobytes())
        with self.assertRaises(ValueError):gpu.copy(words.astype(np.float32))
        with self.assertRaises(ValueError):gpu.prefix({})

    def test_state_dependencies_import_without_mpfr_execution(self):
        from research_v44.diagnostic import reconstruct_fixed
        from research_v46.campaign import validate
        self.assertTrue(callable(reconstruct_fixed) and callable(validate))

    @unittest.skipUnless(os.environ.get('SLURM_JOB_ID'),'Archive paths belong to the Slurm checkout')
    def test_registered_cpu_evidence_readable_on_gpu_python(self):
        from research_v46.campaign import dependencies,validate
        program,result=validate(dependencies())
        self.assertEqual(len(program['records']),8)
        self.assertEqual(result['status'],'complete')


if __name__=='__main__':unittest.main()
