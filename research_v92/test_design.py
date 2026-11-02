"""Frozen workload and complete finite output census, without model execution."""
import copy,unittest
from research_v84 import config as old
from research_v92 import config,storage_plan
from research_v90.outputs import allowance
from research_v80.io import info
class Design(unittest.TestCase):
    def test_exact_workload_and_resource_caps_are_preserved(self):
        for k in ('ORDER','TRIALS','CAP','CELLS','PROFILES','ARM_ORDER','LOCAL_ORDER'):self.assertEqual(getattr(config,k),getattr(old,k))
        self.assertEqual(config.CAP,82840);self.assertEqual(config.design()['controller_cpu_allowance_seconds'],6040)
        for t in config.ORDER:self.assertEqual(config.cpu(t),(300,10202,302))
    def test_every_actual_artifact_and_progress_file_is_reserved(self):
        sources={'fixture.py':info(b'x')};p=storage_plan.build(sources,10240)
        rows=[r for r in p['roles'] if r['role']=='worker_outputs']
        self.assertEqual(len(rows),20)
        for r in rows:
            a=allowance(r['operation']);self.assertEqual((r['bytes'],r['files']),(a['output_bytes'],a['output_files']))
        self.assertEqual(sum(allowance(t)['progress_files'] for t in config.ORDER),1714)
    def test_later_operations_never_credit_old_outputs(self):
        sources={'fixture.py':info(b'x')};p=storage_plan.build(sources,10240)
        req=[storage_plan.requests(p,sources,10240,op) for op in config.OPERATIONS]
        self.assertTrue(all(x['project']['required_bytes']>=y['project']['required_bytes'] for x,y in zip(req,req[1:])))
        self.assertTrue(all(x['temporary']==req[0]['temporary'] for x in req));self.assertFalse(p['old_outputs_credited_as_free'])
    def test_changed_source_or_missing_output_role_refuses(self):
        sources={'fixture.py':info(b'x')};p=storage_plan.build(sources,10240);q=copy.deepcopy(p);q['roles'].pop()
        with self.assertRaises(ValueError):storage_plan.requests(q,sources,10240,'checks')
        with self.assertRaises(ValueError):storage_plan.requests(p,{'fixture.py':info(b'xx')},10240,'checks')
    def test_operation_names_are_unique_and_all_walls_are_preserved(self):
        self.assertEqual(len({config.name(t) for t in config.OPERATIONS}),23)
        for t in config.ORDER:self.assertEqual(config.wall(t),old.TRIALS[t]['wall_seconds']+600)
        self.assertEqual([config.wall(t) for t in ('checks','primary','supplemental')],[600,9000,5400])
        with self.assertRaises(ValueError):config.name('gpt2/unknown')
if __name__=='__main__':unittest.main()
