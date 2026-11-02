"""Historical archive admission and fresh-worker command fixtures."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from research_v54 import archive,campaign,worker
from src.run_store import canonical_json
from src.transaction_timing import verify_command_admission

class ArchiveAdmissionTests(unittest.TestCase):
    def test_later_metadata_is_disclosed_without_claiming_fresh_selection(self):
        a={'old':{'sha256':'1'*64,'bytes':123}}
        b=dict(a,later={'sha256':'2'*64,'bytes':456})
        original=deepcopy(a);current=deepcopy(b)
        r=archive.compare_history(a,b)
        self.assertEqual(r['added'],{'later':b['later']})
        self.assertFalse(r['sampling_reexecuted']);self.assertFalse(r['new_independence_claim'])
        self.assertEqual(a,original);self.assertEqual(b,current)
    def test_changed_or_removed_original_history_fails(self):
        a={'old':{'sha256':'1'*64,'bytes':123}}
        for b in ({},{'old':{'sha256':'2'*64,'bytes':123}},{'old':{'sha256':'1'*64,'bytes':124}}):
            with self.assertRaisesRegex(ValueError,'missing or changed'):archive.compare_history(a,b)
    def test_exact_historical_inventory_is_still_accepted(self):
        r=archive.compare_history({'a':{'sha256':'1'*64,'bytes':1}},{'a':{'sha256':'1'*64,'bytes':1}})
        self.assertEqual(r['added'],{});self.assertTrue(r['original_entries_unchanged'])
    def test_original_registration_source_and_runtime_are_not_relaxed(self):
        with tempfile.TemporaryDirectory() as folder:
            d=Path(folder).resolve()
            p=dict(directory=str(d),policy=archive.POLICY,sources={'old.py':'s'},runtime={'pin':1},history={})
            def read(path):return p if path.name=='program.json' else {'program_sha256':archive.PROGRAM}
            with patch.object(archive,'read',side_effect=read),patch.object(archive,'sha',return_value=archive.PROGRAM),patch.object(archive.data_phase,'sources',return_value={'old.py':'s'}),patch.object(archive,'runtime',return_value={'pin':1}),patch.object(archive,'inventory',return_value={}):
                self.assertEqual(archive.validate_archive(d),p)
                p['runtime']={'pin':2}
                with self.assertRaisesRegex(ValueError,'runtime'):archive.validate_archive(d)
                p['runtime']={'pin':1};p['sources']={'old.py':'tampered'}
                with self.assertRaisesRegex(ValueError,'sources'):archive.validate_archive(d)
    def test_new_literal_command_has_its_own_cpu_admission(self):
        with tempfile.TemporaryDirectory() as folder:
            d=Path(folder).resolve();(d/'program.json').write_bytes(canonical_json({'fixture':True}))
            command=[worker.sys.executable,'-B','-m','research_v54.worker',str(d/'plan.json')]
            with patch('src.experiment_inventory.source_hashes',return_value={'fixture':'1'*64}),patch.object(campaign,'source_hashes',return_value={'fixture':'1'*64}):
                b=campaign.budget({'directory':str(d)});b.reserve('feasibility','fixture',10)
                admission=dict(phase_budget_root=str(b.root),phase_budget_binding_sha256=b.identity_digest,attempt_id='fixture',phase='feasibility',command=command,cwd=str(campaign.ROOT))
                with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(admission).decode()):
                    verify_command_admission(campaign.sha(d/'program.json'),'feasibility',command)
                    old=[x.replace('research_v54.worker','research_v53.worker') for x in command]
                    with self.assertRaisesRegex(ValueError,'exact command'):verify_command_admission(campaign.sha(d/'program.json'),'feasibility',old)
    def test_numerical_service_and_state_are_frozen_v53_implementations(self):
        from research_v53.service import Service
        from research_v53.state import validate_state
        from research_v53.campaign import ORDER,TRIALS,CAP
        self.assertIs(worker.Service,Service);self.assertIs(worker.validate_state,validate_state)
        self.assertEqual(campaign.ORDER,ORDER);self.assertEqual(campaign.TRIALS,TRIALS);self.assertEqual(campaign.CAP,CAP)

if __name__=='__main__':unittest.main()
