"""Generated-data review checks and arithmetic; no model or cluster execution."""
from pathlib import Path
from fractions import Fraction as F
from itertools import product
import ast,hashlib,json,math,sys,platform
import numpy as np
B=Path(__file__).resolve().parent
R=B.parent
FLAT=(B/'low_rank_certified.py').is_file()
def input_path(relative):
 return B/Path(relative).name if FLAT else R/relative
# Reuse the independently written rational matrix helpers only, not research solvers.
t=ast.parse(input_path('validation/check_mathematics_v121.py').read_text())
names={'tr','mm','inv','dot','add_ridge','ldl'}
ns={'F':F};exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'rational-review-helpers','exec'),ns)
tr,mm,inv,dot,add,ldl=[ns[n] for n in ['tr','mm','inv','dot','add_ridge','ldl']]
# Enumerate small feature boxes and their dyadic interior/edge realizations.
boxes=points=bounds=0
for values in product([-1,0,1],repeat=4):
 C=[[F(v) for v in values[:2]],[F(v) for v in values[2:]]]
 K0=mm(C,tr(C));kappa=sum(abs(v) for row in C for v in row) # certified upper bound on Frobenius norm
 for rad in [F(1,16),F(1,64)]:
  eps=2*rad # exact Frobenius radius for four equal entries
  gamma=2*kappa*eps+eps*eps
  for beta in [F(1,4),F(1),F(4)]:
   c0=K0[0][1]/(beta+K0[1][1]);delta=gamma/beta+abs(K0[0][1])*gamma/(beta*beta);boxes+=1
   for signs in product([-1,0,1],repeat=4):
    X=[[C[i][j]+rad*signs[2*i+j] for j in range(2)] for i in range(2)]
    K=mm(X,tr(X));c=K[0][1]/(beta+K[1][1]);assert abs(c-c0)<=delta
    # Uniform code agreement if center +/- propagated uncertainty fits a cell.
    w=F(2,5);u=w*(1+c0);rho=delta*w
    grid=[F(-1),F(0),F(1)];q=min(grid,key=lambda x:(abs(x-u),x))
    a,b={F(-1):(None,F(-1,2)),F(0):(F(-1,2),F(1,2)),F(1):(F(1,2),None)}[q]
    safe=(a is None or u-rho>a) and (b is None or u+rho<=b)
    if safe:assert min(grid,key=lambda x:(abs(x-w*(1+c)),x))==q;bounds+=1
    points+=1
# Exercise actual elementary Python reference helpers against exact rationals.
# These helpers do not assert Linux execution; this is not native-C qualification.
t=ast.parse(input_path('src/low_rank_certified.py').read_text())
names={'_down','_up','_add','_multiply_point','_norm_squared_upper'}
ns={'np':np};exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'frozen-reference-primitives','exec'),ns)
vals=[0.,-0.,2.**-1074,-2.**-1074,2.**-1022,2.**-500,1.,math.nextafter(1.,math.inf),-1.,2.**500,float.fromhex('0x1.fffffffffffffp+1023')]
checked=refused=0
with np.errstate(all='ignore'):
 for a,b in product(vals,repeat=2):
  for op,truth in [(0,F.from_float(a)+F.from_float(b)),(1,F.from_float(a)*F.from_float(b))]:
   lo,hi=ns['_add'](np.float64(a),np.float64(a),np.float64(b),np.float64(b)) if op==0 else ns['_multiply_point'](np.float64(a),np.float64(a),np.float64(b))
   if math.isfinite(float(lo)) and math.isfinite(float(hi)):
    assert F.from_float(float(lo))<=truth<=F.from_float(float(hi));checked+=1
   else:refused+=1
 for a,b in product(vals[:-1],repeat=2):
  v=np.array([a,b]);u=float(ns['_norm_squared_upper'](v,v))
  if math.isfinite(u):assert F.from_float(a)**2+F.from_float(b)**2<=F.from_float(u);checked+=1
  else:refused+=1
r=json.loads(input_path('reports/review-service-v70/E16_comparison_and_costs.json').read_text())
by={(x['arm'],x['step']):x for x in r['rows']};I=23870575
economics=[]
for st in [1,2]:
 delta=by['modern',st]['live_state_bytes']-by['compressed',st]['live_state_bytes']
 economics.append(dict(retained_records=by['modern',st]['retained_records'],gross_saved_bytes=delta,codec_bytes=I,net_single_state_bytes=delta-I,net_two_separate_states_shared_codec_bytes=2*delta-I,minimum_states_for_positive_net_saving=I//delta+1))
report=dict(schema='second-review-response-checks-v122',feature_boxes=boxes,enumerated_feature_realizations=points,coefficient_perturbation_checks=points,certified_uniform_code_cases=bounds,reference_primitive_exact_containment_checks=checked,nonfinite_cases_requiring_refusal=refused,storage_installation_sensitivity=economics,
 scope='Generated exact-rational and Python elementary-helper checks only; not Linux native-C qualification, model results, production transaction tests or a clean empirical reproduction.',new_empirical_execution=False)
report['execution_environment']={'python':sys.version,'executable':sys.executable,'numpy':np.__version__,'platform':platform.platform(),'scope':'Local algebra and primitive checks; no Linux native qualification inferred'}
report['prior_attempt']={'runtime': 'bundled Python runtime', 'outcome': 'NumPy import failed before numerical checks', 'error': 'Accelerate missing _cblas_caxpy$NEWLAPACK$ILP64', 'resolution': 'Used existing system Python and NumPy 1.26.3. No dependency installation or production runtime change.'}
report['input_identities']={n:{'bytes':len(input_path(n).read_bytes()),'sha256':hashlib.sha256(input_path(n).read_bytes()).hexdigest()} for n in ['validation/check_mathematics_v121.py','src/low_rank_certified.py','reports/review-service-v70/E16_comparison_and_costs.json']}
report['enumeration_scope']='81 centers, two radii, three ridges; 81 vertex/interior realizations each; kappa is conservatively bounded by the entrywise L1 norm. Uniform-code cases count point-level implications, not independent trials.'
(B/'v122_generated_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
