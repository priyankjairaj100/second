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
    def test_every_registered_worker_has_exact_artifact_census(self):
        base={'execution-provenance.json','admission.json'}
        rebuilt={'model.bin','lossless-state.bin','lossless-trust.json','compressed48-state.bin','compressed48-trust.json','hybrid_gram-state.bin','hybrid_gram-trust.json','modern_lossless-state.bin','modern_lossless-trust.json'}
        for trial in ORDER:
            with self.subTest(trial=trial):
                local=trial.split('/')[1]
                expected=base|rebuilt if local=='prepare' else base|{f'step-{step}/'+name for step in (1,2) for name in rebuilt} if local=='oracle' else base|{'model.bin','state.bin','trust.json'}
                self.assertEqual(expected_artifacts(trial),expected)
    def test_artifact_census_refuses_unknown_trial(self):
        for trial in ('gpt2/oracle/step-3','gpt2/unknown','other/prepare'):
            with self.assertRaises(ValueError):expected_artifacts(trial)
    def test_artifact_census_returns_independent_sets(self):
        first=expected_artifacts('gpt2/oracle');first.clear()
        self.assertEqual(len(expected_artifacts('gpt2/oracle')),20)
    def test_declaration_matches_actual_production_operation_sources(self):
        # Inspect the frozen source without importing numerical modules on Mac.
        import ast
        root=Path(__file__).resolve().parents[1]
        service=ast.parse((root/'research_v64/service.py').read_text())
        modern=next(ast.literal_eval(node.value) for node in service.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='REPRESENTATION' for t in node.targets))
        operations=ast.parse((root/'research_v81/operations.py').read_text())
        value=next(node.value for node in operations.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='REPRESENTATIONS' for t in node.targets))
        actual=tuple(modern if isinstance(node,ast.Name) and node.id=='MODERN' else ast.literal_eval(node) for node in value.elts)
        self.assertEqual(REBUILT_REPRESENTATIONS,actual)
if __name__=='__main__':unittest.main()
