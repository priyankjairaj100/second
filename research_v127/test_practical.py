import unittest
from pathlib import Path
class SourceTests(unittest.TestCase):
 def test_cpu_changes_only_guard_two_cuda_calls(self):
  p=Path(__file__).parent;a=(p/'upstream/gptq.py').read_text();b=(p/'cpu_reference/gptq.py').read_text()
  a=a.replace('        torch.cuda.synchronize()',"        if self.dev.type == 'cuda':\n            torch.cuda.synchronize()").replace('        torch.cuda.empty_cache()',"        if self.dev.type == 'cuda':\n            torch.cuda.empty_cache()")
  self.assertEqual(a,b);self.assertEqual((p/'upstream/quant.py').read_bytes(),(p/'cpu_reference/quant.py').read_bytes())
 def test_pinned_upstream_file_hashes(self):
  import hashlib,json
  p=Path(__file__).parent/'upstream';j=json.loads((p/'source.json').read_text());self.assertEqual(j['commit'],'2d65066eeb06a5c9ff5184d8cebdf33662c67faf')
  for n,e in j['files'].items():
   b=(p/n).read_bytes();self.assertEqual(len(b),e['bytes']);self.assertEqual(hashlib.sha256(b).hexdigest(),e['sha256'])
class NumericalTests(unittest.TestCase):
 def test_hessian_uses_all_calibration_tokens(self):
  import torch
  from research_v127.practical import reference
  GPTQ,_=reference();g=GPTQ(torch.nn.Linear(3,2,bias=False));a=torch.tensor([[1.,2.,3.],[4.,-1.,2.]]);b=-a*.5
  g.add_batch(a[None],None);g.add_batch(b[None],None)
  torch.testing.assert_close(g.H,a.T@a+b.T@b,rtol=2e-6,atol=2e-6);self.assertEqual(g.nsamples,2);g.free()
 def test_diagonal_metric_matches_independent_nearest_grid(self):
  import torch
  from research_v127.practical import quantize_matrix,reference
  _,Q=reference();w=torch.tensor([[.2,-.3,.1],[.7,-.8,.5]],dtype=torch.float32);g=Q();g.configure(4,perchannel=True,sym=True,mse=False);g.find_params(w,weight=True)
  expected=g.scale*(torch.clamp(torch.round(w/g.scale)+g.zero,0,15)-g.zero)
  with torch.inference_mode():actual,_=quantize_matrix(w,[torch.eye(3)])
  self.assertTrue(torch.equal(actual,expected))
