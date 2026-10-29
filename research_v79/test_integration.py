"""Prospective Linux tests of real tiny service kernels; not empirical evidence."""
import sys
import unittest
from unittest.mock import patch
from dataclasses import replace

from research_v59.test_anchor import RECORDS
from research_v61.test_service import tiny_service
from research_v66.operations import AllRepresentationsService, ARM_REPRESENTATION, rebuild, request
from research_v66.test_operations import MemoryWriter
from research_v79 import implementation as impl


def service():
    s = object.__new__(impl.IntegratedService)
    s.__dict__.update(tiny_service().__dict__)
    return s


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != 'linux':
            raise RuntimeError('Pinned Linux numerical test required, no skips')

    def test_actual_four_cells_equal_fresh_model_state_and_trust(self):
        prep = MemoryWriter(); fresh = MemoryWriter()
        with impl.execution('reference_modern'):
            s = service(); rebuild(s, RECORDS, prep)
            expected = rebuild(s, RECORDS[1:], fresh)
        for cell, arm in impl.CELLS.items():
            with self.subTest(cell=cell), impl.execution(cell) as metadata:
                s = service(); out = MemoryWriter(); rep = ARM_REPRESENTATION[arm]
                answer = request(s, RECORDS, RECORDS[1:], arm,
                    lambda: (prep.files[rep+'-state.bin'], prep.files[rep+'-trust.json']), out)
                self.assertEqual(out.files['model.bin'], fresh.files['model.bin'])
                self.assertEqual(out.files['state.bin'], fresh.files[rep+'-state.bin'])
                self.assertEqual(out.files['trust.json'], fresh.files[rep+'-trust.json'])
                self.assertEqual(answer['code_count'], expected['code_count'])
                self.assertEqual(answer['admission']['resident_reservation_bytes'], impl.RESIDENT_BYTES)
                self.assertEqual(answer['timing']['neural_stage_record_pairs'], 0)
                self.assertTrue(all(row['admission']['resident_bytes'] >= impl.RESIDENT_BYTES
                                    for row in answer['timing']['stages']))
            self.assertTrue(metadata['closed'])
            if cell == 'optimized_modern':
                self.assertGreater(metadata['cache_before_close']['hits'], 0)
                self.assertEqual(metadata['cache']['entries'], 0)
                self.assertEqual(metadata['cache']['retained_bytes'], 0)
                self.assertTrue(metadata['cache']['closed'])

    def test_failure_restores_every_dispatch_and_clears_cache(self):
        original_assess = impl.dispatcher.assess_stage
        original_decode = impl.compressed_codec._decode_payload
        original_select = impl.modern_codec._select
        for cell in impl.CELLS:
            with self.subTest(cell=cell):
                with self.assertRaisesRegex(RuntimeError, 'injected failure'):
                    with impl.execution(cell) as metadata:
                        with self.assertRaisesRegex(RuntimeError, 'Fresh dedicated'):
                            with impl.execution(cell):
                                self.fail('Nested scope admitted')
                        if cell == 'optimized_modern':
                            impl.modern_codec._select(b'\0'*128)
                        raise RuntimeError('injected failure')
                self.assertIs(impl.dispatcher.assess_stage, original_assess)
                self.assertIs(impl.compressed_codec._decode_payload, original_decode)
                self.assertIs(impl.modern_codec._select, original_select)
                self.assertTrue(metadata['closed'])
                if cell == 'optimized_modern':
                    self.assertTrue(metadata['cache']['closed'])
                    self.assertEqual(metadata['cache']['entries'], 0)

    def test_resident_refusal_precedes_predecessor_access(self):
        for cell, arm in impl.CELLS.items():
            with self.subTest(cell=cell), impl.execution(cell):
                s = service(); s.policy = replace(s.policy, max_process_bytes=8*2**30)
                with self.assertRaises(ValueError):
                    request(s, RECORDS, RECORDS[1:], arm,
                            lambda: self.fail('Opened state before resident admission'), MemoryWriter())

    def test_corrupt_state_refuses_before_solver_in_optimized_cells(self):
        prep = MemoryWriter()
        with impl.execution('reference_modern'):
            rebuild(service(), RECORDS, prep)
        for cell in ('optimized_compressed', 'optimized_modern'):
            with self.subTest(cell=cell), impl.execution(cell):
                arm = impl.CELLS[cell]; rep = ARM_REPRESENTATION[arm]
                before = prep.files[rep+'-state.bin']+b'x'
                with patch.object(impl.dispatcher, 'solve_blocks', side_effect=AssertionError('solver accessed')):
                    with self.assertRaises(ValueError):
                        request(service(), RECORDS, RECORDS[1:], arm,
                                lambda: (before, prep.files[rep+'-trust.json']), MemoryWriter())

    def test_single_use_outer_transaction_closes_and_matches_fresh(self):
        prep = MemoryWriter(); fresh = MemoryWriter()
        with impl.execution('reference_modern'):
            s = service(); rebuild(s, RECORDS, prep); rebuild(s, RECORDS[1:], fresh)
        out = MemoryWriter(); rep = ARM_REPRESENTATION['modern']
        result = impl.transaction(service, RECORDS, RECORDS[1:], 'optimized_modern',
            lambda: (prep.files[rep+'-state.bin'], prep.files[rep+'-trust.json']), out)
        self.assertEqual(out.files['model.bin'], fresh.files['model.bin'])
        self.assertEqual(out.files['state.bin'], fresh.files[rep+'-state.bin'])
        self.assertGreater(result['context_request_cleanup_elapsed_ns'], result['request_elapsed_ns'])
        self.assertTrue(result['implementation']['closed'])
        with self.assertRaisesRegex(RuntimeError, 'Fresh process'):
            impl.transaction(service, RECORDS, RECORDS[1:], 'optimized_modern', None, None)


if __name__ == '__main__':
    unittest.main()
