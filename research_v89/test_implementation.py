"""Actual Linux activation identity plus adversarial completion mutations."""
from copy import deepcopy
from unittest.mock import patch
import unittest
from research_v79 import implementation as impl
from research_v89.implementation_audit import verify_implementation
from research_v89 import worker

class Checks(unittest.TestCase):
    def test_actual_four_implementations_and_identity_corruption(self):
        for cell in impl.CELLS:
            with self.subTest(cell=cell):
                with impl.execution(cell) as m:
                    if cell=='optimized_modern':
                        impl.modern_codec._select(b'\0'*128)
                        impl.modern_codec._select(b'\0'*128)
                self.assertTrue(verify_implementation(cell+'-1',m,m['primal']))
                for key,value in [('closed',False),('resident_reservation_bytes',8*2**30),('implementation_sha256','0'*64)]:
                    bad=deepcopy(m);bad[key]=value
                    with self.assertRaises(ValueError):verify_implementation(cell+'-1',bad,bad['primal'])
                if cell.startswith('optimized_'):
                    bad=deepcopy(m);next(iter(bad['tokens'].values()))['source_sha256']='0'*64
                    with self.assertRaises(ValueError):verify_implementation(cell+'-1',bad,bad['primal'])

    def test_cache_overage_and_uncleared_entries_refuse(self):
        with impl.execution('optimized_modern') as m:
            impl.modern_codec._select(b'abc'*80)
        for field,value in [('entries',1),('retained_bytes',1),('peak_retained_bytes',impl.CACHE_BYTES+1)]:
            bad=deepcopy(m);bad['cache'][field]=value
            with self.assertRaises(ValueError):verify_implementation('optimized_modern-2',bad,bad['primal'])

    def test_preparation_must_use_reference_context(self):
        with impl.execution('optimized_compressed') as m:pass
        with self.assertRaises(ValueError):verify_implementation('prepare',m,m['primal'])

    def test_process_api_consumes_even_failed_attempt(self):
        with patch.object(worker,'_CONSUMED',False),patch.object(worker,'_main',side_effect=ValueError('injected')) as run:
            with self.assertRaises(ValueError):worker.main('not-an-empirical-plan')
            with self.assertRaises(RuntimeError):worker.main('not-an-empirical-plan')
            self.assertEqual(run.call_count,1)
