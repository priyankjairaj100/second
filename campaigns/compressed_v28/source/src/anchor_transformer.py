"""Canonical finite transformer anchors and summary-only perturbation bounds.

Anchor leaves require trusted provenance. Hashes detect changed bytes; they do
not authenticate execution. Bounds never access tokens or reexecute features.
Every persistent node stores scalar summaries, not retained operand arrays.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from fractions import Fraction as Q
import base64
import hashlib
import json
import math
from pathlib import Path
import numpy as np

from .anchor_affine import (AffineAnchor, prepare_affine_anchor,
    prepare_affine_change, enclose_affine_output)
from .compact_state import StageCodes, prefix_digest, _name, _digest
from .dyadic_row_quantizer import _grid_arrays
from .finite_feature_boxes import FloatBox, _freeze, _runtime
from .finite_primitives import primitive_scope, rounded
from .ordered_finite import FiniteWeights

_U=Q(1,2**53)
_ETA=Q(1,2**1074)
_MAX=Q.from_float(float.fromhex('0x1.fffffffffffffp+1023'))
_SCHEMA='finite-anchor-summary-v20'
_DEFAULT_BYTES=256*1024*1024
_DEFAULT_NODES=2_000_000
_DEFAULT_VALUES=32_000_000
_DEFAULT_TOKENS=4096


class AnchorBoundUnresolved(ArithmeticError):
    """The summaries cannot prove a finite feature enclosure."""


def _q(x):return Q.from_float(float(x))
def _json(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def _sha(x):return hashlib.sha256(x).hexdigest()
def decoder_binding(decoder):return _sha(_json(decoder.kernel_manifest))
def provider_binding():
    root=Path(__file__).parent
    names=('anchor_transformer.py','anchor_affine.py','finite_feature_boxes.py','finite_primitives.py')
    return _sha(_json({n:_sha((root/n).read_bytes()) for n in names}))


def _up_q(value):
    """Round a nonnegative bound upward to binary64; limit stored bit growth."""
    if value<0 or value>_MAX:raise AnchorBoundUnresolved('finite bound is outside the supported range')
    f=float(value)
    if _q(f)<value:f=float(np.nextafter(f,np.inf))
    if not math.isfinite(f):raise AnchorBoundUnresolved('finite bound overflow')
    return _q(f)


def _rn_difference(delta,magnitude):
    if not delta:return Q(0)
    if magnitude+delta>_MAX:raise AnchorBoundUnresolved('cannot exclude finite operation overflow')
    return _up_q(delta+_U*(2*magnitude+delta)+2*_ETA)


def _float_upper(q):
    if abs(q)>_MAX:raise AnchorBoundUnresolved('primitive argument bound overflow')
    f=float(q)
    if _q(f)<q:f=float(np.nextafter(f,np.inf))
    if not math.isfinite(f):raise AnchorBoundUnresolved('primitive argument bound overflow')
    return f


def _real_primitive_upper(name,q):
    f=rounded(name,_float_upper(q))
    if not math.isfinite(f):raise AnchorBoundUnresolved('primitive result bound overflow')
    return (_q(abs(f))+_ETA)/(1-_U)


@dataclass(frozen=True)
class SummaryNode:
    op:str
    parents:tuple
    minimum:float
    maximum:float
    minimum_absolute:float
    extra:object=None
    @property
    def magnitude(self):return max(abs(self.minimum),abs(self.maximum))


@dataclass(frozen=True,eq=False)
class AnchorRecord:
    record_id:str
    tokens:tuple
    target_sha256:str
    decoder_sha256:str
    provider_sha256:str
    anchor_sha256:str
    nodes:tuple
    factors:tuple
    affines:tuple


@dataclass
class AnchorContext:
    target_sha256:str
    decoder_sha256:str
    provider_sha256:str
    anchor_sha256:str
    anchor_codes:tuple
    anchor_matrices:tuple
    biases:tuple
    changes:dict=field(default_factory=dict)
    initial_matrix_values:int=0


def prepare_context(decoder,target):
    """Prepare fixed nearest codes once. Reuse across all records in a request."""
    _runtime()
    if tuple(s.stage_id for s in target.stages)!=tuple(decoder.stage_ids):
        raise ValueError('target must contain the complete decoder stage order')
    codes=[];matrices=[];biases=[];values=0
    for i,stage in enumerate(target.stages):
        if set(stage.dependencies)!=set(decoder.stage_ids[:i]) or len(stage.dependencies)!=i:
            raise ValueError('target dependencies must equal the complete ancestor prefix')
        if not hasattr(stage,'scale_values'):raise ValueError('anchor requires fixed dyadic row grids')
        weights=FiniteWeights(stage.weights).array()
        grid,boundaries=_grid_arrays(stage.scale_values,stage.bits)
        if len(grid)!=weights.shape[0]:raise ValueError('invalid row grids')
        # The target uses lower-code midpoint ties. All boundaries are exact.
        nearest=np.empty_like(weights)
        for row in range(weights.shape[0]):
            nearest[row]=grid[row,np.searchsorted(boundaries[row],weights[row],side='left')]
        code=StageCodes.from_array(stage.stage_id,nearest,grid_axis='dyadic_row',bits=stage.bits,scale_values=stage.scale_values)
        codes.append(code);matrices.append(_freeze(nearest));values+=weights.size
        block,name=stage.stage_id.split('.')[1:]
        biases.append(_freeze(np.asarray(decoder.base._blocks[int(block)][name+'_bias'],dtype=np.float64)))
    return AnchorContext(target.digest,decoder_binding(decoder),provider_binding(),
        prefix_digest(target.digest,tuple(codes)),tuple(codes),tuple(matrices),tuple(biases),initial_matrix_values=values)


def _context(decoder,target,context):
    c=prepare_context(decoder,target) if context is None else context
    if type(c) is not AnchorContext or (c.target_sha256,c.decoder_sha256,c.provider_sha256)!=(target.digest,decoder_binding(decoder),provider_binding()):
        raise ValueError('foreign or stale anchor context')
    return c


class _Value:
    def __init__(self,tape,index,value):self.tape=tape;self.index=index;self.value=value
    def _coerce(self,v):return v if type(v) is _Value else self.tape.constant(v)
    def __add__(self,b):return self.tape.operation('add',self,self._coerce(b))
    __radd__=__add__
    def __sub__(self,b):return self.tape.operation('sub',self,self._coerce(b))
    def __mul__(self,b):return self.tape.operation('mul',self,self._coerce(b))
    __rmul__=__mul__
    def __truediv__(self,b):return self.tape.operation('div',self,self._coerce(b))
    def __getitem__(self,key):return self.tape.add('copy',(self.index,),self.value[key])
    def primitive(self,name):return self.tape.operation(name,self)
    @property
    def shape(self):return self.value.shape


class _Tape:
    def __init__(self,max_nodes):self.nodes=[];self.affines=[];self.max_nodes=max_nodes
    def add(self,op,parents,value,extra=None):
        if len(self.nodes)>=self.max_nodes:raise AnchorBoundUnresolved('anchor node budget exceeded')
        value=np.asarray(value,dtype=np.float64)
        if value.size==0 or not np.isfinite(value).all():raise AnchorBoundUnresolved('nonfinite or empty anchor intermediate')
        node=SummaryNode(op,tuple(parents),float(np.min(value)),float(np.max(value)),float(np.min(np.abs(value))),extra)
        self.nodes.append(node)
        return _Value(self,len(self.nodes)-1,value)
    def constant(self,value):return self.add('constant',(),value)
    def operation(self,op,*args):
        xs=[v.value for v in args]
        with np.errstate(over='raise',invalid='raise',divide='raise',under='ignore'):
            if op in ('add','sub','mul','div'):
                y={'add':np.add,'sub':np.subtract,'mul':np.multiply,'div':np.divide}[op](*xs)
            elif op=='max':y=np.max(xs[0],axis=-1)
            else:y=np.fromiter((rounded(op,float(x)) for x in xs[0].flat),dtype=np.float64,count=xs[0].size).reshape(xs[0].shape)
        return self.add(op,tuple(v.index for v in args),y)
    def affine(self,value,index,context):
        anchor=prepare_affine_anchor(value.value,context.anchor_matrices[index],context.biases[index])
        # The output is transient. Scalar propagation does not read this field.
        summary=AffineAnchor(anchor.weight_sha256,anchor.bias_sha256,anchor.weight_shape,
            anchor.input_maxima,anchor.product_maxima,anchor.accumulator_maxima,_freeze(np.zeros((0,0))))
        self.affines.append((index,summary))
        return self.add('affine',(value.index,),anchor.output,len(self.affines)-1)
    def concatenate(self,values,axis=0,stack=False):
        fn=np.stack if stack else np.concatenate
        return self.add('join',tuple(v.index for v in values),fn([v.value for v in values],axis=axis))


def _sum(value):
    total=value.tape.constant(np.zeros(value.shape[:-1]))
    for i in range(value.shape[-1]):total=total+value[...,i]
    return total


def _norm(value,scale,bias,epsilon):
    mean=_sum(value)/value.shape[-1]
    centered=value-mean[:,None]
    variance=_sum(centered*centered)/value.shape[-1]
    denominator=(variance+float(epsilon)).primitive('sqrt')
    return (centered/denominator[:,None])*np.asarray(scale,dtype=np.float64)+np.asarray(bias,dtype=np.float64)


def _attention(value,width,heads):
    tape=value.tape;hd=width//heads
    divisor=tape.constant(hd).primitive('sqrt');rows=[]
    for token in range(value.shape[0]):
        row=[]
        for head in range(heads):
            start=head*hd
            query=value[token,start:start+hd]
            keys=value[:token+1,width+start:width+start+hd]
            scores=_sum(query*keys)/divisor
            maximum=tape.operation('max',scores)
            terms=(scores-maximum).primitive('exp')
            probabilities=terms/_sum(terms)
            values=value[:token+1,2*width+start:2*width+start+hd]
            mixed=tape.constant(np.zeros(hd))
            for key in range(token+1):mixed=mixed+probabilities[key]*values[key]
            row.append(mixed)
        rows.append(tape.concatenate(row))
    return tape.concatenate(rows,stack=True)


def _activation(value,name):
    if name=='gelu':
        divisor=value.tape.constant(2).primitive('sqrt')
        return (.5*value)*(1+(value/divisor).primitive('erf'))
    if name!='gelu_new':raise ValueError('unsupported activation')
    coefficient=float.fromhex('0x1.9884533d43651p-1')
    return (.5*value)*(1+(coefficient*(value+0.044715*value*value*value)).primitive('tanh'))


def prepare_anchor(decoder,target,record,*,context=None,max_nodes=_DEFAULT_NODES):
    """Execute each finite anchor stage once; retain canonical scalar summaries."""
    _runtime();c=_context(decoder,target,context)
    if type(record) is not dict or set(record)!={'id','tokens'}:raise ValueError('record requires id and tokens')
    rid=_name(record['id']);tokens=decoder.base._tokens(record['tokens'])
    if len(tokens)>_DEFAULT_TOKENS:raise ValueError('anchor token budget exceeded')
    if type(max_nodes) is not int or max_nodes<1 or max_nodes>_DEFAULT_NODES:raise ValueError('invalid node budget')
    tape=_Tape(max_nodes);factors=[];base=decoder.base;cfg=decoder.config
    def save(sid,value):factors.append((sid,value.index,_freeze(value.value)))
    with primitive_scope(decoder.primitive_backend):
        hidden=tape.constant([base._token_embeddings[t] for t in tokens])+tape.constant([base._position_embeddings[p] for p in range(len(tokens))])
        for block_index,block in enumerate(base._blocks):
            index=4*block_index;prefix=f'block.{block_index:04d}.'
            norm=_norm(hidden,block['norm1_scale'],block['norm1_bias'],cfg.layernorm_epsilon)
            save(prefix+'qkv',norm)
            qkv=tape.affine(norm,index,c)
            mixed=_attention(qkv,cfg.model_width,cfg.head_count)
            save(prefix+'attn_out',mixed)
            hidden=hidden+tape.affine(mixed,index+1,c)
            norm=_norm(hidden,block['norm2_scale'],block['norm2_bias'],cfg.layernorm_epsilon)
            save(prefix+'mlp_up',norm)
            up=tape.affine(norm,index+2,c)
            activated=_activation(up,cfg.activation)
            save(prefix+'mlp_down',activated)
            if block_index+1<len(base._blocks):hidden=hidden+tape.affine(activated,index+3,c)
    if sum(v.size for _,_,v in factors)>_DEFAULT_VALUES:raise AnchorBoundUnresolved('anchor factor budget exceeded')
    return AnchorRecord(rid,tuple(tokens),target.digest,c.decoder_sha256,c.provider_sha256,c.anchor_sha256,
        tuple(tape.nodes),tuple(factors),tuple(tape.affines))


def _node_error(node,nodes,errors):
    if node.op=='constant':return Q(0)
    ds=[errors[p] for p in node.parents]
    if not any(ds):return Q(0)
    if node.op in ('copy','join','max'):return max(ds)
    args=[nodes[p] for p in node.parents]
    a=args[0];da=ds[0];ma=_q(a.magnitude)
    if node.op in ('add','sub','mul','div'):
        b=args[1];db=ds[1];mb=_q(b.magnitude)
        if node.op in ('add','sub'):return _rn_difference(da+db,ma+mb)
        if node.op=='mul':return _rn_difference(ma*db+mb*da+da*db,ma*mb)
        m=_q(b.minimum_absolute)
        if m<=db:raise AnchorBoundUnresolved('anchor bound cannot exclude a zero denominator')
        delta=da/(m-db)+ma*db/(m*(m-db))
        return _rn_difference(delta,ma/m)
    # Certified primitive bounds concern the declared rounded operation.
    if node.op=='tanh':delta=da;real_max=Q(1)
    elif node.op=='erf':delta=2*da;real_max=Q(1)
    elif node.op=='exp':
        real_max=_real_primitive_upper('exp',_q(a.maximum)+da)
        delta=real_max*da
    elif node.op=='sqrt':
        lower=_q(a.minimum)-da
        if lower<0:raise AnchorBoundUnresolved('anchor square-root range contains negative arguments')
        real_max=_real_primitive_upper('sqrt',_q(a.maximum)+da)
        if lower==0:delta=_real_primitive_upper('sqrt',da)
        else:
            # float(lower) may round upward. Correct its argument downward first.
            x=float(lower)
            if _q(x)>lower:x=float(np.nextafter(x,-np.inf))
            f=rounded('sqrt',x)
            root_lower=max(Q(0),(_q(f)-_ETA)/(1+_U))
            if not root_lower:delta=_real_primitive_upper('sqrt',da)
            else:delta=da/(2*root_lower)
    else:raise ValueError('unknown anchor operation')
    if real_max>_MAX:raise AnchorBoundUnresolved('primitive bound cannot exclude overflow')
    return _up_q(delta+2*_U*real_max+2*_ETA)


def _affine_bound(summary,change,bias,input_error):
    """Affine recurrence with upward rounding after each bound operation."""
    if change.anchor_weight_sha256!=summary.weight_sha256 or change.shape!=summary.weight_shape:
        raise ValueError('affine summary binding mismatch')
    if (type(bias) is not np.ndarray or bias.dtype!=np.float64
            or bias.shape!=(summary.weight_shape[0],) or not np.isfinite(bias).all()
            or _sha(str(bias.shape).encode()+bias.astype('<f8',copy=False).tobytes())!=summary.bias_sha256):
        raise ValueError('fixed affine bias binding mismatch')
    accum=Q(0)
    for i in range(summary.weight_shape[1]):
        delta=change.target_column_maxima[i]*input_error+change.difference_column_maxima[i]*_q(summary.input_maxima[i])
        magnitude=(_q(summary.product_maxima[i])+_ETA)/(1-_U)
        product=_rn_difference(delta,magnitude)
        magnitude=_q(summary.accumulator_maxima[i])+_q(summary.product_maxima[i])
        accum=_rn_difference(accum+product,magnitude)
    magnitude=_q(summary.accumulator_maxima[-1])+max(_q(abs(v)) for v in bias)
    return _rn_difference(accum,magnitude)


def bound_stage(decoder,target,anchor,prefix,stage_id,*,context=None,diagnostics=None):
    """Bound one stage from stored summaries. Never read record token values."""
    _runtime();c=_context(decoder,target,context)
    if type(anchor) is not AnchorRecord:raise TypeError('trusted anchor record required')
    if (anchor.target_sha256,anchor.decoder_sha256,anchor.provider_sha256,anchor.anchor_sha256)!=(target.digest,c.decoder_sha256,c.provider_sha256,c.anchor_sha256):
        raise ValueError('anchor binding mismatch')
    try:index=tuple(s.stage_id for s in target.stages).index(stage_id)
    except ValueError as exc:raise ValueError('unknown requested stage') from exc
    prefix=tuple(prefix)
    if len(prefix)!=index:raise ValueError('complete exact ancestor prefix required')
    for j,code in enumerate(prefix):
        old=c.anchor_codes[j]
        if type(code) is not StageCodes or (code.stage_id,code.shape,code.grid_axis,code.bits,code.scale_values)!=(old.stage_id,old.shape,old.grid_axis,old.bits,old.scale_values):
            raise ValueError('ancestor stage grid binding mismatch')
    metrics={'scalar_nodes':0,'affine_bound_coordinates':0,'matrix_scan_values':0,'output_box_values':0,'retained_dot_products':0,'retained_token_reads':0}
    sid,stop,output=anchor.factors[index]
    if sid!=stage_id:raise ValueError('anchor factor order mismatch')
    errors=[]
    try:
        with primitive_scope(decoder.primitive_backend):
            for node in anchor.nodes[:stop+1]:
                metrics['scalar_nodes']+=1
                if node.op=='affine':
                    j,summary=anchor.affines[node.extra]
                    if j>=index:raise ValueError('anchor tape uses an unprovided ancestor')
                    key=(j,prefix[j].digest)
                    if key not in c.changes:
                        c.changes[key]=prepare_affine_change(c.anchor_matrices[j],prefix[j].array())
                        metrics['matrix_scan_values']+=c.anchor_matrices[j].size
                    metrics['affine_bound_coordinates']+=summary.weight_shape[1]
                    error=_affine_bound(summary,c.changes[key],c.biases[j],errors[node.parents[0]])
                else:error=_node_error(node,anchor.nodes,errors)
                errors.append(error)
        metrics['output_box_values']=output.size
        # This wrapper only needs output. Other fields do not enter enclosure.
        holder=AffineAnchor('','',(),(),(),(),output)
        return enclose_affine_output(holder,errors[stop])
    except ArithmeticError as exc:
        raise AnchorBoundUnresolved(str(exc)) from exc
    finally:
        if diagnostics is not None:diagnostics.update(metrics)


def anchor_factor(anchor,stage_id):
    """Return one immutable token-major factor from the fixed anchor."""
    if type(anchor) is not AnchorRecord:raise TypeError('trusted anchor record required')
    for sid,_,value in anchor.factors:
        if sid==stage_id:return value
    raise ValueError('unknown anchor stage')


def _array_payload(array):
    return {'shape':list(array.shape),'binary64_le':base64.b64encode(array.astype('<f8',copy=False).tobytes()).decode('ascii')}


def _payload(anchor):
    return dict(schema=_SCHEMA,record_id=anchor.record_id,tokens=list(anchor.tokens),
        target_sha256=anchor.target_sha256,decoder_sha256=anchor.decoder_sha256,
        provider_sha256=anchor.provider_sha256,anchor_sha256=anchor.anchor_sha256,
        nodes=[[n.op,list(n.parents),n.minimum.hex(),n.maximum.hex(),n.minimum_absolute.hex(),n.extra] for n in anchor.nodes],
        factors=[[sid,index,_array_payload(value)] for sid,index,value in anchor.factors],
        affines=[[i,dict(weight_sha256=a.weight_sha256,bias_sha256=a.bias_sha256,weight_shape=list(a.weight_shape),
            input_maxima=[x.hex() for x in a.input_maxima],product_maxima=[x.hex() for x in a.product_maxima],
            accumulator_maxima=[x.hex() for x in a.accumulator_maxima])] for i,a in anchor.affines])


def encode_anchor(anchor):
    if type(anchor) is not AnchorRecord:raise TypeError('anchor record required')
    raw=_json(_payload(anchor))
    if len(raw)>_DEFAULT_BYTES:raise ValueError('anchor byte budget exceeded')
    return raw


def decode_anchor(data,*,max_bytes=_DEFAULT_BYTES,max_nodes=_DEFAULT_NODES,max_values=_DEFAULT_VALUES,max_tokens=_DEFAULT_TOKENS):
    """Parse canonical trusted leaves with explicit allocation and graph limits."""
    for limit in (max_bytes,max_nodes,max_values,max_tokens):
        if type(limit) is not int or limit<1:raise ValueError('positive parse limits required')
    if type(data) is not bytes or len(data)>max_bytes:raise ValueError('anchor byte budget exceeded')
    try:p=json.loads(data)
    except (ValueError,RecursionError) as exc:raise ValueError('invalid anchor JSON') from exc
    required={'schema','record_id','tokens','target_sha256','decoder_sha256','provider_sha256','anchor_sha256','nodes','factors','affines'}
    if type(p) is not dict or set(p)!=required or p['schema']!=_SCHEMA:raise ValueError('invalid anchor schema')
    _name(p['record_id'])
    for name in ('target_sha256','decoder_sha256','provider_sha256','anchor_sha256'):_digest(p[name])
    tokens=p['tokens']
    if type(tokens) is not list or not 1<=len(tokens)<=max_tokens or any(type(t) is not int or not 0<=t<2**64 for t in tokens):raise ValueError('invalid anchor tokens')
    if type(p['nodes']) is not list or not 1<=len(p['nodes'])<=max_nodes:raise ValueError('anchor node budget exceeded')
    def finite(text):
        if type(text) is not str or len(text)>32:raise ValueError('invalid scalar encoding')
        f=float.fromhex(text)
        if not math.isfinite(f) or f.hex()!=text:raise ValueError('noncanonical finite scalar')
        return f
    nodes=[]
    arity={'constant':0,'copy':1,'max':1,'add':2,'sub':2,'mul':2,'div':2,'sqrt':1,'exp':1,'erf':1,'tanh':1,'affine':1}
    for i,row in enumerate(p['nodes']):
        if type(row) is not list or len(row)!=6:raise ValueError('invalid anchor node')
        op,parents,lo,hi,minimum,extra=row
        if op not in arity and op!='join':raise ValueError('invalid anchor operation')
        if type(parents) is not list or (len(parents)!=arity.get(op,len(parents))) or (op=='join' and not parents):raise ValueError('invalid anchor arity')
        if any(type(j) is not int or not 0<=j<i for j in parents):raise ValueError('anchor graph must be topologically ordered')
        lo,hi,minimum=finite(lo),finite(hi),finite(minimum)
        if lo>hi or minimum<0 or minimum>max(abs(lo),abs(hi)):raise ValueError('invalid anchor extrema')
        if (op=='affine' and (type(extra) is not int or extra<0)) or (op!='affine' and extra is not None):raise ValueError('invalid node metadata')
        nodes.append(SummaryNode(op,tuple(parents),lo,hi,minimum,extra))
    affines=[]
    for row in p['affines']:
        if type(row) is not list or len(row)!=2:raise ValueError('invalid affine summary')
        i,a=row
        keys={'weight_sha256','bias_sha256','weight_shape','input_maxima','product_maxima','accumulator_maxima'}
        if type(i) is not int or i<0 or type(a) is not dict or set(a)!=keys:raise ValueError('invalid affine summary')
        _digest(a['weight_sha256']);_digest(a['bias_sha256']);shape=a['weight_shape']
        if type(shape) is not list or len(shape)!=2 or any(type(x) is not int or not 1<=x<=2**20 for x in shape):raise ValueError('invalid affine dimensions')
        groups=[tuple(finite(x) for x in a[k]) for k in ('input_maxima','product_maxima','accumulator_maxima')]
        if tuple(map(len,groups))!=(shape[1],shape[1],shape[1]+1) or any(x<0 for g in groups for x in g):raise ValueError('invalid affine maxima')
        affines.append((i,AffineAnchor(a['weight_sha256'],a['bias_sha256'],tuple(shape),*groups,_freeze(np.zeros((0,0))))))
    if any(n.op=='affine' and n.extra>=len(affines) for n in nodes):raise ValueError('missing affine summary')
    factors=[];count=0
    for row in p['factors']:
        if type(row) is not list or len(row)!=3:raise ValueError('invalid anchor factor')
        sid,index,a=row;_name(sid)
        if type(index) is not int or not 0<=index<len(nodes):raise ValueError('invalid factor node')
        if type(a) is not dict or set(a)!={'shape','binary64_le'}:raise ValueError('invalid factor array')
        shape=a['shape']
        if type(shape) is not list or len(shape)!=2 or shape[0]!=len(tokens) or any(type(x) is not int or x<1 for x in shape):raise ValueError('invalid factor dimensions')
        size=math.prod(shape);count+=size
        if count>max_values:raise ValueError('anchor factor budget exceeded')
        encoded=a['binary64_le']
        if type(encoded) is not str or len(encoded)!=4*((8*size+2)//3):raise ValueError('invalid factor byte length')
        raw=base64.b64decode(encoded,validate=True)
        if len(raw)!=8*size:raise ValueError('invalid factor bytes')
        value=np.frombuffer(raw,dtype='<f8').reshape(shape)
        if not np.isfinite(value).all():raise ValueError('nonfinite anchor factor')
        factors.append((sid,index,_freeze(value)))
    if not factors or len({s for s,_,_ in factors})!=len(factors):raise ValueError('invalid factor stage list')
    anchor=AnchorRecord(p['record_id'],tuple(tokens),p['target_sha256'],p['decoder_sha256'],p['provider_sha256'],p['anchor_sha256'],tuple(nodes),tuple(factors),tuple(affines))
    if encode_anchor(anchor)!=data:raise ValueError('anchor encoding is not canonical')
    return anchor
