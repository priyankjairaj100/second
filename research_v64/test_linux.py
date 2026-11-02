"""Actual tiny numerical integration, restricted to the pinned Linux runtime.

Only software-generated decoder fixtures and four artificial tokens are used.
No model checkpoint download, empirical input, quality data or campaign is read.
"""
import sys
import unittest

from research_v50.neighbors import enabled
from research_v59 import anchor
from research_v59.test_anchor import RECORDS
from research_v61 import service as old
from research_v61.test_service import tiny_service
from research_v63 import archive
from research_v64.service import ModernService, REPRESENTATION


class LinuxNumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != 'linux':
            raise RuntimeError('Pinned Linux numerical gate required, no platform skip')

    def test_actual_solver_and_fresh_teacher_reconstruction_equal(self):
        reference=tiny_service()
        modern=object.__new__(ModernService)
        modern.__dict__.update(reference.__dict__)
        original=reference.extract(RECORDS,old.telemetry())
        payloads,_,_=modern.prepare_payloads(RECORDS,original,REPRESENTATION,old.telemetry())
        with enabled():
            initial,_=reference.solve(RECORDS,'lossless',{}, {}, {},old.telemetry(),direct_values=original)
            predecessor=modern.serialize(RECORDS,initial,REPRESENTATION,payloads,{}, {},old.telemetry())
            repaired,codes,_=modern.repair(predecessor,RECORDS,RECORDS[1:],old.telemetry())
            # Fresh teacher traversals do not read the predecessor descriptors.
            retained=reference.extract(RECORDS[1:],old.telemetry())
            expected,_=anchor.calibrate(reference.decoder,reference.base,RECORDS[1:])
            direct,_=reference.solve(RECORDS[1:],'lossless',{}, {}, {},old.telemetry(),direct_values=retained)
        self.assertEqual(codes,expected)
        self.assertEqual(codes,direct)
        fresh_payloads,_,_=modern.prepare_payloads(RECORDS[1:],retained,REPRESENTATION,old.telemetry())
        fresh=modern.serialize(RECORDS[1:],expected,REPRESENTATION,fresh_payloads,{}, {},old.telemetry())
        self.assertEqual(repaired,fresh)
        view=archive.unpack(repaired)
        old_payloads,_,_=reference.prepare_payloads(RECORDS[1:],retained,'lossless',old.telemetry())
        legacy=reference.serialize(RECORDS[1:],expected,'lossless',old_payloads,{}, {},old.telemetry())
        self.assertEqual(archive.restore(view),legacy)
        self.assertEqual(view.target,reference.bound)
        self.assertEqual(len(codes),len(reference.target.stages))


if __name__=='__main__':unittest.main()
