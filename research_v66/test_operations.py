"""Synthetic transaction tests. Fixture solver outputs are not certificates."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

from research_v61 import service as old
from research_v61.test_state import BUDGET
from research_v64.test_service import context, ROWS, solver
from research_v66.operations import AllRepresentationsService, request, artifact, MODERN, ARM_REPRESENTATION
from src.run_store import canonical_json,digest


class MemoryWriter:
    def __init__(self):self.files={}
    def __call__(self,name,blob):
        assert name not in self.files
        self.files[name]=blob
        return dict(file=name,bytes=len(blob),sha256=digest(blob))


class OperationTests(unittest.TestCase):
    def setUp(self):
        reference,_,values=context()
        self.service=object.__new__(AllRepresentationsService)
        self.service.__dict__.update(reference.__dict__)
        self.service.gram_budget=BUDGET
        self.values={k:np.arange(v.size,dtype=np.float64).reshape(v.shape)/16 for k,v in values.items()}

    def extract(self,rows,timing):
        timing['neural_stage_record_pairs']+=len(rows)*len(self.service.target.stages)
        return {k:v.copy() for k,v in self.values.items() if k[1] in {r['id'] for r in rows}}

    def initial(self,representation):
        p,g,t=self.service.prepare_payloads(ROWS,self.values,representation,old.telemetry())
        with patch.object(old.dispatch,'solve_blocks',side_effect=solver([])):
            codes,_=self.service.solve(ROWS,'lossless',{}, {}, {},old.telemetry(),direct_values=self.values)
        return self.service.serialize(ROWS,codes,representation,p,g,t,old.telemetry()),canonical_json(old.trust_json(t))

    def test_four_point_arms_recompute_and_write_equal_models(self):
        models=[]
        for arm in ['cached','cold','compressed','modern']:
            with self.subTest(arm=arm):
                before=self.initial(ARM_REPRESENTATION[arm]);written=MemoryWriter();captured=[]
                def answer(spec,weights,blocks,**options):
                    # Compressed low/high bounds can differ; inspect all inputs.
                    parts=list(blocks)
                    self.assertEqual(sum(a.shape[1] for a,b in parts),2)
                    captured.append(spec.stage_id)
                    return SimpleNamespace(
                        codes=np.ones(weights.shape),route='synthetic_fixture',admission={'fixture':True},solver_result={'fixture_only':True})
                with patch.object(self.service,'extract',side_effect=self.extract),patch.object(old.dispatch,'solve_blocks',side_effect=answer):
                    result=request(self.service,ROWS,ROWS[1:],arm,lambda:before,written)
                self.assertEqual(len(captured),2)
                self.assertEqual(set(written.files),{'state.bin','model.bin','trust.json'})
                self.assertEqual(result['live_state_bytes'],len(written.files['state.bin'])+len(written.files['trust.json']))
                self.assertEqual(result['deleted_ids'],['a'])
                self.assertGreater(result['request_elapsed_ns'],result['timing']['disposal_ns'])
                models.append(written.files['model.bin'])
        self.assertTrue(all(m==models[0] for m in models))

    def test_cold_never_reads_predecessor(self):
        with patch.object(self.service,'extract',side_effect=self.extract),patch.object(old.dispatch,'solve_blocks',side_effect=solver([])):
            request(self.service,ROWS,ROWS[1:],'cold',lambda:self.fail('Cold accessed state'),MemoryWriter())

    def test_modified_tokens_refuse_before_predecessor_access(self):
        changed=copy.deepcopy(ROWS[1:]);changed[0]['tokens'][0]+=1
        for arm in ARM_REPRESENTATION:
            with self.subTest(arm=arm),self.assertRaises(ValueError):
                request(self.service,ROWS,changed,arm,lambda:self.fail('Opened predecessor'),MemoryWriter())

    def test_unsorted_root_refuses_before_predecessor_access(self):
        with self.assertRaises(ValueError):request(self.service,list(reversed(ROWS)),ROWS[1:],'cached',lambda:self.fail('Opened predecessor'),MemoryWriter())

    def test_corrupt_modern_state_refuses_without_solver(self):
        before,trust=self.initial(MODERN)
        with patch.object(old.dispatch,'solve_blocks') as call:
            with self.assertRaises(ValueError):request(self.service,ROWS,ROWS[1:],'modern',lambda:(before+b'x',trust),MemoryWriter())
            call.assert_not_called()

    def test_noncanonical_trust_refuses(self):
        before,_=self.initial('lossless')
        with patch.object(old.dispatch,'solve_blocks') as call:
            with self.assertRaises(ValueError):request(self.service,ROWS,ROWS[1:],'cached',lambda:(before,b'{ }'),MemoryWriter())
            call.assert_not_called()

    def test_wrong_representation_refuses_before_solver(self):
        before=self.initial('compressed48')
        with patch.object(old.dispatch,'solve_blocks') as call:
            with self.assertRaises(ValueError):request(self.service,ROWS,ROWS[1:],'cached',lambda:before,MemoryWriter())
            call.assert_not_called()

    def test_output_commitment_mismatch_refuses(self):
        with self.assertRaises(ValueError):artifact(lambda n,b:dict(file=n,bytes=len(b),sha256='0'*64),'model.bin',b'actual')

    def test_unknown_representation_refuses_before_solver(self):
        with self.assertRaises(ValueError):self.service.admit(ROWS,'unregistered')


if __name__=='__main__':unittest.main()
