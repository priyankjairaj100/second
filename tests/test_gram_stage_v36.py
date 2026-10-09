"""V36 software fixtures. No real-data Gram or new quantization is evaluated."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from research_v36 import archive_stage_capsule as capsule
from scripts import launch_gram_stage_v36 as controller
from scripts import execute_gram_stage_v36 as worker

class FullStageProtocolTests(unittest.TestCase):
    def test_shards_roundtrip_and_tamper(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(capsule.MAX_RAW,{'weights':19}):
            p=Path(d);raw=b'full stage fixture!';self.assertEqual(len(raw),19)
            entry=capsule._write_payload(p,'weights',raw)
            self.assertEqual(capsule._read_payload(p,'weights',entry),raw)
            target=p/entry['shards'][0]['file'];target.write_bytes(b'AAAA')
            with self.assertRaises(ValueError):capsule._read_payload(p,'weights',entry)

    def test_shard_filename_cannot_escape_directory(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(capsule.MAX_RAW,{'weights':4}):
            p=Path(d);entry=capsule._write_payload(p,'weights',b'abcd')
            entry['shards'][0]['file']='../escape'
            with self.assertRaisesRegex(ValueError,'name/order'):capsule._read_payload(p,'weights',entry)

    def test_decoder_rejects_declared_short_output(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(capsule.MAX_RAW,{'weights':400}):
            p=Path(d);entry=capsule._write_payload(p,'weights',b'x'*400)
            with patch.dict(capsule.MAX_RAW,{'weights':4}):
                entry['raw_bytes']=4
                with self.assertRaises(ValueError):capsule._read_payload(p,'weights',entry)

    def test_full_output_rows_have_correct_conv1d_axes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.safetensors'
            matrix=np.arange(768*2304,dtype=np.float32).reshape(768,2304)
            raw=matrix.astype('<f4').tobytes();header=json.dumps({'transformer.h.0.attn.c_attn.weight':dict(dtype='F32',shape=[768,2304],data_offsets=[0,len(raw)])}).encode()
            p.write_bytes(struct.pack('<Q',len(header))+header+raw)
            actual=capsule.checkpoint_stage(p)
            self.assertEqual(actual.shape,(2304,768));np.testing.assert_array_equal(actual,matrix.T)

    def test_full_stage_structural_admission(self):
        from research_v35.direct_gram import assess_direct_gram_budget
        from src.primal_certificate_v30 import PrimalBudget
        result=assess_direct_gram_budget(rows=2304,width=768,budget=PrimalBudget(max_workspace_bytes=512*2**20,max_work_units=6_000_000_000))
        self.assertTrue(result['admitted']);self.assertEqual(result['rows']*result['width'],1_769_472)

    def test_existing_campaign_prevents_register(self):
        with tempfile.TemporaryDirectory() as d,patch.object(controller,'bind_inputs',side_effect=AssertionError('must not parse')):
            with self.assertRaises(ValueError):controller.register(Path(d),Path(d)/'manifest.json')

    def test_existing_attempt_prevents_retry(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'attempt').mkdir()
            with patch.object(controller,'verified_program',return_value={}),patch.object(controller,'run_limited',side_effect=AssertionError('must not launch')):
                with self.assertRaises(ValueError):controller.execute(p)

    def test_only_expected_scientific_refusals_continue(self):
        from research_v35.direct_gram import DirectGramUnresolved
        from src.low_rank_certified import LowRankUnresolved
        self.assertTrue(worker.scientific_refusal(DirectGramUnresolved('primal native row verification failed: status=3, row=123, coordinate=42')))
        self.assertTrue(worker.scientific_refusal(DirectGramUnresolved('direct Gram coefficient enclosure failed at coordinate 42: status=2')))
        self.assertTrue(worker.scientific_refusal(LowRankUnresolved('exact fallback budget exceeded at coordinate 42; no codes committed')))
        self.assertFalse(worker.scientific_refusal(DirectGramUnresolved('primal native row verification failed: status=1, row=123, coordinate=42')))
        self.assertFalse(worker.scientific_refusal(DirectGramUnresolved('native allocation failed')))
        self.assertFalse(worker.scientific_refusal(ValueError('exact fallback budget exceeded at coordinate 42; no codes committed')))

    def test_prior_ledger_subset_allows_future_but_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);program=dict(source_sha256={},runtime={},historical_ledgers_sha256={'prior':'original'},inputs={})
            (p/'program.json').write_bytes(worker.canonical_json(program))
            (p/'registration.json').write_text(json.dumps({'program_sha256':worker.hashed(p/'program.json')}))
            with patch.object(controller,'current_sources',return_value={}),patch.object(controller,'capture_runtime_contract',return_value={}),patch.object(controller,'verify_inputs'),patch.object(controller,'historical_ledgers',return_value={'prior':'original','future':'new'}):
                self.assertEqual(controller.verified_program(p),program)
            with patch.object(controller,'current_sources',return_value={}),patch.object(controller,'capture_runtime_contract',return_value={}),patch.object(controller,'verify_inputs'),patch.object(controller,'historical_ledgers',return_value={'prior':'changed'}):
                with self.assertRaisesRegex(ValueError,'bound historical'):controller.verified_program(p)

if __name__=='__main__':unittest.main()
