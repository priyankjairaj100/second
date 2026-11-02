"""Generated held-job guards; no scheduler operations."""
import unittest
from research_v89.submit import held_ok
BASE='JobState=PENDING JobName=second89-checks NumCPUs=1 Requeue=0 MinMemoryNode=16G ReqNodeList=csis.mn1 TimeLimit=00:10:00 Reason=JobHeldUser Priority=0 Dependency=(null)'
class Held(unittest.TestCase):
    def test_exact_resources_and_optional_dependency(self):
        self.assertTrue(held_ok(BASE,'checks','00:10:00',None));self.assertTrue(held_ok(BASE.replace('(null)','afterok:123(unfulfilled)'),'checks','00:10:00','123'))
    def test_substring_wrong_resources_and_extra_dependency_refuse(self):
        for a,b in [('NumCPUs=1','NumCPUs=10'),('16G','16Gx'),('Requeue=0','Requeue=1'),('csis.mn1','csis.mn2'),('PENDING','RUNNING'),('(null)','afterok:123')]:self.assertFalse(held_ok(BASE.replace(a,b),'checks','00:10:00',None))
        self.assertFalse(held_ok(BASE.replace('(null)','afterok:123(unfulfilled),afterany:9'),'checks','00:10:00','123'))
    def test_duplicate_fields_and_wrong_name_refuse(self):
        with self.assertRaises(ValueError):held_ok(BASE+' NumCPUs=2','checks','00:10:00',None)
        self.assertFalse(held_ok(BASE,'other','00:10:00',None))
if __name__=='__main__':unittest.main()
