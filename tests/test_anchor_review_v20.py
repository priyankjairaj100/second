"""Adversarial scalar bound fixtures. These are not empirical datasets."""
from fractions import Fraction as Q
import math
import unittest

from src.anchor_transformer import SummaryNode, _node_error, _up_q
from src.finite_primitives import primitive_scope, rounded


def summary(value):
    return SummaryNode('constant', (), value, value, abs(value))


class AnchorBoundReviewTests(unittest.TestCase):
    def assert_contains(self, op, anchors, changes):
        nodes = tuple(summary(float(x)) for x in anchors)
        errors = tuple(abs(Q.from_float(float(d))) for d in changes)
        output = SummaryNode(op, tuple(range(len(nodes))), 0., 0., 0.)
        bound = _node_error(output, nodes, errors)
        if len(nodes) == 2:
            operation = {'add': lambda a,b:a+b, 'sub':lambda a,b:a-b,
                         'mul':lambda a,b:a*b, 'div':lambda a,b:a/b}[op]
        else:
            operation = lambda a: rounded(op, a)
        old = operation(*anchors)
        new = operation(*(float(x+d) for x,d in zip(anchors, changes)))
        self.assertTrue(math.isfinite(old) and math.isfinite(new))
        self.assertLessEqual(abs(Q.from_float(new)-Q.from_float(old)), bound)

    def test_binary_bounds_with_cancellation_and_subnormals(self):
        tiny = float.fromhex('0x0.0000000000001p-1022')
        normal = float.fromhex('0x1p-1022')
        cells = (
            ('add', (1., -1.), (2.**-52, 0.)),
            ('sub', (1., 1.), (0., 2.**-52)),
            ('mul', (tiny, .5), (tiny, -.25)),
            ('mul', (2.**500, 2.**-500), (2.**448, 2.**-550)),
            ('div', (normal, normal), (tiny, -tiny)),
            ('div', (1., 2.), (2.**-52, -2.**-51)),
        )
        for op, anchors, changes in cells:
            with self.subTest(op=op, anchors=anchors):
                self.assert_contains(op, anchors, changes)

    def test_nonlinear_bounds_near_machine_extremes(self):
        tiny = float.fromhex('0x0.0000000000001p-1022')
        cells = (
            ('sqrt', (tiny,), (tiny,)),
            ('sqrt', (1.,), (-2.**-52,)),
            ('sqrt', (2.**1000,), (2.**948,)),
            ('exp', (-745.,), (1.,)),
            ('exp', (700.,), (1.,)),
            ('exp', (0.,), (2.**-52,)),
            ('erf', (-1.,), (2.**-30,)),
            ('erf', (tiny,), (-tiny,)),
            ('tanh', (100.,), (-2.**-20,)),
            ('tanh', (-tiny,), (tiny,)),
        )
        with primitive_scope('mpfr_enclosure'):
            for op, anchors, changes in cells:
                with self.subTest(op=op, anchors=anchors):
                    self.assert_contains(op, anchors, changes)

    def test_unsafe_domains_fail_closed(self):
        nodes = (summary(1.), summary(1.))
        quotient = SummaryNode('div', (0, 1), 1., 1., 1.)
        with self.assertRaises(ArithmeticError):
            _node_error(quotient, nodes, (Q(0), Q(1)))
        root = SummaryNode('sqrt', (0,), 1., 1., 1.)
        with self.assertRaises(ArithmeticError):
            _node_error(root, nodes, (Q(2), Q(0)))
        maximum = float.fromhex('0x1.fffffffffffffp+1023')
        with self.assertRaises(ArithmeticError):
            _up_q(Q.from_float(maximum)+1)
        with self.assertRaises(ArithmeticError):
            _node_error(SummaryNode('add', (0,1), 0.,0.,0.),
                        (summary(maximum), summary(0.)), (Q(1),Q(0)))

    def test_zero_error_does_not_claim_zero_sign_identity(self):
        node = SummaryNode('mul', (0,1), -0., -0., 0.)
        error = _node_error(node, (summary(-0.), summary(1.)), (Q(0),Q(0)))
        self.assertEqual(error, 0)
        self.assertEqual(-0.*1., +0.*1.)
        self.assertNotEqual(math.copysign(1., -0.*1.), math.copysign(1., +0.*1.))


if __name__ == '__main__':
    unittest.main()
