"""Independent rational conditional minimization; no production oracle imports."""
from fractions import Fraction as Q

def rational(x):
    return Q.from_float(float(x))

def solve(matrix, rhs):
    """Gauss-Jordan elimination with exact row pivots, for small fixtures only."""
    n=len(rhs)
    a=[list(map(Q,row))+[Q(b)] for row,b in zip(matrix,rhs)]
    assert len(a)==n and all(len(row)==n+1 for row in a)
    for j in range(n):
        pivot=next(i for i in range(j,n) if a[i][j])
        a[j],a[pivot]=a[pivot],a[j]
        v=a[j][j];a[j]=[x/v for x in a[j]]
        for i in range(n):
            if i!=j:
                v=a[i][j];a[i]=[x-v*y for x,y in zip(a[i],a[j])]
    return [row[-1] for row in a]

def metric(features, ridge, normalization):
    x=[[rational(v) for v in row] for row in features]
    return [[sum((a*b for a,b in zip(u,v)),Q(0))/normalization+(ridge if i==j else 0)
             for j,v in enumerate(x)] for i,u in enumerate(x)]

def quantize(weights, features, scales, ridge, normalization):
    h=metric(features,ridge,normalization);d=len(h);result=[]
    for row,scale in zip(weights,scales):
        w=list(map(rational,row));grid=[i*rational(scale) for i in range(-8,8)];codes=[]
        for i in range(d):
            suffix=[line[i:] for line in h[i:]]
            rhs=[sum((h[j][k]*(w[k]-codes[k]) for k in range(i)),Q(0)) for j in range(i,d)]
            value=w[i]+solve(suffix,rhs)[0]
            codes.append(min(enumerate(grid),key=lambda kv:(abs(kv[1]-value),kv[0]))[1])
        result.append(codes)
    return result

def coefficient(features, i, beta):
    x=[[rational(v) for v in row] for row in features];n=len(x[0])
    a=[[sum((row[j]*row[k] for row in x[i:]),Q(0))+(beta if j==k else 0)
        for k in range(n)] for j in range(n)]
    return solve(a,x[i])
