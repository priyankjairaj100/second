"""Complete admission write census and exact V88 request compatibility."""
import unittest
from research_v101.storage_plan import build,requests
from research_v101.records import LAYOUT
from research_v101.config import ORDER
from research_v88.storage import requests as validate_requests

class Storage(unittest.TestCase):
    def setUp(self):self.sources={'fixture.py':dict(bytes=1024,sha256='a'*64)};self.plan=build(self.sources,10240)
    def test_both_existing_filesystems_and_monotone_remaining_allowance(self):
        previous=None
        for op in (None,*ORDER):
            r=requests(self.plan,self.sources,10240,op);self.assertEqual(validate_requests(r),r)
            if previous is not None:self.assertLessEqual(r['project']['required_bytes'],previous)
            previous=r['project']['required_bytes'];self.assertGreater(r['temporary']['required_bytes'],16*2**30)
    def test_every_finite_metadata_record_is_counted(self):
        role=next(r for r in self.plan['roles'] if r['role']=='metadata')
        self.assertEqual(role['files'],len(LAYOUT));self.assertEqual(role['bytes'],sum(LAYOUT.values()))
        self.assertIn('software-results.json',LAYOUT)
    def test_source_mutation_unbounded_extent_and_plan_mutation_refuse(self):
        with self.assertRaises(ValueError):requests(self.plan,self.sources,10241)
        with self.assertRaises(ValueError):build(self.sources,64*2**20+1)
        with self.assertRaises(ValueError):build({'a':dict(bytes=64*2**20,sha256='a'*64),'b':dict(bytes=1,sha256='b'*64)},100)
    def test_complete_screen_is_explicitly_outside_this_plan(self):
        self.assertFalse(self.plan['later_complete_screen_covered']);self.assertFalse(self.plan['capacity_reserved'])
        self.assertEqual({r['operation'] for r in self.plan['roles'] if r['operation']},set(ORDER))

if __name__=='__main__':unittest.main()
