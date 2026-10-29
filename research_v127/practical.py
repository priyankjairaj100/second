"""CPU harness for the pinned upstream GPTQ algorithm; no held-out selection."""
import sys,math,json,gc,hashlib
from pathlib import Path
import numpy as np
from research_v46.evaluator import TorchQualityDecoder

def reference():
 path=Path(__file__).parent/'cpu_reference';sys.path.insert(0,str(path))
 import gptq,quant
 assert Path(gptq.__file__).resolve()==path/'gptq.py' and Path(quant.__file__).resolve()==path/'quant.py'
 return gptq.GPTQ,quant.Quantizer

class Float32Decoder(TorchQualityDecoder):
 def copy(self,array):
  assert type(array)is np.ndarray and array.dtype==np.float64 and np.isfinite(array).all()
  self.copied_arrays+=1
  return self.torch.from_numpy(np.array(array,dtype=np.float32,order='C',copy=True))

def features(d,tokens):
 """Each yielded stage consumes the quantized weight sent back by the caller."""
 t=d.torch;cfg=d.config;n=len(tokens);heads=cfg.head_count;hd=cfg.model_width//heads
 x=d.embeddings[list(tokens)]+d.positions[:n]
 mask=t.triu(t.ones((n,n),dtype=t.bool),diagonal=1)
 for i,b in enumerate(d.blocks):
  stem='block.%04d.'%i
  value=d.norm(x,b['norm1_scale'],b['norm1_bias']);w=yield stem+'qkv',value
  qkv=value@w.T+b['qkv_bias']
  q,k,v=[a.reshape(n,heads,hd).permute(1,0,2) for a in qkv.chunk(3,dim=1)]
  score=(q@k.transpose(1,2)/math.sqrt(hd)).masked_fill(mask,float('-inf'));score=score-score.max(dim=-1,keepdim=True).values
  prob=t.exp(score);prob=prob/prob.sum(dim=-1,keepdim=True)
  value=(prob@v).permute(1,0,2).reshape(n,cfg.model_width);w=yield stem+'attn_out',value
  x=x+(value@w.T+b['attn_out_bias'])
  value=d.norm(x,b['norm2_scale'],b['norm2_bias']);w=yield stem+'mlp_up',value
  up=value@w.T+b['mlp_up_bias'];c=float.fromhex('0x1.9884533d43651p-1')
  value=(0.5*up)*(1+t.tanh(c*(up+((0.044715*up)*up)*up)));w=yield stem+'mlp_down',value
  x=x+(value@w.T+b['mlp_down_bias'])
 return d.norm(x,d.final_scale,d.final_bias)@d.head.T+d.head_bias

def consume_original(d,tokens):
 stream=features(d,tokens);sid,x=next(stream);seen=[]
 while True:
  seen.append(sid)
  try:sid,x=stream.send(d.weights[sid])
  except StopIteration as e:return e.value,seen

def quantize_matrix(weight,inputs):
 import torch
 GPTQ,Quantizer=reference();layer=torch.nn.Linear(weight.shape[1],weight.shape[0],bias=False,device='cpu',dtype=torch.float32)
 layer.weight.data.copy_(weight);g=GPTQ(layer);g.quantizer=Quantizer();g.quantizer.configure(bits=4,perchannel=True,sym=True,mse=False)
 for x in inputs:g.add_batch(x.unsqueeze(0),None)
 g.fasterquant(blocksize=128,percdamp=.01,groupsize=-1,actorder=False,static_groups=False)
 q=layer.weight.detach().clone();scale=g.quantizer.scale.detach().clone();zero=g.quantizer.zero.detach().clone()
 assert q.dtype==torch.float32 and torch.isfinite(q).all() and torch.isfinite(scale).all() and torch.all(scale>0) and torch.all(zero==8)
 idx=torch.clamp(torch.round(q/scale)+zero,0,15)
 # Grid reconstruction uses the upstream binary32 multiply.
 assert torch.equal(q,scale*(idx-zero))
 g.free();assert not torch.cuda.is_initialized()
 return q,{'scale':scale.numpy().tolist(),'zero':zero.numpy().tolist(),'nsamples':len(inputs),'grid_words_sha256':hashlib.sha256(q.numpy().astype('<f4').tobytes()).hexdigest()}
