"""Protocol software fixtures only. No archived real-data Gram is computed."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scripts import execute_gram_pilot_v35 as worker
from scripts import launch_gram_pilot_v35 as controller

class GramProtocolTests(unittest.TestCase):
    def test_new_file_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.json';worker.new_file(p,b'first')
            with self.assertRaises(FileExistsError):worker.new_file(p,b'second')
            self.assertEqual(p.read_bytes(),b'first')

    def test_capsule_hash_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'capsule.json';p.write_bytes(b'fixture')
            binding={'capsule':{'path':str(p),'sha256':worker.hashed(p),'bytes':7}}
            worker.verify_inputs(binding)
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):worker.verify_inputs(binding)

    def test_unknown_input_rejected(self):
        with self.assertRaises(ValueError):worker.verify_inputs({'unknown':{}})

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a';p.write_bytes(b'fixture');q=Path(d)/'link';q.symlink_to(p)
            with self.assertRaises(ValueError):worker.hashed(q)

    def test_existing_campaign_prevents_registration(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(controller,'bind_inputs',side_effect=AssertionError('must not read assets')):
                with self.assertRaises(ValueError):controller.register(Path(d),Path(d))

    def test_existing_attempt_prevents_retry(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);(path/'attempt').mkdir()
            with patch.object(controller,'verified_program',return_value={}),patch.object(controller,'run_limited',side_effect=AssertionError('must not launch')):
                with self.assertRaises(ValueError):controller.execute(path)

    def test_terminal_rejects_unregistered_plan_fields(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);attempt=path/'attempt';attempt.mkdir()
            program=dict(inputs={},source_sha256={},runtime={},arm_order=controller.ARM_ORDER)
            (path/'program.json').write_bytes(worker.canonical_json(program))
            plan=dict(schema='archive-gram-plan-v35',program_sha256=worker.hashed(path/'program.json'),inputs={},source_sha256={'unregistered':'source'},runtime={},arm_order=controller.ARM_ORDER,output=str(attempt/'outputs'))
            (attempt/'plan.json').write_bytes(worker.canonical_json(plan))
            with self.assertRaisesRegex(ValueError,'plan differs'):
                controller.verify_terminal(path,program)

    def test_checkpoint_complete_rows_transpose(self):
        # Software-only deterministic values expose a mistaken Conv1D transpose.
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.safetensors'
            matrix=np.zeros((768,2304),dtype='<f4')
            matrix[:,:4]=np.arange(768*4,dtype=np.float32).reshape(768,4)
            raw=matrix.tobytes();header=json.dumps({'transformer.h.0.attn.c_attn.weight':dict(dtype='F32',shape=[768,2304],data_offsets=[0,len(raw)])}).encode()
            p.write_bytes(struct.pack('<Q',len(header))+header+raw)
            actual=worker.checkpoint_rows(p)
            self.assertEqual(actual.shape,(4,768))
            np.testing.assert_array_equal(actual,matrix[:,:4].T)

    def test_reference_rows_preserve_grid_encoding(self):
        from src.compact_state import StageCodes
        from types import SimpleNamespace
        values=np.array([[0.,1.,-1.],[0.,2.,-2.],[0.,4.,-4.],[0.,8.,-8.]],dtype=np.float64)
        stage=StageCodes.from_array(worker.STAGE,values,grid_axis='dyadic_row',bits=4,scale_values=(1.,2.,4.,8.))
        # Reference helper correctly extracts exactly four rows with full stage width.
        stage768=StageCodes.from_array(worker.STAGE,np.tile(values,(1,256)),grid_axis='dyadic_row',bits=4,scale_values=(1.,2.,4.,8.))
        np.testing.assert_array_equal(worker.reference_rows(SimpleNamespace(stages=[stage768])),np.tile(values,(1,256)))

if __name__=='__main__':unittest.main()
