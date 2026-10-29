"""Independent rational checks of manuscript identities; no research code execution."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import random,json
rng=random.Random(121)
def tr(A): return list(map(list,zip(*A)))
def mm(A,B):return [[sum((a*b for a,b in zip(r,c)),F(0)) for c in tr(B)] for r in A]
def inv(A):
 n=len(A);a=[list(r)+[F(i==j) for j in range(n)] for i,r in enumerate(A)]
 for i in range(n):
  p=next(j for j in range(i,n) if a[j][i]);a[i],a[p]=a[p],a[i]
  v=a[i][i];a[i]=[v0/v for v0 in a[i]]
  for j in range(n):
   if j!=i:
    v=a[j][i];a[j]=[x-v*y for x,y in zip(a[j],a[i])]
 return [r[n:] for r in a]
def dot(a,b):return sum((x*y for x,y in zip(a,b)),F(0))
def add_ridge(A,b):return [[x+(b if i==j else 0) for j,x in enumerate(r)] for i,r in enumerate(A)]
def ldl(A):
 n=len(A);L=[[F(i==j) for j in range(n)] for i in range(n)];D=[F(0)]*n
 for i in reversed(range(n)):
  D[i]=A[i][i]-sum(D[k]*L[k][i]**2 for k in range(i+1,n));assert D[i]>0
  for h in range(i):L[i][h]=(A[i][h]-sum(D[k]*L[k][i]*L[k][h] for k in range(i+1,n)))/D[i]
 assert mm(mm(tr(L),[[D[i] if i==j else F(0) for j in range(n)] for i in range(n)]),L)==A
 return L
cases=[]
for vals in product([-1,0,1],repeat=4):
 for b in [F(1,4),F(1),F(4)]:cases.append(([[F(v) for v in vals[:2]],[F(v) for v in vals[2:]]],b))
for d in [1,3,4]:
 for T in [1,2,3,4]:
  for _ in range(6):cases.append(([[F(rng.randint(-3,3),4) for t in range(T)] for i in range(d)],F(rng.choice([1,2,5]),4)))
ncoeff=0
for X,b in cases:
 d=len(X);T=len(X[0]);K=mm(X,tr(X));A=add_ridge(K,b);L=ldl(A)
 w=[F(rng.randint(-4,4),8) for i in range(d)];q=[]
 for i in range(d):
  As=[r[i:] for r in A[i:]];Z=inv(As);z=[r[0] for r in Z]
  B=add_ridge(mm(tr(X[i:]),X[i:]),b);Binv=inv(B);t=[dot(r,X[i]) for r in Binv]
  zp=[F(rng.randint(-4,4),8) for _ in z];tp=[F(rng.randint(-4,4),8) for _ in t]
  res=[F(k==0)-dot(r,zp) for k,r in enumerate(As)];eta2=dot(res,res)
  rt=[x-dot(r,tp) for x,r in zip(X[i],B)];xi2=dot(rt,rt)
  for h in range(i):
   c=dot(K[h][i:],z);assert c==L[i][h]==dot(X[h],t)
   err=(c-dot(K[h][i:],zp))**2
   assert err<=eta2*dot(K[h][i:],K[h][i:])/b**2
   assert err<=eta2*K[h][h]/(4*b)
   assert (c-dot(X[h],tp))**2<=dot(X[h],X[h])*xi2/b**2
   ncoeff+=1
  v=w[i]+sum(L[i][h]*(w[h]-q[h]) for h in range(i))
  # First coordinate of the conditional continuous minimizer; free suffix stationary.
  rhs=[sum(A[j][h]*(w[h]-q[h]) for h in range(i)) for j in range(i,d)]
  delta=[dot(r,rhs) for r in Z]
  assert w[i]+delta[0]==v
  q.append(min([F(-1),F(0),F(1)],key=lambda c:(abs(c-v),c)))
# All singleton and interval endpoint ties, including saturated end codes.
grid=[F(-1),F(0),F(1)];bounds=[F(-1,2),F(1,2)];ncells=0
points=[F(i,4) for i in range(-8,9)]
for lo in points:
 for hi in points:
  if lo>hi:continue
  for a,g in enumerate(grid):
   accept=(a==0 or lo>bounds[a-1]) and (a==2 or hi<=bounds[a])
   probes=[lo,hi]+[x for x in bounds if lo<=x<=hi]
   agrees=all(min(grid,key=lambda c:(abs(c-x),c))==g for x in probes)
   assert accept==agrees;ncells+=1
lo=F(9801,20201);hi=F(10201,19801)
assert F(59,100)<F(2,5)*(1+lo)<F(2,5)*(1+hi)<F(61,100)
# Exact information counterexample: same enclosing box, different retained target.
c0=F(0);c1=F(1,2);assert min(grid,key=lambda q:(abs(F(2,5)*(1+c0)-q),q))!=min(grid,key=lambda q:(abs(F(2,5)*(1+c1)-q),q))
report=dict(schema='second-manuscript-mathematical-audit-v121',rational_matrix_cases=len(cases),coefficient_identity_and_squared_bounds=ncoeff,rounding_cell_boundary_cases=ncells,
 reverse_ldl_suffix_identity=True,token_dual_identity=True,quadratic_stationarity=True,both_feature_residual_bounds=True,token_residual_bound=True,lower_midpoint_ties=True,worked_example=True,
 manual_proof_review='suffix factorization, spectral bound, prefix induction, exact subtraction, canonical state composition',
 scope='Independent exact rational illustration checks support manual derivation review; not empirical results or a formal verification of the executable implementation.',new_model_or_cluster_experiment=False)
(Path(__file__).resolve().parent/'v121_math_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
