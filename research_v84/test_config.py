"""Pure protocol/admission structure tests, not model evidence."""
import unittest
from research_v84.config import *
class MatchedProtocol(unittest.TestCase):
    def test_complete_twenty_trial_census(self):
        self.assertEqual(len(ORDER),20);self.assertEqual(len(set(ORDER)),20);self.assertEqual(set(ORDER),set(TRIALS))
        for profile in PROFILES:self.assertEqual([t.split('/')[1] for t in ORDER if t.startswith(profile+'/')],LOCAL_ORDER)
    def test_same_rows_grids_cells_and_unchanged_ceiling(self):
        p=design();self.assertEqual(p['normalization'],512);self.assertEqual(p['retained_counts'],[3,2]);self.assertEqual(p['grid_allowance'],1327104)
        self.assertEqual(CAP,82840);self.assertLessEqual(CAP,p['preserved_phase_ceiling']);self.assertLessEqual(p['controller_cpu_allowance_seconds'],p['preserved_controller_ceiling'])
        self.assertEqual(p['process_address_space_bytes'],16*2**30)
    def test_predecessor_never_crosses_checkpoint_or_cell(self):
        for profile in PROFILES:
            for cell in CELLS:
                self.assertEqual(predecessor(profile+'/'+cell+'-1')[0],profile+'/prepare')
                self.assertEqual(predecessor(profile+'/'+cell+'-2')[0],profile+'/'+cell+'-1')
    def test_fresh_prepare_and_oracle_cannot_have_predecessor(self):
        for profile in PROFILES:
            for local in ('prepare','oracle'):
                with self.assertRaises(ValueError):predecessor(profile+'/'+local)
    def test_unregistered_trial_and_third_deletion_refuse(self):
        for trial in ('gpt2/reference_modern-3','other/prepare','gpt2/../prepare','prepare'):
            with self.assertRaises(ValueError):trial_parts(trial)
if __name__=='__main__':unittest.main()
