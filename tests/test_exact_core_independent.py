"""Software verification against constrained Gaussian solves, no dataset study."""
import unittest
from fractions import Fraction as F
from src.exact_core import sequential_oracle, certify_relative_enclosure


def solve(a,b):
    a=[list(map(F,row))+[F(y)] for row,y in zip(a,b)]
    n=len(a)
    for i in range(n):
        k=next(k for k in range(i,n) if a[k][i])
        a[i],a[k]=a[k],a[i]
        p=a[i][i]
        a[i]=[v/p for v in a[i]]
        for k in range(n):
            if k!=i:
                p=a[k][i]
                a[k]=[v-p*w for v,w in zip(a[k],a[i])]
    return [row[-1] for row in a]


def constrained_oracle(weights,h,grids):
    out=[]
    n=len(h)
    for w in weights:
        q=[]
        for i in range(n):
            # Minimize (w-q)^T H (w-q) over all still-free coordinates.
            rhs=[-sum(F(h[j][k])*(F(w[k])-q[k]) for k in range(i)) for j in range(i,n)]
            residual=solve([row[i:] for row in h[i:]],rhs)
            conditional=F(w[i])-residual[0]
            q.append(min(map(F,grids[i]),key=lambda c:(abs(c-conditional),c)))
        out.append(tuple(q))
    return tuple(out)

class IndependentCoreTests(unittest.TestCase):
    def test_gaussian_constrained_oracle(self):
        fixtures=[[[2,1],[1,3]],[[4,1,-1],[1,3,1],[-1,1,4]],[[1]]]
        for h in fixtures:
            d=len(h); grids=[[-2,-1,0,1,2]]*d
            for numerator in range(-4,5):
                weights=[[F(numerator+i,3) for i in range(d)],[F(1,2)]*d]
                self.assertEqual(sequential_oracle(weights,h,grids).codes,constrained_oracle(weights,h,grids))
    def test_certified_metric_family(self):
        h=[[2,0],[0,2]]; grids=[[-1,0,1]]*2
        for w in ([[F(1,3),F(1,3)]],[[F(1,2),F(3,4)]],[[3,-3]]):
            cert=certify_relative_enclosure(w,h,grids,F(3,4),F(5,4))
            # H_* = H + [[u,v],[v,-u]] has deviations <=1/2 for these fixtures.
            for u,v in ((F(0),F(0)),(F(1,4),F(1,4)),(F(-1,4),F(1,4)),(F(1,2),F(0))):
                target=[[2+u,v],[v,2-u]]
                if cert.accepted:
                    self.assertEqual(cert.candidate.codes,constrained_oracle(w,target,grids))
    def test_scale_ties_and_input_rejection(self):
        w=[[F(1,2),F(-1,2)]]; h=[[2,1],[1,2]]; g=[[-1,0,1]]*2
        cert=certify_relative_enclosure(w,h,g,3,3)
        self.assertTrue(cert.accepted)
        self.assertEqual(cert.candidate.codes,constrained_oracle(w,[[6,3],[3,6]],g))
        self.assertFalse(cert.spectral_premise_verified_by_module)
        with self.assertRaises(TypeError): sequential_oracle([[0.5]],[[1]],[[0,1]])
        with self.assertRaises(ValueError): sequential_oracle([[1,1]],[[1,2],[2,1]],g)
