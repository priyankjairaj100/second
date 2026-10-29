"""Float64 CUDA translation of the exposed NumPy likelihood evaluator."""
import math
import numpy as np


class TorchQualityDecoder:
    def __init__(self, reference, device='cuda'):
        import torch
        self.torch, self.device = torch, torch.device(device)
        self.reference, self.config = reference, reference.config
        if self.config.activation != 'gelu_new':
            raise ValueError('Only the pinned gelu_new route is admitted')
        self.copied_arrays = 0
        self.weights = {k:self.copy(v) for k,v in reference.weights.items()}
        for name in ('embeddings','positions','head','head_bias','final_scale','final_bias'):
            setattr(self,name,self.copy(getattr(reference,name)))
        self.blocks = [{k:self.copy(v) for k,v in b.items()} for b in reference.blocks]

    def copy(self, array):
        if type(array) is not np.ndarray or array.dtype != np.float64 or not np.isfinite(array).all():
            raise ValueError('Only finite NumPy binary64 tensors are admitted')
        host = np.array(array, dtype=np.float64, order='C', copy=True)
        value = self.torch.from_numpy(host).to(self.device)
        if value.dtype != self.torch.float64 or value.device != self.device:
            # CUDA's unindexed device is equivalent to the current indexed device.
            if not (self.device.type=='cuda' and value.device.type=='cuda'
                    and value.dtype==self.torch.float64 and self.device.index is None):
                raise ValueError('Tensor device or dtype differs')
        if value.cpu().numpy().tobytes() != host.tobytes():
            raise ValueError('Host/device transfer changed binary64 words')
        self.copied_arrays += 1
        return value

    def prefix(self, arrays):
        if set(arrays) != set(self.weights):
            raise ValueError('A complete replacement model is required')
        if any(v.shape != tuple(self.weights[k].shape) for k,v in arrays.items()):
            raise ValueError('Installed model shape differs')
        return {k:self.copy(v) for k,v in arrays.items()}

    def norm(self, x, scale, bias):
        centered = x-x.mean(dim=-1,keepdim=True)
        return centered/self.torch.sqrt((centered*centered).mean(dim=-1,keepdim=True)
            +self.config.layernorm_epsilon)*scale+bias

    def logits(self, tokens, prefix=None):
        t, cfg = self.torch, self.config
        tokens = self.reference.base._tokens(tokens)
        prefix = {} if prefix is None else prefix
        if set(prefix)-set(self.weights):
            raise ValueError('Unknown installed stage')
        n,d,heads = len(tokens),cfg.model_width,cfg.head_count
        hd = d//heads
        x = self.embeddings[list(tokens)]+self.positions[:n]
        mask = t.triu(t.ones((n,n),dtype=t.bool,device=self.device),diagonal=1)
        for index,block in enumerate(self.blocks):
            stem=f'block.{index:04d}.'
            def linear(value,name):
                stage=stem+name
                return value@prefix.get(stage,self.weights[stage]).T+block[name+'_bias']
            qkv=linear(self.norm(x,block['norm1_scale'],block['norm1_bias']),'qkv')
            q,k,v=[part.reshape(n,heads,hd).permute(1,0,2) for part in qkv.chunk(3,dim=1)]
            score=q@k.transpose(1,2)/math.sqrt(hd)
            score=score.masked_fill(mask,float('-inf'))
            score=score-score.max(dim=-1,keepdim=True).values
            prob=t.exp(score);prob=prob/prob.sum(dim=-1,keepdim=True)
            mixed=(prob@v).permute(1,0,2).reshape(n,d)
            x=x+linear(mixed,'attn_out')
            up=linear(self.norm(x,block['norm2_scale'],block['norm2_bias']),'mlp_up')
            c=float.fromhex('0x1.9884533d43651p-1')
            active=(0.5*up)*(1+t.tanh(c*(up+((0.044715*up)*up)*up)))
            x=x+linear(active,'mlp_down')
        logits=self.norm(x,self.final_scale,self.final_bias)@self.head.T+self.head_bias
        if not t.isfinite(logits).all().item():
            raise ArithmeticError('Nonfinite GPU logits')
        return logits

    def nll(self,tokens,prefix=None):
        t=self.torch
        rows=self.logits(tokens,prefix)[:-1]
        maximum=rows.max(dim=1).values
        logsum=maximum+t.log(t.exp(rows-maximum[:,None]).sum(dim=1))
        terms=logsum-rows[t.arange(len(tokens)-1,device=self.device),list(tokens[1:])]
        result=float(terms.sum().item())
        if not math.isfinite(result):
            raise ArithmeticError('Nonfinite GPU likelihood')
        return result


def compare(quality,reference,ids,tolerance=1e-8):
    labels={'full_precision','nearest_rounding','fixed_feature','sequential'}
    if set(quality)!=labels or set(reference)!=labels:
        raise ValueError('All four models are required')
    rows=[]
    for label in sorted(labels):
        for table in (quality[label],reference[label]):
            if len(table)!=len(ids) or {r['id'] for r in table}!=set(ids):
                raise ValueError('Matched article extent differs')
            if any(r['predictions']!=127 or not math.isfinite(r['nll_sum']) for r in table):
                raise ValueError('Invalid likelihood or prediction count')
        old={r['id']:r for r in reference[label]}
        for row in quality[label]:
            delta=abs(row['nll_sum']-old[row['id']]['nll_sum'])/127
            rows.append(dict(model=label,id=row['id'],absolute_mean_nll_deviation=delta,
                threshold=tolerance,passed=delta<=tolerance))
    return dict(passed=all(r['passed'] for r in rows),checks=rows,
        maximum_absolute_mean_nll_deviation=max(r['absolute_mean_nll_deviation'] for r in rows))
