"""Precision separation, charged replay, and shared-backend integration fixtures."""
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from research_v43 import state as old
from research_v53 import state as new, service, worker
from research_v53.test_state import artifacts, bind, fixture, record, codes, state
from src import fixed_factor_codec_v26 as codec


class PrecisionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.target=bind(*fixture(((1,3),),original=8))
        self.records=(record('a',(1,2)),record('b',(3,4)))

    def test_historical_validator_still_rejects_actual_48bit_payload(self):
        prepared=artifacts(self.target,self.records,'compressed48')
        old_records=tuple(old.Record(r.record_id,r.tokens,r.provenance) for r in self.records)
        with self.assertRaisesRegex(ValueError,'40-bit'):
            old.build_state(self.target,old_records,codes(self.target),'compressed40',
                source_payloads=prepared['source_payloads'])
        blob,_=state(self.target,self.records,'compressed48')
        with self.assertRaisesRegex(ValueError,'magic'):
            old.validate_state(blob)

    def test_40bit_and_wrong_block_rejected_in_explicit_48bit_state(self):
        for bits,block in ((40,256),(48,128)):
            prepared=artifacts(self.target,self.records,'compressed48')
            key=next(iter(prepared['source_payloads']))
            desc=codec.parse(prepared['source_payloads'][key]);r=self.records[0]
            blob=codec.serialize(codec.encode_factor(np.ones(desc.shape),bits=bits,block_size=block,
                target_sha256=desc.target_sha256,anchor_target_sha256=desc.anchor_target_sha256,
                record_id=r.record_id,token_sha256=r.token_sha256,stage_id=desc.stage_id))
            prepared['source_payloads'][key]=blob
            with self.assertRaisesRegex(ValueError,'48-bit'):
                new.build_state(self.target,self.records,codes(self.target),'compressed48',**prepared)

    def test_representation_cannot_change_during_deletion(self):
        previous,_=state(self.target,self.records,'compressed48')
        candidate,_=state(self.target,self.records[1:],'lossless')
        with self.assertRaisesRegex(ValueError,'silently change'):
            new.verify_successor(previous,candidate,candidate,['a'])

    def test_every_worker_enters_same_backend_and_restores_on_error(self):
        calls=[]
        @contextmanager
        def selected():
            calls.append('enter')
            try:yield {'backend':'fixture'}
            finally:calls.append('exit')
        with patch('research_v50.neighbors.enabled',selected), patch.object(worker,'_main',side_effect=ValueError('fixture')) as invoke:
            with self.assertRaisesRegex(ValueError,'fixture'):worker.main('plan')
        self.assertEqual(calls,['enter','exit'])
        invoke.assert_called_once_with('plan',{'backend':'fixture'})

    def replay_case(self,corrupt=False):
        instance=object.__new__(service.Service)
        stages=tuple(SimpleNamespace(stage_id=f'stage.{i}',weights=np.ones((1,3)),
            bits=4,scale_values=(1.,),width=3) for i in range(2))
        instance.target=SimpleNamespace(stages=stages,digest=new.sha(self.target.fixed_payload))
        instance.base=SimpleNamespace(digest=new.sha(self.target.anchor_payload))
        instance.policy=service.dispatch.ResourcePolicy();instance.mark=lambda *a,**k:None
        instance.admit=lambda *a,**k:{'admitted':True}
        rows=[{'id':r.record_id,'tokens':list(r.tokens)} for r in self.records]
        values={(s.stage_id,r['id']):np.full((2,3),.25) for s in stages for r in rows}
        payloads={(s.stage_id,r['id']):instance.descriptor(s,r,values[s.stage_id,r['id']],'compressed48') for s in stages for r in rows}
        timing=service.telemetry();replayed=[]
        def extract(rows,timing):
            replayed.append(True);timing['neural_stage_record_pairs']+=48
            return {key:value+(1. if corrupt else 0.) for key,value in values.items()}
        instance.extract=extract
        attempts=[]
        def solve(spec,weights,blocks,**kwargs):
            attempts.append(kwargs['kind']);list(blocks)
            if kwargs['kind']=='box':raise service.dispatch.DispatchRefused('fixture refusal',{})
            return SimpleNamespace(codes=np.zeros((1,3)),route='fixture',admission={},solver_result={})
        with patch.object(service.dispatch.StageSpec,'from_stage',return_value=object()), patch.object(service.dispatch,'solve_blocks',side_effect=solve):
            if corrupt:
                with self.assertRaisesRegex(ValueError,'source identity'):instance.solve(rows,'compressed48',payloads,{},{},timing)
            else:
                answer,_=instance.solve(rows,'compressed48',payloads,{},{},timing)
                self.assertEqual(len(answer),2)
                self.assertEqual(attempts,['box','point','box','point'])
                self.assertTrue(all(x['fallback'] and x['certificate_refusal'] for x in timing['stages']))
        self.assertEqual(len(replayed),1)
        self.assertEqual(timing['neural_stage_record_pairs'],48)

    def test_compressed_refusal_replays_once_and_records_each_failed_stage(self):self.replay_case()
    def test_replayed_source_mismatch_refuses_before_point_output(self):self.replay_case(corrupt=True)

if __name__=='__main__':unittest.main()
