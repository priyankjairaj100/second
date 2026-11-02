"""Complete host/software/numerical CPU partitions preserve original ceilings."""
import unittest
from research_v104.config import ORDER
from research_v104.host import reconcile_cpu
class Accounting(unittest.TestCase):
    def entry(self,numerical=0,software=0,child=100,own=20):
        return dict(sealed_worker_cpu_ns=numerical,software_tree_cpu_ns=software,waited_child_cpu_ns=child,process_cpu_ns=own)
    def test_all_worker_controllers_keep_302_second_ceiling(self):
        for t in ORDER:
            r=reconcile_cpu(t,5,5,120,self.entry(numerical=90));self.assertEqual(r['nonnumerical_cpu_ns'],40)
            self.assertEqual(r['nonnumerical_cap_seconds'],301 if t=='distilgpt2/prepare' else 302)
            with self.assertRaises(ValueError):reconcile_cpu(t,303*10**9,0,120,self.entry(numerical=90))
    def test_uncontained_cpu_and_nested_double_count_refuse(self):
        with self.assertRaises(ValueError):reconcile_cpu(ORDER[0],0,0,100,self.entry(numerical=120))
        r=reconcile_cpu(ORDER[0],1,2,120,self.entry(numerical=90));self.assertEqual(r['envelope_cpu_ns'],123)
    def test_audits_and_software_have_distinct_full_caps(self):
        for op,cap in [('primary',7201),('supplemental',3601)]:
            r=reconcile_cpu(op,10,0,120,self.entry());self.assertEqual(r['nonnumerical_cap_seconds'],cap)
            with self.assertRaises(ValueError):reconcile_cpu(op,(cap+1)*10**9,0,120,self.entry())
        with self.assertRaises(ValueError):reconcile_cpu('checks',303*10**9,0,300*10**9,self.entry(software=300*10**9,child=300*10**9,own=0))
if __name__=='__main__':unittest.main()
