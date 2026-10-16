"""Actual five-arm tiny-model integration; no empirical checkpoint or corpus."""
import sys
import unittest
from research_v50.neighbors import enabled
from research_v59.test_anchor import RECORDS
from research_v61.test_service import tiny_service
from research_v63 import archive
from research_v66.operations import AllRepresentationsService, ARM_REPRESENTATION, MODERN, rebuild, request
from research_v66.test_operations import MemoryWriter


class LinuxOperationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform!='linux':raise RuntimeError('Pinned Linux numerical gate required, no skip')

    def test_five_requests_equal_fresh_model_state_and_trust(self):
        service=object.__new__(AllRepresentationsService)
        service.__dict__.update(tiny_service().__dict__)
        prep=MemoryWriter();fresh=MemoryWriter()
        with enabled():
            initial=rebuild(service,RECORDS,prep)
            expected=rebuild(service,RECORDS[1:],fresh)
            for arm,representation in ARM_REPRESENTATION.items():
                with self.subTest(arm=arm):
                    written=MemoryWriter()
                    def read():
                        if arm=='cold':self.fail('Cold accessed predecessor')
                        return prep.files[representation+'-state.bin'],prep.files[representation+'-trust.json']
                    result=request(service,RECORDS,RECORDS[1:],arm,read,written)
                    self.assertEqual(written.files['model.bin'],fresh.files['model.bin'])
                    self.assertEqual(written.files['state.bin'],fresh.files[representation+'-state.bin'])
                    self.assertEqual(written.files['trust.json'],fresh.files[representation+'-trust.json'])
                    self.assertEqual(result['code_count'],expected['code_count'])
                    if arm in ['cached','modern']:self.assertEqual(result['timing']['neural_stage_record_pairs'],0)
                    if arm in ['cold','hybrid']:self.assertEqual(result['timing']['neural_stage_record_pairs'],len(service.target.stages))
            self.assertEqual(archive.restore(archive.unpack(fresh.files[MODERN+'-state.bin'])),fresh.files['lossless-state.bin'])
            self.assertEqual(initial['common_timing']['neural_stage_record_pairs'],2*len(service.target.stages))
            self.assertTrue(expected['independent_retained_token_traversal'])
            self.assertFalse(expected['prior_state_read'])


if __name__=='__main__':unittest.main()
