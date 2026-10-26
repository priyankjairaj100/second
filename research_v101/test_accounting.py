"""Separate software/target clocks and shared controller ceiling."""
import unittest
from research_v101.host import reconcile_cpu
N=10**9
class Accounting(unittest.TestCase):
    def row(self,work,kind):return dict(process_cpu_ns=2*N,waited_child_cpu_ns=(work+3)*N,
        sealed_worker_cpu_ns=work*N if kind=='target' else 0,software_tree_cpu_ns=work*N if kind=='software' else 0)
    def test_target_cpu_is_contained_and_not_double_counted(self):
        r=reconcile_cpu('gpt2',N,N,105*N,self.row(100,'target'))
        self.assertEqual(r['envelope_cpu_ns'],107*N);self.assertEqual(r['nonnumerical_cpu_ns'],7*N)
    def test_software_helpers_are_inside_software_and_controller_partitions(self):
        r=reconcile_cpu('checks',N,N,105*N,self.row(100,'software'))
        self.assertEqual(r['contained_kind'],'generated_software');self.assertEqual(r['nonnumerical_cpu_ns'],7*N)
    def test_refuse_missing_child_cpu(self):
        with self.assertRaises(ValueError):reconcile_cpu('gpt2',N,N,100*N,self.row(100,'target'))
    def test_complete_controller_and_software_caps_are_independent(self):
        with self.assertRaises(ValueError):reconcile_cpu('gpt2',301*N,N,105*N,self.row(100,'target'))
        with self.assertRaises(ValueError):reconcile_cpu('checks',N,N,545*N,self.row(540,'software'))
        with self.assertRaises(ValueError):reconcile_cpu('checks',291*N,N,105*N,self.row(100,'software'))
    def test_fetch_is_all_controller_work(self):
        r=reconcile_cpu('fetch',N,N,5*N,self.row(0,'none'));self.assertEqual(r['nonnumerical_cpu_ns'],7*N)
    def test_invalid_cpu_types_fail(self):
        with self.assertRaises(ValueError):reconcile_cpu('fetch',True,N,5*N,self.row(0,'none'))

if __name__=='__main__':unittest.main()
