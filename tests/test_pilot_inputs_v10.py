"""Software checks for pilot parsing and exact-order prototype arithmetic."""
import importlib.util
from pathlib import Path
import struct
import unittest

from scripts.prepare_wikitext_pilot import articles


class PilotInputTests(unittest.TestCase):
    def test_article_boundaries_keep_sections(self):
        result=list(articles(['\n','= First Article =\n','Body\n','= = Section = =\n','More\n','= Second Article =\n','Other\n']))
        self.assertEqual(len(result),2)
        self.assertEqual(result[0]['start_row'],1)
        self.assertEqual(len(result[0]['rows']),3)

    def test_leading_body_rejected(self):
        with self.assertRaises(ValueError):list(articles(['Body without title']))


class OrderedKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parents[1]/'pilots/v10/ordered_float64.py'
        spec=importlib.util.spec_from_file_location('ordered_pilot',path)
        cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)

    def compare(self,x,w,b):
        actual=self.module.ordered_linear(x,w,b)
        expected=[]
        for row in x:
            result=[]
            for weight,bias in zip(w,b):
                value=0.0
                for a,z in zip(row,weight):value=value+(a*z)
                result.append(value+bias)
            expected.append(result)
        pack=lambda rows:b''.join(struct.pack('<d',z) for row in rows for z in row)
        self.assertEqual(pack(actual),pack(expected))

    def test_cancellation_and_fma_sensitive_values(self):
        self.compare([[1e16,1.,-1e16],[1.+2**-27,1.,0.]],
            [[1.,1.,1.],[1.-2**-27,-1.,0.]],[-0.0,0.0])

    def test_underflow_subnormals_and_signed_zero(self):
        s=float.fromhex('0x0.0000000000001p-1022')
        self.compare([[s,-s,-0.0],[s*3,s*5,0.0]],[[0.5,1.,1.],[1.,-0.5,0.]],[-0.0,0.0])

    def test_overflow_fails_instead_of_cancelling(self):
        with self.assertRaises(ArithmeticError):
            self.module.ordered_linear([[1e308,1e308]],[[2.,-2.]],[0.])

    def test_shapes_and_nonfinite_rejected(self):
        for x,w,b in [([[1.]],[[1.,2.]],[0.]),([[float('nan')]],[[1.]],[0.])]:
            with self.assertRaises(ValueError):self.module.ordered_linear(x,w,b)


class LastWordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parents[1]/'pilots/v10/lambada_scoring.py'
        spec=importlib.util.spec_from_file_location('last_word_pilot',path)
        cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)

    def test_every_target_token_affects_accuracy(self):
        p={'context':(0,),'target':(1,2),'input_tokens':(0,1),'dropped_context_tokens':0}
        # Last token matches, but the complete word does not.
        r=self.module.score_last_word(p,[[2.,1.,0.],[0.,1.,2.]])
        self.assertFalse(r['word_correct'])
        self.assertEqual(r['target_tokens'],2)
        self.assertLess(r['log_likelihood'],0)

    def test_lower_token_breaks_exact_tie(self):
        p={'context':(0,),'target':(0,),'input_tokens':(0,),'dropped_context_tokens':0}
        self.assertTrue(self.module.score_last_word(p,[[0.,0.]])['word_correct'])

    def test_context_truncation_keeps_complete_target(self):
        mapping={'long context':[0,1,2,3],' word':[4,5], 'long context word':[0,1,2,3,4,5]}
        p=self.module.prepare_last_word('long context word',mapping.__getitem__,3)
        self.assertEqual(p['context'],(2,3))
        self.assertEqual(p['input_tokens'],(2,3,4))
        self.assertEqual(p['target'],(4,5))

    def test_boundary_crossing_rejected(self):
        mapping={'a':[0],' b':[1], 'a b':[2]}
        with self.assertRaises(ValueError):self.module.prepare_last_word('a b',mapping.__getitem__,4)


if __name__=='__main__':unittest.main()
