"""Generated cases against actual frozen native kernels and dispatch routes."""
import ctypes,itertools,random,hashlib
from fractions import Fraction as Q
from types import SimpleNamespace
import numpy as np
from research_v140.reference import rational,quantize,coefficient
from research_v43.dispatcher import StageSpec,solve_blocks,DispatchRefused
from src.dyadic_row_quantizer import dyadic_row_scales
from src import native_box_certificate as interval
from src import native_token_coefficients_v30 as point_coeff
from src import native_box_coefficients_v31 as box_coeff
from src.low_rank_certified import LowRankUnresolved
from src.token_box_certificate import TokenBoxUnresolved

def spec(w,ridge=Q(10),normalization=Q(512)):
 return StageSpec.from_stage(SimpleNamespace(stage_id='v140.synthetic',weights=w,
   scale_values=dyadic_row_scales(w),ridge=ridge,normalization=normalization,bits=4),target_sha256='1'*64)

def realizations(lo,hi):
 for mask in itertools.product((False,True),repeat=lo.size):
  yield np.where(np.asarray(mask).reshape(lo.shape),hi,lo)
 for a in (.25,.5,.75):yield lo+a*(hi-lo)

def check_codes(c,w,x,s):
 expected=quantize(w,x,s.scale_values,s.ridge,s.normalization)
 assert c.tolist()==[[float(v) for v in row] for row in expected], 'native code disagrees with conditional minimization'

def run():
 rng=random.Random(14020261102);out={'seed':14020261102,'cases':[],'failures':0,'empirical_model_result':False}
 def record(family,**kw):out['cases'].append(dict(family=family,**kw))
 ptr=ctypes.POINTER(ctypes.c_double)
 builds={'interval':interval.prepare_native_box(),'point_coefficients':point_coeff.prepare_native_token_coefficients(),'box_coefficients':box_coeff.prepare_native_box_coefficients()}
 # Fixed binary64 boundary regimes and deterministic generated interval products.
 tiny=np.nextafter(0.,1.);largest=np.finfo(np.float64).max
 fixed=[(tiny,2*tiny,-tiny,tiny),(1.,1.,-1.,-1.),(-0.,0.,-1.,1.),(largest,largest,largest,largest),(1.,2.,-2.,-1.)]
 exponents=(-1074,-1022,-540,-100,-1,0,1,100,500,1000)
 for _ in range(96):
  a=sorted(float(np.ldexp(rng.choice((-1.,1.)),rng.choice(exponents))) for _ in range(2))
  b=sorted(float(np.ldexp(rng.choice((-1.,1.)),rng.choice(exponents))) for _ in range(2))
  fixed.append(tuple(a+b))
 for idx,vals in enumerate(fixed):
  for op in (0,1):
   v=np.array(vals);r=np.empty(2);status=interval._NATIVE.nbc_probe(op,v.ctypes.data_as(ptr),r.ctypes.data_as(ptr));assert status in (0,3)
   if status==0:
    for a,b in itertools.product(vals[:2],vals[2:]):
     exact=rational(a)+rational(b) if op==0 else rational(a)*rational(b)
     assert rational(r[0])<=exact<=rational(r[1])
   record('native_add_multiply',index=idx,operation=op,status=status,input_hex=[float(v).hex() for v in vals])
 # Suffix coefficients: independent exact linear systems, including underflow scales.
 for idx in range(36):
  d=2+idx%3;t=1+idx%3;beta=(Q(1,1000),Q(1),Q(30))[idx%3]
  x=np.array([[rng.randint(-8,8)/8 for _ in range(t)] for _ in range(d)],dtype=np.float64)
  if idx in (0,1):x*=2.**-535
  a=point_coeff.native_token_coefficient_enclosures(x,beta)
  for i in range(d):
   e=coefficient(x,i,beta);error=sum(((u-rational(v))**2 for u,v in zip(e,a.coefficients[i])),Q(0));assert error<=rational(a.errors[i])
  record('point_coefficient_containment',index=idx,width=d,tokens=t,coordinates=d)
 for idx in range(12):
  lo=np.array([[rng.randint(-4,4)/8 for _ in range(2)] for _ in range(2)],dtype=np.float64);hi=lo+(2.**-24 if idx<6 else .125);beta=Q(1+idx)
  a=box_coeff.native_box_coefficient_enclosures(lo,hi,beta);count=0
  for x in realizations(lo,hi):
   for i in range(2):
    e=coefficient(x,i,beta);error=sum(((u-rational(v))**2 for u,v in zip(e,a.coefficients[i])),Q(0));assert error<=rational(a.errors[i])
   count+=1
  record('box_coefficient_containment',index=idx,realizations=count,coordinates=2)
 # Full production dispatch, both routes. Refusal is allowed, wrong acceptance is not.
 for idx in range(48):
  d=2+idx%4;t=(0,1,2,4)[(idx//4)%4]
  w=np.array([[rng.randint(-28,28)/4 for _ in range(d)] for _ in range(2)],dtype=np.float64);w[:,-1]=7.
  x=np.array([[rng.randint(-8,8)/8 for _ in range(t)] for _ in range(d)],dtype=np.float64)
  s=spec(w,ridge=(Q(1,100),Q(1),Q(10))[idx%3])
  for route in ('token','streamed'):
   try:
    a=solve_blocks(s,w,[(x,x)] if t else [],total_tokens=t,block_tokens=max(1,t),max_blocks=1,route=route)
    check_codes(a.codes,w,x,s);status='accepted'
   except DispatchRefused:status='refused'
   record('point_dispatch',index=idx,route=route,status=status,width=d,tokens=t)
 for idx in range(24):
  w=np.array([[rng.randint(-28,28)/4,7.]],dtype=np.float64)
  lo=np.array([[rng.randint(-4,4)/8 for _ in range(2)] for _ in range(2)],dtype=np.float64);hi=lo+(2.**-30 if idx<12 else .5);s=spec(w,ridge=Q(1))
  samples=list(realizations(lo,hi))
  ref=[quantize(w,x,s.scale_values,s.ridge,s.normalization) for x in samples];ambiguous=any(x!=ref[0] for x in ref)
  for route in ('token','streamed'):
   try:
    a=solve_blocks(s,w,[(lo,hi)],total_tokens=2,block_tokens=2,max_blocks=1,kind='box',route=route)
    assert not ambiguous
    for x in samples:check_codes(a.codes,w,x,s)
    status='accepted'
   except DispatchRefused:status='refused'
   record('box_dispatch',index=idx,route=route,status=status,realizations=len(samples),sampled_oracle_disagreement=ambiguous)
 # Explicit ties, near ties, saturation by conditional correction, subnormals and cancellation.
 fixtures=[('ties',np.array([[.5,-.5,7.]]),np.zeros((3,1)),Q(1)),
 ('near_ties',np.array([[np.nextafter(.5,0.),np.nextafter(.5,1.),7.]]),np.zeros((3,1)),Q(1)),
 ('saturation',np.array([[.49,7.]]),np.array([[10.],[1.]]),Q(1,1000000)),
 ('subnormal',np.array([[.21,7.]]),np.array([[tiny,-tiny],[2.**-535,-2.**-535]]),Q(10)),
 ('cancellation',np.array([[-.21,7.]]),np.array([[1.,-1.],[-1.,1.]]),Q(10))]
 for name,w,x,beta in fixtures:
  s=spec(w,ridge=beta,normalization=Q(max(1,x.shape[1])))
  for route in ('token','streamed'):
   try:
    a=solve_blocks(s,w,[(x,x)],total_tokens=x.shape[1],block_tokens=x.shape[1],max_blocks=1,route=route);check_codes(a.codes,w,x,s);status='accepted'
   except DispatchRefused:status='refused'
   record('edge_dispatch',name=name,route=route,status=status)
 # Overflow must yield refusal, never a code array.
 w=np.array([[.21,7.]]);x=np.full((2,2),1e200);s=spec(w)
 for route in ('token','streamed'):
  try:solve_blocks(s,w,[(x,x)],total_tokens=2,block_tokens=2,max_blocks=1,route=route)
  except DispatchRefused:record('overflow_dispatch',route=route,status='refused')
  else:raise AssertionError('overflow accepted')
 for route in ('token','streamed'):
  for family in ('point_dispatch','box_dispatch'):
   assert any(c['family']==family and c['route']==route and c['status']=='accepted' for c in out['cases'])
 out['builds']=builds
 out['summary']={family:dict(cases=sum(c['family']==family for c in out['cases']),accepted=sum(c['family']==family and c.get('status')=='accepted' for c in out['cases']),refused=sum(c['family']==family and c.get('status')=='refused' for c in out['cases'])) for family in sorted({c['family'] for c in out['cases']})}
 return out
