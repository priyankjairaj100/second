"""Real small ledger tests for every future command; no numerical workload."""
import os,copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from research_v100.contracts import contract,budget,admit
from research_v100.config import ORDER,CAP,design
from src.run_store import canonical_json,digest
class Contracts(unittest.TestCase):
    def setup_trial(self,root,trial):
        sha='a'*64;p=dict(design(),sources={'fixture.py':dict(bytes=3,sha256='b'*64)})
        c=contract(trial,sha,'76543',0,root=root,cwd=root,executable='/usr/bin/python3')
        ledger=budget(p,sha,root=root)
        binding=dict(schema='limited-worker-identity-v1',identity=c['identity'],command=c['command'],cwd=str(root),limits=c['limits'].payload(),
            phase_budget=dict(binding_sha256=ledger.identity_digest,phase='feasibility',directory=str(ledger.root)))
        attempt=digest(canonical_json(dict(worker=binding,attempt=str(c['worker_root']/'attempt-0001'))))
        ledger.reserve('feasibility',attempt,c['limits'].cpu_seconds+2)
        env=dict(phase_budget_root=str(ledger.root),phase_budget_binding_sha256=ledger.identity_digest,attempt_id=attempt,
            phase='feasibility',command=c['command'],cwd=str(root))
        return p,sha,c,ledger,env
    def test_all_twenty_literal_commands_share_live_ledger_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve()
            for trial in ORDER:
                p,sha,c,b,e=self.setup_trial(root,trial);before=(b.root/'ledger.json').read_bytes()
                with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(e).decode()):self.assertEqual(admit(c,p,sha),e)
                self.assertEqual(before,(b.root/'ledger.json').read_bytes())
            self.assertEqual(b.snapshot()['charged_cpu_seconds'],{'feasibility':CAP})
    def test_other_profile_or_changed_command_cannot_spend_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p,sha,c,b,e=self.setup_trial(root,ORDER[0])
            for change in ('profile','command'):
                altered=copy.deepcopy(c)
                if change=='command':altered['command'][2]=altered['command'][2].replace('research_v100','research_v84')
                else:altered=contract('gpt2/prepare',sha,'76543',0,root=root,cwd=root,executable='/usr/bin/python3')
                with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(e).decode()),self.assertRaises(ValueError):admit(altered,p,sha)
    def test_settled_and_absent_admission_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            p,sha,c,b,e=self.setup_trial(Path(d).resolve(),ORDER[0])
            with patch.dict(os.environ,{},clear=True),self.assertRaises(ValueError):admit(c,p,sha)
            b.settle(e['attempt_id'],10)
            with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(e).decode()),self.assertRaises(ValueError):admit(c,p,sha)
    def test_source_change_refuses_without_ledger_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            p,sha,c,b,e=self.setup_trial(Path(d).resolve(),ORDER[0]);before=(b.root/'ledger.json').read_bytes();p['sources']['fixture.py']['bytes']=4
            with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(e).decode()),self.assertRaises(ValueError):admit(c,p,sha)
            self.assertEqual(before,(b.root/'ledger.json').read_bytes())
    def test_missing_readonly_budget_is_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p=dict(design(),sources={'fixture.py':dict(bytes=3,sha256='b'*64)})
            with self.assertRaises(ValueError):budget(p,'a'*64,root=root,read_only=True)
            self.assertFalse((root/'budget').exists())
if __name__=='__main__':unittest.main()
