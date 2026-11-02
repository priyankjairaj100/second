import copy
import json
import tempfile
import unittest
from pathlib import Path
from . import runner as r


class RunnerTests(unittest.TestCase):
    def test_exclusive_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';r.new(p,{})
            with self.assertRaises(FileExistsError):r.new(p,{})
    def test_bound_read_refuses_tamper_wrong_extent_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve()/'x';p.write_bytes(b'ab');e=r.info(b'ab')
            self.assertEqual(r.bound(p,e),b'ab')
            with self.assertRaises(ValueError):r.bound(p,dict(e,bytes=3))
            p.write_bytes(b'ac')
            with self.assertRaises(ValueError):r.bound(p,e)
            q=p.parent/'q';q.symlink_to(p)
            with self.assertRaises(ValueError):r.bound(q,r.info(b'ac'))
    def test_json_duplicates_and_nonfinite_refuse(self):
        for b in (b'{"x":1,"x":2}',b'{"x":NaN}'):
            with self.assertRaises(ValueError):r.strict(b)
    def test_registration_caps_scope_and_paths_refuse(self):
        p=dict(schema='source-local-lossless-artifact-control-v63',run_directory=str(r.RUN),trials=['checks','measure','audit'],caps=r.CAPS,
            neural_execution=False,calibration=False,quality_evaluation=False,automatic_retry=False,expected_tests=21,
            frozen_sources={str(i):'a'*64 for i in range(432)},new_sources={},states=['a','b','c'],models=['d','e','f'],retained_counts=[13,12,6],factor_counts=[312,288,144],inputs={})
        self.assertEqual(r.validate_plan(p,r.info(r.canonical(p))['sha256']),p)
        for key,value in [('automatic_retry',True),('caps',{}),('neural_execution',True),('retained_counts',[13,11,6]),('new_sources',{'../escape':{}})]:
            bad=copy.deepcopy(p);bad[key]=value
            with self.assertRaises(ValueError):r.validate_plan(bad,r.info(r.canonical(bad))['sha256'])
