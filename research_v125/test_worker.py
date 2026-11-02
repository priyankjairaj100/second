import unittest,tempfile,json,struct
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from research_v125.worker import unroll,audit_parameters,ident,read

class LoaderTests(unittest.TestCase):
 def test_packed_codes_independent_nibble_reference(self):
  raw=bytes(range(256));e={'stage_id':'a','shape':[16,32],'row_scale_hex':[float(2**(-i)).hex() for i in range(16)]}
  x=unroll(raw,[e])['a']
  for n in range(512):self.assertEqual(x.flat[n],((raw[n//2]>>(4*(n%2))&15)-8)*2**(-(n//32)))
 def test_incomplete_or_trailing_model_refused(self):
  e={'stage_id':'a','shape':[1,2],'row_scale_hex':['0x1.0p+0']}
  for raw in [b'',b'\x00\x00']:
   with self.assertRaises(AssertionError):unroll(raw,[e])
 def test_parameter_reader_catches_mapping_and_word_corruption(self):
  # A tiny complete one-block safetensors fixture exercises every mapping.
  tensors={};r=SimpleNamespace(blocks=[{}],weights={})
  for name,src,shape in [('embeddings','wte.weight',(5,2)),('positions','wpe.weight',(3,2)),('final_scale','ln_f.weight',(2,)),('final_bias','ln_f.bias',(2,))]:
   a=np.arange(np.prod(shape),dtype=np.float32).reshape(shape)+0.125;tensors[src]=a;setattr(r,name,a.astype(np.float64))
  r.head=r.embeddings.copy();r.head_bias=np.zeros(5,dtype=np.float64)
  for dest,src in [('norm1_scale','ln_1.weight'),('norm1_bias','ln_1.bias'),('norm2_scale','ln_2.weight'),('norm2_bias','ln_2.bias')]:
   a=np.array([0.25,-0.5],dtype=np.float32);tensors['h.0.'+src]=a;r.blocks[0][dest]=a.astype(np.float64)
  for dest,src,shape in [('qkv','attn.c_attn',(2,6)),('attn_out','attn.c_proj',(2,2)),('mlp_up','mlp.c_fc',(2,8)),('mlp_down','mlp.c_proj',(8,2))]:
   a=np.arange(np.prod(shape),dtype=np.float32).reshape(shape)-3;tensors['h.0.'+src+'.weight']=a;r.weights['block.0000.'+dest]=a.T.astype(np.float64)
   a=np.arange(shape[1],dtype=np.float32);tensors['h.0.'+src+'.bias']=a;r.blocks[0][dest+'_bias']=a.astype(np.float64)
  header={};blob=b''
  for k,a in tensors.items():
   b=a.astype('<f4').tobytes();header[k]={'shape':list(a.shape),'dtype':'F32','data_offsets':[len(blob),len(blob)+len(b)]};blob+=b
  h=json.dumps(header).encode()
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'model.safetensors';p.write_bytes(struct.pack('<Q',len(h))+h+blob)
   self.assertEqual(len(audit_parameters(r,p)),18)
   r.blocks[0]['norm1_bias'][0]+=0.125
   with self.assertRaises(AssertionError):audit_parameters(r,p)
 def test_input_mutation_refused(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x';p.write_bytes(b'a');e=dict(path=str(p),**ident(b'a'));self.assertEqual(read(e),b'a');p.write_bytes(b'b')
   with self.assertRaises(AssertionError):read(e)
class RuntimeTests(unittest.TestCase):
 def test_real_libm_filename_forms(self):
  from research_v125.runtime import is_libm
  for p in ['/usr/lib64/libm-2.17.so','/usr/lib/libm.so.6','/x/libm.so']:
   self.assertTrue(is_libm(p))
 def test_unrelated_libraries_refused(self):
  from research_v125.runtime import is_libm
  for p in ['/x/libmvec.so.1','/x/libmpfr.so.6','/x/libm-malicious.so','relative/libm.so.6']:
   self.assertFalse(is_libm(p))
 def test_no_loaded_math_library_refused(self):
  from research_v125.runtime import libraries
  with self.assertRaises(RuntimeError):libraries('000 r-xp 00 00:00 1 /x/libmvec.so.1')
if __name__=='__main__':unittest.main()

