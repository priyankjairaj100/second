"""Synthetic adapter tests. Solver replies are fixtures, not certificates.

No real checkpoint, corpus, feature evaluator or empirical campaign is executed.
A real numerical tiny-case gate in the pinned Linux runtime remains mandatory.
"""
from dataclasses import replace
from fractions import Fraction
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from research_v61 import service as old
from research_v61.test_target import fixture, service_for, bind
from research_v63 import archive
from research_v63.test_control import record, codes
from research_v64.service import ModernService, REPRESENTATION
from src.run_store import digest

ROWS = [dict(id='a', tokens=[1, 2]), dict(id='b', tokens=[3, 4])]


def context():
    base, _ = fixture(((2, 3), (1, 2)), original=4)
    stages = []
    for entry in base['stages']:
        weights = np.zeros(entry['shape'])
        entry['weights_sha256'] = old.dispatch._weight_digest(weights)
        stages.append(SimpleNamespace(stage_id=entry['stage_id'], rows=len(weights), width=weights.shape[1],
            weights=weights, bits=4, scale_values=(1.,)*len(weights), ridge=Fraction(1,100), normalization=Fraction(4)))
    bound = bind(base, service_for(base))
    objects = []
    for cls in (old.Service, ModernService):
        s = object.__new__(cls)
        s.bound = bound
        s.base = SimpleNamespace(digest=digest(bound.anchor_payload))
        s.target = SimpleNamespace(digest=digest(bound.fixed_payload), stages=tuple(stages))
        s.record_provenance = {r['id']:json.loads(record(r['id'],r['tokens']).provenance) for r in ROWS}
        s.policy = old.dispatch.ResourcePolicy()
        s.mark = lambda *a, **k: None
        s.normalization = 4
        objects.append(s)
    values = {}
    for stage in stages:
        for row in ROWS:
            a = np.arange(2*stage.width,dtype=np.float64).reshape(2,stage.width)/8
            a[0,:2] = [0.,-0.]
            a[1,0] = np.nextafter(0.,1.)
            a[1,1] = np.finfo(np.float64).max
            values[stage.stage_id,row['id']] = a
    return *objects, values


def solver(captured, value=1.):
    def answer(spec, weights, blocks, **options):
        pieces = list(blocks)
        assert all(lo is hi for lo,hi in pieces)
        captured.append((spec,weights.tobytes(),[x.T.copy().tobytes() for x,_ in pieces],options))
        return SimpleNamespace(codes=np.full(weights.shape,value), route='synthetic_fixture',
            admission={'fixture':True}, solver_result={'fixture_only':True})
    return answer


class ModernServiceTests(unittest.TestCase):
    def setUp(self):
        self.old, self.new, self.values = context()
        self.modern, _, _ = self.new.prepare_payloads(ROWS,self.values,REPRESENTATION,old.telemetry())
        self.legacy, _, _ = self.old.prepare_payloads(ROWS,self.values,'lossless',old.telemetry())

    def predecessor(self):
        return archive.pack(self.new.bound,self.new.records(ROWS),codes(self.new.bound),self.modern)

    def test_identical_point_words_solver_options_and_output_codes(self):
        a,b = [],[]
        with patch.object(old.dispatch,'solve_blocks',side_effect=solver(a)):
            x,_ = self.old.solve(ROWS,'lossless',self.legacy,{}, {},old.telemetry())
        with patch.object(old.dispatch,'solve_blocks',side_effect=solver(b)):
            y,_ = self.new.solve(ROWS,REPRESENTATION,self.modern,{}, {},old.telemetry())
        self.assertEqual(a,b)
        self.assertEqual(x,y)
        self.assertEqual(len(b),len(self.new.target.stages))
        for index,stage in enumerate(self.new.target.stages):
            self.assertEqual(b[index][2],[self.values[stage.stage_id,r['id']].tobytes() for r in ROWS])

    def test_direct_values_and_archive_route_match(self):
        a,b = [],[]
        with patch.object(old.dispatch,'solve_blocks',side_effect=solver(a)):
            x,_ = self.new.solve(ROWS,REPRESENTATION,self.modern,{}, {},old.telemetry())
        with patch.object(old.dispatch,'solve_blocks',side_effect=solver(b)):
            y,_ = self.new.solve(ROWS,REPRESENTATION,{}, {}, {},old.telemetry(),direct_values=self.values)
        self.assertEqual(a,b);self.assertEqual(x,y)

    def test_repair_recomputes_codes_and_matches_fresh_state(self):
        before=self.predecessor();captured=[];rows=ROWS[1:];timing=old.telemetry()
        with patch.object(old.dispatch,'solve_blocks',side_effect=solver(captured)):
            after,actual,_=self.new.repair(before,ROWS,rows,timing)
        self.assertEqual(len(captured),2)
        self.assertNotEqual(actual,archive.unpack(before).stage_codes)
        self.assertEqual(timing['neural_stage_record_pairs'],0)
        self.assertGreater(timing['predecessor_validation_ns'],0)
        kept={k:v for k,v in self.values.items() if k[1]=='b'}
        fresh_payloads,_,_=self.new.prepare_payloads(rows,kept,REPRESENTATION,old.telemetry())
        with patch.object(old.dispatch,'solve_blocks',side_effect=solver([])):
            expected,_=self.old.solve(rows,'lossless',{}, {}, {},old.telemetry(),direct_values=kept)
        fresh=archive.pack(self.new.bound,self.new.records(rows),expected,fresh_payloads)
        self.assertEqual(after,fresh)
        self.assertEqual(archive.unpack(after).source_map(),{k:v for k,v in self.modern.items() if k[1]=='b'})

    def test_structural_refusal_before_source_parse_or_solver(self):
        self.new.policy=replace(self.new.policy,max_request_work_units=1)
        with patch.object(archive,'descriptor',side_effect=AssertionError('source opened')),patch.object(old.dispatch,'solve_blocks') as call:
            with self.assertRaises(ValueError):self.new.solve(ROWS,REPRESENTATION,self.modern,{}, {},old.telemetry())
            call.assert_not_called()

    def test_missing_and_extra_sources_refuse(self):
        missing=dict(self.modern);missing.pop(next(iter(missing)))
        for p in (missing,dict(self.modern,extra=b'x')):
            with patch.object(old.dispatch,'solve_blocks') as call:
                with self.assertRaises(ValueError):self.new.solve(ROWS,REPRESENTATION,p,{}, {},old.telemetry())
                call.assert_not_called()

    def test_stage_weight_or_order_mutation_refuses_before_any_solver(self):
        for kind in ('weights','order'):
            _,s,_=context()
            if kind=='weights':s.target.stages[1].weights[0,0]=1.
            else:s.target.stages=tuple(reversed(s.target.stages))
            with patch.object(old.dispatch,'solve_blocks') as call:
                with self.assertRaisesRegex(ValueError,'Numerical stage'):s.solve(ROWS,REPRESENTATION,self.modern,{}, {},old.telemetry())
                call.assert_not_called()

    def test_wrong_source_identity_and_trailing_bytes_refuse(self):
        bad=dict(self.modern);bad['stage.0','a']=bad['stage.0','b']
        for p in (bad,{k:v+b'x' for k,v in self.modern.items()}):
            with patch.object(old.dispatch,'solve_blocks',side_effect=solver([])):
                with self.assertRaises(ValueError):self.new.solve(ROWS,REPRESENTATION,p,{}, {},old.telemetry())

    def test_predecessor_membership_and_non_subset_refuse(self):
        for previous,retained in ((ROWS[:1],ROWS[:1]),(ROWS,ROWS),(ROWS,[]),
                                  (ROWS,[dict(id='a',tokens=[8,9])]),(list(reversed(ROWS)),[ROWS[0],ROWS[0]])):
            with self.assertRaises(ValueError):self.new.repair(self.predecessor(),previous,retained,old.telemetry())
        with self.assertRaisesRegex(ValueError,'Predecessor'):
            self.new.repair(archive.pack(self.new.bound,self.new.records(ROWS[:1]),codes(self.new.bound),
                {k:v for k,v in self.modern.items() if k[1]=='a'}),ROWS,ROWS[:1],old.telemetry())

    def test_wrong_representation_or_external_gram_trust_refuses(self):
        for rep,grams,trust in (('lossless',{},{}),(REPRESENTATION,{'x':b''},{}),(REPRESENTATION,{}, {'x':1})):
            with self.assertRaises(ValueError):self.new.solve(ROWS,rep,self.modern,grams,trust,old.telemetry())

    def test_invalid_direct_shape_dtype_and_nonfinite_values_refuse(self):
        key=next(iter(self.values))
        for v in (np.zeros((1,1)),np.zeros((2,3),dtype=np.float32),np.full((2,3),np.inf)):
            values=dict(self.values);values[key]=v
            with patch.object(old.dispatch,'solve_blocks',side_effect=solver([])):
                with self.assertRaises(ValueError):self.new.solve(ROWS,REPRESENTATION,{}, {}, {},old.telemetry(),direct_values=values)

    def test_failed_encoding_time_is_retained(self):
        timing=old.telemetry()
        with patch.object(self.new,'descriptor',side_effect=ValueError('fixture')):
            with self.assertRaises(ValueError):self.new.prepare_payloads(ROWS,self.values,REPRESENTATION,timing)
        self.assertGreater(timing['encoding_and_gram_ns'],0)

    def test_corrupt_predecessor_cannot_return_successor(self):
        for b in (self.predecessor()+b'x', self.predecessor()[:-1]):
            with patch.object(old.dispatch,'solve_blocks') as call:
                with self.assertRaises(ValueError):self.new.repair(b,ROWS,ROWS[1:],old.telemetry())
                call.assert_not_called()


if __name__=='__main__':unittest.main()
