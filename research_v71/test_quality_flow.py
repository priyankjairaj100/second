"""Generated tokens and fake model factories; no actual CPU/GPU inference."""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json,unittest
from research_v71 import quality_flow as f

RECORDS=[dict(id=f'article-{i:04d}',tokens=[i]*128) for i in range(320)]
BINDINGS={m:dict(fixture_only=m) for m in f.stats.MODELS}

def factory(calls,*,bad_parity=False,adverse=False,fail_at=None,wrong_binding=False):
    @contextmanager
    def make(model):
        def nll(tokens):
            i=tokens[0];calls.append((model,i))
            if len(calls)==fail_at:raise ArithmeticError('generated evaluator refusal')
            if bad_parity and model=='sequential_6' and i==3:return 508.+127*2e-8
            return 508.+(127*.2 if adverse and model.startswith('candidate_') and i>=4 else 0.)
        yield SimpleNamespace(binding={'wrong':True} if wrong_binding else BINDINGS[model],nll=nll)
    return make

def cpu(root):return f.collect('cpu_parity',RECORDS,factory([]),BINDINGS,root/'cpu',registration_sha256='a'*64)

class QualityFlowTests(unittest.TestCase):
    def test_full_gate_precedes_remaining_articles_and_parity_losses_are_not_repeated(self):
        with TemporaryDirectory() as td:
            root=Path(td).resolve();reference=cpu(root);calls=[]
            result=f.collect('gpu_quality',RECORDS,factory(calls),BINDINGS,root/'gpu',registration_sha256='a'*64,cpu_reference=reference)
            self.assertEqual(result['status'],'complete');self.assertEqual(len(calls),1920)
            self.assertEqual(len(set(calls)),1920);self.assertTrue(all(i<4 for m,i in calls[:24]))
            self.assertTrue(all(i>=4 for m,i in calls[24:]));self.assertTrue(result['summary']['all_endpoint_gates_pass'])
            self.assertEqual(reference['completed_article_evaluations'],24)
            original=(root/'gpu/completion.json').read_bytes()
            with self.assertRaises(FileExistsError):f.collect('gpu_quality',RECORDS,factory([]),BINDINGS,root/'gpu',registration_sha256='a'*64,cpu_reference=reference)
            self.assertEqual((root/'gpu/completion.json').read_bytes(),original)

    def test_last_parity_failure_preserves_all24_and_prevents_remaining_inference(self):
        with TemporaryDirectory() as td:
            root=Path(td).resolve();reference=cpu(root);calls=[]
            with self.assertRaisesRegex(ValueError,'All24'):
                f.collect('gpu_quality',RECORDS,factory(calls,bad_parity=True),BINDINGS,root/'gpu',registration_sha256='a'*64,cpu_reference=reference)
            self.assertEqual(len(calls),24);receipt=json.loads((root/'gpu/completion.json').read_bytes())
            self.assertEqual(receipt['status'],'failed');self.assertFalse(receipt['parity']['passed'])
            self.assertFalse((root/'gpu/paired-losses.json').exists())

    def test_adverse_quality_is_complete_and_not_discarded(self):
        with TemporaryDirectory() as td:
            root=Path(td).resolve();result=f.collect('gpu_quality',RECORDS,factory([],adverse=True),BINDINGS,root/'gpu',registration_sha256='a'*64,cpu_reference=cpu(root))
            self.assertEqual(result['status'],'complete');self.assertFalse(result['summary']['all_endpoint_gates_pass'])
            self.assertEqual(result['completed_article_evaluations'],1920)

    def test_evaluator_failure_preserves_partial_losses_and_refuses_same_output_retry(self):
        with TemporaryDirectory() as td:
            root=Path(td).resolve();calls=[]
            with self.assertRaises(ArithmeticError):f.collect('cpu_parity',RECORDS,factory(calls,fail_at=5),BINDINGS,root/'cpu',registration_sha256='a'*64)
            receipt=json.loads((root/'cpu/completion.json').read_bytes())
            self.assertEqual(receipt['completed_article_evaluations'],4);self.assertTrue(receipt['partial_losses_retained'])
            self.assertEqual(len(list((root/'cpu').glob('loss-*.json'))),4)
            with self.assertRaises(FileExistsError):cpu(root)

    def test_wrong_reference_or_installed_model_cannot_execute_any_likelihood(self):
        with TemporaryDirectory() as td:
            root=Path(td).resolve();reference=cpu(root);reference['model_bindings']={};calls=[]
            with self.assertRaises(ValueError):f.collect('gpu_quality',RECORDS,factory(calls),BINDINGS,root/'gpu',registration_sha256='a'*64,cpu_reference=reference)
            self.assertEqual(calls,[])
            with self.assertRaises(ValueError):f.collect('cpu_parity',RECORDS,factory(calls,wrong_binding=True),BINDINGS,root/'bad',registration_sha256='a'*64)
            self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
